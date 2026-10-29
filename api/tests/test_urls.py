import pytest

from app.errors import MSG_INVALID, MSG_UNSUPPORTED, AppError
from app.urls import validate_media_url

VALID = [
    ("https://instagram.com/p/AbC123/", "instagram"),
    ("https://www.instagram.com/reel/AbC123/?igsh=1", "instagram"),
    ("https://www.instagram.com/reels/AbC123/", "instagram"),
    ("https://www.instagram.com/tv/AbC123/", "instagram"),
    ("https://www.instagram.com/stories/maria/123456789/", "instagram"),
    ("https://www.instagram.com/share/reel/AbC123/", "instagram"),
    ("https://www.tiktok.com/@maria/video/1234567890", "tiktok"),
    ("https://www.tiktok.com/@maria/photo/1234567890", "tiktok"),
    ("https://vm.tiktok.com/ZMAb12cd/", "tiktok"),
    ("https://vt.tiktok.com/ZSAb12cd/", "tiktok"),
    ("https://www.tiktok.com/t/ZTAb12cd/", "tiktok"),
    ("https://x.com/maria/status/1234567890", "x"),
    ("https://twitter.com/maria/status/1234567890", "x"),
    ("https://mobile.twitter.com/maria/status/1234567890", "x"),
    ("https://x.com/i/status/1234567890", "x"),
    ("https://x.com/maria/status/1234567890/video/1", "x"),
]


@pytest.mark.parametrize("url,provider", VALID)
def test_accepts_public_media_links(url: str, provider: str) -> None:
    parsed = validate_media_url(f"  {url}  ")
    assert parsed.provider == provider
    assert parsed.url.startswith("https://")
    assert "#" not in parsed.url


@pytest.mark.parametrize(
    "url",
    [
        "",
        "   ",
        "instagram.com/p/AbC123/",
        "javascript:alert(1)",
        "ftp://instagram.com/p/AbC123/",
        "https://user:pass@instagram.com/p/AbC123/",
        "https://instagram.com:8443/p/AbC123/",
        "https://127.0.0.1/p/AbC123/",
        "https://[::1]/",
        "file:///etc/passwd",
        "https://instagram.com/p/AbC123/\nhttps://evil.test",
    ],
)
def test_rejects_malformed_urls(url: str) -> None:
    with pytest.raises(AppError) as exc:
        validate_media_url(url)
    assert exc.value.code == "invalid_url"
    assert exc.value.status_code == 400
    assert exc.value.message == MSG_INVALID


@pytest.mark.parametrize(
    "url",
    [
        "https://youtube.com/watch?v=abc",
        "https://instagram.com.evil.com/p/AbC123/",
        "https://evilinstagram.com/p/AbC123/",
        "https://notinstagram.com/p/AbC123/",
        "https://tiktok.com.attacker.com/@a/video/1",
        "https://example.com/x.com/maria/status/1",
        "https://t.co/abc",
    ],
)
def test_rejects_hosts_outside_the_allowlist(url: str) -> None:
    with pytest.raises(AppError) as exc:
        validate_media_url(url)
    assert exc.value.code == "unsupported_host"
    assert "Instagram" in exc.value.message


@pytest.mark.parametrize(
    "url",
    [
        "https://www.instagram.com/maria/",
        "https://www.instagram.com/stories/maria/",
        "https://www.tiktok.com/@maria",
        "https://x.com/maria",
        "https://www.instagram.com/",
    ],
)
def test_rejects_profiles_and_story_trays(url: str) -> None:
    with pytest.raises(AppError) as exc:
        validate_media_url(url)
    assert exc.value.code == "unsupported_content"
    assert exc.value.message == MSG_UNSUPPORTED


def test_preserves_case_sensitive_path_and_drops_fragment() -> None:
    parsed = validate_media_url("HTTPS://WWW.INSTAGRAM.COM/reel/AbC123/#frag")
    assert parsed.url == "https://www.instagram.com/reel/AbC123/"
    assert parsed.host == "www.instagram.com"
