"""Auto-round: fetch history, then run prediction for active round.

Designed to be called by cron/scheduler every ~3 hours.
Skips gracefully if no active round or queries already spent.
"""

import sys
import subprocess
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).parent
LOG_DIR = ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)


def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_DIR / "auto_round.log", "a") as f:
        f.write(line + "\n")


def main():
    log("=== Auto-round started ===")

    # 1. Fetch latest history
    log("Fetching history...")
    result = subprocess.run(
        [sys.executable, str(ROOT / "fetch_history.py")],
        capture_output=True, text=True, timeout=120, cwd=str(ROOT),
    )
    if result.returncode != 0:
        log(f"fetch_history failed: {result.stderr[-200:]}")
    else:
        log("History fetched OK")

    # 2. Run prediction
    log("Running prediction...")
    result = subprocess.run(
        [sys.executable, str(ROOT / "run_round.py")],
        capture_output=True, text=True, timeout=600, cwd=str(ROOT),
    )
    log(result.stdout[-500:] if result.stdout else "(no output)")
    if result.returncode != 0:
        log(f"run_round failed: {result.stderr[-300:]}")
    else:
        log("Prediction submitted OK")

    log("=== Auto-round finished ===\n")


if __name__ == "__main__":
    main()
