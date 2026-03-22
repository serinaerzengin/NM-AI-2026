"""
Use Gemini API to remove products from shelf images, creating empty shelf backgrounds.

Processes each training image and asks Gemini to clear the shelves while keeping
the shelf structure, price tags, and store background intact.

Requires GEMINI_API_KEY environment variable.
"""

import os
import sys
import time
from pathlib import Path

from google import genai
from google.genai import types
from PIL import Image

# ── Config ───────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent
IMAGES_DIR = ROOT / "data" / "NM_NGD_coco_dataset" / "train" / "images"
OUTPUT_DIR = ROOT / "data" / "empty_shelves"

PROMPT = (
    "Remove all grocery products from the shelves. "
    "IMPORTANT: Keep all small white price label tags on the shelf edges. "
    "Only remove the products, not the price tags."
)

# Rate limiting: Gemini free tier = 10 RPM for image gen
DELAY_BETWEEN_CALLS = 1  # seconds


def main():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: Set GEMINI_API_KEY environment variable")
        print("  export GEMINI_API_KEY=your_key_here")
        sys.exit(1)

    client = genai.Client(api_key=api_key)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Gather all training images (skip synthetic ones and image.png)
    image_paths = sorted(
        p for p in IMAGES_DIR.iterdir()
        if p.suffix.lower() in (".jpg", ".jpeg", ".png")
        and not p.name.startswith("synth_")
        and p.name != "image.png"
    )

    print(f"Found {len(image_paths)} images to process")
    print(f"Output directory: {OUTPUT_DIR}")

    # Check which are already done
    done = {p.stem for p in OUTPUT_DIR.iterdir() if p.suffix == ".png"}
    remaining = [p for p in image_paths if p.stem not in done]
    print(f"Already processed: {len(done)}, remaining: {len(remaining)}")

    for i, img_path in enumerate(remaining):
        out_path = OUTPUT_DIR / f"{img_path.stem}.png"

        print(f"\n[{i+1}/{len(remaining)}] Processing {img_path.name}...")

        try:
            # Load and resize image so Gemini sees the full picture
            img = Image.open(img_path)
            max_dim = 1024
            w, h = img.size
            if max(w, h) > max_dim:
                scale = max_dim / max(w, h)
                img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)

            # Call Gemini image editing
            response = client.models.generate_content(
                model="gemini-3-pro-image-preview",
                contents=[PROMPT, img],
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE", "TEXT"],
                ),
            )

            # Extract generated image from response
            saved = False
            for part in response.candidates[0].content.parts:
                if part.inline_data is not None:
                    # Save the generated image
                    import io
                    result_img = Image.open(io.BytesIO(part.inline_data.data))
                    result_img.save(out_path)
                    print(f"  Saved: {out_path.name} ({result_img.size})")
                    saved = True
                    break

            if not saved:
                # Check if there's text explaining why it failed
                for part in response.candidates[0].content.parts:
                    if part.text:
                        print(f"  Warning: No image returned. Response: {part.text[:200]}")
                print(f"  SKIPPED: No image in response")

        except Exception as e:
            print(f"  ERROR: {e}")

        # Rate limiting
        if i < len(remaining) - 1:
            time.sleep(DELAY_BETWEEN_CALLS)

    print(f"\n{'='*60}")
    total_done = len(list(OUTPUT_DIR.glob("*.png")))
    print(f"Done! {total_done} empty shelf images in {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
