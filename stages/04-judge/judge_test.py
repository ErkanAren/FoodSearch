#!/usr/bin/env python3
"""Stage 04: can an automatic judge learn the reviewer's good / bad verdicts?

Uses ONLY images that already have a human verdict (E11, E14, trials 1-4). Nothing is downloaded, no API is called.
  1. Collect every rated image (icon placeholders excluded), de-duplicated by file hash.
  2. Features: OFF's CLIP image embedding (ONNX, already on disk) + a few simple image statistics.
  3. Logistic regression, evaluated with product-grouped cross-validation: a product's images are never
     in training and test at the same time.
  4. Honest threshold: inside each training fold, pick the threshold that reaches the target precision;
     apply it to the held-out fold; report what that gives on unseen products.
  5. Simulate the shipping pipeline on the 50 trial products: show the trial 3 image if the judge accepts it,
     otherwise a category icon. Also: pick the best-scoring image among trials 1-3 per product.

    .venv/bin/python -I stages/04-judge/judge_test.py
Writes stages/04-judge/out/ (features cache, results.json). Git-ignored.
"""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import onnxruntime as ort
from PIL import Image
from scipy import ndimage
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from tokenizers import Tokenizer

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
OUT = HERE / "out"
CLIP_MODEL = ROOT / "work" / "models" / "off-clip" / "model.onnx"
CLIP_TOKENIZER = ROOT / "work" / "models" / "off-clip" / "tokenizer.json"
RUNS = {  # name -> folder with after/, manifest.json, review.json
    "E11": ROOT / "work" / "photo_pilot",
    "E14": ROOT / "work" / "photo_pilot_crop",
    "T1": ROOT / "stages" / "00-trial-50" / "out",
    "T2": ROOT / "stages" / "01-cutout-all" / "out",
    "T3": ROOT / "stages" / "02-big-model" / "out",
    "T4": ROOT / "stages" / "03-bite-fix" / "out",
}
TARGETS = (0.95, 0.90)
SEEDS = range(5)
MEAN = np.array([0.48145466, 0.4578275, 0.40821073], dtype=np.float32)
STD = np.array([0.26862954, 0.26130258, 0.27577711], dtype=np.float32)


def collect():
    """Unique rated images: {hash: {path, code, verdict, runs, method}}."""
    imgs = {}
    for run, d in RUNS.items():
        rv = json.loads((d / "review.json").read_text())
        methods = {i["code"]: i.get("method", "cutout" if run == "E11" else "crop") for i in json.loads((d / "manifest.json").read_text())["items"]}
        for code, verdict in rv.items():
            if methods.get(code) == "icon":
                continue
            f = d / "after" / f"{code}.jpg"
            h = hashlib.sha1(f.read_bytes()).hexdigest()
            rec = imgs.setdefault(h, {"path": str(f), "code": code, "verdict": verdict, "runs": [], "method": methods.get(code)})
            rec["runs"].append(run)
            assert rec["verdict"] == verdict, f"conflicting verdicts for identical image {f}"
    return imgs


def clip_embed(paths):
    tok = Tokenizer.from_file(str(CLIP_TOKENIZER))
    enc = tok.encode("a product photo")
    ids = np.array([enc.ids], dtype=np.int64)
    mask = np.array([enc.attention_mask], dtype=np.int64)
    opts = ort.SessionOptions()
    opts.log_severity_level = 3
    sess = ort.InferenceSession(str(CLIP_MODEL), opts, providers=["CPUExecutionProvider"])
    out = []
    for p in paths:
        img = Image.open(p).convert("RGB").resize((224, 224), Image.BICUBIC)  # images are already 512x512 squares
        x = (np.asarray(img, dtype=np.float32) / 255.0 - MEAN) / STD
        emb = sess.run(["image_embeds"], {"input_ids": ids, "attention_mask": mask, "pixel_values": x.transpose(2, 0, 1)[None]})[0][0]
        out.append(emb)
    return np.array(out, dtype=np.float32)


def simple_stats(p):
    """Object size / shape statistics of the 512 px composite (white background)."""
    a = np.asarray(Image.open(p).convert("L").resize((128, 128)), dtype=np.float32)
    obj = a < 235
    lab, n = ndimage.label(obj)
    sizes = ndimage.sum(obj, lab, range(1, n + 1)) if n else np.array([0.0])
    ys, xs = np.where(obj) if obj.any() else (np.array([0]), np.array([0]))
    bbox = (ys.max() - ys.min() + 1) * (xs.max() - xs.min() + 1)
    edge = obj ^ ndimage.binary_erosion(obj)
    return [obj.mean(), obj.sum() / bbox, n, sizes.max() / max(obj.sum(), 1), edge.sum() / max(np.sqrt(obj.sum()), 1)]


def model():
    return make_pipeline(StandardScaler(), LogisticRegression(C=0.05, max_iter=5000))


