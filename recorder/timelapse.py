from itertools import zip_longest
from pathlib import Path
from datetime import datetime
from tempfile import NamedTemporaryFile

import httpx
from moviepy import VideoFileClip, CompositeVideoClip, TextClip
from moviepy.video.fx import CrossFadeIn, CrossFadeOut

from gcs import list_gcs_recordings, upload_to_gcs

DOWNLOAD_DIR = "./.downloads"


def create_and_upload_timelapse(
    start: datetime,
    end: datetime,
    device: str,
    duration: int,
    recording_dir: Path,
) -> None:
    with NamedTemporaryFile(suffix=".mp4") as temp_file:
        _make_timelapse(
            start,
            end,
            device,
            Path(temp_file.name),
            recording_dir,
            total_time=duration,
            fade_duration=1,
        )
        upload_to_gcs(
            temp_file.name,
            f"{recording_dir}/timelapses/{device}/{start.isoformat()}_{end.isoformat()}.mp4",
        )


def _make_timelapse(
    start: datetime,
    end: datetime,
    device: str,
    dest: Path,
    recording_dir: Path,
    total_time: int | None = None,
    fade_duration: int | None = None,
) -> None:
    fade_duration = fade_duration or 0
    recordings = list_gcs_recordings(f"{recording_dir}/{device}")
    recordings_in_range = [
        r for r in recordings if start <= datetime.fromisoformat(r.time) <= end
    ]
    downloaded_files = [_download_recording(r.url) for r in recordings_in_range]
    times = [datetime.fromisoformat(r.time) for r in recordings_in_range]
    clips = [VideoFileClip(str(f)).with_speed_scaled(2) for f in downloaded_files]
    text_clips = [
        TextClip(
            text=t.strftime("%Y-%m-%d %H:%M:%S"),
            size=(200, 100),
            color="white",
            text_align="center",
            horizontal_align="center",
        )
        .with_position((0.75, 0.9), relative=True)
        .with_duration(c.duration)
        for t, c in zip(times, clips)
    ]
    optional_durations = [clip.duration for clip in clips]
    if any(d is None for d in optional_durations):
        raise ValueError("Could not get duration of all clips")
    durations = [d for d in optional_durations if d is not None]

    minimal_compression = min(
        _minimal_compression(
            times[i],
            durations[i],
            times[i + 1],
            fade_duration,
        )
        for i in range(len(durations) - 1)
    )

    if total_time is not None:
        desired_compression = (total_time - durations[-1]) / (
            times[-1] - times[0]
        ).total_seconds()
        if desired_compression > minimal_compression:
            raise ValueError("Cannot create timelapse with desired duration")
        compression = desired_compression
    else:
        compression = minimal_compression

    starts = [compression * (t - times[0]).total_seconds() for t in times]

    clips = [
        clip.with_start(start).subclipped(0, (end + fade_duration) if end else None)
        for clip, start, end in zip_longest(clips, starts, starts[1:])
    ]
    text_clips = [
        tc.with_start(start).subclipped(0, (end + fade_duration) if end else None)
        for tc, start, end in zip_longest(text_clips, starts, starts[1:])
    ]

    if fade_duration is not None:
        clips = (
            [clips[0].with_effects([CrossFadeOut(fade_duration)])]
            + [c.with_effects([CrossFadeIn(fade_duration)]) for c in clips[1:-1]]
            + [clips[-1].with_effects([CrossFadeIn(fade_duration)])]
        )
        text_clips = (
            [text_clips[0].with_effects([CrossFadeOut(fade_duration)])]
            + [
                tc.with_effects(
                    [CrossFadeIn(fade_duration), CrossFadeOut(fade_duration)]
                )
                for tc in text_clips[1:-1]
            ]
            + [text_clips[-1].with_effects([CrossFadeIn(fade_duration)])]
        )

    timelapse = CompositeVideoClip(clips + text_clips)
    timelapse.write_videofile(dest)


def _minimal_compression(s1: datetime, d1: float, s2: datetime, fade: float) -> float:
    return (d1 - fade) / (s2 - s1).total_seconds()


def _download_recording(url: str) -> Path:
    name = url.split("/")[-1]
    dest = Path(DOWNLOAD_DIR) / name
    if dest.exists():
        return dest
    response = httpx.get(url)
    response.raise_for_status()
    dest.parent.mkdir(parents=True, exist_ok=True)
    with open(dest, "wb") as f:
        f.write(response.content)
    return dest
