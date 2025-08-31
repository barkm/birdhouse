from pathlib import Path
from datetime import datetime
from subprocess import CalledProcessError, run
from tempfile import NamedTemporaryFile
import logging

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic_settings import BaseSettings
from google.cloud import storage

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


class Settings(BaseSettings):
    relay_url: str | None = None
    recording_dir: str = "/recordings"


settings = Settings()
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/record")
async def record() -> dict:
    if settings.relay_url is None:
        logging.error("Relay url not set")
        return {"error": "Relay url not set"}
    devices = _get_devices(settings.relay_url)
    for device in devices:
        _record_and_save(settings.relay_url, device, settings.recording_dir)
    return {}


def _get_devices(relay_url: str) -> list[str]:
    list_url = f"{relay_url}/list"
    try:
        response = httpx.get(list_url)
        response.raise_for_status()
        return [device["name"] for device in response.json()]
    except httpx.HTTPError as e:
        logging.warning(f"Failed to get devices from {list_url}: {e}")
        return []


def _record_and_save(relay_url: str, device: str, recording_dir: str) -> None:
    output_path = f"{recording_dir}/{device}/{datetime.now().isoformat()}.mp4"
    if recording_dir.startswith("gs://"):
        with NamedTemporaryFile(suffix=".mp4") as temp_file:
            _record(relay_url, device, temp_file.name)
            _upload_to_gcs(temp_file.name, output_path)
    else:
        _record(relay_url, device, output_path)


def _record(relay_url: str, device: str, output_path: str) -> None:
    logging.info(f"Saving recording for {device}")
    start_url = f"{relay_url}/{device}/start"
    start_response = httpx.get(start_url)
    start_response.raise_for_status()
    playlist_path = start_response.json()["playlist"]
    playlist_url = f"{relay_url}/{device}{playlist_path}"
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    # fmt: off
    command = [
        "ffmpeg", "-y",
        "-i", playlist_url,
        "-t", "10",
        "-c:v", "libx264",
        "-c:a", "aac",
        "-movflags", "+faststart",
        "-profile:v", "main",
        "-pix_fmt", "yuv420p",
        output_path
    ]
    # fmt: on
    try:
        run(command, check=True, capture_output=True, text=True)
        logging.info(f"Finished recording video for {device} to {output_path}")
    except CalledProcessError as e:
        logging.error(
            f"Failed to record video for {device}: {e}\n"
            f"stderr: {e.stderr}\n"
            f"stdout: {e.stdout}"
        )


def _upload_to_gcs(source: str, gcs_path: str) -> None:
    *_, bucket_name, dest = gcs_path.split("/", maxsplit=3)
    logging.info(f"Uploading {source} to {dest} in {bucket_name}.")
    client = storage.Client(project="birdhouse-464804")
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(dest)
    blob.upload_from_filename(source)
    logging.info(f"File {source} uploaded to {dest} in {bucket_name}.")


@app.get("/list")
async def list_recordings():
    return "OK"
