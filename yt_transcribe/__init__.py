"""YouTube transcription and report generation tool."""

import logging
import sys
from pathlib import Path

__version__ = "0.1.0"


def setup_logging(output_dir: Path = None, debug: bool = False) -> None:
    """Set up logging for the application.
    
    Args:
        output_dir: Directory to save log file (optional)
        debug: Enable debug-level logging
    """
    level = logging.DEBUG if debug else logging.INFO
    
    # Console handler (user-friendly, INFO and above)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)  # Always INFO on console
    console_formatter = logging.Formatter('%(message)s')
    console_handler.setFormatter(console_formatter)
    
    handlers = [console_handler]
    
    # File handler (detailed, includes DEBUG)
    if output_dir:
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
            log_file = output_dir / 'yt-transcribe.log'
            file_handler = logging.FileHandler(log_file, mode='a')
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

