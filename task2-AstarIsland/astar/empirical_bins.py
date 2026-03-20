"""Empirical bin predictor: use live observations to build per-bin distributions.

For each observation, categorize cells by features (distance to settlement,
coastal/inland, terrain type, settlement density, map size) and count outcome
frequencies. This produces empirical distributions calibrated to the current
round's hidden parameters.
"""

import numpy as np
from collections import defaultdict

from .types import (
    MapState, Observation, Prediction, NUM_CLASSES,
    TERRAIN_TO_CLASS, CLASS_EMPTY, CLASS_MOUNTAIN, OCEAN, MOUNTAIN,
)
from .features import compute_features, FEATURE_NAMES

PROB_FLOOR = 0.01

# Feature indices
_DIST_IDX = FEATURE_NAMES.index("dist_nearest_settlement")
_COASTAL_IDX = FEATURE_NAMES.index("adjacent_ocean")
_FOREST_IDX = FEATURE_NAMES.index("is_forest")
_MOUNTAIN_IDX = FEATURE_NAMES.index("is_mountain")
_OCEAN_IDX = FEATURE_NAMES.index("is_ocean")
_SETTLEMENT_IDX = FEATURE_NAMES.index("is_initial_settlement")
_SETTLE_R5_IDX = FEATURE_NAMES.index("settlements_r5")
_TOTAL_IDX = FEATURE_NAMES.index("total_settlements")

# Distance bins
DIST_BINS = [(0, 0.5), (0.5, 1.5), (1.5, 2.5), (2.5, 4.5), (4.5, 7.5), (7.5, 99)]
DIST_LABELS = ["d0", "d1", "d2", "d3-4", "d5-7", "d8+"]

MIN_BIN_COUNT = 10


def _dist_label(dist: float) -> str:
    for (lo, hi), label in zip(DIST_BINS, DIST_LABELS):
        if lo <= dist < hi:
            return label
    return DIST_LABELS[-1]


def _cell_bin_key(features: np.ndarray) -> str | None:
    """Fine bin key: distance × coastal × terrain × 3-level density × total settlements."""
    if features[_OCEAN_IDX] > 0.5 or features[_MOUNTAIN_IDX] > 0.5:
        return None

    dist_label = _dist_label(features[_DIST_IDX])
    coastal = "coast" if features[_COASTAL_IDX] > 0.5 else "inland"
    is_forest = features[_FOREST_IDX] > 0.5
    is_settlement = features[_SETTLEMENT_IDX] > 0.5
    terrain = "forest" if is_forest else ("settle" if is_settlement else "plain")

    sr5 = features[_SETTLE_R5_IDX]
    density = "hi" if sr5 >= 4 else ("mid" if sr5 >= 2 else "lo")

    total = "Thi" if features[_TOTAL_IDX] >= 40 else "Tlo"

    return f"{dist_label}_{coastal}_{terrain}_{density}_{total}"


def _cell_bin_key_coarse(features: np.ndarray) -> str | None:
    """Coarse fallback: distance × coastal × terrain × binary density."""
    if features[_OCEAN_IDX] > 0.5 or features[_MOUNTAIN_IDX] > 0.5:
        return None

    dist_label = _dist_label(features[_DIST_IDX])
    coastal = "coast" if features[_COASTAL_IDX] > 0.5 else "inland"
    is_forest = features[_FOREST_IDX] > 0.5
    is_settlement = features[_SETTLEMENT_IDX] > 0.5
    terrain = "forest" if is_forest else ("settle" if is_settlement else "plain")

    density = "hi" if features[_SETTLE_R5_IDX] >= 3 else "lo"

    return f"C_{dist_label}_{coastal}_{terrain}_{density}"


