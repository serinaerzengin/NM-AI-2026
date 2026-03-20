"""Phase 3: Optuna hyperparameter search for the chosen model.

Searches training hyperparameters (lr, weight_decay, batch, cls loss weight, etc.)
using the winning model from Phase 2 with best augmentation from Phase 1.

Usage:
    python hyperparam_search.py [--n-trials 80] [--study-name hp_search]

SLURM: --array=0-7 for 8 parallel workers sharing SQLite study.
"""

import argparse
import json
import shutil
from pathlib import Path

import optuna
import torch
from ultralytics import YOLO

from utils import (
    RESULTS_DIR,
    TASK_DIR,
    coco_to_yolo,
    get_slurm_array_task_id,
    load_kfold_splits,
    score_model_on_val,
)

DEVICE = "0" if torch.cuda.is_available() else "cpu"
EPOCHS = 60
FOLD_IDX = 0


def get_winning_model() -> str:
    """Load the winning model from Phase 2."""
    cmp_path = RESULTS_DIR / "model_comparison.json"
    if cmp_path.exists():
        with open(cmp_path) as f:
            data = json.load(f)
        winner = data["winner"]
        for m in data["models"]:
            if m["model"] == winner:
                return m["weights"]

    print("WARNING: No model_comparison.json found, defaulting to yolov8x.pt")
    return "yolov8x.pt"


def get_best_augmentation() -> dict:
    """Load best augmentation config from Phase 1."""
    aug_path = RESULTS_DIR / "aug_search_best.json"
    if aug_path.exists():
        with open(aug_path) as f:
            return json.load(f)["best_params"]

    print("WARNING: No aug_search_best.json found, using defaults")
    return {
        "mosaic": 1.0,
        "mixup": 0.1,
        "copy_paste": 0.0,
        "scale": 0.5,
        "degrees": 5.0,
        "hsv_h": 0.015,
        "hsv_s": 0.7,
        "hsv_v": 0.4,
        "erasing": 0.4,
        "close_mosaic": 10,
    }


def suggest_hyperparams(trial: optuna.Trial) -> dict:
    """Suggest training hyperparameters."""
    return {
        "lr0": trial.suggest_float("lr0", 1e-4, 0.05, log=True),
        "lrf": trial.suggest_float("lrf", 0.001, 0.1, log=True),
        "weight_decay": trial.suggest_float("weight_decay", 1e-5, 1e-2, log=True),
        "batch": trial.suggest_categorical("batch", [4, 8, 16]),
        "imgsz": trial.suggest_categorical("imgsz", [960, 1280, 1600]),
        "cls": trial.suggest_float("cls", 0.3, 2.0),
        "box": trial.suggest_float("box", 5.0, 10.0),
        "optimizer": trial.suggest_categorical("optimizer", ["SGD", "AdamW"]),
        "dropout": trial.suggest_float("dropout", 0.0, 0.3),
        "cos_lr": trial.suggest_categorical("cos_lr", [True, False]),
        "label_smoothing": trial.suggest_float("label_smoothing", 0.0, 0.1),
    }


def objective(trial: optuna.Trial, model_weights: str, aug_params: dict,
              splits: dict) -> float:
    """Train with suggested hyperparams and return competition score."""
    hp = suggest_hyperparams(trial)
    print(f"\nTrial {trial.number}: {hp}")

    fold = splits[f"fold_{FOLD_IDX}"]
    train_ids = fold["train"]
    val_ids = fold["val"]

    # Merge aug params (without imgsz/close_mosaic — those come from hp or aug)
    aug = aug_params.copy()
    close_mosaic = aug.pop("close_mosaic", 10)
    aug.pop("imgsz", None)  # Use HP search imgsz

    # Extract HP-specific params
    imgsz = hp.pop("imgsz")
    batch = hp.pop("batch")

    # Prepare dataset
    work_dir = TASK_DIR / "data" / "processed" / f"hp_search_trial{trial.number}"
    yaml_path = coco_to_yolo(train_ids, val_ids, work_dir)

    model = YOLO(model_weights)

    # Pruning callback
    def on_fit_epoch_end(trainer):
        epoch = trainer.epoch
        map50 = trainer.metrics.get("metrics/mAP50(B)", 0.0)
        trial.report(map50, epoch)
        if trial.should_prune():
            raise optuna.TrialPruned()

    model.add_callback("on_fit_epoch_end", on_fit_epoch_end)

    project_dir = TASK_DIR / "data" / "processed" / "hp_search_runs"
    train_name = f"trial{trial.number}"

    try:
        model.train(
            data=str(yaml_path),
            epochs=EPOCHS,
            imgsz=imgsz,
            batch=batch,
            device=DEVICE,
            project=str(project_dir),
            name=train_name,
            exist_ok=True,
            seed=42,
            close_mosaic=close_mosaic,
            save=True,
            val=True,
            verbose=False,
            **aug,
            **hp,
        )
    except optuna.TrialPruned:
        raise
    except Exception as e:
        print(f"Trial {trial.number} failed: {e}")
        return 0.0

    best_pt = project_dir / train_name / "weights" / "best.pt"
    if not best_pt.exists():
        return 0.0

    result = score_model_on_val(best_pt, set(val_ids), imgsz=imgsz, device=DEVICE)
    score = result["score"]

    print(f"Trial {trial.number}: det={result['detection_map50']:.4f} "
          f"cls={result['classification_map50']:.4f} score={score:.4f}")

    # Cleanup to save disk
    weights_dir = project_dir / train_name / "weights"
    if weights_dir.exists():
        shutil.rmtree(weights_dir)
    # Also cleanup dataset
    if work_dir.exists():
        shutil.rmtree(work_dir)

    return score


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--study-name", default="hp_search")
    parser.add_argument("--db-path", default=str(RESULTS_DIR / "optuna_hp_study.db"))
    parser.add_argument("--n-trials", type=int, default=80)
    parser.add_argument("--splits", default=None)
    args = parser.parse_args()

    splits = load_kfold_splits(Path(args.splits) if args.splits else None)
    model_weights = get_winning_model()
    aug_params = get_best_augmentation()
    worker_id = get_slurm_array_task_id()

    print(f"Model: {model_weights}")
    print(f"Augmentation: {aug_params}")
    print(f"Worker: {worker_id}")

    storage = f"sqlite:///{args.db_path}"
    study = optuna.create_study(
        study_name=args.study_name,
        storage=storage,
        direction="maximize",
        load_if_exists=True,
        pruner=optuna.pruners.MedianPruner(n_startup_trials=8, n_warmup_steps=20),
        sampler=optuna.samplers.TPESampler(seed=42 + worker_id),
    )

    study.optimize(
        lambda trial: objective(trial, model_weights, aug_params, splits),
        n_trials=args.n_trials,
    )

    # Save best result
    best = study.best_trial
    print(f"\nBest trial {best.number}: score={best.value:.4f}")
    print(f"Params: {best.params}")

    output = {"best_params": best.params, "best_score": best.value}
    out_path = RESULTS_DIR / "best_hyperparams.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"Saved to {out_path}")


if __name__ == "__main__":
    main()
