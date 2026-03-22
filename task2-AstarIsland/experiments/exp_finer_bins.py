"""Experiment: Finer bin features to reduce within-bin variance.

Current bins: distance × coastal × terrain × density(hi/lo)
V2 bins: + 3-level density + total_settlements split
"""

import json
import sys
from pathlib import Path
from collections import defaultdict

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

from astar.types import (
    MapState, Observation, RoundStats, NUM_CLASSES, OCEAN, MOUNTAIN,
    TERRAIN_TO_CLASS, CLASS_EMPTY,
)
from astar.features import compute_features, FEATURE_NAMES
from astar.calibration import (
    compute_round_stats_from_ground_truth, compute_round_stats_from_observations,
)
from astar.predictor import Predictor
from astar.scoring import score_prediction
from astar.empirical_bins import (
    build_empirical_distributions, predict_with_empirical_bins, get_bin_coverage_stats,
)
import store

DATA_DIR = Path(__file__).parent.parent / "data" / "rounds"
SEEDS = list(range(5))

_DIST = FEATURE_NAMES.index("dist_nearest_settlement")
_COASTAL = FEATURE_NAMES.index("adjacent_ocean")
_FOREST = FEATURE_NAMES.index("is_forest")
_MTN = FEATURE_NAMES.index("is_mountain")
_OCEAN = FEATURE_NAMES.index("is_ocean")
_SETTLE = FEATURE_NAMES.index("is_initial_settlement")
_SR5 = FEATURE_NAMES.index("settlements_r5")
_TOTAL = FEATURE_NAMES.index("total_settlements")

DIST_BINS = [(0, 0.5), (0.5, 1.5), (1.5, 2.5), (2.5, 4.5), (4.5, 7.5), (7.5, 99)]
DIST_LABELS = ["d0", "d1", "d2", "d3-4", "d5-7", "d8+"]
MIN_BIN = 10
PROB_FLOOR = 0.001


def _dist_label(dist):
    for (lo, hi), label in zip(DIST_BINS, DIST_LABELS):
        if lo <= dist < hi:
            return label
    return DIST_LABELS[-1]


def bin_key_v2(feats):
    """Finer bins: 3-level density + total settlements."""
    if feats[_OCEAN] > 0.5 or feats[_MTN] > 0.5:
        return None
    dl = _dist_label(feats[_DIST])
    coastal = "coast" if feats[_COASTAL] > 0.5 else "inland"
    terrain = "forest" if feats[_FOREST] > 0.5 else ("settle" if feats[_SETTLE] > 0.5 else "plain")
    sr5 = feats[_SR5]
    density = "hi" if sr5 >= 4 else ("mid" if sr5 >= 2 else "lo")
    total = "Thi" if feats[_TOTAL] >= 40 else "Tlo"
    return f"{dl}_{coastal}_{terrain}_{density}_{total}"


def bin_key_v2_coarse(feats):
    """Coarse fallback for v2."""
    if feats[_OCEAN] > 0.5 or feats[_MTN] > 0.5:
        return None
    dl = _dist_label(feats[_DIST])
    coastal = "coast" if feats[_COASTAL] > 0.5 else "inland"
    terrain = "forest" if feats[_FOREST] > 0.5 else ("settle" if feats[_SETTLE] > 0.5 else "plain")
    density = "hi" if feats[_SR5] >= 3 else "lo"
    return f"C_{dl}_{coastal}_{terrain}_{density}"


