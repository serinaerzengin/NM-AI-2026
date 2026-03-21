"""Experiment: Weight training rounds by similarity to the current round.

Instead of treating all training rounds equally, upweight rounds with similar
hidden parameters (as estimated from observation stats) and downweight dissimilar ones.

Uses leave-one-round-out k-fold on rounds with observations (R6-R12).
Optuna optimizes the weighting function parameters.
"""

import json
import sys
from pathlib import Path

import numpy as np
import optuna

sys.path.insert(0, str(Path(__file__).parent.parent))

from astar.types import MapState, Observation, RoundStats, NUM_CLASSES, OCEAN, MOUNTAIN
from astar.features import compute_features
from astar.calibration import (
    compute_round_stats_from_ground_truth,
    compute_round_stats_from_observations,
    round_stats_to_array,
)
from astar.predictor import _build_row, _static_prediction, _is_static_cell
from astar.scoring import score_prediction
from astar.empirical_bins import (
    build_empirical_distributions, get_bin_coverage_stats,
    _cell_bin_key, _cell_bin_key_coarse,
)
from catboost import CatBoostRegressor
import store

DATA_DIR = Path(__file__).parent.parent / "data" / "rounds"
SEEDS = list(range(5))
PROB_FLOOR = 0.0005

ALL_ROUNDS = list(range(1, 14))
ROUNDS_WITH_OBS = [6, 7, 8, 9, 10, 11, 12]

_cache = {}


def load_map(rn, si):
    key = (rn, si)
    if key not in _cache:
        sd = DATA_DIR / f"round_{rn}" / f"seed_{si}"
        with open(sd / "initial_state.json") as f:
            raw = json.load(f)
        with open(sd / "ground_truth.json") as f:
            gt_raw = json.load(f)
        _cache[key] = (
            MapState(grid=np.array(raw["grid"]), settlements=raw["settlements"]),
            np.array(gt_raw["ground_truth"]),
        )
    return _cache[key]


def round_stats_avg(rn):
    stats = []
    for si in SEEDS:
        s, gt = load_map(rn, si)
        stats.append(compute_round_stats_from_ground_truth(gt, s))
    fields = ["ruin_rate", "settlement_rate", "port_rate", "expansion_distance",
              "forest_rate", "empty_rate", "settlement_to_ruin_ratio"]
    return RoundStats(**{f: np.mean([getattr(s, f) for s in stats]) for f in fields})


def load_obs(rn, si):
    out = []
    for raw in store.list_observations(rn, si):
        if isinstance(raw, list):
            raw = raw[0]
        vp = raw["viewport"]
        out.append(Observation(
            grid=np.array(raw["grid"]), settlements=raw.get("settlements", []),
            viewport=(vp["x"], vp["y"], vp["w"], vp["h"]), seed_index=si,
        ))
    return out


def sigmoid(x):
    return 1.0 / (1.0 + np.exp(-np.clip(x, -20, 20)))


def stats_to_vec(stats):
    """Convert RoundStats to a comparable vector."""
    return np.array([
        stats.settlement_rate,
        stats.ruin_rate,
        stats.port_rate,
        stats.expansion_distance / 3.0,  # normalize to ~[0,1]
    ])


def compute_round_similarity(target_stats, train_stats, temperature):
    """Compute similarity weight between target round and a training round.

    Returns weight in [min_weight, 1.0] based on Gaussian similarity.
    """
    target_vec = stats_to_vec(target_stats)
    train_vec = stats_to_vec(train_stats)
    dist_sq = np.sum((target_vec - train_vec) ** 2)
    return np.exp(-dist_sq / (2 * temperature ** 2))


# ── Precompute per-round data ────────────────────────────────────────────

