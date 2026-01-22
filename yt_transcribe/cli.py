"""Command-line interface for yt-transcribe."""

import os
import sys
import click
import logging
from pathlib import Path
from dotenv import load_dotenv

from yt_transcribe import setup_logging
from yt_transcribe.downloader import download_audio, get_video_metadata, sanitize_title_for_folder
from yt_transcribe.transcriber import transcribe_audio
from yt_transcribe.report_generator import generate_report
from yt_transcribe.output import save_transcript, save_report, create_output_directory
from yt_transcribe.validation import validate_all_inputs, validate_openai_model, validate_api_key

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


# ============================================================================
# Helper Functions
# ============================================================================

def _setup_logging(debug: bool, output_dir: Path | None = None) -> None:
    """Configure logging with appropriate level and output location.

    Args:
        debug: Enable debug logging level
        output_dir: Directory to write log file (defaults to current directory)
    """
    log_dir = output_dir if output_dir else Path.cwd()
    setup_logging(log_dir, debug=debug)

    if debug:
        logger.debug("Debug mode enabled")


def _get_video_metadata_and_setup_output(url: str, output_base_dir: Path) -> tuple[Path, str, str]:
    """Get video metadata and create output directory.

    Args:
        url: YouTube video URL
        output_base_dir: Base output directory

    Returns:
        Tuple of (output_dir, video_title, uploader)

    Raises:
        SystemExit: If metadata fetching fails
    """
    click.echo(f"Fetching video metadata from: {url}")
    logger.info(f"Fetching metadata from: {url}")

    try:
        metadata = get_video_metadata(url)
        video_title = metadata["title"]
        uploader = metadata["uploader"]
        click.echo(f"✓ Video: '{video_title}' by {uploader}")
    except Exception as e:
        logger.error(f"Failed to fetch metadata: {e}")
        click.echo(f"Error fetching video metadata: {e}", err=True)
        sys.exit(1)

    # Create output directory structure: output/YYYY-MM-DD/video_title/
    sanitized_title = sanitize_title_for_folder(video_title)
    output_dir = create_output_directory(output_base_dir, sanitized_title)
    logger.debug(f"Video-specific output directory: {output_dir}")

    return output_dir, video_title, uploader


def _download_and_transcribe(
    url: str,
    output_dir: Path,
    model: str,
    device: str,
    keep_audio: bool
) -> Path:
    """Download audio and transcribe to text.

    Args:
        url: YouTube video URL
        output_dir: Directory to save transcript
        model: Whisper model name
        device: Device to use (cpu/cuda)
        keep_audio: Whether to keep the audio file

    Returns:
        Path to saved transcript.txt file

    Raises:
        Exception: If download or transcription fails
    """
    audio_path = None

    try:
        # Download audio to temp directory (not the organized output dir)
        temp_dir = Path.cwd()
        click.echo(f"Downloading audio from: {url}")
        logger.info(f"Downloading audio from: {url}")
        audio_path = download_audio(url, temp_dir)
        click.echo(f"✓ Audio downloaded to: {audio_path}")

        # Transcribe audio
        click.echo(f"Transcribing audio using model: {model}")
        logger.info(f"Starting transcription with model: {model}, device: {device}")
        transcript = transcribe_audio(audio_path, model=model, device=device)
        click.echo("✓ Transcription complete")
        logger.info("Transcription complete")

        # Save transcript to organized directory
        transcript_path = save_transcript(transcript, output_dir)
        click.echo(f"✓ Transcript saved to: {transcript_path}")
        logger.info(f"Transcript saved to: {transcript_path}")

        return transcript_path

    finally:
        # Cleanup temporary audio file unless --keep-audio is specified
        if audio_path and audio_path.exists() and not keep_audio:
            try:
                audio_path.unlink()
                logger.debug(f"Cleaned up temporary file: {audio_path}")
            except Exception as e:
                logger.warning(f"Could not clean up temporary file {audio_path}: {e}")
        elif audio_path and audio_path.exists() and keep_audio:
            logger.info(f"Kept audio file (--keep-audio): {audio_path}")


