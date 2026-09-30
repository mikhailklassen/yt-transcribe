# yt-transcribe

A command-line tool to transcribe YouTube videos and generate AI-powered reports using OpenAI.

## Features

- Download audio from YouTube videos
- Transcribe audio using faster-whisper
- Generate comprehensive reports with OpenAI (Summary, Key Ideas, and a section adapted to the content)
- Export reports as Markdown, with optional PDF (`--pdf`)
- **Config file** - Set your default output directory and models in `config.yml`
- **Input validation** - Validates URLs, model names, and API keys before processing
- **Organized outputs** - One folder per video (date, title and video ID), reused on later runs so videos are never transcribed twice
- **Script- and agent-friendly** - Detailed `ytt --help`, clean stdout/stderr split and meaningful exit codes
- **Detailed logging** - Debug mode with comprehensive logs per video
- **Error handling** - Clear, actionable error messages

## Installation

### macOS

1. Install system dependencies (Cairo, Pango, GDK-PixBuf and libffi are only needed for `--pdf`):
   ```bash
   brew install cairo pango gdk-pixbuf libffi ffmpeg
   ```

2. For PDF output, set the library path (add to your `~/.zshrc` or `~/.bash_profile`):
   ```bash
   export DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib:$DYLD_FALLBACK_LIBRARY_PATH
   ```

3. Install Python dependencies using `uv` (or your preferred package manager):
   ```bash
   uv sync --extra pdf   # or just `uv sync` if you don't need PDF reports
   ```

4. Set up your OpenAI API key:
   ```bash
   echo "OPENAI_API_KEY=your-api-key-here" > .env
   ```
   Or set the `OPENAI_API_KEY` environment variable.

### Linux

1. Install system dependencies (everything except `ffmpeg` is only needed for `--pdf`):
   ```bash
   # Debian/Ubuntu
   sudo apt-get install libcairo2 libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0 libffi-dev ffmpeg
   
   # Fedora/RHEL
   sudo dnf install cairo pango gdk-pixbuf2 libffi-devel ffmpeg
   ```

2. Install Python dependencies:
   ```bash
   uv sync --extra pdf   # or just `uv sync` if you don't need PDF reports
   ```

3. Set up your OpenAI API key:
   ```bash
   echo "OPENAI_API_KEY=your-api-key-here" > .env
   ```
   Or set the `OPENAI_API_KEY` environment variable.

**How the API key is found:** an `OPENAI_API_KEY` environment variable wins; otherwise the `.env` file at the root of this repository is used (also when `ytt` is installed globally and run from another directory). If you get a 401 error, check that your shell doesn't export an old key that overrides `.env`.

### Install `ytt` globally (optional)

To run `ytt` from any directory without `uv run`:

```bash
uv tool install --editable '.[pdf]'
```

The editable install runs the code in this repository, so keep the checkout in place; changes to it take effect without reinstalling. Without a global install, run commands from the repo as `uv run ytt …`.

Run `ytt --help` (or `ytt -h`) for the full workflow, output layout, exit codes and configuration, and `ytt COMMAND --help` for each command's options and examples. `ytt --version` prints the version.

## Usage

### Transcribe a YouTube Video

Download and transcribe a YouTube video to text only (no AI summary):

```bash
ytt transcribe https://youtube.com/watch?v=VIDEO_ID
```

This creates: `output/YYYY-MM-DD/Video_Title_VIDEOID/transcript.txt`

Accepted URLs include `youtube.com/watch?v=…`, `youtu.be/…`, `youtube.com/shorts/…`, `/embed/…` and `/live/…` links (including `m.` and `music.` hosts).

Quote URLs in the shell, since they often contain `&` or `?`.

**No OpenAI API key required** for transcription.

#### Options

- `--output-dir`, `-o`: Base directory for output files (default: `output_dir` from config, else `./output`)
- `--model`, `-m`: Whisper model - `tiny`, `base`, `small`, `medium`, `large`, `large-v2`, `large-v3` (default: `base`)
- `--device`, `-d`: Device to use - `cpu` or `cuda` (default: `cpu`)
- `--keep-audio`: Save the downloaded audio as `audio.mp3` in the output folder
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

**Intelligent transcript reuse:** If this video was transcribed before (on any date), its existing folder and transcript are reused without re-transcribing. Otherwise, the video will be downloaded and transcribed first.

This creates:
- `transcript.txt` (if not already present)
- `report.md` (AI-generated summary)
- `report.pdf` (only with `--pdf`)
- `yt-transcribe.log`

