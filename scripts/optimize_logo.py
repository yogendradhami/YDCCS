#!/usr/bin/env python3
"""Simple image optimizer for project logo.

Creates WebP variants and resized images from media/company/logoo.png
and writes them to static/images/company/ for use by templates.
"""
from pathlib import Path
from PIL import Image
import sys


def main():
    base = Path(__file__).resolve().parent.parent
    src = base / 'media' / 'company' / 'logoo.png'
    if not src.exists():
        print('Source logo not found:', src)
        sys.exit(1)

    out_dir = base / 'static' / 'images' / 'company'
    out_dir.mkdir(parents=True, exist_ok=True)

    img = Image.open(src)
    # Ensure RGBA for transparency, else convert to RGB
    if img.mode not in ('RGB', 'RGBA'):
        img = img.convert('RGBA')

    # Save full-size WebP
    webp_full = out_dir / 'logoo.webp'
    img.save(webp_full, format='WEBP', quality=80, optimize=True)
    print('Wrote', webp_full)

    # Sizes to generate (displayed sizes found in pages)
    sizes = [48, 84, 256]
    for s in sizes:
        resized = img.copy()
        resized.thumbnail((s, s), Image.LANCZOS)
        out = out_dir / f'logoo-{s}.webp'
        resized.save(out, format='WEBP', quality=80, optimize=True)
        print('Wrote', out)

    print('Logo optimization complete.')


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print('Error:', e)
        raise
