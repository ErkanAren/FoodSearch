#!/usr/bin/env python3
"""Stage 05 (owner, 2026-11-19): one classifier that sees both models at once. No generative AI.

The logistic regression (C=20, as before) gets Qwen3 and Arctic embeddings side by side (2 x 1024 numbers per text)
instead of one model's. Trained on the current training set (trainset.CURRENT). Compared with the current vote on the
200 answer-key products, the 98 Greek-only products and the big test (big_test.py); the other vote members' answers
come from out/retrain.json and out/big_test_results.json (same training set), so run those first.

    HF_HUB_OFFLINE=1 .venv/bin/python -I stages/05-category-model/combined.py      # ≈ 10 min the first time
Outputs (git-ignored): out/lr_qwen3+arctic_<hash>.npz (the classifier), out/combined.json (top 3 per test product)
"""
import csv
import json
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from bench import CATS, NEVER, ON_TSV, OUT  # noqa: E402
from embstore import Store  # noqa: E402
from retrain import top3  # noqa: E402
from text_variants import KEYS, compose, texts as product_texts  # noqa: E402
import trainset  # noqa: E402
from vote import VOTE_ORIGINAL as VOTE, rank_vote  # noqa: E402  (the original models, vote.py)

NAME = "qwen3+arctic"


def joined(stores, xs):
    """Both models' (normalised) embeddings side by side, scaled so the joined vector has length 1."""
    return np.concatenate([stores[k].get(xs) for k in KEYS], axis=1) / np.sqrt(len(KEYS))


def main():
    t0 = time.time()
    v = trainset.CURRENT
    cats = json.loads(CATS.read_text())["categories"]
    classes = [c["code"] for c in cats if c["code"] not in NEVER]
    sample = json.loads((OUT / "sample.json").read_text())
    truth = json.loads((OUT / "review.json").read_text())
    ids = {p["id"] for p in sample}
    csv.field_size_limit(10 ** 9)
    with open(ON_TSV, newline="") as f:
        full_ingr = {r["id"]: r["ingredients"] for r in csv.DictReader(f, delimiter="\t") if r["id"] in ids}
    pvars = product_texts(sample, full_ingr)
    greek = json.loads((OUT / "greek_test.json").read_text())["products"]
    big = json.loads((OUT / "big_test.json").read_text())["products"]
    saved = json.loads((OUT / "retrain.json").read_text())["results"][v]
    saved_big = json.loads((OUT / "big_test_results.json").read_text())["results"][v]
    tests = {  # name: (texts, nutrients, answers, saved member predictions)
        "200, title+desc": (pvars["title+desc"], [p["nutr"] for p in sample], [truth[p["id"]] for p in sample],
                            saved["200|title+desc"]),
        "200, +ingr": (pvars["title+desc+ingr"], [p["nutr"] for p in sample], [truth[p["id"]] for p in sample],
                       saved["200|title+desc+ingr"]),
        "Greek-only": ([p["text"] for p in greek], [p["nutr"] or {} for p in greek], [p["code"] for p in greek],
                       saved["greek"]),
        "big, title+desc": ([compose(p["name"], p["description"], p["ingr"])["title+desc"] for p in big],
                            [p["nutr"] for p in big], [p["code"] for p in big], saved_big["title+desc"]),
        "big, +ingr": ([compose(p["name"], p["description"], p["ingr"])["title+desc+ingr"] for p in big],
                       [p["nutr"] for p in big], [p["code"] for p in big], saved_big["title+desc+ingr"]),
    }
    stores = {k: Store(k) for k in KEYS}
    texts, codes, _, _ = trainset.build(cats, v)
    R = joined(stores, texts)
    lr = trainset.classifier(NAME, texts, codes, R)
    print(f"set {v}: {len(texts):,} labelled foods, joined classifier ready ({time.time() - t0:.0f}s)", flush=True)
    cols = [classes.index(c) for c in lr.classes_]

    lines = {"current vote": [], f"joined classifier alone": [], "vote, joined classifier in place of Qwen3's": [],
             "Qwen3 classifier alone (for reference)": []}
    out = {}
    for name, (xs, nutrs, answers, mem) in tests.items():
        P = joined(stores, xs)
        full = np.zeros((len(xs), len(classes)))
        full[:, cols] = lr.predict_proba(P)
        jl = [top3(full[i], classes, nutrs[i]) for i in range(len(xs))]
        out[name] = jl
        new_vote = [[c for c, _ in rank_vote([jl[i]] + [mem[f"{k}|{m}"][i] for k, m in VOTE[1:]])][:3]
                    for i in range(len(xs))]
        for label, tops in (("current vote", mem["vote"]), ("joined classifier alone", jl),
                            ("vote, joined classifier in place of Qwen3's", new_vote),
                            ("Qwen3 classifier alone (for reference)", mem["qwen3-0.6b|lr"])):
            r1 = sum(a == t[0] for a, t in zip(answers, tops)) / len(answers)
            r3 = sum(a in t[:3] for a, t in zip(answers, tops)) / len(answers)
            lines[label].append(f"{r1:>7.1%} ({r3:5.1%})")
    (OUT / "combined.json").write_text(json.dumps({"set": v, "predictions": out}))
    print(f"\nTop-1 (top-3), training set {v}")
    print(f"{'':45}" + "".join(f"{n:>17}" for n in tests))
    for label, cells in lines.items():
        print(f"{label:45}" + "".join(f"{c:>17}" for c in cells))
    print(f"done in {(time.time() - t0) / 60:.1f} min")


if __name__ == "__main__":
    sys.exit(main())
