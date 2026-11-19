#!/usr/bin/env python3
"""Stage 05: a bigger test set (owner, 2026-11-19). The 200 answer-key products can't show gains under ≈ 5 points.

Test products: OpenNutrition products whose Open Food Facts (OFF) entry (same barcode) has a *strong* category tag
(out/tag_labels.json from tag_shortcut.py; strong tags were right on 18 of 20 answer-key products). Their answer is
that tag's category, with the nutrient rules applied to the OpenNutrition nutrients (as for the models' answers).
    * not used: the 200 answer-key products, and any barcode that is a training example of any set (all ranks);
    * at most PER_CATEGORY products per category (fixed pseudo-random order), so common tags don't dominate.
Caveat: the answers come from the same tag mapping as the OFF training labels, so this measures agreement with the
mapping, and it favours training sets with more OFF examples. Good for comparing changes, not a true accuracy.

    HF_HUB_OFFLINE=1 .venv/bin/python -I stages/05-category-model/big_test.py            # all training sets (A-D)
    HF_HUB_OFFLINE=1 .venv/bin/python -I stages/05-category-model/big_test.py --sets D
Outputs (git-ignored): out/big_test.json (the products), out/big_test_results.json (top 3 per model, set and text)
"""
import argparse
import collections
import csv
import hashlib
import json
import math
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from bench import CATS, NEVER, ON_TSV, OUT, apply_rules, first_sentence  # noqa: E402
from retrain import METHODS, embed_all, top3  # noqa: E402
from text_variants import KEYS, compose, ingredients_text  # noqa: E402
import trainset  # noqa: E402
from vote import LEVELS, VOTE_ORIGINAL as VOTE, agreement, rank_vote  # noqa: E402  (the original models, vote.py)

PER_CATEGORY = 40
TEST = OUT / "big_test.json"
RESULTS = OUT / "big_test_results.json"
TEXTS = ("title+desc", "title+desc+ingr")
NUTR_KEYS = ("total_fat", "total_sugars", "carbohydrates", "calories")


def code_norm(code):
    code = (code or "").strip()
    return (code.lstrip("0") or code) if code.isdigit() else code


def build():
    labels = json.loads((OUT / "tag_labels.json").read_text())["on"]
    strong = {pid: code for pid, (code, why) in labels.items() if why == "strong" and code}
    sample_ids = {p["id"] for p in json.loads((OUT / "sample.json").read_text())}
    files = {v.get("off_train", "off_train.json") for v in trainset.VARIANTS.values()}  # every set's training products
    train_bc = {code_norm(e["barcode"]) for f in files for e in json.loads((OUT / f).read_text())["examples"]}
    csv.field_size_limit(10 ** 9)
    rows, skipped = [], collections.Counter()
    with open(ON_TSV, newline="") as f:
        for r in csv.DictReader(f, delimiter="\t"):  # read as in bench.load_sample
            pid = r["id"]
            if pid not in strong:
                continue
            if pid in sample_ids:
                skipped["answer-key product"] += 1
                continue
            if code_norm(r["ean_13"]) in train_bc:
                skipped["barcode is a training example"] += 1
                continue
            n = json.loads(r["nutrition_100g"] or "{}")
            nutr = {k: n.get(k) for k in NUTR_KEYS}
            code = apply_rules(strong[pid], nutr)
            if code in NEVER:
                skipped["survey-only category"] += 1
                continue
            rows.append((hashlib.sha1(pid.encode()).hexdigest(), {
                "id": pid, "type": r["type"], "name": r["name"], "ean": r["ean_13"] or None,
                "description": first_sentence(r["description"]), "ingr": ingredients_text(r["ingredients"]),
                "nutr": nutr, "code": code}))
    by = collections.defaultdict(list)
    for _, p in sorted(rows, key=lambda x: x[0]):
        if len(by[p["code"]]) < PER_CATEGORY:
            by[p["code"]].append(p)
    products = [p for code in sorted(by) for p in by[code]]
    TEST.write_text(json.dumps({"rule": "strong OFF tag, not in training, not an answer-key product, "
                                        f"at most {PER_CATEGORY} per category", "eligible": len(rows),
                                "skipped": skipped, "products": products}, ensure_ascii=False, indent=1))
    print(f"{len(strong):,} with a strong tag · eligible {len(rows):,} · skipped " +
          ", ".join(f"{k} {v:,}" for k, v in skipped.items()) +
          f" -> {len(products):,} test products in {len(by)} categories -> {TEST}", flush=True)
    return products


