"""Live round orchestrator for Astar Island.

Uses CatBoost as primary model + empirical bins for round-specific calibration.
Adaptive stat blending: trusts observations less for high-activity rounds.

Usage:
    python run_round.py              # Auto-detect active round
    python run_round.py <round_id>   # Specify round ID
"""

import json
import sys
import time
from pathlib import Path

import numpy as np
from catboost import CatBoostRegressor

sys.path.insert(0, str(Path(__file__).parent))

import api
import store
from astar.types import MapState, Observation, RoundStats, NUM_CLASSES, OCEAN, MOUNTAIN
from astar.features import compute_features
from astar.calibration import (
    compute_round_stats_from_ground_truth,
    compute_round_stats_from_observations,
    round_stats_to_array,
)
from astar.predictor import _build_row, _static_prediction, _is_static_cell, PROB_FLOOR
from astar.query_strategy import plan_viewports, allocate_queries
from astar.empirical_bins import build_empirical_distributions, predict_with_empirical_bins, get_bin_coverage_stats
from astar.types import Prediction

DATA_DIR = Path(__file__).parent / "data" / "rounds"
BEST_PARAMS_ALL_PATH = Path(__file__).parent / "best_params_all.json"
ADAPTIVE_PARAMS_PATH = Path(__file__).parent / "experiments" / "adaptive_stats_kfold_params.json"
SEEDS = list(range(5))
RATE_LIMIT_DELAY = 0.25

# Default adaptive params (from k-fold Optuna)
DEFAULT_ADAPTIVE = {"a": -15.28, "b": 0.58, "c": 4.41}
DEFAULT_K_PARAMS = {
    "k_base": 49, "k_low_thresh": 0.041, "k_low": 72,
    "k_mid_thresh": 0.149, "k_mid": 156,
}


def sigmoid(x):
    return 1.0 / (1.0 + np.exp(-np.clip(x, -20, 20)))


def get_training_rounds() -> list[int]:
    """Detect all rounds with ground truth data."""
    rounds = []
    for d in sorted(DATA_DIR.iterdir()):
        if d.is_dir() and d.name.startswith("round_"):
            rn = int(d.name.split("_")[1])
            if (d / "seed_0" / "ground_truth.json").exists():
                rounds.append(rn)
    return rounds


def load_catboost_params() -> dict:
    """Load CatBoost params from best_params_all.json, fallback to defaults."""
    if BEST_PARAMS_ALL_PATH.exists():
        with open(BEST_PARAMS_ALL_PATH) as f:
            all_params = json.load(f)
        if "catboost" in all_params:
            return all_params["catboost"]
    return {"iterations": 200, "depth": 5, "learning_rate": 0.1, "l2_leaf_reg": 6.0, "subsample": 0.8}


def load_adaptive_params() -> tuple[dict, dict]:
    """Load adaptive stat blending and k params."""
    if ADAPTIVE_PARAMS_PATH.exists():
        with open(ADAPTIVE_PARAMS_PATH) as f:
            data = json.load(f)
        return data.get("adaptive_stats", DEFAULT_ADAPTIVE), data.get("k_params", DEFAULT_K_PARAMS)
    return DEFAULT_ADAPTIVE, DEFAULT_K_PARAMS


def compute_historical_avg_stats(training_rounds: list[int]) -> RoundStats:
    """Compute average round stats across all training rounds."""
    all_stats = []
    for rn in training_rounds:
        for si in SEEDS:
            sd = DATA_DIR / f"round_{rn}" / f"seed_{si}"
            with open(sd / "initial_state.json") as f:
                raw = json.load(f)
            with open(sd / "ground_truth.json") as f:
                gt_raw = json.load(f)
            state = MapState(grid=np.array(raw["grid"]), settlements=raw["settlements"])
            gt = np.array(gt_raw["ground_truth"])
            all_stats.append(compute_round_stats_from_ground_truth(gt, state))

    fields = ["ruin_rate", "settlement_rate", "port_rate", "expansion_distance",
              "forest_rate", "empty_rate", "settlement_to_ruin_ratio"]
    return RoundStats(**{f: np.mean([getattr(s, f) for s in all_stats]) for f in fields})


