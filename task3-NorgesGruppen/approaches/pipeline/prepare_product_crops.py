"""Phase 0: Prepare product image crops with background removal.

Removes white backgrounds from studio product shots and saves as RGBA PNGs.
These crops are then used for copy-paste augmentation onto shelf images,
targeting rare classes with ≤5 annotations.

Two-tier background removal:
  1. White-background products (322/344): flood-fill from corners + morphological cleanup
  2. Non-white backgrounds (CUSTOM_* etc.): GrabCut with auto-init from edges

Usage:
    python prepare_product_crops.py [--output data/processed/product_crops]
"""

import argparse
import json
from collections import Counter
from pathlib import Path

import cv2
import numpy as np

from utils import TASK_DIR, load_annotations

PRODUCT_DIR = TASK_DIR / "data" / "raw" / "NGD Product Images"
METADATA = PRODUCT_DIR / "metadata.json"
DEFAULT_OUTPUT = TASK_DIR / "data" / "processed" / "product_crops"


def has_white_background(img: np.ndarray, threshold: int = 230) -> bool:
    """Check if image has a white/near-white background using corner pixels."""
    h, w = img.shape[:2]
    # Sample corner patches (more reliable than edge strips when product fills frame)
    m = max(3, min(h, w) // 15)
    corners = np.concatenate([
        img[:m, :m].reshape(-1, 3),
        img[:m, -m:].reshape(-1, 3),
        img[-m:, :m].reshape(-1, 3),
        img[-m:, -m:].reshape(-1, 3),
    ])
    return np.mean(corners > threshold) > 0.8


def remove_white_bg(img: np.ndarray, threshold: int = 235) -> np.ndarray:
    """Remove white background via flood-fill from corners.

    Returns BGRA image with transparent background.
    """
    h, w = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Create mask: white pixels = background candidate
    _, binary = cv2.threshold(gray, threshold, 255, cv2.THRESH_BINARY)

    # Flood fill from all 4 corners to find connected background
    bg_mask = np.zeros((h, w), dtype=np.uint8)

    for seed in [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)]:
        if binary[seed[1], seed[0]] == 255:
            temp_mask = np.zeros((h + 2, w + 2), dtype=np.uint8)
            cv2.floodFill(binary.copy(), temp_mask, seed, 128,
                          loDiff=20, upDiff=20)
            bg_mask |= temp_mask[1:-1, 1:-1]

    # Also threshold very white pixels as background
    white_mask = np.all(img > threshold, axis=2).astype(np.uint8) * 255
    bg_mask = cv2.bitwise_or(bg_mask, white_mask)

    # Morphological cleanup: close small holes in foreground, then open to remove noise
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    fg_mask = cv2.bitwise_not(bg_mask)
    fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_CLOSE, kernel, iterations=2)
    fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, kernel, iterations=1)

    # Slight blur on mask edges for smoother blending
    fg_mask = cv2.GaussianBlur(fg_mask, (3, 3), 0)

    # Compose BGRA
    bgra = cv2.cvtColor(img, cv2.COLOR_BGR2BGRA)
    bgra[:, :, 3] = fg_mask
    return bgra


