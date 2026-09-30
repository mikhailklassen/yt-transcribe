# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

yt-transcribe is a CLI tool that downloads YouTube videos, transcribes audio using faster-whisper, and generates AI-powered reports using OpenAI. The main entry point is `ytt`.

## Commands

```bash
# Install dependencies (plain `uv sync` removes the optional WeasyPrint/PDF extra)
uv sync --extra pdf

# Global `ytt` on PATH (editable: runs this checkout's code, no reinstall needed)
uv tool install --editable '.[pdf]'

# Fix YouTube 403 download errors (yt-dlp falls behind YouTube every few months)
uv lock --upgrade-package yt-dlp && uv sync --extra pdf

# Transcribe only (no OpenAI key required)
ytt transcribe <youtube-url>
ytt transcribe <youtube-url> --model large --device cuda --debug

# Transcribe + generate AI summary (requires OpenAI key)
ytt summarize <youtube-url>
ytt summarize <youtube-url> --openai-model gpt-5
ytt summarize <youtube-url> --prompt "custom prompt here"
ytt summarize <youtube-url> --prompt-file prompt.txt
ytt summarize <youtube-url> --pdf

# Generate report from existing transcript
ytt report <path-to-transcript.txt>
ytt report <path-to-transcript.txt> --openai-model gpt-5

# Debug mode (keeps audio in the output folder, verbose logging)
ytt transcribe <url> --debug --keep-audio
ytt summarize <url> --debug --keep-audio

# Run tests (YouTube, Whisper and OpenAI are faked; no network or API key needed)
uv run pytest
```

Tests live in `tests/`. `tests/test_cli.py` drives the CLI end to end via `CliRunner` with the download, transcription and OpenAI calls monkeypatched on `yt_transcribe.cli`. `tests/conftest.py` points `YTT_CONFIG`, `OPENAI_API_KEY` and the working directory at temp values so tests never touch the real config, key or repo. Still smoke-test with a real video after changing download or transcription code.

## Architecture

```
yt_transcribe/
├── cli.py              # Click CLI (transcribe, summarize, report, config), shared option decorators
├── downloader.py       # YouTube audio download via yt-dlp
├── transcriber.py      # Audio transcription via faster-whisper
├── report_generator.py # AI report generation via OpenAI
├── output.py           # File output handling
├── validation.py       # Input validation (URLs, models, API keys)
└── config.py           # YAML config loading (~/.config/yt-transcribe/config.yml)
tests/                  # pytest suite; test_cli.py fakes YouTube/Whisper/OpenAI
```

**Config:** `config.py` loads `config.yml` and maps its keys onto Click's `default_map` in the `cli` group callback, so CLI options override config values. `ytt config` shows the active file.

**CLI structure:** Uses Click command groups with these commands:
- `ytt transcribe URL` - Download and transcribe only (creates transcript.txt)
- `ytt summarize URL` - Transcribe (if needed) + generate AI summary (creates transcript.txt, report.md; report.pdf with --pdf)
- `ytt report FILE` - Generate report from existing transcript file
- `ytt config` - Show the active config file and its settings

**Output organization:** Files saved to `output/YYYY-MM-DD/Video_Title_VIDEOID/` containing transcript.txt, report.md, report.pdf (with --pdf), and yt-transcribe.log. `output.find_output_directory` locates a video's existing folder by ID on any date, so transcripts are reused. Audio is downloaded into a temporary directory. Nothing is written to the current directory unless `-o` points there.

**Help text is the agent interface:** other agents on this machine learn `ytt` from `ytt --help`. The `cli` group docstring documents the workflow, output layout, stdout/stderr split, exit codes, config lookup and requirements; each command's docstring has URL forms and examples. Keep these (and README.md) in sync with any CLI behavior change. Use Click's `\b` marker before blocks that must not be re-wrapped.

**API key:** read with `os.getenv("OPENAI_API_KEY")` after `load_dotenv()`. A real environment variable wins over `.env`; `load_dotenv()` locates `.env` by walking up from `cli.py`, so the repo-root `.env` is found even when the global `ytt` runs from another directory.

**Logging:** console logs go to stderr at WARNING (everything with `--debug`); records from `yt_transcribe.cli` are kept off the console because the CLI reports progress via `click.echo`. The log file is written only in the video's output folder.

## Code Conventions

- Use `pathlib.Path` for all file operations
- Use `logging` module (not print) - logger per module via `logging.getLogger(__name__)`
- Type hints required for all functions
- Docstrings for all public functions
- Validate inputs before processing (see validation.py patterns)

## Documentation Rules

**DO NOT create new markdown files in the project root.** Update existing files instead:
- User-facing changes and usage examples → `README.md` (and the `--help` text in `cli.py`)
- All changes → `CHANGELOG.md`
- Architecture/design and development workflow → `CLAUDE.md`

Use the todo tool for task tracking, not markdown files.

## macOS Development Note

PDF generation requires setting the library path:
```bash
export DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib:$DYLD_FALLBACK_LIBRARY_PATH
```
