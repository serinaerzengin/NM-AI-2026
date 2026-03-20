"""Astar Island Quickstart - NM i AI 2026

Uses initial terrain + simulation observations to build informed predictions.
- Static cells (ocean, mountain) get near-certain predictions for free
- Forests get high forest probability (but small chance of ruin/settlement)
- Settlement/port cells get priors from simulation observations
- Remaining land cells get weighted priors based on proximity to settlements
"""

import numpy as np

from api import (
    get_active_round,
    get_round_detail,
    get_budget,
    simulate,
    submit,
)
import store

# Prediction class indices
CLASS_EMPTY = 0      # Ocean (10), Plains (11), Empty (0)
CLASS_SETTLEMENT = 1
CLASS_PORT = 2
CLASS_RUIN = 3
CLASS_FOREST = 4
CLASS_MOUNTAIN = 5
NUM_CLASSES = 6

# Internal grid codes → prediction class
GRID_TO_CLASS = {
    10: CLASS_EMPTY,      # Ocean
    11: CLASS_EMPTY,      # Plains
    0:  CLASS_EMPTY,      # Empty
    1:  CLASS_SETTLEMENT,
    2:  CLASS_PORT,
    3:  CLASS_RUIN,
    4:  CLASS_FOREST,
    5:  CLASS_MOUNTAIN,
}

MIN_PROB = 0.01  # Floor to avoid KL divergence blowup


def build_initial_prior(grid: list[list[int]], settlements: list[dict]) -> np.ndarray:
    """Build a prior from the initial state before any simulation queries.

    Static terrain (ocean, mountain) → near-certain predictions.
    Forest → high forest prob with small dynamic chance.
    Plains near settlements → higher settlement/ruin chance.
    """
    h, w = len(grid), len(grid[0])
    pred = np.full((h, w, NUM_CLASSES), MIN_PROB)

    # Mark settlement positions for proximity calc
    settlement_positions = {(s["x"], s["y"]) for s in settlements}
    port_positions = {(s["x"], s["y"]) for s in settlements if s.get("has_port")}

    for y in range(h):
        for x in range(w):
            code = grid[y][x]

            if code == 10:  # Ocean — never changes
                pred[y][x] = [0.98, 0.002, 0.002, 0.002, 0.002, 0.002]

            elif code == 5:  # Mountain — never changes
                pred[y][x] = [0.002, 0.002, 0.002, 0.002, 0.002, 0.98]

            elif code == 4:  # Forest — mostly stable, can be replaced by settlement/ruin
                pred[y][x] = [0.05, 0.03, 0.01, 0.02, 0.85, 0.01]

            elif code in (1, 2):  # Initial settlement/port — dynamic, could survive/die/change
                if code == 2 or (x, y) in port_positions:
                    # Port: likely stays port or becomes ruin
                    pred[y][x] = [0.05, 0.15, 0.45, 0.25, 0.03, 0.01]
                else:
                    # Settlement: could survive, get port, or become ruin
                    pred[y][x] = [0.05, 0.40, 0.15, 0.30, 0.03, 0.01]

            elif code == 11:  # Plains — could get a settlement founded on it
                # Check proximity to existing settlements
                min_dist = _min_settlement_dist(x, y, settlement_positions)
                if min_dist <= 3:
                    # Close to settlement — higher chance of expansion/conflict
                    pred[y][x] = [0.40, 0.20, 0.05, 0.15, 0.10, 0.01]
                elif min_dist <= 6:
                    pred[y][x] = [0.55, 0.12, 0.03, 0.10, 0.10, 0.01]
                else:
                    # Far from settlements — mostly stays empty
                    pred[y][x] = [0.75, 0.05, 0.02, 0.05, 0.08, 0.01]

            else:  # code 0 or unknown
                pred[y][x] = [0.80, 0.04, 0.02, 0.04, 0.04, 0.02]

    return _normalize(pred)


def _min_settlement_dist(x: int, y: int, positions: set[tuple[int, int]]) -> float:
    if not positions:
        return 999.0
    return min(abs(x - sx) + abs(y - sy) for sx, sy in positions)


def update_from_simulation(
    pred: np.ndarray,
    sim_grid: list[list[int]],
    viewport: dict,
    observation_counts: np.ndarray,
    blend_weight: float = 0.3,
) -> np.ndarray:
    """Blend simulation observation into the prediction.

    Each sim query is one stochastic outcome. We accumulate observations
    and blend them with the prior using a weighted average.
    """
    vx, vy = viewport["x"], viewport["y"]
    vh, vw = len(sim_grid), len(sim_grid[0])

    for dy in range(vh):
        for dx in range(vw):
            y, x = vy + dy, vx + dx
            if y >= pred.shape[0] or x >= pred.shape[1]:
                continue

            code = sim_grid[dy][dx]
            cls = GRID_TO_CLASS.get(code, CLASS_EMPTY)

            # Build observation vector: one-hot with floor
            obs = np.full(NUM_CLASSES, MIN_PROB)
            obs[cls] = 1.0
            obs = obs / obs.sum()

            # Weighted running average
            n = observation_counts[y, x]
            if n == 0:
                # First observation: blend with prior
                pred[y, x] = (1 - blend_weight) * pred[y, x] + blend_weight * obs
            else:
                # Incremental average of observations, then blend with prior
                w = blend_weight * min(n + 1, 10) / 10  # Scale weight up with more obs
                pred[y, x] = (1 - w) * pred[y, x] + w * obs

            observation_counts[y, x] += 1

    return _normalize(pred)


