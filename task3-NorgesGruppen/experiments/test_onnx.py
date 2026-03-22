"""Quick test: run both ONNX models on a few training images and compare."""
import json
import numpy as np
from pathlib import Path
from PIL import Image
import onnxruntime as ort

BASE = Path(r"C:\Users\light\Documents\ntnu\NM-AI-2026\task3-NorgesGruppen")
IMAGES_DIR = BASE / "data" / "NM_NGD_coco_dataset" / "train" / "images"
ANNOT_FILE = BASE / "data" / "NM_NGD_coco_dataset" / "train" / "annotations.json"
MODELS = ["best.onnx", "best1.onnx"]
TEST_IMAGES = ["img_00001.jpg", "img_00002.jpg", "img_00004.jpg"]
CONF_THRESH = 0.3
IMG_SIZE = 1280


def preprocess(img_path):
    """Resize and normalize image for YOLO ONNX input."""
    img = Image.open(img_path).convert("RGB")
    orig_w, orig_h = img.size

    # Letterbox resize
    scale = min(IMG_SIZE / orig_w, IMG_SIZE / orig_h)
    new_w, new_h = int(orig_w * scale), int(orig_h * scale)
    pad_w, pad_h = (IMG_SIZE - new_w) / 2, (IMG_SIZE - new_h) / 2

    resized = img.resize((new_w, new_h), Image.BILINEAR)
    canvas = Image.new("RGB", (IMG_SIZE, IMG_SIZE), (114, 114, 114))
    canvas.paste(resized, (int(pad_w), int(pad_h)))

    arr = np.array(canvas).astype(np.float32) / 255.0
    arr = np.transpose(arr, (2, 0, 1))[np.newaxis, ...]
    return arr, orig_w, orig_h, scale, pad_w, pad_h


def postprocess(output, orig_w, orig_h, scale, pad_w, pad_h, conf_thresh=CONF_THRESH):
    """Convert YOLO end-to-end output [1, 300, 6] to list of dicts."""
    dets = output[0]  # (300, 6)
    results = []
    for det in dets:
        x1, y1, x2, y2, conf, cls_id = det
        if conf < conf_thresh:
            continue
        # Undo letterbox
        x1 = (x1 - pad_w) / scale
        y1 = (y1 - pad_h) / scale
        x2 = (x2 - pad_w) / scale
        y2 = (y2 - pad_h) / scale
        # Clip
        x1 = max(0, min(x1, orig_w))
        y1 = max(0, min(y1, orig_h))
        x2 = max(0, min(x2, orig_w))
        y2 = max(0, min(y2, orig_h))
        w, h = x2 - x1, y2 - y1
        if w < 1 or h < 1:
            continue
        results.append({
            "category_id": int(cls_id),
            "bbox": [round(x1, 1), round(y1, 1), round(w, 1), round(h, 1)],
            "score": round(float(conf), 4),
        })
    return results


# Load ground truth for comparison
with open(ANNOT_FILE, "r", encoding="utf-8") as f:
    coco = json.load(f)
cat_map = {c["id"]: c["name"] for c in coco["categories"]}
anns_by_img = {}
img_id_map = {}
for img_info in coco["images"]:
    img_id_map[img_info["file_name"]] = img_info["id"]
for ann in coco["annotations"]:
    anns_by_img.setdefault(ann["image_id"], []).append(ann)

# Run both models
for model_name in MODELS:
    print(f"\n{'='*60}")
    print(f"MODEL: {model_name}")
    print(f"{'='*60}")
    session = ort.InferenceSession(
        str(BASE / model_name),
        providers=["CPUExecutionProvider"],
    )
    input_name = session.get_inputs()[0].name

    for img_name in TEST_IMAGES:
        img_path = IMAGES_DIR / img_name
        arr, ow, oh, sc, pw, ph = preprocess(img_path)
        outputs = session.run(None, {input_name: arr})
        preds = postprocess(outputs[0], ow, oh, sc, pw, ph)

        img_id = img_id_map.get(img_name, -1)
        gt_count = len(anns_by_img.get(img_id, []))

        print(f"\n  {img_name} (GT: {gt_count} objects) -> {len(preds)} detections")
        # Show top 5 by confidence
        preds_sorted = sorted(preds, key=lambda x: -x["score"])
        for p in preds_sorted[:5]:
            cname = cat_map.get(p["category_id"], f"id={p['category_id']}")
            print(f"    conf={p['score']:.3f}  cat={p['category_id']:3d} ({cname})  bbox={p['bbox']}")
        if len(preds_sorted) > 5:
            print(f"    ... and {len(preds_sorted)-5} more")
