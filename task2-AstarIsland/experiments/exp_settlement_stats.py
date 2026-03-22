"""Experiment: Use settlement stats from queries as hidden parameter proxies.

The /simulate API returns per-settlement stats (population, food, wealth, defense,
alive, owner_id) but our pipeline only uses the grid terrain codes. These stats are
direct consequences of hidden parameters and should help the model.

Extracts per-round aggregate settlement stats:
  - avg_population, avg_food, avg_wealth, avg_defense
  - alive_ratio (fraction of observed settlements that are alive)
  - n_factions (number of distinct owner_ids)
  - faction_concentration (max faction share — Herfindahl-like)
  - avg_settlements_per_obs (how many settlements per observation)

These become additional round-level features fed to CatBoost alongside existing
round stats, with corresponding interaction features.

Evaluation: leave-one-round-out CV on all rounds with observations.
"""

import json
import sys
import re
import glob
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
    _cell_bin_key, _cell_bin_key_coarse,
)
import store

DATA_DIR = Path(__file__).parent.parent / "data" / "rounds"
BEST_PARAMS_PATH = Path(__file__).parent.parent / "best_params_all.json"
SEEDS = list(range(5))

_cache = {}


# ── Settlement stat extraction ────────────────────────────────────────

def extract_settlement_stats_from_observations(rn):
    """Extract aggregate settlement stats from stored observations for a round.

    Returns dict with settlement stat aggregates, or None if no data.
    """
    key = f"settle_stats_{rn}"
    if key in _cache:
        return _cache[key]

    all_pops, all_foods, all_wealths, all_defenses = [], [], [], []
    alive_count, total_count = 0, 0
    owner_ids = []
    obs_count = 0

    for si in SEEDS:
        for raw in store.list_observations(rn, si):
            if isinstance(raw, list):
                raw = raw[0]
            settlements = raw.get("settlements", [])
            obs_count += 1
            for s in settlements:
                total_count += 1
                all_pops.append(s.get("population", 0))
                all_foods.append(s.get("food", 0))
                all_wealths.append(s.get("wealth", 0))
                all_defenses.append(s.get("defense", 0))
                if s.get("alive", True):
                    alive_count += 1
                owner_ids.append(s.get("owner_id", -1))

    if total_count == 0:
        result = None
    else:
        # Faction concentration (Herfindahl index)
        faction_counts = defaultdict(int)
        for oid in owner_ids:
            faction_counts[oid] += 1
        shares = np.array(list(faction_counts.values())) / total_count
        hhi = float(np.sum(shares ** 2))

        result = {
            "avg_population": float(np.mean(all_pops)),
            "avg_food": float(np.mean(all_foods)),
            "avg_wealth": float(np.mean(all_wealths)),
            "avg_defense": float(np.mean(all_defenses)),
            "alive_ratio": alive_count / total_count,
            "n_factions": len(faction_counts),
            "faction_concentration": hhi,
            "settlements_per_obs": total_count / max(obs_count, 1),
        }

    _cache[key] = result
    return result


def settlement_stats_to_array(stats):
    """Convert settlement stats dict to feature array."""
    if stats is None:
        return np.zeros(8, dtype=np.float32)
    return np.array([
        stats["avg_population"],
        stats["avg_food"],
        stats["avg_wealth"],
        stats["avg_defense"],
        stats["alive_ratio"],
        stats["n_factions"],
        stats["faction_concentration"],
        stats["settlements_per_obs"],
    ], dtype=np.float32)


SETTLE_STAT_NAMES = [
    "avg_population", "avg_food", "avg_wealth", "avg_defense",
    "alive_ratio", "n_factions", "faction_concentration", "settlements_per_obs",
]


# ── Extended row builder ──────────────────────────────────────────────

_DIST_IDX = FEATURE_NAMES.index("dist_nearest_settlement")
_SETTLE_R5_IDX = FEATURE_NAMES.index("settlements_r5")
_COASTAL_IDX = FEATURE_NAMES.index("adjacent_ocean")
_FOREST_ADJ_IDX = FEATURE_NAMES.index("adjacent_forests")


