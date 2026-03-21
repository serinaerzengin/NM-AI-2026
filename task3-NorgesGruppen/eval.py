"""Local evaluation for NorgesGruppen object detection.

Usage:
  uv run eval.py yolov8                        # run approaches/yolov8/predict.py on val split
  uv run eval.py yolov8 --all                  # evaluate on all images
  uv run eval.py yolov8 --val-ratio 0.2        # custom val split
  uv run eval.py --predictions predictions.json # score an existing predictions file

Each approach needs: approaches/<name>/predict.py
  Contract: python predict.py --input <images_dir> --output <predictions.json>

Score = 0.7 * detection_mAP@0.5 + 0.3 * classification_mAP@0.5
"""

import argparse
import json
import random
import subprocess
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

TASK_DIR = Path(__file__).parent
ANNOTATIONS = TASK_DIR / "data" / "raw" / "train" / "annotations.json"
IMAGES_DIR = TASK_DIR / "data" / "raw" / "train" / "images"


# ---------------------------------------------------------------------------
# Scoring
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


def compute_ap(precisions: list[float], recalls: list[float]) -> float:
    if not precisions:
        return 0.0
    precisions = [0.0] + precisions + [0.0]
    recalls = [0.0] + recalls + [1.0]
    for i in range(len(precisions) - 2, -1, -1):
        precisions[i] = max(precisions[i], precisions[i + 1])
    # 101-point interpolation
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


def score(gt_by_image: dict, pred_by_image: dict) -> dict:
    det = compute_map50(gt_by_image, pred_by_image, check_category=False)
    cls = compute_map50(gt_by_image, pred_by_image, check_category=True)
    return {"detection_map50": det, "classification_map50": cls, "score": 0.7 * det + 0.3 * cls}


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_ground_truth(ann_path: Path, image_ids: set[int] | None = None) -> dict:
    with open(ann_path) as f:
        coco = json.load(f)
    gt = defaultdict(list)
    for ann in coco["annotations"]:
        if image_ids and ann["image_id"] not in image_ids:
            continue
        gt[ann["image_id"]].append({"bbox": ann["bbox"], "category_id": ann["category_id"]})
    return gt


def load_predictions(path: Path, image_ids: set[int] | None = None) -> dict:
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


def val_split(ann_path: Path, val_ratio: float, seed: int) -> set[int]:
    with open(ann_path) as f:
        coco = json.load(f)
    ids = [img["id"] for img in coco["images"]]
    rng = random.Random(seed)
    rng.shuffle(ids)
    n = max(1, int(len(ids) * val_ratio))
    return set(ids[:n])


# ---------------------------------------------------------------------------
# Inference runner
# ---------------------------------------------------------------------------

def run_predict(approach: str, images_dir: Path, image_ids: set[int] | None = None) -> Path:
    predict_py = TASK_DIR / "approaches" / approach / "predict.py"
    if not predict_py.exists():
        print(f"Error: {predict_py} not found")
        print(f"Each approach needs a predict.py with: --input <dir> --output <path>")
        sys.exit(1)

    # Symlink only needed images to a temp dir
    tmp_dir = Path(tempfile.mkdtemp())
    input_dir = tmp_dir / "images"
    input_dir.mkdir()

    for img in images_dir.iterdir():
        if img.suffix.lower() not in (".jpg", ".jpeg", ".png"):
            continue
        if image_ids:
            img_id = int(img.stem.split("_")[-1])
            if img_id not in image_ids:
                continue
        (input_dir / img.name).symlink_to(img.resolve())

    output_path = tmp_dir / "predictions.json"

    cmd = [sys.executable, str(predict_py), "--input", str(input_dir), "--output", str(output_path)]
    print(f"Running: {approach}/predict.py on {len(list(input_dir.iterdir()))} images...")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.stdout.strip():
        print(result.stdout.strip())
    if result.returncode != 0:
        print(f"STDERR:\n{result.stderr}")
        sys.exit(1)

    return output_path


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="uv run eval.py <approach>")
    parser.add_argument("approach", nargs="?", help="Approach folder name (e.g. yolov8)")
    parser.add_argument("--predictions", help="Score an existing predictions.json instead")
    parser.add_argument("--all", action="store_true", help="Evaluate on all images (default: val split)")
    parser.add_argument("--val-ratio", type=float, default=0.1, help="Val split ratio (default: 0.1)")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    if not args.approach and not args.predictions:
        parser.error("Provide an approach name or --predictions path")

    # Val split
    image_ids = None
    if not args.all:
        image_ids = val_split(ANNOTATIONS, args.val_ratio, args.seed)
        print(f"Val split: {len(image_ids)} images (ratio={args.val_ratio}, seed={args.seed})")

    # Get predictions
    if args.approach:
        pred_path = run_predict(args.approach, IMAGES_DIR, image_ids)
    else:
        pred_path = Path(args.predictions)

    # Score
    gt = load_ground_truth(ANNOTATIONS, image_ids)
    preds = load_predictions(pred_path, image_ids)

    total_gt = sum(len(v) for v in gt.values())
    total_pred = sum(len(v) for v in preds.values())
    print(f"\nImages: {len(gt)} GT, {len(preds)} predicted")
    print(f"Boxes:  {total_gt} GT, {total_pred} predicted")

    result = score(gt, preds)

    print(f"\n{'='*44}")
    print(f"  Detection mAP@0.5:       {result['detection_map50']:.4f}  (× 0.7)")
    print(f"  Classification mAP@0.5:  {result['classification_map50']:.4f}  (× 0.3)")
    print(f"{'='*44}")
    print(f"  Final Score:             {result['score']:.4f}")
    print(f"{'='*44}")


if __name__ == "__main__":
    main()
