"""Command-line interface for yt-transcribe."""

import os
import sys
import shutil
import tempfile
import click
import logging
from pathlib import Path
from typing import Callable, NoReturn
from dotenv import load_dotenv

from yt_transcribe import setup_logging, __version__
from yt_transcribe.downloader import download_audio, get_video_metadata
from yt_transcribe.transcriber import transcribe_audio
from yt_transcribe.report_generator import generate_report
from yt_transcribe.output import (
    save_transcript,
    save_report,
    create_output_directory,
    check_pdf_support,
)
from yt_transcribe.validation import validate_all_inputs, validate_openai_model, validate_api_key
from yt_transcribe.config import default_config_path, load_config, build_default_map

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# File extensions that suggest a --prompt value was meant to be a file
PROMPT_FILE_SUFFIXES = {".txt", ".md", ".prompt"}


# ============================================================================
# Shared Options
# ============================================================================

def _default_output_dir() -> Path:
    """Default base output directory, resolved when the command runs."""
    return Path.cwd() / "output"


def output_dir_option(f: Callable) -> Callable:
    """--output-dir option shared by commands that download videos."""
    return click.option(
        "--output-dir",
        "-o",
        type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
        default=_default_output_dir,
        help="Base directory for output files (default: output_dir from config, else ./output)",
    )(f)


def transcription_options(help_suffix: str = "") -> Callable:
    """--model, --device and --keep-audio options, with an optional help suffix."""
    def decorator(f: Callable) -> Callable:
        f = click.option(
            "--keep-audio",
            is_flag=True,
            help=f"Save the downloaded audio as audio.mp3 in the output folder{help_suffix}",
        )(f)
        f = click.option(
            "--device",
            "-d",
            type=click.Choice(["cpu", "cuda"], case_sensitive=False),
            default="cpu",
            show_default=True,
            help=f"Device to use for transcription{help_suffix}",
        )(f)
        f = click.option(
            "--model",
            "-m",
            type=str,
            default="base",
            show_default=True,
            help=f"Whisper model size (tiny, base, small, medium, large){help_suffix}",
        )(f)
        return f
    return decorator


def report_options(f: Callable) -> Callable:
    """--openai-model, --prompt, --prompt-file and --pdf options."""
    f = click.option(
        "--pdf",
        is_flag=True,
        help="Also save the report as PDF (needs the 'pdf' extra)",
    )(f)
    f = click.option(
        "--prompt-file",
        type=click.Path(exists=True, dir_okay=False, path_type=Path),
        default=None,
        help="Read a custom report prompt from this file",
    )(f)
    f = click.option(
        "--prompt",
        type=str,
        default=None,
        help="Custom report prompt text (use --prompt-file for a file). Defaults to the built-in prompt.",
    )(f)
    f = click.option(
        "--openai-model",
        type=str,
        default="gpt-6-luna",
        show_default=True,
        help="OpenAI model to use for report generation",
    )(f)
    return f


def debug_option(f: Callable) -> Callable:
    """--debug option shared by all processing commands."""
    return click.option(
        "--debug",
        is_flag=True,
        help="Enable debug logging",
    )(f)


# ============================================================================
# Helper Functions
# ============================================================================

def _setup_logging(debug: bool, output_dir: Path | None = None) -> None:
    """Configure logging with appropriate level and output location.

    Args:
        debug: Enable debug logging level
        output_dir: Directory to write the log file (None logs to the console only)
    """
    setup_logging(output_dir, debug=debug)

    if debug:
        logger.debug("Debug mode enabled")


def _load_custom_prompt(prompt: str | None, prompt_file: Path | None) -> str | None:
    """Resolve --prompt / --prompt-file into prompt text.

    Args:
        prompt: Prompt text from --prompt
        prompt_file: Path from --prompt-file

    Returns:
        Custom prompt text, or None to use the default prompt

    Raises:
        click.UsageError: If both are given, or --prompt looks like a file path
    """
    if prompt and prompt_file:
        raise click.UsageError("Use either --prompt or --prompt-file, not both.")

    if prompt_file:
        custom_prompt = prompt_file.read_text(encoding="utf-8")
        if not custom_prompt.strip():
            raise click.UsageError(f"Prompt file is empty: {prompt_file}")
        logger.info(f"Using custom prompt from file: {prompt_file}")
        click.echo(f"✓ Using custom prompt from file: {prompt_file}")
        return custom_prompt

    if prompt:
        # Catch file paths passed to --prompt, which would otherwise be sent
        # to the model as the literal prompt text
        if _looks_like_file_path(prompt):
            raise click.UsageError(
                f"--prompt takes the prompt text, but '{prompt}' looks like a file. "
                "Use --prompt-file PATH to read a prompt from a file."
            )
        logger.info(f"Using custom prompt string ({len(prompt)} characters)")
        click.echo("✓ Using custom prompt string")
        return prompt

    return None


