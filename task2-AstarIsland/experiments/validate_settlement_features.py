"""Validate whether settlement details improve predictions on round 6.

Compares three approaches:
  A) Base model (trained on rounds 1-5, basic round stats)
  B) Base model + enriched settlement round stats
  C) Base model + per-cell settlement features + enriched round stats

All evaluated against round 6 ground truth.
"""

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))

from astar.types import MapState, RoundStats, NUM_CLASSES
from astar.features import compute_features
from astar.calibration import compute_round_stats_from_ground_truth, round_stats_to_array
from astar.predictor import Predictor, _build_row, _floor_and_normalize, _static_prediction
from astar.scoring import score_prediction
from astar.settlement_features import (
    compute_settlement_cell_features,
    compute_settlement_round_stats,
    collect_all_settlements,
    NUM_SETTLEMENT_CELL_FEATURES,
    NUM_SETTLEMENT_ROUND_FEATURES,
)
import store

DATA_DIR = Path(__file__).parent / "data" / "rounds"
TRAIN_ROUNDS = list(range(1, 6))
TEST_ROUND = 6
SEEDS = list(range(5))


def load_map(round_num, seed):
    seed_dir = DATA_DIR / f"round_{round_num}" / f"seed_{seed}"
    with open(seed_dir / "initial_state.json") as f:
        raw = json.load(f)
    with open(seed_dir / "ground_truth.json") as f:
        gt_raw = json.load(f)
    state = MapState(grid=np.array(raw["grid"]), settlements=raw["settlements"])
    gt = np.array(gt_raw["ground_truth"])
    return state, gt


def compute_round_stats_avg(round_num):
    stats = []
    for si in SEEDS:
        s, gt = load_map(round_num, si)
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


def load_round6_observations(seed):
    """Load raw observation dicts for round 6."""
    return store.list_observations(TEST_ROUND, seed)


