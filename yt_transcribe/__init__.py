"""YouTube transcription and report generation tool."""

import logging
import sys
from pathlib import Path

__version__ = "0.1.0"


def _not_from_cli(record: logging.LogRecord) -> bool:
    """Console filter: the CLI reports to the user itself via click.echo."""
    return not record.name.startswith("yt_transcribe.cli")


def setup_logging(output_dir: Path | None = None, debug: bool = False) -> None:
    """Set up logging for the application.
    
    Console output goes to stderr and shows warnings and errors only (everything
    with debug), so it doesn't repeat the CLI's own progress messages. The log
    file, when output_dir is given, records everything at INFO (DEBUG with debug).
    
    Args:
        output_dir: Directory to save log file (optional; no file if None)
        debug: Enable debug-level logging
    """
    level = logging.DEBUG if debug else logging.INFO
    
    # Console handler (warnings and errors, or everything in debug mode)
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(logging.DEBUG if debug else logging.WARNING)
    console_handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
    if not debug:
        console_handler.addFilter(_not_from_cli)
    
    handlers: list[logging.Handler] = [console_handler]
    
    # File handler (detailed)
    if output_dir:
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
            log_file = output_dir / 'yt-transcribe.log'
            file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
            file_handler.setLevel(logging.DEBUG)
            file_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            file_handler.setFormatter(file_formatter)
            handlers.append(file_handler)
        except Exception as e:
            # If we can't create log file, continue without it
            print(f"Warning: Could not create log file: {e}", file=sys.stderr)
    
    # Configure root logger
    logging.basicConfig(
        level=level,
        handlers=handlers,
        force=True  # Override any existing configuration
    )
    
    # Third-party HTTP request logs are noise outside debug mode
    for noisy in ("httpx", "httpcore", "huggingface_hub", "faster_whisper"):
        logging.getLogger(noisy).setLevel(logging.DEBUG if debug else logging.WARNING)
