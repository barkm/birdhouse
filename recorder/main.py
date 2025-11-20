from contextlib import asynccontextmanager
from itertools import zip_longest
from pathlib import Path
from datetime import datetime
from subprocess import CalledProcessError, run
from tempfile import NamedTemporaryFile
import logging
from typing import Callable

from common.auth.exception import AuthException
from fastapi.responses import FileResponse, JSONResponse
import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import BaseModel
from google.cloud import storage
from moviepy import VideoFileClip, CompositeVideoClip, TextClip
from moviepy.video.fx import CrossFadeIn, CrossFadeOut

from common.auth import firebase
from common.auth import google

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

DOWNLOAD_DIR = "./.downloads"


class Settings(BaseSettings):
    relay_url: str | None = None
    recording_dir: str = "/recordings"
    allowed_emails: list[str] | None = None

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@asynccontextmanager
async def lifespan(_: FastAPI):
    firebase.initialize()
    yield


settings = Settings()
app = FastAPI(lifespan=lifespan)


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    headers = dict(request.headers)

    verifiers = [
        firebase.verify,
        lambda headers: google.verify(headers, settings.allowed_emails),
    ]

    responses = [get_auth_response(headers, verify) for verify in verifiers]

    if any(response is None for response in responses):
        return await call_next(request)

    return next(response for response in responses if response is not None)


def get_auth_response(
    headers: dict[str, str],
    verify: Callable[[dict[str, str]], JSONResponse | None],
) -> JSONResponse | None:
    try:
        return verify(headers)
    except AuthException as e:
        return JSONResponse({"detail": e.detail}, status_code=e.status_code)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/record")
async def record(duration: int = 10) -> dict:
    if settings.relay_url is None:
        logging.error("Relay url not set")
        return {"error": "Relay url not set"}
    devices = _get_devices(settings.relay_url)
    for device in devices:
        _record_and_save(settings.relay_url, device, settings.recording_dir, duration)
    return {}


def _get_devices(relay_url: str) -> list[str]:
    list_url = f"{relay_url}/list"
    try:
        response = httpx.get(list_url)
        response.raise_for_status()
        return [
            device["name"]
            for device in response.json()
            if device["name"] == "birdhouse"
        ]
    except httpx.HTTPError as e:
        logging.warning(f"Failed to get devices from {list_url}: {e}")
        return []


def _record_and_save(
    relay_url: str, device: str, recording_dir: str, duration: int
) -> None:
    output_path = f"{recording_dir}/{device}/{datetime.now().isoformat()}.mp4"
    if recording_dir.startswith("gs://"):
        with NamedTemporaryFile(suffix=".mp4") as temp_file:
            _record(relay_url, device, temp_file.name, duration)
            _upload_to_gcs(temp_file.name, output_path)
    else:
        _record(relay_url, device, output_path, duration)


def _record(relay_url: str, device: str, output_path: str, duration: int) -> None:
    logging.info(f"Saving recording for {device}")
    start_url = f"{relay_url}/{device}/start"
    start_response = httpx.get(
        start_url, params={"bitrate": 10000000, "framerate": 30}, timeout=20.0
    )
    start_response.raise_for_status()
    playlist_path = start_response.json()["playlist"]
    playlist_url = f"{relay_url}/{device}{playlist_path}"
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    # fmt: off
    command = [
        "ffmpeg", "-y",
        "-i", playlist_url,
        "-t", str(duration),
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
    bucket_name, dest = _get_bucket_and_blob_name(gcs_path)
    logging.info(f"Uploading {source} to {dest} in {bucket_name}.")
    client = storage.Client(project="birdhouse-464804")
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(dest)
    blob.upload_from_filename(source)
    logging.info(f"File {source} uploaded to {dest} in {bucket_name}.")


class Recording(BaseModel):
    time: str
    url: str


@app.get("/recording/{path:path}")
def get_recording(path: str) -> FileResponse:
    return FileResponse(f"{settings.recording_dir}/{path}")


@app.get("/recordings/{device}")
def list_recordings(request: Request, device: str) -> list[Recording]:
    if settings.recording_dir.startswith("gs://"):
        return _list_gcs_recordings(f"{settings.recording_dir}/{device}")
    return _list_local_recordings(str(request.base_url), settings.recording_dir, device)


@app.get("/timelapse")
def create_timelapse(start: datetime, end: datetime, duration: int) -> None:
    devices = _get_devices(settings.relay_url or "")
    for device in devices:
        _create_and_upload_timelapse(start, end, device, duration)


def _list_local_recordings(
    url: str, recording_dir: str, device: str
) -> list[Recording]:
    return [
        Recording(
            time=path.stem, url=f"{url}recording/{path.relative_to(recording_dir)}"
        )
        for path in Path(recording_dir, device).iterdir()
    ]


def _list_gcs_recordings(gcs_dirpath: str) -> list[Recording]:
    bucket_name, prefix = _get_bucket_and_blob_name(gcs_dirpath)
    client = storage.Client(project="birdhouse-464804")
    bucket = client.bucket(bucket_name)
    blobs = bucket.list_blobs(prefix=prefix)
    return [
        Recording(
            time=Path(blob.name).stem,
            url=f"https://storage.googleapis.com/{bucket_name}/{blob.name}",
        )
        for blob in blobs
    ]


def _get_bucket_and_blob_name(gcs_path: str) -> tuple[str, str]:
    *_, bucket_name, blob_name = gcs_path.split("/", maxsplit=3)
    return bucket_name, blob_name


def _create_and_upload_timelapse(
    start: datetime,
    end: datetime,
    device: str,
    duration: int,
) -> None:
    with NamedTemporaryFile(suffix=".mp4") as temp_file:
        _make_timelapse(
            start,
            end,
            device,
            Path(temp_file.name),
            total_time=duration,
            fade_duration=1,
        )
        _upload_to_gcs(
            temp_file.name,
            f"{settings.recording_dir}/timelapses/{device}/{start.isoformat()}_{end.isoformat()}.mp4",
        )


def _make_timelapse(
    start: datetime,
    end: datetime,
    device: str,
    dest: Path,
    total_time: int | None = None,
    fade_duration: int | None = None,
) -> None:
    fade_duration = fade_duration or 0
    recordings = _list_gcs_recordings(f"{settings.recording_dir}/{device}")
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
