"""YOLOv8 training on NorgesGruppen COCO dataset.

Converts COCO annotations to YOLO format, then trains YOLOv8.
Pin ultralytics==8.1.0 to match the sandbox environment.
"""

import json
import random
import shutil
from pathlib import Path

import numpy as np
import torch
from ultralytics import YOLO

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
TASK_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = TASK_DIR / "data" / "raw" / "train"
OUTPUT_DIR = TASK_DIR / "data" / "processed" / "yolov8"
MODEL_OUTPUT = TASK_DIR / "models"
SEED = 42
VAL_RATIO = 0.1

# Training hyperparams
MODEL_SIZE = "yolov8n.pt"  # n/s/m/l/x
EPOCHS = 10
IMGSZ = 640
BATCH_SIZE = 16


def set_seed(seed=42):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


# ---------------------------------------------------------------------------
# COCO -> YOLO format conversion
# ---------------------------------------------------------------------------

def coco_to_yolo(data_dir: Path, output_dir: Path, val_ratio: float = 0.1, seed: int = 42):
    """Convert COCO annotations to YOLO format directory structure.

    Creates:
        output_dir/
        ├── images/
        │   ├── train/
        │   └── val/
        ├── labels/
        │   ├── train/
        │   └── val/
        └── dataset.yaml
    """
    with open(data_dir / "annotations.json", "r") as f:
        coco = json.load(f)

    images_dir = data_dir / "images"

    # Build lookup: image_id -> image info
    img_lookup = {img["id"]: img for img in coco["images"]}

    # Build lookup: image_id -> list of annotations
    anns_by_image = {}
    for ann in coco["annotations"]:
        anns_by_image.setdefault(ann["image_id"], []).append(ann)

    # Number of classes
    num_classes = len(coco["categories"])
    class_names = {cat["id"]: cat["name"] for cat in coco["categories"]}

    # Train/val split
    image_ids = list(img_lookup.keys())
    rng = random.Random(seed)
    rng.shuffle(image_ids)
    n_val = max(1, int(len(image_ids) * val_ratio))
    val_ids = set(image_ids[:n_val])
    train_ids = set(image_ids[n_val:])

    # Create output dirs
    for split in ("train", "val"):
        (output_dir / "images" / split).mkdir(parents=True, exist_ok=True)
        (output_dir / "labels" / split).mkdir(parents=True, exist_ok=True)

    # Convert annotations
    for img_id, img_info in img_lookup.items():
        split = "val" if img_id in val_ids else "train"
        w, h = img_info["width"], img_info["height"]
        fname = img_info["file_name"]
        stem = Path(fname).stem

        # Copy image
        src = images_dir / fname
        dst = output_dir / "images" / split / fname
        if not dst.exists():
            shutil.copy2(src, dst)

        # Write YOLO label file
        label_path = output_dir / "labels" / split / f"{stem}.txt"
        lines = []
        for ann in anns_by_image.get(img_id, []):
            if ann.get("iscrowd", 0):
                continue
            bx, by, bw, bh = ann["bbox"]
            # YOLO format: class cx cy w h (all normalized 0-1)
            cx = (bx + bw / 2) / w
            cy = (by + bh / 2) / h
            nw = bw / w
            nh = bh / h
            # Clamp to [0, 1]
            cx = max(0, min(1, cx))
            cy = max(0, min(1, cy))
            nw = max(0, min(1, nw))
            nh = max(0, min(1, nh))
            lines.append(f"{ann['category_id']} {cx:.6f} {cy:.6f} {nw:.6f} {nh:.6f}")

        label_path.write_text("\n".join(lines))

    # Write dataset.yaml
    yaml_content = f"""path: {output_dir.resolve()}
train: images/train
val: images/val

nc: {num_classes}
names:
"""
    for i in range(num_classes):
        name = class_names.get(i, f"class_{i}")
        yaml_content += f'  {i}: "{name}"\n'

    yaml_path = output_dir / "dataset.yaml"
    yaml_path.write_text(yaml_content)

    print(f"Converted {len(train_ids)} train + {len(val_ids)} val images")
    print(f"Classes: {num_classes}")
    print(f"Dataset yaml: {yaml_path}")

    return yaml_path


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------

def train(dataset_yaml: Path):
    """Train YOLOv8 on the converted dataset."""
    set_seed(SEED)

    model = YOLO(MODEL_SIZE)

    results = model.train(
        data=str(dataset_yaml),
        epochs=EPOCHS,
        imgsz=IMGSZ,
        batch=BATCH_SIZE,
        device="0" if torch.cuda.is_available() else "cpu",
        project=str(OUTPUT_DIR / "runs"),
        name="train",
        exist_ok=True,
        seed=SEED,
        # Augmentation
        hsv_h=0.015,
        hsv_s=0.7,
        hsv_v=0.4,
        degrees=5.0,
        translate=0.1,
        scale=0.5,
        mosaic=1.0,
        mixup=0.1,
        # Save
        save=True,
        save_period=10,
        val=True,
    )

    # Copy best weights to models/
    best_pt = OUTPUT_DIR / "runs" / "train" / "weights" / "best.pt"
    if best_pt.exists():
        MODEL_OUTPUT.mkdir(parents=True, exist_ok=True)
        dst = MODEL_OUTPUT / "best.pt"
        shutil.copy2(best_pt, dst)
        print(f"\nBest model copied to {dst}")

    return results


if __name__ == "__main__":
    set_seed(SEED)

    print("Step 1: Converting COCO to YOLO format...")
    yaml_path = coco_to_yolo(DATA_DIR, OUTPUT_DIR, VAL_RATIO, SEED)

    print("\nStep 2: Training YOLOv8...")
    train(yaml_path)