def _looks_like_file_path(text: str) -> bool:
    """Guess whether a --prompt value was meant to be a file path."""
    stripped = text.strip()
    if not stripped or any(c.isspace() for c in stripped):
        return False
    if Path(stripped).suffix in PROMPT_FILE_SUFFIXES:
        return True
    try:
        return Path(stripped).is_file()
    except OSError:  # e.g. name too long to be a path
        return False


def _get_video_metadata_and_setup_output(url: str, output_base_dir: Path) -> tuple[Path, str, str]:
    """Get video metadata and find or create the video's output directory.

    Args:
        url: YouTube video URL
        output_base_dir: Base output directory

    Returns:
        Tuple of (output_dir, video_title, uploader)

    Raises:
        RuntimeError: If metadata fetching fails
    """
    click.echo(f"Fetching video metadata from: {url}")
    logger.info(f"Fetching metadata from: {url}")

    metadata = get_video_metadata(url)
    video_title = metadata["title"]
    uploader = metadata["uploader"]
    click.echo(f"✓ Video: '{video_title}' by {uploader}")

    # Output directory: output/YYYY-MM-DD/Video_Title_VIDEOID/ (reused if it exists)
    output_dir = create_output_directory(output_base_dir, video_title, metadata["id"])
    logger.debug(f"Video-specific output directory: {output_dir}")

    return output_dir, video_title, uploader


def _download_and_transcribe(
    url: str,
    output_dir: Path,
    model: str,
    device: str,
    keep_audio: bool
) -> Path:
    """Download audio to a temporary directory and transcribe it to text.

    Args:
        url: YouTube video URL
        output_dir: Directory to save transcript (and audio, with keep_audio)
        model: Whisper model name
        device: Device to use (cpu/cuda)
        keep_audio: Move the audio file into output_dir instead of deleting it

    Returns:
        Path to saved transcript.txt file

    Raises:
        Exception: If download or transcription fails
    """
    # The temp directory is removed on exit, including partial downloads after Ctrl-C
    with tempfile.TemporaryDirectory(prefix="yt-transcribe-") as temp_dir:
        click.echo(f"Downloading audio from: {url}")
        logger.info(f"Downloading audio from: {url}")
        audio_path = download_audio(url, Path(temp_dir))
        click.echo("✓ Audio downloaded")

        # Transcribe audio
        click.echo(f"Transcribing audio using model: {model}")
        logger.info(f"Starting transcription with model: {model}, device: {device}")
        transcript = transcribe_audio(audio_path, model=model, device=device)
        click.echo("✓ Transcription complete")
        logger.info("Transcription complete")

        if keep_audio:
            kept_path = output_dir / f"audio{audio_path.suffix}"
            shutil.move(audio_path, kept_path)
            click.echo(f"✓ Audio saved to: {kept_path}")
            logger.info(f"Kept audio file (--keep-audio): {kept_path}")

    # Save transcript to organized directory
    transcript_path = save_transcript(transcript, output_dir)
    click.echo(f"✓ Transcript saved to: {transcript_path}")
    logger.info(f"Transcript saved to: {transcript_path}")

    return transcript_path


def _generate_and_save_report(
    transcript_path: Path,
    output_dir: Path,
    openai_model: str,
    openai_api_key: str,
    custom_prompt: str | None,
    pdf: bool = False
) -> None:
    """Generate AI report and save as markdown (and optionally PDF).

    Args:
        transcript_path: Path to transcript file
        output_dir: Directory to save reports
        openai_model: OpenAI model to use
        openai_api_key: OpenAI API key
        custom_prompt: Custom prompt text (None for the default prompt)
        pdf: Also save the report as PDF
    """
    # Read the transcript
    logger.info(f"Reading transcript from: {transcript_path}")
    transcript = transcript_path.read_text(encoding='utf-8')

    # Generate report
    click.echo(f"Generating report using {openai_model}...")
    logger.info(f"Generating report with OpenAI model: {openai_model}")

    report = generate_report(transcript, openai_api_key, model=openai_model, prompt=custom_prompt)
    click.echo("✓ Report generated")
    logger.info("Report generated")

    # Save report as Markdown (and PDF if requested) to organized directory
    md_path, pdf_path = save_report(report, output_dir, pdf=pdf)
    click.echo(f"✓ Report saved to: {md_path}")
    if pdf_path:
        click.echo(f"✓ Report saved to: {pdf_path}")


