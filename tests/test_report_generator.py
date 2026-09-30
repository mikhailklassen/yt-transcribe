"""Tests for report generation (OpenAI client is faked)."""

from types import SimpleNamespace

import pytest

from yt_transcribe import report_generator
from yt_transcribe.report_generator import check_context_limit, generate_report


class FakeOpenAI:
    """Minimal stand-in for openai.OpenAI that records the request."""

    last_request: dict = {}

    def __init__(self, api_key: str) -> None:
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kwargs) -> SimpleNamespace:
        FakeOpenAI.last_request = kwargs
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="# Report"), finish_reason="stop")],
            usage=SimpleNamespace(prompt_tokens=10, completion_tokens=5, total_tokens=15),
        )


@pytest.fixture
def fake_openai(monkeypatch: pytest.MonkeyPatch) -> type[FakeOpenAI]:
    monkeypatch.setattr(report_generator, "OpenAI", FakeOpenAI)
    return FakeOpenAI


def test_check_context_limit_rejects_oversized_input_for_known_model() -> None:
    with pytest.raises(ValueError, match="too long for gpt-4"):
        check_context_limit("x" * 40_000, "prompt", "gpt-4")


def test_check_context_limit_allows_input_within_limit() -> None:
    check_context_limit("x" * 40_000, "prompt", "gpt-6-luna")


def test_check_context_limit_skips_unknown_models() -> None:
    check_context_limit("x" * 10_000_000, "prompt", "gpt-99-experimental")


def test_generate_report_rejects_empty_transcript(fake_openai: type[FakeOpenAI]) -> None:
    with pytest.raises(ValueError, match="empty"):
        generate_report("   \n", "sk-key")


def test_generate_report_sends_prompt_and_transcript(fake_openai: type[FakeOpenAI]) -> None:
    report = generate_report("hello transcript", "sk-key", model="gpt-5", prompt="custom prompt")

    assert report == "# Report"
    request = fake_openai.last_request
    assert request["model"] == "gpt-5"
    assert request["messages"][0] == {"role": "system", "content": "custom prompt"}
    assert "hello transcript" in request["messages"][1]["content"]


def test_generate_report_uses_default_prompt(fake_openai: type[FakeOpenAI]) -> None:
    generate_report("hello transcript", "sk-key")
    assert fake_openai.last_request["messages"][0]["content"] == report_generator.DEFAULT_PROMPT
