#!/usr/bin/env python3
"""Trial of the v2 image pipeline (docs/HANDOFF-product-images-v2.md), end to end on 50 products.

Goal: see whether it is fast and works well before doing the staged rollout.
Products: the first 50 of the 200-product gold set (same deterministic sample as E11 / E14).

Per product:
  1. Best-of-N front: score EVERY uploaded photo (400 px version from the S3 archive) with the
     front classifier, the product detector, blur and resolution. Upright first, using the OCR text
     direction. Pick the best one; near-ties go to the newest upload, then the app language.
  2. Pack-type router: packaging_shapes from the product data if present, else zero-shot CLIP.
  3. Processor by type:  box -> perspective rectification · can / bottle -> box-prompted cut-out
     (BiRefNet-lite on the detector region + hole filling; SAM 3 needs gated weights + a GPU, so it is
     replaced here) · everything else -> detection crop (E14). Any failure falls back to the crop.
  No automatic judge in this trial: a human reviews the 50 at /photo-pilot?run=trial50.

    .venv/bin/python -I stages/00-trial-50/run_trial.py                         # trial 1: per-type methods
    .venv/bin/python -I stages/00-trial-50/run_trial.py --variant cutout-all    # trial 2: box-limited cut-out for
                                                     # every pack type, no router -> stages/01-cutout-all/out/
    .venv/bin/python -I stages/00-trial-50/run_trial.py --variant big           # trial 3: full BiRefNet + isnet gap
                                                     # filling + soft edges -> stages/02-big-model/out/
    .venv/bin/python -I stages/00-trial-50/run_trial.py --variant bitefix       # trial 4: trial 3 + colour-based bite
                    # repair + partial-pack check -> stages/03-bite-fix/out/ (model masks cached in out/masks/)

Outputs (git-ignored): stages/00-trial-50/out/  ·  state: work/state.sqlite (tables products, candidates)
"""
import argparse
import gzip
import io
import json
import sqlite3
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import onnxruntime as ort
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq
from PIL import Image, ImageDraw, ImageFilter, ImageOps
from scipy import ndimage
from scipy.spatial import ConvexHull
from skimage import measure, morphology, transform

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent  # Foods/
sys.path.insert(0, str(ROOT / "tools" / "photos"))   # our own modules
sys.path.insert(0, str(ROOT / "tools" / "browser"))
from cleanup_pilot import select_products  # noqa: E402
from crop_pilot import CROP_MODEL, FRONT_MODEL, MIN_BOX_CONF, compose as crop_compose, detect_product, front_score  # noqa: E402
from foods_browser import image_folder  # noqa: E402

OUT = HERE / "out"
STATE_DB = ROOT / "work" / "state.sqlite"
PARQUET = ROOT / "openfoodfacts" / "food.parquet"
CLIP_MODEL = ROOT / "work" / "models" / "off-clip" / "model.onnx"
CLIP_TOKENIZER = ROOT / "work" / "models" / "off-clip" / "tokenizer.json"
S3 = "https://openfoodfacts-images.s3.eu-west-3.amazonaws.com/data"
WEB = "https://images.openfoodfacts.org/images/products"  # fallback only when S3 lags (code s3_lag)
USER_AGENT = "FoodImagePipelineTrial/0.1"  # generic client name
PIPELINE_VERSION = "trial-50.1"
APP_LANGS = ["el", "en"]  # ASSUMPTION for the trial (handoff v2 §5 Q3, not confirmed yet)
CANVAS = 512
MARGIN = 0.08
BLUR_OK = 100.0           # variance of Laplacian on the 400 px photo; below this counts as soft
NEAR_TIE = 0.05           # candidates within this score of the best are "tied"
MIN_LONG_SIDE = 400
MIN_SOLIDITY = 0.90       # cut-out mask area / its convex hull: lower means a bite or notch in the pack
# trial 4 (bite repair + partial-pack check)
REPAIR_MIN = 0.002        # ignore repairs smaller than 0.2 % of the mask (noise)
PACK_VOTE = 1.5           # a gap pixel is "pack" when its colour is this much more likely next to the pack than in the background
MIN_EXTENT = 0.90         # the cut-out must span >= 90 % of the product box's width and height

SHAPE_MAP = {  # packaging_shapes_tags -> pack type (lids, caps, labels etc. are ignored)
    "en:box": "box", "en:brick": "box", "en:carton": "box", "en:case": "box",
    "en:can": "can", "en:bottle": "bottle",
    "en:jar": "jar_tub", "en:pot": "jar_tub", "en:tub": "jar_tub",
    "en:bag": "bag", "en:packet": "bag", "en:wrapper": "bag", "en:sachet": "bag", "en:pouch": "bag", "en:film": "bag",
    "en:tray": "other", "en:multipack": "multipack",
}
SHAPE_PRIORITY = ["multipack", "box", "can", "bottle", "jar_tub", "bag", "other"]
CLIP_PROMPTS = {  # v2: product-photo wording; v1 ("a photo of a …") sent most products to multipack / loose
    "box": ["a product photo of a cardboard box", "a product photo of a rectangular carton box package"],
    "can": ["a product photo of an aluminium drink can", "a product photo of a tin can of food"],
    "bottle": ["a product photo of a bottle", "a product photo of a plastic bottle", "a product photo of a glass bottle"],
    "bag": ["a product photo of a plastic bag of food", "a product photo of a bag of chips",
            "a product photo of a flexible pouch", "a product photo of a wrapped chocolate bar"],
    "jar_tub": ["a product photo of a glass jar", "a product photo of a plastic tub", "a product photo of a yogurt pot"],
    "multipack": ["a product photo of a multipack of several identical products"],
    "loose": ["a photo of fresh unpackaged food"],
}
CLIP_MIN_PROB = 0.50  # below this the type is "other" -> crop (misroutes must end at the crop)
METHOD_BY_TYPE = {"box": "rectify", "can": "cutout", "bottle": "cutout"}  # everything else: crop

