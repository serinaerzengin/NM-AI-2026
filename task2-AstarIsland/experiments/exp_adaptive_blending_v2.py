"""Experiment: smarter adaptive stat blending using observation consistency.

Current approach: obs_weight = sigmoid(a * settle_rate + b * divergence + c)
  - Penalizes high settlement rates and divergence from historical avg
  - Problem: on R18 this over-corrected (obs were right but looked extreme)

New idea: measure CONSISTENCY of observations across seeds/viewports.
If all seeds agree on high settlement rate, trust observations even if they
diverge from historical. If seeds disagree, be more skeptical.

Signals to use:
  1. Cross-seed std of settlement rates (low = consistent = trustworthy)
  2. Number of observed dynamic cells (more = more reliable)
  3. How close obs stats are to ground truth (we measure this offline)

Tests several blending strategies on all rounds with observations.
"""

import json
import sys
from pathlib import Path
from collections import defaultdict

import numpy as np
from scipy.optimize import minimize

sys.path.insert(0, str(Path(__file__).parent.parent))

from astar.types import (
    MapState, Observation, RoundStats, Prediction, NUM_CLASSES,
    OCEAN, MOUNTAIN, TERRAIN_TO_CLASS, CLASS_EMPTY, CLASS_SETTLEMENT,
    CLASS_PORT, CLASS_RUIN, CLASS_FOREST, CLASS_MOUNTAIN,
)
from astar.features import compute_features
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


def sigmoid(x):
    return 1.0 / (1.0 + np.exp(-np.clip(x, -20, 20)))


def get_all_rounds():
    rounds = []
    for d in sorted(DATA_DIR.iterdir()):
        if d.is_dir() and d.name.startswith("round_"):
            rn = int(d.name.split("_")[1])
            if (d / "seed_0" / "ground_truth.json").exists():
                rounds.append(rn)
    return rounds


def get_rounds_with_observations():
    rounds = []
    for rn in get_all_rounds():
        obs_dir = DATA_DIR / f"round_{rn}" / "seed_0" / "observations"
        if obs_dir.exists() and any(obs_dir.iterdir()):
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


def blend_stats(obs_stats, hist_stats, obs_weight):
    fields = ["ruin_rate", "settlement_rate", "port_rate", "expansion_distance",
              "forest_rate", "empty_rate", "settlement_to_ruin_ratio"]
    return RoundStats(**{
        f: obs_weight * getattr(obs_stats, f) + (1 - obs_weight) * getattr(hist_stats, f)
        for f in fields
    })


# ── Per-seed obs stats (for consistency measurement) ───────────────────

def compute_per_seed_stats(all_obs_by_seed, states):
    """Compute settlement rate per seed from observations."""
    per_seed_rates = []
    for si in range(len(states)):
        seed_obs = all_obs_by_seed[si]
        if not seed_obs:
            continue
        state = states[si]
        total_cells = 0
        settle_cells = 0
        for obs in seed_obs:
            vx, vy, vw, vh = obs.viewport
            for r in range(vh):
                for c in range(vw):
                    abs_x, abs_y = vx + c, vy + r
                    if abs_y >= 40 or abs_x >= 40:
                        continue
                    terrain_code = int(obs.grid[r, c])
                    cls = TERRAIN_TO_CLASS.get(terrain_code, CLASS_EMPTY)
                    if cls == CLASS_MOUNTAIN:
                        continue
                    initial_cls = TERRAIN_TO_CLASS.get(int(state.grid[abs_y, abs_x]), CLASS_EMPTY)
                    if initial_cls == CLASS_MOUNTAIN:
                        continue
                    total_cells += 1
                    if cls == CLASS_SETTLEMENT:
                        settle_cells += 1
        if total_cells > 0:
            per_seed_rates.append(settle_cells / total_cells)
    return per_seed_rates


def compute_per_viewport_stats(all_obs, states):
    """Compute settlement rate per individual viewport observation."""
    per_vp_rates = []
    for obs in all_obs:
        state = states[obs.seed_index]
        total_cells = 0
        settle_cells = 0
        vx, vy, vw, vh = obs.viewport
        for r in range(vh):
            for c in range(vw):
                abs_x, abs_y = vx + c, vy + r
                if abs_y >= 40 or abs_x >= 40:
                    continue
                terrain_code = int(obs.grid[r, c])
                cls = TERRAIN_TO_CLASS.get(terrain_code, CLASS_EMPTY)
                if cls == CLASS_MOUNTAIN:
                    continue
                initial_cls = TERRAIN_TO_CLASS.get(int(state.grid[abs_y, abs_x]), CLASS_EMPTY)
                if initial_cls == CLASS_MOUNTAIN:
                    continue
                total_cells += 1
                if cls == CLASS_SETTLEMENT:
                    settle_cells += 1
        if total_cells > 0:
            per_vp_rates.append(settle_cells / total_cells)
    return per_vp_rates