def _exit_with_validation_errors(errors: list[str]) -> NoReturn:
    """Print validation errors and exit with status 1."""
    logger.error(f"Input validation failed: {errors}")
    click.echo("❌ Input validation failed:\n", err=True)
    for error in errors:
        click.echo(f"  • {error}", err=True)
    sys.exit(1)


def _exit_with_error(e: BaseException, debug: bool) -> NoReturn:
    """Report a fatal error (or Ctrl-C) and exit with the matching status."""
    if isinstance(e, KeyboardInterrupt):
        logger.warning("Process interrupted by user")
        click.echo("\n\nInterrupted by user", err=True)
        sys.exit(130)

    logger.error(f"Fatal error: {e}", exc_info=debug)
    click.echo(f"\nError: {e}", err=True)
    if debug:
        click.echo("\nSee log file for full traceback.", err=True)
    sys.exit(1)


# ============================================================================
# CLI Commands
# ============================================================================

@click.group()
@click.option(
    "--config",
    "config_path",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="Path to config file (default: $YTT_CONFIG or ~/.config/yt-transcribe/config.yml)",
)
@click.version_option(__version__, prog_name="yt-transcribe")
@click.pass_context
def cli(ctx: click.Context, config_path: Path | None) -> None:
    """Transcribe YouTube videos and generate AI-powered reports.

    Defaults for --output-dir, --model, --device and --openai-model can be set
    in a YAML config file. Command-line options always take precedence.
    """
    # Console-only logging until a command knows its output directory
    setup_logging()

    if config_path is not None and not config_path.exists():
        raise click.BadParameter(f"File not found: {config_path}", param_hint="--config")
    config_path = config_path or default_config_path()

    try:
        config = load_config(config_path)
    except ValueError as e:
        click.echo(f"❌ {e}", err=True)
        sys.exit(1)

    ctx.obj = {"config_path": config_path, "config": config}
    ctx.default_map = build_default_map(config)


@cli.command(name="config")
@click.pass_context
def config_command(ctx: click.Context) -> None:
    """Show the config file location and the settings loaded from it."""
    config_path = ctx.obj["config_path"]
    config = ctx.obj["config"]

    status = "" if config_path.exists() else " (not found - using built-in defaults)"
    click.echo(f"Config file: {config_path}{status}")
    for key, value in config.items():
        click.echo(f"  {key}: {value}")


@cli.command()
@click.argument("url", type=str)
@output_dir_option
@transcription_options()
@debug_option
def transcribe(
    url: str,
    output_dir: Path,
    model: str,
    device: str,
    keep_audio: bool,
    debug: bool,
) -> None:
    """Download and transcribe YouTube video to text.

    URL: YouTube video URL to transcribe

    This command downloads the audio from a YouTube video and transcribes it
    to text using the Whisper model. The transcript is saved to:
    output/YYYY-MM-DD/Video_Title_VIDEOID/transcript.txt

    If the video was processed before (on any date), its existing folder is
    reused and the transcript is replaced.

    No OpenAI API key is required for this command.
    """
    _setup_logging(debug)

    logger.info(f"Starting yt-transcribe v{__version__}")

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
        _exit_with_validation_errors(errors)

    logger.info("✓ All inputs validated")

    try:
        # Get video metadata and find or create the output directory
        output_dir, video_title, uploader = _get_video_metadata_and_setup_output(url, output_dir)

        # Log to the video-specific output directory from here on
        _setup_logging(debug, output_dir)

        # Download and transcribe
        _download_and_transcribe(url, output_dir, model, device, keep_audio)

        # Success message
        click.echo(f"\n✓ All done! Transcript saved to:")
        click.echo(f"  📁 {output_dir}/")
        click.echo(f"     • transcript.txt")
        logger.info("Processing complete (transcription only)")

    except (KeyboardInterrupt, Exception) as e:
        _exit_with_error(e, debug)


