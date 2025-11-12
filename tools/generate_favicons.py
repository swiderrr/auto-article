#!/usr/bin/env python3
"""
Generate favicon and app icon files from a single source image.

Usage:
  python3 tools/generate_favicons.py [source_path]

If no source_path is given the script looks for `kids/static/icons/source.png` or `source.jpg`.

Outputs (written to `kids/static/icons/`):
- favicon-16x16.png
- favicon-32x32.png
- apple-touch-icon.png (180x180)
- android-chrome-192x192.png
- android-chrome-512x512.png
- favicon.ico (contains 16x16,32x32,48x48)

Requires: Pillow (pip install pillow)
"""
import sys
import os
from pathlib import Path

try:
    from PIL import Image, ImageOps
except Exception:
    print("Pillow is required. Install with: pip install pillow")
    sys.exit(2)

ROOT = Path(__file__).resolve().parents[1]
ICONS_DIR = ROOT / 'kids' / 'static' / 'icons'
ICONS_DIR.mkdir(parents=True, exist_ok=True)

candidates = []
if len(sys.argv) > 1:
    candidates.append(Path(sys.argv[1]))
else:
    candidates.extend([ICONS_DIR / 'source.png', ICONS_DIR / 'source.jpg', ROOT / 'kids' / 'static' / 'icons' / 'source.jpeg'])

source = None
for c in candidates:
    if c and c.exists():
        source = c
        break

if not source:
    print("No source image found. Please place a high-resolution square PNG/JPG at:")
    print(f"  {ICONS_DIR / 'source.png'}")
    print("Or run: python3 tools/generate_favicons.py path/to/your/source.png")
    sys.exit(1)

print(f"Using source image: {source}")

# Helper to make square icon with optional background fill
def make_icon(im, size, dest, bgcolor=(255,255,255,0)):
    # Fit the image into a square of given size, preserving aspect ratio
    # If the source has an alpha channel, preserve it; otherwise use white background
    try:
        im2 = ImageOps.fit(im, (size, size), Image.LANCZOS)
    except Exception:
        im2 = im.resize((size, size), Image.LANCZOS)
    # Ensure PNG (RGBA) to preserve transparency
    if im2.mode not in ('RGBA', 'LA'):
        im2 = im2.convert('RGBA')
    dest.parent.mkdir(parents=True, exist_ok=True)
    im2.save(dest, format='PNG')
    print(f"Wrote {dest}")
    return dest

# Load source image
im = Image.open(source).convert('RGBA')

# List of targets
targets = [
    (16, 'favicon-16x16.png'),
    (32, 'favicon-32x32.png'),
    (180, 'apple-touch-icon.png'),
    (192, 'android-chrome-192x192.png'),
    (512, 'android-chrome-512x512.png'),
]

written = []
for size, name in targets:
    out = ICONS_DIR / name
    make_icon(im, size, out)
    written.append(out)

# Create favicon.ico with multiple sizes (16,32,48)
ico_sizes = [16,32,48]
ico_images = []
for s in ico_sizes:
    tmp = ICONS_DIR / f'_tmp_{s}.png'
    make_icon(im, s, tmp)
    ico_images.append(Image.open(tmp))

ico_path = ICONS_DIR / 'favicon.ico'
try:
    ico_images[0].save(ico_path, format='ICO', sizes=[(s,s) for s in ico_sizes])
    print(f"Wrote {ico_path}")
except Exception as e:
    print("Failed to write favicon.ico:", e)

# Clean up temp files
for s in ico_sizes:
    tmp = ICONS_DIR / f'_tmp_{s}.png'
    try:
        tmp.unlink()
    except Exception:
        pass

print("Done. Add/commit the files in kids/static/icons/ and rebuild the site.")
