"""Input validation for yt-transcribe."""

import re
from pathlib import Path
from typing import Tuple
from urllib.parse import urlparse, parse_qs
import logging

logger = logging.getLogger(__name__)

# Valid Whisper model sizes
VALID_WHISPER_MODELS = ["tiny", "base", "small", "medium", "large", "large-v2", "large-v3"]

# Valid OpenAI models (common ones)
VALID_OPENAI_MODELS = [
    "gpt-6-luna",
    "gpt-5",
    "gpt-5-mini",
    "gpt-5-nano",
    "gpt-4.1",
    "gpt-4",
    "gpt-4-turbo",
    "gpt-4-turbo-preview",
    "gpt-4-0125-preview",
    "gpt-4-1106-preview",
    "gpt-4o",
    "gpt-4o-mini",
    "gpt-3.5-turbo",
    "gpt-3.5-turbo-16k",
]

YOUTUBE_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com"}
SHORT_LINK_HOSTS = {"youtu.be", "www.youtu.be"}
# Path prefixes that are followed by the video ID, e.g. /shorts/<id>
ID_PATH_PREFIXES = ("shorts", "embed", "v", "live")
VIDEO_ID_RE = re.compile(r"[A-Za-z0-9_-]{11}")

# Model families accepted by --openai-model; the API rejects anything that doesn't exist
OPENAI_MODEL_RE = re.compile(r"^(gpt-|chatgpt-|o\d|ft:)[\w.:-]*$")


def extract_video_id(url: str) -> str | None:
    """Extract the video ID from a YouTube URL.
    
    Accepts youtube.com (www, m, music) watch/shorts/embed/v/live URLs and
    youtu.be short links, with or without a scheme.
    
    Args:
        url: URL to parse
        
    Returns:
        11-character video ID, or None if this isn't a YouTube video URL
    """
    url = url.strip()
    if "://" not in url:
        url = "https://" + url
    
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return None
    
    host = (parsed.hostname or "").lower()
    path_parts = [part for part in parsed.path.split("/") if part]
    
    candidate = None
    if host in SHORT_LINK_HOSTS and path_parts:
        candidate = path_parts[0]
    elif host in YOUTUBE_HOSTS:
        if path_parts == ["watch"]:
            candidate = parse_qs(parsed.query).get("v", [None])[0]
        elif len(path_parts) >= 2 and path_parts[0] in ID_PATH_PREFIXES:
            candidate = path_parts[1]
    
    if candidate and VIDEO_ID_RE.fullmatch(candidate):
        return candidate
    return None


def validate_youtube_url(url: str) -> Tuple[bool, str, str | None]:
    """Validate YouTube URL and extract video ID.
    
    Args:
        url: URL to validate
        
    Returns:
        Tuple of (is_valid, message, video_id)
    """
    if not url or not isinstance(url, str):
        return False, "URL must be a non-empty string", None
    
    video_id = extract_video_id(url)
    if video_id:
        logger.debug(f"Valid YouTube URL: {url}, Video ID: {video_id}")
        return True, "Valid YouTube URL", video_id
    
    return False, (
        "Invalid YouTube URL format. Expected formats:\n"
        "  - https://www.youtube.com/watch?v=VIDEO_ID\n"
        "  - https://youtu.be/VIDEO_ID\n"
        "  - https://www.youtube.com/shorts/VIDEO_ID\n"
        "  - https://www.youtube.com/embed/VIDEO_ID"
    ), None


def validate_whisper_model(model: str) -> Tuple[bool, str]:
    """Validate Whisper model name.
    
    Args:
        model: Model name to validate
        
    Returns:
        Tuple of (is_valid, message)
    """
    if not model or not isinstance(model, str):
        return False, "Model must be a non-empty string"
    
    model_lower = model.lower()
    
    if model_lower in VALID_WHISPER_MODELS:
        logger.debug(f"Valid Whisper model: {model}")
        return True, f"Valid Whisper model: {model}"
    
    return False, (
        f"Invalid Whisper model: '{model}'\n"
        f"Valid models: {', '.join(VALID_WHISPER_MODELS)}\n"
        "See: https://github.com/guillaumekln/faster-whisper#model"
    )