def blend_stats(obs_stats: RoundStats, hist_stats: RoundStats, obs_weight: float) -> RoundStats:
    """Blend observation stats and historical stats."""
    fields = ["ruin_rate", "settlement_rate", "port_rate", "expansion_distance",
              "forest_rate", "empty_rate", "settlement_to_ruin_ratio"]
    return RoundStats(**{
        f: obs_weight * getattr(obs_stats, f) + (1 - obs_weight) * getattr(hist_stats, f)
        for f in fields
    })


def load_training_data(training_rounds: list[int]):
    """Build training arrays from historical ground truth."""
    X_rows, y_rows, w_rows = [], [], []

    for rn in training_rounds:
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
        stats_arr = round_stats_to_array(avg_stats)

        for state, gt in round_data:
            features = compute_features(state)
            h, w = gt.shape[:2]
            eps = 1e-12
            entropy = -np.sum(gt * np.log(gt + eps), axis=-1)
            for r in range(h):
                for c in range(w):
                    if _is_static_cell(state.grid[r, c], gt[r, c]):
                        continue
                    row = _build_row(features[r, c], stats_arr)
                    X_rows.append(row)
                    y_rows.append(gt[r, c])
                    w_rows.append(entropy[r, c] + 0.1)

    return (
        np.array(X_rows, dtype=np.float32),
        np.array(y_rows, dtype=np.float32),
        np.array(w_rows, dtype=np.float32),
    )


def train_catboost(X, y, w, params):
    """Train 6 CatBoost regressors (one per class)."""
    models = []
    for c in range(NUM_CLASSES):
        target = y[:, c]
        if target.max() - target.min() < 1e-8:
            models.append(None)
            continue
        m = CatBoostRegressor(loss_function="RMSE", verbose=0, thread_count=-1, **params)
        m.fit(X, target, sample_weight=w)
        models.append(m)
    return models


def predict_catboost(models, X):
    """Predict with CatBoost ensemble, returns (N, 6)."""
    return np.column_stack([
        np.zeros(len(X), dtype=np.float32) if m is None else m.predict(X).astype(np.float32)
        for m in models
    ])


def predict_map(models, state, round_stats):
    """Generate full 40x40x6 prediction for a map."""
    features = compute_features(state)
    stats_arr = round_stats_to_array(round_stats)
    h, w = state.grid.shape
    probs = np.zeros((h, w, NUM_CLASSES), dtype=np.float32)

    dynamic_indices = []
    X_rows = []

    for r in range(h):
        for c in range(w):
            sp = _static_prediction(state.grid[r, c])
            if sp is not None:
                probs[r, c] = sp
            else:
                dynamic_indices.append((r, c))
                X_rows.append(_build_row(features[r, c], stats_arr))

    if X_rows:
        X = np.array(X_rows, dtype=np.float32)
        preds = predict_catboost(models, X)
        for (r, c), pred in zip(dynamic_indices, preds):
            probs[r, c] = pred

    probs = np.maximum(probs, PROB_FLOOR)
    probs = probs / probs.sum(axis=-1, keepdims=True)
    return Prediction(probs=probs)


def fetch_round_states(round_detail: dict) -> list[MapState]:
    states = []
    for init_state in round_detail["initial_states"]:
        states.append(MapState(
            grid=np.array(init_state["grid"]),
            settlements=init_state["settlements"],
        ))
    return states


