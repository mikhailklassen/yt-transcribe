# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Input validation for YouTube URLs, model names, and API keys
- Organized output structure: `output/YYYY-MM-DD/Video_Title/`
- Video metadata extraction (title, uploader)
- Simple, clean filenames: `transcript.txt`, `report.md`, `report.pdf`
- Per-video log files in output directories
- `--debug` flag for verbose logging
- `--keep-audio` flag to preserve temporary audio files
- Comprehensive logging framework with file and console handlers
- FFmpeg verification before download
- Audio file validation using ffprobe
- Better error messages with troubleshooting hints

### Changed
- Default output directory changed from `./` to `./output/`
- Output files now organized by date and video title
- Removed silent error suppression in yt-dlp
- Improved error handling across all modules

### Fixed
- Critical bug causing 0-byte audio file downloads
- FFmpeg post-processing failures on macOS
- Temporary audio files not being cleaned up
- Missing error context when downloads fail

## [0.1.0] - 2024-11-05

### Added
- Initial release
- YouTube audio download using yt-dlp
- Audio transcription using faster-whisper
- AI-powered report generation using OpenAI GPT-4
- PDF export using WeasyPrint
- Command-line interface with Click
- Support for multiple Whisper models (tiny, base, small, medium, large)
- GPU acceleration support (CUDA)
- OpenAI API key configuration via environment variable
- Basic error handling
- Cross-platform support (macOS, Linux)

### Known Issues
- FFmpeg library path issues on macOS (requires `DYLD_FALLBACK_LIBRARY_PATH`)
- No progress indicators for long operations
- Limited error messages for debugging

## Historical Context

This changelog consolidates information from previous documentation files:
- ACTION_PLAN.md - Development roadmap and issue tracking
- CHANGES_IMPLEMENTED.md - Detailed implementation notes
- FIXES_SUMMARY.md - Quick fix summaries
- IMPLEMENTATION_SUMMARY.md - Feature implementation details
- NEW_FEATURES.md - Feature documentation

All critical fixes identified in the initial review have been implemented.

