"""yt-dlp metadata lookup. Public media only: no cookies, no account, no disk cache."""

import yt_dlp

from app.errors import MSG_NOT_FOUND, AppError


def ytdlp_options(timeout: float) -> dict:
    return {
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "no_color": True,
        "skip_download": True,
        "noplaylist": False,
        "playlistend": 20,
        "socket_timeout": max(1, int(timeout)),
        "retries": 1,
        "extractor_retries": 1,
        "fragment_retries": 0,
        "cookiefile": None,
        "username": None,
        "password": None,
        "cachedir": False,
    }


def run_ytdlp(url: str, timeout: float) -> dict:
    with yt_dlp.YoutubeDL(ytdlp_options(timeout)) as ydl:
        info = ydl.extract_info(url, download=False)
    if not isinstance(info, dict):
        raise AppError("not_found", MSG_NOT_FOUND, 404)
    return info