**Requires** `OPENAI_API_KEY` (environment variable or `.env`; see [Installation](#installation)). `report.md` is overwritten each time.

#### Options

- `--output-dir`, `-o`: Base directory for output files (default: `output_dir` from config, else `./output`)
- `--model`, `-m`: Whisper model size (default: `base`) - only used if transcription is needed
- `--device`, `-d`: Device: `cpu` or `cuda` (default: `cpu`) - only used if transcription is needed
- `--keep-audio`: Save the downloaded audio in the output folder - only used if transcription is needed
- `--openai-model`: OpenAI model to use (default: `openai_model` from config, else `gpt-6-luna`)
- `--prompt`: Custom summary prompt text
- `--prompt-file`: Read the custom summary prompt from a file
- `--pdf`: Also save the report as `report.pdf`
- `--debug`: Enable debug logging

#### Examples

```bash
# Basic summarization
ytt summarize https://www.youtube.com/watch?v=VIDEO_ID

# Use a different OpenAI model
ytt summarize https://www.youtube.com/watch?v=VIDEO_ID --openai-model gpt-5

# With custom prompt from file
ytt summarize https://www.youtube.com/watch?v=VIDEO_ID --prompt-file prompt.txt

# With custom prompt as string
ytt summarize https://www.youtube.com/watch?v=VIDEO_ID --prompt "Summarize this video focusing on technical details"

# Use larger Whisper model if transcription is needed
ytt summarize https://www.youtube.com/watch?v=VIDEO_ID --model large

# Also produce a PDF
ytt summarize https://www.youtube.com/watch?v=VIDEO_ID --pdf
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

- `--openai-model`: OpenAI model to use (default: `openai_model` from config, else `gpt-6-luna`)
- `--prompt`: Custom summary prompt text
- `--prompt-file`: Read the custom summary prompt from a file
- `--pdf`: Also save the report as `report.pdf`
- `--debug`: Enable debug logging

#### Examples

```bash
# Generate report from existing transcript
ytt report output/2025-11-05/Video_Title_VIDEOID/transcript.txt

# Use a different OpenAI model
ytt report output/2025-11-05/Video_Title_VIDEOID/transcript.txt --openai-model gpt-5

# With custom prompt
ytt report output/2025-11-05/Video_Title_VIDEOID/transcript.txt --prompt "Focus on key takeaways"

# With debug logging
ytt report output/2025-11-05/Video_Title_VIDEOID/transcript.txt --debug
```

The report (`report.md`, plus `report.pdf` with `--pdf`) will be saved in the same directory as the transcript file, replacing any existing report there.

## Configuration

Defaults can be set in a YAML config file, so you don't have to repeat options on every run. The file is read from, in order:

1. `--config PATH` (e.g. `ytt --config my.yml summarize URL`)
2. `$YTT_CONFIG`
3. `~/.config/yt-transcribe/config.yml` (or `$XDG_CONFIG_HOME/yt-transcribe/config.yml`)

All keys are optional, and command-line options always override them:

```yaml
output_dir: ~/Documents/yt-transcribe   # base output directory
openai_model: gpt-6-luna                # used by summarize and report
whisper_model: base                     # tiny, base, small, medium, large, large-v2, large-v3
device: cpu                             # cpu or cuda
```

A commented template is in [config.example.yml](config.example.yml). Run `ytt config` to see which file is being used and what it sets.

## Output Files

Each video gets one folder, named by date, title and video ID:

```
output/
└── YYYY-MM-DD/               # Date the video was first processed
    └── Video_Title_VIDEOID/  # Sanitized title + YouTube video ID
        ├── transcript.txt    # Plain-text transcript (single paragraph, no timestamps)
        ├── report.md         # AI-generated report (summarize/report)
        ├── report.pdf        # Report as PDF - only with --pdf
        ├── audio.mp3         # Downloaded audio - only with --keep-audio
        └── yt-transcribe.log # Log of every run for this video
```

On later runs the video's existing folder is found by its ID (whatever the date) and reused. Audio is downloaded into a temporary directory that is always deleted, so nothing is written to the directory you run `ytt` from.

**What each command creates:**

- `ytt transcribe URL`: Creates `transcript.txt` only
- `ytt summarize URL`: Creates `transcript.txt` (if needed) and `report.md` (plus `report.pdf` with `--pdf`)
- `ytt report FILE`: Creates `report.md` (plus `report.pdf` with `--pdf`) in the same directory as the transcript file

**Example:**
```
output/
└── 2024-11-05/
    └── My_YouTube_Video_dQw4w9WgXcQ/
        ├── transcript.txt
        ├── report.md
        ├── report.pdf
        └── yt-transcribe.log
```

## Requirements

- Python 3.11+
- FFmpeg (for audio extraction)
- System libraries: Cairo, Pango, GDK-PixBuf, libffi (only needed for `--pdf`)
- OpenAI API key

**Note:** Follow the [Installation](#installation) section for your platform to install all dependencies correctly.

## Scripting and Agents

- Progress messages go to **stdout**; warnings and errors go to **stderr**. On success, stdout ends with `📁 <folder>/` followed by the files written.
- Exit codes: `0` success, `1` invalid input or processing error, `2` usage error (bad or conflicting options), `130` interrupted.
- Running `summarize` again on the same video reuses the transcript and only makes one OpenAI call.
- `ytt --help` documents all of this, so an agent can learn the tool from the help text alone.

## Notes

- Run the tests with `uv run pytest` (no network access or API key needed)
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

### YouTube "HTTP Error 403: Forbidden"

YouTube changes regularly and older `yt-dlp` versions get blocked. Upgrade it:

```bash
uv lock --upgrade-package yt-dlp && uv sync --extra pdf
```

### OpenAI "401 Unauthorized" / "Incorrect API key"

The key being used is invalid. An `OPENAI_API_KEY` exported in your shell overrides `.env`, so check both (`echo ${OPENAI_API_KEY: -4}` shows the last four characters of the shell's key).

### Fontconfig Warnings

Fontconfig warnings like "No writable cache directories" are harmless and don't affect functionality. They can be safely ignored.

