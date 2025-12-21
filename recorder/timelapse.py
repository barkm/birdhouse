from dataclasses import dataclass
from itertools import batched
import logging
import math
from pathlib import Path
from datetime import datetime
import shutil
import tempfile
from uuid import uuid4
import ffmpeg


def make_timelapse(
    files: list[str],
    times: list[datetime],
    dest: Path,
    total_time: float | None = None,
    fade_duration: float | None = None,
    batch_size: int | None = None,
) -> None:
    if fade_duration is not None and fade_duration < 0.1:
        raise ValueError("fade_duration must be at least 0.1 seconds")
    fade_duration = fade_duration if fade_duration is not None else 0.1
    durations = [_get_video_duration(f) for f in files]
    durations_files = [
        (d, f, t) for d, f, t in zip(durations, files, times) if d > fade_duration
    ]
    durations = [d for d, _, _ in durations_files]
    files = [f for _, f, _ in durations_files]
    times = [t for _, _, t in durations_files]
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
    if batch_size is None:
        logging.info("Crossfading all videos in a single pass")
        _crossfade_videos(
            files, starts, fade_duration, LIBX264, dest, last_clip_duration
        )
    else:
        logging.info(f"Crossfading videos in batches of {batch_size}")
        _crossfade_videos_constant_memory(
            files, starts, last_clip_duration, fade_duration, dest, batch_size
        )
    logging.info(f"Timelapse created at {dest}")


def _get_video_duration(path: str) -> float:
    return float(ffmpeg.probe(str(path), probesize="1M")["format"]["duration"])


def _minimal_compression(s1: datetime, d1: float, s2: datetime, fade: float) -> float:
    assert s2 > s1
    assert d1 > fade
    return (d1 - fade) / (s2 - s1).total_seconds()


def _crossfade_videos_constant_memory(
    video_paths: list[str],
    starts: list[float],
    last_clip_duration: float,
    fade_duration: float,
    dest: Path,
    batch_size: int,
    lossless: bool = False,
) -> None:
    if not video_paths:
        raise ValueError("No video paths provided")
    videos_with_starts = list(zip(video_paths, starts))
    total_passes = math.ceil(math.log(len(videos_with_starts), batch_size))
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir_path = Path(temp_dir)
        current_videos_with_starts = videos_with_starts
        for _pass in range(total_passes):
            logging.info(f"Starting pass {_pass + 1} / {total_passes}")
            next_videos_with_starts = []
            num_batches = (
                len(current_videos_with_starts) + batch_size - 1
            ) // batch_size
            for i, batch in enumerate(batched(current_videos_with_starts, batch_size)):
                logging.info(f"Processing batch {i + 1} / {num_batches}")
                if len(batch) == 1:
                    next_videos_with_starts.append(batch[0])
                    continue
                video_paths_batch = [vp for vp, _ in batch]
                first_start = batch[0][1]
                batch_starts = [s - first_start for _, s in batch]
                temp_output = temp_dir_path / f"{uuid4().hex}.mov"
                _crossfade_videos(
                    video_paths_batch,
                    batch_starts,
                    fade_duration,
                    PRORES if lossless else LIBX264,
                    temp_output,
                    None,
                )
                next_videos_with_starts.append((temp_output, first_start))
            current_videos_with_starts = next_videos_with_starts

        final_video_path, final_start = current_videos_with_starts[0]
        assert final_start == starts[0]
        if lossless:
            logging.info("Re-encoding final video to target format")
            _reencode_video(
                final_video_path, dest, LIBX264, starts[-1] + last_clip_duration
            )
        else:
            if last_clip_duration is None:
                shutil.copy(final_video_path, dest)
            else:
                logging.info("Trimming final video to target duration")
                ffmpeg.input(str(final_video_path)).trim(
                    duration=starts[-1] + last_clip_duration
                ).output(str(dest)).run(overwrite_output=True, quiet=True)


@dataclass
class Codec:
    name: str
    profile: str
    pix_fmt: str


LIBX264 = Codec(name="libx264", profile="main", pix_fmt="yuv420p")
PRORES = Codec(name="prores_ks", profile="3", pix_fmt="yuv422p10le")


def _crossfade_videos(
    video_paths: list[str],
    starts: list[float],
    duration: float,
    codec: Codec,
    dest: Path,
    last_clip_duration: float | None = None,
) -> None:
    if not video_paths:
        raise ValueError("No video paths provided")
    if len(video_paths) == 1:
        shutil.copy(video_paths[0], dest)
        return
    inputs = [ffmpeg.input(str(path)) for path in video_paths]

    xfade = None
    for i in range(len(inputs) - 1):
        input1 = inputs[i] if i == 0 else xfade
        input2 = inputs[i + 1]
        xfade = ffmpeg.filter(
            [input1, input2],
            "xfade",
            transition="fade",
            duration=duration,
            offset=starts[i + 1],
        )

    output = ffmpeg.output(
        xfade,
        str(dest),
        vcodec=codec.name,
        profile=codec.profile,
        pix_fmt=codec.pix_fmt,
        **(
            {"t": starts[-1] + last_clip_duration}
            if last_clip_duration is not None
            else {}
        ),
    )
    ffmpeg.run(output, overwrite_output=True, quiet=True)


def _reencode_video(
    input_path: str, output_path: Path, codec: Codec, duration: float | None = None
) -> None:
    input_ = ffmpeg.input(str(input_path))
    output = ffmpeg.output(
        input_,
        str(output_path),
        vcodec=codec.name,
        profile=codec.profile,
        pix_fmt=codec.pix_fmt,
        **({"t": duration} if duration is not None else {}),
    )
    ffmpeg.run(output, overwrite_output=True)
