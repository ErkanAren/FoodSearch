#!/usr/bin/env python3
"""Stage 05: which FREE, non-generative model best assigns our 183 food categories? (no LLM, owner 2026-11-16)

Sample: 200 OpenNutrition products (150 packaged + ~50 everyday / prepared / restaurant), fixed pseudo-random.
Models (sentence-transformers embedding models, downloaded once into work/models/hf):
    e5-small, e5-large-instruct, bge-m3, arctic-l-v2, qwen3-0.6b
Methods per model:
    zs   zero-shot: nearest category description (name + definition + examples)
    knn  nearest labelled foods: USDA FNDDS foods with their WWEIA category (≈ 5.3k) + the example phrases in our definitions
    lr   logistic regression trained on the same labelled foods
Every prediction then passes the same deterministic nutrient rules (milk fat, cereal sugar, diet drinks) and never
lands on a survey-only category.

    .venv/bin/python -I stages/05-category-model/bench.py run      # embeddings + predictions + USDA cross-validation
    .venv/bin/python -I stages/05-category-model/bench.py score    # accuracy vs the owner's answers (review page)

Outputs (git-ignored): stages/05-category-model/out/
"""
import argparse
import csv
import hashlib
import json
import re
import sys
import time
from pathlib import Path

import numpy as np
import openpyxl

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
OUT = HERE / "out"
HF_CACHE = ROOT / "work" / "models" / "hf"
ON_TSV = ROOT / "opennutrition-dataset-2025.1" / "opennutrition_foods.tsv"
XLSX = ROOT / "work" / "reference" / "wweia_2021_2023.xlsx"
CATS = ROOT / "tools" / "categories" / "categories.json"
SAMPLE = {"grocery": 150, "everyday": 17, "prepared": 17, "restaurant": 16}
NEVER = {"6489", "7702", "9602", "9999"}  # survey-only + last resort: not predicted by the models
TASK = "Classify this food product into its food category"
MODELS = {  # key: (hub id, prompt for products and labelled foods, prompt for category descriptions)
    "e5-small": ("intfloat/multilingual-e5-small", "query: ", "passage: "),
    "e5-large-instruct": ("intfloat/multilingual-e5-large-instruct", f"Instruct: {TASK}\nQuery: ", ""),
    "bge-m3": ("BAAI/bge-m3", "", ""),
    "arctic-l-v2": ("Snowflake/snowflake-arctic-embed-l-v2.0", "query: ", ""),
    "qwen3-0.6b": ("Qwen/Qwen3-Embedding-0.6B", f"Instruct: {TASK}\nQuery:", ""),
}
FAMILIES = {  # nutrient rules: (codes in the family, function of nutrients -> code)
    "milk": ({"1002", "1004", "1006", "1008"}, lambda n: _by_fat(n, ["1002", "1004", "1006", "1008"])),
    "flavored_milk": ({"1202", "1204", "1206", "1208"}, lambda n: _by_fat(n, ["1202", "1204", "1206", "1208"])),
    "cereal": ({"4602", "4604"}, lambda n: None if n.get("total_sugars") is None else ("4602" if n["total_sugars"] > 21.2 else "4604")),
    "soft": ({"7202", "7102"}, lambda n: _diet(n, "7102", "7202")),
    "sport": ({"7206", "7104"}, lambda n: _diet(n, "7104", "7206")),
    "fruitdrink": ({"7204", "7106"}, lambda n: _diet(n, "7106", "7204")),
}


def _by_fat(n, codes):
    fat = n.get("total_fat")
    if fat is None:
        return codes[1]
    return codes[0] if fat >= 3.0 else codes[1] if fat >= 1.8 else codes[2] if fat >= 0.6 else codes[3]


def _diet(n, diet, regular):
    s = n.get("total_sugars")
    return None if s is None else (diet if s <= 1.0 else regular)


def apply_rules(code, nutr):
    for codes, fn in FAMILIES.values():
        if code in codes:
            return fn(nutr) or code
    return code


def first_sentence(text, limit=220):
    s = re.split(r"(?<=[.!?])\s", (text or "").strip(), maxsplit=1)[0]
    return s[:limit]


