"""run.py — Sandbox entry point for NorgesGruppen object detection.

Executed as: python run.py --input /data/images --output /output/predictions.json

Uses a locally trained YOLOv8 model (best.pt) for inference.
Falls back to detection-only (category_id=0) if no fine-tuned model available.

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

    # Load model — best.pt is fine-tuned on competition data (nc=357)
    # Falls back to yolov8n.pt (pretrained COCO, detection-only baseline)
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
            results = model(str(img_path), device=device, verbose=False)

        for r in results:
            if r.boxes is None:
                continue
            for i in range(len(r.boxes)):
                x1, y1, x2, y2 = r.boxes.xyxy[i].tolist()
                predictions.append({
                    "image_id": image_id,
                    "category_id": int(r.boxes.cls[i].item()),
                    "bbox": [
                        round(x1, 1),
                        round(y1, 1),
                        round(x2 - x1, 1),
                        round(y2 - y1, 1),
                    ],
                    "score": round(float(r.boxes.conf[i].item()), 3),
                })

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(predictions, f)

    print(f"Wrote {len(predictions)} predictions to {args.output}")


if __name__ == "__main__":
    main()