def remove_bg_grabcut(img: np.ndarray) -> np.ndarray:
    """Remove background using GrabCut for non-white backgrounds.

    Initializes GrabCut assuming edges are background.
    """
    h, w = img.shape[:2]
    margin = max(5, min(h, w) // 10)

    # Initialize mask: edges = probable background, center = probable foreground
    mask = np.full((h, w), cv2.GC_PR_BGD, dtype=np.uint8)
    mask[margin:h - margin, margin:w - margin] = cv2.GC_PR_FGD

    bgd_model = np.zeros((1, 65), np.float64)
    fgd_model = np.zeros((1, 65), np.float64)

    try:
        cv2.grabCut(img, mask, None, bgd_model, fgd_model, 5, cv2.GC_INIT_WITH_MASK)
    except cv2.error:
        # GrabCut failed — return with full opacity (no bg removal)
        bgra = cv2.cvtColor(img, cv2.COLOR_BGR2BGRA)
        bgra[:, :, 3] = 255
        return bgra

    fg_mask = np.where((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 255, 0).astype(np.uint8)

    # Cleanup
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_CLOSE, kernel, iterations=2)
    fg_mask = cv2.GaussianBlur(fg_mask, (3, 3), 0)

    bgra = cv2.cvtColor(img, cv2.COLOR_BGR2BGRA)
    bgra[:, :, 3] = fg_mask
    return bgra


def crop_to_content(bgra: np.ndarray, padding: int = 2) -> np.ndarray:
    """Crop BGRA image to its non-transparent bounding box."""
    alpha = bgra[:, :, 3]
    rows = np.any(alpha > 0, axis=1)
    cols = np.any(alpha > 0, axis=0)

    if not rows.any() or not cols.any():
        return bgra

    rmin, rmax = np.where(rows)[0][[0, -1]]
    cmin, cmax = np.where(cols)[0][[0, -1]]

    # Add padding
    h, w = bgra.shape[:2]
    rmin = max(0, rmin - padding)
    rmax = min(h, rmax + padding + 1)
    cmin = max(0, cmin - padding)
    cmax = min(w, cmax + padding + 1)

    return bgra[rmin:rmax, cmin:cmax]


def build_product_to_category_map() -> dict[str, int]:
    """Map product_code (folder name) → category_id via metadata.json."""
    coco = load_annotations()
    cat_by_name = {c["name"]: c["id"] for c in coco["categories"]}

    with open(METADATA) as f:
        meta = json.load(f)

    mapping = {}
    for prod in meta["products"]:
        pname = prod["product_name"]
        if pname in cat_by_name:
            mapping[str(prod["product_code"])] = cat_by_name[pname]

    return mapping


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--only-rare", action="store_true",
                        help="Only process products for rare classes (≤10 annotations)")
    parser.add_argument("--rare-threshold", type=int, default=10)
    args = parser.parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Build mapping
    prod_to_cat = build_product_to_category_map()
    print(f"Product → category mapping: {len(prod_to_cat)} products")

    # Annotation counts per category
    coco = load_annotations()
    ann_counts = Counter(a["category_id"] for a in coco["annotations"])

    if args.only_rare:
        rare_cats = {c for c, n in ann_counts.items() if n <= args.rare_threshold}
        print(f"Filtering to rare classes (≤{args.rare_threshold} ann): {len(rare_cats)} classes")
    else:
        rare_cats = None

    # Preferred image types: front view is most similar to shelf appearance
    preferred_types = ["front", "main", "left", "right"]

    processed = 0
    skipped = 0
    failed = 0

    for prod_code, cat_id in sorted(prod_to_cat.items()):
        if rare_cats is not None and cat_id not in rare_cats:
            skipped += 1
            continue

        prod_path = PRODUCT_DIR / prod_code
        if not prod_path.is_dir():
            continue

        # Find best image
        for img_type in preferred_types:
            img_file = prod_path / f"{img_type}.jpg"
            if img_file.exists():
                break
        else:
            # Take any available image
            jpgs = list(prod_path.glob("*.jpg"))
            if not jpgs:
                continue
            img_file = jpgs[0]
            img_type = img_file.stem

        # Process
        img = cv2.imread(str(img_file))
        if img is None:
            failed += 1
            continue

        if has_white_background(img):
            bgra = remove_white_bg(img)
        else:
            bgra = remove_bg_grabcut(img)

        bgra = crop_to_content(bgra)

        # Check that we actually have meaningful content
        alpha = bgra[:, :, 3]
        if alpha.mean() < 10:  # almost entirely transparent
            failed += 1
            continue

        # Save as category_id for easy lookup during training
        out_path = output_dir / f"cat{cat_id}_{prod_code}_{img_type}.png"
        cv2.imwrite(str(out_path), bgra)
        processed += 1

    print(f"\nProcessed: {processed}, Skipped: {skipped}, Failed: {failed}")
    print(f"Crops saved to {output_dir}")

    # Save a manifest for the copy-paste augmentation
    manifest = {}
    for png in sorted(output_dir.glob("*.png")):
        parts = png.stem.split("_")
        cat_id = int(parts[0].replace("cat", ""))
        manifest.setdefault(cat_id, []).append(png.name)

    with open(output_dir / "manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"Manifest: {len(manifest)} categories with crops")


if __name__ == "__main__":
    main()
