"""Tests for astar/query_strategy.py — viewport placement."""

import numpy as np

from astar.query_strategy import (
    plan_viewports, allocate_queries, _compute_interest_map,
    VIEWPORT_SIZE, MAP_SIZE, MIN_QUERIES_PER_MAP,
)
from astar.types import MapState, OCEAN, PLAINS, MOUNTAIN


def test_plan_viewports_returns_correct_count(simple_map_state):
    viewports = plan_viewports(simple_map_state, n_queries=3)
    assert len(viewports) == 3


def test_viewport_positions_within_bounds(simple_map_state):
    viewports = plan_viewports(simple_map_state, n_queries=3)
    h, w = simple_map_state.grid.shape
    for vx, vy in viewports:
        assert 0 <= vx <= w - VIEWPORT_SIZE or w < VIEWPORT_SIZE
        assert 0 <= vy <= h - VIEWPORT_SIZE or h < VIEWPORT_SIZE


def test_interest_map_zero_for_ocean():
    grid = np.full((10, 10), OCEAN, dtype=int)
    state = MapState(grid=grid, settlements=[])
    interest = _compute_interest_map(state)
    assert interest.sum() == 0


def test_interest_map_peaks_near_settlements():
    grid = np.full((40, 40), PLAINS, dtype=int)
    grid[0, :] = OCEAN
    grid[39, :] = OCEAN
    grid[:, 0] = OCEAN
    grid[:, 39] = OCEAN
    state = MapState(
        grid=grid,
        settlements=[{"x": 20, "y": 20, "has_port": False, "alive": True}],
    )
    interest = _compute_interest_map(state)
    # Cell at settlement position should have highest interest
    assert interest[20, 20] > interest[1, 1]


def test_allocate_queries_sums_to_total():
    states = []
    for _ in range(5):
        grid = np.full((40, 40), PLAINS, dtype=int)
        grid[0, :] = OCEAN
        n_settlements = np.random.randint(5, 20)
        settlements = [
            {"x": np.random.randint(1, 39), "y": np.random.randint(1, 39),
             "has_port": False, "alive": True}
            for _ in range(n_settlements)
        ]
        states.append(MapState(grid=grid, settlements=settlements))

    allocation = allocate_queries(states, total_queries=50)
    assert sum(allocation) == 50
    assert len(allocation) == 5


def test_allocate_queries_respects_minimum():
    states = []
    # One map with many settlements, four with very few
    for i in range(5):
        grid = np.full((40, 40), PLAINS, dtype=int)
        grid[0, :] = OCEAN
        n = 30 if i == 0 else 1
        settlements = [
            {"x": np.random.randint(1, 39), "y": np.random.randint(1, 39),
             "has_port": False, "alive": True}
            for _ in range(n)
        ]
        states.append(MapState(grid=grid, settlements=settlements))

    allocation = allocate_queries(states, total_queries=50)
    for alloc in allocation:
        assert alloc >= MIN_QUERIES_PER_MAP


def test_allocate_queries_gives_more_to_dynamic_maps():
    """Map with more settlements should get more queries."""
    grid = np.full((40, 40), PLAINS, dtype=int)
    grid[0, :] = OCEAN

    # Map 0: lots of settlements
    big_settlements = [
        {"x": x, "y": y, "has_port": False, "alive": True}
        for x in range(5, 35, 3) for y in range(5, 35, 3)
    ]
    # Map 1: few settlements
    small_settlements = [
        {"x": 20, "y": 20, "has_port": False, "alive": True}
    ]

    states = [
        MapState(grid=grid.copy(), settlements=big_settlements),
        MapState(grid=grid.copy(), settlements=small_settlements),
    ]

    allocation = allocate_queries(states, total_queries=20)
    assert allocation[0] > allocation[1]
