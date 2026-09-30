"""Tests for input validation."""

from pathlib import Path

import pytest

from yt_transcribe.validation import (
    extract_video_id,
    validate_all_inputs,
    validate_api_key,
    validate_openai_model,
    validate_whisper_model,
)

VIDEO_ID = "o0DtxUJ6rAc"


@pytest.mark.parametrize(
    "url",
    [
        f"https://www.youtube.com/watch?v={VIDEO_ID}",
        f"https://youtube.com/watch?v={VIDEO_ID}&t=42s",
        f"https://www.youtube.com/watch?list=PL123&v={VIDEO_ID}",
        f"https://m.youtube.com/watch?v={VIDEO_ID}",
        f"https://music.youtube.com/watch?v={VIDEO_ID}",
        f"https://www.youtube.com/shorts/{VIDEO_ID}",
        f"https://www.youtube.com/embed/{VIDEO_ID}",
        f"https://www.youtube.com/live/{VIDEO_ID}?si=abc",
        f"https://youtu.be/{VIDEO_ID}",
        f"https://youtu.be/{VIDEO_ID}?t=5",
        f"youtu.be/{VIDEO_ID}",
        f"www.youtube.com/watch?v={VIDEO_ID}",
        f"  https://www.youtube.com/watch?v={VIDEO_ID}  ",
    ],
)
def test_extract_video_id_accepts_youtube_urls(url: str) -> None:
    assert extract_video_id(url) == VIDEO_ID


@pytest.mark.parametrize(
    "url",
    [
        f"https://example.com/x?u=youtube.com/watch?v={VIDEO_ID}",
        f"https://evil.youtube.com.attacker.io/watch?v={VIDEO_ID}",
        f"https://notyoutube.com/watch?v={VIDEO_ID}",
        f"ftp://www.youtube.com/watch?v={VIDEO_ID}",
        "https://www.youtube.com/watch?v=tooshort",
        "https://www.youtube.com/watch",
        "https://www.youtube.com/@somechannel",
        "https://youtu.be/",
        "not a url",
        "",
    ],
)
def test_extract_video_id_rejects_other_urls(url: str) -> None:
    assert extract_video_id(url) is None


@pytest.mark.parametrize(
    "model", ["gpt-6-luna", "gpt-5-mini", "gpt-4.1", "o3", "o4-mini", "chatgpt-4o-latest", "ft:gpt-4o:org::abc"]
)
def test_validate_openai_model_accepts_known_families(model: str) -> None:
    assert validate_openai_model(model)[0]


@pytest.mark.parametrize("model", ["", "claude-x", "gpt 5", "llama3", "oo3"])
def test_validate_openai_model_rejects_others(model: str) -> None:
    assert not validate_openai_model(model)[0]


def test_validate_whisper_model_is_case_insensitive() -> None:
    assert validate_whisper_model("Large-V3")[0]
    assert not validate_whisper_model("huge")[0]


@pytest.mark.parametrize(
    ("key", "valid"),
    [(None, False), ("", False), ("pk-" + "x" * 40, False), ("sk-short", False), ("sk-" + "x" * 40, True)],
)
def test_validate_api_key(key: str | None, valid: bool) -> None:
    assert validate_api_key(key)[0] is valid


def test_validate_all_inputs_collects_every_error(tmp_path: Path) -> None:
    all_valid, errors = validate_all_inputs(
        url="https://example.com",
        whisper_model="huge",
        openai_model="claude-x",
        output_dir=tmp_path / "out",
        api_key="bad",
    )
    assert not all_valid
    assert [e.split(":")[0] for e in errors] == ["URL", "Whisper model", "OpenAI model", "API key"]
