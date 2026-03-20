"""Tests for astar/scoring.py — entropy-weighted KL divergence scoring."""

import numpy as np

from astar.scoring import score_prediction
from astar.types import NUM_CLASSES


def test_perfect_prediction_scores_100():
    """Predicting the ground truth exactly should score 100."""
    gt = np.random.dirichlet(np.ones(NUM_CLASSES), size=(10, 10)).astype(np.float32)
    score = score_prediction(gt, gt)
    assert abs(score - 100.0) < 0.1


def test_uniform_prediction_scores_lower_than_good():
    """Uniform 1/6 prediction should score worse than a near-perfect prediction."""
    gt = np.zeros((10, 10, NUM_CLASSES), dtype=np.float32)
    # Make sharply peaked distributions (more realistic)
    gt[:, :, 0] = 0.8
    gt[:, :, 1] = 0.15
    gt[:, :, 3] = 0.05

    uniform = np.full_like(gt, 1.0 / NUM_CLASSES)
    good_pred = gt + 0.01
    good_pred = good_pred / good_pred.sum(axis=-1, keepdims=True)

    uniform_score = score_prediction(uniform, gt)
    good_score = score_prediction(good_pred, gt)
    assert good_score > uniform_score
    assert uniform_score < 50


def test_score_bounded():
    """Score should always be between 0 and 100."""
    gt = np.random.dirichlet(np.ones(NUM_CLASSES), size=(10, 10)).astype(np.float32)
    pred = np.random.dirichlet(np.ones(NUM_CLASSES), size=(10, 10)).astype(np.float32)
    score = score_prediction(pred, gt)
    assert 0 <= score <= 100


def test_all_static_cells_score_100():
    """If all cells are static (entropy ~0), score should be 100."""
    gt = np.zeros((5, 5, NUM_CLASSES), dtype=np.float32)
    gt[:, :, 0] = 1.0  # All cells are class 0 with 100% probability

    pred = np.full((5, 5, NUM_CLASSES), 1.0 / NUM_CLASSES, dtype=np.float32)
    score = score_prediction(pred, gt)
    # Static cells have zero entropy → weighted KL = 0 → score = 100
    assert score > 99.0


def test_better_prediction_scores_higher():
    """A prediction closer to ground truth should score higher."""
    gt = np.zeros((5, 5, NUM_CLASSES), dtype=np.float32)
    gt[:, :, 0] = 0.3
    gt[:, :, 1] = 0.5
    gt[:, :, 3] = 0.2

    # Good prediction: close to gt
    good_pred = gt.copy()
    good_pred[:, :, 0] = 0.25
    good_pred[:, :, 1] = 0.55
    good_pred[:, :, 3] = 0.20
    good_pred = good_pred / good_pred.sum(axis=-1, keepdims=True)

    # Bad prediction: far from gt
    bad_pred = np.full_like(gt, 1.0 / NUM_CLASSES)

    good_score = score_prediction(good_pred, gt)
    bad_score = score_prediction(bad_pred, gt)
    assert good_score > bad_score


def test_zero_prediction_handled():
    """Predictions with zeros shouldn't crash (eps handles it)."""
    gt = np.zeros((3, 3, NUM_CLASSES), dtype=np.float32)
    gt[:, :, 0] = 0.5
    gt[:, :, 1] = 0.5

    pred = np.zeros_like(gt)
    pred[:, :, 0] = 1.0  # Predicts class 0 only

    score = score_prediction(pred, gt)
    assert 0 <= score <= 100
