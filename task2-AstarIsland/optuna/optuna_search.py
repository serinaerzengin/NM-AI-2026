"""Optuna hyperparameter search for Astar Island pipeline.

Trains on rounds 1-5, validates on rounds 6+7 (with their observations + empirical bins).
Optimizes for average score across both validation rounds.

Usage:
    python optuna_search.py                  # 100 trials
    python optuna_search.py --n-trials 200   # custom trial count
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import optuna
import xgboost as xgb

sys.path.insert(0, str(Path(__file__).parent))

from astar.types import MapState, Observation, RoundStats, NUM_CLASSES
from astar.features import compute_features, NUM_FEATURES, FEATURE_NAMES
from astar.calibration import (
    compute_round_stats_from_ground_truth,
    compute_round_stats_from_observations,
    round_stats_to_array,
)
from astar.predictor import _build_row, _static_prediction, _is_static_cell
from astar.scoring import score_prediction
from astar.empirical_bins import (
    build_empirical_distributions,
    get_bin_coverage_stats,
    _cell_bin_key,
    _cell_bin_key_coarse,
)
import store

DATA_DIR = Path(__file__).parent / "data" / "rounds"
TRAIN_ROUNDS = list(range(1, 6))
VAL_ROUNDS = [6, 7]
SEEDS = list(range(5))

# ── Data loading (cached) ────────────────────────────────────────────────

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
    fields = [
        "ruin_rate", "settlement_rate", "port_rate", "expansion_distance",
        "forest_rate", "empty_rate", "settlement_to_ruin_ratio",
    ]
    return RoundStats(**{f: np.mean([getattr(s, f) for s in stats]) for f in fields})


def load_obs_typed(rn, si):
    raw_list = store.list_observations(rn, si)
    obs = []
    for raw in raw_list:
        if isinstance(raw, list):
            raw = raw[0]
        vp = raw["viewport"]
        obs.append(Observation(
            grid=np.array(raw["grid"]),
            settlements=raw.get("settlements", []),
            viewport=(vp["x"], vp["y"], vp["w"], vp["h"]),
            seed_index=si,
        ))
    return obs


# ── Precompute training and validation data ──────────────────────────────

def precompute_all():
    """Precompute features and targets for all rounds. Called once."""
    data = {}

    # Training data
    for rn in TRAIN_ROUNDS:
        stats = round_stats_avg(rn)
        for si in SEEDS:
            state, gt = load_map(rn, si)
            features = compute_features(state)
            data[(rn, si)] = {
                "state": state, "gt": gt, "features": features, "stats": stats,
            }

    # Validation data + observations
    for rn in VAL_ROUNDS:
        states = []
        all_obs = []
        for si in SEEDS:
            state, gt = load_map(rn, si)
            features = compute_features(state)
            obs = load_obs_typed(rn, si)
            all_obs.extend(obs)
            states.append(state)
            data[(rn, si)] = {
                "state": state, "gt": gt, "features": features,
            }

        obs_stats = compute_round_stats_from_observations(all_obs, states[0])
        bin_dists = build_empirical_distributions(all_obs, states)
        bin_counts = get_bin_coverage_stats(all_obs, states)
        data[f"val_{rn}"] = {
            "states": states, "obs_stats": obs_stats,
            "bin_dists": bin_dists, "bin_counts": bin_counts,
        }

    return data


# ── Objective function ───────────────────────────────────────────────────

def objective(trial, precomputed):
    # XGBoost hyperparameters
    n_estimators = trial.suggest_int("n_estimators", 100, 800)
    max_depth = trial.suggest_int("max_depth", 4, 10)
    learning_rate = trial.suggest_float("learning_rate", 0.01, 0.3, log=True)
    subsample = trial.suggest_float("subsample", 0.5, 1.0)
    colsample_bytree = trial.suggest_float("colsample_bytree", 0.5, 1.0)
    reg_alpha = trial.suggest_float("reg_alpha", 1e-4, 10.0, log=True)
    reg_lambda = trial.suggest_float("reg_lambda", 0.1, 10.0, log=True)
    min_child_weight = trial.suggest_int("min_child_weight", 1, 20)

    # Empirical bin blending
    k = trial.suggest_float("k", 30, 500, log=True)

    # Probability floor
    prob_floor = trial.suggest_float("prob_floor", 0.001, 0.05, log=True)

    # ── Build training data ──
    X_rows, y_rows, w_rows = [], [], []

    for rn in TRAIN_ROUNDS:
        stats = round_stats_avg(rn)
        stats_arr = round_stats_to_array(stats)
        for si in SEEDS:
            d = precomputed[(rn, si)]
            gt = d["gt"]
            features = d["features"]
            state = d["state"]
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
    sample_weight = np.array(w_rows, dtype=np.float32)

    # ── Train model ──
    model = xgb.XGBRegressor(
        n_estimators=n_estimators,
        max_depth=max_depth,
        learning_rate=learning_rate,
        subsample=subsample,
        colsample_bytree=colsample_bytree,
        reg_alpha=reg_alpha,
        reg_lambda=reg_lambda,
        min_child_weight=min_child_weight,
        multi_strategy="multi_output_tree",
        tree_method="hist",
        objective="reg:squarederror",
        n_jobs=-1,
        verbosity=0,
    )
    model.fit(X, y, sample_weight=sample_weight)

    # ── Evaluate on validation rounds ──
    round_scores = []

    for rn in VAL_ROUNDS:
        val_data = precomputed[f"val_{rn}"]
        obs_stats = val_data["obs_stats"]
        bin_dists = val_data["bin_dists"]
        bin_counts = val_data["bin_counts"]
        stats_arr = round_stats_to_array(obs_stats)

        seed_scores = []
        for si in SEEDS:
            d = precomputed[(rn, si)]
            state, gt, features = d["state"], d["gt"], d["features"]
            h, w = state.grid.shape

            # Model prediction
            probs = np.zeros((h, w, NUM_CLASSES), dtype=np.float32)
            dynamic_indices = []
            X_pred = []

            for r in range(h):
                for c in range(w):
                    static_pred = _static_prediction(state.grid[r, c])
                    if static_pred is not None:
                        probs[r, c] = static_pred
                    else:
                        dynamic_indices.append((r, c))
                        X_pred.append(_build_row(features[r, c], stats_arr))

            if X_pred:
                preds = model.predict(np.array(X_pred, dtype=np.float32))
                for (r, c), pred in zip(dynamic_indices, preds):
                    probs[r, c] = pred

            # Adaptive empirical bin blending
            from astar.types import OCEAN, MOUNTAIN
            for r in range(h):
                for c in range(w):
                    if state.grid[r, c] in (OCEAN, MOUNTAIN):
                        continue
                    bin_key = _cell_bin_key(features[r, c])
                    if bin_key is None or bin_key not in bin_dists:
                        bin_key = _cell_bin_key_coarse(features[r, c])
                    if bin_key is not None and bin_key in bin_dists:
                        n = bin_counts.get(bin_key, 0)
                        weight = n / (n + k)
                        probs[r, c] = weight * bin_dists[bin_key] + (1 - weight) * probs[r, c]

            # Floor and normalize
            probs = np.maximum(probs, prob_floor)
            probs = probs / probs.sum(axis=-1, keepdims=True)

            seed_scores.append(score_prediction(probs, gt))

        round_scores.append(np.mean(seed_scores))

    avg_score = np.mean(round_scores)

    # Log individual round scores
    trial.set_user_attr("round_6_score", round_scores[0])
    trial.set_user_attr("round_7_score", round_scores[1])

    return avg_score


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--n-trials", type=int, default=100)
    parser.add_argument("--study-name", type=str, default="astar-hparam-search")
    parser.add_argument("--storage", type=str, default=None,
                        help="Optuna storage URL (e.g. sqlite:///optuna.db). Default: in-memory.")
    args = parser.parse_args()

    print("Precomputing features and observations...")
    precomputed = precompute_all()
    print("Done.\n")

    study = optuna.create_study(
        study_name=args.study_name,
        direction="maximize",
        storage=args.storage,
        load_if_exists=True,
    )

    study.optimize(lambda trial: objective(trial, precomputed), n_trials=args.n_trials)

    print("\n" + "=" * 60)
    print("BEST TRIAL")
    print("=" * 60)
    best = study.best_trial
    print(f"  Score: {best.value:.4f}")
    print(f"  Round 6: {best.user_attrs['round_6_score']:.2f}")
    print(f"  Round 7: {best.user_attrs['round_7_score']:.2f}")
    print(f"  Params:")
    for k, v in best.params.items():
        print(f"    {k}: {v}")

    # Save best params
    best_params_path = Path(__file__).parent / "best_params.json"
    with open(best_params_path, "w") as f:
        json.dump(best.params, f, indent=2)
    print(f"\n  Saved to {best_params_path}")


if __name__ == "__main__":
    main()