def precompute_round_data():
    """Precompute features/targets per round for flexible reweighting."""
    round_data = {}

    for rn in ALL_ROUNDS:
        stats = round_stats_avg(rn)
        stats_arr = round_stats_to_array(stats)

        X_rows, y_rows, w_rows = [], [], []
        for si in SEEDS:
            state, gt = load_map(rn, si)
            features = compute_features(state)
            eps = 1e-12
            entropy = -np.sum(gt * np.log(gt + eps), axis=-1)
            for r in range(40):
                for c in range(40):
                    if _is_static_cell(state.grid[r, c], gt[r, c]):
                        continue
                    X_rows.append(_build_row(features[r, c], stats_arr))
                    y_rows.append(gt[r, c])
                    w_rows.append(entropy[r, c] + 0.1)

        round_data[rn] = {
            "X": np.array(X_rows, np.float32),
            "y": np.array(y_rows, np.float32),
            "w": np.array(w_rows, np.float32),
            "stats": stats,
            "n_cells": len(X_rows),
        }

    # Validation data (observations + bins)
    val_data = {}
    for rn in ROUNDS_WITH_OBS:
        states, all_obs = [], []
        for si in SEEDS:
            state, _ = load_map(rn, si)
            states.append(state)
            all_obs.extend(load_obs(rn, si))

        if not all_obs:
            continue

        obs_stats = compute_round_stats_from_observations(all_obs, states[0])
        bin_dists = build_empirical_distributions(all_obs, states)
        bin_counts = get_bin_coverage_stats(all_obs, states)

        val_seeds = []
        for si in SEEDS:
            state, gt = load_map(rn, si)
            features = compute_features(state)
            val_seeds.append({"state": state, "gt": gt, "features": features})

        val_data[rn] = {
            "seeds": val_seeds,
            "obs_stats": obs_stats,
            "bin_dists": bin_dists,
            "bin_counts": bin_counts,
        }

    return round_data, val_data


def build_weighted_training(round_data, train_rounds, target_stats, temperature, min_weight):
    """Build training data with per-round similarity weighting."""
    X_all, y_all, w_all = [], [], []

    for rn in train_rounds:
        rd = round_data[rn]
        sim = compute_round_similarity(target_stats, rd["stats"], temperature)
        round_weight = max(min_weight, sim)

        X_all.append(rd["X"])
        y_all.append(rd["y"])
        w_all.append(rd["w"] * round_weight)

    return np.concatenate(X_all), np.concatenate(y_all), np.concatenate(w_all)


def train_catboost(X, y, w, cat_params):
    models = []
    for c in range(NUM_CLASSES):
        t = y[:, c]
        if t.max() - t.min() < 1e-8:
            models.append(None)
            continue
        m = CatBoostRegressor(loss_function="RMSE", verbose=0, thread_count=-1, **cat_params)
        m.fit(X, t, sample_weight=w)
        models.append(m)
    return models


def predict_catboost(models, X):
    return np.column_stack([
        np.zeros(len(X)) if m is None else m.predict(X) for m in models
    ])


def evaluate_fold(models, val_info, blended_stats, k):
    """Score one fold."""
    bin_dists = val_info["bin_dists"]
    bin_counts = val_info["bin_counts"]
    stats_arr = round_stats_to_array(blended_stats)

    seed_scores = []
    for sd in val_info["seeds"]:
        state, gt, features = sd["state"], sd["gt"], sd["features"]
        h, w = state.grid.shape
        probs = np.zeros((h, w, NUM_CLASSES), np.float32)

        dyn, Xp = [], []
        for r in range(h):
            for c in range(w):
                sp = _static_prediction(state.grid[r, c])
                if sp is not None:
                    probs[r, c] = sp
                else:
                    dyn.append((r, c))
                    Xp.append(_build_row(features[r, c], stats_arr))

        if Xp:
            preds = predict_catboost(models, np.array(Xp, np.float32))
            for (r, c), pred in zip(dyn, preds):
                probs[r, c] = pred

        for r in range(h):
            for c in range(w):
                if state.grid[r, c] in (OCEAN, MOUNTAIN):
                    continue
                bk = _cell_bin_key(features[r, c])
                if bk is None or bk not in bin_dists:
                    bk = _cell_bin_key_coarse(features[r, c])
                if bk is not None and bk in bin_dists:
                    n = bin_counts.get(bk, 0)
                    weight = n / (n + k)
                    probs[r, c] = weight * bin_dists[bk] + (1 - weight) * probs[r, c]

        probs = np.maximum(probs, PROB_FLOOR)
        probs /= probs.sum(axis=-1, keepdims=True)
        seed_scores.append(score_prediction(probs, gt))

    return np.mean(seed_scores)


