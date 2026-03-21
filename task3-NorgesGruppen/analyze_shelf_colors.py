"""
Analyze HSV color values of yellow-green shelf edge strips in empty shelf images.
Samples pixels across each image to find horizontal runs of yellowish-green color,
then reports H, S, V ranges for detection.
"""

import cv2
import numpy as np
from pathlib import Path

IMAGE_DIR = Path(r"c:\Users\light\Documents\ntnu\NM-AI-2026\task3-NorgesGruppen\data\placement_preview")
IMAGE_FILES = [
    "img_00001_empty.jpg",
    "img_00002_empty.jpg",
    "img_00004_empty.jpg",
]

# Broad initial HSV range for yellow-green (OpenCV H is 0-179)
# Yellow-green hue ~ 20-45, moderate-high saturation, moderate-high value
H_LOW, H_HIGH = 15, 50
S_LOW, S_HIGH = 30, 255
V_LOW, V_HIGH = 80, 255

MIN_RUN_LENGTH_FRAC = 0.3  # minimum horizontal run as fraction of image width


def find_shelf_strips(img_bgr):
    """Find shelf edge strips by looking for horizontal runs of yellow-green pixels."""
    h, w = img_bgr.shape[:2]
    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)

    # Create mask for yellow-green
    lower = np.array([H_LOW, S_LOW, V_LOW])
    upper = np.array([H_HIGH, S_HIGH, V_HIGH])
    mask = cv2.inRange(hsv, lower, upper)

    # Morphological ops to clean up
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 3))
    mask_clean = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    mask_clean = cv2.morphologyEx(mask_clean, cv2.MORPH_OPEN, kernel)

    # For each row, count horizontal run of yellow-green pixels
    min_run = int(w * MIN_RUN_LENGTH_FRAC)
    strip_rows = []

    for y in range(h):
        row = mask_clean[y, :]
        # Find runs of 255 pixels
        changes = np.diff(np.concatenate(([0], row, [0])))
        starts = np.where(changes == 255)[0]
        ends = np.where(changes == -255)[0]
        for s, e in zip(starts, ends):
            if (e - s) >= min_run:
                strip_rows.append((y, s, e))
                break  # one strip per row is enough

    return strip_rows, mask_clean, hsv


def analyze_strips(hsv, strip_rows, img_w):
    """Collect HSV stats from detected strip pixels."""
    all_h, all_s, all_v = [], [], []
    for y, x_start, x_end in strip_rows:
        pixels = hsv[y, x_start:x_end]
        all_h.extend(pixels[:, 0].tolist())
        all_s.extend(pixels[:, 1].tolist())
        all_v.extend(pixels[:, 2].tolist())
    return np.array(all_h), np.array(all_s), np.array(all_v)


def group_strip_rows(strip_rows):
    """Group consecutive strip rows into individual shelf strips."""
    if not strip_rows:
        return []
    groups = []
    current_group = [strip_rows[0]]
    for i in range(1, len(strip_rows)):
        y_prev = strip_rows[i - 1][0]
        y_curr = strip_rows[i][0]
        if y_curr - y_prev <= 3:  # allow small gaps
            current_group.append(strip_rows[i])
        else:
            groups.append(current_group)
            current_group = [strip_rows[i]]
    groups.append(current_group)
    return groups