def _generate_and_save_report(
    transcript_path: Path,
    output_dir: Path,
    openai_model: str,
    openai_api_key: str,
    prompt: str | None
) -> None:
    """Generate AI report and save as markdown and PDF.

    Args:
        transcript_path: Path to transcript file
        output_dir: Directory to save reports
        openai_model: OpenAI model to use
        openai_api_key: OpenAI API key
        prompt: Custom prompt (file path or string)
    """
    # Read the transcript
    logger.info(f"Reading transcript from: {transcript_path}")
    transcript = transcript_path.read_text(encoding='utf-8')

    # Generate report
    click.echo(f"Generating report using {openai_model}...")
    logger.info(f"Generating report with OpenAI model: {openai_model}")

    # Read custom prompt if provided
    custom_prompt = None
    if prompt:
        prompt_path = Path(prompt)
        if prompt_path.exists() and prompt_path.is_file():
            # It's a file path - read from file
            custom_prompt = prompt_path.read_text(encoding='utf-8')
            logger.info(f"Using custom prompt from file: {prompt_path}")
            click.echo(f"✓ Using custom prompt from file: {prompt_path}")
        else:
            # It's a direct string prompt
            custom_prompt = prompt
            logger.info(f"Using custom prompt string ({len(custom_prompt)} characters)")
            click.echo(f"✓ Using custom prompt string")

    report = generate_report(transcript, openai_api_key, model=openai_model, prompt=custom_prompt)
    click.echo("✓ Report generated")
    logger.info("Report generated")

    # Save report as Markdown and PDF to organized directory
    md_path, pdf_path = save_report(report, output_dir)
    click.echo(f"✓ Report saved to: {md_path}")
    click.echo(f"✓ Report saved to: {pdf_path}")
    logger.info(f"Reports saved to: {md_path}, {pdf_path}")


# ============================================================================
# CLI Commands
# ============================================================================

@click.group()
def cli():
    """Transcribe YouTube videos and generate AI-powered reports."""
    pass


@cli.command()
@click.argument("url", type=str)
@click.option(
    "--output-dir",
    "-o",
    type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
    default=Path.cwd() / "output",
    help="Base directory for output files (default: ./output)",
)
@click.option(
    "--model",
    "-m",
    type=str,
    default="base",
    help="Whisper model size (tiny, base, small, medium, large)",
)
@click.option(
    "--device",
    "-d",
    type=click.Choice(["cpu", "cuda"], case_sensitive=False),
    default="cpu",
    help="Device to use for transcription",
)
@click.option(
    "--debug",
    is_flag=True,
    help="Enable debug logging",
)
@click.option(
    "--keep-audio",
    is_flag=True,
    help="Keep temporary audio file after processing",
)
def transcribe(
    url: str,
    output_dir: Path,
    model: str,
    device: str,
    debug: bool,
    keep_audio: bool,
) -> None:
    """Download and transcribe YouTube video to text.

    URL: YouTube video URL to transcribe

    This command downloads the audio from a YouTube video and transcribes it
    to text using the Whisper model. The transcript is saved to:
    output/YYYY-MM-DD/Video_Title/transcript.txt

    No OpenAI API key is required for this command.
    """
    # Set up logging (temporarily to current directory for validation)
    _setup_logging(debug)

    logger.info(f"Starting yt-transcribe v{__import__('yt_transcribe').__version__}")

    # Validate inputs (no OpenAI validation needed for transcribe)
    logger.info("Validating inputs...")
    all_valid, errors = validate_all_inputs(
        url=url,
        whisper_model=model,
        openai_model=None,  # Not needed for transcribe
        output_dir=output_dir,
        api_key=None  # Not needed for transcribe
    )

    if not all_valid:
        logger.error("Input validation failed")
        click.echo("❌ Input validation failed:\n", err=True)
        for error in errors:
            click.echo(f"  • {error}", err=True)
        sys.exit(1)

    logger.info("✓ All inputs validated")

    try:
        # Get video metadata and create output directory
        output_dir, video_title, uploader = _get_video_metadata_and_setup_output(url, output_dir)

        # Reconfigure logging to use the video-specific output directory
        _setup_logging(debug, output_dir)

        # Download and transcribe
        transcript_path = _download_and_transcribe(url, output_dir, model, device, keep_audio)

        # Success message
        click.echo(f"\n✓ All done! Transcript saved to:")
        click.echo(f"  📁 {output_dir}/")
        click.echo(f"     • transcript.txt")
        logger.info("Processing complete (transcription only)")

    except KeyboardInterrupt:
        logger.warning("Process interrupted by user")
        click.echo("\n\nInterrupted by user", err=True)
        sys.exit(130)

    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=debug)
        click.echo(f"\nError: {e}", err=True)
        if debug:
            click.echo("\nSee log file for full traceback.", err=True)
        sys.exit(1)