def build_bins_v2(observations, states):
    feature_maps = {}
    for obs in observations:
        si = obs.seed_index
        if si not in feature_maps:
            feature_maps[si] = compute_features(states[si])

    bin_counts = defaultdict(lambda: np.zeros(NUM_CLASSES, dtype=np.float64))
    bin_obs_counts = defaultdict(int)

    for obs in observations:
        si = obs.seed_index
        fm = feature_maps[si]
        vx, vy, vw, vh = obs.viewport
        for r in range(vh):
            for c in range(vw):
                ay, ax = vy + r, vx + c
                if ay >= 40 or ax >= 40:
                    continue
                code = int(obs.grid[r, c])
                cls = TERRAIN_TO_CLASS.get(code, CLASS_EMPTY)

                fine = bin_key_v2(fm[ay, ax])
                if fine:
                    bin_counts[fine][cls] += 1
                    bin_obs_counts[fine] += 1
                coarse = bin_key_v2_coarse(fm[ay, ax])
                if coarse:
                    bin_counts[coarse][cls] += 1
                    bin_obs_counts[coarse] += 1

    dists = {}
    for key, counts in bin_counts.items():
        total = counts.sum()
        if total >= MIN_BIN:
            d = counts / total
            d = np.maximum(d, PROB_FLOOR)
            d = d / d.sum()
            dists[key] = d.astype(np.float32)
    return dists, bin_obs_counts


def predict_v2(state, model_probs, bin_dists, bin_obs_counts, k=50):
    feats = compute_features(state)
    h, w = state.grid.shape
    probs = model_probs.copy()
    for r in range(h):
        for c in range(w):
            if state.grid[r, c] in (OCEAN, MOUNTAIN):
                continue
            bk = bin_key_v2(feats[r, c])
            if bk is None or bk not in bin_dists:
                bk = bin_key_v2_coarse(feats[r, c])
            if bk and bk in bin_dists:
                n = bin_obs_counts.get(bk, 0)
                weight = n / (n + k)
                probs[r, c] = weight * bin_dists[bk] + (1 - weight) * probs[r, c]
    probs = np.maximum(probs, PROB_FLOOR)
    probs = probs / probs.sum(axis=-1, keepdims=True)
    return probs


def load_map(rn, si):
    sd = DATA_DIR / f"round_{rn}" / f"seed_{si}"
    with open(sd / "initial_state.json") as f:
        raw = json.load(f)
    with open(sd / "ground_truth.json") as f:
        gt_raw = json.load(f)
    return MapState(grid=np.array(raw["grid"]), settlements=raw["settlements"]), np.array(gt_raw["ground_truth"])


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


def main():
    print("Training model on rounds 1-7...")
    best_params = json.load(open(Path(__file__).parent.parent / "best_params.json"))
    train_s, train_gt, train_st = [], [], []
    for rn in range(1, 8):
        st = round_stats_avg(rn)
        for si in SEEDS:
            s, g = load_map(rn, si)
            train_s.append(s)
            train_gt.append(g)
            train_st.append(st)
    model = Predictor(params=best_params)
    model.fit(train_s, train_gt, train_st)

    for test_rn in [8, 6]:
        print(f"\n=== Round {test_rn} ===")
        states = [load_map(test_rn, si)[0] for si in SEEDS]
        gts = [load_map(test_rn, si)[1] for si in SEEDS]
        all_obs = []
        for si in SEEDS:
            all_obs.extend(load_obs(test_rn, si))

        obs_stats = compute_round_stats_from_observations(all_obs, states[0])

        # Current bins
        curr_bins = build_empirical_distributions(all_obs, states)
        curr_counts = get_bin_coverage_stats(all_obs, states)

        # V2 bins
        v2_bins, v2_counts = build_bins_v2(all_obs, states)

        print(f"Current bins: {len(curr_bins)}, V2 bins: {len(v2_bins)}")

        for label, k_vals in [("Current", [50, 75, 100]), ("V2 finer", [50, 75, 100])]:
            for k in k_vals:
                scores = []
                for si in SEEDS:
                    pred = model.predict(states[si], obs_stats)
                    if label == "Current":
                        blended = predict_with_empirical_bins(
                            states[si], curr_bins, pred, bin_counts=curr_counts, k=k)
                        probs = blended.probs
                    else:
                        probs = predict_v2(states[si], pred.probs, v2_bins, v2_counts, k=k)
                    scores.append(score_prediction(probs, gts[si]))
                print(f"  {label} k={k:<4} avg={np.mean(scores):.2f}  ({' '.join(f'{s:.1f}' for s in scores)})")


if __name__ == "__main__":
    main()