def main():
    all_h_vals, all_s_vals, all_v_vals = [], [], []
    all_strip_heights = []
    all_strip_width_fracs = []

    for fname in IMAGE_FILES:
        path = IMAGE_DIR / fname
        img = cv2.imread(str(path))
        if img is None:
            print(f"Could not load {path}")
            continue

        h_img, w_img = img.shape[:2]
        print(f"\n{'='*70}")
        print(f"Image: {fname}  ({w_img} x {h_img})")
        print(f"{'='*70}")

        strip_rows, mask, hsv = find_shelf_strips(img)
        print(f"  Rows with yellow-green horizontal runs (>={MIN_RUN_LENGTH_FRAC*100:.0f}% width): {len(strip_rows)}")

        if not strip_rows:
            print("  No strips found!")
            continue

        # Group into individual strips
        groups = group_strip_rows(strip_rows)
        print(f"  Number of distinct shelf strips detected: {len(groups)}")

        for i, group in enumerate(groups):
            y_min = group[0][0]
            y_max = group[-1][0]
            strip_height = y_max - y_min + 1
            # Average x range
            x_starts = [r[1] for r in group]
            x_ends = [r[2] for r in group]
            avg_x_start = np.mean(x_starts)
            avg_x_end = np.mean(x_ends)
            width_frac = (avg_x_end - avg_x_start) / w_img

            all_strip_heights.append(strip_height)
            all_strip_width_fracs.append(width_frac)

            print(f"  Strip {i+1}: y=[{y_min}, {y_max}], height={strip_height}px, "
                  f"x=[{avg_x_start:.0f}, {avg_x_end:.0f}], width_frac={width_frac:.2%}")

        # Collect HSV values
        h_vals, s_vals, v_vals = analyze_strips(hsv, strip_rows, w_img)
        all_h_vals.extend(h_vals.tolist())
        all_s_vals.extend(s_vals.tolist())
        all_v_vals.extend(v_vals.tolist())

        # Per-image stats
        print(f"\n  Per-image HSV stats (from strip pixels):")
        print(f"    H: min={h_vals.min()}, max={h_vals.max()}, "
              f"mean={h_vals.mean():.1f}, std={h_vals.std():.1f}, "
              f"p5={np.percentile(h_vals,5):.0f}, p95={np.percentile(h_vals,95):.0f}")
        print(f"    S: min={s_vals.min()}, max={s_vals.max()}, "
              f"mean={s_vals.mean():.1f}, std={s_vals.std():.1f}, "
              f"p5={np.percentile(s_vals,5):.0f}, p95={np.percentile(s_vals,95):.0f}")
        print(f"    V: min={v_vals.min()}, max={v_vals.max()}, "
              f"mean={v_vals.mean():.1f}, std={v_vals.std():.1f}, "
              f"p5={np.percentile(v_vals,5):.0f}, p95={np.percentile(v_vals,95):.0f}")

    # Overall summary
    all_h = np.array(all_h_vals)
    all_s = np.array(all_s_vals)
    all_v = np.array(all_v_vals)

    print(f"\n{'='*70}")
    print(f"OVERALL SUMMARY (across all {len(IMAGE_FILES)} images)")
    print(f"{'='*70}")
    print(f"Total strip pixels sampled: {len(all_h)}")
    print(f"\nHSV ranges (full min-max):")
    print(f"  H: [{all_h.min()}, {all_h.max()}]")
    print(f"  S: [{all_s.min()}, {all_s.max()}]")
    print(f"  V: [{all_v.min()}, {all_v.max()}]")
    print(f"\nHSV ranges (5th-95th percentile, recommended for detection):")
    print(f"  H: [{np.percentile(all_h,5):.0f}, {np.percentile(all_h,95):.0f}]")
    print(f"  S: [{np.percentile(all_s,5):.0f}, {np.percentile(all_s,95):.0f}]")
    print(f"  V: [{np.percentile(all_v,5):.0f}, {np.percentile(all_v,95):.0f}]")
    print(f"\nHSV ranges (1st-99th percentile, wider tolerance):")
    print(f"  H: [{np.percentile(all_h,1):.0f}, {np.percentile(all_h,99):.0f}]")
    print(f"  S: [{np.percentile(all_s,1):.0f}, {np.percentile(all_s,99):.0f}]")
    print(f"  V: [{np.percentile(all_v,1):.0f}, {np.percentile(all_v,99):.0f}]")

    print(f"\nShelf strip dimensions:")
    print(f"  Strip heights (px): {all_strip_heights}")
    print(f"  Mean strip height: {np.mean(all_strip_heights):.1f} px")
    print(f"  Min/Max strip height: {min(all_strip_heights)} / {max(all_strip_heights)} px")
    print(f"  Strip width fractions: {[f'{f:.2%}' for f in all_strip_width_fracs]}")
    print(f"  Mean width fraction: {np.mean(all_strip_width_fracs):.2%}")

    # Suggested thresholds
    margin = 5
    h_lo = max(0, int(np.percentile(all_h, 2)) - margin)
    h_hi = min(179, int(np.percentile(all_h, 98)) + margin)
    s_lo = max(0, int(np.percentile(all_s, 2)) - margin)
    s_hi = min(255, int(np.percentile(all_s, 98)) + margin)
    v_lo = max(0, int(np.percentile(all_v, 2)) - margin)
    v_hi = min(255, int(np.percentile(all_v, 98)) + margin)
    print(f"\nSUGGESTED HSV THRESHOLDS (2nd-98th percentile +/- {margin}):")
    print(f"  lower = np.array([{h_lo}, {s_lo}, {v_lo}])")
    print(f"  upper = np.array([{h_hi}, {s_hi}, {v_hi}])")


if __name__ == "__main__":
    main()