def validate_openai_model(model: str) -> Tuple[bool, str]:
    """Validate OpenAI model name.
    
    Note: This checks against common models but doesn't guarantee the model exists.
    The OpenAI API will return an error if the model is invalid or unavailable.
    
    Args:
        model: Model name to validate
        
    Returns:
        Tuple of (is_valid, message)
    """
    if not model or not isinstance(model, str):
        return False, "Model must be a non-empty string"
    
    # Accept whole model families for forward compatibility (gpt-*, o3, o4-mini, ...)
    if OPENAI_MODEL_RE.match(model):
        logger.debug(f"OpenAI model looks valid: {model}")
        return True, f"OpenAI model: {model}"
    
    return False, (
        f"Invalid OpenAI model: '{model}'\n"
        f"Common models: {', '.join(VALID_OPENAI_MODELS[:3])}\n"
        "Model must start with 'gpt-', 'chatgpt-', 'o<digit>' (e.g. o3, o4-mini) or 'ft:'"
    )


def validate_output_directory(path: Path) -> Tuple[bool, str]:
    """Validate output directory is writable.
    
    Args:
        path: Directory path to validate
        
    Returns:
        Tuple of (is_valid, message)
    """
    try:
        # Try to create the directory
        path.mkdir(parents=True, exist_ok=True)
        
        # Try to write a test file
        test_file = path / ".write_test"
        try:
            test_file.write_text("test")
            test_file.unlink()
            logger.debug(f"Output directory is writable: {path}")
            return True, f"Output directory is writable: {path}"
        except PermissionError:
            return False, f"Permission denied: Cannot write to {path}"
        except Exception as e:
            return False, f"Cannot write to {path}: {e}"
            
    except PermissionError:
        return False, f"Permission denied: Cannot create directory {path}"
    except Exception as e:
        return False, f"Cannot create directory {path}: {e}"


def validate_api_key(api_key: str | None) -> Tuple[bool, str]:
    """Validate OpenAI API key format.
    
    Args:
        api_key: API key to validate
        
    Returns:
        Tuple of (is_valid, message)
    """
    if not api_key:
        return False, (
            "OpenAI API key not set.\n"
            "Set the OPENAI_API_KEY environment variable or add to .env file."
        )
    
    if not isinstance(api_key, str):
        return False, "API key must be a string"
    
    # OpenAI API keys typically start with "sk-"
    if not api_key.startswith("sk-"):
        return False, (
            "Invalid API key format. OpenAI API keys typically start with 'sk-'.\n"
            "Check your OPENAI_API_KEY environment variable."
        )
    
    # Check minimum length (OpenAI keys are usually 40+ characters)
    if len(api_key) < 20:
        return False, "API key appears too short. Check your OPENAI_API_KEY."
    
    logger.debug("API key format appears valid")
    return True, "API key format is valid"


def validate_all_inputs(
    url: str,
    whisper_model: str,
    openai_model: str | None,
    output_dir: Path,
    api_key: str | None
) -> Tuple[bool, list[str]]:
    """Validate all inputs at once.

    Args:
        url: YouTube URL
        whisper_model: Whisper model name
        openai_model: OpenAI model name (None to skip validation)
        output_dir: Output directory path
        api_key: OpenAI API key (None to skip validation)

    Returns:
        Tuple of (all_valid, list_of_error_messages)
    """
    errors = []

    # Validate URL
    valid, msg, _ = validate_youtube_url(url)
    if not valid:
        errors.append(f"URL: {msg}")

    # Validate Whisper model
    valid, msg = validate_whisper_model(whisper_model)
    if not valid:
        errors.append(f"Whisper model: {msg}")

    # Validate OpenAI model (skip if None, e.g., transcript-only mode)
    if openai_model is not None:
        valid, msg = validate_openai_model(openai_model)
        if not valid:
            errors.append(f"OpenAI model: {msg}")

    # Validate output directory
    valid, msg = validate_output_directory(output_dir)
    if not valid:
        errors.append(f"Output directory: {msg}")

    # Validate API key (skip if None, e.g., transcript-only mode)
    if api_key is not None:
        valid, msg = validate_api_key(api_key)
        if not valid:
            errors.append(f"API key: {msg}")

    all_valid = len(errors) == 0

    if all_valid:
        logger.info("All inputs validated successfully")
    else:
        logger.info(f"Input validation failed: {len(errors)} error(s)")

    return all_valid, errors

