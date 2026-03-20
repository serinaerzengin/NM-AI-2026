"""Astar Island API client — wraps all endpoints from api.ainm.no/astar-island"""

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
import requests

load_dotenv(Path(__file__).parent / ".env")

BASE = "https://api.ainm.no/astar-island"


def _session() -> requests.Session:
    token = os.environ.get("AINM_TOKEN", "")
    if not token:
        raise RuntimeError("Set AINM_TOKEN in .env or env var")
    s = requests.Session()
    s.headers["Authorization"] = f"Bearer {token}"
    return s


SESSION: Optional[requests.Session] = None


def get_session() -> requests.Session:
    global SESSION
    if SESSION is None:
        SESSION = _session()
    return SESSION


# ---------------------------------------------------------------------------
# Public endpoints
# ---------------------------------------------------------------------------

def get_rounds() -> list[dict]:
    """GET /rounds — List all rounds with status and timing."""
    r = get_session().get(f"{BASE}/rounds")
    r.raise_for_status()
    return r.json()


def get_round_detail(round_id: str) -> dict:
    """GET /rounds/{round_id} — Round details + initial states for all seeds."""
    r = get_session().get(f"{BASE}/rounds/{round_id}")
    r.raise_for_status()
    return r.json()


def get_leaderboard() -> list[dict]:
    """GET /leaderboard — Public leaderboard."""
    r = get_session().get(f"{BASE}/leaderboard")
    r.raise_for_status()
    return r.json()


# ---------------------------------------------------------------------------
# Team endpoints (auth required)
# ---------------------------------------------------------------------------

def get_budget() -> dict:
    """GET /budget — Query budget for the active round."""
    r = get_session().get(f"{BASE}/budget")
    r.raise_for_status()
    return r.json()


def simulate(
    round_id: str,
    seed_index: int,
    viewport_x: int = 0,
    viewport_y: int = 0,
    viewport_w: int = 15,
    viewport_h: int = 15,
) -> dict:
    """POST /simulate — Run one stochastic simulation, observe viewport. Costs 1 query."""
    r = get_session().post(f"{BASE}/simulate", json={
        "round_id": round_id,
        "seed_index": seed_index,
        "viewport_x": viewport_x,
        "viewport_y": viewport_y,
        "viewport_w": viewport_w,
        "viewport_h": viewport_h,
    })
    r.raise_for_status()
    return r.json()


def submit(round_id: str, seed_index: int, prediction: list) -> dict:
    """POST /submit — Submit H×W×6 prediction tensor for one seed.

    prediction: list[list[list[float]]] — prediction[y][x][class], each cell sums to 1.0.
    Resubmitting overwrites previous prediction.
    """
    r = get_session().post(f"{BASE}/submit", json={
        "round_id": round_id,
        "seed_index": seed_index,
        "prediction": prediction,
    })
    r.raise_for_status()
    return r.json()


def get_my_rounds() -> list[dict]:
    """GET /my-rounds — All rounds with your scores, rank, budget."""
    r = get_session().get(f"{BASE}/my-rounds")
    r.raise_for_status()
    return r.json()


def get_my_predictions(round_id: str) -> list[dict]:
    """GET /my-predictions/{round_id} — Your predictions with argmax/confidence grids."""
    r = get_session().get(f"{BASE}/my-predictions/{round_id}")
    r.raise_for_status()
    return r.json()


def get_analysis(round_id: str, seed_index: int) -> dict:
    """GET /analysis/{round_id}/{seed_index} — Post-round ground truth comparison.

    Only available after round is completed/scoring.
    Returns prediction, ground_truth (H×W×6), score, and initial_grid.
    """
    r = get_session().get(f"{BASE}/analysis/{round_id}/{seed_index}")
    r.raise_for_status()
    return r.json()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_active_round() -> Optional[dict]:
    """Find the currently active round, or None."""
    rounds = get_rounds()
    return next((r for r in rounds if r["status"] == "active"), None)


def get_completed_rounds() -> list[dict]:
    """List all completed rounds, sorted by round_number."""
    rounds = get_rounds()
    completed = [r for r in rounds if r["status"] == "completed"]
    return sorted(completed, key=lambda r: r["round_number"])
