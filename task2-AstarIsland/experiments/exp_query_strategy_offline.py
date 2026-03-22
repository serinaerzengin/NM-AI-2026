"""Experiment: query strategy — coverage vs repetition (offline simulation).

Uses ground truth distributions to sample synthetic observations, simulating
what different query allocation strategies would produce.

Key question: with 50 queries across 5 maps, is it better to:
  A) Maximize spatial coverage (current: ~10 unique viewports per map)
  B) Repeat fewer viewports to get better empirical distributions
  C) Hybrid: some coverage + concentrated repeats on high-interest areas

We sample from ground truth to simulate stochastic observations, build
empirical bins from those synthetic observations, and score against ground truth.
Averaged over many trials to reduce variance.
"""

import json
import sys
from pathlib import Path
from collections import defaultdict

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

from astar.types import (
    MapState, Observation, Prediction, RoundStats, NUM_CLASSES,
    OCEAN, MOUNTAIN, TERRAIN_TO_CLASS, CLASS_EMPTY,
)
from astar.features import compute_features
from astar.calibration import (
    compute_round_stats_from_ground_truth,
    compute_round_stats_from_observations,
    round_stats_to_array,
)
from astar.scoring import score_prediction
from astar.predictor import _build_row, _static_prediction, _is_static_cell
from astar.empirical_bins import (
    build_empirical_distributions, predict_with_empirical_bins,
    get_bin_coverage_stats,
)
from astar.query_strategy import plan_viewports, allocate_queries, _compute_interest_map
from catboost import CatBoostRegressor
import store

DATA_DIR = Path(__file__).parent.parent / "data" / "rounds"
BEST_PARAMS_PATH = Path(__file__).parent.parent / "best_params_all.json"
SEEDS = list(range(5))
VIEWPORT_SIZE = 15
N_TRIALS = 20  # number of random trials per strategy to reduce variance


# ── Synthetic observation sampling ─────────────────────────────────────

# Map from prediction class back to terrain codes (for sampling)
CLASS_TO_TERRAIN = {
    0: 0,   # Empty
    1: 1,   # Settlement
    2: 2,   # Port
    3: 3,   # Ruin
    4: 4,   # Forest
    5: 5,   # Mountain
}


def sample_observation(gt, state, vx, vy, seed_index, rng):
    """Sample a synthetic observation from ground truth distributions.

    For each cell in the viewport, sample one terrain outcome from the
    ground truth probability distribution. This simulates one stochastic
    simulation run.
    """
    vw, vh = VIEWPORT_SIZE, VIEWPORT_SIZE
    grid = np.zeros((vh, vw), dtype=int)

    for r in range(vh):
        for c in range(vw):
            abs_y, abs_x = vy + r, vx + c
            if abs_y >= 40 or abs_x >= 40:
                grid[r, c] = OCEAN
                continue
            probs = gt[abs_y, abs_x]
            cls = rng.choice(NUM_CLASSES, p=probs)
            grid[r, c] = CLASS_TO_TERRAIN[cls]

    # Generate dummy settlement data (we don't use settlement stats in base pipeline)
    settlements = []
    for r in range(vh):
        for c in range(vw):
            if grid[r, c] == 1:  # Settlement
                settlements.append({
                    "x": vx + c, "y": vy + r,
                    "population": rng.uniform(0.5, 3.0),
                    "food": rng.uniform(0.1, 1.0),
                    "wealth": rng.uniform(0.1, 1.0),
                    "defense": rng.uniform(0.1, 1.0),
                    "has_port": False, "alive": True, "owner_id": 0,
                })
            elif grid[r, c] == 2:  # Port
                settlements.append({
                    "x": vx + c, "y": vy + r,
                    "population": rng.uniform(0.5, 3.0),
                    "food": rng.uniform(0.1, 1.0),
                    "wealth": rng.uniform(0.1, 1.0),
                    "defense": rng.uniform(0.1, 1.0),
                    "has_port": True, "alive": True, "owner_id": 0,
                })

    return Observation(
        grid=grid,
        settlements=settlements,
        viewport=(vx, vy, vw, vh),
        seed_index=seed_index,
    )


# ── Query strategies ───────────────────────────────────────────────────

def strategy_coverage(states, total_queries=50):
    """Current strategy: maximize coverage with greedy non-overlapping viewports."""
    allocation = allocate_queries(states, total_queries)
    viewports_per_seed = []
    for si, (state, n_q) in enumerate(zip(states, allocation)):
        vps = plan_viewports(state, n_q)
        viewports_per_seed.append(vps)
    return viewports_per_seed


def strategy_repeat_top_n(states, n_unique=2, total_queries=50):
    """Pick top N interest viewports per map, distribute queries as repeats."""
    allocation = allocate_queries(states, total_queries)
    viewports_per_seed = []
    for si, (state, n_q) in enumerate(zip(states, allocation)):
        # Get top n_unique viewports by interest
        top_vps = plan_viewports(state, n_unique)
        # Distribute n_q queries across those viewports round-robin
        vps = []
        for i in range(n_q):
            vps.append(top_vps[i % len(top_vps)])
        viewports_per_seed.append(vps)
    return viewports_per_seed


