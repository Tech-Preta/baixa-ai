from pathlib import Path

import pytest

from app.errors import AppError
from app.ytdlp_runner import download_format, run_ytdlp


def test_extractor_is_pinned_to_public_metadata_only(monkeypatch) -> None:
    captured: dict = {}

    class FakeYoutubeDL:
        def __init__(self, opts: dict) -> None:
            captured.update(opts)

        def __enter__(self) -> "FakeYoutubeDL":
            return self

        def __exit__(self, *args: object) -> bool:
            return False

        def extract_info(self, url: str, download: bool = False) -> dict:
            assert download is False
            assert url == "https://www.instagram.com/reel/AbC123/"
            return {
                "title": "t",
                "ext": "mp4",
                "protocol": "https",
                "url": "https://cdn.example/v.mp4",
            }

    monkeypatch.setattr("app.ytdlp_runner.yt_dlp.YoutubeDL", FakeYoutubeDL)
    info = run_ytdlp("https://www.instagram.com/reel/AbC123/", 10)
    assert info["title"] == "t"
    assert captured["cookiefile"] is None
    assert captured["username"] is None
    assert captured["password"] is None
    assert captured["skip_download"] is True
    assert captured["cachedir"] is False
    assert captured["noplaylist"] is False


def test_youtube_lookup_stays_a_single_video_without_cookies(monkeypatch) -> None:
    captured: dict = {}

    class FakeYoutubeDL:
        def __init__(self, opts: dict) -> None:
            captured.update(opts)

        def __enter__(self) -> "FakeYoutubeDL":
            return self

        def __exit__(self, *args: object) -> bool:
            return False

        def extract_info(self, url: str, download: bool = False) -> dict:
            assert download is False
            return {"title": "vídeo", "id": "abcdefghijk"}

    monkeypatch.setattr("app.ytdlp_runner.yt_dlp.YoutubeDL", FakeYoutubeDL)

    info = run_ytdlp("https://www.youtube.com/watch?v=abcdefghijk", 10)
    assert info["id"] == "abcdefghijk"
    assert captured["noplaylist"] is True
    assert captured["cookiefile"] is None
    assert captured["username"] is None
    assert captured["password"] is None


def test_download_format_requests_one_id_and_rejects_selectors(tmp_path: Path, monkeypatch) -> None:
    captured: dict = {}

    class FakeYoutubeDL:
        def __init__(self, opts: dict) -> None:
            captured.update(opts)

        def __enter__(self) -> "FakeYoutubeDL":
            return self

        def __exit__(self, *args: object) -> bool:
            return False

        def download(self, urls: list[str]) -> None:
            assert urls == ["https://www.youtube.com/watch?v=abcdefghijk"]
            Path(str(captured["outtmpl"]).replace("%(ext)s", "m4a")).write_bytes(b"audio")

    monkeypatch.setattr("app.ytdlp_runner.yt_dlp.YoutubeDL", FakeYoutubeDL)
    downloaded = download_format(
        "https://www.youtube.com/watch?v=abcdefghijk",
        "140",
        tmp_path,
        15,
        1000,
    )
    assert downloaded.read_bytes() == b"audio"
    assert captured["format"] == "140"
    assert captured["max_filesize"] == 1000
    assert captured["noplaylist"] is True
    assert captured["skip_download"] is False
    assert captured["cookiefile"] is None

    with pytest.raises(AppError) as exc:
        download_format("https://www.youtube.com/watch?v=abcdefghijk", "bv*+ba", tmp_path, 15, 1000)
    assert exc.value.code == "invalid_token"
