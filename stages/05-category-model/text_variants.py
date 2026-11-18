#!/usr/bin/env python3
"""Stage 05: which product text works best? Same models, same training data, only the product text changes.

Owner's request (2026-11-17): no new training; test
    title                       the product name as stored ("<name> by <Brand>")
    title+desc                  name + first sentence of the description (what bench.py uses)
    title+desc+ingr             as above + "Ingredients of this product: <list>" (list cut at a comma near 300 chars)

Models: qwen3-0.6b and arctic-l-v2, trained on the current training set (trainset.CURRENT: USDA foods + definition
phrases + OFF products, see trainset.py). Embeddings come from the per-text cache (embstore.py), so re-runs only embed
new texts. retrain.py --publish writes the same file for any training set.

    HF_HUB_OFFLINE=1 .venv/bin/python -I stages/05-category-model/text_variants.py
      -> out/text_variants.json (predictions) + a score table on screen
"""
import csv
import json
import re
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from bench import CATS, MODELS, NEVER, ON_TSV, OUT, ROOT, HF_CACHE, predict, prototype_text  # noqa: E402
from vote import VOTE, rank_vote  # noqa: E402

KEYS = ["qwen3-0.6b", "arctic-l-v2"]


def compose(name, desc, ingr):
    """The three product texts under test. desc: first sentence of the description; ingr: ingredients_text()."""
    name, desc = name.strip(), (desc or "").strip()
    base = f"{name}. {desc}".strip()
    return {"title": name, "title+desc": base,
            "title+desc+ingr": base + (f" Ingredients of this product: {ingr}." if ingr else "")}


def ingredients_text(raw, limit=300):
    t = re.sub(r"\s+", " ", raw or "").strip().rstrip(".")
    if len(t) > limit:
        cut = t.rfind(",", 0, limit)
        t = t[:cut if cut > 0 else limit].rstrip() + ", …"
    return t


def texts(sample, full_ingr):
    out = {"title": [], "title+desc": [], "title+desc+ingr": []}
    for p in sample:
        for v, t in compose(p["name"], p["description"], ingredients_text(full_ingr.get(p["id"]))).items():
            out[v].append(t)
    return out


def main():
    from sentence_transformers import SentenceTransformer

    import trainset
    from embstore import Store

    cats = json.loads(CATS.read_text())["categories"]
    classes = [c["code"] for c in cats if c["code"] not in NEVER]
    usable = [c for c in cats if c["code"] not in NEVER]
    sample = json.loads((OUT / "sample.json").read_text())
    ids = {p["id"] for p in sample}
    csv.field_size_limit(10 ** 9)
    with open(ON_TSV, newline="") as f:
        full_ingr = {r["id"]: r["ingredients"] for r in csv.DictReader(f, delimiter="\t") if r["id"] in ids}
    variants = texts(sample, full_ingr)
    ref_text, ref_code, _, _ = trainset.build(cats)
    print(f"{len(sample)} products · {len(ref_text):,} labelled foods (training set {trainset.CURRENT}) · with ingredients: "
          f"{sum(1 for p in sample if full_ingr.get(p['id']))}", flush=True)

    preds = {}
    for key in KEYS:
        hub, qp, dp = MODELS[key]
        t0 = time.time()
        local = ROOT / "work" / "models" / "st" / hub.replace("/", "__")
        model = SentenceTransformer(str(local) if (local / "config.json").exists() else hub, cache_folder=str(HF_CACHE), device="mps")
        enc = lambda xs, prompt: model.encode(xs, prompt=prompt, batch_size=64, normalize_embeddings=True,  # noqa: E731
                                              convert_to_numpy=True, show_progress_bar=False).astype(np.float32)
        store = Store(key)
        store.fill(lambda xs: enc(xs, qp), ref_text + [t for xs in variants.values() for t in xs])
        R = store.get(ref_text)
        C = enc([prototype_text(c) for c in usable], dp)
        lr = trainset.classifier(key, ref_text, ref_code, R)
        for vname, xs in variants.items():
            preds[f"{key}|{vname}"] = predict(store.get(xs), R, C, ref_code, classes, lr, sample)
        print(f"  {key}: done in {time.time() - t0:.0f}s", flush=True)
        del model
    (OUT / "text_variants.json").write_text(json.dumps({"training_set": trainset.CURRENT, "training_label": trainset.VARIANTS[trainset.CURRENT]["label"], "texts": {v: dict(zip([p["id"] for p in sample], xs))
                                                                   for v, xs in variants.items()},
                                                         "predictions": preds}, ensure_ascii=False, indent=1))
    score(sample, preds, variants)


def score(sample, preds, variants):
    truth = {k: v for k, v in json.loads((OUT / "review.json").read_text()).items() if v}
    types = {p["id"]: p["type"] for p in sample}
    groups = {"all": list(truth), "packaged": [p for p in truth if types[p] == "grocery"],
              "other": [p for p in truth if types[p] != "grocery"]}

    def acc(top, ids, k=1):
        return sum(truth[p] in top[p][:k] for p in ids) / max(len(ids), 1)

    print(f"\n{'model':12} {'method':6} {'text':16} {'top-1':>6} {'top-3':>6} {'packaged':>9} {'other':>6}")
    for vname in variants:
        rows = [(k, m) for k in KEYS for m in ("lr", "knn")]
        for k, m in rows:
            top = preds[f"{k}|{vname}"][m]
            print(f"{k:12} {m:6} {vname:16} {acc(top, groups['all']):6.1%} {acc(top, groups['all'], 3):6.1%} "
                  f"{acc(top, groups['packaged']):9.1%} {acc(top, groups['other']):6.1%}")
        vote = {p: [c for c, _ in rank_vote([preds[f"{k}|{vname}"][m][p] for k, m in VOTE])] for p in truth}
        print(f"{'3-model vote':19} {vname:16} {acc(vote, groups['all']):6.1%} {acc(vote, groups['all'], 3):6.1%} "
              f"{acc(vote, groups['packaged']):9.1%} {acc(vote, groups['other']):6.1%}\n")


if __name__ == "__main__":
    sys.exit(main())
