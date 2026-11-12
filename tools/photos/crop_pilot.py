#!/usr/bin/env python3
"""E14: product crop with Open Food Facts' ready-made models (no background removal).

Same 200 products as the E11 cut-out pilot, so the two methods can be compared photo by photo.
For each product's OFF front photo:
  1. openfoodfacts/front_image_classification (YOLO11n-cls): is this really a front photo?
  2. openfoodfacts/crop-detection (YOLOv8n): where are the product's edges?
  3. Crop the original to that box (+2 %), centre it on a 512x512 white square (5 % margin).

Needs the project venv (onnxruntime, pillow, numpy), work/browser.sqlite, and the two ONNX models:

    mkdir -p work/models/off-crop-detection work/models/off-front-image
    curl -L -o work/models/off-crop-detection/best.onnx \\
        https://huggingface.co/openfoodfacts/crop-detection/resolve/main/weights/best.onnx
    curl -L -o work/models/off-front-image/model.onnx \\
        https://huggingface.co/openfoodfacts/front_image_classification/resolve/main/weights/model.onnx
    .venv/bin/python -I tools/photos/crop_pilot.py

Both models are AGPL-3.0. We only run them offline here; the app ships the resulting photos, not the models.

Output (git-ignored), default work/photo_pilot_crop/:
    before/<code>.jpg   original, longest side 512 px
    after/<code>.jpg    cropped product on a 512x512 white square
    manifest.json       one record per product: box, confidence, front score, flags, timings
Review at http://127.0.0.1:8765/photo-pilot?run=crop (verdicts go to review.json in the same folder).
"""
import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import onnxruntime as ort
from PIL import Image, ImageOps

sys.path.insert(0, str(Path(__file__).resolve().parent))  # our own sibling module (tools/photos/)
from cleanup_pilot import CANVAS, ROOT, download, select_products  # noqa: E402

CROP_MODEL = ROOT / "work" / "models" / "off-crop-detection" / "best.onnx"
FRONT_MODEL = ROOT / "work" / "models" / "off-front-image" / "model.onnx"
DET_SIZE = 640          # crop-detection input (YOLOv8 letterbox)
CLS_SIZE = 448          # front classifier input
MIN_BOX_CONF = 0.25     # below this we treat it as "no product found" and keep the whole photo
BOX_PAD = 0.02          # grow the detected box a little so edges aren't clipped
MARGIN = 0.05           # white margin around the crop on the square canvas

FLAG_RULES = {
    "no_box": f"no product found (confidence < {MIN_BOX_CONF}); the whole photo is used",
    "not_front": "front-photo model thinks this is not a front photo (back label, nutrition table…)",
    "small_box": "product covers < 15 % of the photo (far away or the wrong object)",
    "low_res": "original longest side < 400 px",
}


def letterbox(img, size):
    """Ultralytics-style letterbox: keep aspect ratio, pad with grey 114. Returns (tensor, scale, left, top)."""
    w, h = img.size
    r = min(size / w, size / h)
    nw, nh = round(w * r), round(h * r)
    left, top = round((size - nw) / 2 - 0.1), round((size - nh) / 2 - 0.1)
    canvas = Image.new("RGB", (size, size), (114, 114, 114))
    canvas.paste(img.resize((nw, nh), Image.BILINEAR), (left, top))
    x = np.asarray(canvas, dtype=np.float32).transpose(2, 0, 1)[None] / 255.0
    return x, r, left, top


def detect_product(sess, img):
    """Best 'product' box in original pixel coordinates, or None. Returns (box, confidence)."""
    x, r, left, top = letterbox(img, DET_SIZE)
    out = sess.run(None, {sess.get_inputs()[0].name: x})[0][0]  # (5, 8400): cx, cy, w, h, score
    best = int(out[4].argmax())
    conf = float(out[4, best])
    if conf < MIN_BOX_CONF:
        return None, conf
    cx, cy, bw, bh = (float(v) for v in out[:4, best])
    if max(cx, cy, bw, bh) <= 2.0:  # this export gives coordinates as fractions of the 640 input
        cx, cy, bw, bh = cx * DET_SIZE, cy * DET_SIZE, bw * DET_SIZE, bh * DET_SIZE
    w, h = img.size
    x0 = max(0.0, (cx - bw / 2 - left) / r)
    y0 = max(0.0, (cy - bh / 2 - top) / r)
    x1 = min(float(w), (cx + bw / 2 - left) / r)
    y1 = min(float(h), (cy + bh / 2 - top) / r)
    return (x0, y0, x1, y1), conf