def load_sample():
    csv.field_size_limit(10 ** 9)
    picked = {t: [] for t in SAMPLE}
    rows = []
    with open(ON_TSV, newline="") as f:
        for r in csv.DictReader(f, delimiter="\t"):
            rows.append((hashlib.sha1(r["id"].encode()).hexdigest(), r))
    rows.sort(key=lambda x: x[0])
    for _, r in rows:
        t = r["type"]
        if len(picked[t]) < SAMPLE[t]:
            n = json.loads(r["nutrition_100g"] or "{}")
            picked[t].append({
                "id": r["id"], "type": t, "name": r["name"], "ean": r["ean_13"] or None,
                "description": first_sentence(r["description"]),
                "ingredients": (r["ingredients"] or "")[:200],
                "nutr": {k: n.get(k) for k in ("total_fat", "total_sugars", "carbohydrates", "calories")},
            })
        if all(len(picked[t]) == SAMPLE[t] for t in SAMPLE):
            break
    return [p for t in SAMPLE for p in picked[t]]


def product_text(p):
    return f"{p['name']}. {p['description']}".strip()


def load_reference(cats):
    """Labelled foods: USDA FNDDS descriptions with their WWEIA code + the example phrases of our definitions."""
    ref_text, ref_code, ref_src = [], [], []
    ws = openpyxl.load_workbook(XLSX, read_only=True).worksheets[0]
    for _, desc, cn, _, _, _ in list(ws.iter_rows(values_only=True))[1:]:
        code = str(cn)
        if code in NEVER:
            continue
        ref_text.append(str(desc)); ref_code.append(code); ref_src.append("fndds")
    for c in cats:
        if c["code"] in NEVER:
            continue
        phrases = [c["name"]] + [x.strip() for x in re.split(r",|;", re.sub(r"\([^)]*\)", "", c["includes"])) if len(x.strip()) > 2]
        for ph in phrases:
            ref_text.append(ph); ref_code.append(c["code"]); ref_src.append("definition")
    return ref_text, np.array(ref_code), np.array(ref_src)


def prototype_text(c):
    return f"{c['name']}: {c['definition']} Includes: {c['includes']}."


def knn_scores(sim, ref_code, classes, k=10):
    """sim: (n, m) similarities to labelled foods -> (n, classes) weighted votes of the k nearest."""
    idx = np.argsort(-sim, axis=1)[:, :k]
    cidx = {c: i for i, c in enumerate(classes)}
    out = np.zeros((sim.shape[0], len(classes)))
    for r in range(sim.shape[0]):
        for j in idx[r]:
            out[r, cidx[ref_code[j]]] += np.exp(sim[r, j] / 0.05)
    return out / out.sum(1, keepdims=True)


def top3(scores, classes):
    order = np.argsort(-scores, axis=1)[:, :3]
    return [[classes[i] for i in row] for row in order]


