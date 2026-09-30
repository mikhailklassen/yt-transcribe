"""Download audio from YouTube videos."""

import yt_dlp
from pathlib import Path
import subprocess
import json
import logging

logger = logging.getLogger(__name__)


def get_video_metadata(url: str) -> dict[str, str]:
    """Extract video metadata from YouTube URL.
    
    Args:
        url: YouTube video URL
        
    Returns:
        Dictionary with video metadata (title, id, duration, etc.)
        
    Raises:
        RuntimeError: If metadata can't be fetched or has no video ID
    """
    logger.debug(f"Extracting metadata from: {url}")
    
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": False,
    }
    
    # Fail loudly: the video ID names the output folder, so guessing here could
    # mix up transcripts from different videos
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as e:
        raise RuntimeError(f"Could not fetch video metadata: {e}") from e
    
    if not info or not info.get("id"):
        raise RuntimeError("Could not fetch video metadata: no video ID returned")
    
    metadata = {
        "title": info.get("title") or info["id"],
        "id": info["id"],
        "duration": info.get("duration", 0),
        "uploader": info.get("uploader") or "Unknown",
        "upload_date": info.get("upload_date", ""),
    }
    
    logger.info(f"Video metadata: '{metadata['title']}' by {metadata['uploader']} ({metadata['id']})")
    return metadata


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
        output_dir: Directory to save the audio file (normally a temp directory)
        
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
    
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": str(output_dir / "audio.%(ext)s"),
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
        "quiet": False,  # Show download progress and errors
        "no_warnings": False,
    }
    
    # Download the audio
    logger.info(f"Starting download from: {url}")
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except Exception as e:
        logger.error(f"yt-dlp download failed: {e}")
        raise RuntimeError(f"Failed to download audio: {e}") from e
    
    # Find the downloaded file (should be .mp3 after postprocessing)
    audio_path = output_dir / "audio.mp3"
    
    if not audio_path.exists():
        possible_files = [f for f in output_dir.glob("audio.*") if f.suffix != ".part"]
        if not possible_files:
            logger.error(f"No downloaded files found in: {output_dir}")
            raise RuntimeError(
                f"Failed to download audio from {url}\n"
                "No output files were created. Check your internet connection."
            )
        audio_path = possible_files[0]
        logger.debug(f"Found alternative file: {audio_path}")
    
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
