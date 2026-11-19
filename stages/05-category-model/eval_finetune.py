#!/usr/bin/env python3
"""Stage 05 (owner, 2026-11-19): is the fine-tuned Qwen3 (finetune.py) better? No generative AI.

The fine-tuned model is used exactly like the original: its embeddings of the current training set feed a logistic
regression (C=20) and the 10-nearest-neighbour vote (key "qwen3-ft", cached in out/store_qwen3-ft.*). Compared on the
200 answer-key products, the 98 Greek-only products and the big test, against the current vote (out/retrain.json,
out/big_test_results.json, same training set).

    HF_HUB_OFFLINE=1 .venv/bin/python -I stages/05-category-model/eval_finetune.py     # ≈ 50 min the first time (embedding)
    ... eval_finetune.py --publish   also adds the fine-tuned model's answers on the 200 to out/text_variants.json
                                     (what the results page shows; its vote is vote.VOTE)
Output (git-ignored): out/eval_finetune.json
"""
import argparse
import csv
import gc
import json
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from bench import CATS, MODELS, NEVER, ON_TSV, OUT  # noqa: E402
from big_test import knn_fast  # noqa: E402
from embstore import Store  # noqa: E402
from finetune import FT_DIR, KEY  # noqa: E402
from retrain import top3  # noqa: E402
from text_variants import compose, texts as product_texts  # noqa: E402
import trainset  # noqa: E402
from vote import VOTE, rank_vote  # noqa: E402

FT = "qwen3-ft"


def predict(key, texts, codes, classes, tests, chunk=500):
    store = Store(key)
    R = store.get(texts)
    lr = trainset.classifier(key, texts, codes, R)
    cols = [classes.index(c) for c in lr.classes_]
    cidx = {c: i for i, c in enumerate(classes)}
    out = {}
    for name, (xs, nutrs, _, _) in tests.items():
        P = store.get(xs)
        res = {"lr": [], "knn": []}
        for s in range(0, len(xs), chunk):
            Pc = P[s:s + chunk]
            full = np.zeros((len(Pc), len(classes)))
            full[:, cols] = lr.predict_proba(Pc)
            kn = knn_fast(Pc @ R.T, codes, cidx, len(classes))
            res["lr"] += [top3(full[i], classes, nutrs[s + i]) for i in range(len(Pc))]
            res["knn"] += [top3(kn[i], classes, nutrs[s + i]) for i in range(len(Pc))]
        out[name] = res
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--publish", action="store_true", help="add the answers on the 200 to out/text_variants.json")
    args = ap.parse_args()
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
    s200 = ([p["nutr"] for p in sample], [truth[p["id"]] for p in sample])
    tests = {  # name: (texts, nutrients, answers, saved predictions of the current members)
        "200, title": (pvars["title"], *s200, saved["200|title"]),
        "200, title+desc": (pvars["title+desc"], *s200, saved["200|title+desc"]),
        "200, +ingr": (pvars["title+desc+ingr"], *s200, saved["200|title+desc+ingr"]),
        "Greek-only": ([p["text"] for p in greek], [p["nutr"] or {} for p in greek], [p["code"] for p in greek],
                       saved["greek"]),
        "big, title+desc": ([compose(p["name"], p["description"], p["ingr"])["title+desc"] for p in big],
                            [p["nutr"] for p in big], [p["code"] for p in big], saved_big["title+desc"]),
        "big, +ingr": ([compose(p["name"], p["description"], p["ingr"])["title+desc+ingr"] for p in big],
                       [p["nutr"] for p in big], [p["code"] for p in big], saved_big["title+desc+ingr"]),
    }
    texts, codes, _, _ = trainset.build(cats, v)
    store = Store(FT)
    todo = store.missing(texts + [t for xs, *_ in tests.values() for t in xs])
    if todo:
        from sentence_transformers import SentenceTransformer
        import torch
        model = SentenceTransformer(str(FT_DIR), device="mps")
        qp = MODELS[KEY][1]
        print(f"embedding {len(todo):,} texts with the fine-tuned model", flush=True)
        store.fill(lambda xs: model.encode(xs, prompt=qp, batch_size=64, normalize_embeddings=True,
                                           convert_to_numpy=True, show_progress_bar=False), todo)
        del model
        gc.collect()
        torch.mps.empty_cache()
    ft = predict(FT, texts, codes, classes, tests)
    print(f"fine-tuned model: classifier and kNN ready ({time.time() - t0:.0f}s)", flush=True)

    rows = {}
    for name, (xs, nutrs, answers, mem) in tests.items():
        f = ft[name]
        cand = {
            "current vote (Qwen3 clf, Qwen3 kNN, Arctic kNN)": mem["vote"],
            "fine-tuned Qwen3 classifier alone": f["lr"],
            "fine-tuned Qwen3 kNN alone": f["knn"],
            "vote: fine-tuned clf, fine-tuned kNN, Arctic kNN":
                [[c for c, _ in rank_vote([f["lr"][i], f["knn"][i], mem["arctic-l-v2|knn"][i]])][:3] for i in range(len(xs))],
            "original Qwen3 classifier alone (reference)": mem["qwen3-0.6b|lr"],
        }
        for label, tops in cand.items():
            r1 = sum(a == t[0] for a, t in zip(answers, tops)) / len(answers)
            r3 = sum(a in t[:3] for a, t in zip(answers, tops)) / len(answers)
            rows.setdefault(label, []).append(f"{r1:>7.1%} ({r3:5.1%})")
        cur = [a == t[0] for a, t in zip(answers, mem["vote"])]
        new = [a == t[0] for a, t in zip(answers, cand["vote: fine-tuned clf, fine-tuned kNN, Arctic kNN"])]
        fixed = sum(n and not c for c, n in zip(cur, new))
        broken = sum(c and not n for c, n in zip(cur, new))
        rows.setdefault("  new vote vs current: fixed / broken", []).append(f"{f'+{fixed} / -{broken}':>17}")
    (OUT / "eval_finetune.json").write_text(json.dumps({"set": v, "predictions": ft}))
    if args.publish:
        tvp = OUT / "text_variants.json"
        d = json.loads(tvp.read_text())
        assert d.get("training_set") == v, f"text_variants.json is from set {d.get('training_set')}, not {v}"
        pids = [p["id"] for p in sample]
        for tv, name in (("title", "200, title"), ("title+desc", "200, title+desc"), ("title+desc+ingr", "200, +ingr")):
            d["predictions"][f"{FT}|{tv}"] = {m: dict(zip(pids, ft[name][m])) for m in ("lr", "knn")}
        d["vote"] = [f"{k}|{m}" for k, m in VOTE]
        tvp.write_text(json.dumps(d, ensure_ascii=False, indent=1))
        print(f"published the fine-tuned model's answers -> {tvp}")
    print(f"\nTop-1 (top-3), training set {v}")
    print(f"{'':52}" + "".join(f"{n:>17}" for n in tests))
    for label, cells in rows.items():
        print(f"{label:52}" + "".join(f"{c:>17}" for c in cells))
    print(f"done in {(time.time() - t0) / 60:.0f} min")


if __name__ == "__main__":
    sys.exit(main())
