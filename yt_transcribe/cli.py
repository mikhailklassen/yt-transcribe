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


@click.group()
def cli():
    """Transcribe YouTube videos and generate AI-powered reports."""
    pass


@cli.command(name="transcribe")
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
@click.option(
    "--keep-audio",
    is_flag=True,
    help="Keep temporary audio file after processing",
)
@click.option(
    "--transcript-only",
    is_flag=True,
    help="Only transcribe the video, skip report generation (no OpenAI API key required)",
)
def transcribe_command(
    url: str,
    output_dir: Path,
    model: str,
    device: str,
    openai_model: str,
    prompt: str | None,
    debug: bool,
    keep_audio: bool,
    transcript_only: bool,
) -> None:
    """Transcribe a YouTube video and generate an AI-powered report.
    
    URL: YouTube video URL to transcribe
    """
    # Set up logging (temporarily to current directory for validation)
    setup_logging(Path.cwd(), debug=debug)
    
    if debug:
        logger.debug("Debug mode enabled")
        logger.debug(f"Arguments: url={url}, output_dir={output_dir}, model={model}, "
                    f"device={device}, openai_model={openai_model}, keep_audio={keep_audio}, "
                    f"transcript_only={transcript_only}")
    
    logger.info(f"Starting yt-transcribe v{__import__('yt_transcribe').__version__}")
    
    # Get API key (only needed if generating reports)
    api_key = os.getenv("OPENAI_API_KEY") if not transcript_only else None

    # Validate all inputs
    logger.info("Validating inputs...")
    all_valid, errors = validate_all_inputs(
        url=url,
        whisper_model=model,
        openai_model=openai_model if not transcript_only else None,
        output_dir=output_dir,
        api_key=api_key if not transcript_only else None
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

        if transcript_only:
            # Skip report generation
            click.echo(f"\n✓ All done! Transcript saved to:")
            click.echo(f"  📁 {video_output_dir}/")
            click.echo(f"     • transcript.txt")
            logger.info("Processing complete (transcript only)")
        else:
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


# Make the CLI group also work as the original main command for backwards compatibility
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
@click.option(
    "--keep-audio",
    is_flag=True,
    help="Keep temporary audio file after processing",
)
@click.option(
    "--transcript-only",
    is_flag=True,
    help="Only transcribe the video, skip report generation (no OpenAI API key required)",
)
def main(
    url: str,
    output_dir: Path,
    model: str,
    device: str,
    openai_model: str,
    prompt: str | None,
    debug: bool,
    keep_audio: bool,
    transcript_only: bool,
) -> None:
    """Transcribe a YouTube video and generate an AI-powered report.

    URL: YouTube video URL to transcribe

    This is a backwards-compatible entry point. For new usage, consider:
      yt-transcribe transcribe URL [OPTIONS]
      yt-transcribe report TRANSCRIPT_FILE [OPTIONS]
    """
    # Call the transcribe command directly
    transcribe_command(url, output_dir, model, device, openai_model, prompt, debug, keep_audio, transcript_only)


if __name__ == "__main__":
    cli()

