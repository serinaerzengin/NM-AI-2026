"""
Synthetic data generation via bbox-swap augmentation for grocery shelf detection.

Uses existing COCO bounding boxes as placement slots: for each real training image,
loads a Gemini-generated empty shelf version, detects price tags to find shelf surfaces,
then pastes random product cutouts bottom-aligned above the price tags.
Oversamples rare categories via inverse-frequency weighting.
"""

import json
import random
import shutil
from collections import Counter, deque
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageFilter, ImageEnhance

# ── Config ───────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent
COCO_DIR = ROOT / "data" / "NM_NGD_coco_dataset" / "train"
PRODUCT_DIR = ROOT / "data" / "NM_NGD_product_images"
ANNOTATIONS_FILE = COCO_DIR / "annotations.json"
METADATA_FILE = PRODUCT_DIR / "metadata.json"
IMAGES_DIR = COCO_DIR / "images"
CUTOUT_CACHE = ROOT / "data" / "product_cutouts"
EMPTY_SHELVES_DIR = ROOT / "data" / "empty_shelves"

NUM_VARIANTS = 3             # synthetic variants per real image
ROTATION_RANGE = 5           # ±5 degrees
BRIGHTNESS_RANGE = 0.10      # ±10% brightness
BLUR_SIGMA = (0.3, 0.8)      # Gaussian blur range for pasted products
FLIP_PROB = 0.5               # probability of horizontal flip per product
OVERSAMPLE_CAP = 100          # max oversampling weight
SEED = 42

# Product sizing: fraction of image dimensions (from real data stats)
PROD_W_FRAC = (0.038, 0.080)  # p25-p75 of real bbox width / image width
PROD_H_FRAC = (0.049, 0.094)  # p25-p75 of real bbox height / image height
PROD_ASPECT = (0.67, 1.26)    # p25-p75 of real bbox aspect ratios (w/h)

# Placement tuning
GAP_BETWEEN_PRODUCTS = (1, 5)  # random px gap between product groups
SHELF_BOTTOM_MARGIN = 5       # px above shelf edge to place product bottom

random.seed(SEED)
np.random.seed(SEED)


# ── Data Loading ─────────────────────────────────────────────────────────

def load_data():
    """Load COCO annotations and product metadata."""
    with open(ANNOTATIONS_FILE, "r", encoding="utf-8") as f:
        coco = json.load(f)
    with open(METADATA_FILE, "r", encoding="utf-8") as f:
        meta = json.load(f)
    return coco, meta


def build_category_mapping(coco, meta):
    """Build category_id -> list of product image paths."""
    cat_to_images = {}
    matched = 0
    for cat in coco["categories"]:
        cid = cat["id"]
        prod_dir = PRODUCT_DIR / f"cat{cid}"
        if not prod_dir.exists():
            continue
        paths = []
        for img_type in ["front", "main"]:
            for ext in [".jpg", ".jpeg", ".png"]:
                p = prod_dir / f"{img_type}{ext}"
                if p.exists():
                    paths.append(p)
                    break
        if paths:
            cat_to_images[cid] = paths
            matched += 1

    print(f"Category mapping: {matched}/{len(coco['categories'])} categories have product images")
    return cat_to_images


# ── Background Removal ───────────────────────────────────────────────────

