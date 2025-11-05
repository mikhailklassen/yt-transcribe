"""Transcribe audio using faster-whisper."""

from faster_whisper import WhisperModel
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


def transcribe_audio(
    audio_path: Path, model: str = "base", device: str = "cpu"
) -> str:
    """Transcribe audio file using faster-whisper.
    
    Args:
        audio_path: Path to audio file
        model: Whisper model size (tiny, base, small, medium, large)
        device: Device to use (cpu or cuda)
        
    Returns:
        Transcribed text as a string
    """
    logger.info(f"Initializing Whisper model: {model} on {device}")
    
    # Initialize the model
    whisper_model = WhisperModel(model, device=device, compute_type="int8")
    
    logger.info(f"Starting transcription of: {audio_path}")
    
    # Transcribe
    segments, info = whisper_model.transcribe(str(audio_path), beam_size=5)
    
    logger.debug(f"Detected language: {info.language} (probability: {info.language_probability:.2f})")
    
    # Combine all segments into a single transcript
    transcript_parts = []
    segment_count = 0
    for segment in segments:
        transcript_parts.append(segment.text)
        segment_count += 1
    
    logger.debug(f"Processed {segment_count} segments")
    
    transcript = " ".join(transcript_parts)
    
    logger.info(f"Transcription complete: {len(transcript)} characters")
    
    return transcript.strip()

