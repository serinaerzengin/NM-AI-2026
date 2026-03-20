"""Shared evaluation harness for model experiments.

Every experiment uses this to ensure identical train/val splits and scoring.

Usage:
    from eval_harness import load_train_val, evaluate_predictions, print_results

Train: rounds 1-5 (25 maps)
Val: rounds 6+7 (10 maps, with observations + empirical bins)
"""

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

from astar.types import MapState, Observation, RoundStats, NUM_CLASSES, OCEAN, MOUNTAIN
from astar.features import compute_features
from astar.calibration import compute_round_stats_from_ground_truth, compute_round_stats_from_observations, round_stats_to_array
from astar.scoring import score_prediction
from astar.predictor import _build_row, _static_prediction, _is_static_cell
from astar.empirical_bins import (
    build_empirical_distributions, predict_with_empirical_bins,
    get_bin_coverage_stats,
)
import store

DATA_DIR = Path(__file__).parent.parent / "data" / "rounds"
TRAIN_ROUNDS = list(range(1, 6))
VAL_ROUNDS = [6, 7]
SEEDS = list(range(5))

_cache = {}


def _load_map(rn, si):
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


def _round_stats_avg(rn):
    stats = []
    for si in SEEDS:
        s, gt = _load_map(rn, si)
        stats.append(compute_round_stats_from_ground_truth(gt, s))
    fields = [
        "ruin_rate", "settlement_rate", "port_rate", "expansion_distance",
        "forest_rate", "empty_rate", "settlement_to_ruin_ratio",
    ]
    return RoundStats(**{f: np.mean([getattr(s, f) for s in stats]) for f in fields})


def _load_obs(rn, si):
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


def load_train_val():
    """Load training and validation data.

    Returns:
        train_X: (N, D) feature matrix for training cells
        train_y: (N, 6) target distributions
        train_w: (N,) entropy-based sample weights
        val_data: dict with per-round validation info
    """
    X_rows, y_rows, w_rows = [], [], []

    for rn in TRAIN_ROUNDS:
        stats = _round_stats_avg(rn)
        stats_arr = round_stats_to_array(stats)
        for si in SEEDS:
            state, gt = _load_map(rn, si)
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

    train_X = np.array(X_rows, dtype=np.float32)
    train_y = np.array(y_rows, dtype=np.float32)
    train_w = np.array(w_rows, dtype=np.float32)

    # Validation data
    val_data = {}
    for rn in VAL_ROUNDS:
        states = []
        all_obs = []
        for si in SEEDS:
            state, _ = _load_map(rn, si)
            states.append(state)
            all_obs.extend(_load_obs(rn, si))

        obs_stats = compute_round_stats_from_observations(all_obs, states[0])
        bin_dists = build_empirical_distributions(all_obs, states)
        bin_counts = get_bin_coverage_stats(all_obs, states)

        val_seeds = []
        for si in SEEDS:
            state, gt = _load_map(rn, si)
            features = compute_features(state)
            stats_arr = round_stats_to_array(obs_stats)

            # Collect dynamic cells for prediction
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
                "state": state,
                "gt": gt,
                "features": features,
                "dynamic_indices": dynamic_indices,
                "X_pred": np.array(X_pred, dtype=np.float32) if X_pred else np.empty((0, train_X.shape[1]), dtype=np.float32),
                "static_preds": static_preds,
            })

        val_data[rn] = {
            "seeds": val_seeds,
            "obs_stats": obs_stats,
            "bin_dists": bin_dists,
            "bin_counts": bin_counts,
        }

    return train_X, train_y, train_w, val_data


def evaluate_predictions(val_data, predict_fn, prob_floor=0.001, k=None):
    """Evaluate a model on validation rounds.

    Args:
        val_data: From load_train_val().
        predict_fn: Function(X) -> (N, 6) predictions for dynamic cells.
        prob_floor: Minimum probability floor.
        k: Empirical bin blend k. If None, uses adaptive k based on settlement rate.

    Returns:
        Dict with per-round and per-seed scores.
    """
    from astar.empirical_bins import _cell_bin_key, _cell_bin_key_coarse, PROB_FLOOR
    from astar.types import Prediction

    results = {}

    for rn, rd in val_data.items():
        bin_dists = rd["bin_dists"]
        bin_counts = rd["bin_counts"]
        settle_rate = rd["obs_stats"].settlement_rate

        if k is not None:
            use_k = k
        elif settle_rate < 0.05:
            use_k = 50
        elif settle_rate < 0.10:
            use_k = 100
        else:
            use_k = 361

        seed_scores = []
        for seed_data in rd["seeds"]:
            state = seed_data["state"]
            gt = seed_data["gt"]
            features = seed_data["features"]
            h, w = state.grid.shape
            probs = np.zeros((h, w, NUM_CLASSES), dtype=np.float32)

            # Static cells
            for (r, c), sp in seed_data["static_preds"].items():
                probs[r, c] = sp

            # Dynamic cells: model prediction
            X_pred = seed_data["X_pred"]
            if len(X_pred) > 0:
                preds = predict_fn(X_pred)
                for (r, c), pred in zip(seed_data["dynamic_indices"], preds):
                    probs[r, c] = pred

            # Empirical bin blending
            for r in range(h):
                for c in range(w):
                    if state.grid[r, c] in (OCEAN, MOUNTAIN):
                        continue
                    bin_key = _cell_bin_key(features[r, c])
                    if bin_key is None or bin_key not in bin_dists:
                        bin_key = _cell_bin_key_coarse(features[r, c])
                    if bin_key is not None and bin_key in bin_dists:
                        n = bin_counts.get(bin_key, 0)
                        weight = n / (n + use_k)
                        probs[r, c] = weight * bin_dists[bin_key] + (1 - weight) * probs[r, c]

            # Floor and normalize
            probs = np.maximum(probs, prob_floor)
            probs = probs / probs.sum(axis=-1, keepdims=True)

            seed_scores.append(score_prediction(probs, gt))

        results[rn] = {
            "scores": seed_scores,
            "avg": np.mean(seed_scores),
            "k_used": use_k,
        }

    return results


def print_results(name, results):
    """Pretty print evaluation results."""
    print(f"\n{'─' * 50}")
    print(f"  {name}")
    print(f"{'─' * 50}")
    total = []
    for rn in sorted(results):
        r = results[rn]
        scores_str = " ".join(f"{s:.1f}" for s in r["scores"])
        print(f"  R{rn}: {scores_str}  avg={r['avg']:.2f}  (k={r['k_used']})")
        total.append(r["avg"])
    print(f"  Overall avg: {np.mean(total):.2f}")
    print(f"{'─' * 50}")
    return np.mean(total)