def strategy_hybrid(states, n_coverage=1, total_queries=50):
    """Hybrid: allocate n_coverage unique viewports per map for coverage,
    then repeat the best viewport with remaining queries."""
    allocation = allocate_queries(states, total_queries)
    viewports_per_seed = []
    for si, (state, n_q) in enumerate(zip(states, allocation)):
        top_vps = plan_viewports(state, max(n_coverage + 1, n_q))
        vps = []
        # First: coverage viewports (1 each)
        for i in range(min(n_coverage, n_q)):
            vps.append(top_vps[i])
        # Rest: repeat best viewport
        for _ in range(n_q - len(vps)):
            vps.append(top_vps[0])
        viewports_per_seed.append(vps)
    return viewports_per_seed


def strategy_concentrate_maps(states, n_maps=3, total_queries=50):
    """Concentrate all queries on the N most interesting maps, skip others.
    Use coverage within selected maps."""
    interest_scores = []
    for state in states:
        interest = _compute_interest_map(state)
        interest_scores.append(interest.sum())

    # Pick top n_maps
    ranked = np.argsort(interest_scores)[::-1]
    selected = sorted(ranked[:n_maps])

    per_map = total_queries // n_maps
    remainder = total_queries - per_map * n_maps

    viewports_per_seed = [[] for _ in states]
    for i, si in enumerate(selected):
        n_q = per_map + (1 if i < remainder else 0)
        vps = plan_viewports(states[si], n_q)
        viewports_per_seed[si] = vps

    return viewports_per_seed


def strategy_concentrate_and_repeat(states, n_maps=3, n_unique=2, total_queries=50):
    """Concentrate on N maps, and within each map repeat top viewports."""
    interest_scores = []
    for state in states:
        interest = _compute_interest_map(state)
        interest_scores.append(interest.sum())

    ranked = np.argsort(interest_scores)[::-1]
    selected = sorted(ranked[:n_maps])

    per_map = total_queries // n_maps
    remainder = total_queries - per_map * n_maps

    viewports_per_seed = [[] for _ in states]
    for i, si in enumerate(selected):
        n_q = per_map + (1 if i < remainder else 0)
        top_vps = plan_viewports(states[si], n_unique)
        vps = []
        for j in range(n_q):
            vps.append(top_vps[j % len(top_vps)])
        viewports_per_seed[si] = vps

    return viewports_per_seed


# ── Evaluation ─────────────────────────────────────────────────────────

def load_map(rn, si):
    sd = DATA_DIR / f"round_{rn}" / f"seed_{si}"
    with open(sd / "initial_state.json") as f:
        raw = json.load(f)
    with open(sd / "ground_truth.json") as f:
        gt_raw = json.load(f)
    return (
        MapState(grid=np.array(raw["grid"]), settlements=raw["settlements"]),
        np.array(gt_raw["ground_truth"]),
    )


def load_catboost_params():
    if BEST_PARAMS_PATH.exists():
        with open(BEST_PARAMS_PATH) as f:
            return json.load(f).get("catboost", {})
    return {"iterations": 200, "depth": 5, "learning_rate": 0.1}


def get_all_rounds():
    rounds = []
    for d in sorted(DATA_DIR.iterdir()):
        if d.is_dir() and d.name.startswith("round_"):
            rn = int(d.name.split("_")[1])
            if (d / "seed_0" / "ground_truth.json").exists():
                rounds.append(rn)
    return rounds


def train_catboost(training_rounds):
    cat_params = load_catboost_params()
    X_rows, y_rows, w_rows = [], [], []

    for rn in training_rounds:
        round_stats = []
        round_data = []
        for si in SEEDS:
            state, gt = load_map(rn, si)
            round_stats.append(compute_round_stats_from_ground_truth(gt, state))
            round_data.append((state, gt))

        fields = ["ruin_rate", "settlement_rate", "port_rate", "expansion_distance",
                  "forest_rate", "empty_rate", "settlement_to_ruin_ratio"]
        avg_stats = RoundStats(**{f: np.mean([getattr(s, f) for s in round_stats]) for f in fields})
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

    X = np.array(X_rows, dtype=np.float32)
    y = np.array(y_rows, dtype=np.float32)
    w = np.array(w_rows, dtype=np.float32)

    models = []
    for c in range(NUM_CLASSES):
        target = y[:, c]
        if target.max() - target.min() < 1e-8:
            models.append(None)
            continue
        m = CatBoostRegressor(loss_function="RMSE", verbose=0, thread_count=-1, **cat_params)
        m.fit(X, target, sample_weight=w)
        models.append(m)
    return models


def predict_map_catboost(models, state, round_stats):
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
        preds = np.column_stack([
            np.zeros(len(X)) if m is None else m.predict(X)
            for m in models
        ])
        for (r, c), pred in zip(dynamic_indices, preds):
            probs[r, c] = pred

    probs = np.maximum(probs, 0.0005)
    probs = probs / probs.sum(axis=-1, keepdims=True)
    return Prediction(probs=probs)


