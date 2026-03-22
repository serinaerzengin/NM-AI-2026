"""Bottleneck analysis: Where are we losing points, and what would fix it?

Tests several potential improvements:
  1. Per-bin adaptive k — use tighter k for high-count bins, looser for low-count
  2. Historical prior bins — build bin distributions from ALL past ground truths,
     blend as fallback when current-round bins have few observations
  3. Three-way blending — model × historical bins × current bins
  4. Oracle analysis — decompose error into model error vs bin error vs coverage gaps

Uses leave-one-round-out CV on rounds with observations.
"""

import json
import sys
from pathlib import Path
from collections import defaultdict

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

from catboost import CatBoostRegressor
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
from astar.predictor import _build_row, _static_prediction, _is_static_cell, PROB_FLOOR
from astar.scoring import score_prediction
from astar.empirical_bins import (
    build_empirical_distributions, get_bin_coverage_stats,
    _cell_bin_key, _cell_bin_key_coarse, MIN_BIN_COUNT,
)
import store

DATA_DIR = Path(__file__).parent.parent / "data" / "rounds"
BEST_PARAMS_PATH = Path(__file__).parent.parent / "best_params_all.json"
SEEDS = list(range(5))

_cache = {}


# ── Data loading ──────────────────────────────────────────────────────

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
    key = (rn, si)
    if key not in _cache:
        sd = DATA_DIR / f"round_{rn}" / f"seed_{si}"
        with open(sd / "initial_state.json") as f:
            raw = json.load(f)
        with open(sd / "ground_truth.json") as f:
            gt_raw = json.load(f)
        _cache[key] = (
            MapState(grid=np.array(raw["grid"]), settlements=raw["settlements"]),
            np.array(gt_raw["ground_truth"]),
        )
    return _cache[key]


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


def load_catboost_params():
    if BEST_PARAMS_PATH.exists():
        with open(BEST_PARAMS_PATH) as f:
            return json.load(f).get("catboost", {})
    return {"iterations": 200, "depth": 5, "learning_rate": 0.1}


# ── Historical prior bins ────────────────────────────────────────────

def build_historical_prior_bins(train_rounds):
    """Build bin distributions from ground truth of training rounds.

    Unlike empirical bins (built from 50 live observations), these use
    the full ground truth distributions — perfect coverage but from
    different hidden parameters.
    """
    key = f"hist_bins_{'_'.join(map(str, sorted(train_rounds)))}"
    if key in _cache:
        return _cache[key]

    bin_accum = defaultdict(lambda: np.zeros(NUM_CLASSES, dtype=np.float64))
    bin_counts = defaultdict(int)

    for rn in train_rounds:
        for si in SEEDS:
            state, gt = load_map(rn, si)
            features = compute_features(state)
            h, w = gt.shape[:2]
            for r in range(h):
                for c in range(w):
                    if state.grid[r, c] in (OCEAN, MOUNTAIN):
                        continue
                    cell_feats = features[r, c]

                    fine_key = _cell_bin_key(cell_feats)
                    if fine_key is not None:
                        bin_accum[fine_key] += gt[r, c]
                        bin_counts[fine_key] += 1

                    coarse_key = _cell_bin_key_coarse(cell_feats)
                    if coarse_key is not None:
                        bin_accum[coarse_key] += gt[r, c]
                        bin_counts[coarse_key] += 1

    bin_dists = {}
    for bk, acc in bin_accum.items():
        n = bin_counts[bk]
        if n >= MIN_BIN_COUNT:
            dist = acc / n
            dist = np.maximum(dist, PROB_FLOOR)
            dist = dist / dist.sum()
            bin_dists[bk] = dist.astype(np.float32)

    result = (bin_dists, dict(bin_counts))
    _cache[key] = result
    return result


# ── Prediction helpers ────────────────────────────────────────────────

def predict_catboost_map(models, state, round_stats):
    """Get raw CatBoost predictions for a map."""
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
            np.zeros(len(X)) if m is None else m.predict(X) for m in models
        ])
        for (r, c), pred in zip(dynamic_indices, preds):
            probs[r, c] = pred
    probs = np.maximum(probs, PROB_FLOOR)
    probs = probs / probs.sum(axis=-1, keepdims=True)
    return probs


