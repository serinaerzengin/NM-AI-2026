"""
NM i AI 2026 — Task 3: NorgesGruppen Object Detection
Ensemble of three YOLOv8 ONNX models with Weighted Boxes Fusion.
"""
import argparse
import json
import numpy as np
from pathlib import Path
from PIL import Image, ImageOps
import onnxruntime as ort
from ensemble_boxes import weighted_boxes_fusion

# ── Config ──────────────────────────────────────────────────────────────
# (filename, input_size)
MODELS = [
    ("best1.onnx", 1280),
    ("last.onnx", 800),
]
CONF_THRESH = 0.05       # per-model threshold before fusion
WBF_IOU_THRESH = 0.40    # WBF IoU threshold
WBF_SKIP_THRESH = 0.05   # minimum score after fusion


def load_sessions(model_dir):
    """Load ONNX sessions with GPU if available."""
    providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
    sessions = []
    for mf, _ in MODELS:
        path = str(model_dir / mf)
        sess = ort.InferenceSession(path, providers=providers)
        sessions.append(sess)
    return sessions


def preprocess(img, img_size):
    """Letterbox resize to img_size x img_size."""
    orig_w, orig_h = img.size

    scale = min(img_size / orig_w, img_size / orig_h)
    new_w, new_h = int(orig_w * scale), int(orig_h * scale)
    pad_w = (img_size - new_w) / 2
    pad_h = (img_size - new_h) / 2

    resized = img.resize((new_w, new_h), Image.BILINEAR)
    canvas = Image.new("RGB", (img_size, img_size), (114, 114, 114))
    canvas.paste(resized, (int(pad_w), int(pad_h)))

    arr = np.array(canvas, dtype=np.float32) / 255.0
    arr = np.transpose(arr, (2, 0, 1))[np.newaxis, ...]
    return arr, scale, pad_w, pad_h


def decode_detections(output, orig_w, orig_h, scale, pad_w, pad_h, flipped=False):
    """Decode end-to-end YOLO output [1, N, 6] -> boxes, scores, labels.

    Returns normalised boxes (0-1 range) for ensemble_boxes compatibility.
    """
    dets = output[0]  # (N, 6): x1, y1, x2, y2, conf, cls
    boxes, scores, labels = [], [], []
    for det in dets:
        x1, y1, x2, y2, conf, cls_id = det
        if conf < CONF_THRESH:
            continue
        # Undo letterbox -> original pixel coords
        x1 = (x1 - pad_w) / scale
        y1 = (y1 - pad_h) / scale
        x2 = (x2 - pad_w) / scale
        y2 = (y2 - pad_h) / scale
        # Undo horizontal flip
        if flipped:
            x1, x2 = orig_w - x2, orig_w - x1
        # Clip
        x1 = max(0.0, min(float(x1), orig_w))
        y1 = max(0.0, min(float(y1), orig_h))
        x2 = max(0.0, min(float(x2), orig_w))
        y2 = max(0.0, min(float(y2), orig_h))
        if x2 - x1 < 1 or y2 - y1 < 1:
            continue
        # Normalise to 0-1 for WBF
        boxes.append([x1 / orig_w, y1 / orig_h, x2 / orig_w, y2 / orig_h])
        scores.append(float(conf))
        labels.append(int(cls_id))
    return boxes, scores, labels


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    model_dir = Path(__file__).parent
    sessions = load_sessions(model_dir)
    input_names = [s.get_inputs()[0].name for s in sessions]

    predictions = []
    images = sorted(
        p for p in Path(args.input).iterdir()
        if p.suffix.lower() in (".jpg", ".jpeg", ".png")
    )

    for img_path in images:
        image_id = int(img_path.stem.split("_")[-1])
        img = Image.open(img_path).convert("RGB")
        orig_w, orig_h = img.size

        # Run all models with TTA (original + horizontal flip)
        img_flip = ImageOps.mirror(img)
        all_boxes, all_scores, all_labels = [], [], []
        for (mf, img_size), sess, inp_name in zip(MODELS, sessions, input_names):
            # Original
            arr, scale, pad_w, pad_h = preprocess(img, img_size)
            output = sess.run(None, {inp_name: arr})
            boxes, scores, labels = decode_detections(
                output[0], orig_w, orig_h, scale, pad_w, pad_h
            )
            all_boxes.append(boxes)
            all_scores.append(scores)
            all_labels.append(labels)
            # Horizontal flip
            arr_f, scale_f, pad_w_f, pad_h_f = preprocess(img_flip, img_size)
            output_f = sess.run(None, {inp_name: arr_f})
            boxes_f, scores_f, labels_f = decode_detections(
                output_f[0], orig_w, orig_h, scale_f, pad_w_f, pad_h_f, flipped=True
            )
            all_boxes.append(boxes_f)
            all_scores.append(scores_f)
            all_labels.append(labels_f)

        # Weighted Boxes Fusion
        if any(len(b) > 0 for b in all_boxes):
            fused_boxes, fused_scores, fused_labels = weighted_boxes_fusion(
                all_boxes, all_scores, all_labels,
                iou_thr=WBF_IOU_THRESH,
                skip_box_thr=WBF_SKIP_THRESH,
            )
        else:
            fused_boxes, fused_scores, fused_labels = [], [], []

        # Convert back to COCO format [x, y, w, h] in pixels
        for box, score, label in zip(fused_boxes, fused_scores, fused_labels):
            x1 = float(box[0]) * orig_w
            y1 = float(box[1]) * orig_h
            x2 = float(box[2]) * orig_w
            y2 = float(box[3]) * orig_h
            predictions.append({
                "image_id": image_id,
                "category_id": int(label),
                "bbox": [round(x1, 1), round(y1, 1), round(x2 - x1, 1), round(y2 - y1, 1)],
                "score": round(float(score), 4),
            })

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(predictions, f)


if __name__ == "__main__":
    main()
