"""Live round orchestrator for Astar Island.

Usage:
    python run_round.py              # Auto-detect active round
    python run_round.py <round_id>   # Specify round ID
"""

import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))

import api
import store
from astar.types import MapState, Observation, RoundStats, NUM_CLASSES
from astar.calibration import (
    compute_round_stats_from_ground_truth,
    compute_round_stats_from_observations,
)
from astar.predictor import Predictor
from astar.query_strategy import plan_viewports, allocate_queries
from astar.empirical_bins import build_empirical_distributions, predict_with_empirical_bins, get_bin_coverage_stats

DATA_DIR = Path(__file__).parent / "data" / "rounds"
BEST_PARAMS_PATH = Path(__file__).parent / "best_params.json"
TRAINING_ROUNDS = list(range(1, 8))  # Rounds 1-7
SEEDS = list(range(5))
RATE_LIMIT_DELAY = 0.25


def load_best_params() -> dict | None:
    if BEST_PARAMS_PATH.exists():
        with open(BEST_PARAMS_PATH) as f:
            return json.load(f)
    return None


def load_training_data() -> tuple[list[MapState], list[np.ndarray], list[RoundStats]]:
    """Load all historical training data (rounds 1-6)."""
    states, gts, stats_list = [], [], []

    for rn in TRAINING_ROUNDS:
        round_stats_all = []
        round_data = []
        for si in SEEDS:
            seed_dir = DATA_DIR / f"round_{rn}" / f"seed_{si}"
            with open(seed_dir / "initial_state.json") as f:
                raw = json.load(f)
            with open(seed_dir / "ground_truth.json") as f:
                gt_raw = json.load(f)
            state = MapState(grid=np.array(raw["grid"]), settlements=raw["settlements"])
            gt = np.array(gt_raw["ground_truth"])
            round_stats_all.append(compute_round_stats_from_ground_truth(gt, state))
            round_data.append((state, gt))

        avg_stats = RoundStats(
            ruin_rate=np.mean([s.ruin_rate for s in round_stats_all]),
            settlement_rate=np.mean([s.settlement_rate for s in round_stats_all]),
            port_rate=np.mean([s.port_rate for s in round_stats_all]),
            expansion_distance=np.mean([s.expansion_distance for s in round_stats_all]),
            forest_rate=np.mean([s.forest_rate for s in round_stats_all]),
            empty_rate=np.mean([s.empty_rate for s in round_stats_all]),
            settlement_to_ruin_ratio=np.mean([s.settlement_to_ruin_ratio for s in round_stats_all]),
        )

        for state, gt in round_data:
            states.append(state)
            gts.append(gt)
            stats_list.append(avg_stats)

    return states, gts, stats_list


def fetch_round_states(round_detail: dict) -> list[MapState]:
    states = []
    for init_state in round_detail["initial_states"]:
        states.append(MapState(
            grid=np.array(init_state["grid"]),
            settlements=init_state["settlements"],
        ))
    return states


def execute_queries(
    round_id: str,
    states: list[MapState],
    round_number: int,
) -> list[list[Observation]]:
    """Execute simulation queries and return observations per seed."""
    allocation = allocate_queries(states)
    print(f"  Query allocation: {allocation} (total={sum(allocation)})")

    all_observations = [[] for _ in range(len(states))]

    for si, (state, n_queries) in enumerate(zip(states, allocation)):
        viewports = plan_viewports(state, n_queries)
        print(f"  Seed {si}: {n_queries} queries, viewports: {viewports[:3]}{'...' if len(viewports) > 3 else ''}")

        for vx, vy in viewports:
            try:
                result = api.simulate(
                    round_id=round_id,
                    seed_index=si,
                    viewport_x=vx,
                    viewport_y=vy,
                )
                obs = Observation(
                    grid=np.array(result["grid"]),
                    settlements=result.get("settlements", []),
                    viewport=(vx, vy, 15, 15),
                    seed_index=si,
                )
                all_observations[si].append(obs)
                store.save_observation(round_number, si, {"x": vx, "y": vy}, result)
                time.sleep(RATE_LIMIT_DELAY)
            except Exception as e:
                print(f"    Query failed at ({vx},{vy}): {e}")

    return all_observations