INFO_CODES = {"lang_variant", "front_changed", "rotated", "router_clip", "s3_lag", "bite_repaired", "repair_reverted"}  # informational, not problems
REASONS = {  # reason codes used in this trial (handoff v2 §3)
    "download_failed": "the chosen photo could not be downloaded → category icon",
    "s3_lag": "photos not in the S3 archive yet → fetched from the web server",
    "no_image": "no photo at all → category icon",
    "no_front": "photos exist but none is a usable front → category icon",
    "low_res": "every candidate is < 400 px",
    "lang_variant": "several front_<lang> photos exist",
    "front_changed": "best-of-N picked a different photo than the OFF-selected front",
    "rotated": "rotated upright using the OCR text direction",
    "person_or_nsfw": "a candidate was dropped by the safe-search flags",
    "router_clip": "pack type from CLIP (no packaging data)",
    "router_unsure": "CLIP not sure → treated as other",
    "bad_quad": "box rectification: no clean 4-corner front → crop",
    "aspect_distort": "box rectification would distort the shape > 25 % → crop",
    "printed_food": "cut-out mask covers < 50 % of the product box (probably the printed food) → crop",
    "multi_instance": "cut-out found several similar objects → crop",
    "mask_bad": "cut-out mask empty or broken → crop",
    "mask_notch": f"cut-out mask has a bite or notch (solidity < {MIN_SOLIDITY}) → crop",
    "partial_pack": f"cut-out spans < {int(MIN_EXTENT * 100)} % of the product box's width or height (flag only: on shelves the box includes neighbours)",
    "repair_reverted": "the bite repair would have triggered a fallback, so the trial 3 mask was kept",
    "touches_frame": "the product touches 2+ edges of the photo (the photo may cut off the pack)",
    "bite_repaired": "gaps that look like the pack (not the background) were filled back in",
}


# ----------------------------------------------------------------------------- data
def fetch(url, dest, max_bytes=30 * 1024 * 1024):
    """Download once (cached). Returns bytes or None."""
    if dest.exists():
        return dest.read_bytes()
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = resp.read(max_bytes + 1)
            if len(data) > max_bytes:
                return None
            dest.parent.mkdir(parents=True, exist_ok=True)
            tmp = dest.with_suffix(dest.suffix + ".part")
            tmp.write_bytes(data)
            tmp.replace(dest)
            return data
        except urllib.error.HTTPError as e:
            if e.code in (403, 404):
                return None
            time.sleep(1 + attempt)
        except Exception:
            time.sleep(1 + attempt)
    return None


def product_rows(codes):
    """images + packaging_shapes_tags for the given barcodes, straight from the parquet."""
    want, found = set(codes), {}
    pf = pq.ParquetFile(PARQUET)
    for i in range(pf.num_row_groups):
        col = pf.read_row_group(i, columns=["code"]).column("code")
        mask = pc.is_in(col, value_set=pa.array(list(want - set(found))))
        if not pc.any(mask).as_py():
            continue
        tb = pf.read_row_group(i, columns=["code", "images", "packaging_shapes_tags"]).filter(mask)
        for code, images, shapes in zip(*(tb.column(c).to_pylist() for c in ("code", "images", "packaging_shapes_tags"))):
            found[code] = {"images": images or [], "shapes": shapes or []}
        if len(found) == len(want):
            break
    return found


def candidates_for(code, images):
    """Every raw upload (numeric key) with its upload time, size and the front_<lang> slots that use it."""
    front_langs = {}
    for im in images:
        if im["key"].startswith("front_") and im["imgid"] is not None:
            front_langs.setdefault(str(im["imgid"]), []).append(im["key"][6:])
    out = []
    for im in images:
        if not im["key"].isdigit():
            continue
        full = (im["sizes"] or {}).get("full") or {}
        out.append({"barcode": code, "image_id": im["key"], "uploaded_at": im["uploaded_t"] or 0,
                    "width": full.get("w") or 0, "height": full.get("h") or 0,
                    "langs": sorted(front_langs.get(im["key"], []))})
    return out, front_langs


