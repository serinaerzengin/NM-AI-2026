"""Optuna CatBoost hyperparameter search with leave-one-round-out cross-validation.

Uses all completed rounds with observations for validation.
Trains on N-1 rounds, validates on 1 round with empirical bins.

Usage:
    python optuna_kfold.py --n-trials 100
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import optuna

sys.path.insert(0, str(Path(__file__).parent))

from astar.types import MapState, Observation, RoundStats, NUM_CLASSES, OCEAN, MOUNTAIN
from astar.features import compute_features, FEATURE_NAMES
from astar.calibration import (
    compute_round_stats_from_ground_truth,
    compute_round_stats_from_observations,
    round_stats_to_array,
)
from astar.predictor import _build_row, _static_prediction, _is_static_cell, PROB_FLOOR
from astar.scoring import score_prediction
from astar.empirical_bins import (
    build_empirical_distributions, get_bin_coverage_stats,
    _cell_bin_key, _cell_bin_key_coarse,
)
import store

DATA_DIR = Path(__file__).parent / "data" / "rounds"
SEEDS = list(range(5))

_cache = {}


def get_all_rounds():
    rounds = []
    for d in sorted(DATA_DIR.iterdir()):
        if d.is_dir() and d.name.startswith("round_"):
            rn = int(d.name.split("_")[1])
            if (d / "seed_0" / "ground_truth.json").exists():
                rounds.append(rn)
    return rounds


def get_rounds_with_observations():
    rounds = []
    for rn in get_all_rounds():
        obs_dir = DATA_DIR / f"round_{rn}" / "seed_0" / "observations"
        if obs_dir.exists() and any(obs_dir.iterdir()):
            rounds.append(rn)
    return rounds


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


# ── Precompute ────────────────────────────────────────────────────────

def precompute_round_training_data(rn):
    """Precompute training data for a single round."""
    key = f"train_{rn}"
    if key in _cache:
        return _cache[key]

    stats = round_stats_avg(rn)
    stats_arr = round_stats_to_array(stats)
    X_rows, y_rows, w_rows = [], [], []

    for si in SEEDS:
        state, gt = load_map(rn, si)
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

    result = (
        np.array(X_rows, dtype=np.float32),
        np.array(y_rows, dtype=np.float32),
        np.array(w_rows, dtype=np.float32),
    )
    _cache[key] = result
    return result


def precompute_val_round(rn):
    """Precompute validation data for a round with observations."""
    key = f"val_{rn}"
    if key in _cache:
        return _cache[key]

    states = []
    all_obs = []
    for si in SEEDS:
        state, _ = load_map(rn, si)
        states.append(state)
        all_obs.extend(load_obs(rn, si))

    obs_stats = compute_round_stats_from_observations(all_obs, states[0])
    bin_dists = build_empirical_distributions(all_obs, states)
    bin_counts = get_bin_coverage_stats(all_obs, states)
    stats_arr = round_stats_to_array(obs_stats)

    val_seeds = []
    for si in SEEDS:
        state, gt = load_map(rn, si)
        features = compute_features(state)
        dynamic_indices = []
        X_pred = []
        static_preds = {}
        h, w = state.grid.shape
        for r in range(h):
            for c in range(w):
                sp = _static_prediction(state.grid[r, c])
                if sp is not None:
                    static_preds[(r, c)] = sp
                else:
                    dynamic_indices.append((r, c))
                    X_pred.append(_build_row(features[r, c], stats_arr))
        val_seeds.append({
            "state": state, "gt": gt, "features": features,
            "dynamic_indices": dynamic_indices,
            "X_pred": np.array(X_pred, dtype=np.float32),
            "static_preds": static_preds,
        })

    result = {
        "seeds": val_seeds, "obs_stats": obs_stats,
        "bin_dists": bin_dists, "bin_counts": bin_counts,
    }
    _cache[key] = result
    return result


def merge_training_data(rounds):
    """Merge precomputed training data for multiple rounds."""
    all_X, all_y, all_w = [], [], []
    for rn in rounds:
        X, y, w = precompute_round_training_data(rn)
        all_X.append(X)
        all_y.append(y)
        all_w.append(w)
    return np.concatenate(all_X), np.concatenate(all_y), np.concatenate(all_w)


def evaluate_on_round(predict_fn, val_rn, k):
    """Score predictions on a single validation round."""
    rd = precompute_val_round(val_rn)
    seed_scores = []
    for sd in rd["seeds"]:
        state, gt = sd["state"], sd["gt"]
        features = sd["features"]
        h, w = state.grid.shape
        probs = np.zeros((h, w, NUM_CLASSES), dtype=np.float32)

        for (r, c), sp in sd["static_preds"].items():
            probs[r, c] = sp

        if len(sd["X_pred"]) > 0:
            preds = predict_fn(sd["X_pred"])
            for (r, c), pred in zip(sd["dynamic_indices"], preds):
                probs[r, c] = pred

        # Empirical bin blending
        bin_dists = rd["bin_dists"]
        bin_counts = rd["bin_counts"]
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
        probs = probs / probs.sum(axis=-1, keepdims=True)
        seed_scores.append(score_prediction(probs, gt))

    return np.mean(seed_scores)


# ── Optuna objective ──────────────────────────────────────────────────

def objective(trial, all_rounds, val_rounds):
    from catboost import CatBoostRegressor

    iters = trial.suggest_int("iterations", 100, 600)
    depth = trial.suggest_int("depth", 4, 9)
    lr = trial.suggest_float("learning_rate", 0.01, 0.3, log=True)
    l2 = trial.suggest_float("l2_leaf_reg", 1.0, 10.0)
    subsample = trial.suggest_float("subsample", 0.5, 1.0)
    k = trial.suggest_int("k", 20, 200)

    fold_scores = []

    for val_rn in val_rounds:
        train_rounds = [r for r in all_rounds if r != val_rn]
        X, y, w = merge_training_data(train_rounds)

        models = []
        for c in range(NUM_CLASSES):
            target = y[:, c]
            if target.max() - target.min() < 1e-8:
                models.append(None)
                continue
            m = CatBoostRegressor(
                iterations=iters, depth=depth, learning_rate=lr,
                l2_leaf_reg=l2, subsample=subsample,
                loss_function="RMSE", verbose=0, thread_count=-1,
            )
            m.fit(X, target, sample_weight=w)
            models.append(m)

        def predict_fn(X_pred):
            return np.column_stack([
                np.zeros(len(X_pred)) if m is None else m.predict(X_pred)
                for m in models
            ])

        score = evaluate_on_round(predict_fn, val_rn, k)
        fold_scores.append(score)
        trial.set_user_attr(f"R{val_rn}", score)

    avg = np.mean(fold_scores)
    trial.set_user_attr("fold_scores", fold_scores)
    return avg


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--n-trials", type=int, default=100)
    args = parser.parse_args()

    all_rounds = get_all_rounds()
    val_rounds = get_rounds_with_observations()

    print(f"All rounds with ground truth: {all_rounds}")
    print(f"Rounds with observations (used as val folds): {val_rounds}")
    print(f"Leave-one-round-out: {len(val_rounds)} folds\n")

    # Precompute all data
    print("Precomputing training data for all rounds...")
    for rn in all_rounds:
        precompute_round_training_data(rn)
        sys.stdout.write(f"\r  Round {rn} done")
        sys.stdout.flush()
    print()

    print("Precomputing validation data...")
    for rn in val_rounds:
        precompute_val_round(rn)
        sys.stdout.write(f"\r  Round {rn} done")
        sys.stdout.flush()
    print()

    total_cells = sum(len(precompute_round_training_data(rn)[0]) for rn in all_rounds)
    print(f"Total training cells: {total_cells}\n")

    # Run Optuna
    print("=" * 65)
    print("CATBOOST K-FOLD OPTUNA SEARCH")
    print("=" * 65)

    study = optuna.create_study(study_name="catboost_kfold", direction="maximize")
    study.optimize(
        lambda t: objective(t, all_rounds, val_rounds),
        n_trials=args.n_trials,
        show_progress_bar=True,
    )

    best = study.best_trial
    print(f"\nBest avg score: {best.value:.2f}")
    print(f"Best params: {best.params}")
    print(f"\nPer-fold scores:")
    for rn in val_rounds:
        key = f"R{rn}"
        if key in best.user_attrs:
            print(f"  R{rn}: {best.user_attrs[key]:.2f}")

    # Save best params
    cat_params = {
        "iterations": best.params["iterations"],
        "depth": best.params["depth"],
        "learning_rate": best.params["learning_rate"],
        "l2_leaf_reg": best.params["l2_leaf_reg"],
        "subsample": best.params["subsample"],
    }
    best_k = best.params["k"]

    # Load existing params and update
    params_path = Path(__file__).parent / "best_params_all.json"
    if params_path.exists():
        with open(params_path) as f:
            all_params = json.load(f)
    else:
        all_params = {}

    all_params["catboost"] = cat_params
    all_params["best_k"] = best_k

    with open(params_path, "w") as f:
        json.dump(all_params, f, indent=2)

    print(f"\nSaved to {params_path}")
    print(f"  CatBoost params: {cat_params}")
    print(f"  Best k: {best_k}")

    # Compare with current params
    print(f"\n{'─' * 65}")
    print("Previous params were:")
    print(f"  iterations=195, depth=6, lr=0.025, l2=2.79, subsample=0.77")
    print(f"  k=49")


if __name__ == "__main__":
    main()
