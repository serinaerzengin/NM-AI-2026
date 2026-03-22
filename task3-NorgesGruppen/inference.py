"""
Inference script for DINOv2-DETR grocery detection model.
Runs on validation split images and saves visualizations with bounding boxes.
"""

import json
import os
import random
from pathlib import Path

import numpy as np
import torch
from PIL import Image, ImageDraw, ImageFont
from transformers import AutoImageProcessor, DetrForObjectDetection

# ── Config ──────────────────────────────────────────────────────────────
MODEL_DIR = "./outputs_dinov2_detr/best"
DATA_DIR = "./data/NM_NGD_coco_dataset/train"
OUTPUT_DIR = "./inference_results"
CONFIDENCE_THRESHOLD = 0.5
NUM_IMAGES = 10          # number of images to run inference on (None = all)
SEED = 42
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# ── Load model & processor ──────────────────────────────────────────────
print(f"Loading model from {MODEL_DIR} ...")
model = DetrForObjectDetection.from_pretrained(MODEL_DIR)
model.to(DEVICE).eval()

image_processor = AutoImageProcessor.from_pretrained(MODEL_DIR)

id2label = model.config.id2label
print(f"Model loaded: {len(id2label)} classes, device={DEVICE}")

# ── Load dataset info & pick validation images ──────────────────────────
with open(os.path.join(DATA_DIR, "annotations.json"), "r", encoding="utf-8") as f:
    coco = json.load(f)

images_dir = os.path.join(DATA_DIR, "images")
all_images = coco["images"]

# Reproduce the same val split as training
random.seed(SEED)
ids = list(range(len(all_images)))
random.shuffle(ids)
n_val = max(1, int(len(all_images) * 0.1))
val_ids = ids[:n_val]

val_images = [all_images[i] for i in val_ids]
if NUM_IMAGES is not None:
    val_images = val_images[:NUM_IMAGES]

print(f"Running inference on {len(val_images)} validation images ...")

# ── Build ground-truth lookup ───────────────────────────────────────────
anns_by_image = {}
for ann in coco["annotations"]:
    anns_by_image.setdefault(ann["image_id"], []).append(ann)

cat_ids = sorted(c["id"] for c in coco["categories"])
cat_id_to_label = {cid: i for i, cid in enumerate(cat_ids)}
cat_id_to_name = {c["id"]: c["name"] for c in coco["categories"]}

# ── Color palette ───────────────────────────────────────────────────────
rng = np.random.RandomState(42)
COLORS = [(int(r), int(g), int(b)) for r, g, b in rng.randint(60, 255, size=(400, 3))]


def draw_detections(image, boxes, scores, labels, id2label, colors, thickness=3):
    """Draw bounding boxes with labels on the image."""
    draw = ImageDraw.Draw(image)
    try:
        font = ImageFont.truetype("arial.ttf", 14)
    except OSError:
        font = ImageFont.load_default()

    for box, score, label in zip(boxes, scores, labels):
        label_id = int(label)
        color = colors[label_id % len(colors)]
        name = id2label.get(str(label_id), f"id={label_id}")
        text = f"{name} {score:.2f}"

        x0, y0, x1, y1 = [int(v) for v in box]
        draw.rectangle([x0, y0, x1, y1], outline=color, width=thickness)

        # text background
        bbox = draw.textbbox((x0, y0), text, font=font)
        draw.rectangle([bbox[0] - 1, bbox[1] - 1, bbox[2] + 1, bbox[3] + 1], fill=color)
        draw.text((x0, y0), text, fill="white", font=font)

    return image


def draw_ground_truth(image, anns, cat_id_to_name, colors, thickness=2):
    """Draw ground-truth boxes in a separate copy."""
    draw = ImageDraw.Draw(image)
    try:
        font = ImageFont.truetype("arial.ttf", 12)
    except OSError:
        font = ImageFont.load_default()

    for ann in anns:
        x, y, w, h = ann["bbox"]
        cat_name = cat_id_to_name.get(ann["category_id"], "?")
        label_idx = cat_id_to_label.get(ann["category_id"], 0)
        color = colors[label_idx % len(colors)]

        draw.rectangle([x, y, x + w, y + h], outline=color, width=thickness)
        draw.text((x, y - 12), cat_name, fill=color, font=font)

    return image


# ── Run inference ───────────────────────────────────────────────────────
os.makedirs(OUTPUT_DIR, exist_ok=True)

for img_info in val_images:
    fname = img_info["file_name"]
    img_id = img_info["id"]
    img_path = os.path.join(images_dir, fname)

    image = Image.open(img_path).convert("RGB")

    # Preprocess & forward
    inputs = image_processor(images=image, return_tensors="pt")
    inputs = {k: v.to(DEVICE) for k, v in inputs.items()}

    with torch.no_grad():
        outputs = model(**inputs)

    # Post-process
    target_sizes = torch.tensor([image.size[::-1]], device=DEVICE)  # (H, W)
    results = image_processor.post_process_object_detection(
        outputs, threshold=CONFIDENCE_THRESHOLD, target_sizes=target_sizes
    )[0]

    boxes = results["boxes"].cpu().numpy()
    scores = results["scores"].cpu().numpy()
    labels = results["labels"].cpu().numpy()

    print(f"  {fname}: {len(boxes)} detections (threshold={CONFIDENCE_THRESHOLD})")

    # Draw predictions
    pred_img = image.copy()
    pred_img = draw_detections(pred_img, boxes, scores, labels, id2label, COLORS)

    # Draw ground truth
    gt_img = image.copy()
    gt_anns = anns_by_image.get(img_id, [])
    gt_img = draw_ground_truth(gt_img, gt_anns, cat_id_to_name, COLORS)

    # Save side by side
    stem = Path(fname).stem
    pred_img.save(os.path.join(OUTPUT_DIR, f"{stem}_pred.jpg"))
    gt_img.save(os.path.join(OUTPUT_DIR, f"{stem}_gt.jpg"))

    # Also save a combined view
    total_w = pred_img.width + gt_img.width
    combined = Image.new("RGB", (total_w, max(pred_img.height, gt_img.height)))
    combined.paste(gt_img, (0, 0))
    combined.paste(pred_img, (gt_img.width, 0))
    combined.save(os.path.join(OUTPUT_DIR, f"{stem}_combined.jpg"))

print(f"\nDone! Results saved to {OUTPUT_DIR}/")
print(f"  *_pred.jpg     = model predictions")
print(f"  *_gt.jpg       = ground truth")
print(f"  *_combined.jpg = GT (left) | Pred (right)")
