"""Tests for astar/settlement_features.py."""

import numpy as np

from astar.settlement_features import (
    compute_settlement_cell_features,
    compute_settlement_round_stats,
    collect_all_settlements,
    NUM_SETTLEMENT_CELL_FEATURES,
    NUM_SETTLEMENT_ROUND_FEATURES,
)


def _make_settlement(x, y, population=1.0, food=0.5, wealth=0.1,
                     defense=0.5, alive=True, has_port=False, owner_id=0):
    return {
        "x": x, "y": y, "population": population, "food": food,
        "wealth": wealth, "defense": defense, "alive": alive,
        "has_port": has_port, "owner_id": owner_id,
    }


# --- compute_settlement_cell_features ---

def test_cell_features_shape():
    settlements = [_make_settlement(5, 5)]
    feats = compute_settlement_cell_features(5, 5, settlements)
    assert feats.shape == (NUM_SETTLEMENT_CELL_FEATURES,)


def test_cell_features_empty_settlements():
    feats = compute_settlement_cell_features(5, 5, [])
    assert feats.shape == (NUM_SETTLEMENT_CELL_FEATURES,)
    assert np.all(feats == 0.0)


def test_nearest_settlement_on_cell():
    """Settlement at same position → distance 0, stats match."""
    s = _make_settlement(10, 10, population=3.0, food=0.8, defense=0.9, wealth=0.5)
    feats = compute_settlement_cell_features(10, 10, [s])
    assert feats[0] == 3.0   # nearest_obs_population
    assert feats[1] == 0.8   # nearest_obs_food
    assert feats[3] == 0.9   # nearest_obs_defense
    assert feats[5] == 0.0   # nearest_obs_dist


def test_nearest_distance_computed_correctly():
    s1 = _make_settlement(0, 0)
    s2 = _make_settlement(3, 4)  # dist from (0,0) = 5.0
    feats = compute_settlement_cell_features(0, 0, [s1, s2])
    assert feats[5] == 0.0  # nearest is s1 at distance 0


def test_neighborhood_counts():
    """Settlements within radius 5 should be counted."""
    settlements = [
        _make_settlement(5, 5, food=0.3, owner_id=1),
        _make_settlement(7, 7, food=0.7, owner_id=2),  # dist ~2.8 from (5,5)
        _make_settlement(20, 20, food=0.9, owner_id=3),  # far away
    ]
    feats = compute_settlement_cell_features(5, 5, settlements)
    assert feats[10] == 2.0  # neighborhood_n_settlements (2 within radius 5)
    assert feats[9] == 2.0   # neighborhood_n_factions (owner 1 and 2)


def test_neighborhood_avg_food():
    settlements = [
        _make_settlement(5, 5, food=0.2),
        _make_settlement(7, 5, food=0.8),  # dist 2 from (5,5)
    ]
    feats = compute_settlement_cell_features(5, 5, settlements)
    assert abs(feats[6] - 0.5) < 0.01  # neighborhood_avg_food = (0.2 + 0.8) / 2


def test_alive_fraction():
    settlements = [
        _make_settlement(5, 5, alive=True),
        _make_settlement(6, 5, alive=False),
        _make_settlement(7, 5, alive=True),
    ]
    feats = compute_settlement_cell_features(5, 5, settlements)
    assert abs(feats[8] - 2.0 / 3.0) < 0.01  # neighborhood_alive_fraction


def test_all_features_finite():
    settlements = [_make_settlement(i, i) for i in range(5)]
    feats = compute_settlement_cell_features(2, 2, settlements)
    assert np.all(np.isfinite(feats))


# --- compute_settlement_round_stats ---

def test_round_stats_shape():
    settlements = [_make_settlement(5, 5)]
    stats = compute_settlement_round_stats(settlements)
    assert stats.shape == (NUM_SETTLEMENT_ROUND_FEATURES,)


def test_round_stats_empty():
    stats = compute_settlement_round_stats([])
    assert stats.shape == (NUM_SETTLEMENT_ROUND_FEATURES,)
    assert np.all(stats == 0.0)


def test_round_stats_values():
    settlements = [
        _make_settlement(0, 0, food=0.2, population=1.0, defense=0.5, wealth=0.1, alive=True, owner_id=1),
        _make_settlement(5, 5, food=0.8, population=3.0, defense=0.9, wealth=0.3, alive=False, owner_id=2),
    ]
    stats = compute_settlement_round_stats(settlements)
    assert abs(stats[0] - 0.5) < 0.01    # round_avg_food
    assert abs(stats[1] - 2.0) < 0.01    # round_avg_population
    assert abs(stats[2] - 0.7) < 0.01    # round_avg_defense
    assert abs(stats[3] - 0.5) < 0.01    # round_alive_fraction
    assert stats[4] == 2.0               # round_n_factions
    assert abs(stats[5] - 0.2) < 0.01    # round_avg_wealth


# --- collect_all_settlements ---

def test_collect_from_observations():
    obs1 = {"settlements": [_make_settlement(1, 1), _make_settlement(2, 2)]}
    obs2 = {"settlements": [_make_settlement(3, 3)]}
    result = collect_all_settlements([obs1, obs2])
    assert len(result) == 3


def test_collect_empty_observations():
    result = collect_all_settlements([{"settlements": []}, {}])
    assert len(result) == 0
