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
            help=f"Transcription device (cuda needs an NVIDIA GPU){help_suffix}",
        )(f)
        f = click.option(
            "--model",
            "-m",
            type=str,
            default="base",
            show_default=True,
            help=f"Whisper model: tiny, base, small, medium, large, large-v2, large-v3 (larger = more accurate, slower){help_suffix}",
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
        help="Custom instructions for the report, as text (replaces the built-in prompt; use --prompt-file for a file)",
    )(f)
    f = click.option(
        "--openai-model",
        type=str,
        default="gpt-6-luna",
        show_default=True,
        help="OpenAI model for the report (gpt-*, o3/o4-*, chatgpt-*, ft:*)",
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

@click.group(context_settings={"help_option_names": ["-h", "--help"], "max_content_width": 100})
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
    """Transcribe YouTube videos locally and summarize them with OpenAI.

    \b
    WORKFLOW
      ytt transcribe URL    Download the audio and transcribe it on this machine
                            (faster-whisper). No API key needed. Writes transcript.txt.
      ytt summarize URL     Transcribe (skipped if the video already has a transcript),
                            then write an AI report, report.md. Needs OPENAI_API_KEY.
      ytt report FILE       Write report.md from an existing transcript file.
      ytt config            Show which config file is active and what it sets.

    \b
    OUTPUT
      Each video gets one folder, found again on later runs by its video ID:
        <output_dir>/YYYY-MM-DD/<Video_Title>_<VIDEO_ID>/
          transcript.txt      plain-text transcript (single paragraph, no timestamps)
          report.md           Markdown report (summarize, report)
          report.pdf          only with --pdf
          audio.mp3           only with --keep-audio
          yt-transcribe.log   detailed log of every run for this video
      On success, stdout ends with "📁 <folder>/" followed by the files written.
      Nothing is written to the current directory (unless --output-dir points there).

    \b
    FOR SCRIPTS AND AGENTS
      - Progress messages go to stdout; warnings and errors go to stderr.
      - Exit codes: 0 success, 1 invalid input or processing error,
        2 usage error (bad or conflicting options), 130 interrupted.
      - Quote URLs in the shell: they often contain '&' or '?'.
      - Transcription can take minutes for long videos; the first run also
        downloads the Whisper model. Re-running summarize on the same video
        reuses the transcript, so it only makes one OpenAI call.
      - report.md is overwritten on every summarize/report run.
      - To get results, read transcript.txt / report.md in the printed folder.

    \b
    CONFIGURATION
      Defaults for --output-dir, --model, --device and --openai-model come from a
      YAML file: --config PATH, else $YTT_CONFIG, else
      ~/.config/yt-transcribe/config.yml. Command-line options always win.
      Run `ytt config -h` for the supported keys.

    \b
    REQUIREMENTS
      - ffmpeg on PATH.
      - summarize/report: OPENAI_API_KEY in the environment, or in the .env file at
        the root of the yt-transcribe source checkout. The environment wins if both.
      - --pdf: the 'pdf' extra (WeasyPrint with Cairo/Pango system libraries).

    Run `ytt COMMAND --help` for each command's options and examples.
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


@cli.command(name="config", short_help="Show the active config file and its settings.")
@click.pass_context
def config_command(ctx: click.Context) -> None:
    """Show which config file is active and the settings it provides.

    \b
    The file is looked up in this order:
      1. ytt --config PATH COMMAND ...
      2. $YTT_CONFIG
      3. $XDG_CONFIG_HOME/yt-transcribe/config.yml (default ~/.config/yt-transcribe/config.yml)

    \b
    Supported keys (all optional; command-line options override them):
      output_dir: ~/Documents/yt-transcribe   base output directory
      openai_model: gpt-6-luna                model for summarize/report
      whisper_model: base                     tiny|base|small|medium|large|large-v2|large-v3
      device: cpu                             cpu|cuda
    """
    config_path = ctx.obj["config_path"]
    config = ctx.obj["config"]

    status = "" if config_path.exists() else " (not found - using built-in defaults)"
    click.echo(f"Config file: {config_path}{status}")
    for key, value in config.items():
        click.echo(f"  {key}: {value}")


@cli.command(short_help="Download and transcribe a video (no API key needed).")
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
    """Download a YouTube video's audio and transcribe it on this machine.

    Uses faster-whisper locally, so no OpenAI API key is needed.

    \b
    Accepted URL forms (www., m. and music. hosts all work):
      https://www.youtube.com/watch?v=VIDEO_ID      https://youtu.be/VIDEO_ID
      https://www.youtube.com/shorts/VIDEO_ID       .../embed/VIDEO_ID, .../live/VIDEO_ID

    \b
    Writes <output_dir>/YYYY-MM-DD/<Video_Title>_<VIDEO_ID>/transcript.txt.
    If the video already has a folder (from any date), that folder is reused
    and its transcript is replaced.

    \b
    Examples:
      ytt transcribe "https://www.youtube.com/watch?v=VIDEO_ID"
      ytt transcribe "https://youtu.be/VIDEO_ID" --model small
      ytt transcribe "https://youtu.be/VIDEO_ID" -o ~/transcripts --keep-audio
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


@cli.command(short_help="Transcribe if needed, then write an AI report (needs OPENAI_API_KEY).")
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
    """Transcribe a YouTube video (if needed) and write an AI summary report.

    \b
    Steps:
      1. Find the video's folder by video ID (any date), or create
         <output_dir>/YYYY-MM-DD/<Video_Title>_<VIDEO_ID>/.
      2. Reuse transcript.txt if it exists; otherwise download and transcribe.
      3. Send the transcript to OpenAI and save report.md (plus report.pdf with --pdf).

    \b
    The built-in prompt produces a Markdown report with a title, a Summary,
    Key Ideas, and a third section suited to the content (e.g. "Why It Matters"
    or "Implementation Notes"). --prompt / --prompt-file replace it entirely.

    \b
    Requires OPENAI_API_KEY (environment or the source checkout's .env).
    Accepts the same URL forms as `ytt transcribe`.

    \b
    Examples:
      ytt summarize "https://www.youtube.com/watch?v=VIDEO_ID"
      ytt summarize "https://youtu.be/VIDEO_ID" --pdf
      ytt summarize "https://youtu.be/VIDEO_ID" --openai-model gpt-5
      ytt summarize "https://youtu.be/VIDEO_ID" --prompt "List every tool mentioned"
      ytt summarize "https://youtu.be/VIDEO_ID" --prompt-file my_prompt.txt
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


@cli.command(name="report", short_help="Write an AI report from an existing transcript file.")
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
    """Write an AI report from an existing transcript file.

    \b
    TRANSCRIPT_FILE can be any non-empty UTF-8 text file; it doesn't have to
    come from ytt. report.md (plus report.pdf with --pdf) is written next to
    it, replacing any existing report there. Useful for trying another model
    or prompt without re-transcribing.

    \b
    Requires OPENAI_API_KEY (environment or the source checkout's .env).

    \b
    Examples:
      ytt report ~/Documents/yt-transcribe/2026-09-29/Some_Title_VIDEO_ID/transcript.txt
      ytt report transcript.txt --openai-model gpt-5 --pdf
      ytt report transcript.txt --prompt "Summarize in 5 bullet points"
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
