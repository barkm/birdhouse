from pathlib import Path
from datetime import datetime
from subprocess import check_output
from tempfile import NamedTemporaryFile

import httpx

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
        recordings = list_gcs_recordings(f"{recording_dir}/{device}")
        recordings_in_range = [
            r for r in recordings if start <= datetime.fromisoformat(r.time) <= end
        ]
        downloaded_files = [_download_recording(r.url) for r in recordings_in_range]
        times = [datetime.fromisoformat(r.time) for r in recordings_in_range]
        _make_timelapse(
            downloaded_files,
            times,
            Path(temp_file.name),
            total_time=duration,
            fade_duration=1,
        )
        upload_to_gcs(
            temp_file.name,
            f"{recording_dir}/timelapses/{device}/{start.isoformat()}_{end.isoformat()}.mp4",
        )


def _make_timelapse(
    files: list[Path],
    times: list[datetime],
    dest: Path,
    total_time: float | None = None,
    fade_duration: float | None = None,
) -> None:
    if fade_duration is not None and fade_duration < 0.1:
        raise ValueError("fade_duration must be at least 0.1 seconds")
    fade_duration = fade_duration if fade_duration is not None else 0.1
    durations = [_get_video_duration(d) for d in files]
    minimal_compression = min(
        _minimal_compression(
            times[i],
            durations[i],
            times[i + 1],
            fade_duration,
        )
        for i in range(len(durations) - 1)
    )
    average_clip_spacing = sum(
        (times[i + 1] - times[i]).total_seconds() for i in range(len(times) - 1)
    ) / (len(times) - 1)
    if total_time is not None:
        desired_compression = total_time / (
            average_clip_spacing + (times[-1] - times[0]).total_seconds()
        )
        if desired_compression > minimal_compression:
            raise ValueError(
                f"Cannot create timelapse with desired duration: {desired_compression} > {minimal_compression}"
            )
        compression = desired_compression
    else:
        compression = minimal_compression
    starts = [compression * (t - times[0]).total_seconds() for t in times]
    last_clip_duration = compression * average_clip_spacing
    _crossfade_videos(files, starts, last_clip_duration, dest)


def _get_video_duration(path: Path) -> float:
    return float(
        check_output(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(path),
            ]
        )
    )


def _crossfade_videos(
    video_paths: list[Path], starts: list[float], last_clip_duration: float, dest: Path
) -> None:
    filter_parts = [
        f"{'[0:v]' if i == 0 else f'[v_fade_{i}]'}[{i + 1}:v]xfade=transition=fade:duration=1:offset={starts[i + 1]}[v_fade_{i + 1}]"
        for i in range(len(video_paths) - 1)
    ]
    command = [
        "ffmpeg",
        "-y",
        *[arg for path in video_paths for arg in ["-i", str(path)]],
        "-filter_complex",
        ";".join(filter_parts),
        "-map",
        f"[v_fade_{len(video_paths) - 1}]",
        "-t",
        str(starts[-1] + last_clip_duration),
        "-pix_fmt",
        "yuv420p",
        str(dest),
    ]
    check_output(command)


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
