"""Error analysis: where does the pipeline lose the most points?

Breaks down entropy-weighted KL divergence by:
  - Distance to nearest settlement
  - Terrain type (forest, plain, initial settlement)
  - Coastal vs inland
  - Settlement density
  - Ground truth entropy (easy vs hard cells)
  - Per-class prediction errors
  - Prediction confidence vs accuracy

Uses leave-one-round-out with stored observations.
"""

import json
import sys
from pathlib import Path
from collections import defaultdict

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

from astar.types import (
    MapState, Observation, RoundStats, Prediction, NUM_CLASSES,
    OCEAN, MOUNTAIN, FOREST, SETTLEMENT, PORT,
)
from astar.features import compute_features, FEATURE_NAMES
from astar.calibration import (
    compute_round_stats_from_ground_truth,
    compute_round_stats_from_observations,
    round_stats_to_array,
)
from astar.scoring import score_prediction
from astar.predictor import _build_row, _static_prediction, _is_static_cell
from astar.empirical_bins import (
    build_empirical_distributions, predict_with_empirical_bins,
    get_bin_coverage_stats, PROB_FLOOR, _cell_bin_key,
)
from catboost import CatBoostRegressor
import store

DATA_DIR = Path(__file__).parent.parent / "data" / "rounds"
BEST_PARAMS_PATH = Path(__file__).parent.parent / "best_params_all.json"
SEEDS = list(range(5))

# Feature indices
_DIST_IDX = FEATURE_NAMES.index("dist_nearest_settlement")
_COASTAL_IDX = FEATURE_NAMES.index("adjacent_ocean")
_FOREST_IDX = FEATURE_NAMES.index("is_forest")
_MOUNTAIN_IDX = FEATURE_NAMES.index("is_mountain")
_OCEAN_IDX = FEATURE_NAMES.index("is_ocean")
_SETTLEMENT_IDX = FEATURE_NAMES.index("is_initial_settlement")
_SETTLE_R5_IDX = FEATURE_NAMES.index("settlements_r5")
_TOTAL_IDX = FEATURE_NAMES.index("total_settlements")
_LAND_IDX = FEATURE_NAMES.index("is_land")
_PORT_IDX = FEATURE_NAMES.index("is_initial_port")


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


def generate_prediction(models, state, obs_stats, bin_dists, bin_counts, k=49):
    """Generate full pipeline prediction for a map."""
    features = compute_features(state)
    stats_arr = round_stats_to_array(obs_stats)
    h, w = state.grid.shape
    probs = np.zeros((h, w, NUM_CLASSES), dtype=np.float32)
    for r in range(h):
        for c in range(w):
            sp = _static_prediction(state.grid[r, c])
            if sp is not None:
                probs[r, c] = sp
            else:
                row = _build_row(features[r, c], stats_arr)
                X = np.array([row], dtype=np.float32)
                pred = np.array([
                    0.0 if m is None else float(m.predict(X)[0])
                    for m in models
                ])
                probs[r, c] = pred
    probs = np.maximum(probs, PROB_FLOOR)
    probs = probs / probs.sum(axis=-1, keepdims=True)

    if bin_dists:
        pred_obj = Prediction(probs=probs)
        final = predict_with_empirical_bins(state, bin_dists, pred_obj, bin_counts=bin_counts, k=k)
        return final.probs
    return probs