def objective(trial, round_data, val_data, cat_params, adapt_params):
    """Optimize round weighting + k jointly."""
    temperature = trial.suggest_float("temperature", 0.01, 0.5)
    min_weight = trial.suggest_float("min_weight", 0.1, 1.0)
    k_base = trial.suggest_float("k_base", 30, 200)

    a, b, c_p = adapt_params["a"], adapt_params["b"], adapt_params["c"]

    round_scores = {}

    for test_rn in ROUNDS_WITH_OBS:
        if test_rn not in val_data:
            continue

        train_rounds = [rn for rn in ALL_ROUNDS if rn != test_rn]
        vi = val_data[test_rn]
        obs_stats = vi["obs_stats"]

        # Compute historical avg from training rounds
        hist_list = [round_data[rn]["stats"] for rn in train_rounds]
        fields = ["ruin_rate", "settlement_rate", "port_rate", "expansion_distance",
                  "forest_rate", "empty_rate", "settlement_to_ruin_ratio"]
        hist_stats = RoundStats(**{f: np.mean([getattr(s, f) for s in hist_list]) for f in fields})

        # Adaptive stat blending
        obs_settle = obs_stats.settlement_rate
        hist_settle = hist_stats.settlement_rate
        divergence = abs(obs_settle - hist_settle) / (hist_settle + 1e-6)
        obs_weight = sigmoid(a * obs_settle + b * divergence + c_p)

        blended = RoundStats(**{
            f: obs_weight * getattr(obs_stats, f) + (1 - obs_weight) * getattr(hist_stats, f)
            for f in fields
        })

        # Build weighted training data
        X, y, w = build_weighted_training(
            round_data, train_rounds, blended, temperature, min_weight
        )

        models = train_catboost(X, y, w, cat_params)
        score = evaluate_fold(models, vi, blended, k_base)
        round_scores[test_rn] = score
        trial.set_user_attr(f"R{test_rn}", score)

    return np.mean(list(round_scores.values()))


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--n-trials", type=int, default=100)
    args = parser.parse_args()

    cat_params = json.load(open(Path(__file__).parent.parent / "best_params_all.json"))["catboost"]

    # Load adaptive stats params
    adapt_path = Path(__file__).parent / "adaptive_stats_kfold_params.json"
    if adapt_path.exists():
        with open(adapt_path) as f:
            saved = json.load(f)
        adapt_params = saved["adaptive_stats"]
    else:
        adapt_params = {"a": -15.28, "b": 0.58, "c": 4.41}

    print("Precomputing round data...")
    round_data, val_data = precompute_round_data()
    print(f"Rounds: {list(round_data.keys())}")
    print(f"Val rounds with obs: {list(val_data.keys())}")

    # Show round stats for context
    print(f"\n{'Round':<8} {'Settle%':>8} {'Ruin%':>7} {'Cells':>7}")
    print("-" * 35)
    for rn in ALL_ROUNDS:
        st = round_data[rn]["stats"]
        print(f"  R{rn:<5} {st.settlement_rate*100:>7.1f} {st.ruin_rate*100:>6.1f} {round_data[rn]['n_cells']:>7}")

    # Baseline: uniform weighting (temperature=inf → all weights=1)
    print("\nBaseline (uniform weighting):")
    baseline_scores = {}
    for test_rn in ROUNDS_WITH_OBS:
        if test_rn not in val_data:
            continue
        train_rounds = [rn for rn in ALL_ROUNDS if rn != test_rn]
        X = np.concatenate([round_data[rn]["X"] for rn in train_rounds])
        y = np.concatenate([round_data[rn]["y"] for rn in train_rounds])
        w = np.concatenate([round_data[rn]["w"] for rn in train_rounds])

        vi = val_data[test_rn]
        obs_stats = vi["obs_stats"]
        hist_list = [round_data[rn]["stats"] for rn in train_rounds]
        fields = ["ruin_rate", "settlement_rate", "port_rate", "expansion_distance",
                  "forest_rate", "empty_rate", "settlement_to_ruin_ratio"]
        hist_stats = RoundStats(**{f: np.mean([getattr(s, f) for s in hist_list]) for f in fields})
        obs_settle = obs_stats.settlement_rate
        divergence = abs(obs_settle - hist_stats.settlement_rate) / (hist_stats.settlement_rate + 1e-6)
        ow = sigmoid(adapt_params["a"] * obs_settle + adapt_params["b"] * divergence + adapt_params["c"])
        blended = RoundStats(**{f: ow * getattr(obs_stats, f) + (1-ow) * getattr(hist_stats, f) for f in fields})

        models = train_catboost(X, y, w, cat_params)
        score = evaluate_fold(models, vi, blended, 80)
        baseline_scores[test_rn] = score
        print(f"  R{test_rn}: {score:.2f}")
    print(f"  Avg: {np.mean(list(baseline_scores.values())):.2f}")

    # Optuna
    print(f"\nRunning Optuna ({args.n_trials} trials)...")
    study = optuna.create_study(study_name="round-weighting", direction="maximize")
    study.enqueue_trial({"temperature": 0.5, "min_weight": 1.0, "k_base": 80})  # baseline
    study.optimize(lambda t: objective(t, round_data, val_data, cat_params, adapt_params),
                   n_trials=args.n_trials)

    best = study.best_trial
    print(f"\n{'=' * 60}")
    print(f"BEST: {best.value:.4f} (trial {best.number})")
    print(f"{'=' * 60}")
    for rn in sorted(ROUNDS_WITH_OBS):
        key = f"R{rn}"
        if key in best.user_attrs:
            bl = baseline_scores.get(rn, 0)
            diff = best.user_attrs[key] - bl
            print(f"  R{rn}: {best.user_attrs[key]:.2f}  (baseline: {bl:.2f}, diff: {diff:+.2f})")
    print(f"  Avg baseline:  {np.mean(list(baseline_scores.values())):.2f}")
    print(f"  Avg optimized: {best.value:.2f}")
    print(f"\n  temperature={best.params['temperature']:.4f}")
    print(f"  min_weight={best.params['min_weight']:.4f}")
    print(f"  k_base={best.params['k_base']:.1f}")

    # Show what the weights look like for a high-activity round
    print(f"\n  Example weights for R12-like round (settle=31.5%):")
    target = round_data[12]["stats"]
    for rn in ALL_ROUNDS:
        sim = compute_round_similarity(target, round_data[rn]["stats"], best.params["temperature"])
        w = max(best.params["min_weight"], sim)
        print(f"    R{rn}: weight={w:.3f}  (settle={round_data[rn]['stats'].settlement_rate*100:.1f}%)")

    # Save
    result = {
        "temperature": best.params["temperature"],
        "min_weight": best.params["min_weight"],
        "k_base": best.params["k_base"],
        "baseline_avg": float(np.mean(list(baseline_scores.values()))),
        "optimized_avg": float(best.value),
    }
    out_path = Path(__file__).parent / "round_weighting_params.json"
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2)
    print(f"\n  Saved to {out_path}")


if __name__ == "__main__":
    main()
