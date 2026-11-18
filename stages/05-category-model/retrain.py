#!/usr/bin/env python3
"""Stage 05 retrain (owner, 2026-11-18): which of the planned changes help? No generative AI.

Training sets (trainset.VARIANTS; each adds one change):
    A  200 per category, names                (as before, plus the strained-yogurt fix and egg/breakfast sandwiches)
    B  1,000 per category, names
    C  1,000, names + ingredients             products with ingredients also appear as "<name>. Ingredients of this product: …"
    D  1,000, names + ingredients, cleaned    OFF examples dropped when, for both models, at most 1 of their 10 nearest
                                              labelled foods shares their category and at least 6 agree on one other category
Models: Qwen3-Embedding-0.6B (classifier + kNN) and Arctic-embed-l-v2 (kNN, classifier), the 3-model vote as before.
Tests: the 200 products (answer key; three product texts, as in text_variants.py) and the 98 Greek-only products
(out/greek_test.json, answers from OFF tags).

    HF_HUB_OFFLINE=1 .venv/bin/python -I stages/05-category-model/retrain.py            # ≈ 1 h the first time
    HF_HUB_OFFLINE=1 .venv/bin/python -I stages/05-category-model/retrain.py --publish D
        -> also writes out/text_variants.json from set D (what the results page shows)
Outputs (git-ignored): out/retrain.json, out/clean_drop.json, out/store_*.{npy,json} (embedding cache), out/lr_*.npz
"""
import argparse
import collections
import csv
import gc
import json
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from bench import CATS, HF_CACHE, MODELS, NEVER, ON_TSV, OUT, ROOT, apply_rules, knn_scores  # noqa: E402
from embstore import Store  # noqa: E402
from text_variants import KEYS, texts as product_texts  # noqa: E402
import trainset  # noqa: E402
from vote import VOTE, rank_vote  # noqa: E402

METHODS = ("lr", "knn")


def embed_all(all_texts):
    from sentence_transformers import SentenceTransformer
    import torch

    stores = {}
    for key in KEYS:
        store = Store(key)
        if store.missing(all_texts):
            hub, qp, _ = MODELS[key]
            local = ROOT / "work" / "models" / "st" / hub.replace("/", "__")
            model = SentenceTransformer(str(local) if (local / "config.json").exists() else hub,
                                        cache_folder=str(HF_CACHE), device="mps")
            enc = lambda xs: model.encode(xs, prompt=qp, batch_size=64, normalize_embeddings=True,  # noqa: E731
                                          convert_to_numpy=True, show_progress_bar=False)
            store.fill(enc, all_texts)
            del model
            gc.collect()
            torch.mps.empty_cache()
        stores[key] = store
    return stores


def clean(stores, cats):
    """Find OFF examples whose nearest labelled foods (both models) clearly belong to another category."""
    texts, codes, srcs, keys = trainset.build(cats, "B")
    off = [i for i, s in enumerate(srcs) if s == "off"]
    found = collections.defaultdict(list)  # example index -> per model (own votes, top other code, its votes)
    for key in KEYS:
        R = stores[key].get(texts)
        for start in range(0, len(off), 512):
            rows = np.array(off[start:start + 512])
            sim = R[rows] @ R.T
            sim[np.arange(len(rows)), rows] = -2.0  # not itself
            nn = np.argpartition(-sim, 10, axis=1)[:, :10]
            for r, i in enumerate(rows):
                c = collections.Counter(codes[nn[r]])
                own = c.pop(codes[i], 0)
                top, n = c.most_common(1)[0] if c else ("", 0)
                found[i].append((own, top, n))
    drop = {}
    for i, per_model in found.items():
        tops = {t for _, t, _ in per_model}
        if len(per_model) == len(KEYS) and len(tops) == 1 and all(own <= 1 and n >= 6 for own, _, n in per_model):
            drop[keys[i]] = {"text": texts[i], "code": str(codes[i]), "neighbours_say": tops.pop()}
    trainset.CLEAN_DROP.write_text(json.dumps({"rule": "both models: <= 1 of 10 nearest share the label, >= 6 agree "
                                                       "on one other category", "drop": drop}, ensure_ascii=False, indent=1))
    print(f"cleaning: {len(drop):,} of {len(off):,} OFF examples dropped -> {trainset.CLEAN_DROP}", flush=True)
    return drop


def top3(row, classes, nutr):
    out = []
    for j in np.argsort(-row)[:3]:  # as bench.predict: best 3, then the nutrient rules, duplicates dropped
        code = apply_rules(classes[j], nutr)
        if code not in out:
            out.append(code)
    return out


