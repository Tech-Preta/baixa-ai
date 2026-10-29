"""Turn a yt-dlp info dict into a small list of downloadable files."""

from collections.abc import Callable
from dataclasses import dataclass

from app.errors import (
    MSG_NOT_FOUND,
    MSG_TOO_LARGE,
    MSG_UNSUPPORTED,
    AppError,
    classify_extractor_error,
)

IMAGE_EXTS = {"jpg", "jpeg", "png", "webp", "gif"}
VIDEO_EXTS = {"mp4", "webm", "mov"}
EXT_CONTENT_TYPES = {
    "mp4": "video/mp4",
    "webm": "video/webm",
    "mov": "video/quicktime",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "webp": "image/webp",
    "gif": "image/gif",
}
_HEADER_ALLOW = {"user-agent", "referer", "accept", "accept-language", "origin"}


@dataclass(frozen=True)
class MediaItem:
    index: int
    format_id: str
    type: str
    ext: str
    label: str
    height: int | None
    filesize: int | None
    url: str
    headers: dict[str, str]


@dataclass(frozen=True)
class ExtractedMedia:
    provider: str
    page_url: str
    title: str | None
    author: str | None
    thumbnail_url: str | None
    items: list[MediaItem]


def safe_headers(raw: object) -> dict[str, str]:
    if not isinstance(raw, dict):
        return {}
    cleaned: dict[str, str] = {}
    for key, value in raw.items():
        if not isinstance(key, str) or not isinstance(value, str):
            continue
        if key.lower() in _HEADER_ALLOW and value.strip():
            cleaned[key] = value
    return cleaned


def extract_media(
    url: str,
    *,
    provider: str,
    timeout: float,
    max_file_bytes: int,
    max_items: int = 20,
    runner: Callable[[str, float], dict],
) -> ExtractedMedia:
    try:
        info = runner(url, timeout)
    except AppError:
        raise
    except Exception as exc:
        raise classify_extractor_error(exc) from exc
    return build_extracted(
        info,
        provider=provider,
        page_url=url,
        max_file_bytes=max_file_bytes,
        max_items=max_items,
    )


def build_extracted(
    info: dict,
    *,
    provider: str,
    page_url: str,
    max_file_bytes: int,
    max_items: int = 20,
) -> ExtractedMedia:
    if not isinstance(info, dict):
        raise AppError("not_found", MSG_NOT_FOUND, 404)
    entries = _entries(info, max_items)
    chosen: list[tuple[int, dict]] = []
    skipped_for_size = False
    for index, entry in enumerate(entries):
        formats, skipped = _options_for_entry(entry, max_file_bytes)
        skipped_for_size = skipped_for_size or skipped
        chosen.extend((index, fmt) for fmt in formats)
    if not chosen:
        if skipped_for_size:
            raise AppError("too_large", MSG_TOO_LARGE, 413)
        raise AppError("unsupported_content", MSG_UNSUPPORTED, 422)
    return ExtractedMedia(
        provider=provider,
        page_url=page_url,
        title=_title(info, entries),
        author=_author(info),
        thumbnail_url=_thumbnail(info, entries),
        items=_with_labels(chosen),
    )


def _entries(info: dict, max_items: int) -> list[dict]:
    raw_entries = info.get("entries")
    if info.get("_type") == "playlist" or isinstance(raw_entries, list):
        collected = [entry for entry in raw_entries or [] if isinstance(entry, dict)]
        return collected[:max_items]
    return [info]


def _options_for_entry(entry: dict, max_file_bytes: int) -> tuple[list[dict], bool]:
    skipped = False
    progressive: list[dict] = []
    images: list[dict] = []
    for fmt in entry.get("formats") or []:
        if not isinstance(fmt, dict):
            continue
        if _too_big(fmt, max_file_bytes):
            skipped = True
            continue
        if _is_progressive(fmt):
            progressive.append(fmt)
        elif _is_image(fmt):
            images.append(fmt)
    if progressive:
        return _best_videos(progressive), skipped
    if images:
        return [_best_image(images)], skipped
    direct = _direct_format(entry, max_file_bytes)
    if direct is not None:
        return [direct], skipped
    if _too_big(entry, max_file_bytes):
        skipped = True
    return [], skipped


def _best_videos(formats: list[dict], limit: int = 3) -> list[dict]:
    ranked = sorted(
        formats,
        key=lambda fmt: (
            fmt.get("height") or 0,
            fmt.get("tbr") or 0,
            _filesize(fmt) or 0,
        ),
        reverse=True,
    )
    picked: list[dict] = []
    seen_heights: set[int] = set()
    for fmt in ranked:
        height = int(fmt.get("height") or 0)
        if height and height in seen_heights:
            continue
        if height:
            seen_heights.add(height)
        picked.append(fmt)
        if len(picked) >= limit:
            break
    return picked


