"""Hybrid prediction model for Astar Island.

Combines three signals:
1. Static prior: terrain type + distance-from-settlement + continuous rate model
2. Simulator: v2 Monte Carlo probabilistic state machine
3. Observations: direct viewport samples from API queries

The blend weights are optimized to maximize score.
"""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))
from simulator.sim_v2 import SimParams as SimV2Params, run_monte_carlo

# Prediction classes
NUM_CLASSES = 6
GRID_TO_CLASS = {10: 0, 11: 0, 0: 0, 1: 1, 2: 2, 3: 3, 4: 4, 5: 5}
FLOOR = 0.005

# Linear model coefficients: prior[class] = a * rate + b
# Fitted from R1-R6 ground truth (Q46 + R6 data)
# Format: {bucket: [(a, b) for each of 6 classes]}
RATE_MODEL = {
    "ocean": [(0, 1.0), (0, 0), (0, 0), (0, 0), (0, 0), (0, 0)],
    "mountain": [(0, 0), (0, 0), (0, 0), (0, 0), (0, 0), (0, 1.0)],
    "settlement": [(-1.51, 0.66), (1.93, 0.03), (0.09, 0.0), (0.15, 0.005), (-0.65, 0.30), (0, 0)],
    "forest": [(0.34, 0.03), (0.91, 0.0), (0.07, 0.0), (0.08, 0.001), (-1.40, 0.97), (0, 0)],
    "plains_d0": [(-1.34, 0.94), (1.08, 0.02), (0.06, 0.001), (0.09, 0.003), (0.10, 0.04), (0, 0)],
    "plains_d1": [(-1.28, 1.01), (0.90, -0.01), (0.09, -0.001), (0.09, -0.001), (0.21, 0.001), (0, 0)],
    "plains_d2": [(-0.67, 1.03), (0.47, -0.02), (0.08, -0.004), (0.05, -0.002), (0.07, -0.002), (0, 0)],
    "plains_d3": [(-0.20, 1.01), (0.15, -0.009), (0.03, -0.002), (0.01, -0.001), (0.01, -0.001), (0, 0)],
}

# Best v2 simulator params from Optuna
BEST_SIM_PARAMS = SimV2Params(
    expand_prob=0.10,  # will be overridden by rate mapping
    collapse_base=0.144,
    collapse_forest_bonus=0.019,
    ruin_to_forest=0.077,
    ruin_to_empty=0.255,
    ruin_rebuild=0.067,
    plains_preference=1.09,
    port_chance=0.038,
    expand_range=3,
)

# Rate mapping: expand_prob = slope * observed_rate + intercept
SIM_RATE_SLOPE = 0.485
SIM_RATE_INTERCEPT = 0.053


def build_static_prior(
    grid: list[list[int]],
    settlements: list[dict],
    rate: float,
) -> np.ndarray:
    """Build static prior from terrain type + distance + continuous rate."""
    h, w = len(grid), len(grid[0])
    pred = np.full((h, w, NUM_CLASSES), FLOOR)
    settle_pos = {(s["x"], s["y"]) for s in settlements}

    for y in range(h):
        for x in range(w):
            code = grid[y][x]

            if code == 10:
                bucket = "ocean"
            elif code == 5:
                bucket = "mountain"
            elif code == 4:
                bucket = "forest"
            elif code in (1, 2):
                bucket = "settlement"
            elif code in (0, 11):
                min_d = min(
                    (abs(x - sx) + abs(y - sy) for sx, sy in settle_pos),
                    default=99,
                )
                if min_d <= 2:
                    bucket = "plains_d0"
                elif min_d <= 5:
                    bucket = "plains_d1"
                elif min_d <= 8:
                    bucket = "plains_d2"
                else:
                    bucket = "plains_d3"
            else:
                bucket = "plains_d3"

            coeffs = RATE_MODEL[bucket]
            for c in range(NUM_CLASSES):
                a, b = coeffs[c]
                pred[y, x, c] = max(FLOOR, a * rate + b)

    pred = np.clip(pred, FLOOR, None)
    pred /= pred.sum(axis=-1, keepdims=True)
    return pred


def build_sim_prediction(
    grid: list[list[int]],
    settlements: list[dict],
    rate: float,
    n_runs: int = 200,
) -> np.ndarray:
    """Run v2 simulator Monte Carlo."""
    expand_prob = max(0.001, min(0.30, SIM_RATE_SLOPE * rate + SIM_RATE_INTERCEPT))
    params = SimV2Params(
        expand_prob=expand_prob,
        collapse_base=BEST_SIM_PARAMS.collapse_base,
        collapse_forest_bonus=BEST_SIM_PARAMS.collapse_forest_bonus,
        ruin_to_forest=BEST_SIM_PARAMS.ruin_to_forest,
        ruin_to_empty=BEST_SIM_PARAMS.ruin_to_empty,
        ruin_rebuild=BEST_SIM_PARAMS.ruin_rebuild,
        plains_preference=BEST_SIM_PARAMS.plains_preference,
        port_chance=BEST_SIM_PARAMS.port_chance,
        expand_range=BEST_SIM_PARAMS.expand_range,
    )
    return run_monte_carlo(grid, settlements, params, n_runs=n_runs, floor=FLOOR)


