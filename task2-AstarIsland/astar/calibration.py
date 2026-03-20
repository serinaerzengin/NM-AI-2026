import numpy as np

from .types import (
    MapState, Observation, RoundStats,
    CLASS_SETTLEMENT, CLASS_PORT, CLASS_RUIN, CLASS_EMPTY, CLASS_FOREST, CLASS_MOUNTAIN,
    TERRAIN_TO_CLASS, NUM_CLASSES,
)


def compute_round_stats_from_ground_truth(
    ground_truth: np.ndarray, state: MapState
) -> RoundStats:
    """Compute round-level statistics from a full ground truth tensor.

    Args:
        ground_truth: (40, 40, 6) probability distributions.
        state: Initial map state with settlement positions.
    """
    dynamic_mask = _dynamic_cell_mask(ground_truth)
    if not dynamic_mask.any():
        return RoundStats(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)

    # Average class probabilities across dynamic cells
    dynamic_probs = ground_truth[dynamic_mask]  # (N, 6)
    mean_probs = dynamic_probs.mean(axis=0)

    settlement_rate = mean_probs[CLASS_SETTLEMENT]
    port_rate = mean_probs[CLASS_PORT]
    ruin_rate = mean_probs[CLASS_RUIN]
    forest_rate = mean_probs[CLASS_FOREST]
    empty_rate = mean_probs[CLASS_EMPTY]

    sr_total = settlement_rate + ruin_rate
    settlement_to_ruin_ratio = settlement_rate / sr_total if sr_total > 1e-6 else 0.5

    # Expansion distance: weighted avg distance of settlement probability from initial positions
    expansion_distance = _compute_expansion_distance(
        ground_truth[:, :, CLASS_SETTLEMENT], state
    )

    return RoundStats(
        ruin_rate=float(ruin_rate),
        settlement_rate=float(settlement_rate),
        port_rate=float(port_rate),
        expansion_distance=float(expansion_distance),
        forest_rate=float(forest_rate),
        empty_rate=float(empty_rate),
        settlement_to_ruin_ratio=float(settlement_to_ruin_ratio),
    )


def compute_round_stats_from_observations(
    observations: list[Observation], state: MapState
) -> RoundStats:
    """Compute round-level statistics from viewport observations.

    Converts observed terrain codes to class counts to estimate the same
    statistics we compute from ground truth during training.
    """
    if not observations:
        return RoundStats(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)

    # Accumulate class counts from all observed cells
    class_counts = np.zeros(NUM_CLASSES, dtype=np.float64)
    total_dynamic = 0

    initial_settlement_set = {
        (s["x"], s["y"]) for s in state.settlements
    }

    expansion_distances = []

    for obs in observations:
        vx, vy, vw, vh = obs.viewport
        for r in range(vh):
            for c in range(vw):
                terrain_code = int(obs.grid[r, c])
                cls = TERRAIN_TO_CLASS.get(terrain_code, CLASS_EMPTY)
                # Skip static cells
                if cls == CLASS_MOUNTAIN:
                    continue
                abs_x, abs_y = vx + c, vy + r
                initial_cls = TERRAIN_TO_CLASS.get(int(state.grid[abs_y, abs_x]), CLASS_EMPTY)
                if initial_cls == CLASS_MOUNTAIN:
                    continue

                class_counts[cls] += 1
                if cls in (CLASS_SETTLEMENT, CLASS_PORT, CLASS_RUIN):
                    total_dynamic += 1

                # Track expansion distance for settlements
                if cls == CLASS_SETTLEMENT:
                    min_dist = _min_dist_to_settlements(abs_x, abs_y, initial_settlement_set)
                    expansion_distances.append(min_dist)

    total = class_counts.sum()
    if total == 0:
        return RoundStats(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)

    settle = class_counts[CLASS_SETTLEMENT] / total
    ruin = class_counts[CLASS_RUIN] / total
    sr_total = settle + ruin
    return RoundStats(
        ruin_rate=float(ruin),
        settlement_rate=float(settle),
        port_rate=float(class_counts[CLASS_PORT] / total),
        expansion_distance=float(np.mean(expansion_distances)) if expansion_distances else 0.0,
        forest_rate=float(class_counts[CLASS_FOREST] / total),
        empty_rate=float(class_counts[CLASS_EMPTY] / total),
        settlement_to_ruin_ratio=float(settle / sr_total) if sr_total > 1e-6 else 0.5,
    )


def round_stats_to_array(stats: RoundStats) -> np.ndarray:
    """Convert RoundStats to a flat feature array for model input."""
    return np.array([
        stats.ruin_rate,
        stats.settlement_rate,
        stats.port_rate,
        stats.expansion_distance,
        stats.forest_rate,
        stats.empty_rate,
        stats.settlement_to_ruin_ratio,
    ], dtype=np.float32)


def _dynamic_cell_mask(ground_truth: np.ndarray) -> np.ndarray:
    """Identify cells that aren't trivially static (entropy > 0.05)."""
    eps = 1e-12
    entropy = -np.sum(ground_truth * np.log(ground_truth + eps), axis=-1)
    return entropy > 0.05


def _compute_expansion_distance(
    settlement_probs: np.ndarray, state: MapState
) -> float:
    """Avg distance of settlement probability mass from initial settlement positions."""
    h, w = settlement_probs.shape
    initial_set = {(s["x"], s["y"]) for s in state.settlements}

    if not initial_set:
        return 0.0

    total_weight = 0.0
    weighted_dist = 0.0

    for r in range(h):
        for c in range(w):
            p = settlement_probs[r, c]
            if p < 0.01:
                continue
            min_dist = _min_dist_to_settlements(c, r, initial_set)
            weighted_dist += p * min_dist
            total_weight += p

    return weighted_dist / total_weight if total_weight > 0 else 0.0


def _min_dist_to_settlements(x: int, y: int, settlement_set: set) -> float:
    """Euclidean distance from (x, y) to nearest settlement in the set."""
    if not settlement_set:
        return 99.0
    return min(
        np.sqrt((x - sx) ** 2 + (y - sy) ** 2)
        for sx, sy in settlement_set
    )