def _build_row_extended(cell_feats, stats_arr, settle_stats_arr):
    """Build model input: cell features + round stats + settlement stats + interactions."""
    settle_rate = stats_arr[1]
    ruin_rate = stats_arr[0]
    dist = cell_feats[_DIST_IDX]
    settle_r5 = cell_feats[_SETTLE_R5_IDX]
    coastal = cell_feats[_COASTAL_IDX]
    forest_adj = cell_feats[_FOREST_ADJ_IDX]

    # Original interactions
    interactions = np.array([
        settle_rate * dist,
        settle_rate * settle_r5,
        settle_rate * coastal,
        ruin_rate * dist,
        settle_rate * forest_adj,
        settle_rate / (dist + 1),
    ], dtype=np.float32)

    # Settlement stat interactions with key cell features
    avg_pop = settle_stats_arr[0]
    alive_ratio = settle_stats_arr[4]
    faction_conc = settle_stats_arr[6]

    settle_interactions = np.array([
        avg_pop * dist,            # population influence decay with distance
        avg_pop / (dist + 1),      # population influence at close range
        alive_ratio * settle_r5,   # survival x local density
        faction_conc * dist,       # faction dominance x distance
    ], dtype=np.float32)

    return np.concatenate([cell_feats, stats_arr, settle_stats_arr, interactions, settle_interactions])


# ── Data loading (reused from optuna_kfold) ───────────────────────────

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


# ── Training data builders ────────────────────────────────────────────

def build_training_data_baseline(rounds):
    """Standard pipeline: cell_feats + round_stats + interactions."""
    X_rows, y_rows, w_rows = [], [], []
    for rn in rounds:
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
    return np.array(X_rows, dtype=np.float32), np.array(y_rows, dtype=np.float32), np.array(w_rows, dtype=np.float32)


def build_training_data_extended(rounds, settle_stats_per_round):
    """Extended pipeline: cell_feats + round_stats + settlement_stats + all interactions."""
    X_rows, y_rows, w_rows = [], [], []

    # For rounds without observation data, use the average of those that do
    known_stats = [v for v in settle_stats_per_round.values() if v is not None]
    if known_stats:
        default_settle_arr = np.mean([settlement_stats_to_array(s) for s in known_stats], axis=0)
    else:
        default_settle_arr = np.zeros(8, dtype=np.float32)

    for rn in rounds:
        stats = round_stats_avg(rn)
        stats_arr = round_stats_to_array(stats)

        ss = settle_stats_per_round.get(rn)
        settle_arr = settlement_stats_to_array(ss) if ss is not None else default_settle_arr

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
                    row = _build_row_extended(features[r, c], stats_arr, settle_arr)
                    X_rows.append(row)
                    y_rows.append(gt[r, c])
                    w_rows.append(entropy[r, c] + 0.1)
    return np.array(X_rows, dtype=np.float32), np.array(y_rows, dtype=np.float32), np.array(w_rows, dtype=np.float32)


# ── Evaluation ────────────────────────────────────────────────────────

def train_and_evaluate(X_train, y_train, w_train, X_val_seeds, val_states, val_gts,
                       bin_dists, bin_counts, k, cat_params, is_extended, settle_arr_val=None):
    """Train CatBoost, predict, blend with empirical bins, score."""
    models = []
    for c in range(NUM_CLASSES):
        target = y_train[:, c]
        if target.max() - target.min() < 1e-8:
            models.append(None)
            continue
        m = CatBoostRegressor(loss_function="RMSE", verbose=0, thread_count=-1, **cat_params)
        m.fit(X_train, target, sample_weight=w_train)
        models.append(m)

    seed_scores = []
    for si in range(len(val_states)):
        state = val_states[si]
        gt = val_gts[si]
        features = compute_features(state)
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
                    # Use appropriate round stats for val
                    if is_extended:
                        obs_stats = X_val_seeds[si]["obs_stats_arr"]
                        X_rows.append(_build_row_extended(features[r, c], obs_stats, settle_arr_val))
                    else:
                        obs_stats = X_val_seeds[si]["obs_stats_arr"]
                        X_rows.append(_build_row(features[r, c], obs_stats))

        if X_rows:
            X = np.array(X_rows, dtype=np.float32)
            preds = np.column_stack([
                np.zeros(len(X)) if m is None else m.predict(X) for m in models
            ])
            for (r, c), pred in zip(dynamic_indices, preds):
                probs[r, c] = pred

        # Empirical bin blending
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

    return seed_scores


