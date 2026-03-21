"""DINOv2+DETR inference — same contract as sandbox run.py.

Usage: python predict.py --input <images_dir> --output <predictions.json>
"""
import argparse
import json
from pathlib import Path

import torch
from PIL import Image
from transformers import AutoImageProcessor, DetrForObjectDetection

MODELS_DIR = Path(__file__).parent.parent.parent / "models"
WEIGHTS_DIR = MODELS_DIR / "dinov2_detr"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    if not WEIGHTS_DIR.exists():
        raise FileNotFoundError(
            f"No DINOv2+DETR weights at {WEIGHTS_DIR}\n"
            "Train first, or copy outputs_dinov2_detr/best/ into models/dinov2_detr/"
        )

    model = DetrForObjectDetection.from_pretrained(str(WEIGHTS_DIR)).to(device).eval()
    processor = AutoImageProcessor.from_pretrained(str(WEIGHTS_DIR))

    predictions = []
    threshold = 0.3

    for img_path in sorted(Path(args.input).iterdir()):
        if img_path.suffix.lower() not in (".jpg", ".jpeg", ".png"):
            continue
        image_id = int(img_path.stem.split("_")[-1])
        image = Image.open(img_path).convert("RGB")

        inputs = processor(images=image, return_tensors="pt").to(device)
        with torch.no_grad():
            outputs = model(**inputs)

        target_sizes = torch.tensor([image.size[::-1]], device=device)
        results = processor.post_process_object_detection(outputs, threshold=threshold, target_sizes=target_sizes)[0]

        for score_t, label, box in zip(results["scores"], results["labels"], results["boxes"]):
            x1, y1, x2, y2 = box.tolist()
            predictions.append({
                "image_id": image_id,
                "category_id": int(label.item()),
                "bbox": [round(x1, 1), round(y1, 1), round(x2 - x1, 1), round(y2 - y1, 1)],
                "score": round(float(score_t.item()), 3),
            })

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(predictions, f)
    print(f"{len(predictions)} predictions")


if __name__ == "__main__":
    main()
