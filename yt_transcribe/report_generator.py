"""Generate AI-powered reports from transcripts using OpenAI."""

from openai import OpenAI
import logging

logger = logging.getLogger(__name__)

# Default prompt for report generation
DEFAULT_PROMPT = """You are an expert analyst who creates comprehensive, detailed reports from video transcripts.

Create a report with the following sections. In each section, balance depth and breadth. The report should be comprehensive and detailed, but not too verbose. Use Markdown formatting.

# Title
Provide a title for the report. This should be a concise and clear title that captures the main content of the video. It could be the title of the video. 

## Summary
Provide a summary of the video content. Include specific points, examples, and key information discussed. This section should be concise, and no more than 4 paragraphs in length,
like an executive summary or the abstract of a research paper. It should be a concise and clear overview of the video content, and should be able to stand alone as a summary of the video.

## Key Ideas
In this section, go into a bit more depth than the summary, parsing out the main points of the video. If the video is making a persuasive argument, the bullet
points of this section would recapitulate the argument, but in a more detailed and structured way. If the video is presenting information, the bullet
points of this section would be a list of the key points of the information presented. Note any important nuances, qualifications, or exceptions discussed. If
there are important illustrative examples, summarize them as a bullet point in this section. Do not create subsections within this section, or bullets within bullets. Do not 
use bullets as "titles" for subsections. Keep it to less than 8 bullets in this section. Focus on the most important ideas or arguments presented in the video.
You may bold or italicize the most important words or phrases within each bullet point, but never the entire bullet point itself.

## Why It Matters
In this section, go beyond the key ideas or arguments presented in the video and connect them to broader ideas, contexts, and implications that are genuinely relevant to the topic.
For example, if there is some important historical context that wasn't mentioned in the video, or some important real-world applications or consequences of the ideas presented,
summarize them as a bullet point in this section. Group relevant points together into subsections (e.g. "### Historical Context", "### Geopolitical Implications", etc.). You don't
need to use exactly those categories, but you should use a natural grouping of points.

Format your response as Markdown. You may use markdown formatting to make the report more readable, such as bolding, italicizing, and bullet points. Avoid the use of emojis.
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

