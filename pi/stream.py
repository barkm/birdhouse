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
    processes: list[subprocess.Popen]
    directory: Path
    playlist_filename: Path
    timer: Timer


class Stream:
    def __init__(
        self,
        test_stream: bool,
        idle_timeout: float | None = 60,
    ):
        self.test_stream = test_stream
        self.idle_timeout = idle_timeout
        self.video = None
        self.video_lock = Lock()

    def get_file(self, filename: str) -> Path | None:
        if Path(filename).suffix not in {".m3u8", ".ts"}:
            return None
        self.start()
        if not self.video:
            return None
        path = self.video.directory / filename
        return path if path.exists() else None

    def start(self, bitrate: int = 500000, framerate: int = 24) -> Path:
        with self.video_lock:
            if self.video:
                self.video.timer.cancel()
                self.video.timer = self._get_video_timer()
            else:
                logger.info("Starting video stream")
                directory = Path(tempfile.mkdtemp())
                playlist_path, processes = _start_hls_video_stream(
                    directory,
                    self.test_stream,
                    bitrate,
                    framerate,
                )
                self.video = Video(
                    directory=directory,
                    playlist_filename=playlist_path,
                    processes=processes,
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
                for process in self.video.processes:
                    process.terminate()
                for process in self.video.processes:
                    process.wait()
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
    work_dir: Path, test_stream: bool, bitrate: int, framerate: int
) -> tuple[Path, list[subprocess.Popen]]:
    work_dir.mkdir(parents=True, exist_ok=True)
    playlist_path, processes = _start_stream_processes(
        work_dir, test_stream, bitrate, framerate
    )
    _wait_until_exists(playlist_path)
    return playlist_path.relative_to(work_dir), processes


def _start_stream_processes(
    work_dir: Path,
    test_stream: bool,
    bitrate: int,
    framerate: int,
) -> tuple[Path, list[subprocess.Popen]]:
    if test_stream:
        return _start_test_stream(work_dir)
    if _is_raspberry_pi():
        return _start_hls_video_stream_raspberry_pi(work_dir, bitrate, framerate)
    if _is_mac():
        return _start_hls_video_stream_mac(work_dir)
    raise RuntimeError("Unsupported platform for HLS streaming")


def _wait_until_exists(path: Path) -> None:
    while not path.exists():
        time.sleep(0.1)


def _start_test_stream(work_dir: Path) -> tuple[Path, list[subprocess.Popen]]:
    test_file = _create_test_video_file(work_dir)
    playlist_path, hls_args = _ffmpeg_hls_arguments(work_dir)
    process = subprocess.Popen(
        [
            "ffmpeg",
            "-re",
            "-stream_loop",
            "-1",
            "-i",
            str(test_file),
            *hls_args,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return playlist_path, [process]


def _create_test_video_file(work_dir: Path) -> Path:
    video_file_path = work_dir / "test.mp4"
    # fmt: off
    command = [
        "ffmpeg",
        "-y",
        "-f", "lavfi", "-i", "testsrc=size=1280x720:rate=30",
        "-f", "lavfi", "-i", "sine=frequency=1000:sample_rate=48000",
        "-t", "20",
        "-c:v", "libx264", "-g", "60", "-preset", "ultrafast",
        "-c:a", "aac",
        "-pix_fmt", "yuv420p",
        str(video_file_path)
    ]
    # fmt: on
    subprocess.check_call(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return video_file_path


def _start_hls_video_stream_mac(
    segment_filename: Path,
) -> tuple[Path, list[subprocess.Popen]]:
    playlist_path, hls_args = _ffmpeg_hls_arguments(segment_filename)
    process = subprocess.Popen(
        [
            "ffmpeg",
            "-framerate",
            "30",
            "-f",
            "avfoundation",
            "-i",
            "0",
            *hls_args,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return playlist_path, [process]


def _start_hls_video_stream_raspberry_pi(
    work_dir: Path, bitrate: int, framerate: int
) -> tuple[Path, list[subprocess.Popen]]:
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
    playlist_path, hls_args = _ffmpeg_hls_arguments(work_dir)
    ffmpeg = subprocess.Popen(
        [
            "ffmpeg",
            "-i",
            "-",
            *hls_args,
        ],
        stdin=rpicam.stdout,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return playlist_path, [rpicam, ffmpeg]


def _ffmpeg_hls_arguments(work_dir: Path) -> tuple[Path, list[str]]:
    playlist_path = work_dir / "playlist.m3u8"
    segment_path = work_dir / (uuid.uuid4().hex + "_%04d.ts")
    args = [
        "-c:v",
        "copy",
        "-f",
        "hls",
        "-hls_time",
        "5",
        "-hls_list_size",
        "60",
        "-hls_flags",
        "delete_segments",
        "-hls_segment_filename",
        str(segment_path),
        str(playlist_path),
    ]
    return playlist_path, args


def _raspberry_pi_camera_available() -> bool:
    return "No cameras available!" not in subprocess.check_output(
        ["rpicam-vid", "--list-cameras"]
    ).decode("utf-8")


def _is_mac():
    return platform.system() == "Darwin"


def _is_raspberry_pi():
    if not platform.system() == "Linux":
        return False

    model_file = Path("/sys/firmware/devicetree/base/model")
    return model_file.exists() and "raspberry pi" in model_file.read_text().lower()
