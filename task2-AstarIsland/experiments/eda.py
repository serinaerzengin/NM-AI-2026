"""Exploratory Data Analysis on historical Astar Island data.

Loads all completed rounds' initial states + ground truths and prints
key statistics to inform feature design and modeling.
"""

import json
import sys
from pathlib import Path
from collections import defaultdict

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from astar.types import MapState, CLASS_SETTLEMENT, CLASS_PORT, CLASS_RUIN, CLASS_FOREST, CLASS_MOUNTAIN, CLASS_EMPTY
from astar.features import compute_features
from astar.calibration import compute_round_stats_from_ground_truth

DATA_DIR = Path(__file__).parent / "data" / "rounds"
ROUNDS = range(1, 6)
SEEDS = range(5)


def load_map(round_num: int, seed: int) -> tuple[MapState, np.ndarray]:
    seed_dir = DATA_DIR / f"round_{round_num}" / f"seed_{seed}"
    with open(seed_dir / "initial_state.json") as f:
        raw = json.load(f)
    with open(seed_dir / "ground_truth.json") as f:
        gt_raw = json.load(f)
    state = MapState(grid=np.array(raw["grid"]), settlements=raw["settlements"])
    ground_truth = np.array(gt_raw["ground_truth"])
    return state, ground_truth


def cell_entropy(gt: np.ndarray) -> np.ndarray:
    eps = 1e-12
    return -np.sum(gt * np.log(gt + eps), axis=-1)


