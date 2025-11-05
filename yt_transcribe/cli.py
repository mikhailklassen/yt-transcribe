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
from yt_transcribe.validation import validate_all_inputs

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


@click.command()
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
    "--openai-model",
    type=str,
    default="gpt-4",
    help="OpenAI model to use for report generation",
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
def main(
    url: str,
    output_dir: Path,
    model: str,
    device: str,
    openai_model: str,
    debug: bool,
    keep_audio: bool,
) -> None:
    """Transcribe a YouTube video and generate an AI-powered report.
    
    URL: YouTube video URL to transcribe
    """
    # Set up logging (temporarily to current directory for validation)
    setup_logging(Path.cwd(), debug=debug)
    
    if debug:
        logger.debug("Debug mode enabled")
        logger.debug(f"Arguments: url={url}, output_dir={output_dir}, model={model}, "
                    f"device={device}, openai_model={openai_model}, keep_audio={keep_audio}")
    
    logger.info(f"Starting yt-transcribe v{__import__('yt_transcribe').__version__}")
    
    # Get API key
    api_key = os.getenv("OPENAI_API_KEY")
    
    # Validate all inputs
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
    
    # Get video metadata first
    click.echo(f"Fetching video metadata from: {url}")
    logger.info(f"Fetching metadata from: {url}")
    try:
        metadata = get_video_metadata(url)
        video_title = metadata["title"]
        click.echo(f"✓ Video: '{video_title}' by {metadata['uploader']}")
    except Exception as e:
        logger.error(f"Failed to fetch metadata: {e}")
        click.echo(f"Error fetching video metadata: {e}", err=True)
        sys.exit(1)
    
    # Create output directory structure: output/YYYY-MM-DD/video_title/
    sanitized_title = sanitize_title_for_folder(video_title)
    video_output_dir = create_output_directory(output_dir, sanitized_title)
    
    # Reconfigure logging to use the video-specific output directory
    setup_logging(video_output_dir, debug=debug)
    
    logger.debug(f"Video-specific output directory: {video_output_dir}")
    
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
        transcript_path = save_transcript(transcript, video_output_dir)
        click.echo(f"✓ Transcript saved to: {transcript_path}")
        logger.info(f"Transcript saved to: {transcript_path}")
        
        # Generate report
        click.echo(f"Generating report using {openai_model}...")
        logger.info(f"Generating report with OpenAI model: {openai_model}")
        report = generate_report(transcript, api_key, model=openai_model)
        click.echo("✓ Report generated")
        logger.info("Report generated")
        
        # Save report as Markdown and PDF to organized directory
        md_path, pdf_path = save_report(report, video_output_dir)
        click.echo(f"✓ Report saved to: {md_path}")
        click.echo(f"✓ Report saved to: {pdf_path}")
        logger.info(f"Reports saved to: {md_path}, {pdf_path}")
        
        click.echo(f"\n✓ All done! Files saved to:")
        click.echo(f"  📁 {video_output_dir}/")
        click.echo(f"     • transcript.txt")
        click.echo(f"     • report.md")
        click.echo(f"     • report.pdf")
        logger.info("Processing complete")
        
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


if __name__ == "__main__":
    main()