@cli.command()
@click.argument("url", type=str)
@click.option(
    "--output-dir",
    "-o",
    type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
    default=Path.cwd() / "output",
    help="Base directory for output files (default: ./output)",
)
@click.option(
    "--model",
    "-m",
    type=str,
    default="base",
    help="Whisper model size (tiny, base, small, medium, large) - only used if transcription is needed",
)
@click.option(
    "--device",
    "-d",
    type=click.Choice(["cpu", "cuda"], case_sensitive=False),
    default="cpu",
    help="Device to use for transcription - only used if transcription is needed",
)
@click.option(
    "--keep-audio",
    is_flag=True,
    help="Keep temporary audio file after processing - only used if transcription is needed",
)
@click.option(
    "--openai-model",
    type=str,
    default="gpt-5-mini",
    help="OpenAI model to use for report generation",
)
@click.option(
    "--prompt",
    type=str,
    default=None,
    help="Custom prompt for report generation. Can be a direct string or a path to a file containing the prompt. If not provided, uses the default prompt.",
)
@click.option(
    "--debug",
    is_flag=True,
    help="Enable debug logging",
)
def summarize(
    url: str,
    output_dir: Path,
    model: str,
    device: str,
    keep_audio: bool,
    openai_model: str,
    prompt: str | None,
    debug: bool,
) -> None:
    """Transcribe (if needed) and generate AI summary of YouTube video.

    URL: YouTube video URL to summarize

    This command intelligently checks if a transcript already exists for the video.
    If found, it uses the existing transcript. If not, it downloads and transcribes
    the video first. Then it generates an AI-powered summary report.

    Files are saved to: output/YYYY-MM-DD/Video_Title/
      • transcript.txt (created if not already present)
      • report.md (AI-generated summary)
      • report.pdf (PDF version)
      • yt-transcribe.log

    Requires OPENAI_API_KEY environment variable.
    """
    # Set up logging (temporarily to current directory for validation)
    _setup_logging(debug)

    logger.info(f"Starting yt-transcribe v{__import__('yt_transcribe').__version__}")

    # Get API key - use empty string if not set to force validation
    api_key = os.getenv("OPENAI_API_KEY") or ""

    # Validate inputs
    logger.info("Validating inputs...")
    all_valid, errors = validate_all_inputs(
        url=url,
        whisper_model=model,
        openai_model=openai_model,
        output_dir=output_dir,
        api_key=api_key
    )

    if not all_valid:
        logger.error("Input validation failed")
        click.echo("❌ Input validation failed:\n", err=True)
        for error in errors:
            click.echo(f"  • {error}", err=True)
        sys.exit(1)

    logger.info("✓ All inputs validated")

    try:
        # Get video metadata and create output directory
        output_dir, video_title, uploader = _get_video_metadata_and_setup_output(url, output_dir)

        # Reconfigure logging to use the video-specific output directory
        _setup_logging(debug, output_dir)

        # Check if transcript already exists
        transcript_path = output_dir / "transcript.txt"

        if transcript_path.exists() and transcript_path.stat().st_size > 0:
            click.echo(f"✓ Using existing transcript: {transcript_path}")
            logger.info(f"Found existing transcript: {transcript_path}")
        else:
            click.echo("Transcript not found, starting transcription...")
            logger.info("No existing transcript found, will transcribe")
            transcript_path = _download_and_transcribe(url, output_dir, model, device, keep_audio)
            click.echo(f"✓ Transcription complete: {transcript_path}")

        # Generate report
        _generate_and_save_report(transcript_path, output_dir, openai_model, api_key, prompt)

        # Success message
        click.echo(f"\n✓ All done! Files saved to:")
        click.echo(f"  📁 {output_dir}/")
        click.echo(f"     • transcript.txt")
        click.echo(f"     • report.md")
        click.echo(f"     • report.pdf")
        logger.info("Processing complete (summary)")

    except KeyboardInterrupt:
        logger.warning("Process interrupted by user")
        click.echo("\n\nInterrupted by user", err=True)
        sys.exit(130)

    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=debug)
        click.echo(f"\nError: {e}", err=True)
        if debug:
            click.echo("\nSee log file for full traceback.", err=True)
        sys.exit(1)