def blend_with_bins(probs, state, bin_dists, bin_counts, k):
    """Blend model predictions with empirical bins using weight = n/(n+k)."""
    features = compute_features(state)
    h, w = state.grid.shape
    result = probs.copy()
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
                result[r, c] = weight * bin_dists[bk] + (1 - weight) * result[r, c]
    result = np.maximum(result, PROB_FLOOR)
    result = result / result.sum(axis=-1, keepdims=True)
    return result


def blend_three_way(state, model_probs, obs_bin_dists, obs_bin_counts,
                    hist_bin_dists, hist_bin_counts, k_obs, k_hist):
    """Three-way blend: model + current-round bins + historical prior bins.

    For each cell:
      1. Start with model prediction
      2. Blend with historical prior bins (broad prior, lower weight)
      3. Blend with current-round empirical bins (specific to this round, higher weight)
    """
    features = compute_features(state)
    h, w = state.grid.shape
    result = model_probs.copy()

    for r in range(h):
        for c in range(w):
            if state.grid[r, c] in (OCEAN, MOUNTAIN):
                continue

            cell_feats = features[r, c]
            fine_key = _cell_bin_key(cell_feats)
            coarse_key = _cell_bin_key_coarse(cell_feats)

            # Step 1: Blend with historical prior
            hk = fine_key if (fine_key and fine_key in hist_bin_dists) else coarse_key
            if hk is not None and hk in hist_bin_dists:
                n = hist_bin_counts.get(hk, 0)
                w_hist = n / (n + k_hist)
                result[r, c] = w_hist * hist_bin_dists[hk] + (1 - w_hist) * result[r, c]

            # Step 2: Blend with current-round empirical bins (overrides)
            ok = fine_key if (fine_key and fine_key in obs_bin_dists) else coarse_key
            if ok is not None and ok in obs_bin_dists:
                n = obs_bin_counts.get(ok, 0)
                w_obs = n / (n + k_obs)
                result[r, c] = w_obs * obs_bin_dists[ok] + (1 - w_obs) * result[r, c]

    result = np.maximum(result, PROB_FLOOR)
    result = result / result.sum(axis=-1, keepdims=True)
    return result


# ── Training ──────────────────────────────────────────────────────────

def train_fold(train_rounds, cat_params):
    """Train CatBoost on training rounds."""
    X_rows, y_rows, w_rows = [], [], []
    for rn in train_rounds:
        stats = round_stats_avg(rn)
        stats_arr = round_stats_to_array(stats)
        for si in SEEDS:
            state, gt = load_map(rn, si)
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


# ── Error decomposition ──────────────────────────────────────────────

def decompose_errors(state, gt, model_probs, obs_bin_dists, obs_bin_counts):
    """Decompose prediction error by cell category."""
    features = compute_features(state)
    h, w = state.grid.shape
    eps = 1e-12
    entropy = -np.sum(gt * np.log(gt + eps), axis=-1)

    categories = {
        "fine_bin_hit": {"kl_sum": 0, "entropy_sum": 0, "count": 0},
        "coarse_bin_hit": {"kl_sum": 0, "entropy_sum": 0, "count": 0},
        "no_bin_hit": {"kl_sum": 0, "entropy_sum": 0, "count": 0},
        "static": {"count": 0},
    }

    for r in range(h):
        for c in range(w):
            if state.grid[r, c] in (OCEAN, MOUNTAIN):
                categories["static"]["count"] += 1
                continue
            if entropy[r, c] < 0.05:
                categories["static"]["count"] += 1
                continue

            cell_feats = features[r, c]
            fine_key = _cell_bin_key(cell_feats)
            coarse_key = _cell_bin_key_coarse(cell_feats)

            kl = float(np.sum(gt[r, c] * np.log((gt[r, c] + eps) / (model_probs[r, c] + eps))))

            if fine_key and fine_key in obs_bin_dists:
                cat = "fine_bin_hit"
            elif coarse_key and coarse_key in obs_bin_dists:
                cat = "coarse_bin_hit"
            else:
                cat = "no_bin_hit"

            categories[cat]["kl_sum"] += entropy[r, c] * kl
            categories[cat]["entropy_sum"] += entropy[r, c]
            categories[cat]["count"] += 1

    return categories


