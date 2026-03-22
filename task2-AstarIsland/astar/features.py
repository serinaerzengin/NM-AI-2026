from collections import deque

import numpy as np
from scipy.ndimage import distance_transform_edt

from .types import MapState, OCEAN, MOUNTAIN, FOREST, SETTLEMENT, PORT


def compute_features(state: MapState) -> np.ndarray:
    """Extract per-cell features from initial map state.

    Returns (40, 40, N_FEATURES) float array.
    Feature order: see FEATURE_NAMES.
    """
    grid = state.grid
    h, w = grid.shape

    settlement_mask = np.zeros((h, w), dtype=bool)
    port_mask = np.zeros((h, w), dtype=bool)
    for s in state.settlements:
        settlement_mask[s["y"], s["x"]] = True
        if s.get("has_port", False):
            port_mask[s["y"], s["x"]] = True

    ocean_mask = grid == OCEAN
    mountain_mask = grid == MOUNTAIN
    forest_mask = grid == FOREST
    land_mask = ~ocean_mask & ~mountain_mask

    # Distance to nearest settlement (Euclidean)
    if settlement_mask.any():
        dist_settlement = distance_transform_edt(~settlement_mask)
    else:
        dist_settlement = np.full((h, w), 99.0)

    # Settlement counts within radii
    settlement_coords = np.argwhere(settlement_mask)  # (N, 2) as (row, col)
    settlements_r3 = _count_within_radius(settlement_coords, h, w, 3)
    settlements_r5 = _count_within_radius(settlement_coords, h, w, 5)
    settlements_r10 = _count_within_radius(settlement_coords, h, w, 10)

    # 8-neighborhood terrain counts
    adjacent_forests = _neighbor_count(forest_mask)
    adjacent_ocean = _neighbor_count(ocean_mask)
    adjacent_mountains = _neighbor_count(mountain_mask)

    # Reachability from any settlement via land (BFS)
    reachable = _compute_reachability(land_mask, settlement_mask)

    # Distance to nearest ocean (for port prediction)
    if ocean_mask.any():
        dist_ocean = distance_transform_edt(~ocean_mask)
    else:
        dist_ocean = np.full((h, w), 99.0)

    # Distance to nearest forest (food access)
    if forest_mask.any():
        dist_forest = distance_transform_edt(~forest_mask)
    else:
        dist_forest = np.full((h, w), 99.0)

    # Broader terrain composition in radius 5 (convolution-based)
    forests_r5 = _count_terrain_in_radius(forest_mask, 5)
    ocean_r5 = _count_terrain_in_radius(ocean_mask, 5)
    land_r5 = _count_terrain_in_radius(land_mask, 5)

    # Global map features (same for every cell, helps model learn map context)
    total_settlements = float(len(state.settlements))
    total_ports = float(sum(1 for s in state.settlements if s.get("has_port", False)))
    land_fraction = float(land_mask.sum()) / (h * w)

    features = np.stack([
        (grid == OCEAN).astype(np.float32),
        (grid == MOUNTAIN).astype(np.float32),
        (grid == FOREST).astype(np.float32),
        land_mask.astype(np.float32),
        settlement_mask.astype(np.float32),
        port_mask.astype(np.float32),
        dist_settlement.astype(np.float32),
        settlements_r3.astype(np.float32),
        settlements_r5.astype(np.float32),
        settlements_r10.astype(np.float32),
        adjacent_forests.astype(np.float32),
        adjacent_ocean.astype(np.float32),
        adjacent_mountains.astype(np.float32),
        reachable.astype(np.float32),
        dist_ocean.astype(np.float32),
        dist_forest.astype(np.float32),
        forests_r5.astype(np.float32),
        ocean_r5.astype(np.float32),
        land_r5.astype(np.float32),
        np.full((h, w), total_settlements, dtype=np.float32),
        np.full((h, w), total_ports, dtype=np.float32),
        np.full((h, w), land_fraction, dtype=np.float32),
    ], axis=-1)

    return features


FEATURE_NAMES = [
    "is_ocean",
    "is_mountain",
    "is_forest",
    "is_land",
    "is_initial_settlement",
    "is_initial_port",
    "dist_nearest_settlement",
    "settlements_r3",
    "settlements_r5",
    "settlements_r10",
    "adjacent_forests",
    "adjacent_ocean",
    "adjacent_mountains",
    "reachable",
    "dist_ocean",
    "dist_forest",
    "forests_r5",
    "ocean_r5",
    "land_r5",
    "total_settlements",
    "total_ports",
    "land_fraction",
]

NUM_FEATURES = len(FEATURE_NAMES)


def _count_within_radius(coords: np.ndarray, h: int, w: int, radius: float) -> np.ndarray:
    """Count how many points in `coords` are within `radius` of each cell."""
    counts = np.zeros((h, w), dtype=np.float32)
    if len(coords) == 0:
        return counts
    for r in range(h):
        for c in range(w):
            dists = np.sqrt((coords[:, 0] - r) ** 2 + (coords[:, 1] - c) ** 2)
            counts[r, c] = np.sum(dists <= radius)
    return counts


def _neighbor_count(mask: np.ndarray) -> np.ndarray:
    """Count True neighbors in 8-connectivity for each cell."""
    h, w = mask.shape
    padded = np.pad(mask.astype(np.float32), 1, mode="constant", constant_values=0)
    count = np.zeros((h, w), dtype=np.float32)
    for dr in [-1, 0, 1]:
        for dc in [-1, 0, 1]:
            if dr == 0 and dc == 0:
                continue
            count += padded[1 + dr: h + 1 + dr, 1 + dc: w + 1 + dc]
    return count


def _count_terrain_in_radius(mask: np.ndarray, radius: int) -> np.ndarray:
    """Count True cells within a square radius using cumulative sums (fast)."""
    from scipy.ndimage import uniform_filter
    float_mask = mask.astype(np.float64)
    size = 2 * radius + 1
    # uniform_filter gives the mean; multiply by area to get count
    filtered = uniform_filter(float_mask, size=size, mode="constant", cval=0.0)
    return (filtered * size * size).astype(np.float32)


def _compute_reachability(land_mask: np.ndarray, settlement_mask: np.ndarray) -> np.ndarray:
    """BFS from all settlements over land cells. Returns bool mask of reachable cells."""
    h, w = land_mask.shape
    reachable = np.zeros((h, w), dtype=bool)
    queue = deque()

    for r in range(h):
        for c in range(w):
            if settlement_mask[r, c]:
                reachable[r, c] = True
                queue.append((r, c))

    while queue:
        r, c = queue.popleft()
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr, nc = r + dr, c + dc
            if 0 <= nr < h and 0 <= nc < w and land_mask[nr, nc] and not reachable[nr, nc]:
                reachable[nr, nc] = True
                queue.append((nr, nc))

    return reachable
