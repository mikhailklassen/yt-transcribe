"""Command-line interface for yt-transcribe."""

import os
import sys
import click
from pathlib import Path
from dotenv import load_dotenv

from yt_transcribe.downloader import download_audio
from yt_transcribe.transcriber import transcribe_audio
from yt_transcribe.report_generator import generate_report
from yt_transcribe.output import save_transcript, save_report

# Load environment variables
load_dotenv()


@click.command()
@click.argument("url", type=str)
@click.option(
    "--output-dir",
    "-o",
    type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
    default=Path.cwd(),
    help="Directory to save output files",
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
def main(url: str, output_dir: Path, model: str, device: str, openai_model: str):
    """Transcribe a YouTube video and generate an AI-powered report.
    
    URL: YouTube video URL to transcribe
    """
    # Check for OpenAI API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        click.echo("Error: OPENAI_API_KEY environment variable not set.", err=True)
        click.echo("Please set it in your .env file or environment.", err=True)
        sys.exit(1)
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    click.echo(f"Downloading audio from: {url}")
    try:
        audio_path = download_audio(url, output_dir)
        click.echo(f"✓ Audio downloaded to: {audio_path}")
    except Exception as e:
        click.echo(f"Error downloading audio: {e}", err=True)
        sys.exit(1)
    
    click.echo(f"Transcribing audio using model: {model}")
    try:
        transcript = transcribe_audio(audio_path, model=model, device=device)
        click.echo("✓ Transcription complete")
        
        # Save transcript
        transcript_path = save_transcript(transcript, output_dir, url)
        click.echo(f"✓ Transcript saved to: {transcript_path}")
    except Exception as e:
        click.echo(f"Error transcribing audio: {e}", err=True)
        sys.exit(1)
    
    click.echo(f"Generating report using {openai_model}...")
    try:
        report = generate_report(transcript, api_key, model=openai_model)
        click.echo("✓ Report generated")
        
        # Save report as Markdown and PDF
        md_path, pdf_path = save_report(report, output_dir, url)
        click.echo(f"✓ Report saved to: {md_path}")
        click.echo(f"✓ Report saved to: {pdf_path}")
    except Exception as e:
        click.echo(f"Error generating report: {e}", err=True)
        sys.exit(1)
    
    click.echo("\n✓ All done!")


if __name__ == "__main__":
    main()

