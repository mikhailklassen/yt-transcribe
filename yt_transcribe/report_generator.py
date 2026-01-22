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

# Model context window limits (total tokens: input + output)
MODEL_CONTEXT_LIMITS = {
    "gpt-4": 8192,
    "gpt-4.1": 128000,
    "gpt-4-turbo": 128000,
    "gpt-4-turbo-preview": 128000,
    "gpt-4-0125-preview": 128000,
    "gpt-4o": 128000,
    "gpt-4o-mini": 128000,
    "gpt-5": 128000,
    "gpt-5-mini": 128000,
    "gpt-5-nano": 128000,
    "gpt-3.5-turbo": 16385,
}


def _estimate_tokens(text: str) -> int:
    """Estimate token count from text (rough estimate: 1 token ≈ 4 characters)."""
    return len(text) // 4


def _calculate_max_completion_tokens(
    model: str, transcript_tokens: int, prompt_tokens: int, safety_buffer: int = 100
) -> int:
    """Calculate maximum completion tokens based on model limits and input size.
    
    Args:
        model: OpenAI model name
        transcript_tokens: Estimated tokens in transcript
        prompt_tokens: Estimated tokens in system prompt
        safety_buffer: Safety buffer to avoid hitting exact limit
        
    Returns:
        Maximum tokens available for completion
    """
    context_limit = MODEL_CONTEXT_LIMITS.get(model, 8192)
    
    # Estimate total input tokens (prompt + transcript + user message overhead)
    input_tokens = prompt_tokens + transcript_tokens + 50  # 50 for message overhead
    
    # Calculate available tokens for completion
    available_tokens = context_limit - input_tokens - safety_buffer
    
    # Ensure minimum of 500 tokens for completion (for very long transcripts)
    max_completion = max(500, available_tokens)
    
    logger.debug(
        f"Token calculation: context_limit={context_limit}, "
        f"input_tokens≈{input_tokens}, available={available_tokens}, "
        f"max_completion={max_completion}"
    )
    
    return max_completion


def generate_report(transcript: str, api_key: str, model: str = "gpt-5-mini", prompt: str | None = None) -> str:
    """Generate a report from a transcript using OpenAI.
    
    Args:
        transcript: The transcribed text
        api_key: OpenAI API key
        model: OpenAI model to use
        prompt: Custom prompt to use for report generation. If None, uses DEFAULT_PROMPT.
        
    Returns:
        Generated report as a string
        
    Raises:
        ValueError: If transcript is too long for the model's context window
    """
    logger.info(f"Initializing OpenAI client with model: {model}")
    client = OpenAI(api_key=api_key)
    
    transcript_length = len(transcript)
    logger.debug(f"Transcript length: {transcript_length} characters")
    
    # Estimate tokens
    transcript_tokens = _estimate_tokens(transcript)
    logger.debug(f"Estimated transcript tokens: {transcript_tokens}")
    
    # Use custom prompt if provided, otherwise use default
    if prompt is None:
        prompt = DEFAULT_PROMPT
        logger.debug("Using default prompt")
    else:
        logger.debug(f"Using custom prompt ({len(prompt)} characters)")

    prompt_tokens = _estimate_tokens(prompt)
    
    # Check if input alone exceeds model limits (before calculating completion tokens)
    context_limit = MODEL_CONTEXT_LIMITS.get(model, 8192)
    estimated_input_tokens = transcript_tokens + prompt_tokens + 100  # 100 for message overhead
    
    if estimated_input_tokens >= context_limit:
        if model == "gpt-4":
            suggested_model = "gpt-5, gpt-5-mini, gpt-5-nano, gpt-4.1, or gpt-4o"
        else:
            suggested_model = "a model with larger context window (e.g., gpt-5, gpt-5-mini, gpt-5-nano, gpt-4.1, gpt-4o)"
        
        error_msg = (
            f"Transcript is too long for {model}. "
            f"Estimated input tokens: {estimated_input_tokens:,} (model limit: {context_limit:,}). "
            f"Please use {suggested_model} instead, or truncate the transcript."
        )
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    # Calculate max completion tokens dynamically based on model limits
    max_completion_tokens = _calculate_max_completion_tokens(
        model, transcript_tokens, prompt_tokens
    )
    
    if max_completion_tokens < 1000:
        logger.warning(
            f"Limited completion tokens available ({max_completion_tokens}). "
            f"Report may be shorter than desired. Consider using a model with larger context window."
        )
    
    logger.info(f"Sending request to OpenAI API...")
    
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
        logger.warning(f"Report was truncated due to token limit! "
                      f"Used {response.usage.completion_tokens} tokens. "
                      f"Consider using a model with higher token limits or adjusting max_tokens.")
        logger.warning("The generated report is incomplete. To get the full report, "
                      "you may need to use a model with larger context window (e.g., 'gpt-5', 'gpt-5-mini', 'gpt-5-nano', 'gpt-4.1', 'gpt-4o') or increase max_tokens.")
    
    logger.info(f"Report generated successfully: {len(report)} characters")
    logger.info(f"Finish reason: {finish_reason}")
    logger.debug(f"Tokens used: prompt={response.usage.prompt_tokens}, "
                f"completion={response.usage.completion_tokens}, "
                f"total={response.usage.total_tokens}")
    
    return report

