"""Sweep WBF thresholds against training GT using mAP@0.5 (detection + classification)."""
import json
import numpy as np
from pathlib import Path
from PIL import Image
import onnxruntime as ort
from ensemble_boxes import weighted_boxes_fusion
from itertools import product

BASE = Path(r"C:\Users\light\Documents\ntnu\NM-AI-2026\task3-NorgesGruppen")
SUBMISSION = BASE / "submission"
IMAGES_DIR = BASE / "data" / "NM_NGD_coco_dataset" / "train" / "images"
ANNOT_FILE = BASE / "data" / "NM_NGD_coco_dataset" / "train" / "annotations.json"

MODELS = [
    ("best.onnx", 1280),
    ("best1.onnx", 1280),
    ("last_int8.onnx", 800),
]

# Use a random subset for speed
NUM_EVAL_IMAGES = 20
SEED = 42

# Sweep ranges
CONF_THRESHOLDS = [0.05, 0.10, 0.15, 0.20, 0.25]
WBF_IOU_THRESHOLDS = [0.40, 0.45, 0.50, 0.55, 0.60, 0.65]
WBF_SKIP_THRESHOLDS = [0.001, 0.01, 0.05]

def preprocess(img, img_size):
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


def decode_detections(output, orig_w, orig_h, scale, pad_w, pad_h, conf_thresh):
    dets = output[0]
    boxes, scores, labels = [], [], []
    for det in dets:
        x1, y1, x2, y2, conf, cls_id = det
        if conf < conf_thresh:
            continue
        x1 = (x1 - pad_w) / scale
        y1 = (y1 - pad_h) / scale
        x2 = (x2 - pad_w) / scale
        y2 = (y2 - pad_h) / scale
        x1 = max(0.0, min(float(x1), orig_w))
        y1 = max(0.0, min(float(y1), orig_h))
        x2 = max(0.0, min(float(x2), orig_w))
        y2 = max(0.0, min(float(y2), orig_h))
        if x2 - x1 < 1 or y2 - y1 < 1:
            continue
        boxes.append([x1 / orig_w, y1 / orig_h, x2 / orig_w, y2 / orig_h])
        scores.append(float(conf))
        labels.append(int(cls_id))
    return boxes, scores, labels


def compute_iou(box_a, box_b):
    x1 = max(box_a[0], box_b[0])
    y1 = max(box_a[1], box_b[1])
    x2 = min(box_a[2], box_b[2])
    y2 = min(box_a[3], box_b[3])
    inter = max(0, x2 - x1) * max(0, y2 - y1)
    area_a = (box_a[2] - box_a[0]) * (box_a[3] - box_a[1])
    area_b = (box_b[2] - box_b[0]) * (box_b[3] - box_b[1])
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0


def compute_ap(scores, matched, n_gt):
    """Compute AP for a single class/image set."""
    if n_gt == 0:
        return 0.0
    order = np.argsort(-np.array(scores))
    matched = np.array(matched, dtype=bool)[order]
    tp = np.cumsum(matched)
    fp = np.cumsum(~matched)
    recall = tp / n_gt
    precision = tp / (tp + fp)
    # 11-point interpolation
    ap = 0.0
    for t in np.arange(0, 1.1, 0.1):
        p = precision[recall >= t]
        ap += (p.max() if len(p) > 0 else 0.0)
    return ap / 11.0


def evaluate(preds_by_img, gt_by_img, check_class=False):
    """Compute mAP@0.5 across images."""
    aps = []
    for img_id in gt_by_img:
        gt_boxes = gt_by_img[img_id]
        preds = preds_by_img.get(img_id, [])
        if len(gt_boxes) == 0 and len(preds) == 0:
            continue
        if len(gt_boxes) == 0:
            continue

        # Sort preds by score desc
        preds = sorted(preds, key=lambda x: -x["score"])
        matched_gt = [False] * len(gt_boxes)
        scores = []
        matched = []

        for p in preds:
            best_iou = 0
            best_j = -1
            for j, gt in enumerate(gt_boxes):
                if matched_gt[j]:
                    continue
                iou = compute_iou(
                    [p["bbox"][0], p["bbox"][1], p["bbox"][0] + p["bbox"][2], p["bbox"][1] + p["bbox"][3]],
                    [gt["bbox"][0], gt["bbox"][1], gt["bbox"][0] + gt["bbox"][2], gt["bbox"][1] + gt["bbox"][3]],
                )
                if iou > best_iou:
                    best_iou = iou
                    best_j = j
            scores.append(p["score"])
            if best_iou >= 0.5 and best_j >= 0:
                if check_class:
                    if p["category_id"] == gt_boxes[best_j]["category_id"]:
                        matched.append(True)
                        matched_gt[best_j] = True
                    else:
                        matched.append(False)
                else:
                    matched.append(True)
                    matched_gt[best_j] = True
            else:
                matched.append(False)

        ap = compute_ap(scores, matched, len(gt_boxes))
        aps.append(ap)

    return np.mean(aps) if aps else 0.0


