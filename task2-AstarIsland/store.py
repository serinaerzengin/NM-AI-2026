"""Persistent storage for Astar Island map data.

Directory layout:
  data/
    rounds/
      round_{number}/
        meta.json                          — round details (id, size, seeds_count, status, weight)
        seed_{idx}/
          initial_state.json               — initial grid + settlements
          observations/
            obs_{viewport_x}_{viewport_y}.json  — simulation result for that viewport
          ground_truth.json                — post-round ground truth (from analysis endpoint)
          prediction.json                  — our submitted prediction (argmax + confidence)
    local-eval/                            — local evaluation results
"""

import json
from pathlib import Path
from typing import Optional

DATA_DIR = Path(__file__).parent / "data"
ROUNDS_DIR = DATA_DIR / "rounds"
EVAL_DIR = DATA_DIR / "local-eval"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _round_dir(round_number: int) -> Path:
    return ROUNDS_DIR / f"round_{round_number}"


def _seed_dir(round_number: int, seed_index: int) -> Path:
    return _round_dir(round_number) / f"seed_{seed_index}"


def _obs_dir(round_number: int, seed_index: int) -> Path:
    return _seed_dir(round_number, seed_index) / "observations"


def _write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2))


def _read_json(path: Path):
    if not path.exists():
        return None
    return json.loads(path.read_text())


# ---------------------------------------------------------------------------
# Round metadata
# ---------------------------------------------------------------------------

def save_round_meta(round_number: int, detail: dict) -> None:
    """Save round metadata (id, size, seeds, status, weight)."""
    meta = {
        "id": detail["id"],
        "round_number": detail.get("round_number", round_number),
        "status": detail.get("status"),
        "map_width": detail["map_width"],
        "map_height": detail["map_height"],
        "seeds_count": detail.get("seeds_count", len(detail.get("initial_states", []))),
        "round_weight": detail.get("round_weight"),
        "started_at": detail.get("started_at"),
        "closes_at": detail.get("closes_at"),
    }
    _write_json(_round_dir(round_number) / "meta.json", meta)


def load_round_meta(round_number: int) -> Optional[dict]:
    return _read_json(_round_dir(round_number) / "meta.json")


# ---------------------------------------------------------------------------
# Initial states
# ---------------------------------------------------------------------------

def save_initial_state(round_number: int, seed_index: int, state: dict) -> None:
    """Save the initial grid and settlements for a seed."""
    _write_json(_seed_dir(round_number, seed_index) / "initial_state.json", state)


def load_initial_state(round_number: int, seed_index: int) -> Optional[dict]:
    return _read_json(_seed_dir(round_number, seed_index) / "initial_state.json")


# ---------------------------------------------------------------------------
# Simulation observations
# ---------------------------------------------------------------------------

def save_observation(
    round_number: int,
    seed_index: int,
    viewport: dict,
    result: dict,
) -> None:
    """Save a simulation observation keyed by viewport coordinates.

    Each coordinate stores a list of observations (different seeds produce
    different results for the same viewport).
    result should contain: grid, settlements, viewport, queries_used, queries_max.
    """
    vx, vy = viewport["x"], viewport["y"]
    fname = f"obs_{vx}_{vy}.json"
    path = _obs_dir(round_number, seed_index) / fname

    existing = _read_json(path)
    if existing is None:
        observations = []
    elif isinstance(existing, list):
        observations = existing
    else:
        # Legacy format: single dict — wrap in a list
        observations = [existing]

    observations.append(result)
    _write_json(path, observations)


def load_observation(
    round_number: int, seed_index: int, viewport_x: int, viewport_y: int
) -> list[dict]:
    """Load all observations for a specific viewport coordinate."""
    fname = f"obs_{viewport_x}_{viewport_y}.json"
    data = _read_json(_obs_dir(round_number, seed_index) / fname)
    if data is None:
        return []
    if isinstance(data, list):
        return data
    # Legacy format: single dict
    return [data]


def list_observations(round_number: int, seed_index: int) -> list[dict]:
    """Load all observations for a seed, sorted by filename.

    Each file may contain multiple observations (list); legacy files with a
    single dict are handled transparently.
    """
    obs_path = _obs_dir(round_number, seed_index)
    if not obs_path.exists():
        return []
    results = []
    for f in sorted(obs_path.glob("obs_*.json")):
        data = json.loads(f.read_text())
        if isinstance(data, list):
            results.extend(data)
        else:
            # Legacy format: single dict
            results.append(data)
    return results


# ---------------------------------------------------------------------------
# Ground truth (post-round analysis)
# ---------------------------------------------------------------------------

def save_ground_truth(round_number: int, seed_index: int, analysis: dict) -> None:
    """Save ground truth from the analysis endpoint."""
    _write_json(_seed_dir(round_number, seed_index) / "ground_truth.json", analysis)


def load_ground_truth(round_number: int, seed_index: int) -> Optional[dict]:
    return _read_json(_seed_dir(round_number, seed_index) / "ground_truth.json")


# ---------------------------------------------------------------------------
# Our predictions
# ---------------------------------------------------------------------------

def save_prediction(round_number: int, seed_index: int, prediction_data: dict) -> None:
    """Save our submitted prediction (argmax_grid, confidence_grid, score, etc)."""
    _write_json(_seed_dir(round_number, seed_index) / "prediction.json", prediction_data)


def load_prediction(round_number: int, seed_index: int) -> Optional[dict]:
    return _read_json(_seed_dir(round_number, seed_index) / "prediction.json")


# ---------------------------------------------------------------------------
# Bulk operations
# ---------------------------------------------------------------------------

def save_round(round_number: int, detail: dict) -> None:
    """Save full round detail: metadata + all initial states."""
    save_round_meta(round_number, detail)
    for i, state in enumerate(detail.get("initial_states", [])):
        save_initial_state(round_number, i, state)


def list_stored_rounds() -> list[int]:
    """List all locally stored round numbers."""
    if not ROUNDS_DIR.exists():
        return []
    rounds = []
    for d in ROUNDS_DIR.iterdir():
        if d.is_dir() and d.name.startswith("round_"):
            try:
                rounds.append(int(d.name.split("_")[1]))
            except ValueError:
                pass
    return sorted(rounds)
