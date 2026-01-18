from datetime import datetime
from tempfile import NamedTemporaryFile
import ffmpeg
import httpx


import logging
from pathlib import Path
from subprocess import CalledProcessError

import src.db.models as models
from src.gcs import upload_to_gcs

from sqlmodel import Session


def record_and_save(
    base_url: str,
    device_url: str,
    device: models.Device,
    recording_dir: str,
    duration: int,
    session: Session,
) -> None:
    output_path = f"{recording_dir}/{device.name}/{datetime.now().isoformat()}.mp4"
    if recording_dir.startswith("gs://"):
        with NamedTemporaryFile(suffix=".mp4") as temp_file:
            _record(device_url, device.name, temp_file.name, duration)
            url = upload_to_gcs(temp_file.name, output_path)
    else:
        _record(device_url, device.name, output_path, duration)
        url = _get_local_recording_url(base_url, recording_dir, Path(output_path))
    logging.info(f"Saved recording for {device.name} to {url}")
    recording = models.Recording(
        device_id=device.id,
        url=url,
    )
    session.add(recording)
    session.commit()
    session.refresh(recording)


def _record(device_url: str, device: str, output_path: str, duration: int) -> None:
    logging.info(f"Saving recording for {device}")
    start_url = f"{device_url}/start"
    start_response = httpx.get(
        start_url, params={"bitrate": 10000000, "framerate": 30}, timeout=60.0
    )
    try:
        start_response.raise_for_status()
    except httpx.HTTPStatusError as e:
        logging.error(f"Failed to start recording for {device}: {e}")
        raise RuntimeError(f"Failed to start recording for {device}: {e}") from e
    playlist_path = start_response.json()["playlist"]
    playlist_url = f"{device_url}{playlist_path}"
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    input_ = ffmpeg.input(playlist_url, t=duration)
    output = ffmpeg.output(
        input_,
        output_path,
        vcodec="libx264",
        acodec="aac",
        movflags="+faststart",
        profile="main",
        pix_fmt="yuv420p",
    )
    try:
        ffmpeg.run(output, overwrite_output=True, quiet=True)
        logging.info(f"Finished recording video for {device} to {output_path}")
    except CalledProcessError as e:
        logging.error(
            f"Failed to record video for {device}: {e}\n"
            f"stderr: {e.stderr}\n"
            f"stdout: {e.stdout}"
        )


def _get_local_recording_url(url: str, recording_dir: str, path: Path) -> str:
    return f"{url}recording/{path.relative_to(recording_dir)}"
