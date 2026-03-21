"""
Quick test: generate a few synthetic images and save side-by-side previews.

Outputs to data/placement_preview/ with:
  - {stem}_empty.jpg        — the empty shelf input
  - {stem}_synthetic.jpg    — products placed on the shelf
  - {stem}_debug.jpg        — synthetic + bounding boxes + shelf rows drawn
"""

import random
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw

from generate_synthetic import (
    load_data,
    build_category_mapping,
    prepare_cutouts,
    compute_sampling_weights,
    detect_shelf_rows,
    detect_shelf_bounds,
    generate_variant,
    EMPTY_SHELVES_DIR,
)

ROOT = Path(__file__).resolve().parent
COCO_DIR = ROOT / "data" / "NM_NGD_coco_dataset" / "train"
PREVIEW_DIR = ROOT / "data" / "placement_preview"
NUM_TEST = 5


def draw_debug(img, annotations, shelf_rows, shelf_bounds, cat_id_to_name):
    """Draw bounding boxes, shelf rows, and shelf bounds on image."""
    draw = ImageDraw.Draw(img)

    # Draw shelf unit bounds in red
    bx1, by1, bx2, by2 = shelf_bounds
    draw.rectangle([bx1, by1, bx2, by2], outline="red", width=3)

    # Draw shelf rows in blue
    for row in shelf_rows:
        y = row["y"]
        draw.rectangle([row["x_left"], y, row["x_right"], y + row["strip_h"]],
                       outline="blue", width=2)

    # Draw product bboxes in green with category label
    for ann in annotations:
        x, y, w, h = ann["bbox"]
        cid = ann["category_id"]
        name = cat_id_to_name.get(cid, f"cat{cid}")
        label = name[:20]
        draw.rectangle([x, y, x + w, y + h], outline="lime", width=2)
        draw.text((x + 2, y + 2), label, fill="lime")

    return img


def main():
    random.seed(42)
    np.random.seed(42)

    print("Loading data...")
    coco, meta = load_data()
    cat_to_images = build_category_mapping(coco, meta)
    cat_to_cutouts = prepare_cutouts(cat_to_images)
    sampling_weights = compute_sampling_weights(coco, cat_to_cutouts)
    cat_id_to_name = {c["id"]: c["name"] for c in coco["categories"]}
    img_entry_map = {Path(im["file_name"]).stem: im for im in coco["images"]}

    empty_paths = sorted(EMPTY_SHELVES_DIR.iterdir())[:NUM_TEST]
    print(f"Testing on {len(empty_paths)} empty shelves\n")

    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)

    for empty_path in empty_paths:
        stem = empty_path.stem
        print(f"--- {stem} ---")

        im_entry = img_entry_map.get(stem)
        if im_entry:
            orig_w, orig_h = im_entry["width"], im_entry["height"]
        else:
            tmp = Image.open(empty_path)
            orig_w, orig_h = tmp.size
            tmp.close()

        empty_shelf = Image.open(empty_path).convert("RGB")
        empty_shelf = empty_shelf.resize((orig_w, orig_h), Image.LANCZOS)

        # Detect shelf structure
        empty_cv = cv2.cvtColor(np.array(empty_shelf), cv2.COLOR_RGB2BGR)
        shelf_rows = detect_shelf_rows(empty_cv)
        print(f"  Shelf rows detected: {len(shelf_rows)}")
        for i, row in enumerate(shelf_rows):
            print(f"    Row {i}: y={row['y']}, x=[{row['x_left']}-{row['x_right']}], h={row['strip_h']}")

        if not shelf_rows:
            print("  Skipping (no shelf rows)")
            continue

        shelf_bounds = detect_shelf_bounds(shelf_rows, orig_w, orig_h)
        print(f"  Shelf bounds: {shelf_bounds}")

        # Generate one variant
        synth_img, annotations = generate_variant(
            empty_shelf, shelf_rows, shelf_bounds,
            cat_to_cutouts, sampling_weights
        )
        print(f"  Products placed: {len(annotations)}")

        # Save
        empty_shelf.save(PREVIEW_DIR / f"{stem}_empty.jpg", quality=90)
        synth_img.save(PREVIEW_DIR / f"{stem}_synthetic.jpg", quality=90)
        debug_img = draw_debug(synth_img.copy(), annotations, shelf_rows,
                               shelf_bounds, cat_id_to_name)
        debug_img.save(PREVIEW_DIR / f"{stem}_debug.jpg", quality=90)

        print(f"  Saved to {PREVIEW_DIR}/")

    print(f"\nDone! Check {PREVIEW_DIR} for results.")


if __name__ == "__main__":
    main()
