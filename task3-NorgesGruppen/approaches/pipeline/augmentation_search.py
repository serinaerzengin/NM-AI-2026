"""Phase 1b: Optuna augmentation search using K-fold validation.

Two-stage optimization:
  Stage 1: Folds 0+1 only, 30 epochs each, 40 trials with MedianPruner
  Stage 2: Top-5 configs → full 5-fold validation, 50 epochs

Uses yolov8s as a fixed (small, fast) model for search.

Usage:
    python augmentation_search.py [--stage 1|2] [--study-name aug_search]

SLURM: Each array worker joins the same Optuna study via shared SQLite.
"""

import argparse
import json
import shutil
from pathlib import Path

import numpy as np
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

SEARCH_MODEL = "yolov8s.pt"
DEVICE = "0" if torch.cuda.is_available() else "cpu"


def suggest_augmentation(trial: optuna.Trial) -> dict:
    """Suggest augmentation hyperparameters.

    Includes a 'crop_mode' meta-parameter that controls whether product image
    copy-paste uses background-removed crops, raw crops, or no product crops.
    This is NOT passed to ultralytics — it's handled in train_fold().
    """
    return {
        "mosaic": trial.suggest_categorical("mosaic", [0.0, 0.5, 1.0]),
        "mixup": trial.suggest_float("mixup", 0.0, 0.3),
        "copy_paste": trial.suggest_float("copy_paste", 0.0, 0.3),
        "scale": trial.suggest_float("scale", 0.2, 0.9),
        "degrees": trial.suggest_float("degrees", 0.0, 10.0),
        "shear": trial.suggest_float("shear", 0.0, 3.0),
        "hsv_h": trial.suggest_float("hsv_h", 0.0, 0.03),
        "hsv_s": trial.suggest_float("hsv_s", 0.0, 0.7),
        "hsv_v": trial.suggest_float("hsv_v", 0.0, 0.5),
        "erasing": trial.suggest_float("erasing", 0.0, 0.5),
        "flipud": trial.suggest_categorical("flipud", [0.0]),  # Never flip vertically — unrealistic
        "bgr": trial.suggest_float("bgr", 0.0, 0.1),
        "imgsz": trial.suggest_categorical("imgsz", [640, 960, 1280]),
        "close_mosaic": trial.suggest_categorical("close_mosaic", [5, 10, 15]),
        # Meta-param: which product crops to inject into training data
        # "none" = no product images, "bg_removed" = transparent bg, "raw" = white bg intact
        "crop_mode": trial.suggest_categorical("crop_mode", ["none", "bg_removed", "raw"]),
    }