def analyze_errors(pred, gt, features, state):
    """Analyze per-cell errors broken down by cell properties."""
    eps = 1e-12
    h, w = gt.shape[:2]

    entropy = -np.sum(gt * np.log(gt + eps), axis=-1)
    kl = np.sum(gt * np.log((gt + eps) / (pred + eps)), axis=-1)
    weighted_kl = entropy * kl

    total_entropy = entropy.sum()
    if total_entropy < eps:
        return None

    cells = []
    for r in range(h):
        for c in range(w):
            if entropy[r, c] < 0.01:
                continue  # skip static cells
            feat = features[r, c]
            dist = feat[_DIST_IDX]
            coastal = feat[_COASTAL_IDX] > 0.5
            is_forest = feat[_FOREST_IDX] > 0.5
            is_settlement = feat[_SETTLEMENT_IDX] > 0.5
            is_port = feat[_PORT_IDX] > 0.5
            density_r5 = feat[_SETTLE_R5_IDX]

            # Distance bucket
            if dist < 0.5:
                dist_bucket = "d=0 (initial)"
            elif dist < 1.5:
                dist_bucket = "d=1"
            elif dist < 2.5:
                dist_bucket = "d=2"
            elif dist < 4.5:
                dist_bucket = "d=3-4"
            elif dist < 7.5:
                dist_bucket = "d=5-7"
            else:
                dist_bucket = "d=8+"

            # Terrain type
            if is_settlement:
                terrain = "initial_settlement"
            elif is_port:
                terrain = "initial_port"
            elif is_forest:
                terrain = "forest"
            else:
                terrain = "plain"

            # Dominant ground truth class
            gt_dominant = int(np.argmax(gt[r, c]))
            pred_dominant = int(np.argmax(pred[r, c]))

            # Per-class errors
            class_errors = {}
            for cls in range(NUM_CLASSES):
                if gt[r, c, cls] > 0.01:
                    class_errors[cls] = gt[r, c, cls] * np.log(
                        (gt[r, c, cls] + eps) / (pred[r, c, cls] + eps)
                    )

            # Entropy bucket
            if entropy[r, c] < 0.3:
                ent_bucket = "low (< 0.3)"
            elif entropy[r, c] < 0.7:
                ent_bucket = "med (0.3-0.7)"
            elif entropy[r, c] < 1.2:
                ent_bucket = "high (0.7-1.2)"
            else:
                ent_bucket = "very high (> 1.2)"

            # Confidence
            pred_conf = float(pred[r, c].max())
            if pred_conf > 0.8:
                conf_bucket = "very confident (>0.8)"
            elif pred_conf > 0.5:
                conf_bucket = "confident (0.5-0.8)"
            elif pred_conf > 0.3:
                conf_bucket = "uncertain (0.3-0.5)"
            else:
                conf_bucket = "very uncertain (<0.3)"

            # Has empirical bin?
            bin_key = _cell_bin_key(feat)
            has_bin = bin_key is not None

            cells.append({
                "r": r, "c": c,
                "entropy": float(entropy[r, c]),
                "kl": float(kl[r, c]),
                "weighted_kl": float(weighted_kl[r, c]),
                "contribution": float(weighted_kl[r, c] / total_entropy),
                "dist_bucket": dist_bucket,
                "dist": float(dist),
                "coastal": coastal,
                "terrain": terrain,
                "density_r5": float(density_r5),
                "gt_dominant": gt_dominant,
                "pred_dominant": pred_dominant,
                "correct_dominant": gt_dominant == pred_dominant,
                "ent_bucket": ent_bucket,
                "conf_bucket": conf_bucket,
                "class_errors": class_errors,
                "has_bin": has_bin,
                "gt_probs": gt[r, c].tolist(),
                "pred_probs": pred[r, c].tolist(),
            })

    return cells


CLASS_NAMES = ["Empty", "Settlement", "Port", "Ruin", "Forest", "Mountain"]


def print_breakdown(all_cells, group_key, title):
    """Print error breakdown by a grouping key."""
    groups = defaultdict(list)
    for cell in all_cells:
        groups[cell[group_key]].append(cell)

    print(f"\n  {title}")
    print(f"  {'Group':<25s} {'Cells':>6s} {'Avg KL':>8s} {'Avg wKL':>8s} {'% Total':>8s} {'Dom Acc':>8s}")
    print(f"  {'─' * 65}")

    total_wkl = sum(c["weighted_kl"] for c in all_cells)
    rows = []
    for key in sorted(groups.keys(), key=str):
        cells = groups[key]
        avg_kl = np.mean([c["kl"] for c in cells])
        avg_wkl = np.mean([c["weighted_kl"] for c in cells])
        sum_wkl = sum(c["weighted_kl"] for c in cells)
        pct = 100 * sum_wkl / total_wkl if total_wkl > 0 else 0
        dom_acc = np.mean([c["correct_dominant"] for c in cells])
        rows.append((key, len(cells), avg_kl, avg_wkl, pct, dom_acc))

    # Sort by % total descending
    rows.sort(key=lambda x: -x[4])
    for key, n, avg_kl, avg_wkl, pct, dom_acc in rows:
        print(f"  {str(key):<25s} {n:>6d} {avg_kl:>8.4f} {avg_wkl:>8.4f} {pct:>7.1f}% {dom_acc:>7.1%}")


def print_class_errors(all_cells):
    """Analyze which prediction classes contribute most error."""
    print(f"\n  Per-class KL contribution (which classes do we predict worst?)")
    print(f"  {'Class':<15s} {'Total KL':>10s} {'% of KL':>8s} {'Avg |gt-pred|':>14s} {'Cells w/ class':>14s}")
    print(f"  {'─' * 65}")

    class_kl = defaultdict(float)
    class_abs_err = defaultdict(list)
    class_count = defaultdict(int)

    for cell in all_cells:
        for cls, kl_contrib in cell["class_errors"].items():
            class_kl[cls] += kl_contrib * cell["entropy"]
            class_abs_err[cls].append(abs(cell["gt_probs"][cls] - cell["pred_probs"][cls]))
            class_count[cls] += 1

    total_kl = sum(class_kl.values())
    for cls in range(NUM_CLASSES):
        if cls not in class_kl:
            continue
        pct = 100 * class_kl[cls] / total_kl if total_kl > 0 else 0
        avg_abs = np.mean(class_abs_err[cls]) if class_abs_err[cls] else 0
        print(f"  {CLASS_NAMES[cls]:<15s} {class_kl[cls]:>10.2f} {pct:>7.1f}% {avg_abs:>14.4f} {class_count[cls]:>14d}")