def remove_background(img):
    """Remove background via adaptive flood-fill from image edges.

    Samples border pixels to detect the background color, then flood-fills
    inward from all edges removing pixels within a color-distance threshold.
    Works on both light and dark solid backgrounds.
    """
    img = img.convert("RGB")
    arr = np.array(img, dtype=np.float32)
    h, w = arr.shape[:2]

    # Determine background color from border pixels
    border = np.concatenate([
        arr[0, :], arr[-1, :],
        arr[:, 0], arr[:, -1],
    ])
    bg_color = np.median(border, axis=0)

    # Pixels within this Euclidean distance of bg_color are considered background
    threshold = 50.0
    dist = np.sqrt(np.sum((arr - bg_color) ** 2, axis=2))
    is_bg = dist < threshold

    mask = np.ones((h, w), dtype=np.uint8) * 255
    visited = np.zeros((h, w), dtype=bool)
    queue = deque()

    # Seed from all border pixels that match background
    for x in range(w):
        for y in [0, h - 1]:
            if not visited[y, x] and is_bg[y, x]:
                visited[y, x] = True
                queue.append((y, x))
    for y in range(h):
        for x in [0, w - 1]:
            if not visited[y, x] and is_bg[y, x]:
                visited[y, x] = True
                queue.append((y, x))

    # 8-connectivity flood fill (crosses diagonal shadow lines)
    while queue:
        cy, cx = queue.popleft()
        mask[cy, cx] = 0
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dy == 0 and dx == 0:
                    continue
                ny, nx = cy + dy, cx + dx
                if 0 <= ny < h and 0 <= nx < w and not visited[ny, nx]:
                    visited[ny, nx] = True
                    if is_bg[ny, nx]:
                        queue.append((ny, nx))

    mask_img = Image.fromarray(mask)
    mask_img = mask_img.filter(ImageFilter.MaxFilter(3))
    mask_img = mask_img.filter(ImageFilter.MinFilter(3))
    mask_img = mask_img.filter(ImageFilter.GaussianBlur(radius=2))

    rgba = img.convert("RGBA")
    rgba.putalpha(mask_img)
    return rgba


def prepare_cutouts(cat_to_images):
    """Process product images: remove background and cache as RGBA PNGs."""
    CUTOUT_CACHE.mkdir(parents=True, exist_ok=True)
    cat_to_cutouts = {}

    total = sum(len(paths) for paths in cat_to_images.values())
    done = 0

    for cid, paths in cat_to_images.items():
        cutout_paths = []
        for p in paths:
            cache_name = f"cat{cid}_{p.stem}.png"
            cache_path = CUTOUT_CACHE / cache_name
            if cache_path.exists():
                cutout_paths.append(cache_path)
            else:
                try:
                    img = Image.open(p)
                    rgba = remove_background(img)
                    rgba.save(cache_path)
                    cutout_paths.append(cache_path)
                except Exception as e:
                    print(f"  Warning: failed to process {p}: {e}")
            done += 1
            if done % 50 == 0:
                print(f"  Processed {done}/{total} product images...")

        if cutout_paths:
            cat_to_cutouts[cid] = cutout_paths

    print(f"Prepared cutouts for {len(cat_to_cutouts)} categories")
    return cat_to_cutouts


# ── Sampling Weights ─────────────────────────────────────────────────────

def compute_sampling_weights(coco, cat_to_cutouts):
    """Compute inverse-frequency sampling weights for categories."""
    ann_counts = Counter(a["category_id"] for a in coco["annotations"])
    valid_cats = list(cat_to_cutouts.keys())
    cat_id_to_name = {c["id"]: c["name"] for c in coco["categories"]}

    counts = []
    for cid in valid_cats:
        name = cat_id_to_name.get(cid, "")
        if name != "unknown_product":
            counts.append(ann_counts.get(cid, 1))

    max_count = max(counts) if counts else 1

    weights = {}
    for cid in valid_cats:
        name = cat_id_to_name.get(cid, "")
        if name == "unknown_product":
            weights[cid] = 0.1
        else:
            count = ann_counts.get(cid, 1)
            weights[cid] = min(max_count / max(count, 1), OVERSAMPLE_CAP)

    total_w = sum(weights.values())
    for cid in weights:
        weights[cid] /= total_w

    return weights


# ── Shelf Structure Detection ────────────────────────────────────────────

