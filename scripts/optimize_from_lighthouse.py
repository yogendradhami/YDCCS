"""
Read `lighthouse-report.json`, find large image/static/media resources, and generate
responsive WebP/AVIF variants under `static/images/optimized/`.

Usage:
  python3 scripts/optimize_from_lighthouse.py

The script requires Pillow installed in your environment (`pip install pillow`).
It will skip files it cannot find and will gracefully continue on format errors.
"""
from pathlib import Path
import json
import os
from PIL import Image

BASE = Path(__file__).resolve().parents[1]
REPORT = BASE / 'lighthouse-report.json'
OUT_BASE = BASE / 'static' / 'images' / 'optimized'
THRESHOLD_BYTES = 100 * 1024  # 100 KB
TARGET_WIDTHS = [320, 480, 768, 1024, 1254]
WEBP_OPTIONS = {'quality': 80, 'method': 6}
AVIF_OPTIONS = {'quality': 50}


def find_resources(obj, results):
    if isinstance(obj, dict):
        if 'url' in obj and ('totalBytes' in obj or 'resourceSize' in obj or 'transferSize' in obj):
            # pick a bytes field if available
            size = obj.get('totalBytes') or obj.get('transferSize') or obj.get('resourceSize') or 0
            results.append((obj['url'], int(size)))
        for v in obj.values():
            find_resources(v, results)
    elif isinstance(obj, list):
        for item in obj:
            find_resources(item, results)


def local_path_from_url(url):
    # Remove scheme and host if present
    # e.g. http://127.0.0.1:8000/media/company/logoo.png -> media/company/logoo.png
    if '://' in url:
        try:
            path = url.split('://', 1)[1]
            # strip host portion
            sep = path.find('/')
            if sep != -1:
                path = path[sep+1:]
            else:
                return None
        except Exception:
            return None
    else:
        path = url.lstrip('/')
    # Only handle media/ and static/ files
    if path.startswith('media/') or path.startswith('static/'):
        return BASE / path
    return None


def ensure_dir(p: Path):
    p.parent.mkdir(parents=True, exist_ok=True)


def try_save_avif(img: Image.Image, out_path: Path):
    try:
        img.save(out_path, format='AVIF')
        return True
    except Exception:
        return False


def try_save_webp(img: Image.Image, out_path: Path):
    try:
        img.save(out_path, format='WEBP', **WEBP_OPTIONS)
        return True
    except Exception:
        return False


def process_file(src_path: Path):
    if not src_path.exists():
        print(f"SKIP - not found: {src_path}")
        return
    try:
        img = Image.open(src_path)
    except Exception as e:
        print(f"SKIP - open failed {src_path}: {e}")
        return
    orig_w, orig_h = img.size
    rel = src_path.relative_to(BASE)
    rel_dir = rel.parent
    name = src_path.stem
    out_dir = OUT_BASE / rel_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    created = []
    for w in TARGET_WIDTHS:
        if w > orig_w:
            continue
        # compute height maintaining aspect
        h = int(orig_h * (w / orig_w))
        try:
            resized = img.copy()
            resized = resized.resize((w, h), Image.LANCZOS)
        except Exception:
            resized = img.copy()
        webp_path = out_dir / f"{name}-{w}.webp"
        avif_path = out_dir / f"{name}-{w}.avif"
        ok_webp = try_save_webp(resized, webp_path)
        ok_avif = try_save_avif(resized, avif_path)
        if ok_webp:
            created.append(str(webp_path.relative_to(BASE)))
        if ok_avif:
            created.append(str(avif_path.relative_to(BASE)))
    # also save a full-size webp
    full_webp = out_dir / f"{name}.webp"
    if try_save_webp(img, full_webp):
        created.append(str(full_webp.relative_to(BASE)))
    print(f"Processed {src_path} -> {len(created)} files")
    for c in created:
        print("  ", c)


if __name__ == '__main__':
    if not REPORT.exists():
        print('lighthouse-report.json not found at', REPORT)
        raise SystemExit(1)

    with REPORT.open('r', encoding='utf-8') as fh:
        j = json.load(fh)

    resources = []
    find_resources(j, resources)

    # filter unique and large
    uniq = {}
    for url, size in resources:
        if url in uniq:
            uniq[url] = max(uniq[url], size)
        else:
            uniq[url] = size

    candidates = [u for u, s in uniq.items() if s >= THRESHOLD_BYTES and ('/media/' in u or '/static/' in u)]
    if not candidates:
        print('No large candidates found in report (threshold', THRESHOLD_BYTES, 'bytes)')
        raise SystemExit(0)

    print('Found', len(candidates), 'candidates; processing...')
    for url in candidates:
        lp = local_path_from_url(url)
        if lp:
            process_file(lp)
        else:
            print('Skip (not local):', url)

    print('Done')
