from dataclasses import dataclass
from pathlib import Path
import platform
import subprocess
import tempfile
import uuid
import time
from threading import Lock, Timer
import logging

logger = logging.getLogger(__name__)


@dataclass
class Video:
    process: list[subprocess.Popen]
    directory: Path
    playlist_filename: str
    timer: Timer


class Stream:
    def __init__(
        self,
        test_stream: bool,
        idle_timeout: float | None = None,
    ):
        self.test_stream = test_stream
        self.idle_timeout = idle_timeout
        self.video = None
        self.video_lock = Lock()

    def get_file(self, filename: str) -> Path | None:
        if Path(filename).suffix not in {".m3u8", ".ts"}:
            return None
        if not self.video:
            return None
        path = self.video.directory / filename
        return path if path.exists() else None

    def start(self, bitrate: int = 500000, framerate: int = 24) -> str:
        with self.video_lock:
            if self.video:
                self.video.timer.cancel()
                self.video.timer = self._get_video_timer()
            else:
                logger.info("Starting video stream")
                directory = Path(tempfile.mkdtemp())
                playlist_filename, process = _start_hls_video_stream(
                    directory,
                    self.test_stream,
                    bitrate,
                    framerate,
                )
                self.video = Video(
                    directory=directory,
                    playlist_filename=playlist_filename,
                    process=process,
                    timer=self._get_video_timer(),
                )
            self.video.timer.start()
        return self.video.playlist_filename

    def _get_video_timer(self) -> Timer:
        return (
            Timer(self.idle_timeout, self.stop)
            if self.idle_timeout is not None
            else Timer(1e6, self.stop)
        )

    def stop(self) -> None:
        with self.video_lock:
            if self.video:
                logger.info("Stopping video stream")
                for process in self.video.process:
                    process.terminate()
                _remove_directory(self.video.directory)
                self.video.timer.cancel()
                self.video = None


def _remove_directory(dirpath: Path) -> None:
    for child in dirpath.iterdir():
        if child.is_dir():
            _remove_directory(child)
        else:
            child.unlink()
    dirpath.rmdir()


def _start_hls_video_stream(
    stream_dir: Path, test_stream: bool, bitrate: int, framerate: int
) -> tuple[str, list[subprocess.Popen]]:
    stream_dir.mkdir(parents=True, exist_ok=True)
    stream_file_path = stream_dir / "playlist.m3u8"
    segment_filename = stream_dir / (uuid.uuid4().hex + "_%04d.ts")
    process = _start_stream_process(
        stream_dir, stream_file_path, segment_filename, test_stream, bitrate, framerate
    )
    _wait_until_exists(stream_file_path)
    return "playlist.m3u8", process


def _start_stream_process(
    stream_dir: Path,
    stream_filepath: Path,
    segment_filepath: Path,
    test_stream: bool,
    bitrate: int,
    framerate: int,
) -> list[subprocess.Popen]:
    if test_stream:
        return [_start_test_stream(stream_dir, segment_filepath, stream_filepath)]
    if is_raspberry_pi():
        return _start_hls_video_stream_raspberry_pi(
            segment_filepath, stream_filepath, bitrate, framerate
        )
    if is_mac():
        return [_start_hls_video_stream_mac(segment_filepath, stream_filepath)]
    raise RuntimeError("Unsupported platform for HLS streaming")


def _wait_until_exists(path: Path) -> None:
    while not path.exists():
        time.sleep(0.1)


def _start_test_stream(
    stream_dir: Path, segment_filename: Path, stream_file_path: Path
) -> subprocess.Popen:
    test_file = _create_test_video_file(stream_dir)
    return subprocess.Popen(
        [
            "ffmpeg",
            "-re",
            "-stream_loop",
            "-1",
            "-i",
            str(test_file),
            *_ffmpeg_hls_arguments(segment_filename, stream_file_path),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def _create_test_video_file(stream_dir: Path) -> Path:
    video_file_path = stream_dir / "test.mp4"
    command = f"ffmpeg -f lavfi -i testsrc=size=1280x720:rate=30 -t 20 -c:v libx264 -g 60 -preset ultrafast {video_file_path}".split()
    subprocess.check_call(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return video_file_path


def _start_hls_video_stream_mac(
    segment_filename: Path, stream_file_path: Path
) -> subprocess.Popen:
    return subprocess.Popen(
        [
            "ffmpeg",
            "-framerate",
            "30",
            "-f",
            "avfoundation",
            "-i",
            "0",
            *_ffmpeg_hls_arguments(segment_filename, stream_file_path),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def _start_hls_video_stream_raspberry_pi(
    segment_filename: Path, stream_file_path: Path, bitrate: int, framerate: int
) -> list[subprocess.Popen]:
    if not _raspberry_pi_camera_available():
        raise RuntimeError("Raspberry Pi camera not available")
    # fmt: off
    rpicam = subprocess.Popen(
        [
            "rpicam-vid",
            "-t", "0",
            "--width", "1920",
            "--height", "1080",
            "--framerate", f"{framerate}",
            "--intra", f"{framerate * 2}",
            "--codec", "h264",
            "--profile", "high",
            "--bitrate", f"{bitrate}",
            "-o",
            "-",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    # fmt: on
    ffmpeg = subprocess.Popen(
        [
            "ffmpeg",
            "-i",
            "-",
            *_ffmpeg_hls_arguments(segment_filename, stream_file_path),
        ],
        stdin=rpicam.stdout,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return [rpicam, ffmpeg]


def _ffmpeg_hls_arguments(segment_filename: Path, stream_file_path: Path) -> list[str]:
    return [
        "-c:v",
        "copy",
        "-f",
        "hls",
        "-hls_time",
        "10",
        "-hls_list_size",
        "60",
        "-hls_flags",
        "delete_segments",
        "-hls_segment_filename",
        str(segment_filename),
        str(stream_file_path),
    ]


def _raspberry_pi_camera_available() -> bool:
    return "No cameras available!" not in subprocess.check_output(
        ["rpicam-vid", "--list-cameras"]
    ).decode("utf-8")


def is_mac():
    """Checks if the code is running on a macOS machine."""
    return platform.system() == "Darwin"


def is_raspberry_pi():
    """Checks if the code is running on a Raspberry Pi."""
    if not platform.system() == "Linux":
        return False

    model_file = Path("/sys/firmware/devicetree/base/model")
    return model_file.exists() and "raspberry pi" in model_file.read_text().lower()