@cli.command(name="report")
@click.argument("transcript_file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option(
    "--openai-model",
    type=str,
    default="gpt-5-mini",
    help="OpenAI model to use for report generation",
)
@click.option(
    "--prompt",
    type=str,
    default=None,
    help="Custom prompt for report generation. Can be a direct string or a path to a file containing the prompt. If not provided, uses the default prompt.",
)
@click.option(
    "--debug",
    is_flag=True,
    help="Enable debug logging",
)
def report_command(
    transcript_file: Path,
    openai_model: str,
    prompt: str | None,
    debug: bool,
) -> None:
    """Generate a report from an existing transcript file.

    TRANSCRIPT_FILE: Path to the transcript.txt file
    """
    # Get the directory containing the transcript
    output_dir = transcript_file.parent

    # Set up logging in the same directory as the transcript
    setup_logging(output_dir, debug=debug)

    if debug:
        logger.debug("Debug mode enabled")
        logger.debug(f"Arguments: transcript_file={transcript_file}, "
                    f"openai_model={openai_model}")

    logger.info(f"Starting yt-transcribe v{__import__('yt_transcribe').__version__}")
    logger.info("Report generation mode")

    # Get API key
    api_key = os.getenv("OPENAI_API_KEY")

    # Validate inputs
    logger.info("Validating inputs...")
    errors = []

    # Validate OpenAI model
    valid, msg = validate_openai_model(openai_model)
    if not valid:
        errors.append(f"OpenAI model: {msg}")

    # Validate API key
    valid, msg = validate_api_key(api_key)
    if not valid:
        errors.append(f"API key: {msg}")

    # Validate transcript file
    if not transcript_file.exists():
        errors.append(f"Transcript file does not exist: {transcript_file}")
    elif not transcript_file.is_file():
        errors.append(f"Path is not a file: {transcript_file}")
    elif transcript_file.stat().st_size == 0:
        errors.append(f"Transcript file is empty: {transcript_file}")

    if errors:
        logger.error("Input validation failed")
        click.echo("❌ Input validation failed:\n", err=True)
        for error in errors:
            click.echo(f"  • {error}", err=True)
        sys.exit(1)

    logger.info("✓ All inputs validated")
    click.echo(f"Reading transcript from: {transcript_file}")

    try:
        # Read the transcript
        logger.info(f"Reading transcript from: {transcript_file}")
        transcript = transcript_file.read_text(encoding='utf-8')
        click.echo(f"✓ Transcript loaded ({len(transcript)} characters)")
        logger.info(f"Transcript loaded: {len(transcript)} characters")

        # Generate report
        click.echo(f"Generating report using {openai_model}...")
        logger.info(f"Generating report with OpenAI model: {openai_model}")

        # Read custom prompt if provided
        custom_prompt = None
        if prompt:
            prompt_path = Path(prompt)
            if prompt_path.exists() and prompt_path.is_file():
                # It's a file path - read from file
                custom_prompt = prompt_path.read_text(encoding='utf-8')
                logger.info(f"Using custom prompt from file: {prompt_path}")
                click.echo(f"✓ Using custom prompt from file: {prompt_path}")
            else:
                # It's a direct string prompt
                custom_prompt = prompt
                logger.info(f"Using custom prompt string ({len(custom_prompt)} characters)")
                click.echo(f"✓ Using custom prompt string")

        report = generate_report(transcript, api_key, model=openai_model, prompt=custom_prompt)
        click.echo("✓ Report generated")
        logger.info("Report generated")

        # Save report as Markdown and PDF to the same directory
        md_path, pdf_path = save_report(report, output_dir)
        click.echo(f"✓ Report saved to: {md_path}")
        click.echo(f"✓ Report saved to: {pdf_path}")
        logger.info(f"Reports saved to: {md_path}, {pdf_path}")

        click.echo(f"\n✓ All done! Files saved to:")
        click.echo(f"  📁 {output_dir}/")
        click.echo(f"     • report.md")
        click.echo(f"     • report.pdf")
        logger.info("Report generation complete")

    except KeyboardInterrupt:
        logger.warning("Process interrupted by user")
        click.echo("\n\nInterrupted by user", err=True)
        sys.exit(130)

    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=debug)
        click.echo(f"\nError: {e}", err=True)
        if debug:
            click.echo("\nSee log file for full traceback.", err=True)
        sys.exit(1)


if __name__ == "__main__":
    cli()
