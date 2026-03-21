"""Optuna optimization for sim_v2 (probabilistic state machine).

Much simpler parameter space than v1 — only 5 key params + 2 mapping params.
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import optuna

sys.path.insert(0, str(Path(__file__).parent.parent))
import store
from simulator.sim_v2 import SimParams, run_monte_carlo
from simulator.evaluate import compute_score, EVAL_DIR

EVAL_ROUNDS = [r for r in store.list_stored_rounds() if store.load_ground_truth(r, 0) is not None]
EVAL_SEEDS = [0]
N_RUNS = 30


def compute_observed_rate(rn: int) -> float:
    rates = []
    for si in EVAL_SEEDS:
        gt_data = store.load_ground_truth(rn, si)
        state = store.load_initial_state(rn, si)
        if gt_data is None or state is None:
            continue
        gt = np.array(gt_data["ground_truth"])
        grid = state["grid"]
        h, w = len(grid), len(grid[0])
        for y in range(h):
            for x in range(w):
                if grid[y][x] not in (10, 5):
                    rates.append(gt[y][x][1] + gt[y][x][2])
    return float(np.mean(rates))


ROUND_RATES = {rn: compute_observed_rate(rn) for rn in EVAL_ROUNDS}
print(f"Rates: {ROUND_RATES}")


def objective(trial: optuna.Trial) -> float:
    # Shared physics params
    collapse_base = trial.suggest_float("collapse_base", 0.02, 0.20)
    collapse_forest_bonus = trial.suggest_float("collapse_forest_bonus", 0.0, 0.03)
    ruin_to_forest = trial.suggest_float("ruin_to_forest", 0.02, 0.20)
    ruin_to_empty = trial.suggest_float("ruin_to_empty", 0.05, 0.30)
    ruin_rebuild = trial.suggest_float("ruin_rebuild", 0.01, 0.15)
    plains_preference = trial.suggest_float("plains_preference", 1.0, 4.0)
    port_chance = trial.suggest_float("port_chance", 0.01, 0.10)
    expand_range = trial.suggest_int("expand_range", 3, 6)

    # Expansion mapping: expand_prob = slope * observed_rate + intercept
    exp_slope = trial.suggest_float("exp_slope", 0.2, 2.0)
    exp_intercept = trial.suggest_float("exp_intercept", -0.05, 0.10)

    scores = []
    for rn in EVAL_ROUNDS:
        observed_rate = ROUND_RATES[rn]
        expand_prob = max(0.001, min(0.30, exp_slope * observed_rate + exp_intercept))

        params = SimParams(
            expand_prob=expand_prob,
            expand_range=expand_range,
            collapse_base=collapse_base,
            collapse_forest_bonus=collapse_forest_bonus,
            ruin_to_forest=ruin_to_forest,
            ruin_to_empty=ruin_to_empty,
            ruin_rebuild=ruin_rebuild,
            plains_preference=plains_preference,
            port_chance=port_chance,
        )

        for si in EVAL_SEEDS:
            gt_data = store.load_ground_truth(rn, si)
            state_data = store.load_initial_state(rn, si)
            if gt_data is None or state_data is None:
                continue

            gt = np.array(gt_data["ground_truth"])
            pred = run_monte_carlo(
                state_data["grid"], state_data["settlements"],
                params, n_runs=N_RUNS,
            )
            metrics = compute_score(pred, gt)
            scores.append(metrics["score"])

    return float(np.mean(scores)) if scores else 0.0


def run_optimization(n_trials: int = 200, n_jobs: int = 1, study_name: str = "sim_v2_opt"):
    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    storage = f"sqlite:///{EVAL_DIR}/optuna_{study_name}.db"

    study = optuna.create_study(
        study_name=study_name,
        storage=storage,
        direction="maximize",
        load_if_exists=True,
    )

    print(f"Rounds: {EVAL_ROUNDS}, Seeds: {EVAL_SEEDS}, MC runs: {N_RUNS}")
    print(f"Running {n_trials} trials, {n_jobs} workers")

    study.optimize(objective, n_trials=n_trials, n_jobs=n_jobs, show_progress_bar=True)

    print(f"\nBest: score={study.best_trial.value:.1f}")
    for k, v in study.best_trial.params.items():
        print(f"  {k}: {v}")

    result = {
        "best_score": round(study.best_trial.value, 2),
        "best_params": {k: round(v, 4) if isinstance(v, float) else v
                        for k, v in study.best_trial.params.items()},
        "n_trials": len(study.trials),
    }
    out_path = EVAL_DIR / f"optuna_{study_name}_best.json"
    out_path.write_text(json.dumps(result, indent=2))
    print(f"Saved to {out_path}")
    return study


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--n-trials", type=int, default=150)
    parser.add_argument("--n-jobs", type=int, default=4)
    parser.add_argument("--study-name", type=str, default="sim_v2_opt")
    args = parser.parse_args()
    run_optimization(n_trials=args.n_trials, n_jobs=args.n_jobs, study_name=args.study_name)