def main():
    print("=" * 60)
    print("ASTAR ISLAND — EXPLORATORY DATA ANALYSIS")
    print("=" * 60)

    # ── 1. Per-round aggregate stats ──────────────────────────
    print("\n── 1. Per-Round Aggregate Stats ──")
    print(f"{'Round':<8} {'Ruin%':>8} {'Settle%':>8} {'Port%':>8} {'Expansion':>10} {'Dynamic':>8}")
    print("-" * 55)

    all_round_stats = {}
    for rn in ROUNDS:
        round_ruin, round_settle, round_port, round_exp = [], [], [], []
        round_dynamic = []
        for si in SEEDS:
            state, gt = load_map(rn, si)
            stats = compute_round_stats_from_ground_truth(gt, state)
            round_ruin.append(stats.ruin_rate)
            round_settle.append(stats.settlement_rate)
            round_port.append(stats.port_rate)
            round_exp.append(stats.expansion_distance)
            ent = cell_entropy(gt)
            round_dynamic.append((ent > 0.1).sum())

        avg = lambda lst: sum(lst) / len(lst)
        all_round_stats[rn] = {
            "ruin": avg(round_ruin), "settle": avg(round_settle),
            "port": avg(round_port), "expansion": avg(round_exp),
            "dynamic": avg(round_dynamic),
        }
        s = all_round_stats[rn]
        print(f"  R{rn:<5} {s['ruin']:>7.3f} {s['settle']:>8.3f} {s['port']:>8.3f} {s['expansion']:>10.2f} {s['dynamic']:>8.0f}")

    # Cross-round variance
    print("\n  Std across rounds:")
    for key in ["ruin", "settle", "port", "expansion"]:
        vals = [all_round_stats[rn][key] for rn in ROUNDS]
        print(f"    {key:>10}: mean={np.mean(vals):.4f}  std={np.std(vals):.4f}")

    # ── 2. Dynamic cell counts ────────────────────────────────
    print("\n── 2. Dynamic Cell Counts ──")
    for rn in ROUNDS:
        for si in SEEDS:
            _, gt = load_map(rn, si)
            ent = cell_entropy(gt)
            n_dynamic = (ent > 0.1).sum()
            n_total = gt.shape[0] * gt.shape[1]
            print(f"  R{rn} S{si}: {n_dynamic:>4}/{n_total} dynamic ({100*n_dynamic/n_total:.1f}%)")

    # ── 3. Outcome distributions by distance-to-settlement ────
    print("\n── 3. Outcome by Distance to Nearest Settlement ──")
    dist_bins = [(0, 0.5), (0.5, 1.5), (1.5, 2.5), (2.5, 4.5), (4.5, 7.5), (7.5, 99)]
    bin_labels = ["0", "1", "2", "3-4", "5-7", "8+"]
    class_names = ["Empty", "Settle", "Port", "Ruin", "Forest", "Mountain"]

    # Collect across all maps
    bin_probs = {label: [] for label in bin_labels}
    for rn in ROUNDS:
        for si in SEEDS:
            state, gt = load_map(rn, si)
            feats = compute_features(state)
            dist = feats[:, :, 6]  # dist_nearest_settlement
            for (lo, hi), label in zip(dist_bins, bin_labels):
                mask = (dist >= lo) & (dist < hi)
                if mask.any():
                    bin_probs[label].append(gt[mask].mean(axis=0))

    print(f"{'Dist':<8}", end="")
    for cn in class_names:
        print(f"{cn:>9}", end="")
    print(f"  {'Count':>6}")
    print("-" * 70)

    for label in bin_labels:
        if bin_probs[label]:
            avg_prob = np.mean(bin_probs[label], axis=0)
            count = len(bin_probs[label])
            print(f"  {label:<6}", end="")
            for p in avg_prob:
                print(f"{p:>9.3f}", end="")
            print(f"  {count:>6}")

    # ── 4. Cross-round variance by cell features ──────────────
    print("\n── 4. Cross-Round Variance (same feature bin, different rounds) ──")
    print("  For cells with similar features, how much do distributions vary across rounds?")
    print()

    # Group cells by (distance_bin, is_coastal) across rounds
    feature_groups = defaultdict(lambda: defaultdict(list))  # (dist_bin, coastal) → round → [distributions]

    for rn in ROUNDS:
        for si in SEEDS:
            state, gt = load_map(rn, si)
            feats = compute_features(state)
            dist = feats[:, :, 6]
            coastal = feats[:, :, 11] > 0  # adjacent_ocean > 0
            ent = cell_entropy(gt)

            for (lo, hi), label in zip(dist_bins, bin_labels):
                for is_coastal in [False, True]:
                    mask = (dist >= lo) & (dist < hi) & (coastal == is_coastal) & (ent > 0.1)
                    if mask.any():
                        avg_dist = gt[mask].mean(axis=0)
                        feature_groups[(label, is_coastal)][rn].append(avg_dist)

    print(f"{'Group':<20} {'Within-round std':>18} {'Between-round std':>18} {'Ratio (B/W)':>12}")
    print("-" * 72)

    for (dist_label, is_coastal), round_data in sorted(feature_groups.items()):
        if len(round_data) < 3:
            continue
        coastal_str = "coastal" if is_coastal else "inland"
        group_name = f"d={dist_label} {coastal_str}"

        # Per-round mean distributions
        round_means = []
        within_stds = []
        for rn, dists in round_data.items():
            arr = np.array(dists)
            round_means.append(arr.mean(axis=0))
            within_stds.append(arr.std(axis=0).mean())

        round_means = np.array(round_means)
        between_std = round_means.std(axis=0).mean()
        within_std = np.mean(within_stds)

        ratio = between_std / within_std if within_std > 1e-6 else float("inf")
        print(f"  {group_name:<18} {within_std:>18.4f} {between_std:>18.4f} {ratio:>12.2f}")

    print()
    print("  Ratio > 1 → hidden params matter more than map-to-map variance")
    print("  Ratio < 1 → map layout dominates, hidden params are secondary")

    # ── 5. Initial settlement counts per map ──────────────────
    print("\n── 5. Initial Settlement Counts ──")
    for rn in ROUNDS:
        for si in SEEDS:
            state, _ = load_map(rn, si)
            n_settlements = len(state.settlements)
            n_ports = sum(1 for s in state.settlements if s.get("has_port"))
            print(f"  R{rn} S{si}: {n_settlements} settlements ({n_ports} ports)")

    print("\n" + "=" * 60)
    print("EDA COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
