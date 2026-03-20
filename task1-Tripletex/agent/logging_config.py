"""
Centralized logging configuration.

Logs go to:
  - stdout (for container/uvicorn output)
  - logs/agent.log (rolling file, one per run for post-mortem debugging)
  - logs/trace.jsonl (structured JSONL of pipeline step traces)
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOGS_DIR = Path(__file__).parent.parent / "logs"
LOGS_DIR.mkdir(exist_ok=True)

AGENT_LOG = LOGS_DIR / "agent.log"
TRACE_JSONL = LOGS_DIR / "trace.jsonl"

_configured = False


def setup_logging(level: int = logging.INFO) -> None:
    """Configure logging once. Safe to call multiple times."""
    global _configured
    if _configured:
        return
    _configured = True

    root = logging.getLogger()
    root.setLevel(level)

    fmt = logging.Formatter(
        "%(asctime)s | %(name)s | %(levelname)s | %(message)s",
        datefmt="%H:%M:%S",
    )

    # Console handler (stdout)
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(level)
    console.setFormatter(fmt)
    root.addHandler(console)

    # File handler — rotating, 5MB max, keep 5 backups
    file_handler = RotatingFileHandler(
        AGENT_LOG, maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    file_handler.setLevel(level)
    file_fmt = logging.Formatter(
        "%(asctime)s | %(name)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(file_fmt)
    root.addHandler(file_handler)


def write_trace(step: int, name: str, input_text: str, output_text: str,
                duration_ms: float, extra: dict | None = None) -> None:
    """Append one structured trace record to logs/trace.jsonl."""
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "step": step,
        "name": name,
        "input": input_text,
        "output": output_text,
        "duration_ms": round(duration_ms, 1),
    }
    if extra:
        record["extra"] = extra
    with open(TRACE_JSONL, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