def front_score(sess, img):
    """P(front) from OFF's classifier. Preprocessing as in OFF's ml_commons.get_predict_transform:
    longest side 448, centre-pad to 448x448 with black, scale to 0..1."""
    im = img.copy()
    im.thumbnail((CLS_SIZE, CLS_SIZE), Image.BILINEAR)
    if max(im.size) < CLS_SIZE:  # LongestMaxSize also upsizes small photos
        r = CLS_SIZE / max(im.size)
        im = img.resize((max(1, round(img.width * r)), max(1, round(img.height * r))), Image.BILINEAR)
    canvas = Image.new("RGB", (CLS_SIZE, CLS_SIZE), (0, 0, 0))
    canvas.paste(im, ((CLS_SIZE - im.width) // 2, (CLS_SIZE - im.height) // 2))
    x = np.asarray(canvas, dtype=np.float32).transpose(2, 0, 1)[None] / 255.0
    probs = sess.run(None, {sess.get_inputs()[0].name: x})[0][0]  # softmax: [front, other]
    return float(probs[0])


def compose(img, box):
    """Crop to the (padded) box and centre it on a white square canvas."""
    if box is not None:
        x0, y0, x1, y1 = box
        px, py = (x1 - x0) * BOX_PAD, (y1 - y0) * BOX_PAD
        img = img.crop((int(max(0, x0 - px)), int(max(0, y0 - py)),
                        int(min(img.width, x1 + px + 0.5)), int(min(img.height, y1 + py + 0.5))))
    inner = CANVAS * (1 - 2 * MARGIN)
    scale = inner / max(img.size)
    obj = img.resize((max(1, round(img.width * scale)), max(1, round(img.height * scale))), Image.LANCZOS)
    canvas = Image.new("RGB", (CANVAS, CANVAS), "white")
    canvas.paste(obj, ((CANVAS - obj.width) // 2, (CANVAS - obj.height) // 2))
    return canvas


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--n", type=int, default=200)
    ap.add_argument("--out", default=str(ROOT / "work" / "photo_pilot_crop"))
    ap.add_argument("--workers", type=int, default=4, help="parallel downloads (keep it polite)")
    args = ap.parse_args()

    for m in (CROP_MODEL, FRONT_MODEL):
        if not m.exists():
            sys.exit(f"Model not found: {m}\nSee the download commands at the top of this script.")
    out = Path(args.out)
    if not out.is_absolute():
        out = ROOT / out
    for sub in ("before", "after"):
        (out / sub).mkdir(parents=True, exist_ok=True)
    raw = ROOT / "work" / "photo_pilot" / "raw"  # shared with the E11 pilot (same products, already cached)
    raw.mkdir(parents=True, exist_ok=True)

    items = select_products(args.n)
    with ThreadPoolExecutor(args.workers) as pool:
        ok = list(pool.map(lambda it: download(it, raw), items))
    print(f"{sum(ok)}/{len(items)} front photos available", flush=True)

    opts = ort.SessionOptions()
    opts.log_severity_level = 3
    det = ort.InferenceSession(str(CROP_MODEL), opts, providers=["CPUExecutionProvider"])
    cls = ort.InferenceSession(str(FRONT_MODEL), opts, providers=["CPUExecutionProvider"])

    records = []
    for item, got in zip(items, ok):
        rec = dict(item)
        if not got:
            rec["flags"] = ["download_failed"]
            records.append(rec)
            continue
        img = ImageOps.exif_transpose(Image.open(raw / f"{item['code']}.jpg")).convert("RGB")
        rec["orig_w"], rec["orig_h"] = img.size
        before = img.copy()
        before.thumbnail((CANVAS, CANVAS), Image.LANCZOS)
        before.save(out / "before" / f"{item['code']}.jpg", quality=88)

        t = time.time()
        rec["front_prob"] = round(front_score(cls, img), 3)
        box, conf = detect_product(det, img)
        after = compose(img, box)
        rec["secs"] = round(time.time() - t, 3)
        after_path = out / "after" / f"{item['code']}.jpg"
        after.save(after_path, quality=88, optimize=True)
        rec["after_kb"] = round(after_path.stat().st_size / 1024, 1)
        rec["box_conf"] = round(conf, 3)
        rec["box"] = [round(v) for v in box] if box else None
        rec["box_area"] = round((box[2] - box[0]) * (box[3] - box[1]) / (img.width * img.height), 3) if box else None

        flags = []
        if box is None:
            flags.append("no_box")
        elif rec["box_area"] < 0.15:
            flags.append("small_box")
        if rec["front_prob"] < 0.5:
            flags.append("not_front")
        if max(img.size) < 400:
            flags.append("low_res")
        rec["flags"] = flags
        records.append(rec)

    done = [r for r in records if "secs" in r]
    summary = {
        "method": "crop",
        "model": "OFF crop-detection + front-image",
        "created": time.strftime("%Y-%m-%d %H:%M"),
        "n_selected": len(items),
        "n_processed": len(done),
        "n_flagged": sum(1 for r in done if r["flags"]),
        "avg_secs": round(sum(r["secs"] for r in done) / max(len(done), 1), 2),
        "avg_after_kb": round(sum(r["after_kb"] for r in done) / max(len(done), 1), 1),
        "flag_rules": FLAG_RULES,
        "compare_run": "cutout",  # the review page shows the E11 cut-out and its verdict next to the crop
    }
    (out / "manifest.json").write_text(json.dumps({"summary": summary, "items": records}, ensure_ascii=False, indent=1))
    print(json.dumps({k: v for k, v in summary.items() if k != "flag_rules"}, indent=1))


if __name__ == "__main__":
    sys.exit(main())
