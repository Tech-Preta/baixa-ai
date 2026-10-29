from app.ytdlp_runner import run_ytdlp


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
