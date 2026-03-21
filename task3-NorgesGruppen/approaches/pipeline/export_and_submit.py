"""Phase 4b: Export best model and update run.py for submission.

Tunes confidence threshold on K-fold validation data, then rewrites run.py
with optimal inference settings.

Usage:
    python export_and_submit.py [--tune-conf]
"""

import argparse
import json
from collections import defaultdict
from pathlib import Path

import numpy as np
import torch
from ultralytics import YOLO

from utils import (
    IMAGES_DIR,
    RESULTS_DIR,
    TASK_DIR,
    competition_score,
    load_annotations,
    load_ground_truth,
    load_kfold_splits,
)

MODEL_PATH = TASK_DIR / "models" / "best.pt"
RUN_PY = TASK_DIR / "run.py"


def tune_confidence(model_path: Path, splits: dict, imgsz: int = 1280,
                    device: str = "0") -> float:
    """Find optimal confidence threshold using K-fold val sets."""
    model = YOLO(str(model_path))
    coco = load_annotations()
    img_lookup = {img["id"]: img for img in coco["images"]}

    # Collect all val predictions across folds
    all_val_ids = set()
    for fold in splits.values():
        all_val_ids.update(fold["val"])

    # Run inference at very low conf to get all candidates
    gt = load_ground_truth(all_val_ids)
    pred_by_image = defaultdict(list)

    for img_id in all_val_ids:
        img_info = img_lookup.get(img_id)
        if img_info is None:
            continue
        img_path = IMAGES_DIR / img_info["file_name"]

        with torch.no_grad():
            results = model(str(img_path), device=device, imgsz=imgsz,
                            conf=0.001, max_det=300, verbose=False)

        for r in results:
            if r.boxes is None:
                continue
            for i in range(len(r.boxes)):
                x1, y1, x2, y2 = r.boxes.xyxy[i].tolist()
                pred_by_image[img_id].append({
                    "bbox": [round(x1, 1), round(y1, 1), round(x2 - x1, 1), round(y2 - y1, 1)],
                    "category_id": int(r.boxes.cls[i].item()),
                    "score": round(float(r.boxes.conf[i].item()), 4),
                })

    for img_id in pred_by_image:
        pred_by_image[img_id].sort(key=lambda x: x["score"], reverse=True)

    # Search for best conf threshold
    best_conf = 0.001
    best_score = 0.0

    for conf in np.arange(0.001, 0.5, 0.005):
        filtered = {}
        for img_id, preds in pred_by_image.items():
            filtered[img_id] = [p for p in preds if p["score"] >= conf]
        result = competition_score(gt, filtered)
        if result["score"] > best_score:
            best_score = result["score"]
            best_conf = float(conf)

    print(f"Best conf threshold: {best_conf:.3f} (score={best_score:.4f})")
    return best_conf


def generate_run_py(conf: float, imgsz: int = 1280, use_tta: bool = True,
                    ensemble: bool = False, second_model: str | None = None) -> str:
    """Generate optimized run.py content."""

    if ensemble and second_model:
        return _generate_ensemble_run_py(conf, imgsz, second_model)

    tta_line = "augment=True," if use_tta else ""

    return f'''"""run.py — Sandbox entry point for NorgesGruppen object detection.

Executed as: python run.py --input /data/images --output /output/predictions.json

Optimized inference settings from pipeline training.
Security: No os/sys/subprocess imports — uses pathlib only.
"""
import argparse
import json
from pathlib import Path

import torch
from ultralytics import YOLO


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Directory with shelf images")
    parser.add_argument("--output", required=True, help="Path to write predictions.json")
    args = parser.parse_args()

    device = "cuda" if torch.cuda.is_available() else "cpu"

    model_path = Path(__file__).parent / "models" / "best.pt"
    if not model_path.exists():
        model_path = Path(__file__).parent / "models" / "yolov8n.pt"
    model = YOLO(str(model_path))

    predictions = []
    input_dir = Path(args.input)

    for img_path in sorted(input_dir.iterdir()):
        if img_path.suffix.lower() not in (".jpg", ".jpeg", ".png"):
            continue

        image_id = int(img_path.stem.split("_")[-1])

        with torch.no_grad():
            results = model(
                str(img_path),
                device=device,
                imgsz={imgsz},
                conf={conf},
                max_det=300,
                half=True,
                {tta_line}
                verbose=False,
            )

        for r in results:
            if r.boxes is None:
                continue
            for i in range(len(r.boxes)):
                x1, y1, x2, y2 = r.boxes.xyxy[i].tolist()
                predictions.append({{
                    "image_id": image_id,
                    "category_id": int(r.boxes.cls[i].item()),
                    "bbox": [
                        round(x1, 1),
                        round(y1, 1),
                        round(x2 - x1, 1),
                        round(y2 - y1, 1),
                    ],
                    "score": round(float(r.boxes.conf[i].item()), 3),
                }})

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(predictions, f)

    print(f"Wrote {{len(predictions)}} predictions to {{args.output}}")


if __name__ == "__main__":
    main()
'''


