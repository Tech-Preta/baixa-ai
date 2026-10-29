import yt_dlp

from app.errors import (
    MSG_BOT,
    MSG_GENERIC,
    MSG_PRIVATE,
    MSG_TIMEOUT,
    MSG_UNSUPPORTED,
    classify_extractor_error,
)


def test_private_and_login_walls_get_a_clear_message() -> None:
    exc = yt_dlp.utils.DownloadError("ERROR: Private video. Sign in to view this content")
    error = classify_extractor_error(exc)
    assert error.code == "private_content"
    assert error.status_code == 422
    assert error.message == MSG_PRIVATE
    assert "Private video" not in error.message


def test_youtube_bot_check_is_not_treated_as_a_private_video() -> None:
    curly = yt_dlp.utils.DownloadError("ERROR: Sign in to confirm you’re not a bot")
    straight = yt_dlp.utils.DownloadError("ERROR: Sign in to confirm you're not a bot")
    for exc in (curly, straight):
        error = classify_extractor_error(exc)
        assert error.code == "upstream_blocked"
        assert error.status_code == 503
        assert error.message == MSG_BOT
        assert "conta" in error.message


def test_instagram_login_wall_is_private() -> None:
    exc = yt_dlp.utils.DownloadError("ERROR: empty media response")
    error = classify_extractor_error(exc)
    assert error.code == "private_content"


def test_unsupported_url_is_not_a_generic_failure() -> None:
    exc = yt_dlp.utils.UnsupportedError("Unsupported URL: https://www.instagram.com/foo")
    error = classify_extractor_error(exc)
    assert error.code == "unsupported_content"
    assert error.status_code == 422
    assert error.message == MSG_UNSUPPORTED


def test_timeout_and_unknown_errors() -> None:
    timeout = classify_extractor_error(TimeoutError())
    assert timeout.code == "timeout"
    assert timeout.status_code == 504
    assert timeout.message == MSG_TIMEOUT

    unknown = classify_extractor_error(RuntimeError("secret internal boom"))
    assert unknown.code == "extraction_failed"
    assert unknown.status_code == 502
    assert unknown.message == MSG_GENERIC
    assert "boom" not in unknown.message


def test_removed_content_is_not_found() -> None:
    exc = yt_dlp.utils.DownloadError("ERROR: Video has been removed")
    error = classify_extractor_error(exc)
    assert error.code == "not_found"
    assert error.status_code == 404
