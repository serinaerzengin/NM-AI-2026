"""
Offline augmentation of original training images with COCO bbox transforms.

Creates ~9 augmented variants per original image (~2200 total) to match
the synthetic data volume. Saves augmented images and merged annotations.

Requires: pip install albumentations
"""

import json
import random
import shutil
from pathlib import Path

import albumentations as A
import cv2
import numpy as np

# ── Config ───────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent
COCO_DIR = ROOT / "data" / "NM_NGD_coco_dataset" / "train"
ANNOTATIONS_FILE = COCO_DIR / "annotations.json"
IMAGES_DIR = COCO_DIR / "images"

VARIANTS_PER_IMAGE = 9       # ~248 * 9 = 2232 augmented images
SEED = 42

random.seed(SEED)
np.random.seed(SEED)

# ── Augmentation Pipeline ────────────────────────────────────────────────

def build_transform():
    """Build augmentation pipeline with bbox-safe transforms."""
    return A.Compose([
        # Geometric
        A.HorizontalFlip(p=0.5),
        A.Affine(
            scale=(0.8, 1.2),
            rotate=(-5, 5),
            shear=(-2, 2),
            p=0.7,
        ),
        A.RandomCrop(
            p=0.3,
            width=1.0,   # placeholder, overridden per-image
            height=1.0,
        ) if False else A.NoOp(),  # skip random crop, use RandomResizedCrop instead
        A.RandomResizedCrop(
            size=(1, 1),  # placeholder, overridden per-image
            scale=(0.7, 1.0),
            ratio=(0.9, 1.1),
            p=0.3,
        ) if False else A.NoOp(),

        # Color
        A.ColorJitter(
            brightness=0.3,
            contrast=0.2,
            saturation=0.3,   # conservative — need color to distinguish products
            hue=0.03,
            p=0.8,
        ),
        A.RandomBrightnessContrast(
            brightness_limit=0.15,
            contrast_limit=0.15,
            p=0.5,
        ),
        A.HueSaturationValue(
            hue_shift_limit=5,
            sat_shift_limit=30,
            val_shift_limit=30,
            p=0.5,
        ),

        # Noise / blur
        A.OneOf([
            A.GaussianBlur(blur_limit=(3, 5), p=1.0),
            A.GaussNoise(std_range=(0.01, 0.03), p=1.0),
        ], p=0.3),

        # Occlusion simulation
        A.CoarseDropout(
            num_holes_range=(1, 5),
            hole_height_range=(0.02, 0.08),
            hole_width_range=(0.02, 0.08),
            fill=0,
            p=0.2,
        ),
    ],
        bbox_params=A.BboxParams(
            format="coco",  # [x, y, width, height]
            min_area=100,
            min_visibility=0.3,
            label_fields=["category_ids"],
        ),
    )


# ── Main ─────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("Offline Augmentation of Original Training Images")
    print("=" * 60)

    # Load annotations
    print("\nLoading annotations...")
    with open(ANNOTATIONS_FILE, "r", encoding="utf-8") as f:
        coco = json.load(f)

    # Build lookup maps
    img_id_to_entry = {im["id"]: im for im in coco["images"]}
    img_id_to_anns = {}
    for ann in coco["annotations"]:
        img_id_to_anns.setdefault(ann["image_id"], []).append(ann)

    # Only augment original images (not synthetic)
    original_images = [im for im in coco["images"]
                       if not im["file_name"].startswith("synth_")
                       and not im["file_name"].startswith("aug_")]
    print(f"Original images: {len(original_images)}")
    print(f"Variants per image: {VARIANTS_PER_IMAGE}")
    print(f"Total augmented images: {len(original_images) * VARIANTS_PER_IMAGE}")

    transform = build_transform()

    max_img_id = max(im["id"] for im in coco["images"])
    max_ann_id = max(a["id"] for a in coco["annotations"])

    aug_images = []
    aug_annotations = []
    img_count = 0

    for i, im_entry in enumerate(original_images):
        img_path = IMAGES_DIR / im_entry["file_name"]
        if not img_path.exists():
            print(f"  Warning: {img_path} not found, skipping")
            continue

        image = cv2.imread(str(img_path))
        if image is None:
            continue
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        # Get annotations for this image
        anns = img_id_to_anns.get(im_entry["id"], [])
        if not anns:
            continue

        bboxes = [a["bbox"] for a in anns]  # COCO format: [x, y, w, h]
        category_ids = [a["category_id"] for a in anns]

        for v in range(VARIANTS_PER_IMAGE):
            try:
                result = transform(
                    image=image,
                    bboxes=bboxes,
                    category_ids=category_ids,
                )
            except Exception:
                continue

            aug_image = result["image"]
            aug_bboxes = result["bboxes"]
            aug_cats = result["category_ids"]

            if len(aug_bboxes) == 0:
                continue

            img_count += 1
            img_id = max_img_id + img_count
            filename = f"aug_{img_count:05d}.jpg"

            # Save augmented image
            out_path = IMAGES_DIR / filename
            aug_bgr = cv2.cvtColor(aug_image, cv2.COLOR_RGB2BGR)
            cv2.imwrite(str(out_path), aug_bgr, [cv2.IMWRITE_JPEG_QUALITY, 90])

            h, w = aug_image.shape[:2]
            aug_images.append({
                "id": img_id,
                "file_name": filename,
                "width": w,
                "height": h,
            })

            for bbox, cat_id in zip(aug_bboxes, aug_cats):
                max_ann_id += 1
                x, y, bw, bh = bbox
                aug_annotations.append({
                    "id": max_ann_id,
                    "image_id": img_id,
                    "category_id": cat_id,
                    "bbox": [round(x, 1), round(y, 1), round(bw, 1), round(bh, 1)],
                    "area": round(bw * bh, 1),
                    "iscrowd": 0,
                })

        if (i + 1) % 25 == 0 or i == 0:
            print(f"  Processed {i+1}/{len(original_images)} images "
                  f"({img_count} augmented so far)")

    print(f"\nGenerated {img_count} augmented images "
          f"with {len(aug_annotations)} annotations")

    # Save augmented-only annotations
    aug_only = {
        "images": aug_images,
        "categories": coco["categories"],
        "annotations": aug_annotations,
    }
    aug_ann_path = COCO_DIR / "annotations_augmented.json"
    with open(aug_ann_path, "w", encoding="utf-8") as f:
        json.dump(aug_only, f, ensure_ascii=False)
    print(f"Saved augmented annotations to {aug_ann_path.name}")

    # Merge into main annotations
    backup_path = COCO_DIR / "annotations_original.json"
    if not backup_path.exists():
        shutil.copy2(ANNOTATIONS_FILE, backup_path)
        print(f"Backed up original annotations to {backup_path.name}")

    merged = {
        "images": coco["images"] + aug_images,
        "categories": coco["categories"],
        "annotations": coco["annotations"] + aug_annotations,
    }
    with open(ANNOTATIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False)
    print(f"Saved merged annotations to {ANNOTATIONS_FILE.name}")

    # Summary
    print("\n" + "=" * 60)
    print("Summary:")
    print(f"  Original: {len(coco['images'])} images, {len(coco['annotations'])} annotations")
    print(f"  Augmented: {len(aug_images)} images, {len(aug_annotations)} annotations")
    print(f"  Merged: {len(merged['images'])} images, {len(merged['annotations'])} annotations")
    print("=" * 60)


if __name__ == "__main__":
    main()