# ----------------------------------------------------------------------------- OCR helpers
def ocr_rotation(ocr):
    """Degrees to rotate (PIL, counter-clockwise) so most text reads left-to-right. 0 if unsure."""
    try:
        words = ocr["responses"][0].get("textAnnotations", [])[1:]
    except (KeyError, IndexError, TypeError):
        return 0
    votes = {0: 0.0, 90: 0.0, 180: 0.0, 270: 0.0}
    for w in words:
        v = w.get("boundingPoly", {}).get("vertices", [])
        if len(v) < 2:
            continue
        dx = v[1].get("x", 0) - v[0].get("x", 0)
        dy = v[1].get("y", 0) - v[0].get("y", 0)
        length = (dx * dx + dy * dy) ** 0.5
        if length < 1:
            continue
        ang = (np.degrees(np.arctan2(dy, dx)) + 360) % 360  # image coords: y points down
        votes[int(((ang + 45) % 360) // 90) * 90] += length
    total = sum(votes.values())
    if len(words) < 5 or total == 0:
        return 0
    best = max(votes, key=votes.get)
    if votes[best] / total < 0.6:
        return 0
    # text running down (90) means the photo was turned clockwise -> rotate back counter-clockwise
    return {0: 0, 90: 90, 180: 180, 270: -90}[best]


def unsafe(ocr):
    try:
        ss = ocr["responses"][0].get("safeSearchAnnotation", {})
    except (KeyError, IndexError, TypeError):
        return False
    return any(ss.get(k) in ("LIKELY", "VERY_LIKELY") for k in ("adult", "violence"))  # "racy" flagged a cola bottle


# ----------------------------------------------------------------------------- scoring
def blur_score(img):
    g = np.asarray(img.convert("L"), dtype=np.float32)
    return float(ndimage.laplace(g).var())


def candidate_score(c):
    if c["p_front"] < 0.5 or c["box_score"] < MIN_BOX_CONF or max(c["width"], c["height"]) < MIN_LONG_SIDE:
        return None
    sharp = min(1.0, c["blur"] / BLUR_OK)
    return round(c["p_front"] * c["box_score"] * (0.5 + 0.5 * sharp), 4)


def pick_best(cands, off_front=None):
    """Best-scoring usable candidate. Near-ties: keep OFF's selected front (a person chose it; trial 1 showed
    'newest first' swapping clean photos for hand-held ones), then the newest upload, then the app language."""
    scored = [c for c in cands if c.get("score") is not None]
    if not scored:
        return None
    top = max(c["score"] for c in scored)
    tied = [c for c in scored if c["score"] >= top - NEAR_TIE]
    for c in tied:
        if c["image_id"] == off_front:
            return c
    lang_rank = lambda c: min([APP_LANGS.index(l) for l in c["langs"] if l in APP_LANGS] or [len(APP_LANGS)])  # noqa: E731
    tied.sort(key=lambda c: (-c["uploaded_at"], lang_rank(c), -c["score"]))
    return tied[0]


# ----------------------------------------------------------------------------- router
class ClipRouter:
    MEAN = np.array([0.48145466, 0.4578275, 0.40821073], dtype=np.float32)
    STD = np.array([0.26862954, 0.26130258, 0.27577711], dtype=np.float32)

    def __init__(self):
        from tokenizers import Tokenizer
        tok = Tokenizer.from_file(str(CLIP_TOKENIZER))
        tok.enable_padding(pad_id=49407, pad_token="<|endoftext|>")
        self.labels, prompts = [], []
        for label, ps in CLIP_PROMPTS.items():
            for p in ps:
                self.labels.append(label)
                prompts.append(p)
        enc = tok.encode_batch(prompts)
        self.ids = np.array([e.ids for e in enc], dtype=np.int64)
        self.mask = np.array([e.attention_mask for e in enc], dtype=np.int64)
        opts = ort.SessionOptions()
        opts.log_severity_level = 3
        self.sess = ort.InferenceSession(str(CLIP_MODEL), opts, providers=["CPUExecutionProvider"])

    def classify(self, img):
        side = max(img.size)
        sq = Image.new("RGB", (side, side), "white")
        sq.paste(img, ((side - img.width) // 2, (side - img.height) // 2))
        x = (np.asarray(sq.resize((224, 224), Image.BICUBIC), dtype=np.float32) / 255.0 - self.MEAN) / self.STD
        logits = self.sess.run(["logits_per_image"], {"input_ids": self.ids, "attention_mask": self.mask,
                                                      "pixel_values": x.transpose(2, 0, 1)[None]})[0][0]
        labels = list(CLIP_PROMPTS)  # best prompt per label, then softmax over labels
        best_logit = np.array([max(l for lab, l in zip(self.labels, logits) if lab == label) for label in labels])
        prob = np.exp(best_logit - best_logit.max())
        prob /= prob.sum()
        best = int(prob.argmax())
        return labels[best], round(float(prob[best]), 3)


def route(shapes, clip, region):
    mapped = [SHAPE_MAP[s] for s in shapes if s in SHAPE_MAP]
    if mapped:
        return sorted(mapped, key=SHAPE_PRIORITY.index)[0], "off", None, []
    label, prob = clip.classify(region)
    if prob < CLIP_MIN_PROB:
        return "other", "clip", prob, ["router_clip", "router_unsure"]
    return label, "clip", prob, ["router_clip"]


# ----------------------------------------------------------------------------- processors
def padded_region(img, box, pad=0.08):
    x0, y0, x1, y1 = box
    px, py = (x1 - x0) * pad, (y1 - y0) * pad
    rx0, ry0 = int(max(0, x0 - px)), int(max(0, y0 - py))
    rx1, ry1 = int(min(img.width, x1 + px)), int(min(img.height, y1 + py))
    return img.crop((rx0, ry0, rx1, ry1)), (rx0, ry0)


def object_mask(region, session, remove):
    """BiRefNet-lite on the detector region (= box prompt). Returns (mask at region size, scale used)."""
    small = region.copy()
    small.thumbnail((1024, 1024), Image.LANCZOS)
    alpha = np.asarray(remove(small, session=session))[:, :, 3]
    mask = alpha > 127
    if small.size != region.size:
        mask = np.asarray(Image.fromarray(mask.astype(np.uint8) * 255).resize(region.size, Image.NEAREST)) > 127
    return mask


def largest_components(mask):
    lab, n = ndimage.label(mask)
    if n == 0:
        return None, []
    sizes = ndimage.sum(mask, lab, range(1, n + 1))
    order = np.argsort(sizes)[::-1]
    return lab, [(int(i) + 1, float(sizes[i])) for i in order]


def soft_shadow_on_white(rgba):
    """Fit an RGBA object on the white square with a margin and a soft drop shadow (white-on-white safe)."""
    inner = CANVAS * (1 - 2 * MARGIN)
    s = inner / max(rgba.size)
    obj = rgba.resize((max(1, round(rgba.width * s)), max(1, round(rgba.height * s))), Image.LANCZOS)
    ox, oy = (CANVAS - obj.width) // 2, (CANVAS - obj.height) // 2
    shadow = Image.new("L", (CANVAS, CANVAS), 0)
    shadow.paste(obj.split()[3], (ox, oy + 6))
    shadow = shadow.filter(ImageFilter.GaussianBlur(9)).point(lambda v: int(v * 0.28))
    canvas = Image.composite(Image.new("RGB", (CANVAS, CANVAS), (110, 110, 110)), Image.new("RGB", (CANVAS, CANVAS), "white"), shadow)
    canvas.paste(obj, (ox, oy), obj)
    return canvas


def cutout(img, box, session, remove):
    region, _ = padded_region(img, box)
    mask = object_mask(region, session, remove)
    lab, comps = largest_components(mask)
    if not comps:
        return None, ["mask_bad"]
    reasons = []
    if len(comps) > 1 and comps[1][1] > 0.3 * comps[0][1]:
        return None, ["multi_instance"]
    keep = ndimage.binary_fill_holes(lab == comps[0][0])  # fills holes, e.g. a label printed as "background"
    bw, bh = box[2] - box[0], box[3] - box[1]
    if keep.sum() < 0.5 * bw * bh:
        return None, ["printed_food"]
    small = keep[::4, ::4]  # cans and bottles are (nearly) convex: a bite out of the edge shows up here
    if small.sum() / max(morphology.convex_hull_image(small).sum(), 1) < MIN_SOLIDITY:
        return None, ["mask_notch"]
    ys, xs = np.where(keep)
    rgba = region.convert("RGBA")
    rgba.putalpha(Image.fromarray((keep * 255).astype(np.uint8)))
    rgba = rgba.crop((int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1))
    return soft_shadow_on_white(rgba), reasons


def soft_alpha(region, session, remove):
    """The model's soft alpha (0-255) at region size; the model itself runs at <= 1024 px."""
    small = region.copy()
    small.thumbnail((1024, 1024), Image.LANCZOS)
    a = np.asarray(remove(small, session=session))[:, :, 3]
    if small.size != region.size:
        a = np.asarray(Image.fromarray(a).resize(region.size, Image.BILINEAR))
    return a


def cutout_v3(img, box, main, second, remove):
    """Trial 3: full BiRefNet mask, gaps filled from a second model (isnet) but only INSIDE the main mask's
    convex hull (fixes bites without letting in background beside bottle necks), and soft edges.
    Returns (image or None, reason codes, info)."""
    region, _ = padded_region(img, box)
    info = {}
    t = time.time()
    a_main = soft_alpha(region, main, remove)
    info["main_model_s"] = round(time.time() - t, 2)
    lab, comps = largest_components(a_main > 127)
    if not comps:
        return None, ["mask_bad"], info
    if len(comps) > 1 and comps[1][1] > 0.3 * comps[0][1]:
        return None, ["multi_instance"], info
    keep = ndimage.binary_fill_holes(lab == comps[0][0])
    if second is not None:
        t = time.time()
        other = soft_alpha(region, second, remove) > 127
        info["second_model_s"] = round(time.time() - t, 2)
        f = 4  # convex hull at 1/4 size for speed, then back to full size
        hull_small = morphology.convex_hull_image(keep[::f, ::f])
        hull = np.asarray(Image.fromarray(hull_small.astype(np.uint8) * 255).resize(region.size, Image.NEAREST)) > 127
        add = other & hull & ~keep
        merged = ndimage.binary_fill_holes(keep | add)
        lab2, _ = ndimage.label(merged)
        core = lab2[keep].max() if keep.any() else 0  # the component that contains the main mask
        merged = lab2 == core
        info["gap_filled_pct"] = round(100 * float((merged & ~keep).sum()) / max(int(keep.sum()), 1), 2)
        keep = merged
    bw, bh = box[2] - box[0], box[3] - box[1]
    if keep.sum() < 0.5 * bw * bh:
        return None, ["printed_food"], info
    small = keep[::4, ::4]
    if small.sum() / max(morphology.convex_hull_image(small).sum(), 1) < MIN_SOLIDITY:
        return None, ["mask_notch"], info
    # soft edges: solid inside, the model's own soft alpha in a thin band along the outline
    band = ndimage.binary_dilation(keep, iterations=2) & ~ndimage.binary_erosion(keep, iterations=2)
    alpha = np.where(keep, 255, 0).astype(np.uint8)
    alpha[band] = a_main[band]
    alpha[ndimage.binary_erosion(keep, iterations=2)] = 255
    ys, xs = np.where(alpha > 10)
    rgba = region.convert("RGBA")
    rgba.putalpha(Image.fromarray(alpha))
    rgba = rgba.crop((int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1))
    return soft_shadow_on_white(rgba), [], info


def cached_alpha(region, path, get_session, remove):
    """Same as soft_alpha(), but the model's small-size alpha is cached as a PNG (lossless), so re-runs with new
    post-processing give identical masks without running the model again."""
    small_img = region.copy()
    small_img.thumbnail((1024, 1024), Image.LANCZOS)
    if path.exists():
        small = np.asarray(Image.open(path))
    else:
        small = np.asarray(remove(small_img, session=get_session()))[:, :, 3]
        path.parent.mkdir(parents=True, exist_ok=True)
        Image.fromarray(small).save(path)
    if small_img.size != region.size:
        small = np.asarray(Image.fromarray(small).resize(region.size, Image.BILINEAR))
    return small


def colour_repair(region, keep, box_r):
    """Fill gaps (inside the hull or the product box) whose colours look like the pack next to them rather than
    the background. Bites where printed food meets the pack edge get filled; background beside a bottle neck does
    not. Works at <= 512 px. Returns the added pixels at full region size, or None."""
    W, H = region.size
    sc = min(1.0, 512 / max(W, H))
    w, h = max(1, round(W * sc)), max(1, round(H * sc))
    pix = np.asarray(region.resize((w, h), Image.BILINEAR)).astype(np.int32)
    k = np.asarray(Image.fromarray(keep.astype(np.uint8) * 255).resize((w, h), Image.NEAREST)) > 127
    if not k.any():
        return None
    hull = morphology.convex_hull_image(k)
    bx0, by0, bx1, by1 = (v * sc for v in box_r)
    m = 0.01 * max(bx1 - bx0, by1 - by0)  # 1 % inside the box edge
    boxm = np.zeros((h, w), bool)
    boxm[max(0, int(by0 + m)):int(by1 - m), max(0, int(bx0 + m)):int(bx1 - m)] = True
    allowed = hull | boxm
    cand = allowed & ~k
    if cand.sum() < REPAIR_MIN * k.sum():
        return None
    d = max(3, int(0.03 * max(w, h)))
    near = ndimage.binary_dilation(cand, iterations=d)
    pack_ring, bg_ring = near & k, near & ~allowed
    if bg_ring.sum() < 50:
        bg_ring = ~allowed
    q = pix // 16
    idx = q[..., 0] * 256 + q[..., 1] * 16 + q[..., 2]

    def hist(mask):
        hst = np.bincount(idx[mask], minlength=4096).astype(np.float64) + 1.0
        return hst / hst.sum()

    hp = hist(pack_ring)
    hb = hist(bg_ring) if bg_ring.sum() >= 50 else np.full(4096, 1 / 4096)  # no background visible: pack colours win
    is_pack = ndimage.binary_opening(cand & (hp[idx] > PACK_VOTE * hb[idx]), iterations=1)
    merged = ndimage.binary_fill_holes(k | is_pack)
    lab, _ = ndimage.label(merged)
    added = (lab == lab[k].max()) & ~k
    if added.sum() < REPAIR_MIN * k.sum():
        return None
    return np.asarray(Image.fromarray(added.astype(np.uint8) * 255).resize((W, H), Image.BILINEAR)) > 127


def cutout_v4(img, box, alpha_main, alpha_second):
    """Trial 4 = trial 3 (identical when nothing new triggers) + colour-based bite repair + partial-pack check +
    touches-frame flag. alpha_main / alpha_second: functions region -> soft alpha at region size."""
    region, (rx0, ry0) = padded_region(img, box)
    info, reasons = {}, []
    W, H = img.size
    if sum([box[0] <= 0.01 * W, box[1] <= 0.01 * H, box[2] >= 0.99 * W, box[3] >= 0.99 * H]) >= 2:
        reasons.append("touches_frame")
    t = time.time()
    a_main = alpha_main(region)
    info["main_model_s"] = round(time.time() - t, 2)
    lab, comps = largest_components(a_main > 127)
    if not comps:
        return None, reasons + ["mask_bad"], info
    if len(comps) > 1 and comps[1][1] > 0.3 * comps[0][1]:
        return None, reasons + ["multi_instance"], info
    keep = ndimage.binary_fill_holes(lab == comps[0][0])
    model_keep = keep.copy()
    t = time.time()
    other = alpha_second(region) > 127
    info["second_model_s"] = round(time.time() - t, 2)
    f = 4  # trial 3 gap filling from the second model, inside the main mask's hull
    hull_small = morphology.convex_hull_image(keep[::f, ::f])
    hull = np.asarray(Image.fromarray(hull_small.astype(np.uint8) * 255).resize(region.size, Image.NEAREST)) > 127
    merged = ndimage.binary_fill_holes(keep | (other & hull & ~keep))
    lab2, _ = ndimage.label(merged)
    keep = lab2 == (lab2[keep].max() if keep.any() else 0)
    # NEW: colour-based bite repair
    box_r = (box[0] - rx0, box[1] - ry0, box[2] - rx0, box[3] - ry0)
    bw, bh = box_r[2] - box_r[0], box_r[3] - box_r[1]

    def check(mask):
        """Trial 3's fallback checks. Returns (reason or None, solidity)."""
        if mask.sum() < 0.5 * bw * bh:
            return "printed_food", None
        sm = mask[::4, ::4]
        sol = float(sm.sum() / max(morphology.convex_hull_image(sm).sum(), 1))
        return ("mask_notch" if sol < MIN_SOLIDITY else None), round(sol, 3)

    added = colour_repair(region, keep, box_r)
    repaired = None
    fail, sol = check(keep)
    if added is not None:
        merged = ndimage.binary_fill_holes(keep | added)
        lab3, _ = ndimage.label(merged)
        new_keep = lab3 == lab3[keep].max()
        fail4, sol4 = check(new_keep)
        if fail4 is None or fail is not None:  # keep the repair unless it causes a NEW fallback
            repaired = new_keep & ~keep
            info["repair_pct"] = round(100 * float(repaired.sum()) / max(int(keep.sum()), 1), 2)
            keep, fail, sol = new_keep, fail4, sol4
            reasons.append("bite_repaired")
        else:
            reasons.append("repair_reverted")
    info["solidity"] = sol
    # NEW: partial pack (flag only; it caught no real case and the box includes shelf neighbours)
    ys, xs = np.where(keep)
    cov_w = (min(xs.max() + 1, box_r[2]) - max(xs.min(), box_r[0])) / bw
    cov_h = (min(ys.max() + 1, box_r[3]) - max(ys.min(), box_r[1])) / bh
    info["extent"] = round(float(min(cov_w, cov_h)), 3)
    if min(cov_w, cov_h) < MIN_EXTENT:
        reasons.append("partial_pack")
    if fail is not None:
        return None, reasons + [fail], info
    # soft edges exactly as trial 3; hard edge where we repaired (the model's alpha is ~0 there)
    band = ndimage.binary_dilation(keep, iterations=2) & ~ndimage.binary_erosion(keep, iterations=2)
    alpha = np.where(keep, 255, 0).astype(np.uint8)
    alpha[band] = a_main[band]
    alpha[ndimage.binary_erosion(keep, iterations=2)] = 255
    if repaired is not None:
        near_rep = ndimage.binary_dilation(repaired, iterations=3)
        alpha[near_rep & keep] = 255
    ys, xs = np.where(alpha > 10)
    rgba = region.convert("RGBA")
    rgba.putalpha(Image.fromarray(alpha))
    rgba = rgba.crop((int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1))
    info["model_px_changed"] = int((keep != model_keep).sum())
    return soft_shadow_on_white(rgba), reasons, info


def order_quad(pts):
    """TL, TR, BR, BL."""
    s, d = pts.sum(1), np.diff(pts, axis=1).ravel()
    return np.array([pts[s.argmin()], pts[d.argmin()], pts[s.argmax()], pts[d.argmax()]], dtype=np.float64)


def rectify(img, box, session, remove):
    region, _ = padded_region(img, box)
    mask = object_mask(region, session, remove)
    lab, comps = largest_components(mask)
    if not comps:
        return None, ["mask_bad"]
    keep = ndimage.binary_fill_holes(lab == comps[0][0])
    bw, bh = box[2] - box[0], box[3] - box[1]
    if keep.sum() < 0.5 * bw * bh:
        return None, ["printed_food"]
    contour = max(measure.find_contours(keep.astype(np.float32), 0.5), key=len)[:, ::-1]  # (x, y)
    hull = contour[ConvexHull(contour).vertices]
    perim = np.sum(np.linalg.norm(np.diff(np.vstack([hull, hull[:1]]), axis=0), axis=1))
    quad = None
    for tol in np.linspace(0.005, 0.08, 40) * perim:
        approx = measure.approximate_polygon(np.vstack([hull, hull[:1]]), tolerance=tol)[:-1]
        if len(approx) == 4:
            quad = approx
            break
        if len(approx) < 4:
            break
    if quad is None:
        return None, ["bad_quad"]
    q = order_quad(quad)
    top, bottom = np.linalg.norm(q[1] - q[0]), np.linalg.norm(q[2] - q[3])
    left, right = np.linalg.norm(q[3] - q[0]), np.linalg.norm(q[2] - q[1])
    if min(top, bottom) < 0.3 * max(top, bottom) or min(left, right) < 0.3 * max(left, right):
        return None, ["bad_quad"]
    quad_area = 0.5 * abs(np.dot(q[:, 0], np.roll(q[:, 1], 1)) - np.dot(q[:, 1], np.roll(q[:, 0], 1)))
    if keep.sum() < 0.85 * quad_area or keep.sum() > 1.15 * quad_area:  # the object is not a 4-cornered card
        return None, ["bad_quad"]
    w, h = (top + bottom) / 2, (left + right) / 2
    if abs(np.log((w / h) / (bw / bh))) > np.log(1.25):
        return None, ["aspect_distort"]
    W, H = int(round(w)), int(round(h))
    tform = transform.ProjectiveTransform.from_estimate(np.array([[0, 0], [W - 1, 0], [W - 1, H - 1], [0, H - 1]], dtype=np.float64), q)
    warped = transform.warp(np.asarray(region), tform, output_shape=(H, W), order=1, preserve_range=True)
    flat = Image.fromarray(np.clip(warped, 0, 255).astype(np.uint8)).convert("RGBA")
    return soft_shadow_on_white(flat), []


def icon_placeholder():
    im = Image.new("RGB", (CANVAS, CANVAS), "white")
    d = ImageDraw.Draw(im)
    d.ellipse((156, 156, 356, 356), outline=(190, 190, 190), width=6)
    d.text((196, 380), "category icon", fill=(150, 150, 150))
    return im


# ----------------------------------------------------------------------------- state store
SCHEMA = """
CREATE TABLE IF NOT EXISTS products (
  barcode TEXT PRIMARY KEY, chosen_image_id TEXT, image_rev INTEGER, pack_type TEXT, type_source TEXT,
  method TEXT, judge_verdict TEXT, judge_conf REAL, judge_model TEXT, prompt_version TEXT, human_verdict TEXT,
  reason_codes TEXT, output_path TEXT, output_hash TEXT, source_url TEXT, pipeline_version TEXT, processed_at TEXT);
CREATE TABLE IF NOT EXISTS candidates (
  barcode TEXT, image_id TEXT, rev INTEGER, lang TEXT, uploaded_at INTEGER, p_front REAL, box_score REAL,
  box_area REAL, blur REAL, width INTEGER, height INTEGER, rank INTEGER, PRIMARY KEY (barcode, image_id));
"""


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--n", type=int, default=50)
    ap.add_argument("--workers", type=int, default=4, help="parallel downloads (keep it polite)")
    ap.add_argument("--variant", choices=["typed", "cutout-all", "big", "bitefix"], default="typed",
                    help="typed = router + per-type method (trial 1); cutout-all = box-limited cut-out for every type (trial 2)")
    args = ap.parse_args()
    cutout_all = args.variant in ("cutout-all", "big", "bitefix")  # these skip the router and cut out every pack type
    big = args.variant in ("big", "bitefix")
    bitefix = args.variant == "bitefix"
    # photos are cached in trial 1's folder and shared; results go to the variant's own folder
    res = {"typed": OUT, "cutout-all": ROOT / "stages" / "01-cutout-all" / "out",
           "big": ROOT / "stages" / "02-big-model" / "out",
           "bitefix": ROOT / "stages" / "03-bite-fix" / "out"}[args.variant]
    prev = {"cutout-all": (OUT, "trial 1"), "big": (ROOT / "stages" / "01-cutout-all" / "out", "trial 2"),
            "bitefix": (ROOT / "stages" / "02-big-model" / "out", "trial 3")}.get(args.variant)
    version = PIPELINE_VERSION + {"typed": "", "cutout-all": ".cutout-all", "big": ".big", "bitefix": ".bitefix"}[args.variant]
    main_model = "birefnet-general" if big else "birefnet-general-lite"

    import hashlib
    for sub in ("cands", "raw"):
        (OUT / sub).mkdir(parents=True, exist_ok=True)
    for sub in ("before", "after"):
        (res / sub).mkdir(parents=True, exist_ok=True)
    timings = {k: 0.0 for k in ("data", "download_candidates", "score_candidates", "download_full", "route", "process")}

    t = time.time()
    products = select_products(200)[: args.n]
    rows = product_rows([p["code"] for p in products])
    timings["data"] = time.time() - t
    print(f"{len(products)} products, product data loaded in {timings['data']:.0f}s", flush=True)

    opts = ort.SessionOptions()
    opts.log_severity_level = 3
    det = ort.InferenceSession(str(CROP_MODEL), opts, providers=["CPUExecutionProvider"])
    cls = ort.InferenceSession(str(FRONT_MODEL), opts, providers=["CPUExecutionProvider"])
    clip = None if cutout_all else ClipRouter()
    rembg_session, rembg_remove, second_session = None, None, None

    # 1a. download every candidate (400 px + OCR json) in parallel
    jobs = []
    per_product = {}
    for p in products:
        cands, front_langs = candidates_for(p["code"], rows.get(p["code"], {}).get("images", []))
        per_product[p["code"]] = (cands, front_langs)
        folder = image_folder(p["code"])
        for c in cands:
            base = OUT / "cands" / p["code"]
            jobs.append((p["code"], f"{folder}/{c['image_id']}", base / f"{c['image_id']}.400.jpg", ".400.jpg"))
            jobs.append((p["code"], f"{folder}/{c['image_id']}", base / f"{c['image_id']}.json.gz", ".json.gz"))
    s3_lag = set()

    def get(job):
        code, stem, dest, suffix = job
        lag_marker = dest.with_suffix(dest.suffix + ".from_web")
        if lag_marker.exists():  # cached earlier from the web server
            s3_lag.add(code)
            return
        if fetch(f"{S3}/{stem}{suffix}", dest) is not None:
            return
        # not in the monthly S3 sync yet: same file from the web server (OCR is plain .json there)
        if suffix == ".json.gz":
            data = fetch(f"{WEB}/{stem}.json", dest.with_suffix(".plain"))
            if data is not None:
                dest.write_bytes(gzip.compress(data))
        elif fetch(f"{WEB}/{stem}{suffix}", dest) is not None:
            lag_marker.touch()
            s3_lag.add(code)

    t = time.time()
    with ThreadPoolExecutor(args.workers) as pool:
        list(pool.map(get, jobs))
    timings["download_candidates"] = time.time() - t
    n_cands = sum(len(v[0]) for v in per_product.values())
    print(f"{n_cands} candidate photos ({len(jobs)} files) in {timings['download_candidates']:.0f}s", flush=True)

    # 1b. score every candidate (made upright with the OCR text direction first); pick the best per product
    pre, best_by_code = {}, {}
    t_all = time.time()
    for p in products:
        code = p["code"]
        cands = per_product[code][0]
        found, t = [], time.time()
        for c in cands:
            base = OUT / "cands" / code
            f400 = base / f"{c['image_id']}.400.jpg"
            fj = base / f"{c['image_id']}.json.gz"
            c.update(p_front=0.0, box_score=0.0, box_area=0.0, blur=0.0, rot=0, score=None)
            if not f400.exists():
                continue
            ocr = None
            if fj.exists():
                try:
                    ocr = json.loads(gzip.decompress(fj.read_bytes()))
                except Exception:
                    ocr = None
            if ocr and unsafe(ocr):
                found.append("person_or_nsfw")
                continue
            img = ImageOps.exif_transpose(Image.open(f400)).convert("RGB")
            c["rot"] = ocr_rotation(ocr) if ocr else 0
            if c["rot"]:
                img = img.rotate(c["rot"], expand=True)
            c["p_front"] = round(front_score(cls, img), 3)
            box, conf = detect_product(det, img)
            c["box_score"] = round(conf, 3)
            c["box_area"] = round((box[2] - box[0]) * (box[3] - box[1]) / (img.width * img.height), 3) if box else 0.0
            c["blur"] = round(blur_score(img), 1)
            c["score"] = candidate_score(c)
        off_front = next((str(im["imgid"]) for im in rows.get(code, {}).get("images", [])
                          if im["key"] == p.get("front_key") and im["imgid"] is not None), None)
        best_by_code[code] = pick_best(cands, off_front)
        pre[code] = {"reasons": sorted(set(found)), "secs": time.time() - t}
    timings["score_candidates"] = time.time() - t_all
    print(f"scored in {timings['score_candidates']:.0f}s", flush=True)

    # 2. full-size photo of every winner, downloaded in the background while we process
    def get_full(code):
        stem = f"{image_folder(code)}/{best_by_code[code]['image_id']}"
        dest = OUT / "raw" / f"{code}_{best_by_code[code]['image_id']}.jpg"
        return fetch(f"{S3}/{stem}.jpg", dest) or fetch(f"{WEB}/{stem}.jpg", dest)

    dl_pool = ThreadPoolExecutor(args.workers)
    full_photos = {code: dl_pool.submit(get_full, code) for code, b in best_by_code.items() if b}

    con = sqlite3.connect(STATE_DB)
    con.executescript(SCHEMA)
    records = []
    for i, p in enumerate(products, 1):
        code = p["code"]
        cands, front_langs = per_product[code]
        folder = image_folder(code)
        rec = {k: p[k] for k in ("code", "name", "brand")}
        reasons, tt = [], {}
        off_front_imgid = None
        off_key = p.get("front_key")
        for im in rows.get(code, {}).get("images", []):
            if im["key"] == off_key and im["imgid"] is not None:
                off_front_imgid = str(im["imgid"])
        if sum(1 for k in front_langs.values() for _ in k) > 1:
            reasons.append("lang_variant")
        if code in s3_lag:
            reasons.append("s3_lag")

        reasons += pre[code]["reasons"]
        tt["score"] = round(pre[code]["secs"], 2)
        best = best_by_code[code]
        ranked = sorted(cands, key=lambda c: -(c["score"] or -1))
        for rank, c in enumerate(ranked, 1):
            con.execute("INSERT OR REPLACE INTO candidates VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                        (code, c["image_id"], None, ",".join(c["langs"]) or None, c["uploaded_at"], c["p_front"],
                         c["box_score"], c["box_area"], c["blur"], c["width"], c["height"], rank))
        rec["n_candidates"] = len(cands)
        rec["off_front"] = off_front_imgid

        out_path = res / "after" / f"{code}.jpg"
        data = None
        if best is not None:  # 2. full photo of the winner (downloaded in the background)
            t = time.time()
            data = full_photos[code].result()
            tt["download_full"] = time.time() - t
            timings["download_full"] += tt["download_full"]
            if data is None:
                reasons.append("download_failed")
                best = None
        if best is None:
            if "download_failed" in reasons:
                pass
            else:
                reasons.append("no_image" if not cands else ("low_res" if all(max(c["width"], c["height"]) < MIN_LONG_SIDE for c in cands) else "no_front"))
            icon_placeholder().save(out_path, quality=88)
            Image.new("RGB", (CANVAS, CANVAS), "white").save(res / "before" / f"{code}.jpg", quality=88)
            rec.update(method="icon", pack_type=None, type_source=None, chosen=None)
        else:
            rec["chosen"] = best["image_id"]
            rec["changed_front"] = best["image_id"] != off_front_imgid
            if rec["changed_front"]:
                reasons.append("front_changed")
            img = ImageOps.exif_transpose(Image.open(io.BytesIO(data))).convert("RGB")
            if best["rot"]:
                img = img.rotate(best["rot"], expand=True)
                reasons.append("rotated")
            rec["orig_w"], rec["orig_h"] = img.size
            before = img.copy()
            before.thumbnail((CANVAS, CANVAS), Image.LANCZOS)
            before.save(res / "before" / f"{code}.jpg", quality=88)
            box, conf = detect_product(det, img)

            # 3. route
            t = time.time()
            region = padded_region(img, box, 0.05)[0] if box else img
            if cutout_all:  # no router: pack type only from the product data, for the record
                mapped = [SHAPE_MAP[x] for x in rows.get(code, {}).get("shapes", []) if x in SHAPE_MAP]
                pack_type, type_source, type_prob, r = (sorted(mapped, key=SHAPE_PRIORITY.index)[0] if mapped else None), ("off" if mapped else None), None, []
            else:
                pack_type, type_source, type_prob, r = route(rows.get(code, {}).get("shapes", []), clip, region)
            reasons += r
            tt["route"] = time.time() - t
            timings["route"] += tt["route"]

            # 4. process
            t = time.time()
            method = ("cutout" if cutout_all else METHOD_BY_TYPE.get(pack_type, "crop")) if box else "crop"
            result = None
            if method in ("rectify", "cutout"):
                if rembg_session is None:
                    from rembg import new_session, remove
                    rembg_session, rembg_remove = new_session(main_model), remove
                    second_session = new_session("isnet-general-use") if big else None
                if bitefix:  # masks cached per product + photo + model, so post-processing tweaks re-run in seconds
                    mdir = res / "masks"

                    def get_main():
                        return rembg_session

                    def get_second():
                        return second_session

                    result, r, extra = cutout_v4(
                        img, box,
                        lambda reg: cached_alpha(reg, mdir / f"{code}_{best['image_id']}_{main_model}.png", get_main, rembg_remove),
                        lambda reg: cached_alpha(reg, mdir / f"{code}_{best['image_id']}_isnet-general-use.png", get_second, rembg_remove))
                    tt.update({k: v for k, v in extra.items() if k.endswith("_s")})
                    rec.update({k: v for k, v in extra.items() if not k.endswith("_s")})
                elif big:
                    result, r, extra = cutout_v3(img, box, rembg_session, second_session, rembg_remove)
                    tt.update({k: v for k, v in extra.items() if k.endswith("_s")})
                    rec.update({k: v for k, v in extra.items() if not k.endswith("_s")})
                else:
                    fn = rectify if method == "rectify" else cutout
                    result, r = fn(img, box, rembg_session, rembg_remove)
                reasons += r
                if result is None:
                    method = "crop"
            if result is None:
                result = crop_compose(img, box)
            result.save(out_path, quality=88, optimize=True)
            tt["process"] = time.time() - t
            timings["process"] += tt["process"]
            rec.update(method=method, pack_type=pack_type, type_source=type_source, type_prob=type_prob,
                       box_conf=round(conf, 3), front_prob=best["p_front"])

        rec["flags"] = [r for r in reasons if r not in INFO_CODES]
        rec["info"] = [r for r in reasons if r in INFO_CODES]
        rec["timings"] = {k: round(v, 2) for k, v in tt.items()}
        rec["secs"] = round(sum(v for k, v in tt.items() if not k.endswith("_s")), 2)
        rec["after_kb"] = round(out_path.stat().st_size / 1024, 1)
        records.append(rec)
        h = hashlib.sha256(out_path.read_bytes()).hexdigest()[:8]
        con.execute("INSERT OR REPLACE INTO products (barcode, chosen_image_id, pack_type, type_source, method, reason_codes,"
                    " output_path, output_hash, source_url, pipeline_version, processed_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                    (code, rec.get("chosen"), rec.get("pack_type"), rec.get("type_source"), rec["method"], json.dumps(reasons),
                     str(out_path.relative_to(ROOT)), h,
                     f"{S3}/{folder}/{rec['chosen']}.jpg" if rec.get("chosen") else None, version, time.strftime("%Y-%m-%d %H:%M:%S")))
        con.commit()
        print(f"  {i:2d}/{len(products)} {code:>14} {rec['method']:8} {str(rec.get('pack_type')):9} {rec['secs']:5.1f}s  {','.join(reasons)}", flush=True)
    con.close()
    dl_pool.shutdown()

    done = [r for r in records if r["method"] != "icon"]
    summary = {
        "method": {"typed": "trial-v2", "cutout-all": "trial-v2b", "big": "trial-v3", "bitefix": "trial-v4"}[args.variant],
        "model": {"typed": "best-of-N + router + rectify / cut-out / crop",
                  "cutout-all": "best-of-N + box-limited cut-out for all + crop fallback",
                  "big": "best-of-N + full BiRefNet + isnet gap fill + soft edges + crop fallback",
                  "bitefix": "trial 3 + colour bite repair + partial-pack check"}[args.variant],
        "created": time.strftime("%Y-%m-%d %H:%M"),
        "pipeline_version": version,
        "n_selected": len(products),
        "n_processed": len(records),
        "n_flagged": sum(1 for r in records if r["flags"]),
        "n_s3_lag": len(s3_lag),
        "avg_secs": round(sum(r["secs"] for r in records) / max(len(records), 1), 2),
        "avg_after_kb": round(sum(r["after_kb"] for r in records) / max(len(records), 1), 1),
        "n_candidates": n_cands,
        "timings_total": {k: round(v, 1) for k, v in timings.items()},
        "methods": {m: sum(1 for r in records if r["method"] == m) for m in ("rectify", "cutout", "crop", "icon")},
        "front_changed": sum(1 for r in done if r.get("changed_front")),
        "flag_rules": REASONS,
        # review page shows the previous result (and its verdict) next to the new one
        "compare_run": {"typed": "crop", "cutout-all": "trial50", "big": "cutoutall", "bitefix": "bigmodel"}[args.variant],
    }
    if big:  # model speed, the number that sets the GPU / CPU budget
        ms = [r["timings"]["main_model_s"] for r in records if "main_model_s" in r.get("timings", {})]
        ss = [r["timings"]["second_model_s"] for r in records if "second_model_s" in r.get("timings", {})]
        summary["main_model"] = main_model
        summary["main_model_avg_s"] = round(sum(ms) / max(len(ms), 1), 2)
        summary["second_model_avg_s"] = round(sum(ss) / max(len(ss), 1), 2)
    if prev:  # same image as the previous trial -> carry the human verdict over (marked; the reviewer can change it)
        prev_dir, prev_name = prev
        label = "same_as_" + prev_name.replace(" ", "")
        prev_rv_path = prev_dir / "review.json"
        prev_rv = json.loads(prev_rv_path.read_text()) if prev_rv_path.exists() else {}
        carried = {}
        for r in records:
            a, b = res / "after" / f"{r['code']}.jpg", prev_dir / "after" / f"{r['code']}.jpg"
            if b.exists() and a.read_bytes() == b.read_bytes() and r["code"] in prev_rv:
                carried[r["code"]] = prev_rv[r["code"]]
                r["info"].append(label)
        summary["carried_over"] = len(carried)
        summary["flag_rules"] = dict(summary["flag_rules"], **{label: f"identical to the {prev_name} image: your {prev_name} verdict was copied"})
        if not (res / "review.json").exists():  # never overwrite verdicts already given for this run
            (res / "review.json").write_text(json.dumps(carried, indent=1, sort_keys=True))
    (res / "manifest.json").write_text(json.dumps({"summary": summary, "items": records}, ensure_ascii=False, indent=1))
    print(json.dumps({k: v for k, v in summary.items() if k != "flag_rules"}, indent=1))


if __name__ == "__main__":
    sys.exit(main())
