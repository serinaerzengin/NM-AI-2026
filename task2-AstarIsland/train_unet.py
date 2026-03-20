"""Train and evaluate the U-Net predictor on historical rounds.

Usage:
    python train_unet.py                        # defaults: train on R1-5, validate on R6-8
    python train_unet.py --epochs 120 --lr 5e-4
    python train_unet.py --base-ch 48           # wider model
    python train_unet.py --save unet.pt         # save checkpoint
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))

from astar.types import MapState, NUM_CLASSES, OCEAN, MOUNTAIN
from astar.features import compute_features
from astar.calibration import (
    compute_round_stats_from_ground_truth,
    compute_round_stats_from_observations,
    round_stats_to_array,
)
from astar.scoring import score_prediction
from astar.empirical_bins import (
    build_empirical_distributions,
    get_bin_coverage_stats,
    _cell_bin_key,
    _cell_bin_key_coarse,
)
from astar.unet_predictor import UNetPredictor
import store

DATA_DIR = Path(__file__).parent / "data" / "rounds"
TRAIN_ROUNDS = list(range(1, 6))
VAL_ROUNDS = [6, 7, 8]
SEEDS = list(range(5))
PROB_FLOOR = 0.001


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


def round_stats_avg(rn):
    from astar.types import RoundStats
    stats = []
    for si in SEEDS:
        _, gt = load_map(rn, si)
        s, _ = load_map(rn, si)
        stats.append(compute_round_stats_from_ground_truth(gt, s))
    fields = [
        "ruin_rate", "settlement_rate", "port_rate", "expansion_distance",
        "forest_rate", "empty_rate", "settlement_to_ruin_ratio",
    ]
    return RoundStats(**{f: np.mean([getattr(s, f) for s in stats]) for f in fields})


def load_obs(rn, si):
    from astar.types import Observation
    out = []
    for raw in store.list_observations(rn, si):
        if isinstance(raw, list):
            raw = raw[0]
        vp = raw["viewport"]
        out.append(Observation(
            grid=np.array(raw["grid"]),
            settlements=raw.get("settlements", []),
            viewport=(vp["x"], vp["y"], vp["w"], vp["h"]),
            seed_index=si,
        ))
    return out


def evaluate(predictor, val_rounds=VAL_ROUNDS):
    """Evaluate on validation rounds with empirical bin blending."""
    round_scores = []
    for rn in val_rounds:
        states, all_obs = [], []
        for si in SEEDS:
            state, _ = load_map(rn, si)
            states.append(state)
            all_obs.extend(load_obs(rn, si))

        obs_stats = compute_round_stats_from_observations(all_obs, states[0])
        bin_dists = build_empirical_distributions(all_obs, states)
        bin_counts = get_bin_coverage_stats(all_obs, states)

        settle_rate = obs_stats.settlement_rate
        if settle_rate < 0.05:
            k = 50
        elif settle_rate < 0.10:
            k = 100
        else:
            k = 361

        seed_scores = []
        for si in SEEDS:
            state, gt = load_map(rn, si)
            pred = predictor.predict(state, obs_stats)
            probs = pred.probs.copy()  # (40, 40, 6)

            # Blend with empirical bins
            features = compute_features(state)
            h, w = state.grid.shape
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

        avg = np.mean(seed_scores)
        round_scores.append(avg)
        print(f"  Round {rn}: {avg:.2f}  (seeds: {', '.join(f'{s:.2f}' for s in seed_scores)})")

    overall = np.mean(round_scores)
    print(f"  Average: {overall:.2f}")
    return round_scores


def main():
    parser = argparse.ArgumentParser(description="Train U-Net predictor")
    parser.add_argument("--epochs", type=int, default=80)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--base-ch", type=int, default=32)
    parser.add_argument("--weight-decay", type=float, default=1e-4)
    parser.add_argument("--no-augment", action="store_true")
    parser.add_argument("--save", type=str, default=None, help="Save checkpoint path")
    parser.add_argument("--train-rounds", type=str, default=None,
                        help="Comma-separated training round numbers (default: 1-5)")
    parser.add_argument("--val-rounds", type=str, default=None,
                        help="Comma-separated validation round numbers (default: 6,7,8)")
    args = parser.parse_args()

    train_rounds = [int(x) for x in args.train_rounds.split(",")] if args.train_rounds else TRAIN_ROUNDS
    val_rounds = [int(x) for x in args.val_rounds.split(",")] if args.val_rounds else VAL_ROUNDS

    # Load training data
    print(f"Loading training data (rounds {train_rounds})...")
    states, ground_truths, round_stats_list = [], [], []
    for rn in train_rounds:
        stats = round_stats_avg(rn)
        for si in SEEDS:
            state, gt = load_map(rn, si)
            states.append(state)
            ground_truths.append(gt)
            round_stats_list.append(stats)

    print(f"  {len(states)} maps loaded")

    # Train
    print(f"\nTraining U-Net (base_ch={args.base_ch}, epochs={args.epochs}, lr={args.lr})...")
    predictor = UNetPredictor(base_ch=args.base_ch)
    history = predictor.fit(
        states, ground_truths, round_stats_list,
        epochs=args.epochs,
        lr=args.lr,
        weight_decay=args.weight_decay,
        augment=not args.no_augment,
        verbose=True,
    )
    print(f"  Final train loss: {history['train_loss'][-1]:.4f}")

    # Evaluate
    print(f"\nEvaluating on validation rounds {val_rounds}...")
    evaluate(predictor, val_rounds)

    # Save
    if args.save:
        save_path = Path(__file__).parent / args.save
        predictor.save(str(save_path))
        print(f"\nCheckpoint saved to {save_path}")


if __name__ == "__main__":
    main()
