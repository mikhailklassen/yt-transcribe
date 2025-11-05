"""Download audio from YouTube videos."""

import yt_dlp
from pathlib import Path
import tempfile
import shutil
import os
import subprocess
import json
import logging
import re

logger = logging.getLogger(__name__)


def get_video_metadata(url: str) -> dict[str, str]:
    """Extract video metadata from YouTube URL.
    
    Args:
        url: YouTube video URL
        
    Returns:
        Dictionary with video metadata (title, id, duration, etc.)
    """
    logger.debug(f"Extracting metadata from: {url}")
    
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": False,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            metadata = {
                "title": info.get("title", "Unknown"),
                "id": info.get("id", "unknown"),
                "duration": info.get("duration", 0),
                "uploader": info.get("uploader", "Unknown"),
                "upload_date": info.get("upload_date", ""),
            }
            
            logger.info(f"Video metadata: '{metadata['title']}' by {metadata['uploader']}")
            return metadata
            
    except Exception as e:
        logger.warning(f"Could not extract metadata: {e}")
        # Return minimal metadata
        return {
            "title": "Unknown",
            "id": "unknown",
            "duration": 0,
            "uploader": "Unknown",
            "upload_date": "",
        }


def sanitize_title_for_folder(title: str, max_length: int = 50) -> str:
    """Sanitize video title for use as a folder name.
    
    Args:
        title: Video title
        max_length: Maximum length for folder name
        
    Returns:
        Sanitized folder name
    """
    # Remove or replace invalid characters for folder names
    sanitized = re.sub(r'[<>:"/\\|?*]', '', title)
    # Replace spaces and multiple whitespace with single underscores
    sanitized = re.sub(r'\s+', '_', sanitized)
    # Remove leading/trailing underscores and dots
    sanitized = sanitized.strip('._')
    # Truncate if too long
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length].rstrip('._')
    # If empty after sanitization, use a default
    if not sanitized:
        sanitized = "video"
    
    return sanitized


def verify_ffmpeg() -> tuple[bool, str]:
    """Verify FFmpeg is accessible and working.
    
    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            logger.debug("FFmpeg is accessible")
            return True, "FFmpeg is accessible"
        else:
            return False, f"FFmpeg returned error code {result.returncode}"
    except FileNotFoundError:
        return False, (
            "FFmpeg not found in PATH. Please install:\n"
            "  macOS: brew install ffmpeg\n"
            "  Linux: sudo apt-get install ffmpeg"
        )
    except subprocess.TimeoutExpired:
        return False, "FFmpeg check timed out"
    except Exception as e:
        return False, f"Error checking FFmpeg: {e}"


def validate_audio_file(audio_path: Path) -> tuple[bool, str]:
    """Validate audio file using ffprobe.
    
    Args:
        audio_path: Path to the audio file
    
    Returns:
        Tuple of (valid: bool, message: str)
    """
    if not audio_path.exists():
        return False, "File does not exist"
    
    file_size = audio_path.stat().st_size
    if file_size == 0:
        return False, "File is empty (0 bytes)"
    
    logger.debug(f"Validating audio file: {audio_path} ({file_size} bytes)")
    
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "error",
                "-show_entries", "stream=codec_type,duration",
                "-of", "json",
                str(audio_path)
            ],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode != 0:
            return False, f"ffprobe error: {result.stderr}"
        
        data = json.loads(result.stdout)
        
        if not data.get("streams"):
            return False, "No audio streams found in file"
        
        has_audio = any(
            s.get("codec_type") == "audio" 
            for s in data["streams"]
        )
        
        if not has_audio:
            return False, "File does not contain audio"
        
        logger.debug("Audio file validation successful")
        return True, "Audio file is valid"
        
    except subprocess.TimeoutExpired:
        return False, "ffprobe check timed out"
    except json.JSONDecodeError as e:
        return False, f"Could not parse ffprobe output: {e}"
    except Exception as e:
        return False, f"Validation error: {e}"


def download_audio(url: str, output_dir: Path) -> Path:
    """Download audio from a YouTube URL.
    
    Args:
        url: YouTube video URL
        output_dir: Directory to save the audio file
        
    Returns:
        Path to the downloaded audio file
        
    Raises:
        RuntimeError: If FFmpeg is not available or download/validation fails
    """
    # Verify FFmpeg is available before attempting download
    ffmpeg_ok, ffmpeg_msg = verify_ffmpeg()
    if not ffmpeg_ok:
        logger.error(f"FFmpeg verification failed: {ffmpeg_msg}")
        raise RuntimeError(ffmpeg_msg)
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Create a unique base name without extension
    temp_file = tempfile.NamedTemporaryFile(
        delete=False, suffix="", dir=output_dir, prefix="audio_"
    )
    base_path = temp_file.name
    temp_file.close()
    Path(base_path).unlink()  # Remove the empty file, let yt-dlp create it
    
    logger.debug(f"Temporary file base path: {base_path}")
    
    # Find ffmpeg/ffprobe in common locations
    ffmpeg_path = shutil.which("ffmpeg")
    
    # Try Homebrew location if not in PATH
    if not ffmpeg_path:
        homebrew_ffmpeg = "/opt/homebrew/bin/ffmpeg"
        if Path(homebrew_ffmpeg).exists():
            ffmpeg_path = homebrew_ffmpeg
            logger.debug(f"Using Homebrew FFmpeg: {ffmpeg_path}")
    
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": base_path + ".%(ext)s",  # Let yt-dlp add the extension
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
        "quiet": False,  # Changed: Allow errors to surface
        "no_warnings": False,  # Changed: Show warnings
    }
    
    # Set ffmpeg paths if found
    if ffmpeg_path:
        ydl_opts["ffmpeg_location"] = str(Path(ffmpeg_path).parent)
        logger.debug(f"Set ffmpeg_location to: {Path(ffmpeg_path).parent}")
    
    # Download the audio
    logger.info(f"Starting download from: {url}")
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except Exception as e:
        logger.error(f"yt-dlp download failed: {e}")
        raise RuntimeError(f"Failed to download audio: {e}")
    
    # Find the downloaded file (should be .mp3 after postprocessing)
    audio_path = Path(base_path + ".mp3")
    
    # Check if file exists and has content
    if not audio_path.exists():
        # Try to find any file with the base name
        possible_files = list(output_dir.glob(f"{Path(base_path).name}.*"))
        if possible_files:
            audio_path = possible_files[0]
            logger.debug(f"Found alternative file: {audio_path}")
        else:
            logger.error(f"No downloaded files found for base path: {base_path}")
            raise RuntimeError(
                f"Failed to download audio from {url}\n"
                "No output files were created. Check your internet connection."
            )
    
    # Validate the downloaded file
    logger.debug(f"Validating downloaded file: {audio_path}")
    valid, msg = validate_audio_file(audio_path)
    if not valid:
        logger.error(f"Audio validation failed: {msg}")
        audio_path.unlink()  # Clean up bad file
        raise RuntimeError(
            f"Downloaded file is invalid: {msg}\n"
            "This usually indicates an FFmpeg post-processing error.\n"
            "On macOS, try: export DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib\n"
            "Or add to your ~/.zshrc for permanent fix."
        )
    
    logger.info(f"Successfully downloaded and validated: {audio_path}")
    return audio_path

