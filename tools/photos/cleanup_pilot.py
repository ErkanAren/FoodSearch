#!/usr/bin/env python3
"""E11: OFF photo clean-up pilot (background removal -> square white catalogue image).

Needs the project venv (rembg) and work/browser.sqlite (built by tools/browser/foods_browser.py):

    .venv/bin/python -I tools/photos/cleanup_pilot.py                  # 200 products, default model
    .venv/bin/python -I tools/photos/cleanup_pilot.py --n 8 --model isnet-general-use --out work/photo_model_test/isnet-general-use

Output (git-ignored), default work/photo_pilot/:
    raw/<code>.jpg      downloaded full-size OFF front photo (untrusted input, cached)
    before/<code>.jpg   original, longest side 512 px (for side-by-side review)
    after/<code>.jpg    cleaned: background removed, cropped, 8 % margin, 512x512 on white
    manifest.json       one record per product: source, sizes, timings, auto-QA metrics and flags

Review the result in the browser at http://127.0.0.1:8765/photo-pilot (verdicts go to review.json).
"""
import argparse
import hashlib
import io
import json
import sqlite3
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parent.parent.parent  # Foods/
DB_PATH = ROOT / "work" / "browser.sqlite"
USER_AGENT = "KnowD1FoodsPhotoPilot/0.1"  # generic client name, no personal details
CANVAS = 512
MARGIN = 0.08
WORK_MAX_SIDE = 1024
MAX_DOWNLOAD_BYTES = 25 * 1024 * 1024

# Auto-QA thresholds (flags only point a reviewer at likely failures; they never reject on their own)
FLAG_RULES = {
    "fg_small": "foreground < 3 % of the photo (mask probably lost the product)",
    "fg_huge": "foreground > 97 % of the photo (background not removed)",
    "fragmented": "foreground fills < 35 % of its bounding box (scattered pieces)",
    "soft_edges": "> 25 % of foreground pixels are semi-transparent (fuzzy mask)",
    "low_res": "original longest side < 400 px",
}


def select_products(n):
    """Greek OFF products with a front photo, in a fixed pseudo-random order (SHA-1 of the barcode)."""
    con = sqlite3.connect(DB_PATH.as_uri() + "?mode=ro", uri=True)
    rows = con.execute("SELECT id, name, brand, photos FROM off WHERE photos IS NOT NULL").fetchall()
    con.close()
    items = []
    for code, name, brand, photos in rows:
        front = json.loads(photos).get("front")
        if front:
            items.append({"code": code, "name": name, "brand": brand, "front_key": front["key"], "src": front["full"]})
    items.sort(key=lambda it: hashlib.sha1(it["code"].encode()).hexdigest())
    return items[:n]


