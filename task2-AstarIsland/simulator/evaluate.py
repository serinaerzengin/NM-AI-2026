"""Evaluate simulator predictions against ground truth.

Computes competition metrics and saves results to data/local-eval/.
"""

import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))
import store
from simulator.sim import SimParams, run_monte_carlo, GRID_TO_CLASS, NUM_CLASSES

EVAL_DIR = store.EVAL_DIR


def compute_score(pred: np.ndarray, gt: np.ndarray) -> dict:
    """Compute competition score and diagnostic metrics.

    Both pred and gt are (H, W, 6) probability tensors.
    """
    eps = 1e-10
    gt_c = np.clip(gt, eps, None)
    pred_c = np.clip(pred, eps, None)

    # Entropy of ground truth
    entropy = -np.sum(gt_c * np.log(gt_c), axis=-1)

    # KL divergence
    kl = np.sum(gt_c * np.log(gt_c / pred_c), axis=-1)

    # Entropy-weighted KL
    total_entropy = entropy.sum()
    if total_entropy < eps:
        weighted_kl = 0.0
    else:
        weighted_kl = (entropy * kl).sum() / total_entropy

    score = max(0.0, min(100.0, 100.0 * np.exp(-3 * weighted_kl)))

    # Dynamic cell mask
    dynamic = entropy > 0.01

    # Per-class Brier score on dynamic cells
    brier = {}
    class_names = ["empty", "settlement", "port", "ruin", "forest", "mountain"]
    if dynamic.sum() > 0:
        for c in range(NUM_CLASSES):
            brier[class_names[c]] = float(
                np.mean((pred[:, :, c][dynamic] - gt[:, :, c][dynamic]) ** 2)
            )

    # Settlement rate calibration
    if dynamic.sum() > 0:
        pred_rate = float((pred[:, :, 1] + pred[:, :, 2])[dynamic].mean())
        true_rate = float((gt[:, :, 1] + gt[:, :, 2])[dynamic].mean())
    else:
        pred_rate = true_rate = 0.0

    # Top-N cell concentration
    weighted_kl_map = entropy * kl
    flat = weighted_kl_map.flatten()
    total = flat.sum()
    if total > eps:
        sorted_vals = np.sort(flat)[::-1]
        top50 = float(sorted_vals[:50].sum() / total)
        top100 = float(sorted_vals[:100].sum() / total)
    else:
        top50 = top100 = 0.0

    return {
        "score": round(score, 2),
        "weighted_kl": round(float(weighted_kl), 6),
        "brier": {k: round(v, 6) for k, v in brier.items()},
        "pred_settle_rate": round(pred_rate, 4),
        "true_settle_rate": round(true_rate, 4),
        "rate_error": round(abs(pred_rate - true_rate), 4),
        "n_dynamic": int(dynamic.sum()),
        "top50_contrib": round(top50, 3),
        "top100_contrib": round(top100, 3),
    }


def evaluate_params(
    params: SimParams,
    rounds: list[int] | None = None,
    seeds: list[int] | None = None,
    n_runs: int = 200,
    label: str = "eval",
) -> dict:
    """Run simulator with given params against ground truth.

    Saves results to data/local-eval/{label}.json and returns the results dict.
    """
    if rounds is None:
        rounds = store.list_stored_rounds()
        # Only evaluate completed rounds with ground truth
        rounds = [r for r in rounds if store.load_ground_truth(r, 0) is not None]
    if seeds is None:
        seeds = list(range(5))

    results = {}
    all_scores = []

    for rn in rounds:
        meta = store.load_round_meta(rn)
        if meta is None:
            continue
        round_key = f"round_{rn}"
        results[round_key] = {}
        round_scores = []

        for si in seeds:
            gt_data = store.load_ground_truth(rn, si)
            state = store.load_initial_state(rn, si)
            if gt_data is None or state is None:
                continue

            gt = np.array(gt_data["ground_truth"])
            grid = state["grid"]
            settlements = state["settlements"]

            t0 = time.time()
            pred = run_monte_carlo(grid, settlements, params, n_runs=n_runs)
            elapsed = time.time() - t0

            metrics = compute_score(pred, gt)
            metrics["elapsed_s"] = round(elapsed, 1)
            results[round_key][f"seed_{si}"] = metrics

            round_scores.append(metrics["score"])
            all_scores.append(metrics["score"])

            print(
                f"  R{rn} S{si}: score={metrics['score']:.1f} "
                f"rate_err={metrics['rate_error']:.4f} "
                f"brier_s={metrics['brier'].get('settlement', 0):.4f} "
                f"({elapsed:.1f}s)"
            )

        if round_scores:
            avg = sum(round_scores) / len(round_scores)
            results[round_key]["mean_score"] = round(avg, 2)
            print(f"  R{rn} mean: {avg:.1f}")

    # Summary
    output = {
        "label": label,
        "params": {
            k: v for k, v in params.__dict__.items()
        },
        "n_runs": n_runs,
        "results": results,
        "mean_score": round(sum(all_scores) / len(all_scores), 2) if all_scores else 0,
    }

    # Save
    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    out_path = EVAL_DIR / f"{label}.json"
    out_path.write_text(json.dumps(output, indent=2))
    print(f"\nSaved to {out_path}")
    print(f"Overall mean score: {output['mean_score']}")

    return output


if __name__ == "__main__":
    # Quick test with default params
    print("Evaluating default params on all completed rounds...")
    print()
    params = SimParams()
    evaluate_params(params, n_runs=50, label="default_params")
