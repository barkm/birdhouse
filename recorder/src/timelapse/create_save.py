from src.db import queries, models
from src.gcs import upload_to_gcs
from src.timelapse.timelapse import make_timelapse


from sqlmodel import Session


import logging
import os
import shutil
from datetime import datetime
from pathlib import Path
from tempfile import NamedTemporaryFile


def create_and_save_timelapse(
    start: datetime,
    end: datetime,
    device: models.Device,
    duration: int | None,
    fade_duration: float | None,
    batch_size: int | None,
    recording_dir: str,
    session: Session,
) -> None:
    with NamedTemporaryFile(suffix=".mp4") as temp_file:
        recordings = queries.get_recordings(session, device.name)
        if not recordings:
            logging.info(f"No recordings found for device {device}, skipping timelapse")
            return
        else:
            logging.info(f"Found {len(recordings)} recordings for device {device}")
        recordings_in_range = [r for r in recordings if start <= r.created_at <= end]
        logging.info(
            f"Found {len(recordings_in_range)} recordings for device {device} in range {start} - {end}"
        )
        urls = [r.url for r in recordings_in_range]
        times = [r.created_at for r in recordings_in_range]
        make_timelapse(
            urls,
            times,
            Path(temp_file.name),
            total_time=duration,
            fade_duration=fade_duration,
            batch_size=batch_size,
        )
        save_path = os.path.join(
            recording_dir,
            "timelapses",
            device.name,
            f"{start.isoformat()}_{end.isoformat()}.mp4",
        )
        if recording_dir.startswith("gs://"):
            upload_to_gcs(temp_file.name, str(save_path))
        else:
            shutil.move(temp_file.name, save_path)
