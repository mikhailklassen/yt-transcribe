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

### Transcribe a YouTube Video

Download and transcribe a YouTube video to text only (no AI summary):

```bash
ytt transcribe https://youtube.com/watch?v=VIDEO_ID
```

This creates: `output/YYYY-MM-DD/Video_Title/transcript.txt`

**No OpenAI API key required** for transcription.

#### Options

- `--output-dir`, `-o`: Base directory for output files (default: `./output`)
- `--model`, `-m`: Whisper model size - `tiny`, `base`, `small`, `medium`, `large` (default: `base`)
- `--device`, `-d`: Device to use - `cpu` or `cuda` (default: `cpu`)
- `--keep-audio`: Keep temporary audio file after processing (for debugging)
- `--debug`: Enable debug logging (shows detailed processing info)

#### Examples

```bash
# Basic transcription
ytt transcribe https://www.youtube.com/watch?v=VIDEO_ID

# Use a larger model for better accuracy
ytt transcribe https://www.youtube.com/watch?v=VIDEO_ID --model large

# Use GPU acceleration (if available)
ytt transcribe https://www.youtube.com/watch?v=VIDEO_ID --device cuda

# Specify output directory
ytt transcribe https://www.youtube.com/watch?v=VIDEO_ID -o ./reports
```

### Generate AI Summary

Generate an AI-powered summary report (transcribes first if needed):

```bash
ytt summarize https://youtube.com/watch?v=VIDEO_ID
```

**Intelligent transcript reuse:** If a transcript already exists in the output directory, it will be reused without re-transcribing. Otherwise, the video will be downloaded and transcribed first.

This creates:
- `transcript.txt` (if not already present)
- `report.md` (AI-generated summary)
- `report.pdf` (PDF version)
- `yt-transcribe.log`

**Requires** `OPENAI_API_KEY` environment variable.

#### Options

- `--output-dir`, `-o`: Base directory for output files (default: `./output`)
- `--model`, `-m`: Whisper model size (default: `base`) - only used if transcription is needed
- `--device`, `-d`: Device: `cpu` or `cuda` (default: `cpu`) - only used if transcription is needed
- `--keep-audio`: Keep audio file - only used if transcription is needed
- `--openai-model`: OpenAI model to use (default: `gpt-5-mini`)
- `--prompt`: Custom summary prompt (file path or string)
- `--debug`: Enable debug logging

#### Examples

```bash
# Basic summarization
ytt summarize https://www.youtube.com/watch?v=VIDEO_ID

# Use a different OpenAI model
ytt summarize https://www.youtube.com/watch?v=VIDEO_ID --openai-model gpt-5

# With custom prompt from file
ytt summarize https://www.youtube.com/watch?v=VIDEO_ID --prompt prompt.txt

# With custom prompt as string
ytt summarize https://www.youtube.com/watch?v=VIDEO_ID --prompt "Summarize this video focusing on technical details"

# Use larger Whisper model if transcription is needed
ytt summarize https://www.youtube.com/watch?v=VIDEO_ID --model large
```

### Generate Report from Existing Transcript

Generate a report from an arbitrary transcript file:

```bash
ytt report <path-to-transcript.txt>
```

This is useful when you:
- Want to regenerate a report with different parameters
- Have a transcript from a previous run and want to create a report without re-transcribing
- Want to try different OpenAI models to see which produces better results
- Have a transcript file from another source

#### Options

- `--openai-model`: OpenAI model to use (default: `gpt-5-mini`)
- `--prompt`: Custom summary prompt (file path or string)
- `--debug`: Enable debug logging

#### Examples

```bash
# Generate report from existing transcript
ytt report output/2025-11-05/Video_Title/transcript.txt

# Use a different OpenAI model
ytt report output/2025-11-05/Video_Title/transcript.txt --openai-model gpt-5

# With custom prompt
ytt report output/2025-11-05/Video_Title/transcript.txt --prompt "Focus on key takeaways"

# With debug logging
ytt report output/2025-11-05/Video_Title/transcript.txt --debug
```

The report files (`report.md` and `report.pdf`) will be saved in the same directory as the transcript file.

## Output Files

Files are organized by date and video title:

```
output/
└── YYYY-MM-DD/              # Date of processing
    └── Video_Title/         # Sanitized video title
        ├── transcript.txt   # Raw transcription
        ├── report.md        # AI-generated report (Markdown) - only with summarize
        ├── report.pdf       # Report as PDF - only with summarize
        └── yt-transcribe.log # Processing log
```

**What each command creates:**

- `ytt transcribe URL`: Creates `transcript.txt` only
- `ytt summarize URL`: Creates `transcript.txt` (if needed), `report.md`, and `report.pdf`
- `ytt report FILE`: Creates `report.md` and `report.pdf` in the same directory as the transcript file

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
- **[CLAUDE.md](CLAUDE.md)** - Development documentation, architecture, and guidelines for contributors

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

