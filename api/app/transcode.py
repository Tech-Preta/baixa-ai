"""Turn separated streams into one file with ffmpeg. Video is remuxed, never re-encoded."""

import shutil
import subprocess
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from app.errors import MSG_GENERIC, MSG_TIMEOUT, MSG_TOO_LARGE, AppError
from app.media import MediaItem
from app.ytdlp_runner import download_format

DownloadFormat = Callable[[str, str, Path, float, int], Path]
RunCommand = Callable[[list[str], float], None]


@dataclass(frozen=True)
class LocalMedia:
    path: Path
    cleanup: Callable[[], None]


def mp3_command(source: Path, dest: Path) -> list[str]:
    return [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-threads",
        "1",
        "-i",
        str(source),
        "-vn",
        "-ac",
        "2",
        "-acodec",
        "libmp3lame",
        "-b:a",
        "192k",
        str(dest),
    ]


def remux_command(video: Path, audio: Path, dest: Path) -> list[str]:
    return [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-threads",
        "1",
        "-i",
        str(video),
        "-i",
        str(audio),
        "-map",
        "0:v:0",
        "-map",
        "1:a:0",
        "-c",
        "copy",
        "-movflags",
        "+faststart",
        str(dest),
    ]


def run_command(command: list[str], timeout: float) -> None:
    try:
        completed = subprocess.run(
            command,
            check=False,
            timeout=timeout,
            capture_output=True,
        )
    except subprocess.TimeoutExpired as exc:
        raise AppError("timeout", MSG_TIMEOUT, 504) from exc
    if completed.returncode != 0:
        raise AppError("extraction_failed", MSG_GENERIC, 502)


def prepare_local_media(
    item: MediaItem,
    page_url: str,
    timeout: float,
    max_bytes: int,
    *,
    download: DownloadFormat = download_format,
    run: RunCommand = run_command,
) -> LocalMedia:
    if item.filesize is not None and item.filesize > max_bytes:
        raise AppError("too_large", MSG_TOO_LARGE, 413)
    directory = Path(tempfile.mkdtemp(prefix="baixa-"))

    def cleanup() -> None:
        shutil.rmtree(directory, ignore_errors=True)

    try:
        if item.delivery == "mp3":
            if not item.audio_format_id:
                raise AppError("extraction_failed", MSG_GENERIC, 502)
            source_dir = directory / "source"
            source = download(page_url, item.audio_format_id, source_dir, timeout, max_bytes)
            dest = directory / "audio.mp3"
            run(mp3_command(source, dest), timeout)
            source.unlink(missing_ok=True)
        elif item.delivery == "merge":
            if not item.video_format_id or not item.audio_format_id:
                raise AppError("extraction_failed", MSG_GENERIC, 502)
            video = download(
                page_url,
                item.video_format_id,
                directory / "video",
                timeout,
                max_bytes,
            )
            audio = download(
                page_url,
                item.audio_format_id,
                directory / "audio",
                timeout,
                max_bytes,
            )
            dest = directory / "video.mp4"
            run(remux_command(video, audio, dest), timeout)
            video.unlink(missing_ok=True)
            audio.unlink(missing_ok=True)
        else:
            raise AppError("extraction_failed", MSG_GENERIC, 502)
        _enforce_size(dest, max_bytes)
    except Exception:
        cleanup()
        raise
    return LocalMedia(path=dest, cleanup=cleanup)


def _enforce_size(path: Path, max_bytes: int) -> None:
    if not path.is_file() or path.stat().st_size > max_bytes:
        raise AppError("too_large", MSG_TOO_LARGE, 413)
