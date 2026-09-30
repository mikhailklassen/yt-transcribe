"""End-to-end CLI tests with YouTube, Whisper and OpenAI faked out."""

from pathlib import Path

import pytest
from click.testing import CliRunner, Result

from yt_transcribe import cli as cli_module
from yt_transcribe.cli import cli

URL = "https://www.youtube.com/watch?v=o0DtxUJ6rAc"
VIDEO_ID = "o0DtxUJ6rAc"


class FakeServices:
    """Records calls to the faked download/transcribe/report functions."""

    def __init__(self) -> None:
        self.metadata = {"title": "Bodybuilding for the Mind", "id": VIDEO_ID, "uploader": "Someone"}
        self.metadata_error: Exception | None = None
        self.download_dirs: list[Path] = []
        self.transcribe_calls = 0
        self.report_transcripts: list[str] = []
        self.report_prompts: list[str | None] = []

    def get_video_metadata(self, url: str) -> dict:
        if self.metadata_error:
            raise self.metadata_error
        return dict(self.metadata)

    def download_audio(self, url: str, output_dir: Path) -> Path:
        self.download_dirs.append(output_dir)
        audio = output_dir / "audio.mp3"
        audio.write_bytes(b"fake audio")
        return audio

    def transcribe_audio(self, audio_path: Path, model: str, device: str) -> str:
        self.transcribe_calls += 1
        return f"transcript of {self.metadata['id']}"

    def generate_report(self, transcript: str, api_key: str, model: str, prompt: str | None) -> str:
        self.report_transcripts.append(transcript)
        self.report_prompts.append(prompt)
        return f"# Report\n\nBased on: {transcript}"


@pytest.fixture
def services(monkeypatch: pytest.MonkeyPatch) -> FakeServices:
    fake = FakeServices()
    for name in ("get_video_metadata", "download_audio", "transcribe_audio", "generate_report"):
        monkeypatch.setattr(cli_module, name, getattr(fake, name))
    return fake


@pytest.fixture
def out(tmp_path: Path) -> Path:
    return tmp_path / "out"


def run(*args: str) -> Result:
    return CliRunner().invoke(cli, list(args), catch_exceptions=False)


def video_dirs(base: Path) -> list[Path]:
    return sorted(p for p in base.glob("*/*") if p.is_dir())


def test_transcribe_creates_id_named_folder_and_cleans_up_audio(services: FakeServices, out: Path) -> None:
    result = run("transcribe", URL, "-o", str(out))

    assert result.exit_code == 0, result.output
    [folder] = video_dirs(out)
    assert folder.name == f"Bodybuilding_for_the_Mind_{VIDEO_ID}"
    assert (folder / "transcript.txt").read_text() == f"transcript of {VIDEO_ID}"
    assert (folder / "yt-transcribe.log").exists()
    assert not (folder / "audio.mp3").exists()
    assert not services.download_dirs[0].exists(), "temporary download directory should be removed"


def test_transcribe_leaves_nothing_in_working_directory(services: FakeServices, out: Path) -> None:
    run("transcribe", URL, "-o", str(out))
    assert list(Path.cwd().iterdir()) == []


def test_keep_audio_moves_audio_into_output_folder(services: FakeServices, out: Path) -> None:
    result = run("transcribe", URL, "-o", str(out), "--keep-audio")

    assert result.exit_code == 0, result.output
    [folder] = video_dirs(out)
    assert (folder / "audio.mp3").read_bytes() == b"fake audio"


def test_metadata_failure_exits_without_creating_folders(services: FakeServices, out: Path) -> None:
    services.metadata_error = RuntimeError("Could not fetch video metadata: boom")

    result = run("summarize", URL, "-o", str(out))

    assert result.exit_code == 1
    assert "Could not fetch video metadata" in result.output
    assert video_dirs(out) == []
    assert services.report_transcripts == []


def test_summarize_writes_markdown_but_no_pdf_by_default(services: FakeServices, out: Path) -> None:
    result = run("summarize", URL, "-o", str(out))

    assert result.exit_code == 0, result.output
    [folder] = video_dirs(out)
    assert (folder / "report.md").exists()
    assert not (folder / "report.pdf").exists()


def test_summarize_reuses_transcript_from_an_earlier_day(services: FakeServices, out: Path) -> None:
    run("transcribe", URL, "-o", str(out))
    [folder] = video_dirs(out)
    old_folder = out / "2020-01-01" / folder.name
    old_folder.parent.mkdir()
    folder.rename(old_folder)

    result = run("summarize", URL, "-o", str(out))

    assert result.exit_code == 0, result.output
    assert services.transcribe_calls == 1, "transcript should be reused, not re-transcribed"
    assert (old_folder / "report.md").exists()


