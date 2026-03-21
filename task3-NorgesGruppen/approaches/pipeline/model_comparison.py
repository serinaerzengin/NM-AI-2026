"""Phase 2: Model head-to-head comparison.

Trains 4 models on fold 0 with best augmentation from Phase 1, 80 epochs, imgsz=1280.
Scores with competition formula: 0.7 * det_mAP@0.5 + 0.3 * cls_mAP@0.5.

Usage:
    python model_comparison.py [--model-idx 0]

SLURM: --array=0-3 for parallel training of 4 models.
"""

import argparse
import json
from pathlib import Path

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

MODELS = [
    {"name": "yolov8l", "weights": "yolov8l.pt", "type": "yolo"},
    {"name": "yolov8x", "weights": "yolov8x.pt", "type": "yolo"},
    {"name": "rtdetr-l", "weights": "rtdetr-l.pt", "type": "rtdetr"},
    {"name": "rtdetr-x", "weights": "rtdetr-x.pt", "type": "rtdetr"},
]

DEVICE = "0" if torch.cuda.is_available() else "cpu"
EPOCHS = 80
FOLD_IDX = 0


def load_best_augmentation() -> dict:
    """Load best augmentation config from Phase 1."""
    aug_path = RESULTS_DIR / "aug_search_best.json"
    if aug_path.exists():
        with open(aug_path) as f:
            data = json.load(f)
        return data["best_params"]

    # Sensible defaults if Phase 1 hasn't run
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


def train_and_score(model_info: dict, aug_params: dict, splits: dict) -> dict:
    """Train one model and return results."""
    fold = splits[f"fold_{FOLD_IDX}"]
    train_ids = fold["train"]
    val_ids = fold["val"]

    name = model_info["name"]
    print(f"\n{'='*60}")
    print(f"Training {name} ({model_info['weights']})")
    print(f"{'='*60}")

    # Prepare dataset
    work_dir = TASK_DIR / "data" / "processed" / f"model_cmp_{name}"
    yaml_path = coco_to_yolo(train_ids, val_ids, work_dir)

    # Extract imgsz and close_mosaic from aug_params
    params = aug_params.copy()
    imgsz = params.pop("imgsz", 1280)
    close_mosaic = params.pop("close_mosaic", 10)

    model = YOLO(model_info["weights"])

    project_dir = TASK_DIR / "data" / "processed" / "model_cmp_runs"
    model.train(
        data=str(yaml_path),
        epochs=EPOCHS,
        imgsz=imgsz,
        batch=-1,  # auto batch
        device=DEVICE,
        project=str(project_dir),
        name=name,
        exist_ok=True,
        seed=42,
        close_mosaic=close_mosaic,
        save=True,
        val=True,
        **params,
    )

    # Score with competition metric
    best_pt = project_dir / name / "weights" / "best.pt"
    if not best_pt.exists():
        print(f"ERROR: No best.pt found for {name}")
        return {"model": name, "score": 0, "detection_map50": 0, "classification_map50": 0}

    result = score_model_on_val(best_pt, set(val_ids), imgsz=imgsz, device=DEVICE)

    # Check model size (FP16)
    import os
    model_size_mb = os.path.getsize(best_pt) / (1024 * 1024)

    output = {
        "model": name,
        "weights": model_info["weights"],
        "type": model_info["type"],
        "size_mb": round(model_size_mb, 1),
        "imgsz": imgsz,
        **result,
    }

    print(f"\n{name} results:")
    print(f"  Detection mAP@0.5:      {result['detection_map50']:.4f}")
    print(f"  Classification mAP@0.5: {result['classification_map50']:.4f}")
    print(f"  Score:                   {result['score']:.4f}")
    print(f"  Model size:              {model_size_mb:.1f} MB")

    return output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-idx", type=int, default=None,
                        help="Model index (0-3). Uses SLURM_ARRAY_TASK_ID if not set.")
    parser.add_argument("--splits", default=None)
    args = parser.parse_args()

    model_idx = args.model_idx if args.model_idx is not None else get_slurm_array_task_id()
    splits = load_kfold_splits(Path(args.splits) if args.splits else None)
    aug_params = load_best_augmentation()
    print(f"Augmentation config: {aug_params}")

    if model_idx < len(MODELS):
        # Train single model (SLURM worker mode)
        model_info = MODELS[model_idx]
        result = train_and_score(model_info, aug_params, splits)

        # Save individual result
        out_path = RESULTS_DIR / f"model_cmp_{model_info['name']}.json"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w") as f:
            json.dump(result, f, indent=2)
        print(f"Saved to {out_path}")
    else:
        print(f"Invalid model index: {model_idx}")
        return

    # If we're the last worker (or running locally), aggregate results
    all_results = []
    for m in MODELS:
        path = RESULTS_DIR / f"model_cmp_{m['name']}.json"
        if path.exists():
            with open(path) as f:
                all_results.append(json.load(f))

    if len(all_results) == len(MODELS):
        all_results.sort(key=lambda x: x["score"], reverse=True)
        winner = all_results[0]

        summary = {"models": all_results, "winner": winner["model"]}
        out_path = RESULTS_DIR / "model_comparison.json"
        with open(out_path, "w") as f:
            json.dump(summary, f, indent=2)

        print(f"\n{'='*60}")
        print("ALL MODELS COMPARED:")
        for r in all_results:
            print(f"  {r['model']:12s}  score={r['score']:.4f}  "
                  f"det={r['detection_map50']:.4f}  cls={r['classification_map50']:.4f}  "
                  f"size={r['size_mb']:.0f}MB")
        print(f"WINNER: {winner['model']}")
        print(f"{'='*60}")


if __name__ == "__main__":
    main()