def blend_observations(
    pred: np.ndarray,
    observations: list[dict],
) -> np.ndarray:
    """Blend viewport observations into prediction."""
    h, w, _ = pred.shape
    obs_count = np.zeros((h, w))
    obs_sum = np.zeros((h, w, NUM_CLASSES))

    for obs in observations:
        vp = obs["viewport"]
        sim_grid = obs["grid"]
        vx, vy = vp["x"], vp["y"]
        for dy in range(len(sim_grid)):
            for dx in range(len(sim_grid[0])):
                y, x = vy + dy, vx + dx
                if y >= h or x >= w:
                    continue
                cls = GRID_TO_CLASS.get(sim_grid[dy][dx], 0)
                obs_count[y][x] += 1
                obs_sum[y][x][cls] += 1

    for y in range(h):
        for x in range(w):
            n = obs_count[y][x]
            if n > 0:
                emp = obs_sum[y][x] / n
                emp = np.maximum(emp, FLOOR)
                emp /= emp.sum()
                # Weight: more observations = trust empirical more
                weight = min(n / 5.0, 0.7)
                pred[y][x] = (1 - weight) * pred[y][x] + weight * emp

    pred = np.clip(pred, FLOOR, None)
    pred /= pred.sum(axis=-1, keepdims=True)
    return pred


def compute_observed_rate(observations: list[dict], grid: list[list[int]]) -> float:
    """Compute settlement rate from viewport observations."""
    total = 0
    settle = 0
    for obs in observations:
        vp = obs["viewport"]
        sim_grid = obs["grid"]
        vx, vy = vp["x"], vp["y"]
        h_grid, w_grid = len(grid), len(grid[0])
        for dy in range(len(sim_grid)):
            for dx in range(len(sim_grid[0])):
                y, x = vy + dy, vx + dx
                if y >= h_grid or x >= w_grid:
                    continue
                if grid[y][x] in (10, 5):  # skip ocean/mountain
                    continue
                total += 1
                if sim_grid[dy][dx] in (1, 2):  # settlement or port
                    settle += 1
    return settle / max(total, 1)


def predict(
    grid: list[list[int]],
    settlements: list[dict],
    observations: list[dict],
    sim_weight: float = 0.35,
    n_sim_runs: int = 200,
) -> np.ndarray:
    """Build hybrid prediction.

    1. Compute observed settlement rate from observations
    2. Build static prior using continuous rate model
    3. Run simulator Monte Carlo
    4. Blend: (1-sim_weight) * static + sim_weight * simulator
    5. Blend observations on top

    Returns: H×W×6 probability tensor ready for submission.
    """
    # Step 1: Detect rate from observations
    rate = compute_observed_rate(observations, grid)
    print(f"  Observed settlement rate: {rate:.4f}")

    # Step 2: Static prior
    static = build_static_prior(grid, settlements, rate)

    # Step 3: Simulator
    sim_pred = build_sim_prediction(grid, settlements, rate, n_runs=n_sim_runs)

    # Step 4: Blend static + sim
    pred = (1 - sim_weight) * static + sim_weight * sim_pred

    # Step 5: Blend observations
    if observations:
        pred = blend_observations(pred, observations)

    # Final normalization
    pred = np.clip(pred, FLOOR, None)
    pred /= pred.sum(axis=-1, keepdims=True)
    return pred


if __name__ == "__main__":
    # Evaluate hybrid on all rounds with ground truth
    import store
    from simulator.evaluate import compute_score
    import json

    print("=== Hybrid Model Evaluation ===\n")

    all_scores = []
    results = {}

    for rn in store.list_stored_rounds():
        gt_data = store.load_ground_truth(rn, 0)
        if gt_data is None:
            continue

        round_scores = []
        for si in range(5):
            state = store.load_initial_state(rn, si)
            gt_data = store.load_ground_truth(rn, si)
            if state is None or gt_data is None:
                continue

            gt = np.array(gt_data["ground_truth"])

            # Use ground truth rate as if we had perfect observation
            # (in live rounds, this comes from API queries)
            h, w = len(state["grid"]), len(state["grid"][0])
            dynamic = [
                (y, x)
                for y in range(h)
                for x in range(w)
                if state["grid"][y][x] not in (10, 5)
            ]
            true_rate = np.mean([gt[y][x][1] + gt[y][x][2] for y, x in dynamic])

            # Build prediction using true rate (best case for static prior)
            static = build_static_prior(state["grid"], state["settlements"], true_rate)
            sim = build_sim_prediction(state["grid"], state["settlements"], true_rate, n_runs=100)
            pred = 0.65 * static + 0.35 * sim
            pred = np.clip(pred, FLOOR, None)
            pred /= pred.sum(axis=-1, keepdims=True)

            metrics = compute_score(pred, gt)
            round_scores.append(metrics["score"])
            all_scores.append(metrics["score"])

        avg = np.mean(round_scores) if round_scores else 0
        results[f"round_{rn}"] = round(avg, 1)
        print(f"R{rn}: mean={avg:.1f}, seeds={[round(s, 1) for s in round_scores]}")

    print(f"\nOverall mean: {np.mean(all_scores):.1f}")

    store.EVAL_DIR.mkdir(parents=True, exist_ok=True)
    (store.EVAL_DIR / "hybrid_eval.json").write_text(
        json.dumps({"results": results, "mean_score": round(np.mean(all_scores), 1)}, indent=2)
    )