def execute_queries(round_id, states, round_number):
    allocation = allocate_queries(states)
    print(f"  Query allocation: {allocation} (total={sum(allocation)})")

    all_observations = [[] for _ in range(len(states))]

    for si, (state, n_queries) in enumerate(zip(states, allocation)):
        viewports = plan_viewports(state, n_queries)
        print(f"  Seed {si}: {n_queries} queries, viewports: {viewports[:3]}{'...' if len(viewports) > 3 else ''}")

        for vx, vy in viewports:
            try:
                result = api.simulate(
                    round_id=round_id, seed_index=si,
                    viewport_x=vx, viewport_y=vy,
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

    # Step 1: Train CatBoost
    print("\n[1/5] Training CatBoost on historical data...")
    training_rounds = get_training_rounds()
    cat_params = load_catboost_params()
    print(f"  Params: {cat_params}")
    X, y, w = load_training_data(training_rounds)
    models = train_catboost(X, y, w, cat_params)
    print(f"  Trained on {len(X)} cells from {len(training_rounds)} rounds ({training_rounds})")

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
        print("  No queries remaining — loading stored observations")
        all_observations = [[] for _ in states]
        for si in range(len(states)):
            for raw in store.list_observations(round_number, si):
                if isinstance(raw, list):
                    raw = raw[0]
                vp = raw["viewport"]
                all_observations[si].append(Observation(
                    grid=np.array(raw["grid"]),
                    settlements=raw.get("settlements", []),
                    viewport=(vp["x"], vp["y"], vp["w"], vp["h"]),
                    seed_index=si,
                ))
        stored_count = sum(len(obs) for obs in all_observations)
        print(f"  Loaded {stored_count} stored observations")
    else:
        all_observations = execute_queries(round_id, states, round_number)

    all_obs_flat = []
    for obs_list in all_observations:
        all_obs_flat.extend(obs_list)

    # Step 4: Adaptive stat blending + empirical bins + predict
    print("\n[4/5] Generating predictions...")

    # Load adaptive params
    adapt_params, k_params = load_adaptive_params()
    hist_stats = compute_historical_avg_stats(training_rounds)

    if all_obs_flat:
        obs_stats = compute_round_stats_from_observations(all_obs_flat, states[0])
        bin_dists = build_empirical_distributions(all_obs_flat, states)
        bin_counts = get_bin_coverage_stats(all_obs_flat, states)

        # Adaptive blending: trust observations less for high-activity rounds
        obs_settle = obs_stats.settlement_rate
        hist_settle = hist_stats.settlement_rate
        divergence = abs(obs_settle - hist_settle) / (hist_settle + 1e-6)
        obs_weight = sigmoid(
            adapt_params["a"] * obs_settle +
            adapt_params["b"] * divergence +
            adapt_params["c"]
        )

        blended_stats = blend_stats(obs_stats, hist_stats, obs_weight)

        print(f"  Empirical bins: {len(bin_dists)} bins with data")
        print(f"  OBS stats:  settle={obs_stats.settlement_rate:.3f}, ruin={obs_stats.ruin_rate:.3f}")
        print(f"  HIST stats: settle={hist_stats.settlement_rate:.3f}, ruin={hist_stats.ruin_rate:.3f}")
        print(f"  Blended:    settle={blended_stats.settlement_rate:.3f} (obs_weight={obs_weight:.3f})")
    else:
        blended_stats = hist_stats
        bin_dists = {}
        bin_counts = {}
        print(f"  No observations — using historical avg stats")
        print(f"  HIST stats: settle={hist_stats.settlement_rate:.3f}, ruin={hist_stats.ruin_rate:.3f}")

    # Adaptive k based on blended settlement rate
    settle = blended_stats.settlement_rate
    if settle < k_params["k_low_thresh"]:
        k = k_params["k_low"]
    elif settle < k_params["k_mid_thresh"]:
        k = k_params["k_mid"]
    else:
        k = k_params["k_base"]

    # Predict and submit each seed
    for si, state in enumerate(states):
        base_pred = predict_map(models, state, blended_stats)

        if bin_dists:
            if si == 0:
                print(f"    k={k:.0f} (settle_rate={settle:.3f})")
            final_pred = predict_with_empirical_bins(
                state, bin_dists, base_pred, bin_counts=bin_counts, k=k
            )
        else:
            final_pred = base_pred

        probs = final_pred.probs

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
        if current and current.get("round_score"):
            print(f"  Round score: {current['round_score']}")
    except Exception:
        pass


if __name__ == "__main__":
    main()
