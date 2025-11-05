"""Generate AI-powered reports from transcripts using OpenAI."""

from openai import OpenAI


def generate_report(transcript: str, api_key: str, model: str = "gpt-4") -> str:
    """Generate a report from a transcript using OpenAI.
    
    Args:
        transcript: The transcribed text
        api_key: OpenAI API key
        model: OpenAI model to use
        
    Returns:
        Generated report as a string
    """
    client = OpenAI(api_key=api_key)
    
    prompt = """You are an expert analyst who creates comprehensive reports from video transcripts.

Create a detailed report with the following sections:

## Summary
Provide a clear and concise summary of the video content.

## Key Ideas
List and explain the main ideas and concepts discussed in the video.

## Why It Matters
This section should go beyond mere summarization to provide meaningful context and significance. Analyze the content and naturally connect it to broader ideas, contexts, and implications that are genuinely relevant to the topic. 

Consider where appropriate (but only if truly relevant to the content):
- How these ideas fit into larger intellectual or cultural conversations
- Connections to established theories, movements, or trends
- Real-world applications or consequences
- Why these concepts matter to understanding the world
- Cross-disciplinary connections that illuminate the topic

Write this as a cohesive analytical narrative, not as separate subsections. Focus on making insightful connections that help readers understand the deeper significance of the content, rather than forcing coverage of unrelated areas.

Format your response as Markdown."""

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
        raise ValueError("OpenAI API returned an empty response")
    
    return report

