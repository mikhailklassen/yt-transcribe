# Usage Guide

This document provides comprehensive usage examples and practical scenarios for yt-transcribe.

## Basic Workflows

### Full Transcription and Report Generation

The most common use case - transcribe a YouTube video and generate a report:

```bash
ytt https://www.youtube.com/watch?v=VIDEO_ID
```

Output:
```
output/
└── 2025-11-05/
    └── Video_Title/
        ├── transcript.txt
        ├── report.md
        ├── report.pdf
        └── yt-transcribe.log
```

### Generate Report from Existing Transcript

If you already have a transcript and want to:
- Try a different OpenAI model for better results
- Regenerate a report that was truncated
- Create a new report after the prompt was improved

```bash
# Using default model (gpt-5-mini)
ytt report output/2025-11-05/Video_Title/transcript.txt

# Using a more powerful model
ytt report output/2025-11-05/Video_Title/transcript.txt --openai-model gpt-5

# Using a different model for faster/cheaper generation
ytt report output/2025-11-05/Video_Title/transcript.txt --openai-model gpt-3.5-turbo
```

## Advanced Workflows

### Using Different Whisper Models

For better accuracy, use larger Whisper models:

```bash
# High accuracy (slower)
ytt https://www.youtube.com/watch?v=VIDEO_ID --model large

# Medium accuracy (balanced)
ytt https://www.youtube.com/watch?v=VIDEO_ID --model medium

# Fast transcription (less accurate)
ytt https://www.youtube.com/watch?v=VIDEO_ID --model tiny
```

### GPU Acceleration

If you have a CUDA-compatible GPU:

```bash
ytt https://www.youtube.com/watch?v=VIDEO_ID --device cuda --model large
```

### Custom Output Directory

Organize your transcripts in a custom location:

```bash
ytt https://www.youtube.com/watch?v=VIDEO_ID -o ~/Documents/transcripts
```

### Debug Mode

Enable detailed logging for troubleshooting:

```bash
# For full workflow
ytt https://www.youtube.com/watch?v=VIDEO_ID --debug

# For report generation only
ytt report transcript.txt --debug
```

## Real-World Scenarios

### Scenario 1: Educational Content Archive

You're archiving educational videos and want detailed reports:

```bash
# Transcribe with high accuracy
ytt https://www.youtube.com/watch?v=VIDEO_ID --model large --openai-model gpt-5

# If you need to regenerate the report later
ytt report output/2025-11-05/Lecture_Title/transcript.txt --openai-model gpt-5
```

### Scenario 2: Content Research

You're researching a topic and need summaries of multiple videos:

```bash
# Transcribe multiple videos
ytt https://www.youtube.com/watch?v=VIDEO_ID_1
ytt https://www.youtube.com/watch?v=VIDEO_ID_2
ytt https://www.youtube.com/watch?v=VIDEO_ID_3

# Later, regenerate all reports with a more powerful model
for transcript in output/2025-11-05/*/transcript.txt; do
    ytt report "$transcript" --openai-model gpt-5
done
```

### Scenario 3: Testing OpenAI Models

You want to evaluate which OpenAI model produces the best reports:

```bash
# First, transcribe once
ytt https://www.youtube.com/watch?v=VIDEO_ID

# Test different models (this only calls OpenAI API, no re-transcription)
TRANSCRIPT="output/2025-11-05/Video_Title/transcript.txt"

# Test gpt-4
ytt report "$TRANSCRIPT" --openai-model gpt-4
cp output/2025-11-05/Video_Title/report.md comparison/gpt4.md

# Test gpt-5
ytt report "$TRANSCRIPT" --openai-model gpt-5
cp output/2025-11-05/Video_Title/report.md comparison/gpt5.md

# Test gpt-3.5-turbo (faster/cheaper)
ytt report "$TRANSCRIPT" --openai-model gpt-3.5-turbo
cp output/2025-11-05/Video_Title/report.md comparison/gpt3.5_turbo.md

# Now compare the reports in the comparison/ directory
```

### Scenario 4: Cost Optimization

You want to minimize costs by using cheaper models when appropriate:

```bash
# Use small Whisper model and gpt-3.5-turbo for casual content
ytt https://www.youtube.com/watch?v=VIDEO_ID --model small --openai-model gpt-3.5-turbo

# If you need a better report later, regenerate with a better model
# (only pays for the OpenAI API call, not re-transcription)
ytt report output/2025-11-05/Video_Title/transcript.txt --openai-model gpt-5
```

## Command Reference

### Full Workflow Command

```bash
ytt [URL] [OPTIONS]
# or
ytt transcribe [URL] [OPTIONS]
```

**Options:**
- `--output-dir, -o`: Output directory (default: ./output)
- `--model, -m`: Whisper model (tiny, base, small, medium, large)
- `--device, -d`: cpu or cuda
- `--openai-model`: OpenAI model (default: gpt-4)
- `--debug`: Enable debug logging
- `--keep-audio`: Keep temporary audio file

### Report Generation Command

```bash
ytt report [TRANSCRIPT_FILE] [OPTIONS]
```

**Options:**
- `--openai-model`: OpenAI model (default: gpt-4)
- `--debug`: Enable debug logging

## Tips and Best Practices

1. **Save transcripts, regenerate reports**: Transcription is the slow/expensive step. Keep your transcripts and regenerate reports as needed.

2. **Start with smaller models**: Use `--model base` initially. If accuracy isn't good enough, regenerate the transcript with `--model large`.

3. **Try different OpenAI models**: The `report` command makes it easy to experiment with different models without re-transcribing.

4. **Use debug mode for issues**: If something goes wrong, run with `--debug` to see detailed logs.

5. **Keep audio files for debugging**: Use `--keep-audio` if you need to inspect the downloaded audio file.

6. **Organize by project**: Use custom output directories (`-o`) to keep different projects separated.

## Getting Help

```bash
# General help
ytt --help

# Help for transcribe command
ytt transcribe --help

# Help for report command
ytt report --help
```