def download(item, raw_dir):
    dest = raw_dir / f"{item['code']}.jpg"
    if dest.exists():
        return True
    for attempt in range(3):
        try:
            req = urllib.request.Request(item["src"], headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = resp.read(MAX_DOWNLOAD_BYTES + 1)
            if len(data) > MAX_DOWNLOAD_BYTES:
                return False
            Image.open(io.BytesIO(data)).verify()  # must be a real image
            tmp = dest.with_suffix(".part")
            tmp.write_bytes(data)
            tmp.replace(dest)
            return True
        except Exception as e:  # network errors, 404s, broken files
            item["download_error"] = str(e)[:200]
            time.sleep(1 + attempt)
    return False


def clean(img, session, remove):
    """Return (cleaned 512x512 RGB image, metrics dict)."""
    cut = remove(img, session=session)  # RGBA
    alpha = np.asarray(cut)[:, :, 3]
    fg = alpha > 10
    fg_px = int(fg.sum())
    metrics = {
        "coverage": round(fg_px / fg.size, 4),
        "soft": round(float(((alpha > 20) & (alpha < 235)).sum()) / max(fg_px, 1), 4),
        "fill": 0.0,
    }
    canvas = Image.new("RGB", (CANVAS, CANVAS), "white")
    if fg_px == 0:
        return canvas, metrics
    ys, xs = np.where(fg)
    x0, x1, y0, y1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
    metrics["fill"] = round(fg_px / ((x1 - x0) * (y1 - y0)), 4)
    obj = cut.crop((int(x0), int(y0), int(x1), int(y1)))
    side = max(obj.size) / (1 - 2 * MARGIN)
    scale = CANVAS / side
    obj = obj.resize((max(1, round(obj.width * scale)), max(1, round(obj.height * scale))), Image.LANCZOS)
    canvas.paste(obj, ((CANVAS - obj.width) // 2, (CANVAS - obj.height) // 2), obj)
    return canvas, metrics


def flags_for(m, orig_size):
    flags = []
    if m["coverage"] < 0.03:
        flags.append("fg_small")
    if m["coverage"] > 0.97:
        flags.append("fg_huge")
    if m["coverage"] >= 0.03 and m["fill"] < 0.35:
        flags.append("fragmented")
    if m["soft"] > 0.25:
        flags.append("soft_edges")
    if max(orig_size) < 400:
        flags.append("low_res")
    return flags


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--n", type=int, default=200)
    ap.add_argument("--model", default="birefnet-general-lite", help="rembg model name (E11: birefnet-general-lite beat isnet-general-use)")
    ap.add_argument("--out", default=str(ROOT / "work" / "photo_pilot"))
    ap.add_argument("--workers", type=int, default=4, help="parallel downloads (keep it polite)")
    args = ap.parse_args()

    from rembg import new_session, remove

    out = Path(args.out)
    if not out.is_absolute():
        out = ROOT / out
    dirs = {k: out / k for k in ("raw", "before", "after")}
    for d in dirs.values():
        d.mkdir(parents=True, exist_ok=True)
    # raw downloads are shared between runs so model comparisons don't re-download
    shared_raw = ROOT / "work" / "photo_pilot" / "raw"
    shared_raw.mkdir(parents=True, exist_ok=True)

    items = select_products(args.n)
    print(f"Selected {len(items)} products. Downloading front photos ({args.workers} at a time)…", flush=True)
    t0 = time.time()
    with ThreadPoolExecutor(args.workers) as pool:
        ok = list(pool.map(lambda it: download(it, shared_raw), items))
    print(f"  downloaded {sum(ok)}/{len(items)} in {time.time() - t0:.0f}s", flush=True)

    print(f"Loading model {args.model}…", flush=True)
    session = new_session(args.model)
    records = []
    t_all = time.time()
    for i, (item, got) in enumerate(zip(items, ok), 1):
        rec = dict(item)
        if not got:
            rec["flags"] = ["download_failed"]
            records.append(rec)
            continue
        img = ImageOps.exif_transpose(Image.open(shared_raw / f"{item['code']}.jpg")).convert("RGB")
        rec["orig_w"], rec["orig_h"] = img.size
        img.thumbnail((WORK_MAX_SIDE, WORK_MAX_SIDE), Image.LANCZOS)
        before = img.copy()
        before.thumbnail((CANVAS, CANVAS), Image.LANCZOS)
        before.save(dirs["before"] / f"{item['code']}.jpg", quality=88)
        t = time.time()
        after, metrics = clean(img, session, remove)
        rec["secs"] = round(time.time() - t, 2)
        after_path = dirs["after"] / f"{item['code']}.jpg"
        after.save(after_path, quality=88, optimize=True)
        rec["after_kb"] = round(after_path.stat().st_size / 1024, 1)
        rec.update(metrics)
        rec["flags"] = flags_for(metrics, (rec["orig_w"], rec["orig_h"]))
        records.append(rec)
        if i % 20 == 0 or i == len(items):
            print(f"  processed {i}/{len(items)} - {time.time() - t_all:.0f}s", flush=True)

    done = [r for r in records if "secs" in r]
    summary = {
        "model": args.model,
        "created": time.strftime("%Y-%m-%d %H:%M"),
        "n_selected": len(items),
        "n_processed": len(done),
        "n_flagged": sum(1 for r in done if r["flags"]),
        "avg_secs": round(sum(r["secs"] for r in done) / max(len(done), 1), 2),
        "avg_after_kb": round(sum(r["after_kb"] for r in done) / max(len(done), 1), 1),
        "flag_rules": FLAG_RULES,
    }
    (out / "manifest.json").write_text(json.dumps({"summary": summary, "items": records}, ensure_ascii=False, indent=1))
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    sys.exit(main())
