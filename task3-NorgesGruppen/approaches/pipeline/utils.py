"""Shared utilities for the training pipeline.

Provides scoring callback for Optuna, fold loading, COCO-to-YOLO conversion,
and the competition scoring function.
"""

import json
import shutil
from collections import defaultdict
from pathlib import Path

import numpy as np  # noqa: F401 — used in downstream pipeline scripts

TASK_DIR = Path(__file__).resolve().parent.parent.parent
ANNOTATIONS = TASK_DIR / "data" / "raw" / "train" / "annotations.json"
IMAGES_DIR = TASK_DIR / "data" / "raw" / "train" / "images"
SPLITS_DIR = TASK_DIR / "data" / "splits"
RESULTS_DIR = TASK_DIR / "results"


# ---------------------------------------------------------------------------
# Scoring (matches eval.py exactly)
# ---------------------------------------------------------------------------

def compute_iou(box1: list, box2: list) -> float:
    x1, y1, w1, h1 = box1
    x2, y2, w2, h2 = box2
    ix0, iy0 = max(x1, x2), max(y1, y2)
    ix1, iy1 = min(x1 + w1, x2 + w2), min(y1 + h1, y2 + h2)
    if ix1 <= ix0 or iy1 <= iy0:
        return 0.0
    inter = (ix1 - ix0) * (iy1 - iy0)
    union = w1 * h1 + w2 * h2 - inter
    return inter / union if union > 0 else 0.0


def compute_ap(precisions: list, recalls: list) -> float:
    if not precisions:
        return 0.0
    precisions = [0.0] + precisions + [0.0]
    recalls = [0.0] + recalls + [1.0]
    for i in range(len(precisions) - 2, -1, -1):
        precisions[i] = max(precisions[i], precisions[i + 1])
    ap = 0.0
    for k in range(101):
        t = k / 100.0
        p = 0.0
        for r, pr in zip(recalls, precisions):
            if r >= t:
                p = max(p, pr)
        ap += p
    return ap / 101


def compute_map50(gt_by_image: dict, pred_by_image: dict, check_category: bool = False) -> float:
    all_image_ids = set(gt_by_image) | set(pred_by_image)
    all_preds = []
    total_gt = 0
    for img_id in all_image_ids:
        gts = gt_by_image.get(img_id, [])
        preds = pred_by_image.get(img_id, [])
        total_gt += len(gts)
        matched = set()
        for pred in preds:
            best_iou, best_idx = 0.0, -1
            for gi, gt in enumerate(gts):
                if gi in matched:
                    continue
                iou = compute_iou(pred["bbox"], gt["bbox"])
                if iou > best_iou:
                    best_iou, best_idx = iou, gi
            if best_iou >= 0.5 and best_idx >= 0:
                if not check_category or pred["category_id"] == gts[best_idx]["category_id"]:
                    all_preds.append((pred["score"], True))
                    matched.add(best_idx)
                else:
                    all_preds.append((pred["score"], False))
            else:
                all_preds.append((pred["score"], False))
    if total_gt == 0:
        return 0.0
    all_preds.sort(key=lambda x: x[0], reverse=True)
    tp, precisions, recalls = 0, [], []
    for i, (_, is_tp) in enumerate(all_preds):
        tp += is_tp
        precisions.append(tp / (i + 1))
        recalls.append(tp / total_gt)
    return compute_ap(precisions, recalls)


def competition_score(gt_by_image: dict, pred_by_image: dict) -> dict:
    det = compute_map50(gt_by_image, pred_by_image, check_category=False)
    cls = compute_map50(gt_by_image, pred_by_image, check_category=True)
    return {"detection_map50": det, "classification_map50": cls, "score": 0.7 * det + 0.3 * cls}


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_annotations():
    """Load COCO annotations."""
    with open(ANNOTATIONS) as f:
        return json.load(f)


def load_ground_truth(image_ids: set | None = None) -> dict:
    coco = load_annotations()
    gt = defaultdict(list)
    for ann in coco["annotations"]:
        if image_ids and ann["image_id"] not in image_ids:
            continue
        gt[ann["image_id"]].append({"bbox": ann["bbox"], "category_id": ann["category_id"]})
    return gt


def load_predictions(path: Path, image_ids: set | None = None) -> dict:
    with open(path) as f:
        preds = json.load(f)
    by_image = defaultdict(list)
    for p in preds:
        if image_ids and p["image_id"] not in image_ids:
            continue
        by_image[p["image_id"]].append({"bbox": p["bbox"], "category_id": p["category_id"], "score": p["score"]})
    for img_id in by_image:
        by_image[img_id].sort(key=lambda x: x["score"], reverse=True)
    return by_image


