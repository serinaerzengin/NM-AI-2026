"""Experiment: Adaptive stats blending with leave-one-round-out k-fold.

For each validation round (those with observations), trains CatBoost on ALL
other rounds and evaluates on the held-out round. This maximizes training data
and gives unbiased per-round scores.

Optuna optimizes the adaptive stat blending and k parameters.
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

# All rounds with ground truth
ALL_ROUNDS = list(range(1, 14))
# Rounds with observations (can validate with bins)
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


def blend_stats(obs_stats, hist_stats, obs_weight):
    fields = ["ruin_rate", "settlement_rate", "port_rate", "expansion_distance",
              "forest_rate", "empty_rate", "settlement_to_ruin_ratio"]
    return RoundStats(**{
        f: obs_weight * getattr(obs_stats, f) + (1 - obs_weight) * getattr(hist_stats, f)
        for f in fields
    })


def build_training_data(train_rounds):
    X_rows, y_rows, w_rows = [], [], []
    for rn in train_rounds:
        stats = round_stats_avg(rn)
        stats_arr = round_stats_to_array(stats)
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
    return np.array(X_rows, np.float32), np.array(y_rows, np.float32), np.array(w_rows, np.float32)


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


# ── Precompute per-fold data ─────────────────────────────────────────────

def precompute_folds(cat_params):
    """Train a separate model for each fold, precompute validation data."""
    folds = {}

    for test_rn in ROUNDS_WITH_OBS:
        train_rounds = [rn for rn in ALL_ROUNDS if rn != test_rn]

        # Train
        X, y, w = build_training_data(train_rounds)
        models = train_catboost(X, y, w, cat_params)

        # Historical avg stats (from training rounds)
        hist_list = [round_stats_avg(rn) for rn in train_rounds]
        fields = ["ruin_rate", "settlement_rate", "port_rate", "expansion_distance",
                  "forest_rate", "empty_rate", "settlement_to_ruin_ratio"]
        hist_stats = RoundStats(**{f: np.mean([getattr(s, f) for s in hist_list]) for f in fields})

        # Validation data
        states, all_obs = [], []
        for si in SEEDS:
            state, _ = load_map(test_rn, si)
            states.append(state)
            all_obs.extend(load_obs(test_rn, si))

        obs_stats = compute_round_stats_from_observations(all_obs, states[0])
        gt_stats = round_stats_avg(test_rn)
        bin_dists = build_empirical_distributions(all_obs, states)
        bin_counts = get_bin_coverage_stats(all_obs, states)

        val_seeds = []
        for si in SEEDS:
            state, gt = load_map(test_rn, si)
            features = compute_features(state)
            val_seeds.append({"state": state, "gt": gt, "features": features})

        folds[test_rn] = {
            "models": models,
            "hist_stats": hist_stats,
            "obs_stats": obs_stats,
            "gt_stats": gt_stats,
            "bin_dists": bin_dists,
            "bin_counts": bin_counts,
            "seeds": val_seeds,
            "train_size": len(X),
        }

    return folds


def evaluate_folds(folds, adaptive_params, k_params):
    a, b, c_param = adaptive_params["a"], adaptive_params["b"], adaptive_params["c"]
    k_base = k_params["k_base"]
    k_low_thresh = k_params["k_low_thresh"]
    k_low = k_params["k_low"]
    k_mid_thresh = k_params["k_mid_thresh"]
    k_mid = k_params["k_mid"]

    round_scores = {}

    for test_rn, fold in folds.items():
        models = fold["models"]
        obs_stats = fold["obs_stats"]
        hist_stats = fold["hist_stats"]
        bin_dists = fold["bin_dists"]
        bin_counts = fold["bin_counts"]

        # Adaptive obs_weight
        obs_settle = obs_stats.settlement_rate
        hist_settle = hist_stats.settlement_rate
        divergence = abs(obs_settle - hist_settle) / (hist_settle + 1e-6)
        obs_weight = sigmoid(a * obs_settle + b * divergence + c_param)

        blended = blend_stats(obs_stats, hist_stats, obs_weight)
        stats_arr = round_stats_to_array(blended)

        settle = blended.settlement_rate
        if settle < k_low_thresh:
            k = k_low
        elif settle < k_mid_thresh:
            k = k_mid
        else:
            k = k_base

        seed_scores = []
        for sd in fold["seeds"]:
            state, gt, features = sd["state"], sd["gt"], sd["features"]
            h, w = state.grid.shape
            probs = np.zeros((h, w, NUM_CLASSES), dtype=np.float32)

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
            probs = probs / probs.sum(axis=-1, keepdims=True)
            seed_scores.append(score_prediction(probs, gt))

        round_scores[test_rn] = np.mean(seed_scores)

    return round_scores


def objective(trial, folds):
    a = trial.suggest_float("a", -20.0, 5.0)
    b = trial.suggest_float("b", -10.0, 10.0)
    c_param = trial.suggest_float("c", -5.0, 5.0)
    k_base = trial.suggest_float("k_base", 30, 500)
    k_low_thresh = trial.suggest_float("k_low_thresh", 0.02, 0.08)
    k_low = trial.suggest_float("k_low", 10, 200)
    k_mid_thresh = trial.suggest_float("k_mid_thresh", 0.08, 0.15)
    k_mid = trial.suggest_float("k_mid", 20, 300)

    scores = evaluate_folds(
        folds,
        {"a": a, "b": b, "c": c_param},
        {"k_base": k_base, "k_low_thresh": k_low_thresh, "k_low": k_low,
         "k_mid_thresh": k_mid_thresh, "k_mid": k_mid},
    )

    for rn, s in scores.items():
        trial.set_user_attr(f"R{rn}", s)
    return np.mean(list(scores.values()))


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--n-trials", type=int, default=200)
    args = parser.parse_args()

    cat_params = json.load(open(Path(__file__).parent.parent / "best_params_all.json"))["catboost"]

    print(f"Precomputing {len(ROUNDS_WITH_OBS)} folds (leave-one-round-out)...")
    print(f"Training on {len(ALL_ROUNDS)-1} rounds per fold, validating on 1")
    folds = precompute_folds(cat_params)
    for rn, fold in folds.items():
        print(f"  Fold R{rn}: train={fold['train_size']} cells, "
              f"obs_settle={fold['obs_stats'].settlement_rate:.3f}, "
              f"gt_settle={fold['gt_stats'].settlement_rate:.3f}")

    # Baseline
    print("\nBaseline (pure obs stats, current k logic):")
    baseline = evaluate_folds(
        folds,
        {"a": 0, "b": 0, "c": 10},
        {"k_base": 361, "k_low_thresh": 0.05, "k_low": 50, "k_mid_thresh": 0.10, "k_mid": 100},
    )
    for rn in sorted(baseline):
        gt_s = folds[rn]["gt_stats"].settlement_rate
        obs_s = folds[rn]["obs_stats"].settlement_rate
        print(f"  R{rn}: {baseline[rn]:.2f}  (gt_settle={gt_s:.3f}, obs_settle={obs_s:.3f})")
    print(f"  Avg: {np.mean(list(baseline.values())):.2f}")

    # Optuna
    print(f"\nRunning Optuna ({args.n_trials} trials)...")
    study = optuna.create_study(study_name="adaptive-kfold", direction="maximize")
    study.enqueue_trial({"a": 0, "b": 0, "c": 10, "k_base": 361,
                         "k_low_thresh": 0.05, "k_low": 50, "k_mid_thresh": 0.10, "k_mid": 100})
    study.optimize(lambda t: objective(t, folds), n_trials=args.n_trials)

    best = study.best_trial
    print(f"\n{'=' * 60}")
    print(f"BEST: {best.value:.4f} (trial {best.number})")
    print(f"{'=' * 60}")
    for rn in sorted(ROUNDS_WITH_OBS):
        key = f"R{rn}"
        if key in best.user_attrs:
            bl = baseline.get(rn, 0)
            diff = best.user_attrs[key] - bl
            print(f"  R{rn}: {best.user_attrs[key]:.2f}  (baseline: {bl:.2f}, diff: {diff:+.2f})")
    print(f"  Avg baseline: {np.mean(list(baseline.values())):.2f}")
    print(f"  Avg optimized: {best.value:.2f}")
    print(f"\n  Params: {best.params}")

    # Interpret
    a, b, c_p = best.params["a"], best.params["b"], best.params["c"]
    print(f"\n  Weight function: sigmoid({a:.2f} * settle + {b:.2f} * divergence + {c_p:.2f})")
    for settle in [0.03, 0.10, 0.15, 0.20, 0.30]:
        avg_hist = np.mean([folds[rn]["hist_stats"].settlement_rate for rn in folds])
        div = abs(settle - avg_hist) / (avg_hist + 1e-6)
        w = sigmoid(a * settle + b * div + c_p)
        print(f"    settle={settle:.2f} → obs_weight={w:.3f}")

    # Save
    result = {
        "adaptive_stats": {"a": a, "b": b, "c": c_p},
        "k_params": {k: best.params[k] for k in ["k_base", "k_low_thresh", "k_low", "k_mid_thresh", "k_mid"]},
        "baseline_avg": float(np.mean(list(baseline.values()))),
        "optimized_avg": float(best.value),
        "per_round_baseline": {str(k): v for k, v in baseline.items()},
        "per_round_optimized": {str(k): best.user_attrs[f"R{k}"] for k in ROUNDS_WITH_OBS if f"R{k}" in best.user_attrs},
    }
    out_path = Path(__file__).parent / "adaptive_stats_kfold_params.json"
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2)
    print(f"\n  Saved to {out_path}")


if __name__ == "__main__":
    main()