def knn_fast(sim, ref_code, cidx, n_classes, k=10):
    """= bench.knn_scores (10 nearest, shifted exp, temperature 0.05) with argpartition: fast on 178k labelled foods."""
    part = np.argpartition(-sim, k, axis=1)[:, :k]
    order = np.take_along_axis(sim, part, 1).argsort(axis=1)[:, ::-1]
    idx = np.take_along_axis(part, order, 1)
    out = np.zeros((sim.shape[0], n_classes))
    for r in range(sim.shape[0]):
        best = sim[r, idx[r, 0]]
        for j in idx[r]:
            out[r, cidx[ref_code[j]]] += np.exp((sim[r, j] - best) / 0.05)
    return out / out.sum(1, keepdims=True)


def predict(stores, cats, classes, variant, xs_by_text, nutrs, chunk=500):
    texts, codes, _, _ = trainset.build(cats, variant)
    cidx = {c: i for i, c in enumerate(classes)}
    out = {tv: {} for tv in xs_by_text}
    for key in KEYS:
        t0 = time.time()
        R = stores[key].get(texts)
        lr = trainset.classifier(key, texts, codes, R)
        cols = [cidx[c] for c in lr.classes_]
        for tv, xs in xs_by_text.items():
            P = stores[key].get(xs)
            res = {m: [] for m in METHODS}
            for s in range(0, len(xs), chunk):
                Pc = P[s:s + chunk]
                lr_full = np.zeros((len(Pc), len(classes)))
                lr_full[:, cols] = lr.predict_proba(Pc)
                scores = {"lr": lr_full, "knn": knn_fast(Pc @ R.T, codes, cidx, len(classes))}
                for m in METHODS:
                    res[m] += [top3(scores[m][i], classes, nutrs[s + i]) for i in range(len(Pc))]
            for m in METHODS:
                out[tv][f"{key}|{m}"] = res[m]
        print(f"  set {variant} {key}: {len(texts):,} labelled foods, predicted ({time.time() - t0:.0f}s)", flush=True)
    for tv in out:
        out[tv]["vote"] = [[c for c, _ in rank_vote([out[tv][f"{k}|{m}"][i] for k, m in VOTE])][:3]
                           for i in range(len(nutrs))]
    return out


