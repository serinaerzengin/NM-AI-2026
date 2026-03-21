"""LLM client — OpenAI SDK pointing to Gemini via OpenAI-compatible API."""

import asyncio
import json
import logging
import os
from openai import AsyncOpenAI, APIError

logger = logging.getLogger("llm")

# Gemini via OpenAI-compatible endpoint
DEFAULT_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
DEFAULT_MODEL = "gemini-3.1-pro-preview"


def get_client() -> AsyncOpenAI:
    """Create an AsyncOpenAI client configured for Gemini."""
    return AsyncOpenAI(
        api_key=os.getenv("GEMINI_API_KEY"),
        base_url=os.getenv("LLM_BASE_URL", DEFAULT_BASE_URL),
    )


async def ask(
    client: AsyncOpenAI,
    system: str,
    user_content: list[dict] | str,
    model: str | None = None,
    temperature: float = 0.0,
    max_tokens: int | None = None,
) -> str:
    """Send a message and get a text response.

    user_content can be a plain string or a list of content blocks
    (text + image_url) for vision inputs.
    """
    try:
        resp = await asyncio.wait_for(
            client.chat.completions.create(
                model=model or os.getenv("LLM_MODEL", DEFAULT_MODEL),
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user_content},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            ),
            timeout=60.0,
        )
        return resp.choices[0].message.content or ""
    except (APIError, asyncio.TimeoutError) as e:
        logger.error(f"LLM API error: {e}")
        return ""


async def ask_json(
    client: AsyncOpenAI,
    system: str,
    user_content: list[dict] | str,
    model: str | None = None,
    temperature: float = 0.0,
    max_tokens: int | None = None,
) -> dict | list:
    """Send a message and get a parsed JSON response.

    Instructs the model to respond in JSON and parses the result.
    """
    json_system = system + "\n\nYou MUST respond with valid JSON only. No markdown, no explanation."

    try:
        resp = await asyncio.wait_for(
            client.chat.completions.create(
                model=model or os.getenv("LLM_MODEL", DEFAULT_MODEL),
                messages=[
                    {"role": "system", "content": json_system},
                    {"role": "user", "content": user_content},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                response_format={"type": "json_object"},
            ),
            timeout=90.0,
        )
    except (APIError, asyncio.TimeoutError) as e:
        logger.error(f"LLM API error: {e}")
        return {"error": "api_error", "message": str(e)}

    text = resp.choices[0].message.content or ""
    try:
        return json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return {"error": "invalid_json", "raw": text[:500]}