def _best_image(formats: list[dict]) -> dict:
    return max(formats, key=lambda fmt: (fmt.get("width") or 0, _filesize(fmt) or 0))


def _direct_format(entry: dict, max_file_bytes: int) -> dict | None:
    url = _http_url(entry.get("url"))
    ext = str(entry.get("ext") or "").lower()
    protocol = str(entry.get("protocol") or "")
    if not url or ext not in IMAGE_EXTS | VIDEO_EXTS:
        return None
    if protocol and ("m3u8" in protocol or "dash" in protocol):
        return None
    if _too_big(entry, max_file_bytes):
        return None
    format_id = entry.get("format_id") or "direct"
    return {
        "format_id": format_id,
        "ext": ext,
        "url": url,
        "height": entry.get("height"),
        "filesize": _filesize(entry),
        "http_headers": entry.get("http_headers") or {},
        "protocol": protocol or "https",
    }


def _with_labels(chosen: list[tuple[int, dict]]) -> list[MediaItem]:
    kinds = [_kind(fmt) for _, fmt in chosen]
    image_total = sum(kind == "image" for kind in kinds)
    video_entries: list[int] = []
    for (index, _fmt), kind in zip(chosen, kinds, strict=True):
        if kind == "video" and index not in video_entries:
            video_entries.append(index)

    items: list[MediaItem] = []
    image_seen = 0
    for (index, fmt), kind in zip(chosen, kinds, strict=True):
        ext = str(fmt.get("ext") or "bin").lower()
        height = fmt.get("height") if isinstance(fmt.get("height"), int) else None
        if kind == "image":
            image_seen += 1
            label = "Imagem" if image_total == 1 else f"Imagem {image_seen}"
        else:
            quality = f" · {height}p" if height else ""
            if len(video_entries) > 1:
                label = f"Vídeo {video_entries.index(index) + 1}{quality}"
            else:
                label = f"Vídeo{quality}"
        items.append(
            MediaItem(
                index=index,
                format_id=str(fmt.get("format_id") or "direct"),
                type=kind,
                ext=ext,
                label=label,
                height=height,
                filesize=_filesize(fmt),
                url=str(fmt["url"]),
                headers=safe_headers(fmt.get("http_headers")),
            )
        )
    return items


def _kind(fmt: dict) -> str:
    ext = str(fmt.get("ext") or "").lower()
    if ext in IMAGE_EXTS and not _is_progressive(fmt):
        return "image"
    return "video"


def _is_progressive(fmt: dict) -> bool:
    if fmt.get("vcodec") in (None, "none") or fmt.get("acodec") in (None, "none"):
        return False
    protocol = str(fmt.get("protocol") or "")
    if "m3u8" in protocol or "dash" in protocol or protocol.startswith("mhtml"):
        return False
    if not protocol.startswith("http"):
        return False
    return _http_url(fmt.get("url")) is not None


def _is_image(fmt: dict) -> bool:
    ext = str(fmt.get("ext") or "").lower()
    if ext not in IMAGE_EXTS:
        return False
    protocol = str(fmt.get("protocol") or "https")
    if "m3u8" in protocol or "dash" in protocol:
        return False
    return _http_url(fmt.get("url")) is not None


def _filesize(fmt: dict) -> int | None:
    for key in ("filesize", "filesize_approx"):
        value = fmt.get(key)
        if isinstance(value, int) and value >= 0:
            return value
    return None


def _too_big(fmt: dict, max_file_bytes: int) -> bool:
    size = _filesize(fmt)
    return size is not None and size > max_file_bytes


def _http_url(value: object) -> str | None:
    if isinstance(value, str) and value.startswith(("http://", "https://")):
        return value
    return None


def _clean_text(value: object, limit: int) -> str | None:
    if not isinstance(value, str):
        return None
    text = " ".join(value.split())
    if not text:
        return None
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def _author(info: dict) -> str | None:
    for key in ("uploader", "creator", "channel", "uploader_id"):
        text = _clean_text(info.get(key), 80)
        if text:
            return text
    return None


def _title(info: dict, entries: list[dict]) -> str | None:
    text = _clean_text(info.get("title"), 180)
    if text:
        return text
    if entries:
        titled = _clean_text(entries[0].get("title"), 180)
        if titled:
            return titled
    return _clean_text(info.get("description"), 180)


def _thumbnail(info: dict, entries: list[dict]) -> str | None:
    sources = [info, *entries[:1]]
    for source in sources:
        url = _http_url(source.get("thumbnail"))
        if url:
            return url
    return None
