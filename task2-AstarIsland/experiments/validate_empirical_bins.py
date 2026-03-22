"""Validate empirical bin approach on round 6.

Round 6 has observations + ground truth. We train the base model on rounds 1-5,
then test: does blending with empirical bins from round 6 observations improve scores?
"""

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))

from astar.types import MapState, RoundStats, Observation, NUM_CLASSES
from astar.calibration import compute_round_stats_from_ground_truth
from astar.predictor import Predictor
from astar.scoring import score_prediction
from astar.empirical_bins import (
    build_empirical_distributions,
    predict_with_empirical_bins,
    get_bin_coverage_stats,
)
import store

DATA_DIR = Path(__file__).parent / "data" / "rounds"
TRAIN_ROUNDS = list(range(1, 6))
TEST_ROUND = 6
SEEDS = list(range(5))


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
    return RoundStats(
        ruin_rate=np.mean([s.ruin_rate for s in stats]),
        settlement_rate=np.mean([s.settlement_rate for s in stats]),
        port_rate=np.mean([s.port_rate for s in stats]),
        expansion_distance=np.mean([s.expansion_distance for s in stats]),
        forest_rate=np.mean([s.forest_rate for s in stats]),
        empty_rate=np.mean([s.empty_rate for s in stats]),
        settlement_to_ruin_ratio=np.mean([s.settlement_to_ruin_ratio for s in stats]),
    )


def load_observations_as_typed(rn, si) -> list[Observation]:
    """Load stored observations and convert to Observation dataclass."""
    raw_list = store.list_observations(rn, si)
    observations = []
    for raw in raw_list:
        vp = raw["viewport"]
        observations.append(Observation(
            grid=np.array(raw["grid"]),
            settlements=raw.get("settlements", []),
            viewport=(vp["x"], vp["y"], vp["w"], vp["h"]),
            seed_index=si,
        ))
    return observations


def main():
    print("=" * 60)
    print("EMPIRICAL BINS VALIDATION — ROUND 6")
    print("=" * 60)

    # Train base model on rounds 1-5
    print("\nTraining base model on rounds 1-5...")
    train_states, train_gts, train_stats = [], [], []
    for rn in TRAIN_ROUNDS:
        stats = round_stats_avg(rn)
        for si in SEEDS:
            s, gt = load_map(rn, si)
            train_states.append(s)
            train_gts.append(gt)
            train_stats.append(stats)

    model = Predictor()
    model.fit(train_states, train_gts, train_stats)

    r6_stats = round_stats_avg(TEST_ROUND)

    # Load all round 6 data
    r6_states = []
    r6_gts = []
    all_observations = []

    for si in SEEDS:
        state, gt = load_map(TEST_ROUND, si)
        r6_states.append(state)
        r6_gts.append(gt)
        all_observations.extend(load_observations_as_typed(TEST_ROUND, si))

    # Build empirical bins from ALL round 6 observations
    print(f"\nBuilding empirical bins from {len(all_observations)} observations...")
    bin_dists = build_empirical_distributions(all_observations, r6_states)
    bin_coverage = get_bin_coverage_stats(all_observations, r6_states)

    print(f"  Bins with enough data: {len(bin_dists)}")
    print(f"  Total bin keys: {len(bin_coverage)}")
    for key in sorted(bin_coverage, key=bin_coverage.get, reverse=True)[:15]:
        has_dist = "YES" if key in bin_dists else "no"
        print(f"    {key:<25} count={bin_coverage[key]:>5}  empirical={has_dist}")

    # Score: model only vs model + empirical bins at different blend weights
    print("\n── Score comparison ──")
    print(f"{'Approach':<40} {'S0':>6} {'S1':>6} {'S2':>6} {'S3':>6} {'S4':>6} {'Avg':>6}")
    print("-" * 76)

    # A) Model only
    model_scores = []
    for si in SEEDS:
        pred = model.predict(r6_states[si], r6_stats)
        s = score_prediction(pred.probs, r6_gts[si])
        model_scores.append(s)
    print(f"{'Model only':<40}", " ".join(f"{s:>6.2f}" for s in model_scores), f"{np.mean(model_scores):>6.2f}")

    # B) Empirical bins at different blend weights
    for weight in [0.3, 0.5, 0.7, 0.85, 1.0]:
        scores = []
        for si in SEEDS:
            base_pred = model.predict(r6_states[si], r6_stats)
            blended = predict_with_empirical_bins(
                r6_states[si], bin_dists, base_pred, blend_weight=weight
            )
            s = score_prediction(blended.probs, r6_gts[si])
            scores.append(s)
        label = f"Empirical bins (w={weight})"
        print(f"{label:<40}", " ".join(f"{s:>6.2f}" for s in scores), f"{np.mean(scores):>6.2f}")

    # C) Pure empirical (no model)
    scores = []
    for si in SEEDS:
        base_pred = model.predict(r6_states[si], r6_stats)
        blended = predict_with_empirical_bins(
            r6_states[si], bin_dists, base_pred, blend_weight=1.0
        )
        s = score_prediction(blended.probs, r6_gts[si])
        scores.append(s)

    print()
    print("=" * 60)


if __name__ == "__main__":
    main()
