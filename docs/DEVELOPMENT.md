# Development Documentation

This document contains development notes, architecture decisions, and historical context for the yt-transcribe project.

## Architecture Overview

The project is organized into modular components:

```
yt_transcribe/
├── __init__.py           # Package initialization and logging setup
├── cli.py                # Command-line interface (Click)
├── downloader.py         # YouTube audio download (yt-dlp)
├── transcriber.py        # Audio transcription (faster-whisper)
├── report_generator.py   # AI report generation (OpenAI)
├── output.py             # File output handling
└── validation.py         # Input validation
```

## Key Design Decisions

### 1. Modular Architecture
Each component has a single responsibility and can be tested independently. The CLI orchestrates the workflow but doesn't contain business logic.

### 2. Output Organization
Files are organized as `output/YYYY-MM-DD/Video_Title/` for easy navigation and archival. This was chosen over flat structure for better long-term usability.

### 3. Validation First
All inputs are validated before processing begins, providing fast feedback and clear error messages.

### 4. Logging Strategy
- Console: User-friendly messages (INFO level)
- Log files: Detailed debug information per video
- Separation of concerns: User output vs. diagnostic logging

## Historical Issues and Resolutions

### Critical Bug: 0-Byte Audio Downloads

**Problem:** FFmpeg post-processing was failing silently, creating empty audio files.

**Root Causes:**
1. Silent error suppression (`quiet: True` in yt-dlp)
2. No FFmpeg verification before download
3. No audio file validation after download
4. macOS library path issues (`DYLD_FALLBACK_LIBRARY_PATH`)

**Solution:**
1. Added FFmpeg verification before downloads
2. Added audio file validation using ffprobe
3. Removed silent error suppression
4. Added helpful error messages with macOS-specific instructions
5. Documented library path requirement

### Temporary File Cleanup

**Problem:** Audio files were never deleted, filling up disk space.

**Solution:**
1. Added cleanup in `finally` block in CLI
2. Added `--keep-audio` flag for debugging
3. Smart cleanup: delete on success, keep on failure for debugging

### Input Validation

**Problem:** Cryptic errors when users provided invalid inputs.

**Solution:**
1. Created comprehensive validation module
2. Validate URLs, model names, API keys, directories
3. Clear error messages with valid examples
4. Fail fast before any processing

## Testing Strategy

### Current State
- Manual testing with real YouTube videos
- No automated test suite yet

### Future Testing Goals
1. **Unit Tests**
   - Validation module (easiest to test)
   - Output module (file operations)
   - Mock tests for external APIs

2. **Integration Tests**
   - Full pipeline with sample audio
   - Error handling scenarios

3. **CI/CD**
   - GitHub Actions workflow
   - Automated testing on push
   - Linting and type checking

## Known Limitations

1. **No Progress Bars** - Long operations appear frozen
2. **No Retry Logic** - Transient failures require manual retry
3. **No Rate Limiting** - OpenAI API rate limits not handled
4. **Token Limits** - Very long transcripts may exceed API limits
5. **No Batch Processing** - One video at a time only

## Future Enhancements

### High Priority
- [ ] Progress indicators for downloads and transcription
- [ ] OpenAI rate limit handling with retry logic
- [ ] Token counting and transcript chunking
- [ ] Unit test coverage (>50%)

### Medium Priority
- [ ] Batch processing multiple videos
- [ ] Resume capability after failures
- [ ] Additional output formats (JSON, SRT, VTT)
- [ ] Configuration file support

### Nice to Have
- [ ] Web interface
- [ ] Plugin system for custom formatters
- [ ] Database for tracking processed videos
- [ ] Search through transcripts

## Development Guidelines

### Adding New Features

1. **Validation First**: Add input validation for new parameters
2. **Logging**: Add appropriate logging (DEBUG for details, INFO for milestones)
3. **Error Handling**: Use specific exceptions with helpful messages
4. **Documentation**: Update README.md and this file
5. **Type Hints**: Add type annotations for all functions

### Code Style

- Use `pathlib.Path` for file operations
- Type hints for all function signatures
- Docstrings for all public functions
- Specific exceptions over broad `Exception` catches
- Logging over print statements

### Testing Checklist

Before committing:
- [ ] Code runs without errors
- [ ] No linting errors
- [ ] Type hints added
- [ ] Documentation updated
- [ ] Error messages are helpful
- [ ] Logging added for debugging

## Historical Project Review

A comprehensive review was conducted that identified multiple critical issues:

**Critical Issues (All Fixed):**
1. ✅ 0-byte download bug
2. ✅ Temporary file cleanup
3. ✅ Missing logging framework
4. ✅ Poor error messages

**High Priority (Partially Complete):**
1. ✅ Input validation
2. ✅ Better output organization
3. ⏳ Error handling improvements (ongoing)
4. ❌ Unit tests (not started)
5. ❌ Progress indicators (not started)

See `CHANGELOG.md` for detailed history of changes.

## Troubleshooting Development Issues

### macOS FFmpeg Issues

If you encounter FFmpeg errors during development:

```bash
# Verify FFmpeg works
ffmpeg -version
ffprobe -version

# Check library path
echo $DYLD_FALLBACK_LIBRARY_PATH

# Set library path if needed
export DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib:$DYLD_FALLBACK_LIBRARY_PATH
```

### Testing with Debug Mode

Always test with `--debug` flag during development:

```bash
ytt https://www.youtube.com/watch?v=VIDEO_ID --debug --keep-audio
```

This provides:
- Detailed console output
- Comprehensive log files
- Preserved audio files for inspection

### Common Development Patterns

**Adding a new CLI option:**
```python
# 1. Add to cli.py
@click.option("--new-option", default=value, help="Description")

# 2. Add to function signature
def main(..., new_option: Type):

# 3. Add validation in validation.py (if needed)
def validate_new_option(value: Type) -> tuple[bool, str]:
    # validation logic
    
# 4. Use in appropriate module
# 5. Update README.md with new option
```

**Adding logging to a module:**
```python
import logging

logger = logging.getLogger(__name__)

def my_function():
    logger.debug("Detailed debug info")
    logger.info("User-facing milestone")
    logger.warning("Something unusual happened")
    logger.error("Error occurred", exc_info=True)
```

## Performance Considerations

### Current Performance
- Download: Depends on video length and network speed
- Transcription: ~1-2x real-time (base model on CPU)
- Report generation: 10-30 seconds (depends on transcript length)

### Optimization Opportunities
1. Parallel processing for batch operations
2. GPU acceleration for transcription
3. Caching downloaded audio files
4. Streaming transcription for faster feedback

## Security Notes

1. **API Keys**: Never log or print OpenAI API keys
2. **URL Validation**: All URLs validated before passing to yt-dlp
3. **File Paths**: Use pathlib for safe path manipulation
4. **Input Sanitization**: All user inputs validated

## Contributing

When contributing to this project:

1. Read this development documentation
2. Review the CHANGELOG for recent changes
3. Test with multiple YouTube videos
4. Ensure all validation passes
5. Add appropriate logging
6. Update documentation

## Resources

- [faster-whisper documentation](https://github.com/guillaumekln/faster-whisper)
- [yt-dlp documentation](https://github.com/yt-dlp/yt-dlp)
- [OpenAI API documentation](https://platform.openai.com/docs)
- [Click documentation](https://click.palletsprojects.com/)
- [WeasyPrint documentation](https://doc.courtbouillon.org/weasyprint/)

