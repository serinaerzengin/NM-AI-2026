"""Tests for astar/predictor.py — XGBoost predictor."""

import numpy as np
import pytest

from astar.predictor import Predictor, _floor_and_normalize, _static_prediction
from astar.types import (
    MapState, RoundStats, Prediction, NUM_CLASSES,
    OCEAN, PLAINS, MOUNTAIN, FOREST,
)


def test_floor_and_normalize_no_zeros():
    """After flooring, no probability should be below PROB_FLOOR."""
    probs = np.zeros((3, 3, NUM_CLASSES), dtype=np.float32)
    probs[:, :, 0] = 1.0
    result = _floor_and_normalize(probs)
    assert np.all(result >= 0.009)  # slightly below 0.01 due to renormalization


def test_floor_and_normalize_sums_to_one():
    """Each cell should sum to 1 after normalization."""
    probs = np.random.rand(5, 5, NUM_CLASSES).astype(np.float32)
    result = _floor_and_normalize(probs)
    sums = result.sum(axis=-1)
    np.testing.assert_allclose(sums, 1.0, atol=1e-5)


def test_static_prediction_ocean():
    pred = _static_prediction(OCEAN)
    assert pred is not None
    assert pred[0] == 1.0  # CLASS_EMPTY
    assert pred.sum() == 1.0


def test_static_prediction_mountain():
    pred = _static_prediction(MOUNTAIN)
    assert pred is not None
    assert pred[5] == 1.0  # CLASS_MOUNTAIN
    assert pred.sum() == 1.0


def test_static_prediction_plains_returns_none():
    """Plains are not static — model should predict them."""
    pred = _static_prediction(PLAINS)
    assert pred is None


def test_static_prediction_forest_returns_none():
    """Forests are not fully static — model should predict them."""
    pred = _static_prediction(FOREST)
    assert pred is None


def test_predictor_fit_and_predict():
    """Predictor should fit on training data and produce valid predictions."""
    # Create small training data
    grid = np.full((10, 10), PLAINS, dtype=int)
    grid[0, :] = OCEAN
    grid[9, :] = OCEAN
    grid[:, 0] = OCEAN
    grid[:, 9] = OCEAN
    grid[5, 5] = MOUNTAIN

    state = MapState(
        grid=grid,
        settlements=[{"x": 3, "y": 3, "has_port": False, "alive": True}],
    )

    gt = np.full((10, 10, NUM_CLASSES), 0.01, dtype=np.float32)
    gt[:, :, 0] = 0.95
    gt = gt / gt.sum(axis=-1, keepdims=True)
    # Ocean/mountain static
    gt[0, :] = [1, 0, 0, 0, 0, 0]
    gt[9, :] = [1, 0, 0, 0, 0, 0]
    gt[:, 0] = [1, 0, 0, 0, 0, 0]
    gt[:, 9] = [1, 0, 0, 0, 0, 0]
    gt[5, 5] = [0, 0, 0, 0, 0, 1]

    stats = RoundStats(ruin_rate=0.01, settlement_rate=0.1, port_rate=0.01, expansion_distance=2.0, forest_rate=0.2, empty_rate=0.6, settlement_to_ruin_ratio=0.9)

    predictor = Predictor(params={"n_estimators": 10, "max_depth": 3})
    predictor.fit([state, state], [gt, gt], [stats, stats])

    pred = predictor.predict(state, stats)
    assert isinstance(pred, Prediction)
    assert pred.probs.shape == (10, 10, NUM_CLASSES)


def test_predictor_output_sums_to_one():
    """Every cell's prediction should sum to 1."""
    grid = np.full((10, 10), PLAINS, dtype=int)
    grid[0, :] = OCEAN
    grid[9, :] = OCEAN
    grid[:, 0] = OCEAN
    grid[:, 9] = OCEAN

    state = MapState(
        grid=grid,
        settlements=[{"x": 3, "y": 3, "has_port": False, "alive": True}],
    )

    gt = np.random.dirichlet(np.ones(NUM_CLASSES), size=(10, 10)).astype(np.float32)
    gt[0, :] = [1, 0, 0, 0, 0, 0]
    gt[9, :] = [1, 0, 0, 0, 0, 0]
    gt[:, 0] = [1, 0, 0, 0, 0, 0]
    gt[:, 9] = [1, 0, 0, 0, 0, 0]

    stats = RoundStats(ruin_rate=0.02, settlement_rate=0.15, port_rate=0.01, expansion_distance=2.0, forest_rate=0.2, empty_rate=0.6, settlement_to_ruin_ratio=0.88)

    predictor = Predictor(params={"n_estimators": 10, "max_depth": 3})
    predictor.fit([state], [gt], [stats])
    pred = predictor.predict(state, stats)

    sums = pred.probs.sum(axis=-1)
    np.testing.assert_allclose(sums, 1.0, atol=1e-5)


def test_predictor_no_zeros():
    """No cell should have 0 probability for any class."""
    grid = np.full((10, 10), PLAINS, dtype=int)
    grid[0, :] = OCEAN
    state = MapState(grid=grid, settlements=[{"x": 3, "y": 3, "has_port": False, "alive": True}])

    gt = np.random.dirichlet(np.ones(NUM_CLASSES), size=(10, 10)).astype(np.float32)
    gt[0, :] = [1, 0, 0, 0, 0, 0]

    stats = RoundStats(ruin_rate=0.02, settlement_rate=0.15, port_rate=0.01, expansion_distance=2.0, forest_rate=0.2, empty_rate=0.6, settlement_to_ruin_ratio=0.88)

    predictor = Predictor(params={"n_estimators": 10, "max_depth": 3})
    predictor.fit([state], [gt], [stats])
    pred = predictor.predict(state, stats)

    # Non-static cells should have no exact zeros
    for r in range(1, 10):
        for c in range(10):
            assert np.all(pred.probs[r, c] > 0), f"Zero found at ({r}, {c})"


def test_predictor_raises_if_not_fitted():
    predictor = Predictor()
    grid = np.full((5, 5), PLAINS, dtype=int)
    state = MapState(grid=grid, settlements=[])
    stats = RoundStats(0, 0, 0, 0, 0, 0, 0)
    with pytest.raises(RuntimeError):
        predictor.predict(state, stats)