def evaluate_strategy(strategy_fn, strategy_name, val_round, models, states, gts,
                      obs_stats_from_gt, k=49, n_trials=N_TRIALS):
    """Evaluate a query strategy over multiple random trials."""
    rng = np.random.default_rng(42)
    trial_scores = []

    for trial in range(n_trials):
        # Generate viewports for this strategy
        viewports_per_seed = strategy_fn(states)

        # Sample synthetic observations
        all_obs = []
        for si, vps in enumerate(viewports_per_seed):
            for vx, vy in vps:
                obs = sample_observation(gts[si], states[si], vx, vy, si, rng)
                all_obs.append(obs)

        if not all_obs:
            # Strategy skipped some seeds — those get model-only predictions
            pass

        # Build empirical bins from synthetic observations
        obs_stats = compute_round_stats_from_observations(all_obs, states[0]) if all_obs else obs_stats_from_gt
        bin_dists = build_empirical_distributions(all_obs, states) if all_obs else {}
        bin_counts = get_bin_coverage_stats(all_obs, states) if all_obs else {}

        # Predict and score each seed
        seed_scores = []
        for si in range(len(states)):
            base_pred = predict_map_catboost(models, states[si], obs_stats)
            if bin_dists:
                final_pred = predict_with_empirical_bins(
                    states[si], bin_dists, base_pred,
                    bin_counts=bin_counts, k=k,
                )
            else:
                final_pred = base_pred
            seed_scores.append(score_prediction(final_pred.probs, gts[si]))

        trial_scores.append(np.mean(seed_scores))

    return {
        "mean": np.mean(trial_scores),
        "std": np.std(trial_scores),
        "min": np.min(trial_scores),
        "max": np.max(trial_scores),
        "trials": trial_scores,
    }


def main():
    all_rounds = get_all_rounds()
    # Test on a subset of rounds to keep runtime reasonable
    test_rounds = [8, 9, 10, 11, 14, 15]
    test_rounds = [r for r in test_rounds if r in all_rounds]

    strategies = {
        "A: coverage (current)":        lambda states: strategy_coverage(states),
        "B: repeat top-2":              lambda states: strategy_repeat_top_n(states, n_unique=2),
        "C: repeat top-3":              lambda states: strategy_repeat_top_n(states, n_unique=3),
        "D: hybrid (2 cover + repeat)": lambda states: strategy_hybrid(states, n_coverage=2),
        "E: hybrid (3 cover + repeat)": lambda states: strategy_hybrid(states, n_coverage=3),
        "F: 3 maps, coverage":          lambda states: strategy_concentrate_maps(states, n_maps=3),
        "G: 3 maps, repeat top-2":      lambda states: strategy_concentrate_and_repeat(states, n_maps=3, n_unique=2),
    }

    print(f"Testing {len(strategies)} strategies on rounds {test_rounds}")
    print(f"Using {N_TRIALS} trials per strategy per round\n")

    # Aggregate results
    all_results = {name: [] for name in strategies}

    for val_rn in test_rounds:
        train_rounds = [r for r in all_rounds if r != val_rn]
        print(f"── Round {val_rn} (train on {len(train_rounds)} rounds) ──")

        models = train_catboost(train_rounds)

        states = []
        gts = []
        for si in SEEDS:
            state, gt = load_map(val_rn, si)
            states.append(state)
            gts.append(gt)

        # Ground truth stats for fallback
        gt_stats = []
        for si in SEEDS:
            gt_stats.append(compute_round_stats_from_ground_truth(gts[si], states[si]))
        fields = ["ruin_rate", "settlement_rate", "port_rate", "expansion_distance",
                  "forest_rate", "empty_rate", "settlement_to_ruin_ratio"]
        obs_stats_gt = RoundStats(**{f: np.mean([getattr(s, f) for s in gt_stats]) for f in fields})

        for name, strategy_fn in strategies.items():
            result = evaluate_strategy(
                strategy_fn, name, val_rn, models, states, gts,
                obs_stats_gt, k=49,
            )
            all_results[name].append(result["mean"])
            print(f"  {name:35s}  {result['mean']:.2f} ± {result['std']:.2f}  (range: {result['min']:.2f}-{result['max']:.2f})")

        print()

    # Final summary
    print(f"\n{'═' * 70}")
    print(f"  SUMMARY: Average across rounds {test_rounds}")
    print(f"{'═' * 70}")

    baseline_avg = np.mean(all_results["A: coverage (current)"])
    ranked = sorted(all_results.items(), key=lambda x: np.mean(x[1]), reverse=True)

    for name, scores in ranked:
        avg = np.mean(scores)
        diff = avg - baseline_avg
        sign = "+" if diff >= 0 else ""
        per_round = "  ".join(f"{s:.1f}" for s in scores)
        print(f"  {name:35s}  avg={avg:.2f}  ({sign}{diff:.2f})  [{per_round}]")

    print(f"{'═' * 70}")


if __name__ == "__main__":
    main()