def load_kfold_splits(path: Path | None = None) -> dict:
    """Load K-fold splits from JSON."""
    if path is None:
        path = SPLITS_DIR / "kfold_5.json"
    with open(path) as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# COCO → YOLO conversion
# ---------------------------------------------------------------------------

def coco_to_yolo(train_ids: list[int], val_ids: list[int], output_dir: Path, clean: bool = True) -> Path:
    """Convert COCO annotations to YOLO format for given train/val image IDs.

    Returns path to dataset.yaml.
    """
    coco = load_annotations()
    images_dir = IMAGES_DIR

    img_lookup = {img["id"]: img for img in coco["images"]}
    anns_by_image = {}
    for ann in coco["annotations"]:
        anns_by_image.setdefault(ann["image_id"], []).append(ann)

    num_classes = len(coco["categories"])
    class_names = {cat["id"]: cat["name"] for cat in coco["categories"]}

    if clean and output_dir.exists():
        shutil.rmtree(output_dir)

    for split in ("train", "val"):
        (output_dir / "images" / split).mkdir(parents=True, exist_ok=True)
        (output_dir / "labels" / split).mkdir(parents=True, exist_ok=True)

    split_map = {**{i: "train" for i in train_ids}, **{i: "val" for i in val_ids}}

    for img_id, split in split_map.items():
        img_info = img_lookup[img_id]
        w, h = img_info["width"], img_info["height"]
        fname = img_info["file_name"]
        stem = Path(fname).stem

        src = images_dir / fname
        dst = output_dir / "images" / split / fname
        if not dst.exists():
            # Use symlink for speed
            dst.symlink_to(src.resolve())

        label_path = output_dir / "labels" / split / f"{stem}.txt"
        lines = []
        for ann in anns_by_image.get(img_id, []):
            if ann.get("iscrowd", 0):
                continue
            bx, by, bw, bh = ann["bbox"]
            cx = max(0, min(1, (bx + bw / 2) / w))
            cy = max(0, min(1, (by + bh / 2) / h))
            nw = max(0, min(1, bw / w))
            nh = max(0, min(1, bh / h))
            lines.append(f"{ann['category_id']} {cx:.6f} {cy:.6f} {nw:.6f} {nh:.6f}")
        label_path.write_text("\n".join(lines))

    yaml_content = f"""path: {output_dir.resolve()}
train: images/train
val: images/val

nc: {num_classes}
names:
"""
    for i in range(num_classes):
        name = class_names.get(i, f"class_{i}")
        yaml_content += f'  {i}: "{name}"\n'

    yaml_path = output_dir / "dataset.yaml"
    yaml_path.write_text(yaml_content)
    return yaml_path


def coco_to_yolo_all(output_dir: Path, clean: bool = True) -> Path:
    """Convert all images (no val split) for final training."""
    coco = load_annotations()
    all_ids = [img["id"] for img in coco["images"]]
    # Put all images in train, use a dummy val with 1 image
    return coco_to_yolo(all_ids, [all_ids[0]], output_dir, clean=clean)


# ---------------------------------------------------------------------------
# Ultralytics scoring callback for Optuna
# ---------------------------------------------------------------------------

def score_model_on_val(model_path: Path, val_image_ids: set[int], imgsz: int = 1280,
                       conf: float = 0.001, device: str = "0") -> dict:
    """Run inference with a trained model and compute competition score."""
    import torch
    from ultralytics import YOLO

    model = YOLO(str(model_path))
    gt = load_ground_truth(val_image_ids)

    pred_by_image = defaultdict(list)
    for img_id in val_image_ids:
        img_info = None
        coco = load_annotations()
        for img in coco["images"]:
            if img["id"] == img_id:
                img_info = img
                break
        if img_info is None:
            continue

        img_path = IMAGES_DIR / img_info["file_name"]
        with torch.no_grad():
            results = model(str(img_path), device=device, imgsz=imgsz, conf=conf,
                            max_det=300, verbose=False)

        for r in results:
            if r.boxes is None:
                continue
            for i in range(len(r.boxes)):
                x1, y1, x2, y2 = r.boxes.xyxy[i].tolist()
                pred_by_image[img_id].append({
                    "bbox": [round(x1, 1), round(y1, 1), round(x2 - x1, 1), round(y2 - y1, 1)],
                    "category_id": int(r.boxes.cls[i].item()),
                    "score": round(float(r.boxes.conf[i].item()), 3),
                })

    for img_id in pred_by_image:
        pred_by_image[img_id].sort(key=lambda x: x["score"], reverse=True)

    return competition_score(gt, pred_by_image)


# ---------------------------------------------------------------------------
# SLURM helpers
# ---------------------------------------------------------------------------

def get_slurm_array_task_id() -> int:
    """Get SLURM array task ID, defaulting to 0."""
    import os
    return int(os.environ.get("SLURM_ARRAY_TASK_ID", "0"))
