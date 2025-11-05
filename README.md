# yt-transcribe

A command-line tool to transcribe YouTube videos and generate AI-powered reports using OpenAI.

## Features

- Download audio from YouTube videos
- Transcribe audio using faster-whisper
- Generate comprehensive reports with OpenAI (Summary, Key Ideas, Why It Matters)
- Export reports as both Markdown and PDF
- **Input validation** - Validates URLs, model names, and API keys before processing
- **Organized outputs** - Files organized by date and video title
- **Detailed logging** - Debug mode with comprehensive logs per video
- **Error handling** - Clear, actionable error messages

## Installation

### macOS

1. Install system dependencies (required for PDF generation):
   ```bash
   brew install cairo pango gdk-pixbuf libffi ffmpeg
   ```

2. Set library path (add to your `~/.zshrc` or `~/.bash_profile`):
   ```bash
   export DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib:$DYLD_FALLBACK_LIBRARY_PATH
   ```

3. Install Python dependencies using `uv` (or your preferred package manager):
   ```bash
   uv sync
   ```

4. Set up your OpenAI API key:
   ```bash
   echo "OPENAI_API_KEY=your-api-key-here" > .env
   ```
   Or set the `OPENAI_API_KEY` environment variable.

### Linux

1. Install system dependencies:
   ```bash
   # Debian/Ubuntu
   sudo apt-get install libcairo2 libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0 libffi-dev ffmpeg
   
   # Fedora/RHEL
   sudo dnf install cairo pango gdk-pixbuf2 libffi-devel ffmpeg
   ```

2. Install Python dependencies:
   ```bash
   uv sync
   ```

3. Set up your OpenAI API key:
   ```bash
   echo "OPENAI_API_KEY=your-api-key-here" > .env
   ```

## Usage

```bash
ytt <youtube-url>
```

### Options

- `--output-dir`, `-o`: Base directory for output files (default: `./output`)
- `--model`, `-m`: Whisper model size - `tiny`, `base`, `small`, `medium`, `large` (default: `base`)
- `--device`, `-d`: Device to use - `cpu` or `cuda` (default: `cpu`)
- `--openai-model`: OpenAI model to use (default: `gpt-4`)
- `--debug`: Enable debug logging (shows detailed processing info)
- `--keep-audio`: Keep temporary audio file after processing (for debugging)

### Examples

```bash
# Basic usage
ytt https://www.youtube.com/watch?v=VIDEO_ID

# Use a larger model for better accuracy
ytt https://www.youtube.com/watch?v=VIDEO_ID --model large

# Use GPU acceleration (if available)
ytt https://www.youtube.com/watch?v=VIDEO_ID --device cuda

# Specify output directory
ytt https://www.youtube.com/watch?v=VIDEO_ID -o ./reports

# Use a different OpenAI model
ytt https://www.youtube.com/watch?v=VIDEO_ID --openai-model gpt-4-turbo
```

## Output Files

For each video, the tool creates an organized folder structure:

```
output/
└── YYYY-MM-DD/              # Date of processing
    └── Video_Title/         # Sanitized video title
        ├── transcript.txt   # Raw transcription
        ├── report.md        # AI-generated report (Markdown)
        ├── report.pdf       # Report as PDF
        └── yt-transcribe.log # Processing log
```

**Example:**
```
output/
└── 2024-11-05/
    └── The_Apostles_Creed/
        ├── transcript.txt
        ├── report.md
        ├── report.pdf
        └── yt-transcribe.log
```

All files are organized by date and video title for easy navigation.

## Requirements

- Python 3.11+
- FFmpeg (for audio extraction)
- System libraries: Cairo, Pango, GDK-PixBuf, libffi (for PDF generation)
- OpenAI API key

**Note:** Follow the [Installation](#installation) section for your platform to install all dependencies correctly.

## Notes

- The first time you run the tool, faster-whisper will download the model files (this may take a few minutes)
- Larger Whisper models provide better accuracy but are slower
- GPU acceleration (CUDA) requires appropriate hardware and drivers

## Documentation

- **[CHANGELOG.md](CHANGELOG.md)** - Version history and change log
- **[docs/DEVELOPMENT.md](docs/DEVELOPMENT.md)** - Development documentation, architecture, and guidelines
- **[docs/](docs/)** - Additional developer documentation

## Troubleshooting

### macOS: "cannot load library 'libgobject-2.0-0'" Error

If you see this error when running the tool, make sure you've set the library path:

```bash
export DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib:$DYLD_FALLBACK_LIBRARY_PATH
```

Add this to your `~/.zshrc` to make it permanent.

### FFmpeg/FFprobe Not Found

If you see errors about ffmpeg or ffprobe:

```bash
# Verify FFmpeg is installed
which ffmpeg
which ffprobe

# If not found, install with:
brew install ffmpeg  # macOS
# or
sudo apt-get install ffmpeg  # Linux
```

### Fontconfig Warnings

Fontconfig warnings like "No writable cache directories" are harmless and don't affect functionality. They can be safely ignored.

