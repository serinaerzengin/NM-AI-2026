"""Optuna search for CatBoost, LightGBM, and stacking ensemble.

Trains on rounds 1-5, validates on rounds 6+7+8 (with observations + empirical bins).
Saves best params for each model, then builds and evaluates a stacking ensemble.

Usage:
    python optuna_all_models.py --n-trials 100
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
from astar.predictor import _build_row, _static_prediction, _is_static_cell
from astar.scoring import score_prediction
from astar.empirical_bins import (
    build_empirical_distributions, get_bin_coverage_stats,
    _cell_bin_key, _cell_bin_key_coarse,
)
import store

DATA_DIR = Path(__file__).parent / "data" / "rounds"
TRAIN_ROUNDS = list(range(1, 11))  # Rounds 1-10 (50 maps)
VAL_ROUNDS = [11, 12, 13]  # Most recent rounds with observations
SEEDS = list(range(5))
PROB_FLOOR = 0.001

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


# ── Precompute ────────────────────────────────────────────────────────────

def precompute():
    data = {}

    # Training data
    X_rows, y_rows, w_rows = [], [], []
    for rn in TRAIN_ROUNDS:
        stats = round_stats_avg(rn)
        stats_arr = round_stats_to_array(stats)
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

    data["train_X"] = np.array(X_rows, dtype=np.float32)
    data["train_y"] = np.array(y_rows, dtype=np.float32)
    data["train_w"] = np.array(w_rows, dtype=np.float32)

    # Validation data
    for rn in VAL_ROUNDS:
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

        data[f"val_{rn}"] = {
            "seeds": val_seeds, "obs_stats": obs_stats,
            "bin_dists": bin_dists, "bin_counts": bin_counts,
        }

    return data


def evaluate_model(predict_fn, data, k_override=None):
    """Score a predict_fn on all validation rounds with empirical bins."""
    round_scores = []
    for rn in VAL_ROUNDS:
        rd = data[f"val_{rn}"]
        settle_rate = rd["obs_stats"].settlement_rate
        if k_override is not None:
            k = k_override
        elif settle_rate < 0.05:
            k = 50
        elif settle_rate < 0.10:
            k = 100
        else:
            k = 361

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

        round_scores.append(np.mean(seed_scores))
    return round_scores


# ── Optuna objectives ─────────────────────────────────────────────────────

def objective_catboost(trial, data):
    from catboost import CatBoostRegressor

    iters = trial.suggest_int("iterations", 100, 600)
    depth = trial.suggest_int("depth", 4, 9)
    lr = trial.suggest_float("learning_rate", 0.01, 0.3, log=True)
    l2 = trial.suggest_float("l2_leaf_reg", 1.0, 10.0)
    subsample = trial.suggest_float("subsample", 0.5, 1.0)

    X, y, w = data["train_X"], data["train_y"], data["train_w"]
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

    def predict(X):
        return np.column_stack([
            np.zeros(len(X)) if m is None else m.predict(X) for m in models
        ])

    scores = evaluate_model(predict, data)
    avg = np.mean(scores)
    for rn, s in zip(VAL_ROUNDS, scores):
        trial.set_user_attr(f"R{rn}", s)
    return avg


def objective_lightgbm(trial, data):
    from lightgbm import LGBMRegressor

    n_est = trial.suggest_int("n_estimators", 100, 700)
    depth = trial.suggest_int("max_depth", 3, 10)
    lr = trial.suggest_float("learning_rate", 0.01, 0.3, log=True)
    subsample = trial.suggest_float("subsample", 0.5, 1.0)
    colsample = trial.suggest_float("colsample_bytree", 0.5, 1.0)
    reg_alpha = trial.suggest_float("reg_alpha", 1e-4, 10.0, log=True)
    reg_lambda = trial.suggest_float("reg_lambda", 0.1, 10.0, log=True)
    min_child = trial.suggest_int("min_child_samples", 5, 50)

    X, y, w = data["train_X"], data["train_y"], data["train_w"]
    models = []
    for c in range(NUM_CLASSES):
        m = LGBMRegressor(
            n_estimators=n_est, max_depth=depth, learning_rate=lr,
            subsample=subsample, colsample_bytree=colsample,
            reg_alpha=reg_alpha, reg_lambda=reg_lambda,
            min_child_samples=min_child, verbosity=-1, n_jobs=-1,
        )
        m.fit(X, y[:, c], sample_weight=w)
        models.append(m)

    def predict(X):
        return np.column_stack([m.predict(X) for m in models])

    scores = evaluate_model(predict, data)
    avg = np.mean(scores)
    for rn, s in zip(VAL_ROUNDS, scores):
        trial.set_user_attr(f"R{rn}", s)
    return avg


# ── Stacking ──────────────────────────────────────────────────────────────

def build_stacking(data, xgb_params, cat_params, lgb_params):
    """Train 3 base models, then a ridge regression meta-model on their predictions."""
    import xgboost as xgb
    from catboost import CatBoostRegressor
    from lightgbm import LGBMRegressor
    from sklearn.linear_model import Ridge

    X, y, w = data["train_X"], data["train_y"], data["train_w"]

    # Train base models on full training data
    print("  Training XGBoost...")
    xgb_model = xgb.XGBRegressor(
        multi_strategy="multi_output_tree", tree_method="hist",
        objective="reg:squarederror", n_jobs=-1, verbosity=0, **xgb_params)
    xgb_model.fit(X, y, sample_weight=w)

    print("  Training CatBoost...")
    cat_models = []
    for c in range(NUM_CLASSES):
        target = y[:, c]
        if target.max() - target.min() < 1e-8:
            cat_models.append(None)
            continue
        m = CatBoostRegressor(loss_function="RMSE", verbose=0, thread_count=-1, **cat_params)
        m.fit(X, target, sample_weight=w)
        cat_models.append(m)

    print("  Training LightGBM...")
    lgb_models = []
    for c in range(NUM_CLASSES):
        m = LGBMRegressor(verbosity=-1, n_jobs=-1, **lgb_params)
        m.fit(X, y[:, c], sample_weight=w)
        lgb_models.append(m)

    def xgb_pred(X):
        return xgb_model.predict(X)

    def cat_pred(X):
        return np.column_stack([
            np.zeros(len(X)) if m is None else m.predict(X) for m in cat_models])

    def lgb_pred(X):
        return np.column_stack([m.predict(X) for m in lgb_models])

    # Generate stacking features: predictions from each base model on training data
    print("  Generating stacking features...")
    p_xgb = xgb_pred(X)
    p_cat = cat_pred(X)
    p_lgb = lgb_pred(X)

    # Stack: (N, 18) = 3 models × 6 classes
    stack_X = np.hstack([p_xgb, p_cat, p_lgb])

    # Train meta-model (one per class)
    print("  Training meta-models...")
    meta_models = []
    for c in range(NUM_CLASSES):
        meta = Ridge(alpha=1.0)
        meta.fit(stack_X, y[:, c], sample_weight=w)
        meta_models.append(meta)

    def stacking_predict(X_new):
        p1 = xgb_pred(X_new)
        p2 = cat_pred(X_new)
        p3 = lgb_pred(X_new)
        stack = np.hstack([p1, p2, p3])
        return np.column_stack([m.predict(stack) for m in meta_models])

    return stacking_predict, xgb_pred, cat_pred, lgb_pred


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--n-trials", type=int, default=100)
    args = parser.parse_args()

    print("Precomputing features...")
    data = precompute()
    print(f"Train: {data['train_X'].shape}, Val rounds: {VAL_ROUNDS}\n")

    # ── 1. Optuna for CatBoost ──
    print("=" * 60)
    print("CATBOOST OPTUNA SEARCH")
    print("=" * 60)
    cat_study = optuna.create_study(study_name="catboost", direction="maximize")
    cat_study.optimize(lambda t: objective_catboost(t, data), n_trials=args.n_trials)
    cat_best = cat_study.best_trial
    print(f"\nBest CatBoost: {cat_best.value:.2f}")
    for rn in VAL_ROUNDS:
        print(f"  R{rn}: {cat_best.user_attrs[f'R{rn}']:.2f}")
    print(f"  Params: {cat_best.params}")

    cat_params = {
        "iterations": cat_best.params["iterations"],
        "depth": cat_best.params["depth"],
        "learning_rate": cat_best.params["learning_rate"],
        "l2_leaf_reg": cat_best.params["l2_leaf_reg"],
        "subsample": cat_best.params["subsample"],
    }

    # ── 2. Optuna for LightGBM ──
    print("\n" + "=" * 60)
    print("LIGHTGBM OPTUNA SEARCH")
    print("=" * 60)
    lgb_study = optuna.create_study(study_name="lightgbm", direction="maximize")
    lgb_study.optimize(lambda t: objective_lightgbm(t, data), n_trials=args.n_trials)
    lgb_best = lgb_study.best_trial
    print(f"\nBest LightGBM: {lgb_best.value:.2f}")
    for rn in VAL_ROUNDS:
        print(f"  R{rn}: {lgb_best.user_attrs[f'R{rn}']:.2f}")
    print(f"  Params: {lgb_best.params}")

    lgb_params = {
        "n_estimators": lgb_best.params["n_estimators"],
        "max_depth": lgb_best.params["max_depth"],
        "learning_rate": lgb_best.params["learning_rate"],
        "subsample": lgb_best.params["subsample"],
        "colsample_bytree": lgb_best.params["colsample_bytree"],
        "reg_alpha": lgb_best.params["reg_alpha"],
        "reg_lambda": lgb_best.params["reg_lambda"],
        "min_child_samples": lgb_best.params["min_child_samples"],
    }

    # ── 3. Stacking ensemble ──
    print("\n" + "=" * 60)
    print("STACKING ENSEMBLE")
    print("=" * 60)

    xgb_params = json.load(open(Path(__file__).parent / "best_params.json"))
    # Filter to XGBoost-relevant params only
    xgb_relevant = {k: v for k, v in xgb_params.items()
                    if k in ["n_estimators", "max_depth", "learning_rate", "subsample",
                             "colsample_bytree", "reg_alpha", "reg_lambda", "min_child_weight"]}

    stacking_pred, xgb_pred, cat_pred_fn, lgb_pred_fn = build_stacking(
        data, xgb_relevant, cat_params, lgb_params)

    # Evaluate all
    print("\n── Results ──")
    for name, fn in [("XGBoost", xgb_pred), ("CatBoost", cat_pred_fn),
                     ("LightGBM", lgb_pred_fn), ("Stacking", stacking_pred)]:
        scores = evaluate_model(fn, data)
        r_str = "  ".join(f"R{rn}={s:.2f}" for rn, s in zip(VAL_ROUNDS, scores))
        print(f"  {name:<12} avg={np.mean(scores):.2f}  {r_str}")

    # Save all params
    all_params = {
        "xgboost": xgb_relevant,
        "catboost": cat_params,
        "lightgbm": lgb_params,
    }
    out_path = Path(__file__).parent / "best_params_all.json"
    with open(out_path, "w") as f:
        json.dump(all_params, f, indent=2)
    print(f"\nSaved all params to {out_path}")


if __name__ == "__main__":
    main()
