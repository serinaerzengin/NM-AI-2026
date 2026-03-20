"""Phase 4a: Final training on ALL 248 images.

Uses best augmentation (Phase 1) + best model (Phase 2) + best hyperparameters (Phase 3).
Trains for 300 epochs with patience=50, close_mosaic at last 30 epochs.

Usage:
    python final_train.py [--epochs 300] [--patience 50]
"""

import argparse
import json
import shutil

import torch
from ultralytics import YOLO

from utils import RESULTS_DIR, TASK_DIR, coco_to_yolo_all


DEVICE = "0" if torch.cuda.is_available() else "cpu"
MODEL_OUTPUT = TASK_DIR / "models"


def load_full_config() -> dict:
    """Load and merge best configs from all phases."""
    # Best augmentation
    aug_path = RESULTS_DIR / "aug_search_best.json"
    if aug_path.exists():
        with open(aug_path) as f:
            aug = json.load(f)["best_params"]
    else:
        print("WARNING: Using default augmentation")
        aug = {
            "mosaic": 1.0, "mixup": 0.1, "copy_paste": 0.0,
            "scale": 0.5, "degrees": 5.0,
            "hsv_h": 0.015, "hsv_s": 0.7, "hsv_v": 0.4,
            "erasing": 0.4, "close_mosaic": 10,
        }

    # Best model
    cmp_path = RESULTS_DIR / "model_comparison.json"
    if cmp_path.exists():
        with open(cmp_path) as f:
            cmp = json.load(f)
        winner = cmp["winner"]
        model_weights = None
        for m in cmp["models"]:
            if m["model"] == winner:
                model_weights = m["weights"]
                break
    else:
        print("WARNING: Using default model yolov8x.pt")
        model_weights = "yolov8x.pt"

    # Best hyperparameters
    hp_path = RESULTS_DIR / "best_hyperparams.json"
    if hp_path.exists():
        with open(hp_path) as f:
            hp = json.load(f)["best_params"]
    else:
        print("WARNING: Using default hyperparameters")
        hp = {
            "lr0": 0.01, "lrf": 0.01, "weight_decay": 0.0005,
            "batch": 8, "imgsz": 1280,
            "cls": 0.5, "box": 7.5,
            "optimizer": "AdamW", "dropout": 0.0,
            "cos_lr": False, "label_smoothing": 0.0,
        }

    return {
        "model_weights": model_weights,
        "aug": aug,
        "hp": hp,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--epochs", type=int, default=300)
    parser.add_argument("--patience", type=int, default=50)
    args = parser.parse_args()

    config = load_full_config()
    model_weights = config["model_weights"]
    aug = config["aug"]
    hp = config["hp"]

    print(f"Model: {model_weights}")
    print(f"Augmentation: {json.dumps(aug, indent=2)}")
    print(f"Hyperparameters: {json.dumps(hp, indent=2)}")

    # Prepare dataset with ALL images
    work_dir = TASK_DIR / "data" / "processed" / "final_train"
    yaml_path = coco_to_yolo_all(work_dir)
    print(f"Dataset: {yaml_path}")

    # Extract params
    imgsz = hp.pop("imgsz", 1280)
    batch = hp.pop("batch", 8)
    aug.pop("close_mosaic", None)  # Override with longer close_mosaic for final training
    aug.pop("imgsz", None)

    # Use close_mosaic = 30 for final training (last 30 epochs without mosaic)
    final_close_mosaic = 30

    model = YOLO(model_weights)

    project_dir = TASK_DIR / "data" / "processed" / "final_train_runs"
    model.train(
        data=str(yaml_path),
        epochs=args.epochs,
        imgsz=imgsz,
        batch=batch,
        device=DEVICE,
        project=str(project_dir),
        name="final",
        exist_ok=True,
        seed=42,
        patience=args.patience,
        close_mosaic=final_close_mosaic,
        save=True,
        val=True,
        multi_scale=0.5,
        **aug,
        **hp,
    )

    # Copy best weights to models/
    best_pt = project_dir / "final" / "weights" / "best.pt"
    if best_pt.exists():
        MODEL_OUTPUT.mkdir(parents=True, exist_ok=True)
        dst = MODEL_OUTPUT / "best.pt"
        shutil.copy2(best_pt, dst)
        print(f"\nBest model copied to {dst}")

        import os
        size_mb = os.path.getsize(dst) / (1024 * 1024)
        print(f"Model size: {size_mb:.1f} MB")
        if size_mb > 420:
            print("WARNING: Model exceeds 420 MB submission limit!")
    else:
        print("ERROR: No best.pt found!")

    # Save final config for reference
    config_out = {
        "model": model_weights,
        "epochs": args.epochs,
        "imgsz": imgsz,
        "batch": batch,
        "augmentation": aug,
        "hyperparameters": hp,
    }
    with open(RESULTS_DIR / "final_train_config.json", "w") as f:
        json.dump(config_out, f, indent=2)


if __name__ == "__main__":
    main()