def detect_shelf_rows(image_cv):
    """Detect shelf rows using horizontal edge detection.

    Finds strong horizontal edges (shelf surfaces) by analyzing the
    vertical gradient profile. Shelf edges appear as peaks in the
    row-summed horizontal gradient.

    Returns list of shelf rows sorted top-to-bottom, each row is a dict:
        {"y": int, "x_left": int, "x_right": int, "strip_h": int}
    where y is the shelf surface (product bottom rests here).
    """
    img_h, img_w = image_cv.shape[:2]
    gray = cv2.cvtColor(image_cv, cv2.COLOR_BGR2GRAY)

    # Compute vertical gradient (detects horizontal edges)
    sobel_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
    abs_grad = np.abs(sobel_y)

    # Sum gradient magnitude across each row
    row_profile = np.sum(abs_grad, axis=1)

    # Smooth the profile to reduce noise
    kernel_size = max(5, img_h // 100)
    if kernel_size % 2 == 0:
        kernel_size += 1
    from scipy.ndimage import uniform_filter1d
    row_profile_smooth = uniform_filter1d(row_profile, size=kernel_size)

    # Find peaks: rows with high horizontal gradient
    # Use 75th percentile to catch weaker bottom-shelf edges
    threshold = np.percentile(row_profile_smooth, 75)
    above = row_profile_smooth > threshold

    # Find contiguous regions above threshold
    regions = []
    in_region = False
    start = 0
    for y in range(len(above)):
        if above[y] and not in_region:
            start = y
            in_region = True
        elif not above[y] and in_region:
            regions.append((start, y))
            in_region = False
    if in_region:
        regions.append((start, len(above)))

    # Take the peak y of each region as the shelf edge
    min_gap = img_h * 0.06  # minimum spacing between shelf rows
    shelf_edges = []
    for start, end in regions:
        peak_y = start + np.argmax(row_profile_smooth[start:end])
        strip_h = end - start

        # Skip very thin noise or very thick regions (not shelf edges)
        if strip_h < 3 or strip_h > img_h * 0.08:
            continue

        # Skip if too close to a previous edge
        if shelf_edges and (peak_y - shelf_edges[-1]["y"]) < min_gap:
            # Keep the stronger one
            prev = shelf_edges[-1]
            if row_profile_smooth[peak_y] > row_profile_smooth[prev["y"]]:
                shelf_edges[-1] = {"y": peak_y, "strip_h": strip_h}
            continue

        shelf_edges.append({"y": peak_y, "strip_h": strip_h})

    # Skip edges in the very top 10% (ceiling/rails/signage) or bottom 3%
    shelf_edges = [e for e in shelf_edges
                   if img_h * 0.10 < e["y"] < img_h * 0.97]

    # Determine horizontal extent of each shelf edge
    # Use the gradient to find where the horizontal edge actually exists
    for edge in shelf_edges:
        y = edge["y"]
        y_start = max(0, y - 5)
        y_end = min(img_h, y + 5)
        row_slice = abs_grad[y_start:y_end]
        col_profile = np.max(row_slice, axis=0)
        edge_threshold = np.percentile(col_profile, 30)
        active_cols = col_profile > edge_threshold

        # Find leftmost and rightmost active columns
        active_indices = np.where(active_cols)[0]
        if len(active_indices) > 0:
            edge["x_left"] = int(active_indices[0])
            edge["x_right"] = int(active_indices[-1])
        else:
            edge["x_left"] = 0
            edge["x_right"] = img_w

    # Filter: edges should span at least 25% of image width
    min_width = img_w * 0.25
    shelf_edges = [e for e in shelf_edges
                   if (e["x_right"] - e["x_left"]) >= min_width]

    shelf_edges = sorted(shelf_edges, key=lambda r: r["y"])

    # Validate top row: if gap to row 1 is much larger than typical spacing,
    # it's likely a ceiling rail / signage edge, not a shelf
    if len(shelf_edges) >= 3:
        spacings = [shelf_edges[i+1]["y"] - shelf_edges[i]["y"]
                    for i in range(len(shelf_edges) - 1)]
        median_sp = np.median(spacings)
        top_gap = shelf_edges[1]["y"] - shelf_edges[0]["y"]
        if top_gap > median_sp * 1.8:
            shelf_edges = shelf_edges[1:]

    # Extrapolate missing rows below if spacing is regular
    if len(shelf_edges) >= 3:
        spacings = [shelf_edges[i+1]["y"] - shelf_edges[i]["y"]
                    for i in range(len(shelf_edges) - 1)]
        median_spacing = int(np.median(spacings))

        # Use the widest detected row as template for x-extents
        widest = max(shelf_edges, key=lambda e: e["x_right"] - e["x_left"])

        # Interpolate: fill large gaps between detected rows
        interpolated = []
        for i in range(len(shelf_edges) - 1):
            interpolated.append(shelf_edges[i])
            gap = shelf_edges[i+1]["y"] - shelf_edges[i]["y"]
            if gap > median_spacing * 1.6:
                num_insert = round(gap / median_spacing) - 1
                for j in range(1, num_insert + 1):
                    interp_y = shelf_edges[i]["y"] + int(j * gap / (num_insert + 1))
                    interpolated.append({
                        "y": interp_y,
                        "x_left": widest["x_left"],
                        "x_right": widest["x_right"],
                        "strip_h": 10,
                    })
        interpolated.append(shelf_edges[-1])
        shelf_edges = interpolated

        # Extrapolate below the last detected row
        last_y = shelf_edges[-1]["y"]
        max_y = int(img_h * 0.95)
        while last_y + median_spacing < max_y:
            last_y += median_spacing
            shelf_edges.append({
                "y": last_y,
                "x_left": widest["x_left"],
                "x_right": widest["x_right"],
                "strip_h": 10,
            })

    return sorted(shelf_edges, key=lambda r: r["y"])


def detect_shelf_bounds(shelf_rows, img_w, img_h):
    """Estimate the overall shelf unit bounding box from detected rows.

    Returns (x_left, y_top, x_right, y_bottom) of the shelf unit.
    """
    if not shelf_rows:
        return (0, 0, img_w, img_h)

    x_left = min(r["x_left"] for r in shelf_rows)
    x_right = max(r["x_right"] for r in shelf_rows)

    # Top: the first row is the top rail — don't place above it
    y_top = shelf_rows[0]["y"] + shelf_rows[0].get("strip_h", 10)

    # Bottom: the bottom of the lowest shelf strip
    y_bottom = shelf_rows[-1]["y"] + shelf_rows[-1]["strip_h"]

    return (x_left, y_top, x_right, y_bottom)


def _estimate_row_spacing(shelf_rows, img_h):
    """Estimate typical vertical spacing between shelf rows."""
    if len(shelf_rows) < 2:
        return int(img_h * 0.15)
    spacings = [shelf_rows[i+1]["y"] - shelf_rows[i]["y"]
                for i in range(len(shelf_rows) - 1)]
    return int(np.median(spacings))


# ── Product Placement ────────────────────────────────────────────────────

def _augment_product(cutout_raw, prod_w, prod_h):
    """Resize and apply visual augmentations to a product cutout."""
    prod = cutout_raw.resize((prod_w, prod_h), Image.LANCZOS)

    # Horizontal flip
    if random.random() < FLIP_PROB:
        prod = prod.transpose(Image.FLIP_LEFT_RIGHT)

    # Slight rotation
    angle = random.uniform(-ROTATION_RANGE, ROTATION_RANGE)
    if abs(angle) > 0.5:
        prod = prod.rotate(angle, expand=True, resample=Image.BICUBIC)

    # Brightness jitter
    factor = 1.0 + random.uniform(-BRIGHTNESS_RANGE, BRIGHTNESS_RANGE)
    r, g, b, a = prod.split()
    rgb = ImageEnhance.Brightness(Image.merge("RGB", (r, g, b))).enhance(factor)
    prod = Image.merge("RGBA", (*rgb.split(), a))

    # Slight blur
    sigma = random.uniform(*BLUR_SIGMA)
    r, g, b, a = prod.split()
    rgb = Image.merge("RGB", (r, g, b)).filter(ImageFilter.GaussianBlur(radius=sigma))
    prod = Image.merge("RGBA", (*rgb.split(), a))

    return prod


def _paste_product(bg, prod, x, y, img_w, img_h):
    """Paste an augmented product onto the background. Returns bbox or None."""
    pw, ph = prod.size
    x = max(0, min(x, img_w - pw))
    y = max(0, min(y, img_h - ph))

    paste_w = min(pw, img_w - x)
    paste_h = min(ph, img_h - y)
    if paste_w <= 0 or paste_h <= 0:
        return None

    if paste_w < pw or paste_h < ph:
        prod = prod.crop((0, 0, paste_w, paste_h))

    bg.paste(prod, (x, y), prod)
    return [int(x), int(y), int(paste_w), int(paste_h)]


def _sample_product_size(img_w, img_h, cutout_aspect):
    """Sample a product size based on real dataset statistics.

    cutout_aspect = cutout_width / cutout_height (natural aspect of product image).
    Returns (prod_w, prod_h).
    """
    # Sample target height as fraction of image
    h_frac = random.uniform(*PROD_H_FRAC)
    prod_h = int(img_h * h_frac)

    # Use cutout's natural aspect ratio, but clamp to realistic range
    aspect = max(PROD_ASPECT[0], min(PROD_ASPECT[1], cutout_aspect))
    prod_w = int(prod_h * aspect)

    # Clamp width to realistic fraction of image
    max_w = int(img_w * PROD_W_FRAC[1] * 1.2)
    min_w = int(img_w * PROD_W_FRAC[0] * 0.8)
    prod_w = max(min_w, min(max_w, prod_w))

    return prod_w, prod_h


def generate_variant(bg_img, shelf_rows, shelf_bounds, cat_to_cutouts,
                     sampling_weights):
    """Generate one synthetic variant by densely packing products on shelves.

    Detects shelf rows and fills each row left-to-right with products,
    then stacks duplicates vertically where space allows.

    Returns:
        (image, annotations) tuple
    """
    bg = bg_img.copy()
    img_w, img_h = bg.size
    bound_left, bound_top, bound_right, bound_bottom = shelf_bounds

    cat_ids = list(sampling_weights.keys())
    cat_weights = [sampling_weights[cid] for cid in cat_ids]

    cutout_cache = {}
    new_annotations = []
    placed_regions = []  # list of (x, y, w, h)
    placed_info = []     # list of (bbox, cat_id, cutout, prod_w, prod_h)

    def _sample_cutout():
        """Sample a random category and return (category_id, cutout_image)."""
        chosen_cat = random.choices(cat_ids, weights=cat_weights, k=1)[0]
        if chosen_cat not in cutout_cache:
            cutout_path = random.choice(cat_to_cutouts[chosen_cat])
            try:
                cutout_cache[chosen_cat] = Image.open(cutout_path).convert("RGBA")
            except Exception:
                return None, None
        return chosen_cat, cutout_cache[chosen_cat]

    def _add_annotation(bbox, cat_id, cutout, prod_w, prod_h):
        placed_regions.append(tuple(bbox))
        placed_info.append((tuple(bbox), cat_id, cutout, prod_w, prod_h))
        new_annotations.append({
            "category_id": cat_id,
            "bbox": bbox,
            "area": bbox[2] * bbox[3],
            "iscrowd": 0,
        })

    num_rows = len(shelf_rows)

    # Step 1: Pack each shelf row densely left-to-right with product grouping
    for row_idx, row in enumerate(shelf_rows):
        shelf_y = row["y"]  # top of shelf edge strip (product bottom)
        row_left = max(row["x_left"], bound_left)
        row_right = min(row["x_right"], bound_right)

        # Available height: from shelf above down to this shelf edge
        # The first detected edge is the top rail — no shelf surface above it
        if row_idx == 0:
            continue  # products below this row are placed by row_idx=1
        prev_bottom = shelf_rows[row_idx - 1]["y"] + shelf_rows[row_idx - 1]["strip_h"]
        avail_top = prev_bottom + 5  # small gap below previous shelf strip

        avail_height = shelf_y - avail_top - SHELF_BOTTOM_MARGIN

        if avail_height < 30 or (row_right - row_left) < 30:
            continue

        # Bottom shelves get slightly larger products (like real stores)
        row_frac = row_idx / max(num_rows - 1, 1)  # 0=top, 1=bottom
        size_scale = 0.85 + 0.3 * row_frac  # 0.85x at top, 1.15x at bottom

        # Fill this row left-to-right, grouping same products together
        cursor_x = row_left
        group_remaining = 0
        group_cat = None
        group_cutout = None
        group_w = 0
        group_h = 0

        while cursor_x < row_right - 20:
            # Start a new product group or continue current one
            if group_remaining <= 0:
                chosen_cat, cutout = _sample_cutout()
                if cutout is None:
                    cursor_x += 20
                    continue

                cw, ch = cutout.size
                cutout_aspect = cw / ch
                prod_w, prod_h = _sample_product_size(img_w, img_h, cutout_aspect)

                # Apply shelf-position scaling
                prod_w = int(prod_w * size_scale)
                prod_h = int(prod_h * size_scale)

                # Clamp height to available space on this shelf
                if prod_h > avail_height:
                    prod_h = avail_height
                    prod_w = int(prod_h * cutout_aspect)

                if prod_w < 15 or prod_h < 20:
                    cursor_x += 20
                    continue

                # Group: 1-5 of the same product in a row
                group_remaining = random.choices(
                    [1, 2, 3, 4, 5],
                    weights=[0.15, 0.25, 0.30, 0.20, 0.10],
                    k=1
                )[0]
                group_cat = chosen_cat
                group_cutout = cutout
                group_w = prod_w
                group_h = prod_h
            else:
                chosen_cat = group_cat
                cutout = group_cutout
                prod_w = group_w
                prod_h = group_h

            group_remaining -= 1

            # Don't overflow past row right edge
            if cursor_x + prod_w > row_right:
                group_remaining = 0
                break

            # Position: bottom-aligned to shelf edge, at cursor_x
            x = cursor_x
            y = shelf_y - prod_h - SHELF_BOTTOM_MARGIN

            prod = _augment_product(cutout, prod_w, prod_h)
            bbox = _paste_product(bg, prod, x, y, img_w, img_h)

            if bbox:
                _add_annotation(bbox, chosen_cat, cutout, prod_w, prod_h)

            # Advance cursor — tighter gap within groups, larger between groups
            if group_remaining > 0:
                gap = random.randint(1, 3)
            else:
                gap = random.randint(*GAP_BETWEEN_PRODUCTS)
            cursor_x += prod_w + gap

    # Step 2: Stack — place the same product on top of itself where space allows
    for (rx, ry, rw, rh), cat_id, cutout, orig_w, orig_h in list(placed_info):
        x = rx
        y = ry - orig_h - 2  # 2px gap above

        if y < bound_top:
            continue

        # Check collision with existing placed products
        fits = True
        for px, py, ppw, pph in placed_regions:
            if x < px + ppw and x + orig_w > px:
                if y < py + pph and y + orig_h > py:
                    fits = False
                    break
        if not fits:
            continue

        prod = _augment_product(cutout, orig_w, orig_h)
        bbox = _paste_product(bg, prod, x, y, img_w, img_h)
        if bbox:
            _add_annotation(bbox, cat_id, cutout, orig_w, orig_h)

    return bg, new_annotations


# ── Main ─────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("Synthetic Data Generator — Bbox-Swap with Empty Shelves")
    print("=" * 60)

    # Phase 1: Load data
    print("\n[Phase 1] Loading data and loading pre-built cutouts...")
    coco, meta = load_data()

    # Load cutouts directly from cache (pre-built)
    cat_to_cutouts = {}
    for p in sorted(CUTOUT_CACHE.iterdir()):
        if p.suffix == ".png":
            cat_id = int(p.stem.split("_")[0].replace("cat", ""))
            cat_to_cutouts.setdefault(cat_id, []).append(p)
    print(f"  Loaded cutouts for {len(cat_to_cutouts)} categories")

    # Phase 2: Compute sampling weights
    print("\n[Phase 2] Computing sampling weights...")
    sampling_weights = compute_sampling_weights(coco, cat_to_cutouts)

    cat_id_to_name = {c["id"]: c["name"] for c in coco["categories"]}
    ann_counts = Counter(a["category_id"] for a in coco["annotations"])
    rare = [(cat_id_to_name[cid], ann_counts.get(cid, 0), w)
            for cid, w in sorted(sampling_weights.items(), key=lambda x: -x[1])[:10]]
    print("Top 10 oversampled categories:")
    for name, count, weight in rare:
        print(f"  {name}: {count} annotations, weight={weight:.4f}")

    # Phase 4: Find empty shelf backgrounds
    print("\n[Phase 4] Finding empty shelf backgrounds...")

    available_empty = {}
    if EMPTY_SHELVES_DIR.exists():
        for p in EMPTY_SHELVES_DIR.iterdir():
            if p.suffix.lower() in (".png", ".jpg", ".jpeg"):
                available_empty[p.stem] = p
    print(f"  Found {len(available_empty)} empty shelf backgrounds")

    if not available_empty:
        print("\n  ERROR: No empty shelf images found in", EMPTY_SHELVES_DIR)
        print("  Run clear_shelves.py first to generate empty shelf backgrounds.")
        return

    # Get original image dimensions for resizing
    img_entry_map = {Path(im["file_name"]).stem: im for im in coco["images"]}

    # Phase 5: Generate synthetic images
    total_variants = len(available_empty) * NUM_VARIANTS
    print(f"\n[Phase 5] Generating {total_variants} synthetic images "
          f"({len(available_empty)} backgrounds × {NUM_VARIANTS} variants)...")

    max_img_id = max(img["id"] for img in coco["images"])
    max_ann_id = max(a["id"] for a in coco["annotations"])

    synthetic_images = []
    synthetic_annotations = []
    total_products = 0
    img_count = 0

    for stem, empty_path in available_empty.items():
        # Get original dimensions to resize to
        im_entry = img_entry_map.get(stem)
        if im_entry:
            orig_w, orig_h = im_entry["width"], im_entry["height"]
        else:
            # Unknown original, use empty shelf as-is
            tmp = Image.open(empty_path)
            orig_w, orig_h = tmp.size
            tmp.close()

        # Load empty shelf and resize to match original
        empty_shelf = Image.open(empty_path).convert("RGB")
        empty_shelf = empty_shelf.resize((orig_w, orig_h), Image.LANCZOS)

        # Detect shelf structure
        empty_cv = cv2.cvtColor(np.array(empty_shelf), cv2.COLOR_RGB2BGR)
        shelf_rows = detect_shelf_rows(empty_cv)
        print(f"  {stem}: {len(shelf_rows)} shelf rows detected")

        if not shelf_rows:
            continue

        shelf_bounds = detect_shelf_bounds(shelf_rows, orig_w, orig_h)

        # Generate variants
        for v in range(NUM_VARIANTS):
            img_count += 1
            img_id = max_img_id + img_count
            filename = f"synth_{img_count:05d}.jpg"

            bg, new_anns = generate_variant(
                empty_shelf, shelf_rows, shelf_bounds,
                cat_to_cutouts, sampling_weights
            )

            # Save image
            out_path = IMAGES_DIR / filename
            bg.save(out_path, quality=90)

            synthetic_images.append({
                "id": img_id,
                "file_name": filename,
                "width": orig_w,
                "height": orig_h,
            })

            for ann in new_anns:
                max_ann_id += 1
                ann["id"] = max_ann_id
                ann["image_id"] = img_id
                synthetic_annotations.append(ann)

            total_products += len(new_anns)

            if img_count % 20 == 0 or img_count == 1:
                print(f"  Generated {img_count}/{total_variants} images "
                      f"({total_products} total products)")

    print(f"\nGenerated {img_count} images with {total_products} product annotations")

    # Phase 6: Merge and save
    print("\n[Phase 6] Merging annotations...")

    backup_path = COCO_DIR / "annotations_original.json"
    if not backup_path.exists():
        shutil.copy2(ANNOTATIONS_FILE, backup_path)
        print(f"  Backed up original annotations to {backup_path.name}")

    synthetic_only = {
        "images": synthetic_images,
        "categories": coco["categories"],
        "annotations": synthetic_annotations,
    }
    synth_ann_path = COCO_DIR / "annotations_synthetic.json"
    with open(synth_ann_path, "w", encoding="utf-8") as f:
        json.dump(synthetic_only, f, ensure_ascii=False)
    print(f"  Saved synthetic-only annotations to {synth_ann_path.name}")

    merged = {
        "images": coco["images"] + synthetic_images,
        "categories": coco["categories"],
        "annotations": coco["annotations"] + synthetic_annotations,
    }
    with open(ANNOTATIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False)
    print(f"  Saved merged annotations to {ANNOTATIONS_FILE.name}")

    # Summary
    print("\n" + "=" * 60)
    print("Summary:")
    print(f"  Original: {len(coco['images'])} images, {len(coco['annotations'])} annotations")
    print(f"  Synthetic: {len(synthetic_images)} images, {len(synthetic_annotations)} annotations")
    print(f"  Merged: {len(merged['images'])} images, {len(merged['annotations'])} annotations")
    print(f"  Categories with cutouts: {len(cat_to_cutouts)}")

    synth_cats = Counter(a["category_id"] for a in synthetic_annotations)
    rare_cats_boosted = sum(1 for cid in synth_cats if ann_counts.get(cid, 0) <= 10)
    print(f"  Rare categories (≤10 real) appearing in synthetic: {rare_cats_boosted}")
    print("=" * 60)


if __name__ == "__main__":
    main()
