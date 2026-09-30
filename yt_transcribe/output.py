"""Handle output file generation."""

import re
from pathlib import Path
from datetime import datetime
from markdown import markdown
import logging

logger = logging.getLogger(__name__)


def sanitize_title_for_folder(title: str, max_length: int = 50) -> str:
    """Sanitize video title for use as a folder name.
    
    Args:
        title: Video title
        max_length: Maximum length for folder name
        
    Returns:
        Sanitized folder name
    """
    # Remove or replace invalid characters for folder names
    sanitized = re.sub(r'[<>:"/\\|?*]', '', title)
    # Replace spaces and multiple whitespace with single underscores
    sanitized = re.sub(r'\s+', '_', sanitized)
    # Remove leading/trailing underscores and dots
    sanitized = sanitized.strip('._')
    # Truncate if too long
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length].rstrip('._')
    # If empty after sanitization, use a default
    if not sanitized:
        sanitized = "video"
    
    return sanitized


def find_output_directory(base_dir: Path, video_id: str) -> Path | None:
    """Find an existing output directory for a video, from any date.
    
    Args:
        base_dir: Base output directory
        video_id: YouTube video ID
        
    Returns:
        Most recent matching directory, or None if the video hasn't been processed
    """
    # Folder names end in "_<video_id>"; IDs are [A-Za-z0-9_-], so no glob escaping needed
    matches = [path for path in base_dir.glob(f"*/*_{video_id}") if path.is_dir()]
    if not matches:
        return None
    # Date folders are YYYY-MM-DD, so the lexically greatest is the most recent
    return max(matches, key=lambda path: path.parent.name)


def create_output_directory(base_dir: Path, video_title: str, video_id: str) -> Path:
    """Return the output directory for a video, creating it if needed.
    
    Reuses the video's existing directory if there is one (so transcripts are
    found again on later days); otherwise creates base_dir/YYYY-MM-DD/Title_ID/.
    
    Args:
        base_dir: Base output directory (e.g., "output")
        video_title: Video title (sanitized here for the folder name)
        video_id: YouTube video ID, which keeps same-titled videos apart
        
    Returns:
        Path to the video-specific output directory
    """
    existing = find_output_directory(base_dir, video_id)
    if existing:
        logger.info(f"Using existing output directory: {existing}")
        return existing
    
    date_str = datetime.now().strftime("%Y-%m-%d")
    folder_name = f"{sanitize_title_for_folder(video_title)}_{video_id}"
    output_path = base_dir / date_str / folder_name
    
    logger.debug(f"Creating output directory: {output_path}")
    output_path.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Output directory: {output_path}")
    return output_path


def check_pdf_support() -> tuple[bool, str]:
    """Check that WeasyPrint (the optional PDF dependency) can be loaded.
    
    Returns:
        Tuple of (available, message)
    """
    try:
        import weasyprint  # noqa: F401
    except ImportError:
        return False, (
            "PDF support is not installed. Install it with:\n"
            "  uv sync --extra pdf              (from the repo)\n"
            "  uv tool install --editable '.[pdf]'   (global ytt)"
        )
    except OSError as e:
        return False, (
            f"PDF libraries could not be loaded: {e}\n"
            "Install Cairo and Pango (see README). On macOS, also set "
            "DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib"
        )
    return True, "PDF support available"


def _refuse_url_fetch(url: str, *args, **kwargs) -> dict:
    """WeasyPrint URL fetcher that blocks every request.
    
    The report is LLM output derived from untrusted video audio, so any HTML it
    contains must not be able to pull local files or remote URLs into the PDF.
    
    Raises:
        ValueError: Always
    """
    raise ValueError(f"Blocked external resource in report: {url}")


def save_transcript(transcript: str, output_dir: Path) -> Path:
    """Save transcript to a text file.
    
    Args:
        transcript: The transcript text
        output_dir: Directory to save the file (already organized by date/video)
        
    Returns:
        Path to the saved file
    """
    filename = "transcript.txt"
    filepath = output_dir / filename
    
    logger.debug(f"Saving transcript to: {filepath}")
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(transcript)
    
    logger.info(f"Transcript saved: {filepath} ({len(transcript)} characters)")
    
    return filepath


def save_report(report: str, output_dir: Path, pdf: bool = False) -> tuple[Path, Path | None]:
    """Save report as Markdown, and optionally as PDF.
    
    Args:
        report: The report text (in Markdown format)
        output_dir: Directory to save the files (already organized by date/video)
        pdf: Also render the report to report.pdf
        
    Returns:
        Tuple of (markdown_path, pdf_path); pdf_path is None when pdf is False
    """
    logger.debug(f"Saving report to: {output_dir}")
    
    # Save Markdown
    md_path = output_dir / "report.md"
    logger.debug(f"Saving Markdown to: {md_path}")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(report)
    
    if not pdf:
        logger.info(f"Report saved: {md_path}")
        return md_path, None
    
    # Imported lazily: WeasyPrint is optional, slow to load and needs system libraries
    from weasyprint import HTML
    
    # Convert Markdown to HTML and then to PDF
    logger.debug("Converting Markdown to HTML")
    html_content = markdown(report, extensions=['fenced_code', 'tables'])
    
    # Create a full HTML document with styling
    full_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            color: #333;
        }}
        h1, h2, h3 {{
            color: #2c3e50;
            margin-top: 1.5em;
        }}
        h1 {{
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
        }}
        h2 {{
            border-bottom: 2px solid #ecf0f1;
            padding-bottom: 8px;
        }}
        code {{
            background-color: #f4f4f4;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Courier New', monospace;
        }}
        pre {{
            background-color: #f4f4f4;
            padding: 15px;
            border-radius: 5px;
        }}
        ul, ol {{
            margin-left: 20px;
        }}
        li {{
            margin-bottom: 0.5em;
        }}
    </style>
</head>
<body>
    {html_content}
</body>
</html>"""
    
    # Save PDF
    pdf_path = output_dir / "report.pdf"
    logger.debug(f"Generating PDF: {pdf_path}")
    HTML(string=full_html, url_fetcher=_refuse_url_fetch).write_pdf(pdf_path)
    
    logger.info(f"Reports saved: {md_path}, {pdf_path}")
    
    return md_path, pdf_path

