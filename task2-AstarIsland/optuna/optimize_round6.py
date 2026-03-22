"""Optimize the full prediction pipeline on round 6.

Simulates a realistic live round: base model + observation-derived round stats +
empirical bins + per-cell direct observations. No ground-truth cheating.
"""

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))

from astar.types import MapState, Observation, RoundStats, NUM_CLASSES, TERRAIN_TO_CLASS, CLASS_EMPTY, OCEAN, MOUNTAIN
from astar.features import compute_features, FEATURE_NAMES
from astar.calibration import (
    compute_round_stats_from_ground_truth,
    compute_round_stats_from_observations,
    round_stats_to_array,
)
from astar.predictor import Predictor
from astar.scoring import score_prediction
from astar.empirical_bins import (
    build_empirical_distributions,
    predict_with_empirical_bins,
    _cell_bin_key,
    PROB_FLOOR,
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


def load_observations(rn, si) -> list[Observation]:
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


def build_per_cell_observations(observations: list[Observation]) -> tuple[np.ndarray, np.ndarray]:
    """Build per-cell empirical distributions from direct observations.

    Returns:
        obs_counts: (40, 40, 6) count of each class observed per cell
        obs_total: (40, 40) total observations per cell
    """
    obs_counts = np.zeros((40, 40, NUM_CLASSES), dtype=np.float32)
    obs_total = np.zeros((40, 40), dtype=np.float32)

    for obs in observations:
        vx, vy, vw, vh = obs.viewport
        for r in range(vh):
            for c in range(vw):
                abs_y, abs_x = vy + r, vx + c
                if 0 <= abs_y < 40 and 0 <= abs_x < 40:
                    terrain_code = int(obs.grid[r, c])
                    cls = TERRAIN_TO_CLASS.get(terrain_code, CLASS_EMPTY)
                    obs_counts[abs_y, abs_x, cls] += 1
                    obs_total[abs_y, abs_x] += 1

    return obs_counts, obs_total


def predict_layered(
    state: MapState,
    model_probs: np.ndarray,
    bin_dists: dict[str, np.ndarray],
    obs_counts: np.ndarray,
    obs_total: np.ndarray,
    bin_weight: float = 0.5,
    direct_weight_per_obs: float = 0.15,
) -> np.ndarray:
    """Three-layer prediction: model → empirical bins → direct cell observations.

    Layer 1 (base): Model prediction for all cells.
    Layer 2 (bins): Override with empirical bin distribution where bins have data.
    Layer 3 (direct): Override with direct per-cell observations where available.

    The blend weights determine how much each layer overrides the previous.
    """
    features = compute_features(state)
    h, w = state.grid.shape
    probs = model_probs.copy()

    for r in range(h):
        for c in range(w):
            if state.grid[r, c] in (OCEAN, MOUNTAIN):
                continue

            current = probs[r, c].copy()

            # Layer 2: empirical bin
            bin_key = _cell_bin_key(features[r, c])
            if bin_key is not None and bin_key in bin_dists:
                empirical_bin = bin_dists[bin_key]
                current = (1 - bin_weight) * current + bin_weight * empirical_bin

            # Layer 3: direct per-cell observation
            n = obs_total[r, c]
            if n > 0:
                empirical_cell = obs_counts[r, c] / n
                # Weight increases with number of observations
                direct_weight = min(0.9, direct_weight_per_obs * n)
                current = (1 - direct_weight) * current + direct_weight * empirical_cell

            probs[r, c] = current

    # Floor and normalize
    probs = np.maximum(probs, PROB_FLOOR)
    probs = probs / probs.sum(axis=-1, keepdims=True)
    return probs


def main():
    print("=" * 70)
    print("ROUND 6 OPTIMIZATION — FULL PIPELINE SIMULATION")
    print("=" * 70)

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

    # Load round 6 data
    r6_states, r6_gts = [], []
    all_observations = []
    per_seed_observations = {}
    for si in SEEDS:
        state, gt = load_map(TEST_ROUND, si)
        r6_states.append(state)
        r6_gts.append(gt)
        obs = load_observations(TEST_ROUND, si)
        per_seed_observations[si] = obs
        all_observations.extend(obs)

    # Round stats: GT vs observation-derived
    gt_stats = round_stats_avg(TEST_ROUND)
    obs_stats = compute_round_stats_from_observations(all_observations, r6_states[0])
    print(f"\n  GT  round stats: settle={gt_stats.settlement_rate:.4f}, ruin={gt_stats.ruin_rate:.4f}, "
          f"port={gt_stats.port_rate:.4f}, expansion={gt_stats.expansion_distance:.2f}")
    print(f"  OBS round stats: settle={obs_stats.settlement_rate:.4f}, ruin={obs_stats.ruin_rate:.4f}, "
          f"port={obs_stats.port_rate:.4f}, expansion={obs_stats.expansion_distance:.2f}")

    # Build empirical bins from all observations
    bin_dists = build_empirical_distributions(all_observations, r6_states)
    print(f"\n  Empirical bins: {len(bin_dists)} bins")

    # Per-seed direct observation counts
    seed_obs_data = {}
    for si in SEEDS:
        counts, total = build_per_cell_observations(per_seed_observations[si])
        n_observed = (total > 0).sum()
        seed_obs_data[si] = (counts, total)
        print(f"  Seed {si}: {n_observed} cells directly observed")

    # ── Test configurations ──
    print("\n" + "=" * 70)
    print(f"{'Configuration':<55} {'S0':>5} {'S1':>5} {'S2':>5} {'S3':>5} {'S4':>5} {'Avg':>6}")
    print("-" * 87)

    configs = [
        # (label, use_obs_stats, bin_weight, direct_weight_per_obs)
        ("1. Model only (GT stats)", False, 0, 0),
        ("2. Model only (OBS stats)", True, 0, 0),
        ("3. Model + bins w=0.3 (OBS stats)", True, 0.3, 0),
        ("4. Model + bins w=0.5 (OBS stats)", True, 0.5, 0),
        ("5. Model + bins w=0.7 (OBS stats)", True, 0.7, 0),
        ("6. Model + direct only dw=0.15 (OBS stats)", True, 0, 0.15),
        ("7. Model + direct only dw=0.3 (OBS stats)", True, 0, 0.3),
        ("8. Model+bins0.5+direct0.15 (OBS stats)", True, 0.5, 0.15),
        ("9. Model+bins0.5+direct0.3 (OBS stats)", True, 0.5, 0.3),
        ("10. Model+bins0.3+direct0.2 (OBS stats)", True, 0.3, 0.2),
        ("11. Model+bins0.5+direct0.2 (OBS stats)", True, 0.5, 0.2),
        ("12. Model+bins0.7+direct0.2 (OBS stats)", True, 0.7, 0.2),
        ("13. Model+bins0.5+direct0.4 (OBS stats)", True, 0.5, 0.4),
        ("14. Model+bins0.3+direct0.3 (OBS stats)", True, 0.3, 0.3),
    ]

    best_avg = 0
    best_label = ""

    for label, use_obs, bw, dw in configs:
        stats = obs_stats if use_obs else gt_stats
        scores = []
        for si in SEEDS:
            base_pred = model.predict(r6_states[si], stats)
            obs_counts, obs_total = seed_obs_data[si]

            if bw == 0 and dw == 0:
                probs = base_pred.probs.copy()
                probs = np.maximum(probs, PROB_FLOOR)
                probs = probs / probs.sum(axis=-1, keepdims=True)
            else:
                probs = predict_layered(
                    r6_states[si], base_pred.probs, bin_dists,
                    obs_counts, obs_total,
                    bin_weight=bw, direct_weight_per_obs=dw,
                )

            scores.append(score_prediction(probs, r6_gts[si]))

        avg = np.mean(scores)
        marker = " <-- BEST" if avg > best_avg else ""
        if avg > best_avg:
            best_avg = avg
            best_label = label
        print(f"{label:<55} {scores[0]:>5.1f} {scores[1]:>5.1f} {scores[2]:>5.1f} {scores[3]:>5.1f} {scores[4]:>5.1f} {avg:>6.2f}{marker}")

    print("-" * 87)
    print(f"\nBest: {best_label} → {best_avg:.2f}")


if __name__ == "__main__":
    main()
