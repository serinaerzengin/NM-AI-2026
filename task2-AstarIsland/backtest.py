"""Leave-one-round-out backtest for the Astar Island predictor.

For each round, trains on the other 4 rounds and predicts the held-out round.
Reports per-seed and per-round scores.
"""

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from astar.types import MapState, RoundStats, NUM_CLASSES
from astar.calibration import compute_round_stats_from_ground_truth
from astar.predictor import Predictor
from astar.scoring import score_prediction

DATA_DIR = Path(__file__).parent / "data" / "rounds"
ROUNDS = list(range(1, 8))
SEEDS = list(range(5))


def load_map(round_num: int, seed: int) -> tuple[MapState, np.ndarray]:
    seed_dir = DATA_DIR / f"round_{round_num}" / f"seed_{seed}"
    with open(seed_dir / "initial_state.json") as f:
        raw = json.load(f)
    with open(seed_dir / "ground_truth.json") as f:
        gt_raw = json.load(f)
    state = MapState(grid=np.array(raw["grid"]), settlements=raw["settlements"])
    ground_truth = np.array(gt_raw["ground_truth"])
    return state, ground_truth


def compute_round_stats_avg(round_num: int) -> RoundStats:
    """Average RoundStats across all seeds of a round."""
    stats_list = []
    for si in SEEDS:
        state, gt = load_map(round_num, si)
        stats_list.append(compute_round_stats_from_ground_truth(gt, state))
    return RoundStats(
        ruin_rate=np.mean([s.ruin_rate for s in stats_list]),
        settlement_rate=np.mean([s.settlement_rate for s in stats_list]),
        port_rate=np.mean([s.port_rate for s in stats_list]),
        expansion_distance=np.mean([s.expansion_distance for s in stats_list]),
        forest_rate=np.mean([s.forest_rate for s in stats_list]),
        empty_rate=np.mean([s.empty_rate for s in stats_list]),
        settlement_to_ruin_ratio=np.mean([s.settlement_to_ruin_ratio for s in stats_list]),
    )


def uniform_score(ground_truth: np.ndarray) -> float:
    """Score of a uniform 1/6 prediction."""
    uniform = np.full_like(ground_truth, 1.0 / NUM_CLASSES)
    return score_prediction(uniform, ground_truth)


def main():
    print("=" * 60)
    print("ASTAR ISLAND — LEAVE-ONE-ROUND-OUT BACKTEST")
    print("=" * 60)

    # Preload all data
    all_data = {}
    all_round_stats = {}
    for rn in ROUNDS:
        all_round_stats[rn] = compute_round_stats_avg(rn)
        for si in SEEDS:
            all_data[(rn, si)] = load_map(rn, si)

    round_scores = []
    uniform_scores = []

    for test_round in ROUNDS:
        print(f"\n── Held-out Round {test_round} ──")
        train_rounds = [r for r in ROUNDS if r != test_round]

        # Build training data
        train_states = []
        train_gts = []
        train_stats = []

        for rn in train_rounds:
            stats = all_round_stats[rn]
            for si in SEEDS:
                state, gt = all_data[(rn, si)]
                train_states.append(state)
                train_gts.append(gt)
                train_stats.append(stats)

        # Train predictor
        predictor = Predictor()
        print(f"  Training on rounds {train_rounds} ({len(train_states)} maps)...")
        predictor.fit(train_states, train_gts, train_stats)

        # Predict held-out round
        test_stats = all_round_stats[test_round]
        seed_scores = []

        for si in SEEDS:
            state, gt = all_data[(test_round, si)]
            pred = predictor.predict(state, test_stats)
            s = score_prediction(pred.probs, gt)
            u = uniform_score(gt)
            seed_scores.append(s)
            uniform_scores.append(u)
            print(f"  Seed {si}: score={s:.2f}  (uniform={u:.2f})")

        avg = np.mean(seed_scores)
        round_scores.append(avg)
        print(f"  Round avg: {avg:.2f}")

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for rn, score in zip(ROUNDS, round_scores):
        print(f"  Round {rn}: {score:.2f}")
    print(f"\n  Overall avg: {np.mean(round_scores):.2f}")
    print(f"  Uniform avg: {np.mean(uniform_scores):.2f}")
    print("=" * 60)


if __name__ == "__main__":
    main()