def _generate_ensemble_run_py(conf: float, imgsz: int, second_model: str) -> str:
    """Generate run.py with WBF ensemble of two models."""
    return f'''"""run.py — Sandbox entry point with WBF ensemble.

Executed as: python run.py --input /data/images --output /output/predictions.json

Runs two models and fuses predictions with Weighted Boxes Fusion.
Security: No os/sys/subprocess imports — uses pathlib only.
"""
import argparse
import json
from pathlib import Path

import numpy as np
import torch
from ensemble_boxes import weighted_boxes_fusion
from ultralytics import YOLO


def run_model(model, img_path, device, imgsz, conf):
    """Run inference and return normalized boxes, scores, labels."""
    with torch.no_grad():
        results = model(str(img_path), device=device, imgsz=imgsz,
                        conf=conf, max_det=300, half=True, verbose=False)

    boxes, scores, labels = [], [], []
    for r in results:
        if r.boxes is None:
            continue
        # Get image dimensions for normalization
        h, w = r.orig_shape
        for i in range(len(r.boxes)):
            x1, y1, x2, y2 = r.boxes.xyxy[i].tolist()
            boxes.append([x1/w, y1/h, x2/w, y2/h])
            scores.append(float(r.boxes.conf[i].item()))
            labels.append(int(r.boxes.cls[i].item()))

    return boxes, scores, labels, (h, w)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    device = "cuda" if torch.cuda.is_available() else "cpu"

    model_dir = Path(__file__).parent / "models"
    model1 = YOLO(str(model_dir / "best.pt"))
    model2 = YOLO(str(model_dir / "{second_model}"))

    predictions = []
    input_dir = Path(args.input)

    for img_path in sorted(input_dir.iterdir()):
        if img_path.suffix.lower() not in (".jpg", ".jpeg", ".png"):
            continue

        image_id = int(img_path.stem.split("_")[-1])

        # Run both models
        b1, s1, l1, (h, w) = run_model(model1, img_path, device, {imgsz}, {conf})
        b2, s2, l2, _ = run_model(model2, img_path, device, {imgsz}, {conf})

        if not b1 and not b2:
            continue

        # WBF fusion
        boxes_list = [b1, b2]
        scores_list = [s1, s2]
        labels_list = [l1, l2]

        fused_boxes, fused_scores, fused_labels = weighted_boxes_fusion(
            boxes_list, scores_list, labels_list,
            weights=[1.0, 0.8],
            iou_thr=0.55,
            skip_box_thr={conf},
        )

        for box, score, label in zip(fused_boxes, fused_scores, fused_labels):
            x1, y1, x2, y2 = box
            predictions.append({{
                "image_id": image_id,
                "category_id": int(label),
                "bbox": [
                    round(x1 * w, 1),
                    round(y1 * h, 1),
                    round((x2 - x1) * w, 1),
                    round((y2 - y1) * h, 1),
                ],
                "score": round(float(score), 3),
            }})

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(predictions, f)

    print(f"Wrote {{len(predictions)}} predictions to {{args.output}}")


if __name__ == "__main__":
    main()
'''


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tune-conf", action="store_true",
                        help="Tune confidence threshold on K-fold val")
    parser.add_argument("--imgsz", type=int, default=1280)
    parser.add_argument("--no-tta", action="store_true", help="Disable TTA")
    parser.add_argument("--ensemble", action="store_true", help="Generate ensemble run.py")
    parser.add_argument("--second-model", default=None, help="Second model filename for ensemble")
    args = parser.parse_args()

    device = "0" if torch.cuda.is_available() else "cpu"

    # Determine conf threshold
    if args.tune_conf:
        splits = load_kfold_splits()
        conf = tune_confidence(MODEL_PATH, splits, imgsz=args.imgsz, device=device)
    else:
        conf = 0.01  # reasonable default

    # Verify model size
    if MODEL_PATH.exists():
        import os
        size_mb = os.path.getsize(MODEL_PATH) / (1024 * 1024)
        print(f"Model size: {size_mb:.1f} MB")
        if size_mb > 420:
            print("WARNING: Model exceeds 420 MB limit!")
    else:
        print("WARNING: models/best.pt not found!")

    # Generate and write run.py
    content = generate_run_py(
        conf=conf,
        imgsz=args.imgsz,
        use_tta=not args.no_tta,
        ensemble=args.ensemble,
        second_model=args.second_model,
    )

    RUN_PY.write_text(content)
    print(f"Updated {RUN_PY}")
    print(f"  conf={conf}, imgsz={args.imgsz}, tta={not args.no_tta}, ensemble={args.ensemble}")

    # Save export config
    export_config = {
        "conf": conf,
        "imgsz": args.imgsz,
        "tta": not args.no_tta,
        "ensemble": args.ensemble,
        "second_model": args.second_model,
    }
    with open(RESULTS_DIR / "export_config.json", "w") as f:
        json.dump(export_config, f, indent=2)


if __name__ == "__main__":
    main()