def test_videos_with_same_title_do_not_share_transcripts(services: FakeServices, out: Path) -> None:
    run("summarize", URL, "-o", str(out))
    services.metadata["id"] = "ZZZZZZZZZZZ"
    run("summarize", "https://youtu.be/ZZZZZZZZZZZ", "-o", str(out))

    assert len(video_dirs(out)) == 2
    assert services.transcribe_calls == 2
    assert services.report_transcripts == [f"transcript of {VIDEO_ID}", "transcript of ZZZZZZZZZZZ"]


def test_prompt_and_prompt_file_are_mutually_exclusive(services: FakeServices, out: Path, tmp_path: Path) -> None:
    prompt_file = tmp_path / "prompt.txt"
    prompt_file.write_text("from file")

    result = run("summarize", URL, "-o", str(out), "--prompt", "text", "--prompt-file", str(prompt_file))

    assert result.exit_code == 2
    assert "not both" in result.output


@pytest.mark.parametrize("value", ["promtp.txt", "notes.md"])
def test_prompt_that_looks_like_a_file_is_rejected(services: FakeServices, out: Path, value: str) -> None:
    result = run("summarize", URL, "-o", str(out), "--prompt", value)

    assert result.exit_code == 2
    assert "--prompt-file" in result.output
    assert services.transcribe_calls == 0, "should fail before any slow work"


def test_prompt_file_contents_are_used(services: FakeServices, out: Path, tmp_path: Path) -> None:
    prompt_file = tmp_path / "prompt.txt"
    prompt_file.write_text("Summarize in one line.")

    result = run("summarize", URL, "-o", str(out), "--prompt-file", str(prompt_file))

    assert result.exit_code == 0, result.output
    assert services.report_prompts == ["Summarize in one line."]


def test_prompt_text_is_used(services: FakeServices, out: Path) -> None:
    run("summarize", URL, "-o", str(out), "--prompt", "Focus on key takeaways")
    assert services.report_prompts == ["Focus on key takeaways"]


def test_report_command_writes_next_to_transcript(services: FakeServices, tmp_path: Path) -> None:
    transcript = tmp_path / "somewhere" / "transcript.txt"
    transcript.parent.mkdir()
    transcript.write_text("existing transcript")

    result = run("report", str(transcript))

    assert result.exit_code == 0, result.output
    assert (transcript.parent / "report.md").read_text().endswith("existing transcript")
    assert not (transcript.parent / "report.pdf").exists()


def test_report_command_rejects_empty_transcript(services: FakeServices, tmp_path: Path) -> None:
    transcript = tmp_path / "transcript.txt"
    transcript.write_text("")

    result = run("report", str(transcript))

    assert result.exit_code == 1
    assert "empty" in result.output


def test_missing_api_key_fails_validation(
    services: FakeServices, out: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("OPENAI_API_KEY")
    monkeypatch.setattr(cli_module.os, "getenv", lambda key, default=None: None)

    result = run("summarize", URL, "-o", str(out))

    assert result.exit_code == 1
    assert "API key" in result.output


def test_invalid_url_fails_validation(services: FakeServices, out: Path) -> None:
    result = run("transcribe", "https://example.com/watch?v=o0DtxUJ6rAc", "-o", str(out))

    assert result.exit_code == 1
    assert "Invalid YouTube URL" in result.output


def test_config_sets_output_dir_and_cli_option_overrides_it(
    services: FakeServices, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = tmp_path / "config.yml"
    config.write_text(f"output_dir: {tmp_path / 'from-config'}\n")
    monkeypatch.setenv("YTT_CONFIG", str(config))

    run("transcribe", URL)
    run("transcribe", URL, "-o", str(tmp_path / "from-cli"))

    assert len(video_dirs(tmp_path / "from-config")) == 1
    assert len(video_dirs(tmp_path / "from-cli")) == 1


def test_default_output_dir_is_resolved_at_run_time(services: FakeServices) -> None:
    run("transcribe", URL)
    assert len(video_dirs(Path.cwd() / "output")) == 1


def test_config_command_shows_active_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config = tmp_path / "config.yml"
    config.write_text("openai_model: gpt-5\n")

    result = run("--config", str(config), "config")

    assert result.exit_code == 0
    assert str(config) in result.output
    assert "openai_model: gpt-5" in result.output


def test_version_option() -> None:
    result = run("--version")
    assert result.exit_code == 0
    assert "version" in result.output
