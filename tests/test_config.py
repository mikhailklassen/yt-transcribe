"""Tests for config file loading."""

from pathlib import Path

import pytest

from yt_transcribe.config import build_default_map, default_config_path, load_config


def test_default_config_path_prefers_ytt_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("YTT_CONFIG", str(tmp_path / "custom.yml"))
    assert default_config_path() == tmp_path / "custom.yml"


def test_default_config_path_uses_xdg_config_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("YTT_CONFIG")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    assert default_config_path() == tmp_path / "yt-transcribe" / "config.yml"


def test_default_config_path_falls_back_to_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("YTT_CONFIG")
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    assert default_config_path() == tmp_path / ".config" / "yt-transcribe" / "config.yml"


def test_missing_config_file_gives_empty_config(tmp_path: Path) -> None:
    assert load_config(tmp_path / "missing.yml") == {}


def test_empty_config_file_gives_empty_config(tmp_path: Path) -> None:
    path = tmp_path / "config.yml"
    path.write_text("# only comments\n")
    assert load_config(path) == {}


def test_load_config_expands_output_dir_and_skips_unknown_and_null_keys(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    path = tmp_path / "config.yml"
    path.write_text("output_dir: ~/videos\nopenai_model: gpt-5\ndevice:\nbogus: 1\n")

    config = load_config(path)

    assert config == {"output_dir": tmp_path / "videos", "openai_model": "gpt-5"}


@pytest.mark.parametrize("content", ["a: [\n", "- just\n- a list\n"])
def test_load_config_rejects_invalid_files(tmp_path: Path, content: str) -> None:
    path = tmp_path / "config.yml"
    path.write_text(content)
    with pytest.raises(ValueError):
        load_config(path)


def test_build_default_map_maps_keys_to_command_options(tmp_path: Path) -> None:
    default_map = build_default_map(
        {"output_dir": tmp_path, "openai_model": "gpt-5", "whisper_model": "small", "device": "cuda"}
    )
    assert default_map == {
        "transcribe": {"output_dir": tmp_path, "model": "small", "device": "cuda"},
        "summarize": {"output_dir": tmp_path, "openai_model": "gpt-5", "model": "small", "device": "cuda"},
        "report": {"openai_model": "gpt-5"},
    }
