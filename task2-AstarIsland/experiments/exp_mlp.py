"""Experiment: MLP (Multi-Layer Perceptron) model.

Uses sklearn MLPRegressor with StandardScaler preprocessing.
MLPs benefit from normalized inputs — StandardScaler is essential here.
Note: sklearn MLPRegressor does not support sample_weight, so we train
unweighted. This is fine for architecture comparison purposes.
"""

import sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

from eval_harness import load_train_val, evaluate_predictions, print_results
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import StandardScaler


def run_mlp(name, train_X, train_y, val_data, scaler, **mlp_kwargs):
    """Train and evaluate a single MLP configuration."""
    print(f"\nTraining {name}...")
    model = MLPRegressor(random_state=42, **mlp_kwargs)
    X_scaled = scaler.transform(train_X)
    model.fit(X_scaled, train_y)
    print(f"  Converged: {model.n_iter_} iters, final loss: {model.loss_:.6f}")

    def predict_fn(X):
        return model.predict(scaler.transform(X))

    results = evaluate_predictions(val_data, predict_fn, prob_floor=0.001)
    return print_results(name, results)


def main():
    print("Loading data...")
    train_X, train_y, train_w, val_data = load_train_val()
    print(f"Train: {train_X.shape[0]} samples, {train_X.shape[1]} features")
    print(f"Targets: {train_y.shape[1]} classes")

    # Fit scaler on training data
    print("Fitting StandardScaler...")
    scaler = StandardScaler()
    scaler.fit(train_X)

    configs = [
        ("MLP (128, 64)", dict(
            hidden_layer_sizes=(128, 64),
            max_iter=500,
        )),
        ("MLP (256, 128, 64)", dict(
            hidden_layer_sizes=(256, 128, 64),
            max_iter=500,
        )),
        ("MLP (128, 128)", dict(
            hidden_layer_sizes=(128, 128),
            max_iter=1000,
        )),
    ]

    best_score = -1
    best_name = ""
    for name, kwargs in configs:
        score = run_mlp(name, train_X, train_y, val_data, scaler, **kwargs)
        if score > best_score:
            best_score = score
            best_name = name

    print(f"\n{'=' * 50}")
    print(f"  Best config: {best_name} (avg {best_score:.2f})")
    print(f"{'=' * 50}")


if __name__ == "__main__":
    main()