def run(args):
    from sentence_transformers import SentenceTransformer
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import StratifiedKFold

    OUT.mkdir(parents=True, exist_ok=True)
    cats = [c for c in json.loads(CATS.read_text())["categories"]]
    usable = [c for c in cats if c["code"] not in NEVER]
    classes = [c["code"] for c in usable]
    sample = load_sample()
    (OUT / "sample.json").write_text(json.dumps(sample, ensure_ascii=False, indent=1))
    ref_text, ref_code, ref_src = load_reference(cats)
    print(f"sample {len(sample)} products · labelled foods {len(ref_text)} (USDA {int((ref_src == 'fndds').sum())}) · {len(classes)} categories", flush=True)

    preds_path = OUT / "predictions.json"
    preds = json.loads(preds_path.read_text()) if preds_path.exists() else {}
    for key in args.models.split(","):
        hub, qp, dp = MODELS[key]
        print(f"\n== {key} ({hub})", flush=True)
        t0 = time.time()
        local = ROOT / "work" / "models" / "st" / hub.replace("/", "__")  # fetched by fetch_models.sh (curl)
        model = SentenceTransformer(str(local) if (local / "config.json").exists() else hub, cache_folder=str(HF_CACHE), device=args.device)
        t_load = time.time() - t0
        enc = lambda texts, prompt: model.encode(texts, prompt=prompt, batch_size=64, normalize_embeddings=True,  # noqa: E731
                                                 convert_to_numpy=True, show_progress_bar=False)
        t0 = time.time()
        P = enc([product_text(p) for p in sample], qp)
        t_prod = time.time() - t0
        R = enc(ref_text, qp)
        C = enc([prototype_text(c) for c in usable], dp)
        print(f"  loaded {t_load:.0f}s · 200 products {t_prod:.1f}s ({len(sample) / t_prod:.0f}/s) · all embeddings {time.time() - t0:.0f}s", flush=True)

        # --- USDA cross-validation (label-free benchmark): train on 4/5 of USDA foods + definition phrases, test on 1/5
        fn = np.where(ref_src == "fndds")[0]
        dfn = np.where(ref_src == "definition")[0]
        y = ref_code[fn]
        skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=0)
        hits = {"zs": 0, "knn": 0, "lr": 0}
        yy = np.array([c if (y == c).sum() >= 5 else "rare" for c in y])  # stratify; rare classes go anywhere
        for tr, te in skf.split(fn, yy):
            tr_idx = np.concatenate([fn[tr], dfn])
            sim = R[fn[te]] @ R[tr_idx].T
            hits["knn"] += sum(a[0] == b for a, b in zip(top3(knn_scores(sim, ref_code[tr_idx], classes), classes), y[te]))
            lr = LogisticRegression(C=20, max_iter=3000).fit(R[tr_idx], ref_code[tr_idx])
            pr = lr.predict(R[fn[te]])
            hits["lr"] += int((pr == y[te]).sum())
        zs = top3(R[fn] @ C.T, classes)
        hits["zs"] = sum(a[0] == b for a, b in zip(zs, y))
        cv = {m: round(h / len(fn), 3) for m, h in hits.items()}
        print(f"  USDA foods top-1 accuracy: zero-shot {cv['zs']:.1%} · kNN {cv['knn']:.1%} · classifier {cv['lr']:.1%}", flush=True)

        # --- the 200-product sample
        lr = LogisticRegression(C=20, max_iter=3000).fit(R, ref_code)
        lr_classes = list(lr.classes_)
        lr_p = lr.predict_proba(P)
        lr_full = np.zeros((len(sample), len(classes)))
        for j, c in enumerate(lr_classes):
            lr_full[:, classes.index(c)] = lr_p[:, j]
        per_method = {
            "zs": top3(P @ C.T, classes),
            "knn": top3(knn_scores(P @ R.T, ref_code, classes), classes),
            "lr": top3(lr_full, classes),
        }
        out = {}
        for m, tops in per_method.items():
            out[m] = {}
            for p, t in zip(sample, tops):
                ruled = [apply_rules(c, p["nutr"]) for c in t]
                out[m][p["id"]] = list(dict.fromkeys(ruled))  # keep order, drop duplicates created by the rules
        preds[key] = {"methods": out, "usda_cv_top1": cv, "products_per_s": round(len(sample) / t_prod, 1), "load_s": round(t_load, 1)}
        preds_path.write_text(json.dumps(preds, indent=1))
        del model


def score(_args):
    rv_path = OUT / "review.json"
    preds = json.loads((OUT / "predictions.json").read_text())
    sample = {p["id"]: p for p in json.loads((OUT / "sample.json").read_text())}
    truth = json.loads(rv_path.read_text()) if rv_path.exists() else {}
    truth = {k: v for k, v in truth.items() if v}
    print(f"{len(truth)}/{len(sample)} products have an answer\n")
    rows = []
    for key, info in preds.items():
        for m, by_pid in info["methods"].items():
            top1 = sum(by_pid[pid][0] == code for pid, code in truth.items())
            top3 = sum(code in by_pid[pid][:3] for pid, code in truth.items())
            pk = sum(by_pid[pid][0] == code for pid, code in truth.items() if sample[pid]["type"] == "grocery")
            nk = sum(1 for pid in truth if sample[pid]["type"] == "grocery")
            rows.append((top1 / max(len(truth), 1), key, m, top1, top3, pk, nk, info["usda_cv_top1"][m], info["products_per_s"]))
    rows.sort(reverse=True)
    print(f"{'model':18} {'method':6} {'top-1':>7} {'top-3':>7} {'packaged top-1':>15} {'USDA CV':>8} {'products/s':>11}")
    for acc, key, m, t1, t3, pk, nk, cv, sp in rows:
        print(f"{key:18} {m:6} {acc:7.1%} {t3 / max(len(truth), 1):7.1%} {pk / max(nk, 1):15.1%} {cv:8.1%} {sp:11.0f}")
    (OUT / "scores.json").write_text(json.dumps([dict(zip(["top1", "model", "method", "hits1", "hits3", "packaged_hits1", "packaged_n", "usda_cv", "products_per_s"], r)) for r in rows], indent=1))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--models", default=",".join(MODELS))
    r.add_argument("--device", default="mps")
    sub.add_parser("score")
    args = ap.parse_args()
    run(args) if args.cmd == "run" else score(args)


if __name__ == "__main__":
    sys.exit(main())