def predict(stores, cats, classes, variant, tests):
    """tests: {name: (texts, nutrients)} -> {name: {"<model>|<method>": [top 3 per text]}}."""
    texts, codes, _, _ = trainset.build(cats, variant)
    out = {name: {} for name in tests}
    for key in KEYS:
        R = stores[key].get(texts)
        t0 = time.time()
        lr = trainset.classifier(key, texts, codes, R)
        print(f"  {variant} {key}: {len(texts):,} labelled foods, classifier ready ({time.time() - t0:.0f}s)", flush=True)
        for name, (xs, nutrs) in tests.items():
            P = stores[key].get(xs)
            proba = lr.predict_proba(P)
            lr_full = np.zeros((len(xs), len(classes)))
            for j, c in enumerate(lr.classes_):
                lr_full[:, classes.index(c)] = proba[:, j]
            scores = {"lr": lr_full, "knn": knn_scores(P @ R.T, codes, classes)}
            for m in METHODS:
                out[name][f"{key}|{m}"] = [top3(scores[m][i], classes, nutrs[i]) for i in range(len(xs))]
    for name in tests:
        n = len(tests[name][0])
        out[name]["vote"] = [[c for c, _ in rank_vote([out[name][f"{k}|{m}"][i] for k, m in VOTE])][:3] for i in range(n)]
    return out, len(texts)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--publish", choices=list(trainset.VARIANTS), help="write out/text_variants.json from this set")
    ap.add_argument("--reclean", action="store_true", help="recompute out/clean_drop.json")
    args = ap.parse_args()
    t0 = time.time()
    cats = json.loads(CATS.read_text())["categories"]
    classes = [c["code"] for c in cats if c["code"] not in NEVER]
    sample = json.loads((OUT / "sample.json").read_text())
    truth = {k: v for k, v in json.loads((OUT / "review.json").read_text()).items() if v}
    ids = {p["id"] for p in sample}
    csv.field_size_limit(10 ** 9)
    with open(ON_TSV, newline="") as f:
        full_ingr = {r["id"]: r["ingredients"] for r in csv.DictReader(f, delimiter="\t") if r["id"] in ids}
    pvars = product_texts(sample, full_ingr)
    greek = json.loads((OUT / "greek_test.json").read_text())["products"]
    tests = {f"200|{v}": (xs, [p["nutr"] for p in sample]) for v, xs in pvars.items()}
    tests["greek"] = ([p["text"] for p in greek], [p["nutr"] or {} for p in greek])

    all_texts = [t for xs, _ in tests.values() for t in xs]
    for v in ("A", "B", "C"):  # D is a subset of C
        all_texts += trainset.build(cats, v)[0]
    print(f"{len(set(all_texts)):,} distinct texts ({time.time() - t0:.0f}s)", flush=True)
    stores = embed_all(all_texts)
    if args.reclean or not trainset.CLEAN_DROP.exists():
        clean(stores, cats)

    res, sizes = {}, {}
    for v in trainset.VARIANTS:
        res[v], sizes[v] = predict(stores, cats, classes, v, tests)
    (OUT / "retrain.json").write_text(json.dumps({"variants": trainset.VARIANTS, "sizes": sizes, "results": res}))

    pids = [p["id"] for p in sample]
    kind = {p["id"]: p["type"] == "grocery" for p in sample}
    gtruth = [p["code"] for p in greek]

    def acc200(tops, k=1, packaged=None):
        idx = [i for i, pid in enumerate(pids) if pid in truth and (packaged is None or kind[pid] == packaged)]
        return sum(truth[pids[i]] in tops[i][:k] for i in idx) / len(idx)

    def accg(tops, k=1):
        return sum(gtruth[i] in tops[i][:k] for i in range(len(gtruth))) / len(gtruth)

    print(f"\nTop-1 (top-3). 200 test products: answer key. Greek: {len(greek)} Greek-only products, answers from OFF tags.")
    print(f"{'set':38} {'labelled':>9} | {'vote, title+desc':>17} {'vote, +ingr':>15} {'Qwen3 clf':>10} {'Arctic kNN':>10}"
          f" | {'packaged':>8} {'other':>6} | {'Greek vote':>15}")
    for v, cfg in trainset.VARIANTS.items():
        r = res[v]
        td, ti = r["200|title+desc"], r["200|title+desc+ingr"]
        print(f"{v} {cfg['label']:36} {sizes[v]:>9,} | {acc200(td['vote']):>8.1%} ({acc200(td['vote'], 3):5.1%})"
              f" {acc200(ti['vote']):>6.1%} ({acc200(ti['vote'], 3):5.1%}) {acc200(td['qwen3-0.6b|lr']):>10.1%}"
              f" {acc200(td['arctic-l-v2|knn']):>10.1%} | {acc200(td['vote'], 1, True):>8.1%} {acc200(td['vote'], 1, False):>6.1%}"
              f" | {accg(r['greek']['vote']):>6.1%} ({accg(r['greek']['vote'], 3):5.1%})")

    if args.publish:
        r = res[args.publish]
        preds = {f"{k}|{tv}": {m: dict(zip(pids, r[f"200|{tv}"][f"{k}|{m}"])) for m in METHODS}
                 for k in KEYS for tv in pvars}
        (OUT / "text_variants.json").write_text(json.dumps(
            {"training_set": args.publish, "training_label": trainset.VARIANTS[args.publish]["label"], "texts": {tv: dict(zip(pids, xs)) for tv, xs in pvars.items()},
             "predictions": preds}, ensure_ascii=False, indent=1))
        print(f"published set {args.publish} -> {OUT / 'text_variants.json'}")
    print(f"done in {(time.time() - t0) / 60:.0f} min")


if __name__ == "__main__":
    sys.exit(main())
