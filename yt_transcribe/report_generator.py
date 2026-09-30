"""Generate AI-powered reports from transcripts using OpenAI."""

from openai import OpenAI
import logging

logger = logging.getLogger(__name__)

# Default prompt for report generation
DEFAULT_PROMPT = """You are an expert analyst who creates comprehensive, detailed reports from video transcripts.

First, assess the content type and scope of this video. Adapt your report structure accordingly:
- For general/educational content: focus on key ideas and broader implications
- For tutorials/how-tos: focus on steps, procedures, and practical details
- For technical/specialized content: focus on accuracy and technical details
- For niche topics: prioritize faithful summarization over adding external context

Create a report with the following sections:

# Title
Provide a title for the report. This should be a concise and clear title that captures the main content of the video. It could be the title of the video.

## Summary
Provide a concise summary of the video content (typically 3-4 paragraphs, but may be longer if needed for completeness). Include specific points, examples, and key information discussed. This should be like an executive summary that can stand alone as a summary of the video.

## Key Ideas
Parse out the main points in detail (typically 5-10 bullets, more if the content is dense or technical):
- If the video makes an argument, recapitulate the argument structure
- If the video presents information, list the key points
- If the video is a tutorial, highlight the main steps/concepts
- Include important nuances, qualifications, or examples
- Keep bullets concise - no sub-bullets or nested sections
- You may bold/italicize key terms, but never entire bullets

## [Adaptive Third Section]
The title and content of this section should match the content type:

- For general topics with broader relevance: Use "Why It Matters" and discuss implications, historical context, real-world applications
- For tutorials/how-tos: Use "Implementation Notes" or "Key Takeaways" and focus on practical details, common pitfalls, important caveats
- For technical/specialized content: Use "Additional Context" or "Technical Details" and expand on complex concepts
- For highly niche content where you lack broader context: Skip this section OR keep it brief and domain-specific

**Important:** Only include information supported by the transcript. Do not hallucinate broader context or implications if you're uncertain. For niche topics, accuracy matters more than comprehensiveness.

Format as Markdown. Use formatting (bold, italic, bullets) for readability. Avoid emojis.
"""

# Model context window limits (total tokens: input + output). Models not listed
# here skip the local size check and rely on the API to reject oversized input.
MODEL_CONTEXT_LIMITS = {
    "gpt-6-luna": 1_050_000,
    "gpt-5": 400_000,
    "gpt-5-mini": 400_000,
    "gpt-5-nano": 400_000,
    "gpt-4.1": 1_047_576,
    "gpt-4.1-mini": 1_047_576,
    "gpt-4.1-nano": 1_047_576,
    "o3": 200_000,
    "o4-mini": 200_000,
    "gpt-4o": 128_000,
    "gpt-4o-mini": 128_000,
    "gpt-4-turbo": 128_000,
    "gpt-4-turbo-preview": 128_000,
    "gpt-4-0125-preview": 128_000,
    "gpt-4": 8_192,
    "gpt-3.5-turbo": 16_385,
}

# Rough allowance for chat message formatting around the prompt and transcript
MESSAGE_OVERHEAD_TOKENS = 100


def _estimate_tokens(text: str) -> int:
    """Estimate token count from text (rough estimate: 1 token ≈ 4 characters)."""
    return len(text) // 4


def check_context_limit(transcript: str, prompt: str, model: str) -> None:
    """Fail fast if the input clearly won't fit in the model's context window.
    
    Args:
        transcript: The transcribed text
        prompt: System prompt that will be sent with it
        model: OpenAI model name
        
    Raises:
        ValueError: If the estimated input exceeds a known model's context window
    """
    context_limit = MODEL_CONTEXT_LIMITS.get(model)
    if context_limit is None:
        logger.debug(f"No known context limit for {model}; skipping size check")
        return
    
    estimated_input_tokens = (
        _estimate_tokens(transcript) + _estimate_tokens(prompt) + MESSAGE_OVERHEAD_TOKENS
    )
    logger.debug(
        f"Estimated input tokens: {estimated_input_tokens:,} (limit for {model}: {context_limit:,})"
    )
    
    if estimated_input_tokens >= context_limit:
        error_msg = (
            f"Transcript is too long for {model}. "
            f"Estimated input tokens: {estimated_input_tokens:,} (model limit: {context_limit:,}). "
            "Please use a model with a larger context window (e.g., gpt-6-luna, gpt-4.1), "
            "or truncate the transcript."
        )
        logger.error(error_msg)
        raise ValueError(error_msg)


def generate_report(transcript: str, api_key: str, model: str = "gpt-6-luna", prompt: str | None = None) -> str:
    """Generate a report from a transcript using OpenAI.
    
    Args:
        transcript: The transcribed text
        api_key: OpenAI API key
        model: OpenAI model to use
        prompt: Custom prompt to use for report generation. If None, uses DEFAULT_PROMPT.
        
    Returns:
        Generated report as a string
        
    Raises:
        ValueError: If the transcript is empty or too long for the model's context window
    """
    if not transcript.strip():
        raise ValueError("Transcript is empty (no speech detected?); nothing to summarize")
    
    logger.debug(f"Transcript length: {len(transcript)} characters")
    
    # Use custom prompt if provided, otherwise use default
    if prompt is None:
        prompt = DEFAULT_PROMPT
        logger.debug("Using default prompt")
    else:
        logger.debug(f"Using custom prompt ({len(prompt)} characters)")
    
    check_context_limit(transcript, prompt, model)
    
    logger.info(f"Sending request to OpenAI API (model: {model})...")
    client = OpenAI(api_key=api_key)
    
    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": prompt,
            },
            {
                "role": "user",
                "content": f"Please analyze this transcript and create a report:\n\n{transcript}",
            },
        ],
    )
    
    report = response.choices[0].message.content
    finish_reason = response.choices[0].finish_reason
    
    if not report:
        logger.error("OpenAI API returned empty response")
        raise ValueError("OpenAI API returned an empty response")
    
    # Check if the response was truncated
    if finish_reason == "length":
        logger.warning(
            f"Report was truncated at the model's output limit "
            f"({response.usage.completion_tokens} tokens); the saved report is incomplete."
        )
    
    logger.info(f"Report generated successfully: {len(report)} characters")
    logger.info(f"Finish reason: {finish_reason}")
    logger.debug(f"Tokens used: prompt={response.usage.prompt_tokens}, "
                f"completion={response.usage.completion_tokens}, "
                f"total={response.usage.total_tokens}")
    
    return report
