"""
Compare model combinations with and without TTA on training images.
TTA: original + horizontal flip, merged via WBF.
"""
# Add torch CUDA DLLs to PATH before importing onnxruntime
import os
_torch_lib = os.path.join(os.path.dirname(__file__), ".venv313", "Lib", "site-packages", "torch", "lib")
if os.path.isdir(_torch_lib):
    os.add_dll_directory(_torch_lib)
    os.environ["PATH"] = _torch_lib + os.pathsep + os.environ.get("PATH", "")

import json
import numpy as np
from pathlib import Path
from PIL import Image, ImageOps
import onnxruntime as ort
from ensemble_boxes import weighted_boxes_fusion
from itertools import combinations

BASE = Path(r"C:\Users\light\Documents\ntnu\NM-AI-2026\task3-NorgesGruppen")
IMAGES_DIR = BASE / "data" / "NM_NGD_coco_dataset" / "train" / "images"
ANNOT_FILE = BASE / "data" / "NM_NGD_coco_dataset" / "train" / "annotations.json"

ALL_MODELS = {
    "best":       (BASE / "best.onnx",               1280),
    "best1":      (BASE / "best1.onnx",              1280),
    "last":       (BASE / "models" / "last.onnx",    800),
    "best_final": (BASE / "models" / "best_final.onnx", 800),
    "sunday99":   (BASE / "models_sunday99" / "models" / "last.onnx", 800),
    "epoch140":   (BASE / "models_epoch140freeze" / "models" / "last.onnx", 800),
}

NUM_EVAL_IMAGES = 20
SEED = 42
CONF_THRESH = 0.05
WBF_IOU = 0.40
WBF_SKIP = 0.05


def letterbox(img, img_size):
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


def decode(output, orig_w, orig_h, scale, pad_w, pad_h, flipped=False):
    dets = output[0]
    boxes, scores, labels = [], [], []
    for det in dets:
        x1, y1, x2, y2, conf, cls_id = det
        if conf < CONF_THRESH:
            continue
        x1 = (x1 - pad_w) / scale
        y1 = (y1 - pad_h) / scale
        x2 = (x2 - pad_w) / scale
        y2 = (y2 - pad_h) / scale
        if flipped:
            x1, x2 = orig_w - x2, orig_w - x1
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


def run_model(session, inp_name, img, img_size, orig_w, orig_h, use_tta=False):
    """Run model with optional TTA. Returns list of (boxes, scores, labels) per augmentation."""
    results = []

    # Original
    arr, scale, pad_w, pad_h = letterbox(img, img_size)
    output = session.run(None, {inp_name: arr})
    results.append(decode(output[0], orig_w, orig_h, scale, pad_w, pad_h))

    if use_tta:
        # Horizontal flip
        img_flip = ImageOps.mirror(img)
        arr_f, scale_f, pad_w_f, pad_h_f = letterbox(img_flip, img_size)
        output_f = session.run(None, {inp_name: arr_f})
        results.append(decode(output_f[0], orig_w, orig_h, scale_f, pad_w_f, pad_h_f, flipped=True))

    return results


def compute_ap(scores, matched, n_gt):
    if n_gt == 0:
        return 0.0
    order = np.argsort(-np.array(scores))
    matched = np.array(matched, dtype=bool)[order]
    tp = np.cumsum(matched)
    fp = np.cumsum(~matched)
    recall = tp / n_gt
    precision = tp / (tp + fp)
    ap = 0.0
    for t in np.arange(0, 1.1, 0.1):
        p = precision[recall >= t]
        ap += (p.max() if len(p) > 0 else 0.0)
    return ap / 11.0


def evaluate(preds_by_img, gt_by_img, check_class=False):
    aps = []
    for img_id in gt_by_img:
        gt_boxes = gt_by_img[img_id]
        preds = preds_by_img.get(img_id, [])
        if len(gt_boxes) == 0:
            continue
        preds = sorted(preds, key=lambda x: -x["score"])
        matched_gt = [False] * len(gt_boxes)
        scores, matched = [], []
        for p in preds:
            best_iou, best_j = 0, -1
            for j, gt in enumerate(gt_boxes):
                if matched_gt[j]:
                    continue
                ix1 = max(p["bbox"][0], gt["bbox"][0])
                iy1 = max(p["bbox"][1], gt["bbox"][1])
                ix2 = min(p["bbox"][0] + p["bbox"][2], gt["bbox"][0] + gt["bbox"][2])
                iy2 = min(p["bbox"][1] + p["bbox"][3], gt["bbox"][1] + gt["bbox"][3])
                inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
                area_p = p["bbox"][2] * p["bbox"][3]
                area_g = gt["bbox"][2] * gt["bbox"][3]
                iou = inter / (area_p + area_g - inter) if (area_p + area_g - inter) > 0 else 0
                if iou > best_iou:
                    best_iou = iou
                    best_j = j
            scores.append(p["score"])
            if best_iou >= 0.5 and best_j >= 0:
                if check_class and p["category_id"] != gt_boxes[best_j]["category_id"]:
                    matched.append(False)
                else:
                    matched.append(True)
                    matched_gt[best_j] = True
            else:
                matched.append(False)
        aps.append(compute_ap(scores, matched, len(gt_boxes)))
    return np.mean(aps) if aps else 0.0


