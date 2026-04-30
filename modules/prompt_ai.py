import os
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def enhance_prompt_with_ai(user_prompt: str) -> str:
    if not os.getenv("OPENAI_API_KEY"):
        return user_prompt

    response = client.responses.create(
        model="gpt-5.4-mini",
        input=f"""
Rewrite this user song idea into a clear Suno music prompt.

Rules:
- Keep the original meaning.
- Fix spelling and grammar.
- Add genre/mood if obvious.
- Keep it under 40 words.
- Do not add explanations.
- Return only the final prompt.

User prompt:
{user_prompt}
"""
    )

    return response.output_text.strip()