def main():
    all_rounds = get_all_rounds()
    val_rounds = get_rounds_with_observations()
    cat_params = load_catboost_params()

    print("Settlement Stats Experiment")
    print("=" * 70)
    print(f"All rounds: {all_rounds}")
    print(f"Val rounds: {val_rounds}")
    print(f"CatBoost params: {cat_params}\n")

    # Extract settlement stats for all rounds with observations
    print("Extracting settlement stats from observations...")
    settle_stats = {}
    for rn in val_rounds:
        ss = extract_settlement_stats_from_observations(rn)
        settle_stats[rn] = ss
        if ss:
            print(f"  R{rn}: pop={ss['avg_population']:.3f} food={ss['avg_food']:.3f} "
                  f"wealth={ss['avg_wealth']:.3f} defense={ss['avg_defense']:.3f} "
                  f"alive={ss['alive_ratio']:.3f} factions={ss['n_factions']} "
                  f"HHI={ss['faction_concentration']:.3f} s/obs={ss['settlements_per_obs']:.1f}")

    # K value: use 49 (known good) for fair comparison
    k = 49
    print(f"\nUsing k={k} for empirical bin blending\n")

    # Leave-one-round-out evaluation
    print(f"{'─' * 90}")
    print(f"  {'Round':<8s} {'Baseline seeds':>35s} {'Avg':>6s}  |  {'Extended seeds':>35s} {'Avg':>6s}  {'Delta':>6s}")
    print(f"{'─' * 90}")

    baseline_avgs = []
    extended_avgs = []

    for val_rn in val_rounds:
        train_rounds = [r for r in all_rounds if r != val_rn]

        # Load validation data
        val_states, val_gts = [], []
        all_obs = []
        for si in SEEDS:
            state, gt = load_map(val_rn, si)
            val_states.append(state)
            val_gts.append(gt)
            all_obs.extend(load_obs(val_rn, si))

        obs_stats = compute_round_stats_from_observations(all_obs, val_states[0])
        obs_stats_arr = round_stats_to_array(obs_stats)
        bin_dists = build_empirical_distributions(all_obs, val_states)
        bin_counts = get_bin_coverage_stats(all_obs, val_states)

        val_seed_info = [{"obs_stats_arr": obs_stats_arr} for _ in SEEDS]

        # Settlement stats for val round
        settle_arr_val = settlement_stats_to_array(settle_stats.get(val_rn))

        # --- Baseline ---
        X_train, y_train, w_train = build_training_data_baseline(train_rounds)
        baseline_scores = train_and_evaluate(
            X_train, y_train, w_train, val_seed_info, val_states, val_gts,
            bin_dists, bin_counts, k, cat_params, is_extended=False,
        )
        baseline_avg = np.mean(baseline_scores)
        baseline_avgs.append(baseline_avg)

        # --- Extended (with settlement stats) ---
        # For training, use settle stats for rounds that have them, avg for rest
        X_ext, y_ext, w_ext = build_training_data_extended(train_rounds, settle_stats)
        extended_scores = train_and_evaluate(
            X_ext, y_ext, w_ext, val_seed_info, val_states, val_gts,
            bin_dists, bin_counts, k, cat_params, is_extended=True,
            settle_arr_val=settle_arr_val,
        )
        extended_avg = np.mean(extended_scores)
        extended_avgs.append(extended_avg)

        delta = extended_avg - baseline_avg
        b_str = " ".join(f"{s:.1f}" for s in baseline_scores)
        e_str = " ".join(f"{s:.1f}" for s in extended_scores)
        sign = "+" if delta >= 0 else ""
        print(f"  R{val_rn:<6d} {b_str:>35s} {baseline_avg:>6.2f}  |  {e_str:>35s} {extended_avg:>6.2f}  {sign}{delta:>5.2f}")

    print(f"{'─' * 90}")
    overall_b = np.mean(baseline_avgs)
    overall_e = np.mean(extended_avgs)
    delta = overall_e - overall_b
    sign = "+" if delta >= 0 else ""
    print(f"  {'OVERALL':<8s} {'':>35s} {overall_b:>6.2f}  |  {'':>35s} {overall_e:>6.2f}  {sign}{delta:>5.2f}")

    # Print settlement stats summary
    print(f"\n{'=' * 70}")
    print(f"Settlement stats summary across rounds:")
    print(f"  {'Round':>5s}  {'pop':>6s}  {'food':>6s}  {'wealth':>6s}  {'def':>6s}  {'alive':>6s}  {'factions':>8s}  {'HHI':>6s}")
    for rn in val_rounds:
        ss = settle_stats.get(rn)
        if ss:
            print(f"  R{rn:>3d}  {ss['avg_population']:>6.3f}  {ss['avg_food']:>6.3f}  "
                  f"{ss['avg_wealth']:>6.3f}  {ss['avg_defense']:>6.3f}  "
                  f"{ss['alive_ratio']:>6.3f}  {ss['n_factions']:>8d}  {ss['faction_concentration']:>6.3f}")


if __name__ == "__main__":
    main()
