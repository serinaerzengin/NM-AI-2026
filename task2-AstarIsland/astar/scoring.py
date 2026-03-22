import numpy as np


def score_prediction(prediction: np.ndarray, ground_truth: np.ndarray) -> float:
    """Compute seed score using entropy-weighted KL divergence.

    Args:
        prediction: (H, W, 6) predicted probability distributions.
        ground_truth: (H, W, 6) true probability distributions.

    Returns:
        Score in [0, 100]. Higher is better.
    """
    eps = 1e-12

    # Per-cell entropy of ground truth
    entropy = -np.sum(ground_truth * np.log(ground_truth + eps), axis=-1)  # (H, W)

    # Per-cell KL divergence: KL(ground_truth || prediction)
    kl = np.sum(ground_truth * np.log((ground_truth + eps) / (prediction + eps)), axis=-1)  # (H, W)

    # Entropy-weighted average KL
    total_entropy = entropy.sum()
    if total_entropy < eps:
        return 100.0  # All cells are static → perfect by default

    weighted_kl = (entropy * kl).sum() / total_entropy

    # Score formula
    score = max(0.0, min(100.0, 100.0 * np.exp(-3.0 * weighted_kl)))
    return float(score)
