"""Optuna search for optimal k value (and adaptive k thresholds).

Fixes CatBoost params from best_params_all.json, only tunes:
  - k_base (main k for empirical bin blending)
  - k_low, k_low_thresh, k_mid, k_mid_thresh (adaptive k schedule)

Uses leave-one-round-out cross-validation on rounds with observations.

Usage:
    python optuna_k_search.py --n-trials 200
    python optuna_k_search.py --n-trials 200 --simple   # Only tune k_base (no adaptive schedule)
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import optuna

sys.path.insert(0, str(Path(__file__).parent))

from catboost import CatBoostRegressor
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
BEST_PARAMS_PATH = Path(__file__).parent / "best_params_all.json"
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


def load_catboost_params():
    if BEST_PARAMS_PATH.exists():
        with open(BEST_PARAMS_PATH) as f:
            return json.load(f).get("catboost", {})
    return {"iterations": 200, "depth": 5, "learning_rate": 0.1}


# ── Precompute ────────────────────────────────────────────────────────

def precompute_training_data(rn):
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
    all_X, all_y, all_w = [], [], []
    for rn in rounds:
        X, y, w = precompute_training_data(rn)
        all_X.append(X)
        all_y.append(y)
        all_w.append(w)
    return np.concatenate(all_X), np.concatenate(all_y), np.concatenate(all_w)


# ── Precompute models (CatBoost params are fixed) ────────────────────

def precompute_fold_models(all_rounds, val_rounds, cat_params):
    """Train CatBoost for each fold (val_round excluded) and cache."""
    fold_models = {}
    for val_rn in val_rounds:
        key = f"model_{val_rn}"
        if key in _cache:
            fold_models[val_rn] = _cache[key]
            continue

        train_rounds = [r for r in all_rounds if r != val_rn]
        X, y, w = merge_training_data(train_rounds)

        models = []
        for c in range(NUM_CLASSES):
            target = y[:, c]
            if target.max() - target.min() < 1e-8:
                models.append(None)
                continue
            m = CatBoostRegressor(
                loss_function="RMSE", verbose=0, thread_count=-1, **cat_params,
            )
            m.fit(X, target, sample_weight=w)
            models.append(m)

        _cache[key] = models
        fold_models[val_rn] = models
        print(f"  Trained fold model (val=R{val_rn})")

    return fold_models


def evaluate_on_round(models, val_rn, k):
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
            preds = np.column_stack([
                np.zeros(len(sd["X_pred"])) if m is None else m.predict(sd["X_pred"])
                for m in models
            ])
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


# ── Optuna objectives ────────────────────────────────────────────────

def objective_simple(trial, fold_models, val_rounds):
    """Only tune k_base — single k for all rounds."""
    k = trial.suggest_int("k", 10, 300)

    fold_scores = []
    for val_rn in val_rounds:
        score = evaluate_on_round(fold_models[val_rn], val_rn, k)
        fold_scores.append(score)
        trial.set_user_attr(f"R{val_rn}", round(score, 2))

    avg = np.mean(fold_scores)
    return avg


def objective_adaptive(trial, fold_models, val_rounds):
    """Tune adaptive k schedule: different k for different settlement rates."""
    k_base = trial.suggest_int("k_base", 10, 300)
    k_low = trial.suggest_int("k_low", 10, 300)
    k_low_thresh = trial.suggest_float("k_low_thresh", 0.01, 0.15)
    k_mid = trial.suggest_int("k_mid", 10, 300)
    k_mid_thresh = trial.suggest_float("k_mid_thresh", 0.05, 0.35)

    # Ensure thresholds are ordered
    if k_low_thresh >= k_mid_thresh:
        return -100.0

    fold_scores = []
    for val_rn in val_rounds:
        rd = precompute_val_round(val_rn)
        settle = rd["obs_stats"].settlement_rate

        if settle < k_low_thresh:
            k = k_low
        elif settle < k_mid_thresh:
            k = k_mid
        else:
            k = k_base

        score = evaluate_on_round(fold_models[val_rn], val_rn, k)
        fold_scores.append(score)
        trial.set_user_attr(f"R{val_rn}", round(score, 2))

    avg = np.mean(fold_scores)
    return avg


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--n-trials", type=int, default=200)
    parser.add_argument("--simple", action="store_true",
                        help="Only tune k_base (no adaptive schedule)")
    args = parser.parse_args()

    all_rounds = get_all_rounds()
    val_rounds = get_rounds_with_observations()
    cat_params = load_catboost_params()

    print(f"All rounds: {all_rounds}")
    print(f"Val rounds (with observations): {val_rounds}")
    print(f"CatBoost params (fixed): {cat_params}")
    print(f"Mode: {'simple k' if args.simple else 'adaptive k schedule'}\n")

    # Precompute everything
    print("Precomputing training data...")
    for rn in all_rounds:
        precompute_training_data(rn)
        sys.stdout.write(f"\r  Round {rn} done")
        sys.stdout.flush()
    print()

    print("Precomputing validation data...")
    for rn in val_rounds:
        precompute_val_round(rn)
        sys.stdout.write(f"\r  Round {rn} done")
        sys.stdout.flush()
    print()

    print("Training CatBoost models for each fold...")
    fold_models = precompute_fold_models(all_rounds, val_rounds, cat_params)

    # Run Optuna
    print(f"\n{'=' * 65}")
    print(f"OPTUNA K SEARCH ({'simple' if args.simple else 'adaptive'})")
    print(f"{'=' * 65}\n")

    study = optuna.create_study(study_name="k_search", direction="maximize")

    if args.simple:
        study.optimize(
            lambda t: objective_simple(t, fold_models, val_rounds),
            n_trials=args.n_trials,
            show_progress_bar=True,
        )
    else:
        study.optimize(
            lambda t: objective_adaptive(t, fold_models, val_rounds),
            n_trials=args.n_trials,
            show_progress_bar=True,
        )

    best = study.best_trial
    print(f"\nBest avg score: {best.value:.4f}")
    print(f"Best params: {best.params}")
    print(f"\nPer-fold scores:")
    for rn in val_rounds:
        key = f"R{rn}"
        if key in best.user_attrs:
            print(f"  R{rn}: {best.user_attrs[key]}")

    # Show top 10 trials
    print(f"\n{'─' * 65}")
    print(f"Top 10 trials:")
    trials_sorted = sorted(study.trials, key=lambda t: t.value if t.value else -999, reverse=True)
    for i, t in enumerate(trials_sorted[:10]):
        print(f"  #{i+1}: score={t.value:.4f}  params={t.params}")

    # Save
    if args.simple:
        best_k = best.params["k"]
        print(f"\nBest k: {best_k}")

        if BEST_PARAMS_PATH.exists():
            with open(BEST_PARAMS_PATH) as f:
                all_params = json.load(f)
        else:
            all_params = {}
        all_params["best_k"] = best_k
        with open(BEST_PARAMS_PATH, "w") as f:
            json.dump(all_params, f, indent=2)
        print(f"Saved best_k={best_k} to {BEST_PARAMS_PATH}")
    else:
        k_params = {
            "k_base": best.params["k_base"],
            "k_low": best.params["k_low"],
            "k_low_thresh": best.params["k_low_thresh"],
            "k_mid": best.params["k_mid"],
            "k_mid_thresh": best.params["k_mid_thresh"],
        }
        print(f"\nBest adaptive k params: {k_params}")

        adaptive_path = Path(__file__).parent / "experiments" / "adaptive_stats_kfold_params.json"
        if adaptive_path.exists():
            with open(adaptive_path) as f:
                adaptive_data = json.load(f)
        else:
            adaptive_data = {}
        adaptive_data["k_params"] = k_params
        with open(adaptive_path, "w") as f:
            json.dump(adaptive_data, f, indent=2)
        print(f"Saved to {adaptive_path}")

        # Also save k_base to best_params_all.json
        if BEST_PARAMS_PATH.exists():
            with open(BEST_PARAMS_PATH) as f:
                all_params = json.load(f)
        else:
            all_params = {}
        all_params["best_k"] = best.params["k_base"]
        with open(BEST_PARAMS_PATH, "w") as f:
            json.dump(all_params, f, indent=2)
        print(f"Saved best_k={best.params['k_base']} to {BEST_PARAMS_PATH}")


if __name__ == "__main__":
    main()
