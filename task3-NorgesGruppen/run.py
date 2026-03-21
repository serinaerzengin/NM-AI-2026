"""run.py — Sandbox entry point for NorgesGruppen object detection.

Executed as: python run.py --input /data/images --output /output/predictions.json

Uses ONNX Runtime with YOLO26x model (end-to-end, no NMS needed).
Security: No os/sys/subprocess imports — uses pathlib only.
"""
import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image
import onnxruntime as ort


CONF_THRESH = 0.25
IMGSZ = 800


def letterbox(img: Image.Image, new_shape: int = 640):
    """Resize and pad image to square, preserving aspect ratio."""
    w, h = img.size
    scale = new_shape / max(w, h)
    nw, nh = int(w * scale), int(h * scale)
    img_resized = img.resize((nw, nh), Image.BILINEAR)

    padded = Image.new("RGB", (new_shape, new_shape), (114, 114, 114))
    pad_x = (new_shape - nw) // 2
    pad_y = (new_shape - nh) // 2
    padded.paste(img_resized, (pad_x, pad_y))
    return padded, scale, pad_x, pad_y


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Directory with shelf images")
    parser.add_argument("--output", required=True, help="Path to write predictions.json")
    args = parser.parse_args()

    model_path = Path(__file__).parent / "models" / "last.onnx"
    session = ort.InferenceSession(
        str(model_path),
        providers=["CUDAExecutionProvider", "CPUExecutionProvider"],
    )
    input_name = session.get_inputs()[0].name

    predictions = []
    input_dir = Path(args.input)

    for img_path in sorted(input_dir.iterdir()):
        if img_path.suffix.lower() not in (".jpg", ".jpeg", ".png"):
            continue

        image_id = int(img_path.stem.split("_")[-1])
        img = Image.open(img_path).convert("RGB")
        orig_w, orig_h = img.size

        # Preprocess: letterbox + normalize
        padded, scale, pad_x, pad_y = letterbox(img, IMGSZ)
        arr = np.array(padded, dtype=np.float32) / 255.0
        arr = np.transpose(arr, (2, 0, 1))[np.newaxis, ...]  # [1, 3, 640, 640]

        # Inference — output: [1, 300, 6] = [x1, y1, x2, y2, conf, class_id]
        outputs = session.run(None, {input_name: arr})
        pred = outputs[0][0]  # [300, 6]

        # Filter by confidence
        mask = pred[:, 4] > CONF_THRESH
        pred = pred[mask]

        # Scale back to original image coordinates
        for det in pred:
            x1 = (float(det[0]) - pad_x) / scale
            y1 = (float(det[1]) - pad_y) / scale
            x2 = (float(det[2]) - pad_x) / scale
            y2 = (float(det[3]) - pad_y) / scale
            # Clip to image bounds
            x1 = max(0, min(x1, orig_w))
            y1 = max(0, min(y1, orig_h))
            x2 = max(0, min(x2, orig_w))
            y2 = max(0, min(y2, orig_h))
            predictions.append({
                "image_id": image_id,
                "category_id": int(det[5]),
                "bbox": [
                    round(x1, 1),
                    round(y1, 1),
                    round(x2 - x1, 1),
                    round(y2 - y1, 1),
                ],
                "score": round(float(det[4]), 3),
            })

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(predictions, f)

    print(f"Wrote {len(predictions)} predictions to {args.output}")


if __name__ == "__main__":
    main()
