"""Tests for astar/calibration.py — round statistics computation."""

import numpy as np

from astar.calibration import (
    compute_round_stats_from_ground_truth,
    compute_round_stats_from_observations,
    round_stats_to_array,
)
from astar.types import (
    MapState, Observation, RoundStats,
    OCEAN, PLAINS, MOUNTAIN, SETTLEMENT, RUIN, PORT,
    CLASS_EMPTY, CLASS_SETTLEMENT, CLASS_PORT, CLASS_RUIN, CLASS_MOUNTAIN,
)


def test_round_stats_from_ground_truth(simple_map_state, simple_ground_truth):
    stats = compute_round_stats_from_ground_truth(simple_ground_truth, simple_map_state)
    assert isinstance(stats, RoundStats)
    assert stats.ruin_rate >= 0
    assert stats.settlement_rate >= 0
    assert stats.port_rate >= 0
    assert stats.expansion_distance >= 0


def test_round_stats_settlement_rate_positive(simple_map_state, simple_ground_truth):
    """Ground truth has settlement probability > 0 for dynamic cells."""
    stats = compute_round_stats_from_ground_truth(simple_ground_truth, simple_map_state)
    assert stats.settlement_rate > 0


def test_round_stats_to_array(sample_round_stats):
    arr = round_stats_to_array(sample_round_stats)
    assert arr.shape == (7,)
    assert arr[0] == sample_round_stats.ruin_rate
    assert arr[1] == sample_round_stats.settlement_rate
    assert arr[2] == sample_round_stats.port_rate
    assert arr[3] == sample_round_stats.expansion_distance
    assert arr[4] == sample_round_stats.forest_rate
    assert arr[5] == sample_round_stats.empty_rate
    assert arr[6] == sample_round_stats.settlement_to_ruin_ratio


def test_round_stats_from_observations_empty():
    """No observations → zero stats."""
    grid = np.full((10, 10), PLAINS, dtype=int)
    grid[0, :] = OCEAN
    state = MapState(grid=grid, settlements=[])
    stats = compute_round_stats_from_observations([], state)
    assert stats.ruin_rate == 0.0
    assert stats.settlement_rate == 0.0


def test_round_stats_from_observations_with_data():
    """Observations with known terrain should produce expected stats."""
    grid = np.full((10, 10), PLAINS, dtype=int)
    state = MapState(
        grid=grid,
        settlements=[{"x": 2, "y": 2, "has_port": False, "alive": True}],
    )

    # Create an observation: 5x5 viewport with mix of terrain
    obs_grid = np.full((5, 5), 11, dtype=int)  # plains (class 0)
    obs_grid[1, 1] = SETTLEMENT
    obs_grid[2, 2] = RUIN
    obs_grid[3, 3] = SETTLEMENT

    obs = Observation(
        grid=obs_grid,
        settlements=[],
        viewport=(0, 0, 5, 5),
        seed_index=0,
    )

    stats = compute_round_stats_from_observations([obs], state)
    assert stats.settlement_rate > 0
    assert stats.ruin_rate > 0


def test_all_static_map_returns_zero_stats():
    """A map with only ocean should return zero stats."""
    grid = np.full((5, 5), OCEAN, dtype=int)
    gt = np.zeros((5, 5, 6), dtype=np.float32)
    gt[:, :, CLASS_EMPTY] = 1.0
    state = MapState(grid=grid, settlements=[])
    stats = compute_round_stats_from_ground_truth(gt, state)
    assert stats.ruin_rate == 0.0
    assert stats.settlement_rate == 0.0