def build_empirical_distributions(
    observations: list[Observation],
    states: list[MapState],
) -> dict[str, np.ndarray]:
    """Build per-bin empirical distributions from live observations.

    Args:
        observations: All observations across all seeds for this round.
        states: Initial map states (one per seed, indexed by Observation.seed_index).

    Returns:
        Dict mapping bin_key -> (NUM_CLASSES,) probability distribution.
    """
    feature_maps = {}
    for obs in observations:
        si = obs.seed_index
        if si not in feature_maps:
            feature_maps[si] = compute_features(states[si])

    bin_counts = defaultdict(lambda: np.zeros(NUM_CLASSES, dtype=np.float64))

    for obs in observations:
        si = obs.seed_index
        feat_map = feature_maps[si]
        vx, vy, vw, vh = obs.viewport

        for r in range(vh):
            for c in range(vw):
                abs_y, abs_x = vy + r, vx + c
                if abs_y >= 40 or abs_x >= 40:
                    continue

                cell_feats = feat_map[abs_y, abs_x]
                terrain_code = int(obs.grid[r, c])
                cls = TERRAIN_TO_CLASS.get(terrain_code, CLASS_EMPTY)

                fine_key = _cell_bin_key(cell_feats)
                if fine_key is not None:
                    bin_counts[fine_key][cls] += 1

                coarse_key = _cell_bin_key_coarse(cell_feats)
                if coarse_key is not None:
                    bin_counts[coarse_key][cls] += 1

    bin_distributions = {}
    for key, counts in bin_counts.items():
        total = counts.sum()
        if total >= MIN_BIN_COUNT:
            dist = counts / total
            dist = np.maximum(dist, PROB_FLOOR)
            dist = dist / dist.sum()
            bin_distributions[key] = dist.astype(np.float32)

    return bin_distributions


def predict_with_empirical_bins(
    state: MapState,
    bin_distributions: dict[str, np.ndarray],
    model_prediction: Prediction,
    bin_counts: dict[str, int],
    k: float = 150,
) -> Prediction:
    """Blend model predictions with empirical bin distributions.

    Uses adaptive weighting: bins with more observations get higher weight.
    Weight = n / (n + k), where n = observation count for the bin.

    Args:
        state: Initial map state.
        bin_distributions: From build_empirical_distributions().
        model_prediction: Base model prediction.
        bin_counts: Observation count per bin key (from get_bin_coverage_stats).
        k: Inflection point for adaptive weight. At n=k, weight=0.5.

    Returns:
        Blended prediction.
    """
    features = compute_features(state)
    h, w = state.grid.shape
    probs = model_prediction.probs.copy()

    for r in range(h):
        for c in range(w):
            if state.grid[r, c] in (OCEAN, MOUNTAIN):
                continue

            # Try fine bin first, fall back to coarse
            bin_key = _cell_bin_key(features[r, c])
            if bin_key is None or bin_key not in bin_distributions:
                bin_key = _cell_bin_key_coarse(features[r, c])
            if bin_key is not None and bin_key in bin_distributions:
                empirical = bin_distributions[bin_key]
                n = bin_counts.get(bin_key, 0)
                weight = n / (n + k)
                probs[r, c] = weight * empirical + (1 - weight) * probs[r, c]

    # Re-floor and normalize
    probs = np.maximum(probs, PROB_FLOOR)
    probs = probs / probs.sum(axis=-1, keepdims=True)

    return Prediction(probs=probs)


def get_bin_coverage_stats(
    observations: list[Observation],
    states: list[MapState],
) -> dict[str, int]:
    """Report how many observations each bin has. For diagnostics."""
    feature_maps = {}
    for obs in observations:
        si = obs.seed_index
        if si not in feature_maps:
            feature_maps[si] = compute_features(states[si])

    bin_counts = defaultdict(int)
    for obs in observations:
        si = obs.seed_index
        feat_map = feature_maps[si]
        vx, vy, vw, vh = obs.viewport

        for r in range(vh):
            for c in range(vw):
                abs_y, abs_x = vy + r, vx + c
                if abs_y >= 40 or abs_x >= 40:
                    continue
                cell_feats = feat_map[abs_y, abs_x]
                # Count for both fine and coarse (matches build_empirical_distributions)
                fine_key = _cell_bin_key(cell_feats)
                if fine_key is not None:
                    bin_counts[fine_key] += 1
                coarse_key = _cell_bin_key_coarse(cell_feats)
                if coarse_key is not None:
                    bin_counts[coarse_key] += 1

    return dict(bin_counts)
