import tempfile
from pathlib import Path

import pytest

from app.errors import AppError
from app.media import MediaItem
from app.transcode import mp3_command, prepare_local_media, remux_command


def _item(**overrides: object) -> MediaItem:
    data: dict[str, object] = {
        "index": 0,
        "format_id": "mp3",
        "type": "audio",
        "ext": "mp3",
        "label": "MP3",
        "height": None,
        "filesize": None,
        "url": "",
        "headers": {},
        "delivery": "mp3",
        "video_format_id": None,
        "audio_format_id": "140",
    }
    data.update(overrides)
    return MediaItem(**data)  # type: ignore[arg-type]


def test_mp3_command_reencodes_audio_on_one_thread() -> None:
    command = mp3_command(Path("in.m4a"), Path("out.mp3"))
    assert command[0] == "ffmpeg"
    assert command[command.index("-threads") + 1] == "1"
    assert "libmp3lame" in command
    assert "192k" in command
    assert "-vn" in command
    assert "libx264" not in command


def test_remux_command_copies_streams_without_reencoding() -> None:
    command = remux_command(Path("video.mp4"), Path("audio.m4a"), Path("out.mp4"))
    assert command[command.index("-c") + 1] == "copy"
    assert "libx264" not in command
    assert "libmp3lame" not in command
    assert "-b:v" not in command
    assert "+faststart" in command


def test_mp3_path_writes_a_file_and_cleans_the_temp_dir(monkeypatch: pytest.MonkeyPatch) -> None:
    created: list[str] = []
    real_mkdtemp = tempfile.mkdtemp

    def tracking_mkdtemp(*args: object, **kwargs: object) -> str:
        path = real_mkdtemp(prefix="baixa-test-")
        created.append(path)
        return path

    monkeypatch.setattr("app.transcode.tempfile.mkdtemp", tracking_mkdtemp)

    def fake_download(
        url: str,
        format_id: str,
        dest_dir: Path,
        timeout: float,
        max_bytes: int,
    ) -> Path:
        assert url.endswith("abcdefghijk")
        assert format_id == "140"
        dest_dir.mkdir(parents=True, exist_ok=True)
        source = dest_dir / "source.m4a"
        source.write_bytes(b"audio")
        return source

    def fake_run(command: list[str], timeout: float) -> None:
        assert command == mp3_command(Path(command[command.index("-i") + 1]), Path(command[-1]))
        Path(command[-1]).write_bytes(b"mp3data")

    local = prepare_local_media(
        _item(),
        "https://www.youtube.com/watch?v=abcdefghijk",
        30,
        1000,
        download=fake_download,
        run=fake_run,
    )
    assert local.path.read_bytes() == b"mp3data"
    assert created and Path(created[0]).exists()
    local.cleanup()
    assert not Path(created[0]).exists()


def test_merge_uses_remux_and_oversized_output_is_removed(monkeypatch: pytest.MonkeyPatch) -> None:
    created: list[str] = []
    real_mkdtemp = tempfile.mkdtemp

    def tracking_mkdtemp(*args: object, **kwargs: object) -> str:
        path = real_mkdtemp(prefix="baixa-test-")
        created.append(path)
        return path

    monkeypatch.setattr("app.transcode.tempfile.mkdtemp", tracking_mkdtemp)
    seen: list[str] = []

    def fake_download(
        url: str,
        format_id: str,
        dest_dir: Path,
        timeout: float,
        max_bytes: int,
    ) -> Path:
        seen.append(format_id)
        dest_dir.mkdir(parents=True, exist_ok=True)
        source = dest_dir / f"{format_id}.mp4"
        source.write_bytes(b"src")
        return source

    def fake_run(command: list[str], timeout: float) -> None:
        assert command[command.index("-c") + 1] == "copy"
        assert "libx264" not in command
        Path(command[-1]).write_bytes(b"x" * 50)

    with pytest.raises(AppError) as exc:
        prepare_local_media(
            _item(
                format_id="merge-137-140",
                type="video",
                ext="mp4",
                label="Vídeo · 1080p",
                height=1080,
                delivery="merge",
                video_format_id="137",
                audio_format_id="140",
            ),
            "https://www.youtube.com/watch?v=abcdefghijk",
            30,
            10,
            download=fake_download,
            run=fake_run,
        )
    assert exc.value.code == "too_large"
    assert seen == ["137", "140"]
    assert created and not Path(created[0]).exists()
