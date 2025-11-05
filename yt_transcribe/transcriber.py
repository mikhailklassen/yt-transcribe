"""Transcribe audio using faster-whisper."""

from faster_whisper import WhisperModel
from pathlib import Path


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
    # Initialize the model
    whisper_model = WhisperModel(model, device=device, compute_type="int8")
    
    # Transcribe
    segments, info = whisper_model.transcribe(str(audio_path), beam_size=5)
    
    # Combine all segments into a single transcript
    transcript_parts = []
    for segment in segments:
        transcript_parts.append(segment.text)
    
    transcript = " ".join(transcript_parts)
    
    return transcript.strip()