def inject_product_crops(work_dir: Path, crop_mode: str):
    """Inject product image crops into the YOLO training set.

    For each product crop, pastes it onto a random shelf training image
    at a realistic scale and adds the corresponding YOLO label.
    """
    if crop_mode == "none":
        return

    import cv2

    if crop_mode == "bg_removed":
        crop_dir = TASK_DIR / "data" / "processed" / "product_crops"
    else:  # "raw"
        crop_dir = TASK_DIR / "data" / "processed" / "product_crops_raw"

    manifest_path = crop_dir / "manifest.json"
    if not manifest_path.exists():
        print(f"WARNING: No manifest at {manifest_path}, skipping crop injection")
        return

    import json
    import random
    with open(manifest_path) as f:
        manifest = json.load(f)

    train_img_dir = work_dir / "images" / "train"
    train_lbl_dir = work_dir / "labels" / "train"

    # Get list of existing training images to use as backgrounds
    bg_images = sorted(train_img_dir.glob("*.jpg"))
    if not bg_images:
        return

    rng = random.Random(42)
    injected = 0

    for cat_id_str, crop_files in manifest.items():
        cat_id = int(cat_id_str)

        for crop_file in crop_files:
            crop_path = crop_dir / crop_file

            if crop_mode == "bg_removed":
                crop = cv2.imread(str(crop_path), cv2.IMREAD_UNCHANGED)  # BGRA
                if crop is None or crop.shape[2] != 4:
                    continue
            else:
                crop = cv2.imread(str(crop_path))  # BGR
                if crop is None:
                    continue
                # Add full-opacity alpha channel
                alpha = np.full(crop.shape[:2], 255, dtype=np.uint8)
                crop = np.dstack([crop, alpha])

            crop_h, crop_w = crop.shape[:2]

            # Pick a random background image
            bg_path = rng.choice(bg_images)
            bg_real = bg_path.resolve() if bg_path.is_symlink() else bg_path
            bg = cv2.imread(str(bg_real))
            if bg is None:
                continue
            bg_h, bg_w = bg.shape[:2]

            # Scale crop to realistic shelf-product size (50-150px in a ~2000px image)
            target_h = rng.randint(max(30, bg_h // 30), max(60, bg_h // 10))
            scale = target_h / crop_h
            new_w = int(crop_w * scale)
            new_h = int(crop_h * scale)

            if new_w < 10 or new_h < 10 or new_w >= bg_w or new_h >= bg_h:
                continue

            crop_resized = cv2.resize(crop, (new_w, new_h), interpolation=cv2.INTER_AREA)

            # Random position
            x = rng.randint(0, bg_w - new_w)
            y = rng.randint(0, bg_h - new_h)

            # Alpha-blend onto background
            alpha_mask = crop_resized[:, :, 3:4].astype(np.float32) / 255.0
            fg = crop_resized[:, :, :3].astype(np.float32)
            bg_roi = bg[y:y + new_h, x:x + new_w].astype(np.float32)
            blended = (fg * alpha_mask + bg_roi * (1 - alpha_mask)).astype(np.uint8)
            bg[y:y + new_h, x:x + new_w] = blended

            # Save as new synthetic training image
            syn_name = f"syn_cat{cat_id}_{injected:04d}"
            cv2.imwrite(str(train_img_dir / f"{syn_name}.jpg"), bg)

            # Write YOLO label (append to existing if we reused a bg)
            cx = (x + new_w / 2) / bg_w
            cy = (y + new_h / 2) / bg_h
            nw = new_w / bg_w
            nh = new_h / bg_h
            label_line = f"{cat_id} {cx:.6f} {cy:.6f} {nw:.6f} {nh:.6f}"

            # Also copy original labels from the background image
            orig_label = train_lbl_dir / f"{bg_path.stem}.txt"
            existing_labels = orig_label.read_text().strip() if orig_label.exists() else ""
            new_label_path = train_lbl_dir / f"{syn_name}.txt"
            if existing_labels:
                new_label_path.write_text(existing_labels + "\n" + label_line)
            else:
                new_label_path.write_text(label_line)

            injected += 1

    print(f"  Injected {injected} synthetic images (crop_mode={crop_mode})")


def train_fold(aug_params: dict, fold_idx: int, splits: dict, epochs: int,
               trial: optuna.Trial | None = None, run_name: str = "aug_search") -> float:
    """Train on one fold and return competition score."""
    fold = splits[f"fold_{fold_idx}"]
    train_ids = fold["train"]
    val_ids = fold["val"]

    imgsz = aug_params.pop("imgsz", 1280)
    close_mosaic = aug_params.pop("close_mosaic", 10)
    crop_mode = aug_params.pop("crop_mode", "none")

    # Prepare YOLO dataset
    work_dir = TASK_DIR / "data" / "processed" / f"aug_search_fold{fold_idx}"
    yaml_path = coco_to_yolo(train_ids, val_ids, work_dir)

    # Inject product crops if requested
    inject_product_crops(work_dir, crop_mode)

    model = YOLO(SEARCH_MODEL)

    # Custom callback for Optuna pruning
    def on_fit_epoch_end(trainer):
        if trial is None:
            return
        epoch = trainer.epoch
        metrics = trainer.metrics
        # Use YOLO's built-in mAP50 as a proxy for pruning
        map50 = metrics.get("metrics/mAP50(B)", 0.0)
        trial.report(map50, epoch)
        if trial.should_prune():
            raise optuna.TrialPruned()

    model.add_callback("on_fit_epoch_end", on_fit_epoch_end)

    project_dir = TASK_DIR / "data" / "processed" / "aug_search_runs"
    train_name = f"{run_name}_fold{fold_idx}"

    model.train(
        data=str(yaml_path),
        epochs=epochs,
        imgsz=imgsz,
        batch=-1,  # auto batch size
        device=DEVICE,
        project=str(project_dir),
        name=train_name,
        exist_ok=True,
        seed=42,
        close_mosaic=close_mosaic,
        save=True,
        val=True,
        verbose=False,
        **aug_params,
    )

    # Score with competition metric
    best_pt = project_dir / train_name / "weights" / "best.pt"
    if not best_pt.exists():
        return 0.0

    result = score_model_on_val(best_pt, set(val_ids), imgsz=imgsz, device=DEVICE)
    print(f"  Fold {fold_idx}: det={result['detection_map50']:.4f} "
          f"cls={result['classification_map50']:.4f} score={result['score']:.4f}")

    # Cleanup weights to save disk
    weights_dir = project_dir / train_name / "weights"
    if weights_dir.exists():
        shutil.rmtree(weights_dir)

    return result["score"]


def stage1_objective(trial: optuna.Trial, splits: dict) -> float:
    """Stage 1: Quick evaluation on folds 0 and 1."""
    aug_params = suggest_augmentation(trial)
    print(f"\nTrial {trial.number}: {aug_params}")

    scores = []
    for fold_idx in [0, 1]:
        # Each fold gets its own copy of params (since we pop imgsz/close_mosaic)
        params_copy = aug_params.copy()
        score = train_fold(params_copy, fold_idx, splits, epochs=30,
                           trial=trial, run_name=f"trial{trial.number}")
        scores.append(score)

    avg_score = sum(scores) / len(scores)
    print(f"Trial {trial.number} avg score: {avg_score:.4f}")
    return avg_score


def stage2_evaluate(config: dict, splits: dict, n_folds: int = 5) -> float:
    """Stage 2: Full K-fold evaluation of a config."""
    scores = []
    for fold_idx in range(n_folds):
        params_copy = config.copy()
        score = train_fold(params_copy, fold_idx, splits, epochs=50,
                           run_name=f"stage2_{hash(json.dumps(config, sort_keys=True)) % 10000}")
        scores.append(score)

    avg_score = sum(scores) / len(scores)
    return avg_score


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", type=int, default=1, choices=[1, 2])
    parser.add_argument("--study-name", default="aug_search")
    parser.add_argument("--db-path", default=str(RESULTS_DIR / "optuna_aug_study.db"))
    parser.add_argument("--n-trials", type=int, default=40)
    parser.add_argument("--splits", default=None, help="Path to kfold splits JSON")
    args = parser.parse_args()

    splits = load_kfold_splits(Path(args.splits) if args.splits else None)
    worker_id = get_slurm_array_task_id()

    if args.stage == 1:
        storage = f"sqlite:///{args.db_path}"
        study = optuna.create_study(
            study_name=args.study_name,
            storage=storage,
            direction="maximize",
            load_if_exists=True,
            pruner=optuna.pruners.MedianPruner(n_startup_trials=5, n_warmup_steps=10),
            sampler=optuna.samplers.TPESampler(seed=42 + worker_id),
        )

        study.optimize(
            lambda trial: stage1_objective(trial, splits),
            n_trials=args.n_trials,
        )

        # Save best config
        best = study.best_trial
        print(f"\nBest trial {best.number}: score={best.value:.4f}")
        print(f"Params: {best.params}")

        # Save top-5 for stage 2
        trials_sorted = sorted(study.trials, key=lambda t: t.value if t.value else 0, reverse=True)
        top5 = []
        for t in trials_sorted[:5]:
            if t.value is not None:
                top5.append({"trial": t.number, "score": t.value, "params": t.params})

        output = {"best": best.params, "best_score": best.value, "top5": top5}
        out_path = RESULTS_DIR / "aug_search_stage1.json"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w") as f:
            json.dump(output, f, indent=2)
        print(f"Saved stage 1 results to {out_path}")

    elif args.stage == 2:
        # Load top-5 from stage 1
        stage1_path = RESULTS_DIR / "aug_search_stage1.json"
        with open(stage1_path) as f:
            stage1 = json.load(f)

        top5 = stage1["top5"]
        print(f"Stage 2: evaluating {len(top5)} configs with full 5-fold")

        best_score = 0
        best_config = None

        for i, entry in enumerate(top5):
            config = entry["params"]
            print(f"\nConfig {i+1}/{len(top5)} (trial {entry['trial']}, stage1 score={entry['score']:.4f}):")
            avg = stage2_evaluate(config, splits)
            print(f"  5-fold avg: {avg:.4f}")

            if avg > best_score:
                best_score = avg
                best_config = config

        output = {"best_params": best_config, "best_score": best_score}
        out_path = RESULTS_DIR / "aug_search_best.json"
        with open(out_path, "w") as f:
            json.dump(output, f, indent=2)
        print(f"\nBest augmentation config (score={best_score:.4f}): {best_config}")
        print(f"Saved to {out_path}")


if __name__ == "__main__":
    main()
