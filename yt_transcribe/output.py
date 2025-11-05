"""Handle output file generation."""

import re
from pathlib import Path
from datetime import datetime
from weasyprint import HTML
from markdown import markdown


def sanitize_filename(text: str, max_length: int = 100) -> str:
    """Sanitize a string to be used as a filename.
    
    Args:
        text: Text to sanitize
        max_length: Maximum length of the filename
        
    Returns:
        Sanitized filename
    """
    # Remove or replace invalid characters
    text = re.sub(r'[<>:"/\\|?*]', '', text)
    text = re.sub(r'\s+', '_', text)
    text = text.strip('._')
    
    # Truncate if too long
    if len(text) > max_length:
        text = text[:max_length]
    
    return text or "video"


def get_video_title(url: str) -> str:
    """Extract a simple title from URL or use a default.
    
    Args:
        url: YouTube URL
        
    Returns:
        A title string
    """
    # Try to extract video ID
    video_id_match = re.search(r'(?:v=|\/)([0-9A-Za-z_-]{11}).*', url)
    if video_id_match:
        return f"video_{video_id_match.group(1)}"
    return "video"


def save_transcript(transcript: str, output_dir: Path, url: str) -> Path:
    """Save transcript to a text file.
    
    Args:
        transcript: The transcript text
        output_dir: Directory to save the file
        url: Original video URL (for naming)
        
    Returns:
        Path to the saved file
    """
    video_title = get_video_title(url)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{video_title}_{timestamp}_transcript.txt"
    filepath = output_dir / filename
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(transcript)
    
    return filepath


def save_report(report: str, output_dir: Path, url: str) -> tuple[Path, Path]:
    """Save report as both Markdown and PDF.
    
    Args:
        report: The report text (in Markdown format)
        output_dir: Directory to save the files
        url: Original video URL (for naming)
        
    Returns:
        Tuple of (markdown_path, pdf_path)
    """
    video_title = get_video_title(url)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_filename = f"{video_title}_{timestamp}_report"
    
    # Save Markdown
    md_path = output_dir / f"{base_filename}.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(report)
    
    # Convert Markdown to HTML and then to PDF
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
            overflow-x: auto;
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
    pdf_path = output_dir / f"{base_filename}.pdf"
    HTML(string=full_html).write_pdf(pdf_path)
    
    return md_path, pdf_path

