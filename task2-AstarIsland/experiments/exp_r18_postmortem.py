"""R18 postmortem: what could we have done better?

Compares our actual submission against:
  1. Model with ground-truth stats (perfect obs_stats)
  2. Different k values
  3. Different obs_weight (adaptive blending)
  4. Model-only (no empirical bins)
  5. Oracle bins (bins built from ground truth)
"""

import json
import sys
from pathlib import Path
from collections import defaultdict

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

from astar.types import (
    MapState, Observation, RoundStats, Prediction, NUM_CLASSES,
    OCEAN, MOUNTAIN, TERRAIN_TO_CLASS, CLASS_EMPTY,
)
from astar.features import compute_features, FEATURE_NAMES
from astar.calibration import (
    compute_round_stats_from_ground_truth,
    compute_round_stats_from_observations,
    round_stats_to_array,
)
from astar.scoring import score_prediction
from astar.predictor import _build_row, _static_prediction, _is_static_cell, PROB_FLOOR
from astar.empirical_bins import (
    build_empirical_distributions, predict_with_empirical_bins,
    get_bin_coverage_stats,
)
from catboost import CatBoostRegressor
import store

DATA_DIR = Path(__file__).parent.parent / "data" / "rounds"
BEST_PARAMS_PATH = Path(__file__).parent.parent / "best_params_all.json"
SEEDS = list(range(5))
ROUND = 18


def get_all_rounds():
    rounds = []
    for d in sorted(DATA_DIR.iterdir()):
        if d.is_dir() and d.name.startswith("round_"):
            rn = int(d.name.split("_")[1])
            if (d / "seed_0" / "ground_truth.json").exists():
                rounds.append(rn)
    return rounds


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


def load_observations(rn, si):
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


def load_catboost_params():
    if BEST_PARAMS_PATH.exists():
        with open(BEST_PARAMS_PATH) as f:
            return json.load(f).get("catboost", {})
    return {"iterations": 200, "depth": 5, "learning_rate": 0.1}


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


def predict_map(models, state, round_stats):
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
    probs = np.maximum(probs, PROB_FLOOR)
    probs = probs / probs.sum(axis=-1, keepdims=True)
    return Prediction(probs=probs)


def sigmoid(x):
    return 1.0 / (1.0 + np.exp(-np.clip(x, -20, 20)))


def blend_stats(obs_stats, hist_stats, obs_weight):
    fields = ["ruin_rate", "settlement_rate", "port_rate", "expansion_distance",
              "forest_rate", "empty_rate", "settlement_to_ruin_ratio"]
    return RoundStats(**{
        f: obs_weight * getattr(obs_stats, f) + (1 - obs_weight) * getattr(hist_stats, f)
        for f in fields
    })


def build_oracle_bins(states, gts):
    """Build empirical bins from ground truth (oracle — unlimited observations)."""
    from astar.empirical_bins import _cell_bin_key, _cell_bin_key_coarse, MIN_BIN_COUNT
    bin_counts_raw = defaultdict(lambda: np.zeros(NUM_CLASSES, dtype=np.float64))

    for si in range(len(states)):
        feat_map = compute_features(states[si])
        gt = gts[si]
        h, w = gt.shape[:2]
        for r in range(h):
            for c in range(w):
                cell_feats = feat_map[r, c]
                # Weight by ground truth distribution (simulates many observations)
                fine_key = _cell_bin_key(cell_feats)
                if fine_key is not None:
                    bin_counts_raw[fine_key] += gt[r, c] * 100  # simulate 100 observations
                coarse_key = _cell_bin_key_coarse(cell_feats)
                if coarse_key is not None:
                    bin_counts_raw[coarse_key] += gt[r, c] * 100

    bin_distributions = {}
    raw_counts = {}
    for key, counts in bin_counts_raw.items():
        total = counts.sum()
        raw_counts[key] = int(total)
        if total >= MIN_BIN_COUNT:
            dist = counts / total
            dist = np.maximum(dist, PROB_FLOOR)
            dist = dist / dist.sum()
            bin_distributions[key] = dist.astype(np.float32)

    return bin_distributions, raw_counts