# ── Blending strategies ───────────────────────────────────────────────

def strategy_current(obs_stats, hist_stats, consistency_info):
    """Current: sigmoid(a * settle_rate + b * divergence + c)"""
    a, b, c = -15.28, 0.58, 4.41
    divergence = abs(obs_stats.settlement_rate - hist_stats.settlement_rate) / (hist_stats.settlement_rate + 1e-6)
    obs_weight = sigmoid(a * obs_stats.settlement_rate + b * divergence + c)
    return obs_weight


def strategy_fixed_high(obs_stats, hist_stats, consistency_info):
    """Always trust observations highly."""
    return 0.9


def strategy_fixed_medium(obs_stats, hist_stats, consistency_info):
    """Always trust observations moderately."""
    return 0.7


def strategy_consistency_based(obs_stats, hist_stats, consistency_info):
    """Trust observations proportionally to cross-seed consistency."""
    seed_std = consistency_info["seed_std"]
    # Low std → high trust. Typical std range: 0.01-0.15
    # Map: std=0 → weight=0.95, std=0.15 → weight=0.3
    obs_weight = max(0.3, 0.95 - seed_std * 4.0)
    return obs_weight


def strategy_consistency_v2(obs_stats, hist_stats, consistency_info):
    """Blend current approach with consistency signal."""
    # Start with moderate trust
    base_weight = 0.7

    # Adjust by consistency (cross-seed std)
    seed_std = consistency_info["seed_std"]
    consistency_bonus = max(-0.3, 0.2 - seed_std * 3.0)  # +0.2 if very consistent, -0.3 if not

    # Adjust by sample size (more viewports = more reliable)
    n_obs = consistency_info["n_observations"]
    size_bonus = min(0.1, (n_obs - 30) * 0.005)  # small bonus for >30 observations

    obs_weight = np.clip(base_weight + consistency_bonus + size_bonus, 0.2, 0.98)
    return obs_weight


def strategy_viewport_consistency(obs_stats, hist_stats, consistency_info):
    """Use per-viewport variance as trust signal."""
    vp_std = consistency_info["viewport_std"]
    # Low viewport std → consistent observations → high trust
    obs_weight = max(0.3, 0.95 - vp_std * 3.0)
    return obs_weight


def strategy_capped_current(obs_stats, hist_stats, consistency_info):
    """Current strategy but with a minimum obs_weight floor."""
    current_weight = strategy_current(obs_stats, hist_stats, consistency_info)
    return max(0.5, current_weight)  # Never trust obs less than 50%


# ── Evaluation ─────────────────────────────────────────────────────────

def evaluate_strategy(strategy_fn, strategy_name, val_round, models, states, gts,
                      all_obs_by_seed, all_obs_flat, hist_stats, k=49):
    """Evaluate a blending strategy on a single round."""
    obs_stats = compute_round_stats_from_observations(all_obs_flat, states[0])
    bin_dists = build_empirical_distributions(all_obs_flat, states)
    bin_counts = get_bin_coverage_stats(all_obs_flat, states)

    # Compute consistency signals
    per_seed_rates = compute_per_seed_stats(all_obs_by_seed, states)
    per_vp_rates = compute_per_viewport_stats(all_obs_flat, states)

    consistency_info = {
        "seed_std": np.std(per_seed_rates) if len(per_seed_rates) > 1 else 0.1,
        "seed_rates": per_seed_rates,
        "viewport_std": np.std(per_vp_rates) if len(per_vp_rates) > 1 else 0.1,
        "n_observations": len(all_obs_flat),
        "n_seeds_observed": len(per_seed_rates),
    }

    obs_weight = strategy_fn(obs_stats, hist_stats, consistency_info)
    blended = blend_stats(obs_stats, hist_stats, obs_weight)

    seed_scores = []
    for si in SEEDS:
        base_pred = predict_map(models, states[si], blended)
        if bin_dists:
            final = predict_with_empirical_bins(states[si], bin_dists, base_pred, bin_counts=bin_counts, k=k)
        else:
            final = base_pred
        seed_scores.append(score_prediction(final.probs, gts[si]))

    return {
        "scores": seed_scores,
        "avg": np.mean(seed_scores),
        "obs_weight": obs_weight,
        "seed_std": consistency_info["seed_std"],
        "viewport_std": consistency_info["viewport_std"],
        "obs_settle": obs_stats.settlement_rate,
        "gt_settle": np.mean([compute_round_stats_from_ground_truth(gts[si], states[si]).settlement_rate for si in SEEDS]),
    }


