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

HLS_SEGMENT_LENGTH = 10
HLS_LIST_SIZE = 60


@dataclass
class Video:
    process: list[subprocess.Popen]
    directory: Path
    timer: Timer


class Stream:
    def __init__(
        self,
        playlist_filename: str,
        test_stream: bool,
        idle_timeout: float | None = None,
    ):
        self.playlist_filename = playlist_filename
        self.test_stream = test_stream
        self.idle_timeout = idle_timeout
        self.video = None
        self.video_lock = Lock()

    def get_file(self, filename: str) -> Path | None:
        if Path(filename).suffix not in {".m3u8", ".ts"}:
            return None
        path = self.start() / filename
        return path if path.exists() else None

    def start(self, bitrate: int = 500000, framerate: int = 24) -> Path:
        with self.video_lock:
            if self.video:
                self.video.timer.cancel()
                self.video.timer = self._get_video_timer()
            else:
                logger.info("Starting video stream")
                directory = Path(tempfile.mkdtemp())
                self.video = Video(
                    process=_start_hls_video_stream(
                        directory,
                        self.playlist_filename,
                        self.test_stream,
                        bitrate,
                        framerate,
                    ),
                    directory=directory,
                    timer=self._get_video_timer(),
                )
            self.video.timer.start()
        return self.video.directory

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
    stream_dir: Path, playlist_filename, test_stream: bool, bitrate: int, framerate: int
) -> list[subprocess.Popen]:
    stream_dir.mkdir(parents=True, exist_ok=True)
    stream_file_path = stream_dir / playlist_filename
    segment_filename = stream_dir / (uuid.uuid4().hex + "_%04d.ts")
    process = _start_stream_process(
        stream_dir, stream_file_path, segment_filename, test_stream, bitrate, framerate
    )
    _wait_until_exists(stream_file_path)
    return process


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
            "-c",
            "copy",
            "-f",
            "hls",
            "-hls_time",
            str(HLS_SEGMENT_LENGTH),
            "-hls_list_size",
            str(HLS_LIST_SIZE),
            "-hls_flags",
            "delete_segments",
            "-hls_segment_filename",
            str(segment_filename),
            str(stream_file_path),
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
            "-f",
            "hls",
            "-hls_time",
            str(HLS_SEGMENT_LENGTH),
            "-hls_list_size",
            str(HLS_LIST_SIZE),
            "-hls_flags",
            "delete_segments",
            "-hls_segment_filename",
            str(segment_filename),
            str(stream_file_path),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def _start_hls_video_stream_raspberry_pi(
    segment_filename: Path,
    stream_file_path: Path,
    bitrate: int,  # Not used for raw source, but kept for interface consistency
    framerate: int,
) -> list[subprocess.Popen]:
    if not _raspberry_pi_camera_available():
        raise RuntimeError("Raspberry Pi camera not available")

    # 1. SETUP: Define resolutions and bitrates
    # (Using slightly lower bitrates to save the Pi's CPU)
    width = 1920
    height = 1080

    # 2. RPICAM: Output RAW video (yuv420p) to stdout
    # We do not encode to h264 here anymore.
    # fmt: off
    rpicam = subprocess.Popen(
        [
            "rpicam-vid",
            "-t", "0",
            "--width", str(width),
            "--height", str(height),
            "--framerate", str(framerate),
            "--codec", "yuv420p", # Output raw data
            "-o", "-",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    # fmt: on

    # 3. FFMPEG: Ingest raw, Split, Scale, Encode x2 (High/Low)
    # We are doing 2 streams (1080p and 480p) to be realistic about Pi CPU.
    # If on Pi 5, you can add a 3rd stream.
    master_playlist = stream_file_path.with_name("master.m3u8")
    base_stream_name = stream_file_path.stem  # e.g. "stream"

    ffmpeg = subprocess.Popen(
        [
            "ffmpeg",
            # --- INPUT SETTINGS (Crucial for Raw Video) ---
            "-f",
            "rawvideo",
            "-vcodec",
            "rawvideo",
            "-s",
            f"{width}x{height}",  # Must match rpicam output
            "-r",
            str(framerate),
            "-pix_fmt",
            "yuv420p",
            "-i",
            "-",  # Read from stdin
            # --- FILTER GRAPH ---
            # Split input into 2 streams ([v1], [v2])
            # Scale [v2] down to 854x480
            "-filter_complex",
            "[0:v]split=2[v1][v2];[v2]scale=w=854:h=480[v2out]",
            # --- ENCODING STREAM 1 (High - 1080p) ---
            "-map",
            "[v1]",
            "-c:v:0",
            "libx264",
            "-b:v:0",
            "2500k",
            "-maxrate:v:0",
            "2675k",
            "-bufsize:v:0",
            "3000k",
            "-g",
            str(framerate * 2),
            "-keyint_min",
            str(framerate * 2),
            "-sc_threshold",
            "0",
            "-preset",
            "ultrafast",  # Crucial for Pi performance
            # --- ENCODING STREAM 2 (Low - 480p) ---
            "-map",
            "[v2out]",
            "-c:v:1",
            "libx264",
            "-b:v:1",
            "600k",
            "-maxrate:v:1",
            "642k",
            "-bufsize:v:1",
            "800k",
            "-g",
            str(framerate * 2),
            "-keyint_min",
            str(framerate * 2),
            "-sc_threshold",
            "0",
            "-preset",
            "ultrafast",
            # --- HLS SETTINGS ---
            "-f",
            "hls",
            "-hls_time",
            str(HLS_SEGMENT_LENGTH),
            "-hls_list_size",
            str(HLS_LIST_SIZE),
            "-hls_flags",
            "delete_segments+independent_segments",
            "-master_pl_name",
            str(master_playlist.name),
            # Map the variants to specific output m3u8 files
            "-hls_segment_filename",
            f"{stream_file_path.parent}/{base_stream_name}_%v_%03d.ts",
            "-var_stream_map",
            "v:0 v:1",
            # The output pattern for the variant playlists
            f"{stream_file_path.parent}/{base_stream_name}_%v.m3u8",
        ],
        stdin=rpicam.stdout,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    return [rpicam, ffmpeg]


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
