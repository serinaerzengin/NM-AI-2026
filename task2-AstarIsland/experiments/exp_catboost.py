"""Experiment: CatBoost model.

CatBoost uses ordered boosting and handles categorical features natively.
Train 6 separate CatBoostRegressor models (one per class) with RMSE loss,
since MultiRMSE fails when individual target columns are constant.
"""

import sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

from eval_harness import load_train_val, evaluate_predictions, print_results
from catboost import CatBoostRegressor


def train_catboost_ensemble(train_X, train_y, train_w, depth=7, lr=0.05, iters=500, verbose=100):
    """Train 6 separate CatBoostRegressor models, one per output class."""
    n_classes = train_y.shape[1]
    models = []
    for c in range(n_classes):
        target = train_y[:, c]
        # Skip constant targets (e.g., mountain class is always 0 for dynamic cells)
        if target.max() - target.min() < 1e-8:
            models.append(None)
            if verbose:
                print(f"  Class {c}: constant target, skipping")
            continue
        if verbose:
            print(f"  Training model for class {c}...")
        model = CatBoostRegressor(
            iterations=iters,
            depth=depth,
            learning_rate=lr,
            loss_function="RMSE",
            verbose=verbose,
            thread_count=-1,
        )
        model.fit(train_X, target, sample_weight=train_w)
        models.append(model)
    return models


def make_predict_fn(models):
    """Return a predict function that stacks all 6 model outputs into (N, 6)."""
    def predict_fn(X):
        cols = []
        for m in models:
            if m is None:
                cols.append(np.zeros(len(X), dtype=np.float32))
            else:
                cols.append(m.predict(X))
        return np.column_stack(cols)
    return predict_fn


def main():
    print("Loading data...")
    train_X, train_y, train_w, val_data = load_train_val()
    print(f"Train: {train_X.shape[0]} samples, {train_X.shape[1]} features")

    # Default params
    print("\nTraining CatBoost (depth=7, lr=0.05, iters=500)...")
    models = train_catboost_ensemble(train_X, train_y, train_w, depth=7, lr=0.05, iters=500, verbose=100)
    predict_fn = make_predict_fn(models)

    results = evaluate_predictions(val_data, predict_fn, prob_floor=0.001)
    best_avg = print_results("CatBoost (d=7, lr=0.05, i=500)", results)
    best_name = "CatBoost (d=7, lr=0.05, i=500)"

    # Try different hyperparameter combos
    for depth, lr, iters in [(5, 0.1, 300), (6, 0.08, 500)]:
        print(f"\nTraining CatBoost (depth={depth}, lr={lr}, iters={iters})...")
        models2 = train_catboost_ensemble(train_X, train_y, train_w, depth=depth, lr=lr, iters=iters, verbose=0)
        predict_fn2 = make_predict_fn(models2)
        results2 = evaluate_predictions(val_data, predict_fn2, prob_floor=0.001)
        avg = print_results(f"CatBoost (d={depth}, lr={lr}, i={iters})", results2)
        if avg < best_avg:
            best_avg = avg
            best_name = f"CatBoost (d={depth}, lr={lr}, i={iters})"

    print(f"\nBest config: {best_name} with avg score {best_avg:.2f}")


if __name__ == "__main__":
    main()