def main():
    # Load GT
    with open(ANNOT_FILE, "r", encoding="utf-8") as f:
        coco = json.load(f)

    img_id_map = {img["file_name"]: img["id"] for img in coco["images"]}
    gt_by_img = {}
    for ann in coco["annotations"]:
        gt_by_img.setdefault(ann["image_id"], []).append(ann)

    # Pick eval images (with most annotations for informative eval)
    all_images = sorted(coco["images"], key=lambda x: len(gt_by_img.get(x["id"], [])), reverse=True)
    np.random.seed(SEED)
    eval_images = all_images[:NUM_EVAL_IMAGES]
    print(f"Evaluating on {len(eval_images)} images")

    # Load models
    providers = ["CPUExecutionProvider"]
    sessions = []
    for mf, _ in MODELS:
        sess = ort.InferenceSession(str(SUBMISSION / mf), providers=providers)
        sessions.append(sess)
    input_names = [s.get_inputs()[0].name for s in sessions]

    # Pre-compute all model outputs for all images at lowest conf threshold
    min_conf = min(CONF_THRESHOLDS)
    print(f"Running inference on {len(eval_images)} images with {len(MODELS)} models...")
    raw_outputs = {}  # img_id -> list of (output, orig_w, orig_h, scale, pad_w, pad_h) per model
    for i, img_info in enumerate(eval_images):
        fname = img_info["file_name"]
        img_id = img_info["id"]
        img = Image.open(IMAGES_DIR / fname).convert("RGB")
        orig_w, orig_h = img.size
        model_results = []
        for (mf, img_size), sess, inp_name in zip(MODELS, sessions, input_names):
            arr, scale, pad_w, pad_h = preprocess(img, img_size)
            output = sess.run(None, {inp_name: arr})
            model_results.append((output[0], orig_w, orig_h, scale, pad_w, pad_h))
        raw_outputs[img_id] = model_results
        if (i + 1) % 5 == 0:
            print(f"  {i+1}/{len(eval_images)} done")

    print(f"\nSweeping {len(CONF_THRESHOLDS)} x {len(WBF_IOU_THRESHOLDS)} x {len(WBF_SKIP_THRESHOLDS)} = "
          f"{len(CONF_THRESHOLDS)*len(WBF_IOU_THRESHOLDS)*len(WBF_SKIP_THRESHOLDS)} combinations...\n")

    best_score = 0
    best_params = None
    results = []

    for conf_t, wbf_iou, wbf_skip in product(CONF_THRESHOLDS, WBF_IOU_THRESHOLDS, WBF_SKIP_THRESHOLDS):
        preds_by_img = {}
        for img_info in eval_images:
            img_id = img_info["id"]
            model_results = raw_outputs[img_id]

            all_boxes, all_scores, all_labels = [], [], []
            for output, orig_w, orig_h, scale, pad_w, pad_h in model_results:
                boxes, scores, labels = decode_detections(
                    output, orig_w, orig_h, scale, pad_w, pad_h, conf_t
                )
                all_boxes.append(boxes)
                all_scores.append(scores)
                all_labels.append(labels)

            if any(len(b) > 0 for b in all_boxes):
                fused_boxes, fused_scores, fused_labels = weighted_boxes_fusion(
                    all_boxes, all_scores, all_labels,
                    iou_thr=wbf_iou, skip_box_thr=wbf_skip,
                )
            else:
                fused_boxes, fused_scores, fused_labels = [], [], []

            orig_w = model_results[0][1]
            orig_h = model_results[0][2]
            preds = []
            for box, score, label in zip(fused_boxes, fused_scores, fused_labels):
                x1 = float(box[0]) * orig_w
                y1 = float(box[1]) * orig_h
                x2 = float(box[2]) * orig_w
                y2 = float(box[3]) * orig_h
                preds.append({
                    "category_id": int(label),
                    "bbox": [x1, y1, x2 - x1, y2 - y1],
                    "score": float(score),
                })
            preds_by_img[img_id] = preds

        det_map = evaluate(preds_by_img, gt_by_img, check_class=False)
        cls_map = evaluate(preds_by_img, gt_by_img, check_class=True)
        combined = 0.7 * det_map + 0.3 * cls_map

        results.append((combined, det_map, cls_map, conf_t, wbf_iou, wbf_skip))
        if combined > best_score:
            best_score = combined
            best_params = (conf_t, wbf_iou, wbf_skip)

    # Sort and print top 10
    results.sort(reverse=True)
    print(f"{'Score':>7} {'Det':>6} {'Cls':>6} | {'Conf':>5} {'IoU':>5} {'Skip':>6}")
    print("-" * 50)
    for score, det, cls, conf_t, wbf_iou, wbf_skip in results[:15]:
        marker = " <-- BEST" if (conf_t, wbf_iou, wbf_skip) == best_params else ""
        print(f"{score:.4f} {det:.4f} {cls:.4f} | {conf_t:.2f}  {wbf_iou:.2f}  {wbf_skip:.3f}{marker}")

    print(f"\nBest: conf={best_params[0]}, wbf_iou={best_params[1]}, wbf_skip={best_params[2]} -> {best_score:.4f}")


if __name__ == "__main__":
    main()
