"""
Run the agent from the terminal.

Usage:
    source .env && uv run python -m agent "Opprett en ny ansatt med navn Ola Nordmann"
    source .env && uv run python -m agent   # interactive prompt
"""

import asyncio
import os
import sys

from agent.logging_config import setup_logging
from agent.orchestrator import run

setup_logging()


async def main(prompt: str) -> None:
    base_url = os.environ["TRIPLETEX_BASE_URL"]
    session_token = os.environ["TRIPLETEX_SESSION_TOKEN"]

    print(f"\n{'=' * 70}")
    print(f"PROMPT: {prompt}")
    print(f"{'=' * 70}\n")

    await run(prompt, base_url, session_token)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        prompt = " ".join(sys.argv[1:])
    else:
        prompt = input("Enter prompt: ")

    asyncio.run(main(prompt))