def main():
    print("=" * 60)
    print("SETTLEMENT FEATURES VALIDATION — ROUND 6")
    print("=" * 60)

    # Train base model on rounds 1-5
    print("\nTraining base model on rounds 1-5...")
    train_states, train_gts, train_stats = [], [], []
    for rn in TRAIN_ROUNDS:
        stats = compute_round_stats_avg(rn)
        for si in SEEDS:
            s, gt = load_map(rn, si)
            train_states.append(s)
            train_gts.append(gt)
            train_stats.append(stats)

    base_model = Predictor()
    base_model.fit(train_states, train_gts, train_stats)

    # Get round 6 ground truth stats (cheating — we'd estimate from observations in live)
    r6_stats = compute_round_stats_avg(TEST_ROUND)
    r6_stats_arr = round_stats_to_array(r6_stats)

    # Evaluate on each seed
    for approach in ["A: Base model", "B: + settlement round stats", "C: + per-cell features"]:
        print(f"\n── {approach} ──")
        seed_scores = []

        for si in SEEDS:
            state, gt = load_map(TEST_ROUND, si)
            features = compute_features(state)
            h, w = state.grid.shape
            probs = np.zeros((h, w, NUM_CLASSES), dtype=np.float32)

            # Load observations and extract settlement details
            raw_observations = load_round6_observations(si)
            all_settlements = collect_all_settlements(raw_observations)
            settlement_round_feats = compute_settlement_round_stats(all_settlements)

            # Build predictions for each cell
            dynamic_indices = []
            X_rows = []

            for r in range(h):
                for c in range(w):
                    static_pred = _static_prediction(state.grid[r, c])
                    if static_pred is not None:
                        probs[r, c] = static_pred
                        continue

                    base_row = _build_row(features[r, c], r6_stats_arr)

                    if approach.startswith("A"):
                        row = base_row
                    elif approach.startswith("B"):
                        row = np.concatenate([base_row, settlement_round_feats])
                    else:  # C
                        cell_settle_feats = compute_settlement_cell_features(
                            c, r, all_settlements
                        )
                        row = np.concatenate([base_row, settlement_round_feats, cell_settle_feats])

                    dynamic_indices.append((r, c))
                    X_rows.append(row)

            # For approach A, use the base model directly
            if approach.startswith("A"):
                pred = base_model.predict(state, r6_stats)
                s = score_prediction(pred.probs, gt)
            else:
                # For B and C, we need to retrain with the extra features
                # For now, just use the base model (same prediction) to establish baseline
                # The real test will be retraining with these features
                pred = base_model.predict(state, r6_stats)
                s = score_prediction(pred.probs, gt)

            seed_scores.append(s)
            print(f"  Seed {si}: {s:.2f}")

        print(f"  Avg: {np.mean(seed_scores):.2f}")

    # Now the real test: train models WITH settlement features
    print("\n" + "=" * 60)
    print("RETRAINING WITH SETTLEMENT FEATURES")
    print("=" * 60)

    # We need to figure out what settlement round stats would have been
    # for rounds 1-5 (where we don't have observations).
    # Strategy: compute proxy stats from ground truth distributions.
    # For round 6: use actual observation-derived settlement stats.

    # First, let's see what round 6 settlement stats look like
    print("\n── Round 6 Settlement Stats (from observations) ──")
    for si in SEEDS:
        raw_obs = load_round6_observations(si)
        settlements = collect_all_settlements(raw_obs)
        stats = compute_settlement_round_stats(settlements)
        print(f"  Seed {si}: n_settlements={len(settlements)}, "
              f"avg_food={stats[0]:.3f}, avg_pop={stats[1]:.3f}, "
              f"avg_defense={stats[2]:.3f}, alive_frac={stats[3]:.3f}, "
              f"n_factions={stats[4]:.0f}, avg_wealth={stats[5]:.3f}")

    # For rounds 1-5, we don't have settlement details.
    # Option: use the round 6 stats as a baseline and see how much
    # knowing the "correct" settlement stats helps on round 6.
    # If it helps, the approach is validated.

    # Train a new model that includes settlement round stats as features
    print("\n── Training model with settlement round stats ──")

    # Use average of round 6 settlement stats for rounds 1-5 (proxy)
    all_r6_settlements = []
    for si in SEEDS:
        all_r6_settlements.extend(collect_all_settlements(load_round6_observations(si)))
    r6_settle_stats = compute_settlement_round_stats(all_r6_settlements)

    # Default settlement stats for rounds without observations
    # Use round 6 stats as default (imperfect but reasonable)
    default_settle_stats = r6_settle_stats

    # Build enriched training data
    enriched_X = []
    enriched_y = []
    enriched_w = []

    for state, gt, stats in zip(train_states, train_gts, train_stats):
        feat_map = compute_features(state)
        stats_arr = round_stats_to_array(stats)
        h, w = gt.shape[:2]
        eps = 1e-12
        entropy = -np.sum(gt * np.log(gt + eps), axis=-1)

        for r in range(h):
            for c in range(w):
                if gt[r, c].max() > 0.99:
                    continue
                base_row = _build_row(feat_map[r, c], stats_arr)
                row = np.concatenate([base_row, default_settle_stats])
                enriched_X.append(row)
                enriched_y.append(gt[r, c])
                enriched_w.append(entropy[r, c] + 0.1)

    import xgboost as xgb
    enriched_model = xgb.XGBRegressor(
        n_estimators=500, max_depth=7, learning_rate=0.05,
        multi_strategy="multi_output_tree", tree_method="hist",
        objective="reg:squarederror", subsample=0.8,
        colsample_bytree=0.8, reg_alpha=0.01, reg_lambda=1.0, n_jobs=-1,
    )
    enriched_model.fit(
        np.array(enriched_X, dtype=np.float32),
        np.array(enriched_y, dtype=np.float32),
        sample_weight=np.array(enriched_w, dtype=np.float32),
    )

    # Now predict round 6 with ACTUAL settlement stats from observations
    print("\n── Round 6 scores: enriched model + observation settlement stats ──")
    seed_scores_enriched = []

    for si in SEEDS:
        state, gt = load_map(TEST_ROUND, si)
        feat_map = compute_features(state)
        stats_arr = round_stats_to_array(r6_stats)
        h, w = state.grid.shape

        raw_obs = load_round6_observations(si)
        seed_settle_stats = compute_settlement_round_stats(collect_all_settlements(raw_obs))

        probs = np.zeros((h, w, NUM_CLASSES), dtype=np.float32)
        X_rows = []
        dynamic_indices = []

        for r in range(h):
            for c in range(w):
                static_pred = _static_prediction(state.grid[r, c])
                if static_pred is not None:
                    probs[r, c] = static_pred
                    continue
                base_row = _build_row(feat_map[r, c], stats_arr)
                row = np.concatenate([base_row, seed_settle_stats])
                X_rows.append(row)
                dynamic_indices.append((r, c))

        if X_rows:
            preds = enriched_model.predict(np.array(X_rows, dtype=np.float32))
            for (r, c), pred in zip(dynamic_indices, preds):
                probs[r, c] = pred

        probs = _floor_and_normalize(probs)
        s = score_prediction(probs, gt)
        seed_scores_enriched.append(s)
        print(f"  Seed {si}: {s:.2f}")

    print(f"  Avg: {np.mean(seed_scores_enriched):.2f}")

    # Compare to base model
    print("\n── Comparison ──")
    base_scores = []
    for si in SEEDS:
        state, gt = load_map(TEST_ROUND, si)
        pred = base_model.predict(state, r6_stats)
        base_scores.append(score_prediction(pred.probs, gt))

    print(f"  Base model avg:     {np.mean(base_scores):.2f}")
    print(f"  Enriched model avg: {np.mean(seed_scores_enriched):.2f}")
    print(f"  Improvement:        {np.mean(seed_scores_enriched) - np.mean(base_scores):+.2f}")


if __name__ == "__main__":
    main()
