"""yt-dlp metadata lookup. Public media only: no cookies, no account, no disk cache."""

import re
from pathlib import Path
from urllib.parse import urlsplit

import yt_dlp

from app.errors import MSG_GENERIC, MSG_NOT_FOUND, MSG_TOKEN, AppError

_FORMAT_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


def ytdlp_options(timeout: float, url: str = "") -> dict:
    return {
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "no_color": True,
        "skip_download": True,
        "noplaylist": _is_youtube(url),
        "playlistend": 20,
        "socket_timeout": max(1, int(timeout)),
        "retries": 1,
        "extractor_retries": 1,
        "fragment_retries": 0,
        "concurrent_fragment_downloads": 1,
        "cookiefile": None,
        "username": None,
        "password": None,
        "cachedir": False,
    }


def run_ytdlp(url: str, timeout: float) -> dict:
    with yt_dlp.YoutubeDL(ytdlp_options(timeout, url)) as ydl:
        info = ydl.extract_info(url, download=False)
    if not isinstance(info, dict):
        raise AppError("not_found", MSG_NOT_FOUND, 404)
    return info


def download_format(
    url: str,
    format_id: str,
    dest_dir: Path,
    timeout: float,
    max_bytes: int,
) -> Path:
    """Download one format id into dest_dir. The id is checked so it cannot be a selector."""
    safe_id = _require_format_id(format_id)
    dest_dir.mkdir(parents=True, exist_ok=True)
    before = {path.resolve() for path in dest_dir.iterdir()}
    options = ytdlp_options(timeout, url)
    options.update(
        {
            "skip_download": False,
            "noplaylist": True,
            "format": safe_id,
            "outtmpl": str(dest_dir / "source.%(ext)s"),
            "max_filesize": max_bytes,
        }
    )
    with yt_dlp.YoutubeDL(options) as ydl:
        ydl.download([url])
    created = [
        path
        for path in dest_dir.iterdir()
        if path.is_file() and path.resolve() not in before and not path.name.endswith(".part")
    ]
    if not created:
        raise AppError("extraction_failed", MSG_GENERIC, 502)
    return max(created, key=lambda path: path.stat().st_size)


def _require_format_id(format_id: str) -> str:
    if _FORMAT_ID.fullmatch(format_id or "") is None:
        raise AppError("invalid_token", MSG_TOKEN, 400)
    return format_id


def _is_youtube(url: str) -> bool:
    host = (urlsplit(url).hostname or "").lower().rstrip(".")
    return host in {"youtu.be", "youtube.com"} or host.endswith((".youtu.be", ".youtube.com"))