def sign_p(a, b):
    """Two-sided exact sign test: a products fixed, b broken."""
    n = a + b
    if n == 0:
        return 1.0
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(min(a, b) + 1)) / 2 ** n)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sets", default="".join(trainset.VARIANTS), help="training sets to test, e.g. AD (default: all)")
    ap.add_argument("--rebuild", action="store_true", help="pick the test products again")
    args = ap.parse_args()
    sets = [v for v in args.sets if v in trainset.VARIANTS]
    t0 = time.time()
    cats = json.loads(CATS.read_text())["categories"]
    names = {c["code"]: c["name"] for c in cats}
    classes = [c["code"] for c in cats if c["code"] not in NEVER]
    products = build() if args.rebuild or not TEST.exists() else json.loads(TEST.read_text())["products"]
    xs = {tv: [] for tv in TEXTS}
    for p in products:
        t = compose(p["name"], p["description"], p["ingr"])
        for tv in TEXTS:
            xs[tv].append(t[tv])
    nutrs = [p["nutr"] for p in products]
    truth = [p["code"] for p in products]
    all_texts = [t for tv in TEXTS for t in xs[tv]]
    for v in sets:
        all_texts += trainset.build(cats, v)[0]
    stores = embed_all(all_texts)

    res = {v: predict(stores, cats, classes, v, xs, nutrs) for v in sets}
    RESULTS.write_text(json.dumps({"products": [p["id"] for p in products], "results": res}))

    def right(tops, k=1):
        return [truth[i] in tops[i][:k] for i in range(len(truth))]

    def acc(tops, k=1):
        return sum(right(tops, k)) / len(truth)

    types = collections.Counter(p["type"] for p in products)
    print(f"\n{len(products):,} test products ({', '.join(f'{t} {n:,}' for t, n in types.most_common())}), "
          f"{len(set(truth))} categories. Top-1 (top-3); answers from strong OFF tags.")
    members = ["qwen3-0.6b|lr", "qwen3-0.6b|knn", "arctic-l-v2|lr", "arctic-l-v2|knn"]
    print(f"{'set':38} {'vote, title+desc':>17} {'vote, +ingr':>17} | +ingr: " + " ".join(f"{m:>15}" for m in members))
    for v in sets:
        r = res[v]
        print(f"{v} {trainset.VARIANTS[v]['label']:36} "
              + " ".join(f"{acc(r[tv]['vote']):>8.1%} ({acc(r[tv]['vote'], 3):5.1%})" for tv in TEXTS)
              + " | " + " ".join(f"{acc(r['title+desc+ingr'][m]):>15.1%}" for m in members))

    for base, v in zip(sets, sets[1:]):  # each set against the one before: what its change contributed
        for tv in TEXTS:
            a, b = right(res[base][tv]["vote"]), right(res[v][tv]["vote"])
            fixed, broken = sum(y and not x for x, y in zip(a, b)), sum(x and not y for x, y in zip(a, b))
            print(f"  {v} vs {base}, {tv:16}: {fixed} fixed, {broken} broken, net {fixed - broken:+} "
                  f"({(fixed - broken) / len(truth):+.1%}), sign test p = {sign_p(fixed, broken):.3f}")

    last = sets[-1]
    for tv in TEXTS:
        st = collections.defaultdict(lambda: [0, 0])
        r = res[last][tv]
        for i in range(len(truth)):
            lv = agreement([r[f"{k}|{m}"][i] for k, m in VOTE])
            st[lv][0] += 1
            st[lv][1] += r["vote"][i][0] == truth[i]
        print(f"set {last}, {tv}: " + " · ".join(f"{LEVELS[lv]}: {n:,} ({n / len(truth):.0%}), {ok / n:.0%} right"
                                                for lv, (n, ok) in sorted(st.items(), key=lambda x: -x[1][0])))

    r = res[last]["title+desc+ingr"]["vote"]
    per = collections.defaultdict(lambda: [0, 0, collections.Counter()])
    for i, c in enumerate(truth):
        per[c][0] += 1
        per[c][1] += r[i][0] == c
        if r[i][0] != c:
            per[c][2][r[i][0]] += 1
    rows = sorted(per.items(), key=lambda x: x[1][1] / x[1][0])
    print(f"\nset {last}, +ingr, weakest categories (at least 10 test products):")
    for c, (n, ok, wrong) in [x for x in rows if x[1][0] >= 10][:20]:
        top = ", ".join(f"{names[w][:28]} {k}" for w, k in wrong.most_common(2))
        print(f"  {c} {names[c][:34]:34} {ok:>3}/{n:<3} {ok / n:>4.0%} · instead: {top}")
    good = [x for x in rows if x[1][0] >= 10 and x[1][1] / x[1][0] >= 0.9]
    print(f"categories with >= 10 test products: {sum(1 for x in rows if x[1][0] >= 10)}, "
          f"of which >= 90 % right: {len(good)}")
    print(f"done in {(time.time() - t0) / 60:.1f} min -> {RESULTS}")


if __name__ == "__main__":
    sys.exit(main())