def main():
    # Determine round
    if len(sys.argv) > 1:
        round_id = sys.argv[1]
        detail = api.get_round_detail(round_id)
    else:
        active = api.get_active_round()
        if active is None:
            print("No active round found.")
            return
        round_id = active["id"]
        detail = api.get_round_detail(round_id)

    round_number = detail["round_number"]
    print(f"=== Round {round_number} (id={round_id}) ===")
    print(f"  Status: {detail['status']}")
    print(f"  Seeds: {detail.get('seeds_count', len(detail.get('initial_states', [])))}")

    store.save_round(round_number, detail)

    # Step 1: Train model
    print("\n[1/5] Training model on historical data...")
    best_params = load_best_params()
    if best_params:
        print(f"  Using optimized params from {BEST_PARAMS_PATH.name}")
    train_states, train_gts, train_stats = load_training_data()
    predictor = Predictor(params=best_params)
    predictor.fit(train_states, train_gts, train_stats)
    print(f"  Trained on {len(train_states)} maps ({len(TRAINING_ROUNDS)} rounds)")

    # Step 2: Get current round states
    print("\n[2/5] Loading current round initial states...")
    states = fetch_round_states(detail)
    print(f"  {len(states)} maps loaded")

    # Step 3: Execute queries
    print("\n[3/5] Executing simulation queries...")
    budget = api.get_budget()
    queries_used = budget.get("queries_used", 0)
    queries_max = budget.get("queries_max", 50)
    remaining = queries_max - queries_used
    print(f"  Budget: {queries_used}/{queries_max} used, {remaining} remaining")

    if remaining <= 0:
        print("  No queries remaining — using model predictions only")
        all_observations = [[] for _ in states]
    else:
        all_observations = execute_queries(round_id, states, round_number)

    # Flatten all observations for empirical bins
    all_obs_flat = []
    for obs_list in all_observations:
        all_obs_flat.extend(obs_list)

    # Step 4: Build empirical bins from all observations
    print("\n[4/5] Generating predictions...")

    # Compute round stats from all observations combined
    if all_obs_flat:
        combined_round_stats = compute_round_stats_from_observations(all_obs_flat, states[0])
        # Build empirical bins across ALL seeds' observations
        bin_dists = build_empirical_distributions(all_obs_flat, states)
        bin_counts = get_bin_coverage_stats(all_obs_flat, states)
        print(f"  Empirical bins: {len(bin_dists)} bins with data")
        print(f"  Round stats: settle={combined_round_stats.settlement_rate:.3f}, "
              f"ruin={combined_round_stats.ruin_rate:.3f}")
    else:
        combined_round_stats = RoundStats(
            ruin_rate=np.mean([s.ruin_rate for s in train_stats]),
            settlement_rate=np.mean([s.settlement_rate for s in train_stats]),
            port_rate=np.mean([s.port_rate for s in train_stats]),
            expansion_distance=np.mean([s.expansion_distance for s in train_stats]),
            forest_rate=np.mean([s.forest_rate for s in train_stats]),
            empty_rate=np.mean([s.empty_rate for s in train_stats]),
            settlement_to_ruin_ratio=np.mean([s.settlement_to_ruin_ratio for s in train_stats]),
        )
        bin_dists = {}

    # Predict and submit each seed
    for si, state in enumerate(states):
        # Base model prediction
        base_pred = predictor.predict(state, combined_round_stats)

        # Blend with empirical bins
        if bin_dists:
            # Adaptive k: low-activity rounds → trust bins more (lower k)
            base_k = best_params.get("k", 150) if best_params else 150
            settle_rate = combined_round_stats.settlement_rate
            if settle_rate < 0.05:
                k = 50  # Low activity: bins are very reliable
            elif settle_rate < 0.10:
                k = min(base_k, 100)
            else:
                k = base_k
            print(f"    k={k:.0f} (settle_rate={settle_rate:.3f})")
            final_pred = predict_with_empirical_bins(
                state, bin_dists, base_pred, bin_counts=bin_counts, k=k
            )
        else:
            final_pred = base_pred

        probs = final_pred.probs

        # Submit
        print(f"  Seed {si}: submitting...")
        try:
            result = api.submit(round_id, si, probs.tolist())
            print(f"    Submitted OK")
            store.save_prediction(round_number, si, {
                "argmax_grid": probs.argmax(axis=-1).tolist(),
                "confidence_grid": probs.max(axis=-1).tolist(),
            })
        except Exception as e:
            print(f"    Submit failed: {e}")

        time.sleep(0.6)

    # Step 5: Done
    print("\n[5/5] Done! Check scores at https://app.ainm.no")
    try:
        my_rounds = api.get_my_rounds()
        current = next((r for r in my_rounds if r["id"] == round_id), None)
        if current and current.get("scores"):
            print(f"  Scores: {current['scores']}")
    except Exception:
        pass


if __name__ == "__main__":
    main()
