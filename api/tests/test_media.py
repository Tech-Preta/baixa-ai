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
        ("mp3", "MP3"),
    ]
    assert media.items[-1].delivery == "mp3"
    assert media.items[-1].audio_format_id == "hd"
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
    assert all(item.delivery != "mp3" for item in media.items)
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


def _youtube_formats() -> list[dict]:
    def video(format_id: str, height: int, vcodec: str, size: int) -> dict:
        return {
            "format_id": format_id,
            "ext": "mp4",
            "protocol": "https",
            "vcodec": vcodec,
            "acodec": "none",
            "height": height,
            "tbr": height,
            "filesize": size,
            "url": f"https://cdn.example/{format_id}.mp4",
        }

    return [
        {
            "format_id": "18",
            "ext": "mp4",
            "protocol": "https",
            "vcodec": "avc1.4d401e",
            "acodec": "mp4a.40.2",
            "height": 360,
            "tbr": 500,
            "filesize": 800,
            "url": "https://cdn.example/360.mp4",
        },
        video("137", 1080, "avc1.640028", 4_000),
        video("136", 720, "avc1.4d401f", 2_000),
        video("248", 1080, "vp9", 3_000),
        video("400", 1440, "avc1.640032", 8_000),
        {
            "format_id": "140",
            "ext": "m4a",
            "protocol": "https",
            "vcodec": "none",
            "acodec": "mp4a.40.2",
            "abr": 128,
            "filesize": 300,
            "url": "https://cdn.example/audio.m4a",
        },
        {
            "format_id": "251",
            "ext": "webm",
            "protocol": "https",
            "vcodec": "none",
            "acodec": "opus",
            "abr": 160,
            "filesize": 200,
            "url": "https://cdn.example/opus.webm",
        },
        {
            "format_id": "hls",
            "ext": "mp4",
            "protocol": "m3u8_native",
            "vcodec": "avc1",
            "acodec": "mp4a",
            "height": 1080,
            "url": "https://cdn.example/playlist.m3u8",
        },
    ]


def test_youtube_keeps_progressive_and_adds_remux_plus_mp3() -> None:
    media = build_extracted(
        {"title": "Um vídeo", "uploader": "canal", "duration": 30, "formats": _youtube_formats()},
        provider="youtube",
        page_url="https://www.youtube.com/watch?v=abcdefghijk",
        max_file_bytes=2_000_000,
    )
    by_label = {item.label: item for item in media.items}
    assert by_label["Vídeo · 1080p"].delivery == "merge"
    assert by_label["Vídeo · 1080p"].video_format_id == "137"
    assert by_label["Vídeo · 1080p"].audio_format_id == "140"
    assert by_label["Vídeo · 1080p"].ext == "mp4"
    assert by_label["Vídeo · 720p"].video_format_id == "136"
    assert by_label["Vídeo · 360p"].delivery == "direct"
    assert by_label["Vídeo · 360p"].format_id == "18"
    assert by_label["MP3"].delivery == "mp3"
    assert by_label["MP3"].audio_format_id == "251"
    assert by_label["MP3"].ext == "mp3"
    assert all(item.video_format_id != "248" for item in media.items)
    assert all(item.height is None or item.height <= 1080 for item in media.items)
    assert "cdn.example" not in by_label["Vídeo · 1080p"].url


def test_vp9_alone_is_not_reencoded_into_mp4() -> None:
    media = build_extracted(
        {
            "title": "VP9",
            "duration": 10,
            "formats": [
                {
                    "format_id": "18",
                    "ext": "mp4",
                    "protocol": "https",
                    "vcodec": "avc1",
                    "acodec": "mp4a",
                    "height": 360,
                    "filesize": 100,
                    "url": "https://cdn.example/360.mp4",
                },
                {
                    "format_id": "248",
                    "ext": "webm",
                    "protocol": "https",
                    "vcodec": "vp9",
                    "acodec": "none",
                    "height": 1080,
                    "filesize": 100,
                    "url": "https://cdn.example/vp9.webm",
                },
                {
                    "format_id": "251",
                    "ext": "webm",
                    "protocol": "https",
                    "vcodec": "none",
                    "acodec": "opus",
                    "abr": 160,
                    "url": "https://cdn.example/opus.webm",
                },
            ],
        },
        provider="youtube",
        page_url="https://www.youtube.com/watch?v=abcdefghijk",
        max_file_bytes=2_000_000,
    )
    assert [item.label for item in media.items] == ["Vídeo · 360p", "MP3"]
    assert all(item.delivery != "merge" for item in media.items)


def test_youtube_live_and_playlists_are_rejected() -> None:
    page = "https://www.youtube.com/watch?v=abcdefghijk"
    with pytest.raises(AppError) as live:
        build_extracted(
            {"title": "Ao vivo", "is_live": True, "formats": [VIDEO]},
            provider="youtube",
            page_url=page,
            max_file_bytes=10_000,
        )
    assert live.value.message.startswith("Transmissões ao vivo")

    with pytest.raises(AppError) as playlist:
        build_extracted(
            {"_type": "playlist", "entries": [{"title": "um"}]},
            provider="youtube",
            page_url=page,
            max_file_bytes=10_000,
        )
    assert playlist.value.code == "unsupported_content"


def test_long_video_skips_mp3_when_the_estimate_exceeds_the_cap() -> None:
    media = build_extracted(
        {
            "title": "Longo",
            "duration": 10_000,
            "formats": [VIDEO],
        },
        provider="tiktok",
        page_url="https://www.tiktok.com/@maria/video/1",
        max_file_bytes=5_000,
    )
    assert [item.format_id for item in media.items] == ["hd"]


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
