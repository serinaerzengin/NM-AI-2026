"""Fit simulator parameters against ground truth from completed rounds.

Strategy:
  Stage 1: Sweep expansion_rate (the dominant parameter) per round
  Stage 2: Fine-tune secondary params (optional)
  Stage 3: Build observed_rate → expansion_rate mapping for live rounds
"""

import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))
import store
from simulator.sim import SimParams, run_monte_carlo, GRID_TO_CLASS
from simulator.evaluate import compute_score, EVAL_DIR


def sweep_expansion_rate(
    round_number: int,
    rates: list[float] | None = None,
    n_runs: int = 100,
    seeds: list[int] | None = None,
) -> dict:
    """Sweep expansion_rate for a single round. Returns best rate and all scores."""
    if rates is None:
        rates = [0.001, 0.005, 0.01, 0.03, 0.05, 0.08, 0.10, 0.13, 0.16, 0.20, 0.25]
    if seeds is None:
        seeds = list(range(5))

    results = {}
    best_rate = 0.0
    best_score = -1.0

    for rate in rates:
        params = SimParams(expansion_rate=rate)
        scores = []

        for si in seeds:
            state = store.load_initial_state(round_number, si)
            gt_data = store.load_ground_truth(round_number, si)
            if state is None or gt_data is None:
                continue

            gt = np.array(gt_data["ground_truth"])
            pred = run_monte_carlo(
                state["grid"], state["settlements"], params, n_runs=n_runs
            )
            metrics = compute_score(pred, gt)
            scores.append(metrics["score"])

        if scores:
            avg = sum(scores) / len(scores)
            results[rate] = {
                "mean_score": round(avg, 2),
                "per_seed": [round(s, 2) for s in scores],
            }
            print(f"  rate={rate:.3f}: score={avg:.1f}")

            if avg > best_score:
                best_score = avg
                best_rate = rate

    return {
        "round": round_number,
        "best_rate": best_rate,
        "best_score": round(best_score, 2),
        "all_results": results,
    }


def compute_observed_settle_rate(round_number: int, seed_index: int = 0) -> float:
    """Compute the observed settlement rate from ground truth (for calibration)."""
    gt_data = store.load_ground_truth(round_number, seed_index)
    state = store.load_initial_state(round_number, seed_index)
    if gt_data is None or state is None:
        return 0.0

    gt = np.array(gt_data["ground_truth"])
    grid = state["grid"]
    h, w = len(grid), len(grid[0])

    settle_probs = []
    for y in range(h):
        for x in range(w):
            if grid[y][x] not in (10, 5):
                settle_probs.append(gt[y][x][1] + gt[y][x][2])

    return float(np.mean(settle_probs)) if settle_probs else 0.0


def fit_all_rounds(
    rounds: list[int] | None = None,
    n_runs: int = 100,
) -> dict:
    """Fit expansion_rate per round and build the rate mapping.

    Returns calibration data: observed_settle_rate → best_expansion_rate.
    """
    if rounds is None:
        rounds = [r for r in store.list_stored_rounds()
                  if store.load_ground_truth(r, 0) is not None]

    print(f"Fitting expansion_rate for {len(rounds)} rounds...")
    print()

    calibration = []
    all_results = {}

    for rn in rounds:
        print(f"=== Round {rn} ===")
        t0 = time.time()
        result = sweep_expansion_rate(rn, n_runs=n_runs)
        elapsed = time.time() - t0
        all_results[f"round_{rn}"] = result

        # Get observed settlement rate from ground truth
        observed_rates = []
        for si in range(5):
            r = compute_observed_settle_rate(rn, si)
            observed_rates.append(r)
        obs_rate = float(np.mean(observed_rates))

        calibration.append({
            "round": rn,
            "observed_settle_rate": round(obs_rate, 4),
            "best_expansion_rate": result["best_rate"],
            "best_score": result["best_score"],
        })
        print(f"  → observed_rate={obs_rate:.4f}, best_expansion_rate={result['best_rate']:.3f}, score={result['best_score']:.1f} ({elapsed:.0f}s)")
        print()

    # Fit linear mapping: observed_rate → expansion_rate
    obs_rates = np.array([c["observed_settle_rate"] for c in calibration])
    exp_rates = np.array([c["best_expansion_rate"] for c in calibration])

    if len(obs_rates) >= 2:
        A = np.column_stack([obs_rates, np.ones_like(obs_rates)])
        result_fit = np.linalg.lstsq(A, exp_rates, rcond=None)
        slope, intercept = result_fit[0]
        mapping = {"slope": round(float(slope), 4), "intercept": round(float(intercept), 4)}
        print(f"Rate mapping: expansion_rate = {slope:.4f} * observed_settle_rate + {intercept:.4f}")
    else:
        mapping = {"slope": 1.0, "intercept": 0.0}

    output = {
        "calibration": calibration,
        "rate_mapping": mapping,
        "per_round": all_results,
    }

    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    out_path = EVAL_DIR / "fit_results.json"
    out_path.write_text(json.dumps(output, indent=2))
    print(f"\nSaved to {out_path}")

    return output


def get_expansion_rate_for_observed(observed_rate: float, fit_results: dict | None = None) -> float:
    """Given an observed settlement rate from live queries, return the expansion_rate param."""
    if fit_results is None:
        fit_path = EVAL_DIR / "fit_results.json"
        if fit_path.exists():
            fit_results = json.loads(fit_path.read_text())
        else:
            # Fallback: rough mapping
            return max(0.001, observed_rate * 0.8)

    m = fit_results["rate_mapping"]
    rate = m["slope"] * observed_rate + m["intercept"]
    return max(0.001, min(0.3, rate))


if __name__ == "__main__":
    fit_all_rounds(n_runs=50)
