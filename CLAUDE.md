# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

yt-transcribe is a CLI tool that downloads YouTube videos, transcribes audio using faster-whisper, and generates AI-powered reports using OpenAI. The main entry point is `ytt`.

## Commands

```bash
# Install dependencies
uv sync

# Transcribe only (no OpenAI key required)
ytt transcribe <youtube-url>
ytt transcribe <youtube-url> --model large --device cuda --debug

# Transcribe + generate AI summary (requires OpenAI key)
ytt summarize <youtube-url>
ytt summarize <youtube-url> --openai-model gpt-5
ytt summarize <youtube-url> --prompt "custom prompt here"

# Generate report from existing transcript
ytt report <path-to-transcript.txt>
ytt report <path-to-transcript.txt> --openai-model gpt-5

# Debug mode (preserves audio files, verbose logging)
ytt transcribe <url> --debug --keep-audio
ytt summarize <url> --debug --keep-audio
```

No automated tests exist yet. Manual testing with real YouTube videos is the current approach.

## Architecture

```
yt_transcribe/
├── cli.py              # Click CLI with command groups (transcribe, summarize, report)
├── downloader.py       # YouTube audio download via yt-dlp
├── transcriber.py      # Audio transcription via faster-whisper
├── report_generator.py # AI report generation via OpenAI
├── output.py           # File output handling
└── validation.py       # Input validation (URLs, models, API keys)
```

**CLI structure:** Uses Click command groups with three commands:
- `ytt transcribe URL` - Download and transcribe only (creates transcript.txt)
- `ytt summarize URL` - Transcribe (if needed) + generate AI summary (creates transcript.txt, report.md, report.pdf)
- `ytt report FILE` - Generate report from existing transcript file

**Output organization:** Files saved to `output/YYYY-MM-DD/Video_Title/` containing transcript.txt, report.md, report.pdf, and yt-transcribe.log.

## Code Conventions

- Use `pathlib.Path` for all file operations
- Use `logging` module (not print) - logger per module via `logging.getLogger(__name__)`
- Type hints required for all functions
- Docstrings for all public functions
- Validate inputs before processing (see validation.py patterns)

## Documentation Rules

**DO NOT create new markdown files in the project root.** Update existing files instead:
- User-facing changes → `README.md`
- All changes → `CHANGELOG.md`
- Architecture/design → `docs/DEVELOPMENT.md`
- Usage examples → `docs/USAGE.md`

Use the todo tool for task tracking, not markdown files.

## macOS Development Note

PDF generation requires setting the library path:
```bash
export DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib:$DYLD_FALLBACK_LIBRARY_PATH
```
