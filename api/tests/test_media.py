import pytest

from app.errors import AppError
from app.media import build_extracted

VIDEO = {
    "format_id": "hd",
    "ext": "mp4",
    "protocol": "https",
    "vcodec": "avc1",
    "acodec": "mp4a",
    "height": 720,
    "tbr": 2000,
    "filesize": 4000,
    "url": "https://cdn.example/720.mp4",
    "http_headers": {
        "User-Agent": "Baixa",
        "Cookie": "session=nope",
        "Referer": "https://www.instagram.com/",
    },
}
SD = {
    "format_id": "sd",
    "ext": "mp4",
    "protocol": "https",
    "vcodec": "avc1",
    "acodec": "mp4a",
    "height": 360,
    "tbr": 800,
    "filesize": 1000,
    "url": "https://cdn.example/360.mp4",
    "http_headers": {"User-Agent": "Baixa"},
}
HLS = {
    "format_id": "hls",
    "ext": "mp4",
    "protocol": "m3u8_native",
    "vcodec": "avc1",
    "acodec": "mp4a",
    "height": 1080,
    "url": "https://cdn.example/playlist.m3u8",
}
VIDEO_ONLY = {
    "format_id": "vonly",
    "ext": "mp4",
    "protocol": "https",
    "vcodec": "avc1",
    "acodec": "none",
    "height": 1080,
    "url": "https://cdn.example/silent.mp4",
}


def test_picks_progressive_videos_and_strips_cookies() -> None:
    media = build_extracted(
        {
            "title": "Um reel\n curto",
            "uploader": "maria",
            "thumbnail": "https://cdn.example/thumb.jpg",
            "formats": [HLS, VIDEO_ONLY, SD, VIDEO],
        },
        provider="instagram",
        page_url="https://www.instagram.com/reel/AbC123/",
        max_file_bytes=10_000,
    )
    assert media.title == "Um reel curto"
    assert media.author == "maria"
    assert media.thumbnail_url == "https://cdn.example/thumb.jpg"
    assert [(item.format_id, item.label) for item in media.items] == [
        ("hd", "Vídeo · 720p"),
        ("sd", "Vídeo · 360p"),
    ]
    assert media.items[0].headers == {
        "User-Agent": "Baixa",
        "Referer": "https://www.instagram.com/",
    }
    assert "Cookie" not in media.items[0].headers


def test_carousel_images_are_numbered() -> None:
    entries = [
        {
            "id": str(index),
            "formats": [
                {
                    "format_id": f"img{index}",
                    "ext": "jpg",
                    "protocol": "https",
                    "vcodec": "none",
                    "acodec": "none",
                    "width": 1080,
                    "url": f"https://cdn.example/{index}.jpg",
                }
            ],
        }
        for index in (1, 2)
    ]
    media = build_extracted(
        {"_type": "playlist", "title": "Carrossel", "entries": entries},
        provider="instagram",
        page_url="https://www.instagram.com/p/AbC123/",
        max_file_bytes=10_000,
    )
    assert [item.label for item in media.items] == ["Imagem 1", "Imagem 2"]
    assert [item.type for item in media.items] == ["image", "image"]
    assert [item.index for item in media.items] == [0, 1]


def test_single_image_label() -> None:
    media = build_extracted(
        {
            "title": "Foto",
            "ext": "jpg",
            "url": "https://cdn.example/only.jpg",
            "protocol": "https",
        },
        provider="instagram",
        page_url="https://www.instagram.com/p/AbC123/",
        max_file_bytes=10_000,
    )
    assert len(media.items) == 1
    assert media.items[0].label == "Imagem"
    assert media.items[0].format_id == "direct"


def test_skips_oversized_formats_and_fails_when_nothing_fits() -> None:
    with pytest.raises(AppError) as exc:
        build_extracted(
            {"title": "Grande", "formats": [{**VIDEO, "filesize": 50_000}]},
            provider="tiktok",
            page_url="https://www.tiktok.com/@maria/video/1",
            max_file_bytes=1000,
        )
    assert exc.value.code == "too_large"
    assert exc.value.status_code == 413


def test_hls_only_is_unsupported() -> None:
    with pytest.raises(AppError) as exc:
        build_extracted(
            {"title": "Só stream", "formats": [HLS, VIDEO_ONLY]},
            provider="x",
            page_url="https://x.com/maria/status/1",
            max_file_bytes=10_000,
        )
    assert exc.value.code == "unsupported_content"


def test_caps_playlist_length() -> None:
    entries = [
        {
            "id": str(index),
            "ext": "jpg",
            "url": f"https://cdn.example/{index}.jpg",
            "protocol": "https",
        }
        for index in range(30)
    ]
    media = build_extracted(
        {"_type": "playlist", "entries": entries},
        provider="instagram",
        page_url="https://www.instagram.com/p/AbC123/",
        max_file_bytes=10_000,
        max_items=20,
    )
    assert len(media.items) == 20