def main():
    all_rounds = get_all_rounds()
    val_rounds = get_rounds_with_observations()
    cat_params = load_catboost_params()

    print("Bottleneck Analysis & Alternative Approaches")
    print("=" * 85)
    print(f"All rounds: {all_rounds}")
    print(f"Val rounds: {val_rounds}")
    print(f"CatBoost: {cat_params}\n")

    # ── Experiment 1: Error decomposition ─────────────────────────────
    print("=" * 85)
    print("EXPERIMENT 1: Error Decomposition (where are points lost?)")
    print("=" * 85)
    print(f"  {'Round':>5s}  {'Fine bin cells':>15s}  {'Coarse bin cells':>17s}  {'No bin cells':>14s}  {'Static':>7s}")

    for val_rn in val_rounds:
        train_rounds = [r for r in all_rounds if r != val_rn]
        models = train_fold(train_rounds, cat_params)

        all_obs = []
        for si in SEEDS:
            all_obs.extend(load_obs(val_rn, si))

        states = [load_map(val_rn, si)[0] for si in SEEDS]
        obs_stats = compute_round_stats_from_observations(all_obs, states[0])
        obs_bins = build_empirical_distributions(all_obs, states)
        obs_counts = get_bin_coverage_stats(all_obs, states)

        # Aggregate across seeds
        total_fine, total_coarse, total_nobin, total_static = 0, 0, 0, 0
        fine_wkl, coarse_wkl, nobin_wkl = 0, 0, 0
        fine_entropy, coarse_entropy, nobin_entropy = 0, 0, 0

        for si in SEEDS:
            state, gt = load_map(val_rn, si)
            model_probs = predict_catboost_map(models, state, obs_stats)
            # Apply bin blending for fair comparison
            blended = blend_with_bins(model_probs, state, obs_bins, obs_counts, k=139)
            cats = decompose_errors(state, gt, blended, obs_bins, obs_counts)

            total_fine += cats["fine_bin_hit"]["count"]
            total_coarse += cats["coarse_bin_hit"]["count"]
            total_nobin += cats["no_bin_hit"]["count"]
            total_static += cats["static"]["count"]
            fine_wkl += cats["fine_bin_hit"]["kl_sum"]
            coarse_wkl += cats["coarse_bin_hit"]["kl_sum"]
            nobin_wkl += cats["no_bin_hit"]["kl_sum"]
            fine_entropy += cats["fine_bin_hit"]["entropy_sum"]
            coarse_entropy += cats["coarse_bin_hit"]["entropy_sum"]
            nobin_entropy += cats["no_bin_hit"]["entropy_sum"]

        fine_avg = fine_wkl / fine_entropy if fine_entropy > 0 else 0
        coarse_avg = coarse_wkl / coarse_entropy if coarse_entropy > 0 else 0
        nobin_avg = nobin_wkl / nobin_entropy if nobin_entropy > 0 else 0

        print(f"  R{val_rn:>3d}  {total_fine:>5d} (kl={fine_avg:.4f})  "
              f"{total_coarse:>5d} (kl={coarse_avg:.4f})  "
              f"{total_nobin:>5d} (kl={nobin_avg:.4f})  {total_static:>5d}")

    # ── Experiment 2: Historical prior bins ────────────────────────────
    print(f"\n{'=' * 85}")
    print("EXPERIMENT 2: Historical Prior Bins as Fallback")
    print("  Uses ground truth from training rounds to build 'prior' bin distributions")
    print("  Three-way blend: model → historical bins → current-round bins")
    print("=" * 85)

    k_obs = 139  # Current best for observation bins
    k_hist_values = [500, 1000, 2000, 5000]

    print(f"\n  {'Round':>5s}  {'Baseline':>8s}", end="")
    for kh in k_hist_values:
        print(f"  {'k_h='+str(kh):>10s}", end="")
    print(f"  {'Oracle bins':>11s}")

    overall_baseline = []
    overall_results = {kh: [] for kh in k_hist_values}
    overall_oracle = []

    for val_rn in val_rounds:
        train_rounds = [r for r in all_rounds if r != val_rn]
        models = train_fold(train_rounds, cat_params)

        # Build historical prior bins from training rounds
        hist_bins, hist_counts = build_historical_prior_bins(train_rounds)

        # Load val data
        all_obs = []
        states, gts = [], []
        for si in SEEDS:
            state, gt = load_map(val_rn, si)
            states.append(state)
            gts.append(gt)
            all_obs.extend(load_obs(val_rn, si))

        obs_stats = compute_round_stats_from_observations(all_obs, states[0])
        obs_bins = build_empirical_distributions(all_obs, states)
        obs_counts = get_bin_coverage_stats(all_obs, states)

        # Oracle bins from val round ground truth
        oracle_accum = defaultdict(lambda: np.zeros(NUM_CLASSES, dtype=np.float64))
        oracle_n = defaultdict(int)
        for si in SEEDS:
            features = compute_features(states[si])
            h, w = gts[si].shape[:2]
            for r in range(h):
                for c in range(w):
                    if states[si].grid[r, c] in (OCEAN, MOUNTAIN):
                        continue
                    cell_feats = features[r, c]
                    for key_fn in [_cell_bin_key, _cell_bin_key_coarse]:
                        bk = key_fn(cell_feats)
                        if bk:
                            oracle_accum[bk] += gts[si][r, c]
                            oracle_n[bk] += 1
        oracle_bins = {}
        for bk, acc in oracle_accum.items():
            if oracle_n[bk] >= MIN_BIN_COUNT:
                d = acc / oracle_n[bk]
                d = np.maximum(d, PROB_FLOOR)
                oracle_bins[bk] = (d / d.sum()).astype(np.float32)

        # Evaluate
        # Baseline: model + obs bins (k=139)
        baseline_scores = []
        for si in SEEDS:
            mp = predict_catboost_map(models, states[si], obs_stats)
            bp = blend_with_bins(mp, states[si], obs_bins, obs_counts, k=k_obs)
            baseline_scores.append(score_prediction(bp, gts[si]))
        baseline_avg = np.mean(baseline_scores)
        overall_baseline.append(baseline_avg)

        # Three-way with different k_hist
        results_str = f"  R{val_rn:>3d}  {baseline_avg:>8.2f}"
        for kh in k_hist_values:
            scores = []
            for si in SEEDS:
                mp = predict_catboost_map(models, states[si], obs_stats)
                tp = blend_three_way(states[si], mp, obs_bins, obs_counts,
                                     hist_bins, hist_counts, k_obs, kh)
                scores.append(score_prediction(tp, gts[si]))
            avg = np.mean(scores)
            overall_results[kh].append(avg)
            delta = avg - baseline_avg
            sign = "+" if delta >= 0 else ""
            results_str += f"  {avg:>6.2f}({sign}{delta:.2f})"

        # Oracle bins
        oracle_scores = []
        for si in SEEDS:
            mp = predict_catboost_map(models, states[si], obs_stats)
            bp = blend_with_bins(mp, states[si], oracle_bins, oracle_n, k=20)
            oracle_scores.append(score_prediction(bp, gts[si]))
        oracle_avg = np.mean(oracle_scores)
        overall_oracle.append(oracle_avg)
        results_str += f"  {oracle_avg:>8.2f}"

        print(results_str)

    # Overall
    print(f"  {'─' * 80}")
    overall_b = np.mean(overall_baseline)
    results_str = f"  {'AVG':>5s}  {overall_b:>8.2f}"
    for kh in k_hist_values:
        avg = np.mean(overall_results[kh])
        delta = avg - overall_b
        sign = "+" if delta >= 0 else ""
        results_str += f"  {avg:>6.2f}({sign}{delta:.2f})"
    results_str += f"  {np.mean(overall_oracle):>8.2f}"
    print(results_str)

    # ── Experiment 3: Concentrated queries simulation ─────────────────
    print(f"\n{'=' * 85}")
    print("EXPERIMENT 3: Query Concentration vs Coverage")
    print("  Simulate: what if we used fewer unique viewports but more repeats?")
    print("  (subsample observations to simulate fewer queries)")
    print("=" * 85)

    # For each val round, compare full obs vs half obs (simulating 25 queries)
    print(f"\n  {'Round':>5s}  {'50 queries':>10s}  {'25 queries':>10s}  {'15 queries':>10s}  {'Loss @25':>8s}  {'Loss @15':>8s}")

    for val_rn in val_rounds:
        train_rounds = [r for r in all_rounds if r != val_rn]
        models = train_fold(train_rounds, cat_params)

        states, gts = [], []
        all_obs_by_seed = {}
        for si in SEEDS:
            state, gt = load_map(val_rn, si)
            states.append(state)
            gts.append(gt)
            all_obs_by_seed[si] = load_obs(val_rn, si)

        all_obs = []
        for obs_list in all_obs_by_seed.values():
            all_obs.extend(obs_list)

        obs_stats = compute_round_stats_from_observations(all_obs, states[0])

        scores_by_budget = {}
        for budget_frac, label in [(1.0, "50"), (0.5, "25"), (0.3, "15")]:
            # Subsample observations
            sub_obs = []
            for si in SEEDS:
                seed_obs = all_obs_by_seed[si]
                n_keep = max(1, int(len(seed_obs) * budget_frac))
                sub_obs.extend(seed_obs[:n_keep])

            sub_bins = build_empirical_distributions(sub_obs, states)
            sub_counts = get_bin_coverage_stats(sub_obs, states)

            seed_scores = []
            for si in SEEDS:
                mp = predict_catboost_map(models, states[si], obs_stats)
                bp = blend_with_bins(mp, states[si], sub_bins, sub_counts, k=k_obs)
                seed_scores.append(score_prediction(bp, gts[si]))
            scores_by_budget[label] = np.mean(seed_scores)

        loss_25 = scores_by_budget["25"] - scores_by_budget["50"]
        loss_15 = scores_by_budget["15"] - scores_by_budget["50"]
        print(f"  R{val_rn:>3d}  {scores_by_budget['50']:>10.2f}  {scores_by_budget['25']:>10.2f}  "
              f"{scores_by_budget['15']:>10.2f}  {loss_25:>+8.2f}  {loss_15:>+8.2f}")

    # ── Experiment 4: Model-only ceiling (no bins) ────────────────────
    print(f"\n{'=' * 85}")
    print("EXPERIMENT 4: Component Contributions")
    print("  Model-only vs Model+Bins vs Oracle ceiling")
    print("=" * 85)

    print(f"\n  {'Round':>5s}  {'Model only':>10s}  {'+ Obs bins':>10s}  {'+ Oracle':>10s}  {'Bin gain':>8s}  {'Ceiling gap':>11s}")

    for val_rn in val_rounds:
        train_rounds = [r for r in all_rounds if r != val_rn]
        models = train_fold(train_rounds, cat_params)

        states, gts = [], []
        all_obs = []
        for si in SEEDS:
            state, gt = load_map(val_rn, si)
            states.append(state)
            gts.append(gt)
            all_obs.extend(load_obs(val_rn, si))

        obs_stats = compute_round_stats_from_observations(all_obs, states[0])
        obs_bins = build_empirical_distributions(all_obs, states)
        obs_counts = get_bin_coverage_stats(all_obs, states)

        # Oracle bins
        oracle_accum = defaultdict(lambda: np.zeros(NUM_CLASSES, dtype=np.float64))
        oracle_n = defaultdict(int)
        for si in SEEDS:
            features = compute_features(states[si])
            h, w = gts[si].shape[:2]
            for r in range(h):
                for c in range(w):
                    if states[si].grid[r, c] in (OCEAN, MOUNTAIN):
                        continue
                    for key_fn in [_cell_bin_key, _cell_bin_key_coarse]:
                        bk = key_fn(features[r, c])
                        if bk:
                            oracle_accum[bk] += gts[si][r, c]
                            oracle_n[bk] += 1
        oracle_bins = {}
        for bk, acc in oracle_accum.items():
            if oracle_n[bk] >= MIN_BIN_COUNT:
                d = acc / oracle_n[bk]
                d = np.maximum(d, PROB_FLOOR)
                oracle_bins[bk] = (d / d.sum()).astype(np.float32)

        model_scores, obs_scores, oracle_scores = [], [], []
        for si in SEEDS:
            mp = predict_catboost_map(models, states[si], obs_stats)
            model_scores.append(score_prediction(mp, gts[si]))
            bp = blend_with_bins(mp, states[si], obs_bins, obs_counts, k=k_obs)
            obs_scores.append(score_prediction(bp, gts[si]))
            op = blend_with_bins(mp, states[si], oracle_bins, oracle_n, k=20)
            oracle_scores.append(score_prediction(op, gts[si]))

        m_avg = np.mean(model_scores)
        o_avg = np.mean(obs_scores)
        or_avg = np.mean(oracle_scores)
        bin_gain = o_avg - m_avg
        ceiling_gap = or_avg - o_avg
        print(f"  R{val_rn:>3d}  {m_avg:>10.2f}  {o_avg:>10.2f}  {or_avg:>10.2f}  {bin_gain:>+8.2f}  {ceiling_gap:>+11.2f}")


if __name__ == "__main__":
    main()
