"""Generate AI-powered reports from transcripts using OpenAI."""

from openai import OpenAI
import logging

logger = logging.getLogger(__name__)


def generate_report(transcript: str, api_key: str, model: str = "gpt-4") -> str:
    """Generate a report from a transcript using OpenAI.
    
    Args:
        transcript: The transcribed text
        api_key: OpenAI API key
        model: OpenAI model to use
        
    Returns:
        Generated report as a string
    """
    logger.info(f"Initializing OpenAI client with model: {model}")
    client = OpenAI(api_key=api_key)
    
    transcript_length = len(transcript)
    logger.debug(f"Transcript length: {transcript_length} characters")
    
    # Rough token estimate (1 token ≈ 4 characters)
    estimated_tokens = transcript_length // 4
    logger.debug(f"Estimated tokens: {estimated_tokens}")
    
    if estimated_tokens > 100000:
        logger.warning(f"Transcript is very long ({estimated_tokens} tokens). May exceed token limits.")
    
    prompt = """You are an expert analyst who creates comprehensive, detailed reports from video transcripts.

Create a thorough and in-depth report with the following sections. Aim for substantial detail and depth in each section:

## Summary
Provide a comprehensive and detailed summary of the video content. Include specific points, examples, and key information discussed. Don't just skim the surface—dive deep into the main themes, arguments, and information presented. The summary should be substantial enough that someone could understand the video's content without watching it.

## Key Ideas
Provide a detailed exploration of the main ideas and concepts discussed in the video. For each key idea:
- Explain the concept thoroughly with context
- Include specific examples, details, or evidence mentioned in the video
- Describe how ideas connect to each other
- Note any important nuances, qualifications, or exceptions discussed
- Reference specific points or arguments made in the transcript

Aim for depth rather than breadth—thoroughly explore each major idea rather than just listing many points superficially.

## Why It Matters
This section should go beyond mere summarization to provide meaningful context and significance. Analyze the content and naturally connect it to broader ideas, contexts, and implications that are genuinely relevant to the topic. 

Consider where appropriate (but only if truly relevant to the content):
- How these ideas fit into larger intellectual or cultural conversations
- Connections to established theories, movements, or trends
- Real-world applications or consequences
- Why these concepts matter to understanding the world
- Cross-disciplinary connections that illuminate the topic
- Practical implications for different audiences
- Historical context or future implications

Write this as a cohesive analytical narrative, not as separate subsections. Focus on making insightful connections that help readers understand the deeper significance of the content, rather than forcing coverage of unrelated areas. Provide substantial detail and examples to support your analysis.

Overall, prioritize depth, detail, and comprehensiveness. The report should be thorough enough to serve as a valuable reference document. Include specific information from the transcript rather than vague generalizations.

Format your response as Markdown."""

    logger.info("Sending request to OpenAI API...")
    
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
        temperature=0.7,
    )
    
    report = response.choices[0].message.content
    
    if not report:
        logger.error("OpenAI API returned empty response")
        raise ValueError("OpenAI API returned an empty response")
    
    logger.info(f"Report generated successfully: {len(report)} characters")
    logger.debug(f"Tokens used: prompt={response.usage.prompt_tokens}, "
                f"completion={response.usage.completion_tokens}, "
                f"total={response.usage.total_tokens}")
    
    return report

