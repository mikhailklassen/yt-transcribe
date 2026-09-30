"""Shared fixtures for yt-transcribe tests."""

from pathlib import Path

import pytest

FAKE_API_KEY = "sk-test-" + "x" * 40


@pytest.fixture(autouse=True)
def isolated_environment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep tests away from the user's real config, API key and working directory."""
    monkeypatch.setenv("YTT_CONFIG", str(tmp_path / "no-config.yml"))
    monkeypatch.setenv("OPENAI_API_KEY", FAKE_API_KEY)
    work_dir = tmp_path / "cwd"
    work_dir.mkdir()
    monkeypatch.chdir(work_dir)