@cli.command()
@click.argument("url", type=str)
@output_dir_option
@transcription_options(" - only used if transcription is needed")
@report_options
@debug_option
def summarize(
    url: str,
    output_dir: Path,
    model: str,
    device: str,
    keep_audio: bool,
    openai_model: str,
    prompt: str | None,
    prompt_file: Path | None,
    pdf: bool,
    debug: bool,
) -> None:
    """Transcribe (if needed) and generate AI summary of YouTube video.

    URL: YouTube video URL to summarize

    If this video already has a transcript (from any date), it is reused.
    Otherwise the video is downloaded and transcribed first. Then an
    AI-powered summary report is generated.

    \b
    Files are saved to: output/YYYY-MM-DD/Video_Title_VIDEOID/
      • transcript.txt (created if not already present)
      • report.md (AI-generated summary)
      • report.pdf (only with --pdf)
      • yt-transcribe.log

    Requires OPENAI_API_KEY environment variable.
    """
    _setup_logging(debug)

    logger.info(f"Starting yt-transcribe v{__version__}")

    # Get API key - use empty string if not set to force validation
    api_key = os.getenv("OPENAI_API_KEY") or ""

    # Validate inputs before any slow work
    logger.info("Validating inputs...")
    all_valid, errors = validate_all_inputs(
        url=url,
        whisper_model=model,
        openai_model=openai_model,
        output_dir=output_dir,
        api_key=api_key
    )
    if pdf:
        pdf_ok, pdf_msg = check_pdf_support()
        if not pdf_ok:
            errors.append(f"PDF: {pdf_msg}")
            all_valid = False
    if not all_valid:
        _exit_with_validation_errors(errors)

    custom_prompt = _load_custom_prompt(prompt, prompt_file)

    logger.info("✓ All inputs validated")

    try:
        # Get video metadata and find or create the output directory
        output_dir, video_title, uploader = _get_video_metadata_and_setup_output(url, output_dir)

        # Log to the video-specific output directory from here on
        _setup_logging(debug, output_dir)

        # Reuse an existing transcript if there is one
        transcript_path = output_dir / "transcript.txt"

        if transcript_path.exists() and transcript_path.stat().st_size > 0:
            click.echo(f"✓ Using existing transcript: {transcript_path}")
            logger.info(f"Found existing transcript: {transcript_path}")
        else:
            click.echo("Transcript not found, starting transcription...")
            logger.info("No existing transcript found, will transcribe")
            transcript_path = _download_and_transcribe(url, output_dir, model, device, keep_audio)

        # Generate report
        _generate_and_save_report(transcript_path, output_dir, openai_model, api_key, custom_prompt, pdf)

        # Success message
        click.echo(f"\n✓ All done! Files saved to:")
        click.echo(f"  📁 {output_dir}/")
        click.echo(f"     • transcript.txt")
        click.echo(f"     • report.md")
        if pdf:
            click.echo(f"     • report.pdf")
        logger.info("Processing complete (summary)")

    except (KeyboardInterrupt, Exception) as e:
        _exit_with_error(e, debug)


@cli.command(name="report")
@click.argument("transcript_file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@report_options
@debug_option
def report_command(
    transcript_file: Path,
    openai_model: str,
    prompt: str | None,
    prompt_file: Path | None,
    pdf: bool,
    debug: bool,
) -> None:
    """Generate a report from an existing transcript file.

    TRANSCRIPT_FILE: Path to the transcript.txt file

    The report is saved next to the transcript file.
    """
    # Get the directory containing the transcript
    output_dir = transcript_file.parent

    # Set up logging in the same directory as the transcript
    _setup_logging(debug, output_dir)

    logger.debug(f"Arguments: transcript_file={transcript_file}, openai_model={openai_model}")
    logger.info(f"Starting yt-transcribe v{__version__}")
    logger.info("Report generation mode")

    # Get API key
    api_key = os.getenv("OPENAI_API_KEY")

    # Validate inputs
    logger.info("Validating inputs...")
    errors = []

    valid, msg = validate_openai_model(openai_model)
    if not valid:
        errors.append(f"OpenAI model: {msg}")

    valid, msg = validate_api_key(api_key)
    if not valid:
        errors.append(f"API key: {msg}")

    if transcript_file.stat().st_size == 0:
        errors.append(f"Transcript file is empty: {transcript_file}")

    if pdf:
        pdf_ok, pdf_msg = check_pdf_support()
        if not pdf_ok:
            errors.append(f"PDF: {pdf_msg}")

    if errors:
        _exit_with_validation_errors(errors)

    custom_prompt = _load_custom_prompt(prompt, prompt_file)

    logger.info("✓ All inputs validated")

    try:
        _generate_and_save_report(transcript_file, output_dir, openai_model, api_key, custom_prompt, pdf)

        click.echo(f"\n✓ All done! Files saved to:")
        click.echo(f"  📁 {output_dir}/")
        click.echo(f"     • report.md")
        if pdf:
            click.echo(f"     • report.pdf")
        logger.info("Report generation complete")

    except (KeyboardInterrupt, Exception) as e:
        _exit_with_error(e, debug)


if __name__ == "__main__":
    cli()
