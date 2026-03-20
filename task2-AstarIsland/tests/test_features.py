"""Tests for astar/features.py — feature extraction."""

import numpy as np

from astar.features import compute_features, FEATURE_NAMES, NUM_FEATURES
from astar.types import MapState, OCEAN, PLAINS, FOREST, MOUNTAIN


def test_output_shape(simple_map_state):
    feats = compute_features(simple_map_state)
    assert feats.shape == (10, 10, NUM_FEATURES)


def test_feature_count_matches_names():
    assert len(FEATURE_NAMES) == NUM_FEATURES


def test_ocean_cell_features(simple_map_state):
    """Ocean cells should have is_ocean=1, is_land=0, reachable=0."""
    feats = compute_features(simple_map_state)
    ocean_feats = feats[0, 0]
    idx = {name: i for i, name in enumerate(FEATURE_NAMES)}

    assert ocean_feats[idx["is_ocean"]] == 1.0
    assert ocean_feats[idx["is_land"]] == 0.0
    assert ocean_feats[idx["reachable"]] == 0.0


def test_mountain_cell_features(simple_map_state):
    """Mountain cells should have is_mountain=1, is_land=0."""
    feats = compute_features(simple_map_state)
    # Mountain at (5, 5)
    mtn_feats = feats[5, 5]
    idx = {name: i for i, name in enumerate(FEATURE_NAMES)}

    assert mtn_feats[idx["is_mountain"]] == 1.0
    assert mtn_feats[idx["is_land"]] == 0.0


def test_settlement_cell_features(simple_map_state):
    """Settlement at (3, 3) should have is_initial_settlement=1, dist=0."""
    feats = compute_features(simple_map_state)
    # Settlement at x=3, y=3 → grid[3, 3]
    s_feats = feats[3, 3]
    idx = {name: i for i, name in enumerate(FEATURE_NAMES)}

    assert s_feats[idx["is_initial_settlement"]] == 1.0
    assert s_feats[idx["dist_nearest_settlement"]] == 0.0
    assert s_feats[idx["reachable"]] == 1.0


def test_port_cell_features(simple_map_state):
    """Port at (1, 5) should have is_initial_port=1."""
    feats = compute_features(simple_map_state)
    # Port at x=1, y=5 → grid[5, 1]
    p_feats = feats[5, 1]
    idx = {name: i for i, name in enumerate(FEATURE_NAMES)}

    assert p_feats[idx["is_initial_port"]] == 1.0
    assert p_feats[idx["is_initial_settlement"]] == 1.0


def test_forest_adjacent_count(simple_map_state):
    """Cell (3, 3) has forests at (2,2), (2,3), (3,2) — 3 adjacent forests."""
    feats = compute_features(simple_map_state)
    idx = {name: i for i, name in enumerate(FEATURE_NAMES)}
    assert feats[3, 3, idx["adjacent_forests"]] == 3.0


def test_coastal_cell(simple_map_state):
    """Cell (1, 1) is adjacent to ocean at (0,1) and (1,0) — should have adjacent_ocean >= 2."""
    feats = compute_features(simple_map_state)
    idx = {name: i for i, name in enumerate(FEATURE_NAMES)}
    assert feats[1, 1, idx["adjacent_ocean"]] >= 2.0


def test_distance_increases_with_position(simple_map_state):
    """Cells further from settlements should have higher dist_nearest_settlement."""
    feats = compute_features(simple_map_state)
    idx = {name: i for i, name in enumerate(FEATURE_NAMES)}
    dist_at_settlement = feats[3, 3, idx["dist_nearest_settlement"]]
    dist_far = feats[1, 8, idx["dist_nearest_settlement"]]
    assert dist_at_settlement < dist_far


def test_reachability_excludes_ocean(simple_map_state):
    """Ocean cells should not be reachable."""
    feats = compute_features(simple_map_state)
    idx = {name: i for i, name in enumerate(FEATURE_NAMES)}
    for c in range(10):
        assert feats[0, c, idx["reachable"]] == 0.0  # top ocean row


def test_settlements_within_radius(simple_map_state):
    """Cell (3, 3) should count itself in radius-3 settlements."""
    feats = compute_features(simple_map_state)
    idx = {name: i for i, name in enumerate(FEATURE_NAMES)}
    assert feats[3, 3, idx["settlements_r3"]] >= 1.0


def test_all_features_finite(simple_map_state):
    """No NaN or Inf in features."""
    feats = compute_features(simple_map_state)
    assert np.all(np.isfinite(feats))
