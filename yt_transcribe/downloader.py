"""Download audio from YouTube videos."""

import yt_dlp
from pathlib import Path
import tempfile
import shutil
import os


def download_audio(url: str, output_dir: Path) -> Path:
    """Download audio from a YouTube URL.
    
    Args:
        url: YouTube video URL
        output_dir: Directory to save the audio file
        
    Returns:
        Path to the downloaded audio file
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Create a unique base name without extension
    temp_file = tempfile.NamedTemporaryFile(
        delete=False, suffix="", dir=output_dir, prefix="audio_"
    )
    base_path = temp_file.name
    temp_file.close()
    Path(base_path).unlink()  # Remove the empty file, let yt-dlp create it
    
    # Find ffmpeg/ffprobe in common locations
    ffmpeg_path = shutil.which("ffmpeg")
    
    # Try Homebrew location if not in PATH
    if not ffmpeg_path:
        homebrew_ffmpeg = "/opt/homebrew/bin/ffmpeg"
        if Path(homebrew_ffmpeg).exists():
            ffmpeg_path = homebrew_ffmpeg
    
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
        "quiet": True,
        "no_warnings": True,
    }
    
    # Set ffmpeg paths if found
    if ffmpeg_path:
        ydl_opts["ffmpeg_location"] = str(Path(ffmpeg_path).parent)
    
    # Download the audio
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    
    # Find the downloaded file (should be .mp3 after postprocessing)
    audio_path = Path(base_path + ".mp3")
    
    # Check if file exists and has content
    if not audio_path.exists():
        # Try to find any file with the base name
        possible_files = list(output_dir.glob(f"{Path(base_path).name}.*"))
        if possible_files:
            audio_path = possible_files[0]
        else:
            raise RuntimeError(f"Failed to download audio from {url}")
    
    # Verify the file has content
    if audio_path.stat().st_size == 0:
        audio_path.unlink()  # Delete empty file
        raise RuntimeError(f"Downloaded audio file is empty (0 bytes)")
    
    return audio_path

