"""Shared test fixtures for Astar Island tests."""

import numpy as np
import pytest

from astar.types import (
    MapState, Observation, RoundStats, Prediction,
    OCEAN, PLAINS, FOREST, MOUNTAIN, SETTLEMENT, PORT, RUIN, EMPTY,
)


@pytest.fixture
def simple_map_state() -> MapState:
    """A minimal 10x10 map with known terrain layout.

    Layout:
        Row 0: all ocean (border)
        Row 1-8: mix of plains, forest, mountain
        Row 9: all ocean (border)
        Col 0, 9: all ocean (border)

    Settlements at (3, 3) and (6, 6), port at (1, 5).
    """
    grid = np.full((10, 10), PLAINS, dtype=int)
    # Ocean border
    grid[0, :] = OCEAN
    grid[9, :] = OCEAN
    grid[:, 0] = OCEAN
    grid[:, 9] = OCEAN
    # Some terrain
    grid[2, 2] = FOREST
    grid[2, 3] = FOREST
    grid[3, 2] = FOREST
    grid[5, 5] = MOUNTAIN
    grid[7, 7] = MOUNTAIN

    settlements = [
        {"x": 3, "y": 3, "has_port": False, "alive": True},
        {"x": 6, "y": 6, "has_port": False, "alive": True},
        {"x": 1, "y": 5, "has_port": True, "alive": True},
    ]
    return MapState(grid=grid, settlements=settlements)


@pytest.fixture
def simple_ground_truth() -> np.ndarray:
    """A 10x10x6 ground truth matching simple_map_state.

    Static cells get deterministic distributions.
    Dynamic cells get mixed distributions.
    """
    gt = np.zeros((10, 10, 6), dtype=np.float32)

    for r in range(10):
        for c in range(10):
            if r == 0 or r == 9 or c == 0 or c == 9:
                gt[r, c, 0] = 1.0  # ocean → empty
            else:
                gt[r, c, 0] = 0.7  # mostly empty
                gt[r, c, 1] = 0.15  # some settlement
                gt[r, c, 3] = 0.05  # some ruin
                gt[r, c, 4] = 0.10  # some forest

    # Mountain cells are static
    gt[5, 5] = [0, 0, 0, 0, 0, 1]
    gt[7, 7] = [0, 0, 0, 0, 0, 1]

    # Settlement cell: more likely to stay settlement
    gt[3, 3] = [0.1, 0.6, 0.0, 0.2, 0.1, 0.0]
    gt[6, 6] = [0.1, 0.5, 0.0, 0.3, 0.1, 0.0]
    gt[5, 1] = [0.1, 0.3, 0.3, 0.1, 0.2, 0.0]  # port cell

    return gt


@pytest.fixture
def sample_round_stats() -> RoundStats:
    return RoundStats(
        ruin_rate=0.02,
        settlement_rate=0.15,
        port_rate=0.01,
        expansion_distance=2.5,
        forest_rate=0.20,
        empty_rate=0.60,
        settlement_to_ruin_ratio=0.88,
    )
