"""Live round submission using hybrid model.

Usage:
    uv run python task2-AstarIsland/submit_round.py

Workflow:
1. Find active round, fetch details
2. Query viewports for regime detection + coverage
3. Build hybrid predictions (static prior + simulator + observations)
4. Submit all 5 seeds
"""

import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import api
import store
from simulator.hybrid import predict, compute_observed_rate, GRID_TO_CLASS


def plan_queries(settlements: list[dict], width: int, height: int, budget: int) -> list[dict]:
    """Plan viewport queries focused on settlement clusters."""
    seen = set()
    viewports = []

    # Phase 1: Settlement-centered viewports (the important cells)
    for s in settlements:
        vx = max(0, min(s["x"] - 7, width - 15))
        vy = max(0, min(s["y"] - 7, height - 15))
        key = (vx, vy)
        if key not in seen:
            viewports.append({"x": vx, "y": vy, "w": 15, "h": 15})
            seen.add(key)

    # Phase 2: Fill remaining budget with grid coverage (skip borders)
    for vy in range(1, height - 1, 13):
        for vx in range(1, width - 1, 13):
            vx_c = min(vx, width - 15)
            vy_c = min(vy, height - 15)
            key = (vx_c, vy_c)
            if key not in seen:
                viewports.append({"x": vx_c, "y": vy_c, "w": 15, "h": 15})
                seen.add(key)

    return viewports[:budget]


def main():
    # --- Step 1: Find active round ---
    active = api.get_active_round()
    if not active:
        print("No active round. Checking for upcoming rounds...")
        for r in api.get_rounds():
            print(f"  Round {r['round_number']}: {r['status']}")
        return

    round_id = active["id"]
    rn = active["round_number"]
    print(f"Active round: {rn} (id={round_id})")
    print(f"Closes at: {active['closes_at']}")

    # --- Step 2: Get round details ---
    detail = api.get_round_detail(round_id)
    width = detail["map_width"]
    height = detail["map_height"]
    seeds = detail["seeds_count"]
    store.save_round(rn, detail)
    print(f"Map: {width}x{height}, {seeds} seeds")

    # --- Step 3: Check budget ---
    budget = api.get_budget()
    queries_left = budget["queries_max"] - budget["queries_used"]
    print(f"Budget: {budget['queries_used']}/{budget['queries_max']} ({queries_left} left)")

    if queries_left <= 0:
        print("No queries left — using stored observations only.")

    # --- Step 4: Query viewports ---
    queries_per_seed = queries_left // seeds if seeds > 0 else 0

    all_observations = {}
    for si in range(seeds):
        state = detail["initial_states"][si]
        settlements = state["settlements"]

        # Load existing observations
        existing = store.list_observations(rn, si)
        all_observations[si] = list(existing)

        if queries_per_seed > 0:
            vps = plan_queries(settlements, width, height, queries_per_seed)
            print(f"\n  Seed {si}: {len(vps)} queries planned ({len(settlements)} settlements)")

            for vp in vps:
                try:
                    result = api.simulate(
                        round_id=round_id,
                        seed_index=si,
                        viewport_x=vp["x"],
                        viewport_y=vp["y"],
                        viewport_w=vp["w"],
                        viewport_h=vp["h"],
                    )
                    store.save_observation(rn, si, result["viewport"], result)
                    all_observations[si].append(result)
                    remaining = result["queries_max"] - result["queries_used"]
                    print(f"    VP ({vp['x']:2d},{vp['y']:2d}) — {remaining} left")
                    time.sleep(0.25)

                    if remaining <= 0:
                        print("    Budget exhausted!")
                        break
                except Exception as e:
                    print(f"    VP ({vp['x']},{vp['y']}) FAILED: {e}")
                    break

    # --- Step 5: Compute observed rate from ALL observations ---
    all_obs_flat = []
    for si in range(seeds):
        all_obs_flat.extend(all_observations.get(si, []))

    if all_obs_flat:
        # Use seed 0's grid for rate computation
        global_rate = compute_observed_rate(all_obs_flat, detail["initial_states"][0]["grid"])
        print(f"\nObserved settlement rate (all seeds): {global_rate:.4f}")
    else:
        global_rate = 0.15  # default medium-high
        print(f"\nNo observations — using default rate: {global_rate:.4f}")

    # --- Step 6: Build predictions and submit ---
    print(f"\nBuilding hybrid predictions (200 MC runs per seed)...")

    for si in range(seeds):
        state = detail["initial_states"][si]
        grid = state["grid"]
        settlements = state["settlements"]
        obs = all_observations.get(si, [])

        print(f"\n  Seed {si} ({len(obs)} observations):")
        pred = predict(
            grid=grid,
            settlements=settlements,
            observations=obs,
            sim_weight=0.35,
            n_sim_runs=200,
        )

        # Sanity check
        settle_rate = (pred[:, :, 1] + pred[:, :, 2]).mean()
        n_settle_argmax = (pred.argmax(axis=-1) == 1).sum() + (pred.argmax(axis=-1) == 2).sum()
        print(f"    Avg P(settle+port): {settle_rate:.4f}, argmax settle cells: {n_settle_argmax}")

        # Submit
        resp = api.submit(round_id, si, pred.tolist())
        print(f"    Submitted: {resp}")

        # Save prediction
        store.save_prediction(rn, si, {
            "seed_index": si,
            "argmax_grid": pred.argmax(axis=-1).tolist(),
            "confidence_grid": [[round(float(c), 3) for c in row] for row in pred.max(axis=-1)],
        })
        time.sleep(1)

    print(f"\nDone! All {seeds} seeds submitted for round {rn}.")
    final_budget = api.get_budget()
    print(f"Final budget: {final_budget['queries_used']}/{final_budget['queries_max']}")


if __name__ == "__main__":
    main()