def main():
    all_rounds = get_all_rounds()
    train_rounds = [r for r in all_rounds if r != ROUND]

    print(f"R{ROUND} Postmortem Analysis")
    print(f"{'═' * 65}\n")

    # Train model
    print("Training CatBoost on all other rounds...")
    models = train_catboost(train_rounds)

    # Load R18 data
    states, gts = [], []
    all_obs = []
    for si in SEEDS:
        state, gt = load_map(ROUND, si)
        states.append(state)
        gts.append(gt)
        all_obs.extend(load_observations(ROUND, si))

    # Ground truth stats
    gt_stats_list = [compute_round_stats_from_ground_truth(gts[si], states[si]) for si in SEEDS]
    fields = ["ruin_rate", "settlement_rate", "port_rate", "expansion_distance",
              "forest_rate", "empty_rate", "settlement_to_ruin_ratio"]
    gt_stats = RoundStats(**{f: np.mean([getattr(s, f) for s in gt_stats_list]) for f in fields})

    # Obs stats
    obs_stats = compute_round_stats_from_observations(all_obs, states[0])

    # Historical avg stats
    hist_stats_list = []
    for rn in train_rounds:
        for si in SEEDS:
            s, gt = load_map(rn, si)
            hist_stats_list.append(compute_round_stats_from_ground_truth(gt, s))
    hist_stats = RoundStats(**{f: np.mean([getattr(s, f) for s in hist_stats_list]) for f in fields})

    # Adaptive blending (what we actually did)
    adapt_a, adapt_b, adapt_c = -15.28, 0.58, 4.41
    divergence = abs(obs_stats.settlement_rate - hist_stats.settlement_rate) / (hist_stats.settlement_rate + 1e-6)
    actual_obs_weight = sigmoid(adapt_a * obs_stats.settlement_rate + adapt_b * divergence + adapt_c)
    actual_blended = blend_stats(obs_stats, hist_stats, actual_obs_weight)

    print(f"\n  Stats comparison:")
    print(f"    {'':20s} {'settle':>8s} {'ruin':>8s} {'port':>8s} {'forest':>8s} {'empty':>8s}")
    print(f"    {'Observed':20s} {obs_stats.settlement_rate:8.3f} {obs_stats.ruin_rate:8.3f} {obs_stats.port_rate:8.3f} {obs_stats.forest_rate:8.3f} {obs_stats.empty_rate:8.3f}")
    print(f"    {'Historical avg':20s} {hist_stats.settlement_rate:8.3f} {hist_stats.ruin_rate:8.3f} {hist_stats.port_rate:8.3f} {hist_stats.forest_rate:8.3f} {hist_stats.empty_rate:8.3f}")
    print(f"    {'Blended (w={actual_obs_weight:.3f})':20s} {actual_blended.settlement_rate:8.3f} {actual_blended.ruin_rate:8.3f} {actual_blended.port_rate:8.3f} {actual_blended.forest_rate:8.3f} {actual_blended.empty_rate:8.3f}")
    print(f"    {'Ground truth':20s} {gt_stats.settlement_rate:8.3f} {gt_stats.ruin_rate:8.3f} {gt_stats.port_rate:8.3f} {gt_stats.forest_rate:8.3f} {gt_stats.empty_rate:8.3f}")

    # Empirical bins from observations
    bin_dists = build_empirical_distributions(all_obs, states)
    bin_counts = get_bin_coverage_stats(all_obs, states)

    # Oracle bins
    oracle_bins, oracle_counts = build_oracle_bins(states, gts)

    print(f"\n  Bins: {len(bin_dists)} from observations, {len(oracle_bins)} oracle")

    # Test various configurations
    configs = []

    # 1. What we actually submitted (reconstructed)
    configs.append(("Actual submission (blended stats, obs bins, k=49)",
                     actual_blended, bin_dists, bin_counts, 49))

    # 2. With ground truth stats
    configs.append(("GT stats + obs bins, k=49",
                     gt_stats, bin_dists, bin_counts, 49))

    # 3. With pure obs stats (no blending)
    configs.append(("Pure obs stats + obs bins, k=49",
                     obs_stats, bin_dists, bin_counts, 49))

    # 4. With historical stats only
    configs.append(("Historical stats + obs bins, k=49",
                     hist_stats, bin_dists, bin_counts, 49))

    # 5. Model only (no bins)
    configs.append(("GT stats, no bins",
                     gt_stats, {}, {}, 49))

    # 6. Model only with blended stats
    configs.append(("Blended stats, no bins",
                     actual_blended, {}, {}, 49))

    # 7. Oracle bins
    configs.append(("GT stats + oracle bins, k=49",
                     gt_stats, oracle_bins, oracle_counts, 49))

    # 8. Different k values with obs bins
    for k in [20, 30, 49, 80, 150, 300]:
        configs.append((f"Blended stats + obs bins, k={k}",
                         actual_blended, bin_dists, bin_counts, k))

    # 9. Different obs_weights
    for ow in [0.0, 0.1, 0.238, 0.5, 0.7, 0.9, 1.0]:
        blended = blend_stats(obs_stats, hist_stats, ow)
        configs.append((f"obs_weight={ow:.1f} + obs bins, k=49",
                         blended, bin_dists, bin_counts, 49))

    print(f"\n{'─' * 75}")
    print(f"  {'Configuration':<45s} {'Seed scores':>30s} {'Avg':>6s}")
    print(f"{'─' * 75}")

    for name, stats, bins, bcounts, k in configs:
        seed_scores = []
        for si in SEEDS:
            base_pred = predict_map(models, states[si], stats)
            if bins:
                final = predict_with_empirical_bins(states[si], bins, base_pred, bin_counts=bcounts, k=k)
            else:
                final = base_pred
            seed_scores.append(score_prediction(final.probs, gts[si]))

        scores_str = " ".join(f"{s:.1f}" for s in seed_scores)
        avg = np.mean(seed_scores)
        print(f"  {name:<45s} {scores_str:>30s} {avg:>6.2f}")

    print(f"{'─' * 75}")


if __name__ == "__main__":
    main()