def main():
    # Load GT
    with open(ANNOT_FILE, "r", encoding="utf-8") as f:
        coco = json.load(f)
    gt_by_img = {}
    for ann in coco["annotations"]:
        gt_by_img.setdefault(ann["image_id"], []).append(ann)

    # Pick diverse eval images (mix of dense and sparse)
    all_images = sorted(coco["images"], key=lambda x: len(gt_by_img.get(x["id"], [])), reverse=True)
    np.random.seed(SEED)
    eval_images = all_images[:NUM_EVAL_IMAGES]
    print(f"Evaluating on {len(eval_images)} images\n")

    # Load all model sessions
    sessions = {}
    for name, (path, img_size) in ALL_MODELS.items():
        print(f"Loading {name} ({path.name})...")
        sess = ort.InferenceSession(str(path), providers=["CPUExecutionProvider"])
        inp_name = sess.get_inputs()[0].name
        sessions[name] = (sess, inp_name, img_size)

    # Pre-run all models on all images (with TTA)
    import time
    t_start = time.time()
    print("\nRunning inference...")
    # raw[model_name][img_id] = list of (boxes, scores, labels) per augmentation
    raw = {name: {} for name in ALL_MODELS}
    for i, img_info in enumerate(eval_images):
        img = Image.open(IMAGES_DIR / img_info["file_name"]).convert("RGB")
        orig_w, orig_h = img.size
        img_id = img_info["id"]
        for name, (sess, inp_name, img_size) in sessions.items():
            raw[name][img_id] = {
                "orig_w": orig_w,
                "orig_h": orig_h,
                "results": run_model(sess, inp_name, img, img_size, orig_w, orig_h, use_tta=True),
            }
        if (i + 1) % 5 == 0:
            elapsed = time.time() - t_start
            eta = elapsed / (i + 1) * (len(eval_images) - i - 1)
            print(f"  {i+1}/{len(eval_images)} ({elapsed:.0f}s elapsed, ~{eta:.0f}s remaining)")

    # Define combinations to test
    model_names = list(ALL_MODELS.keys())
    combos = []
    # All singles (with and without TTA)
    for name in model_names:
        combos.append(([name], False, f"{name}"))
        combos.append(([name], True, f"{name}+TTA"))
    # All pairs (with and without TTA)
    for a, b in combinations(model_names, 2):
        combos.append(([a, b], False, f"{a}+{b}"))
        combos.append(([a, b], True, f"{a}+{b}+TTA"))
    # Best triples: mix 1280 + 800 models
    for a, b, c in combinations(model_names, 3):
        combos.append(([a, b, c], False, f"{a}+{b}+{c}"))
        combos.append(([a, b, c], True, f"{a}+{b}+{c}+TTA"))
    # All 800 models
    all_800 = ["last", "best_final", "sunday99", "epoch140"]
    combos.append((all_800, False, "all_800"))
    combos.append((all_800, True, "all_800+TTA"))
    # Best 1280 + all 800
    combos.append((["best1"] + all_800, False, "best1+all_800"))
    combos.append((["best1"] + all_800, True, "best1+all_800+TTA"))
    # All 6
    combos.append((model_names, False, "all6"))
    combos.append((model_names, True, "all6+TTA"))

    print(f"\nTesting {len(combos)} combinations...\n")

    results = []
    for model_list, use_tta, label in combos:
        preds_by_img = {}
        for img_info in eval_images:
            img_id = img_info["id"]
            all_boxes, all_scores, all_labels = [], [], []

            for name in model_list:
                aug_results = raw[name][img_id]["results"]
                # Always include original (index 0)
                b, s, l = aug_results[0]
                all_boxes.append(b)
                all_scores.append(s)
                all_labels.append(l)
                # Include TTA augmentations (index 1+)
                if use_tta:
                    for aug_idx in range(1, len(aug_results)):
                        b, s, l = aug_results[aug_idx]
                        all_boxes.append(b)
                        all_scores.append(s)
                        all_labels.append(l)

            orig_w = raw[model_list[0]][img_id]["orig_w"]
            orig_h = raw[model_list[0]][img_id]["orig_h"]

            if any(len(b) > 0 for b in all_boxes):
                fused_boxes, fused_scores, fused_labels = weighted_boxes_fusion(
                    all_boxes, all_scores, all_labels,
                    iou_thr=WBF_IOU, skip_box_thr=WBF_SKIP,
                )
            else:
                fused_boxes, fused_scores, fused_labels = [], [], []

            preds = []
            for box, score, label_id in zip(fused_boxes, fused_scores, fused_labels):
                x1 = float(box[0]) * orig_w
                y1 = float(box[1]) * orig_h
                x2 = float(box[2]) * orig_w
                y2 = float(box[3]) * orig_h
                preds.append({
                    "category_id": int(label_id),
                    "bbox": [x1, y1, x2 - x1, y2 - y1],
                    "score": float(score),
                })
            preds_by_img[img_id] = preds

        det_map = evaluate(preds_by_img, gt_by_img, check_class=False)
        cls_map = evaluate(preds_by_img, gt_by_img, check_class=True)
        combined = 0.7 * det_map + 0.3 * cls_map
        results.append((combined, det_map, cls_map, label))

    # Sort and print
    results.sort(reverse=True)
    print(f"{'Score':>7} {'Det':>6} {'Cls':>6} | Combination")
    print("-" * 55)
    for score, det, cls, label in results:
        print(f"{score:.4f} {det:.4f} {cls:.4f} | {label}")


if __name__ == "__main__":
    main()
