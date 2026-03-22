"""Experiment: Query strategy comparison.

Simulates different query allocation strategies on R8 ground truth
to measure how much query placement affects the final score.
"""

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

from astar.types import MapState, Observation, RoundStats, NUM_CLASSES
from astar.features import compute_features
from astar.calibration import compute_round_stats_from_ground_truth, compute_round_stats_from_observations
from astar.predictor import Predictor
from astar.scoring import score_prediction
from astar.empirical_bins import (
    build_empirical_distributions, predict_with_empirical_bins, get_bin_coverage_stats,
)
from astar.query_strategy import plan_viewports, allocate_queries

DATA_DIR = Path(__file__).parent.parent / "data" / "rounds"
SEEDS = list(range(5))
TEST_ROUND = 8


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


def simulate_observation(state, gt, vx, vy):
    """Create a fake observation by sampling one outcome per cell from ground truth."""
    grid = np.zeros((15, 15), dtype=int)
    for r in range(15):
        for c in range(15):
            ay, ax = vy + r, vx + c
            if ay >= 40 or ax >= 40:
                grid[r, c] = 10
                continue
            cls = np.random.choice(6, p=gt[ay, ax])
            grid[r, c] = [0, 1, 2, 3, 4, 5][cls]
    return grid


def strategy_current(states, gts, n_queries=50):
    """Current strategy: greedy settlement-focused, 1 query per viewport."""
    allocation = allocate_queries(states, n_queries)
    obs = []
    for si in range(5):
        viewports = plan_viewports(states[si], allocation[si])
        for vx, vy in viewports:
            grid = simulate_observation(states[si], gts[si], vx, vy)
            obs.append(Observation(grid=grid, settlements=[], viewport=(vx, vy, 15, 15), seed_index=si))
    return obs


def strategy_repeat(states, gts, repeats=2, n_queries=50):
    """Repeat each viewport N times for better empirical estimates."""
    unique = n_queries // repeats
    allocation = allocate_queries(states, unique)
    obs = []
    for si in range(5):
        viewports = plan_viewports(states[si], allocation[si])
        for vx, vy in viewports:
            for _ in range(repeats):
                grid = simulate_observation(states[si], gts[si], vx, vy)
                obs.append(Observation(grid=grid, settlements=[], viewport=(vx, vy, 15, 15), seed_index=si))
    return obs


def strategy_heavy_repeat(states, gts, n_queries=50):
    """10 viewports × 5 repeats each."""
    return strategy_repeat(states, gts, repeats=5, n_queries=n_queries)


def strategy_focus_3_maps(states, gts, n_queries=50):
    """All queries on 3 maps (more per map, skip 2 maps entirely)."""
    obs = []
    per_map = n_queries // 3
    for si in range(3):
        n = per_map + (1 if si < n_queries % 3 else 0)
        viewports = plan_viewports(states[si], n)
        for vx, vy in viewports:
            grid = simulate_observation(states[si], gts[si], vx, vy)
            obs.append(Observation(grid=grid, settlements=[], viewport=(vx, vy, 15, 15), seed_index=si))
    return obs


def evaluate_strategy(name, obs, states, gts, model):
    obs_stats = compute_round_stats_from_observations(obs, states[0])
    bin_dists = build_empirical_distributions(obs, states)
    bin_counts = get_bin_coverage_stats(obs, states)

    scores = []
    for si in SEEDS:
        pred = model.predict(states[si], obs_stats)
        blended = predict_with_empirical_bins(states[si], bin_dists, pred, bin_counts=bin_counts, k=50)
        scores.append(score_prediction(blended.probs, gts[si]))
    return scores


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

    r8_states = [load_map(TEST_ROUND, si)[0] for si in SEEDS]
    r8_gts = [load_map(TEST_ROUND, si)[1] for si in SEEDS]

    strategies = [
        ("50 unique viewports (current)", strategy_current),
        ("25 viewports × 2 repeats", lambda s, g: strategy_repeat(s, g, repeats=2)),
        ("16 viewports × 3 repeats", lambda s, g: strategy_repeat(s, g, repeats=3)),
        ("10 viewports × 5 repeats", strategy_heavy_repeat),
        ("Focus on 3 maps only", strategy_focus_3_maps),
    ]

    # Run each strategy 10 times with different random seeds to average out noise
    N_RUNS = 10

    print(f"\nRound {TEST_ROUND} query strategy comparison ({N_RUNS} runs each)")
    print(f"Oracle ceiling: 95.77")
    print(f"{'Strategy':<35} {'Mean':>6} {'Std':>5} {'Min':>6} {'Max':>6}")
    print("-" * 65)

    for name, strategy_fn in strategies:
        run_avgs = []
        for seed in range(N_RUNS):
            np.random.seed(seed)
            obs = strategy_fn(r8_states, r8_gts)
            scores = evaluate_strategy(name, obs, r8_states, r8_gts, model)
            run_avgs.append(np.mean(scores))

        mean = np.mean(run_avgs)
        std = np.std(run_avgs)
        print(f"{name:<35} {mean:>6.2f} {std:>5.2f} {min(run_avgs):>6.2f} {max(run_avgs):>6.2f}")

    print(f"\nOur actual R8 submission: 89.83")


if __name__ == "__main__":
    main()