def main():
    all_rounds = get_all_rounds()
    obs_rounds = get_rounds_with_observations()
    test_rounds = [r for r in obs_rounds if r in all_rounds]

    strategies = {
        "A: current":              strategy_current,
        "B: fixed 0.9":            strategy_fixed_high,
        "C: fixed 0.7":            strategy_fixed_medium,
        "D: cross-seed std":       strategy_consistency_based,
        "E: consistency v2":       strategy_consistency_v2,
        "F: viewport std":         strategy_viewport_consistency,
        "G: capped current (≥0.5)": strategy_capped_current,
    }

    print(f"Adaptive blending v2 experiment")
    print(f"Testing {len(strategies)} strategies on {len(test_rounds)} rounds: {test_rounds}\n")

    # First, show consistency signals per round
    print(f"{'Round':>5s} {'obs_settle':>10s} {'gt_settle':>10s} {'seed_std':>9s} {'vp_std':>7s} {'n_obs':>6s}")
    print("─" * 50)

    all_results = {name: [] for name in strategies}
    round_info = {}

    for val_rn in test_rounds:
        train_rounds = [r for r in all_rounds if r != val_rn]
        models = train_catboost(train_rounds)

        states, gts = [], []
        all_obs_by_seed = {}
        all_obs_flat = []
        for si in SEEDS:
            state, gt = load_map(val_rn, si)
            states.append(state)
            gts.append(gt)
            seed_obs = load_observations(val_rn, si)
            all_obs_by_seed[si] = seed_obs
            all_obs_flat.extend(seed_obs)

        # Historical stats (from training rounds)
        hist_stats_list = []
        for rn in train_rounds:
            for si in SEEDS:
                s, gt = load_map(rn, si)
                hist_stats_list.append(compute_round_stats_from_ground_truth(gt, s))
        fields = ["ruin_rate", "settlement_rate", "port_rate", "expansion_distance",
                  "forest_rate", "empty_rate", "settlement_to_ruin_ratio"]
        hist_stats = RoundStats(**{f: np.mean([getattr(s, f) for s in hist_stats_list]) for f in fields})

        # Consistency info for display
        obs_stats = compute_round_stats_from_observations(all_obs_flat, states[0])
        per_seed = compute_per_seed_stats(all_obs_by_seed, states)
        per_vp = compute_per_viewport_stats(all_obs_flat, states)
        seed_std = np.std(per_seed) if len(per_seed) > 1 else 0
        vp_std = np.std(per_vp) if len(per_vp) > 1 else 0
        gt_settle = np.mean([compute_round_stats_from_ground_truth(gts[si], states[si]).settlement_rate for si in SEEDS])

        round_info[val_rn] = {
            "obs_settle": obs_stats.settlement_rate,
            "gt_settle": gt_settle,
            "seed_std": seed_std,
            "vp_std": vp_std,
        }
        print(f"R{val_rn:3d} {obs_stats.settlement_rate:10.3f} {gt_settle:10.3f} {seed_std:9.4f} {vp_std:7.4f} {len(all_obs_flat):>6d}")

        # Evaluate all strategies
        for name, fn in strategies.items():
            result = evaluate_strategy(fn, name, val_rn, models, states, gts,
                                       all_obs_by_seed, all_obs_flat, hist_stats)
            all_results[name].append(result)

    # Per-round results
    print(f"\n{'═' * 90}")
    print(f"  Per-round scores")
    print(f"{'═' * 90}")

    for val_rn in test_rounds:
        idx = test_rounds.index(val_rn)
        info = round_info[val_rn]
        print(f"\n  R{val_rn} (obs_settle={info['obs_settle']:.3f}, gt_settle={info['gt_settle']:.3f}, seed_std={info['seed_std']:.4f})")
        for name in strategies:
            r = all_results[name][idx]
            diff = r["avg"] - all_results["A: current"][idx]["avg"]
            sign = "+" if diff >= 0 else ""
            print(f"    {name:<30s}  avg={r['avg']:.2f}  w={r['obs_weight']:.3f}  ({sign}{diff:.2f})")

    # Summary
    print(f"\n{'═' * 90}")
    print(f"  SUMMARY across all {len(test_rounds)} rounds")
    print(f"{'═' * 90}")

    baseline_avg = np.mean([r["avg"] for r in all_results["A: current"]])
    ranked = []
    for name in strategies:
        avgs = [r["avg"] for r in all_results[name]]
        overall = np.mean(avgs)
        diff = overall - baseline_avg
        ranked.append((name, overall, diff, avgs))

    ranked.sort(key=lambda x: -x[1])
    for name, overall, diff, avgs in ranked:
        sign = "+" if diff >= 0 else ""
        per_round = "  ".join(f"{a:.1f}" for a in avgs)
        print(f"  {name:<30s}  avg={overall:.2f}  ({sign}{diff:.2f})  [{per_round}]")

    print(f"{'═' * 90}")


if __name__ == "__main__":
    main()
