"""Experiment: Ensemble of XGBoost + CatBoost + LightGBM.

Simple average of three diverse tree-based models.
Also tests weighted averaging.
"""

import sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

from eval_harness import load_train_val, evaluate_predictions, print_results
import xgboost as xgb
from catboost import CatBoostRegressor
from lightgbm import LGBMRegressor
import json


def train_xgboost(train_X, train_y, train_w):
    params = json.load(open(Path(__file__).parent.parent / "best_params.json"))
    model = xgb.XGBRegressor(
        n_estimators=params.get("n_estimators", 500),
        max_depth=params.get("max_depth", 7),
        learning_rate=params.get("learning_rate", 0.05),
        subsample=params.get("subsample", 0.8),
        colsample_bytree=params.get("colsample_bytree", 0.8),
        reg_alpha=params.get("reg_alpha", 0.01),
        reg_lambda=params.get("reg_lambda", 1.0),
        min_child_weight=params.get("min_child_weight", 1),
        multi_strategy="multi_output_tree",
        tree_method="hist",
        objective="reg:squarederror",
        n_jobs=-1,
        verbosity=0,
    )
    model.fit(train_X, train_y, sample_weight=train_w)
    return lambda X: model.predict(X)


def train_catboost(train_X, train_y, train_w, depth=5, lr=0.1, iters=300):
    models = []
    for c in range(train_y.shape[1]):
        target = train_y[:, c]
        if target.max() - target.min() < 1e-8:
            models.append(None)
            continue
        m = CatBoostRegressor(
            iterations=iters, depth=depth, learning_rate=lr,
            loss_function="RMSE", verbose=0, thread_count=-1,
        )
        m.fit(train_X, target, sample_weight=train_w)
        models.append(m)

    def predict(X):
        cols = []
        for m in models:
            if m is None:
                cols.append(np.zeros(len(X), dtype=np.float32))
            else:
                cols.append(m.predict(X))
        return np.column_stack(cols)
    return predict


def train_lightgbm(train_X, train_y, train_w, n_estimators=300, max_depth=5, lr=0.1, subsample=0.7):
    models = []
    for c in range(train_y.shape[1]):
        m = LGBMRegressor(
            n_estimators=n_estimators, max_depth=max_depth,
            learning_rate=lr, subsample=subsample,
            verbosity=-1, n_jobs=-1,
        )
        m.fit(train_X, train_y[:, c], sample_weight=train_w)
        models.append(m)

    def predict(X):
        return np.column_stack([m.predict(X) for m in models])
    return predict


def main():
    print("Loading data...")
    train_X, train_y, train_w, val_data = load_train_val()
    print(f"Train: {train_X.shape[0]} samples, {train_X.shape[1]} features\n")

    # Train all three models
    print("Training XGBoost (Optuna params)...")
    xgb_predict = train_xgboost(train_X, train_y, train_w)

    print("Training CatBoost (d=5, lr=0.1, i=300)...")
    cat_predict = train_catboost(train_X, train_y, train_w)

    print("Training LightGBM (n=300, d=5, lr=0.1)...")
    lgb_predict = train_lightgbm(train_X, train_y, train_w)

    # Individual scores for reference
    print("\n=== Individual Models ===")
    for name, fn in [("XGBoost", xgb_predict), ("CatBoost", cat_predict), ("LightGBM", lgb_predict)]:
        results = evaluate_predictions(val_data, fn, prob_floor=0.001)
        print_results(name, results)

    # Equal-weight ensemble
    print("\n=== Ensembles ===")
    def ensemble_equal(X):
        return (xgb_predict(X) + cat_predict(X) + lgb_predict(X)) / 3.0

    results = evaluate_predictions(val_data, ensemble_equal, prob_floor=0.001)
    print_results("Ensemble (equal 1/3 each)", results)

    # XGBoost-weighted ensemble (since it's the best individual)
    for xgb_w in [0.4, 0.5, 0.6]:
        other_w = (1.0 - xgb_w) / 2.0
        def make_weighted(xw=xgb_w, ow=other_w):
            def fn(X):
                return xw * xgb_predict(X) + ow * cat_predict(X) + ow * lgb_predict(X)
            return fn
        results = evaluate_predictions(val_data, make_weighted(), prob_floor=0.001)
        print_results(f"Ensemble (XGB={xgb_w}, Cat={other_w:.2f}, LGB={other_w:.2f})", results)

    # Two-model ensembles
    def xgb_cat(X):
        return (xgb_predict(X) + cat_predict(X)) / 2.0
    def xgb_lgb(X):
        return (xgb_predict(X) + lgb_predict(X)) / 2.0

    results = evaluate_predictions(val_data, xgb_cat, prob_floor=0.001)
    print_results("Ensemble (XGB + Cat)", results)

    results = evaluate_predictions(val_data, xgb_lgb, prob_floor=0.001)
    print_results("Ensemble (XGB + LGB)", results)


if __name__ == "__main__":
    main()