def print_worst_cells(all_cells, n=15):
    """Show the worst-predicted cells."""
    print(f"\n  Top {n} worst cells (highest weighted KL contribution):")
    print(f"  {'Pos':<8s} {'wKL':>7s} {'Entropy':>8s} {'Dist':>5s} {'Terrain':<12s} {'GT dominant':<12s} {'Pred dominant':<14s} {'GT probs':<35s} {'Pred probs'}")
    print(f"  {'─' * 130}")

    sorted_cells = sorted(all_cells, key=lambda c: -c["weighted_kl"])
    for cell in sorted_cells[:n]:
        gt_str = " ".join(f"{p:.2f}" for p in cell["gt_probs"])
        pred_str = " ".join(f"{p:.2f}" for p in cell["pred_probs"])
        print(f"  ({cell['r']:2d},{cell['c']:2d}) {cell['weighted_kl']:>7.4f} {cell['entropy']:>8.3f} "
              f"{cell['dist']:>5.1f} {cell['terrain']:<12s} "
              f"{CLASS_NAMES[cell['gt_dominant']]:<12s} {CLASS_NAMES[cell['pred_dominant']]:<14s} "
              f"{gt_str:<35s} {pred_str}")


def print_prediction_bias(all_cells):
    """Check if we systematically over/under-predict certain classes."""
    print(f"\n  Prediction bias (avg ground_truth - avg prediction per class):")
    print(f"  {'Class':<15s} {'Avg GT':>8s} {'Avg Pred':>9s} {'Bias':>8s} {'Direction'}")
    print(f"  {'─' * 55}")

    for cls in range(NUM_CLASSES):
        gt_vals = [c["gt_probs"][cls] for c in all_cells]
        pred_vals = [c["pred_probs"][cls] for c in all_cells]
        avg_gt = np.mean(gt_vals)
        avg_pred = np.mean(pred_vals)
        bias = avg_gt - avg_pred
        direction = "UNDER-predict" if bias > 0.005 else ("OVER-predict" if bias < -0.005 else "OK")
        print(f"  {CLASS_NAMES[cls]:<15s} {avg_gt:>8.4f} {avg_pred:>9.4f} {bias:>+8.4f} {direction}")


def main():
    all_rounds = get_all_rounds()
    obs_rounds = get_rounds_with_observations()
    test_rounds = [8, 9, 10, 11, 14, 15]
    test_rounds = [r for r in test_rounds if r in obs_rounds]

    print(f"Error analysis on rounds: {test_rounds}\n")

    all_cells_global = []

    for val_rn in test_rounds:
        train_rounds = [r for r in all_rounds if r != val_rn]
        print(f"{'═' * 70}")
        print(f"  Round {val_rn}")
        print(f"{'═' * 70}")

        models = train_catboost(train_rounds)

        states, gts, all_obs = [], [], []
        for si in SEEDS:
            state, gt = load_map(val_rn, si)
            states.append(state)
            gts.append(gt)
            all_obs.extend(load_observations(val_rn, si))

        obs_stats = compute_round_stats_from_observations(all_obs, states[0])
        bin_dists = build_empirical_distributions(all_obs, states)
        bin_counts = get_bin_coverage_stats(all_obs, states)

        round_cells = []
        for si in SEEDS:
            pred = generate_prediction(models, states[si], obs_stats, bin_dists, bin_counts, k=49)
            features = compute_features(states[si])
            cells = analyze_errors(pred, gts[si], features, states[si])
            if cells:
                round_cells.extend(cells)
                all_cells_global.extend(cells)

        score = score_prediction(
            generate_prediction(models, states[0], obs_stats, bin_dists, bin_counts),
            gts[0]
        )

        print_breakdown(round_cells, "dist_bucket", f"By distance to settlement (R{val_rn})")
        print_breakdown(round_cells, "terrain", f"By terrain type (R{val_rn})")
        print_breakdown(round_cells, "coastal", f"By coastal/inland (R{val_rn})")
        print_prediction_bias(round_cells)
        print()

    # Global analysis across all rounds
    print(f"\n{'═' * 70}")
    print(f"  GLOBAL ANALYSIS (all {len(test_rounds)} rounds combined)")
    print(f"  Total dynamic cells analyzed: {len(all_cells_global)}")
    print(f"{'═' * 70}")

    print_breakdown(all_cells_global, "dist_bucket", "By distance to settlement")
    print_breakdown(all_cells_global, "terrain", "By terrain type")
    print_breakdown(all_cells_global, "coastal", "By coastal/inland")
    print_breakdown(all_cells_global, "ent_bucket", "By ground truth entropy")
    print_breakdown(all_cells_global, "conf_bucket", "By prediction confidence")
    print_class_errors(all_cells_global)
    print_prediction_bias(all_cells_global)
    print_worst_cells(all_cells_global, n=20)


if __name__ == "__main__":
    main()
