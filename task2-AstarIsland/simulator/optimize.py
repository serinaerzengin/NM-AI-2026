"""Optuna-based hyperparameter optimization for the Astar Island simulator.

Parallelizable — run multiple instances against the same SQLite study.
Usage:
    uv run python -m simulator.optimize              # single process
    uv run python -m simulator.optimize --n-jobs 4   # 4 parallel workers
"""

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import optuna

sys.path.insert(0, str(Path(__file__).parent.parent))
import store
from simulator.sim import SimParams, run_monte_carlo
from simulator.evaluate import compute_score, EVAL_DIR

# Rounds with ground truth available
EVAL_ROUNDS = [r for r in store.list_stored_rounds() if store.load_ground_truth(r, 0) is not None]
# Use 2 seeds per round for speed during optimization
EVAL_SEEDS = [0, 2]
N_RUNS = 50  # MC runs per evaluation (tradeoff: speed vs accuracy)


def compute_observed_rate(rn: int, si: int) -> float:
    """Get the true settlement rate from ground truth (used to set expansion_rate per round)."""
    gt_data = store.load_ground_truth(rn, si)
    state_data = store.load_initial_state(rn, si)
    if gt_data is None or state_data is None:
        return 0.1
    gt = np.array(gt_data["ground_truth"])
    grid = state_data["grid"]
    h, w = len(grid), len(grid[0])
    rates = []
    for y in range(h):
        for x in range(w):
            if grid[y][x] not in (10, 5):
                rates.append(gt[y][x][1] + gt[y][x][2])
    return float(np.mean(rates))


# Precompute observed rates per round (expansion_rate varies, other params shared)
ROUND_RATES = {}
for _rn in EVAL_ROUNDS:
    rates = [compute_observed_rate(_rn, si) for si in EVAL_SEEDS]
    ROUND_RATES[_rn] = float(np.mean(rates))
print(f"Observed settlement rates: {ROUND_RATES}")


def objective(trial: optuna.Trial) -> float:
    """Optimize shared simulator params across all rounds.

    expansion_rate is set PER ROUND using a linear mapping from observed settlement rate.
    All other params are shared across rounds (they represent the simulation mechanics).
    """

    # Shared params (same across all rounds — the "physics" of the simulation)
    winter_severity = trial.suggest_float("winter_severity", 0.15, 0.80)
    raid_aggression = trial.suggest_float("raid_aggression", 0.05, 0.60)
    food_per_forest = trial.suggest_float("food_per_forest", 0.10, 0.80)
    base_food_production = trial.suggest_float("base_food_production", 0.05, 0.40)
    expand_pop_threshold = trial.suggest_float("expand_pop_threshold", 2.0, 6.0)
    reclamation_forest_rate = trial.suggest_float("reclamation_forest_rate", 0.02, 0.25)
    reclamation_empty_rate = trial.suggest_float("reclamation_empty_rate", 0.05, 0.35)
    reclamation_settle_rate = trial.suggest_float("reclamation_settle_rate", 0.01, 0.20)
    trade_food_bonus = trial.suggest_float("trade_food_bonus", 0.01, 0.30)
    port_build_chance = trial.suggest_float("port_build_chance", 0.01, 0.15)
    init_pop_mean = trial.suggest_float("init_pop_mean", 1.5, 5.0)
    init_food = trial.suggest_float("init_food", 0.3, 2.0)

    # Expansion rate mapping: expansion_rate = slope * observed_rate + intercept
    exp_slope = trial.suggest_float("exp_slope", 0.3, 3.0)
    exp_intercept = trial.suggest_float("exp_intercept", -0.10, 0.10)

    scores = []
    for rn in EVAL_ROUNDS:
        # Set expansion_rate from observed rate via the linear mapping
        observed_rate = ROUND_RATES[rn]
        expansion_rate = max(0.001, exp_slope * observed_rate + exp_intercept)

        params = SimParams(
            expansion_rate=expansion_rate,
            winter_severity=winter_severity,
            raid_aggression=raid_aggression,
            food_per_forest=food_per_forest,
            base_food_production=base_food_production,
            expand_pop_threshold=expand_pop_threshold,
            reclamation_forest_rate=reclamation_forest_rate,
            reclamation_empty_rate=reclamation_empty_rate,
            reclamation_settle_rate=reclamation_settle_rate,
            trade_food_bonus=trade_food_bonus,
            port_build_chance=port_build_chance,
            init_pop_mean=init_pop_mean,
            init_food=init_food,
        )

        for si in EVAL_SEEDS:
            gt_data = store.load_ground_truth(rn, si)
            state_data = store.load_initial_state(rn, si)
            if gt_data is None or state_data is None:
                continue

            gt = np.array(gt_data["ground_truth"])
            pred = run_monte_carlo(
                state_data["grid"],
                state_data["settlements"],
                params,
                n_runs=N_RUNS,
            )
            metrics = compute_score(pred, gt)
            scores.append(metrics["score"])

    if not scores:
        return 0.0

    return float(np.mean(scores))


def run_optimization(n_trials: int = 200, n_jobs: int = 1, study_name: str = "sim_v2"):
    """Run Optuna optimization."""
    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    storage = f"sqlite:///{EVAL_DIR}/optuna_{study_name}.db"

    study = optuna.create_study(
        study_name=study_name,
        storage=storage,
        direction="maximize",
        load_if_exists=True,
    )

    print(f"Optimizing on rounds {EVAL_ROUNDS}, seeds {EVAL_SEEDS}, {N_RUNS} MC runs per eval")
    print(f"Study: {study_name}, storage: {storage}")
    print(f"Running {n_trials} trials with {n_jobs} parallel workers")
    print()

    study.optimize(objective, n_trials=n_trials, n_jobs=n_jobs, show_progress_bar=True)

    # Print results
    print(f"\nBest trial: score={study.best_trial.value:.1f}")
    print("Best params:")
    for k, v in study.best_trial.params.items():
        print(f"  {k}: {v:.4f}")

    # Save best params
    result = {
        "study_name": study_name,
        "best_score": round(study.best_trial.value, 2),
        "best_params": {k: round(v, 4) for k, v in study.best_trial.params.items()},
        "n_trials": len(study.trials),
        "eval_rounds": EVAL_ROUNDS,
        "eval_seeds": EVAL_SEEDS,
        "n_mc_runs": N_RUNS,
    }
    out_path = EVAL_DIR / f"optuna_{study_name}_best.json"
    out_path.write_text(json.dumps(result, indent=2))
    print(f"\nSaved to {out_path}")

    return study


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--n-trials", type=int, default=200)
    parser.add_argument("--n-jobs", type=int, default=1)
    parser.add_argument("--study-name", type=str, default="sim_v2")
    args = parser.parse_args()

    run_optimization(
        n_trials=args.n_trials,
        n_jobs=args.n_jobs,
        study_name=args.study_name,
    )
