"""Stage 05: the training sets ("labelled foods") the category models learn from, in one place.

Every set = USDA FNDDS foods + the example phrases of our definitions + Open Food Facts (OFF) products labelled by their
tags (out/off_train.json, from build_off_train.py). The variants differ only in which OFF products and texts they use.
Used by retrain.py (comparison), serve_models.py (live tester) and eval_greek.py.
"""
import hashlib
import json

import numpy as np

from bench import OUT, load_reference

VARIANTS = {  # retrain, owner 2026-11-18; each adds one change to the one before
    "A": {"label": "200 per category, names", "per_category": 200, "ingr": False, "clean": False},
    "B": {"label": "1,000 per category, names", "per_category": 1000, "ingr": False, "clean": False},
    "C": {"label": "1,000, names + ingredients", "per_category": 1000, "ingr": True, "clean": False},
    "D": {"label": "1,000, names + ingredients, cleaned", "per_category": 1000, "ingr": True, "clean": True},
}
CURRENT = "D"  # the set the live tester uses: chosen in the retrain comparison, REPORT.md Result 7 (2026-11-18)
CLEAN_DROP = OUT / "clean_drop.json"  # written by retrain.py: OFF examples whose neighbours disagree with their label


def ingredient_text(name, ingr):
    return f"{name}. Ingredients of this product: {ingr}."  # the same form as the test texts (text_variants.compose)


def build(cats, variant=CURRENT, langs=("en", "el")):
    """-> texts, codes (np.array), sources (np.array: fndds / definition / off), keys (OFF "barcode|lang", else "")."""
    v = VARIANTS[variant]
    texts, codes, srcs = load_reference(cats)
    texts, codes, srcs = list(texts), list(codes), list(srcs)
    keys = [""] * len(texts)
    drop = set(json.loads(CLEAN_DROP.read_text())["drop"]) if v["clean"] else set()
    for e in json.loads((OUT / "off_train.json").read_text())["examples"]:
        key = f"{e['barcode']}|{e.get('lang', 'en')}"
        if e.get("lang", "en") not in langs or e.get("rank", 0) >= v["per_category"] or key in drop:
            continue
        rows = [e["text"]] + ([ingredient_text(e["text"], e["ingr"])] if v["ingr"] and e.get("ingr") else [])
        for t in rows:
            texts.append(t)
            codes.append(e["code"])
            srcs.append("off")
            keys.append(key)
    return texts, np.array(codes), np.array(srcs), keys


def classifier(key, texts, codes, R):
    """Logistic regression on the embeddings R, cached in out/lr_<model>_<hash of texts + labels>.npz (no pickle)."""
    from sklearn.linear_model import LogisticRegression

    h = hashlib.sha1("\n".join(f"{t}\t{c}" for t, c in zip(texts, codes)).encode()).hexdigest()[:12]
    path = OUT / f"lr_{key}_{h}.npz"
    lr = LogisticRegression(C=20, max_iter=3000)
    if path.exists():
        z = np.load(path, allow_pickle=False)
        lr.coef_, lr.intercept_, lr.classes_ = z["coef"], z["intercept"], z["classes"]
    else:
        lr.fit(R, codes)
        np.savez(path, coef=lr.coef_, intercept=lr.intercept_, classes=lr.classes_)
    return lr