def threshold_for(y, s, target):
    """Lowest threshold whose precision (share good among accepted) is >= target. None if never reached."""
    order = np.argsort(-s)
    ys, ss = y[order], s[order]
    tp = np.cumsum(ys)
    prec = tp / np.arange(1, len(ys) + 1)
    ok = np.where(prec >= target)[0]
    ok = ok[ok >= 4]  # need at least 5 accepted to call it a precision
    return None if len(ok) == 0 else float(ss[ok.max()])


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    imgs = collect()
    keys = sorted(imgs)
    rows = [imgs[k] for k in keys]
    y = np.array([r["verdict"] == "good" for r in rows], dtype=int)
    groups = np.array([r["code"] for r in rows])
    cache = OUT / "features.npz"
    if cache.exists() and list(np.load(cache, allow_pickle=True)["keys"]) == keys:
        X = np.load(cache)["X"]
    else:
        print(f"embedding {len(rows)} images…", flush=True)
        X = np.hstack([clip_embed([r["path"] for r in rows]), np.array([simple_stats(r["path"]) for r in rows])])
        np.savez(cache, X=X, keys=np.array(keys))
    print(f"{len(rows)} unique rated images, {y.mean():.0%} good, {len(set(groups))} products", flush=True)

    res = {"n_images": len(rows), "share_good": round(float(y.mean()), 3), "n_products": len(set(groups)), "seeds": {}}
    oof_all = np.zeros((len(SEEDS), len(rows)))
    realised = {t: {"tp": 0, "acc": 0, "good": 0, "n": 0} for t in TARGETS}
    for seed in SEEDS:
        outer = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=seed)
        oof = np.zeros(len(rows))
        for tr, te in outer.split(X, y, groups):
            m = model().fit(X[tr], y[tr])
            oof[te] = m.predict_proba(X[te])[:, 1]
            # threshold chosen INSIDE the training fold (inner CV), then applied to the unseen test fold
            inner = StratifiedGroupKFold(n_splits=4, shuffle=True, random_state=seed)
            inner_oof = np.zeros(len(tr))
            for itr, ite in inner.split(X[tr], y[tr], groups[tr]):
                inner_oof[ite] = model().fit(X[tr][itr], y[tr][itr]).predict_proba(X[tr][ite])[:, 1]
            for t in TARGETS:
                th = threshold_for(y[tr], inner_oof, t)
                acc = oof[te] >= th if th is not None else np.zeros(len(te), bool)
                realised[t]["tp"] += int((acc & (y[te] == 1)).sum())
                realised[t]["acc"] += int(acc.sum())
                realised[t]["good"] += int((y[te] == 1).sum())
                realised[t]["n"] += len(te)
        oof_all[seed] = oof
        res["seeds"][seed] = {"auc": round(float(roc_auc_score(y, oof)), 3)}
    oof = oof_all.mean(0)
    res["auc_mean"] = round(float(np.mean([v["auc"] for v in res["seeds"].values()])), 3)
    res["realised"] = {str(t): {
        "precision": round(r["tp"] / max(r["acc"], 1), 3),
        "good_accepted": round(r["tp"] / max(r["good"], 1), 3),
        "images_accepted": round(r["acc"] / max(r["n"], 1), 3)} for t, r in realised.items()}

    # --- simulate the shipping pipeline on the 50 trial products (scores are out-of-fold: product never trained on)
    score = {k: s for k, s in zip(keys, oof)}
    by_run_code = {}
    for k, r in zip(keys, rows):
        for run in r["runs"]:
            by_run_code[(run, r["code"])] = (score[k], r["verdict"])
    t3 = json.loads((RUNS["T3"] / "manifest.json").read_text())["items"]
    sim = {}
    for t in TARGETS:
        th = threshold_for(y, oof, t)  # for the simulation only (whole-set threshold, slightly optimistic)
        shown = good = 0
        shown_b = good_b = 0
        for it in t3:
            c = it["code"]
            if (("T3", c)) in by_run_code:
                s, v = by_run_code[("T3", c)]
                if th is not None and s >= th:
                    shown += 1
                    good += v == "good"
            cands = [by_run_code[(run, c)] for run in ("T1", "T2", "T3") if (run, c) in by_run_code]
            if cands:
                s, v = max(cands, key=lambda sv: sv[0])
                if th is not None and s >= th:
                    shown_b += 1
                    good_b += v == "good"
        sim[str(t)] = {"threshold": th,
                       "t3_only": {"shown": shown, "good_shown": good, "icons": 50 - shown},
                       "best_of_t1_t3": {"shown": shown_b, "good_shown": good_b, "icons": 50 - shown_b}}
    res["simulation_50"] = sim
    (OUT / "results.json").write_text(json.dumps(res, indent=1))
    print(json.dumps({k: v for k, v in res.items() if k != "seeds"}, indent=1))


if __name__ == "__main__":
    sys.exit(main())
