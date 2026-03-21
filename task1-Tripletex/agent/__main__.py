"""
Run the preprocessing pipeline from the terminal.

Usage:
    uv run python -m agent "Opprett en ny ansatt med navn Ola Nordmann"
    uv run python -m agent   # interactive prompt
"""

import asyncio
import json
import sys

from agent.logging_config import setup_logging
from agent.pipeline import preprocess

setup_logging()


async def main(prompt: str) -> None:
    print(f"\n{'='*70}")
    print(f"INPUT PROMPT:\n{prompt}")
    print(f"{'='*70}\n")

    result = await preprocess(prompt)

    # Print each step's trace
    for t in result.trace.traces:
        print(f"{'─'*70}")
        print(f"STEP {t.step} — {t.name} ({t.duration_ms:.0f}ms)")
        print(f"  IN:  {t.input[:200]}")
        print(f"  OUT: {t.output[:300]}")
        if t.extra:
            print(f"  EXTRA: {json.dumps(t.extra, ensure_ascii=False, default=str)[:300]}")

    # Print final plan
    print(f"\n{'='*70}")
    print(f"EXECUTION PLAN ({len(result.plan.steps)} steps):")
    print(f"{'='*70}")
    for s in result.plan.steps:
        deps = f" (after Step {', '.join(str(d) for d in s.depends_on)})" if s.depends_on else ""
        schema_info = ""
        if s.schema:
            fields = list(s.schema.get("request_body", {}).get("properties", {}).keys())[:8]
            params = [p["name"] for p in s.schema.get("query_params", [])[:5]]
            if fields:
                schema_info = f"\n    body fields: {', '.join(fields)}"
            if params:
                schema_info += f"\n    query params: {', '.join(params)}"
        else:
            schema_info = "\n    ⚠ no registry match"
        print(f"\n  Step {s.step}: {s.action}{deps}")
        print(f"    → {s.method} {s.endpoint}{schema_info}")

    print(f"\n{'─'*70}")
    print(result.trace.summary())
    print()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        prompt = " ".join(sys.argv[1:])
    else:
        prompt = input("Enter prompt: ")

    asyncio.run(main(prompt))