def _normalize(pred: np.ndarray) -> np.ndarray:
    """Enforce min probability floor and renormalize."""
    pred = np.clip(pred, MIN_PROB, None)
    pred = pred / pred.sum(axis=-1, keepdims=True)
    return pred


def plan_viewports(
    width: int, height: int, settlements: list[dict], budget: int
) -> list[dict]:
    """Plan viewport queries to maximize information.

    Strategy: prioritize areas around settlements (the dynamic parts),
    then fill remaining budget with coverage of unexplored land.
    """
    viewports = []
    covered = set()

    # Phase 1: Cover settlement clusters
    for s in settlements:
        sx, sy = s["x"], s["y"]
        # Center a 15x15 viewport on the settlement
        vx = max(0, min(sx - 7, width - 15))
        vy = max(0, min(sy - 7, height - 15))
        key = (vx, vy)
        if key not in covered:
            viewports.append({"x": vx, "y": vy, "w": 15, "h": 15})
            covered.add(key)

    # Phase 2: Grid coverage for remaining budget
    step = 12  # Slight overlap between viewports
    for vy in range(0, height, step):
        for vx in range(0, width, step):
            vx_c = min(vx, width - 15)
            vy_c = min(vy, height - 15)
            key = (vx_c, vy_c)
            if key not in covered:
                viewports.append({"x": vx_c, "y": vy_c, "w": 15, "h": 15})
                covered.add(key)

    return viewports[:budget]


def main():
    # --- Step 1: Find active round ---
    active = get_active_round()
    if not active:
        print("No active round found.")
        return

    round_id = active["id"]
    round_number = active["round_number"]
    print(f"Active round: {round_number} (id={round_id})")

    # --- Step 2: Get round details and store ---
    detail = get_round_detail(round_id)
    width = detail["map_width"]
    height = detail["map_height"]
    seeds = detail["seeds_count"]
    print(f"Map: {width}x{height}, {seeds} seeds")

    store.save_round(round_number, detail)
    print(f"Saved round {round_number} to data/")

    # --- Step 3: Check budget ---
    budget_info = get_budget()
    queries_left = budget_info["queries_max"] - budget_info["queries_used"]
    print(f"Budget: {budget_info['queries_used']}/{budget_info['queries_max']} used, {queries_left} remaining")

    if queries_left <= 0:
        print("No queries left — submitting predictions from initial state only.")
        queries_left = 0

    # --- Step 4: Build predictions for each seed ---
    queries_per_seed = queries_left // seeds if seeds > 0 else 0

    for seed_idx in range(seeds):
        state = detail["initial_states"][seed_idx]
        grid = state["grid"]
        settlements = state["settlements"]
        print(f"\n--- Seed {seed_idx}: {len(settlements)} settlements ---")

        # Load any existing observations from prior runs
        existing_obs = store.list_observations(round_number, seed_idx)

        # Build prior from initial terrain
        pred = build_initial_prior(grid, settlements)
        observation_counts = np.zeros((height, width), dtype=int)

        # Replay stored observations into the prediction
        for obs in existing_obs:
            pred = update_from_simulation(
                pred, obs["grid"], obs["viewport"], observation_counts
            )
        if existing_obs:
            print(f"  Replayed {len(existing_obs)} stored observations")

        # Plan and execute new viewports
        if queries_per_seed > 0:
            viewports = plan_viewports(width, height, settlements, queries_per_seed)
            print(f"  Planned {len(viewports)} viewports (budget: {queries_per_seed})")

            for i, vp in enumerate(viewports):
                try:
                    result = simulate(
                        round_id=round_id,
                        seed_index=seed_idx,
                        viewport_x=vp["x"],
                        viewport_y=vp["y"],
                        viewport_w=vp["w"],
                        viewport_h=vp["h"],
                    )

                    # Store the observation
                    store.save_observation(round_number, seed_idx, result["viewport"], result)

                    pred = update_from_simulation(
                        pred, result["grid"], result["viewport"], observation_counts
                    )
                    remaining = result["queries_max"] - result["queries_used"]
                    print(f"  Query {i+1}: viewport ({vp['x']},{vp['y']}) — {remaining} queries left")

                    if remaining <= 0:
                        print("  Budget exhausted!")
                        break
                except Exception as e:
                    print(f"  Query {i+1} failed: {e}")
                    break

        # Ensure valid prediction
        pred = _normalize(pred)

        # Submit
        resp = submit(round_id, seed_idx, pred.tolist())
        print(f"  Submitted seed {seed_idx}: {resp}")

        # Store our prediction
        argmax = pred.argmax(axis=-1).tolist()
        confidence = pred.max(axis=-1).tolist()
        store.save_prediction(round_number, seed_idx, {
            "seed_index": seed_idx,
            "argmax_grid": argmax,
            "confidence_grid": [[round(c, 3) for c in row] for row in confidence],
        })

    print(f"\nDone! All data stored in data/round_{round_number}/")


if __name__ == "__main__":
    main()
