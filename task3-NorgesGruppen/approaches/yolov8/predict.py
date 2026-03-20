"""YOLOv8 inference — same contract as sandbox run.py.

Usage: python predict.py --input <images_dir> --output <predictions.json>
"""
import argparse
import json
from pathlib import Path

import torch
from ultralytics import YOLO

MODELS_DIR = Path(__file__).parent.parent.parent / "models"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    device = "cuda" if torch.cuda.is_available() else "cpu"

    model_path = MODELS_DIR / "best.pt"
    if not model_path.exists():
        model_path = MODELS_DIR / "yolov8n.pt"
    if not model_path.exists():
        raise FileNotFoundError(f"No model found in {MODELS_DIR}")

    model = YOLO(str(model_path))
    predictions = []

    for img_path in sorted(Path(args.input).iterdir()):
        if img_path.suffix.lower() not in (".jpg", ".jpeg", ".png"):
            continue
        image_id = int(img_path.stem.split("_")[-1])
        with torch.no_grad():
            results = model(str(img_path), device=device, verbose=False)
        for r in results:
            if r.boxes is None:
                continue
            for i in range(len(r.boxes)):
                x1, y1, x2, y2 = r.boxes.xyxy[i].tolist()
                predictions.append({
                    "image_id": image_id,
                    "category_id": int(r.boxes.cls[i].item()),
                    "bbox": [round(x1, 1), round(y1, 1), round(x2 - x1, 1), round(y2 - y1, 1)],
                    "score": round(float(r.boxes.conf[i].item()), 3),
                })

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(predictions, f)
    print(f"{len(predictions)} predictions")


if __name__ == "__main__":
    main()
