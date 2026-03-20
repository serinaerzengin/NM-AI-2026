"""Experiment: LightGBM model.

LightGBM uses histogram-based splitting and leaf-wise tree growth,
which can be faster and sometimes more accurate than XGBoost/CatBoost.

Since LightGBM doesn't support multi-output natively, we train 6
separate LGBMRegressor models (one per target class).
"""

import sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

from eval_harness import load_train_val, evaluate_predictions, print_results
from lightgbm import LGBMRegressor


def train_multioutput_lgbm(train_X, train_y, train_w, **params):
    """Train 6 independent LGBMRegressor models, one per class."""
    n_classes = train_y.shape[1]
    models = []
    for c in range(n_classes):
        model = LGBMRegressor(
            verbosity=-1,
            n_jobs=-1,
            **params,
        )
        model.fit(train_X, train_y[:, c], sample_weight=train_w)
        models.append(model)
    return models


def make_predict_fn(models):
    """Create a predict function that returns (N, 6) from 6 models."""
    def predict_fn(X):
        preds = np.column_stack([m.predict(X) for m in models])
        return preds
    return predict_fn


def main():
    print("Loading data...")
    train_X, train_y, train_w, val_data = load_train_val()
    print(f"Train: {train_X.shape[0]} samples, {train_X.shape[1]} features")
    print(f"Targets: {train_y.shape[1]} classes")

    configs = [
        {"n_estimators": 500, "max_depth": 7, "learning_rate": 0.05, "subsample": 0.8},
        {"n_estimators": 300, "max_depth": 5, "learning_rate": 0.1,  "subsample": 0.7},
        {"n_estimators": 700, "max_depth": 8, "learning_rate": 0.03, "subsample": 0.8},
    ]

    best_avg = -1
    best_name = ""

    for i, params in enumerate(configs):
        name = (
            f"LightGBM (n={params['n_estimators']}, d={params['max_depth']}, "
            f"lr={params['learning_rate']}, sub={params['subsample']})"
        )
        print(f"\n[{i+1}/{len(configs)}] Training {name}...")

        models = train_multioutput_lgbm(train_X, train_y, train_w, **params)
        predict_fn = make_predict_fn(models)

        results = evaluate_predictions(val_data, predict_fn, prob_floor=0.001)
        avg = print_results(name, results)

        if avg > best_avg:
            best_avg = avg
            best_name = name

    print(f"\n{'=' * 50}")
    print(f"  Best config: {best_name}")
    print(f"  Best overall avg: {best_avg:.2f}")
    print(f"{'=' * 50}")


if __name__ == "__main__":
    main()
