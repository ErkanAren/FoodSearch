#!/usr/bin/env python3
"""Stage 05, improvement step 1: real packaged products as training examples (no LLM, no human labelling).

Labels every Open Food Facts product that has category tags with tools/categories/off_map.py, then keeps up to
N products with an English name per category (most-scanned first, then a fixed pseudo-random order). Products in the 200-product test sample
are never used.

Greek names (owner, 2026-11-18): up to N more examples per category from products with a Greek name, so the models
also learn Greek words ("κουλούρι", "γιαούρτι"). One in ten Greek names (fixed by a hash of the name) is never used for
training: products with only a Greek name from that tenth form the Greek test set (labels from their OFF tags).

Retrain (owner, 2026-11-18): each example also carries its ingredients ("ingr", English for English names, Greek or
English for Greek names, cut near 300 characters) and its "rank" within its category, so smaller sets (rank < 200) can be
compared with the same file.

Name rules (off_map.NAME_RULES, since 2026-11-18): when the tags stop at the general category, the product name decides,
e.g. yogurts named Greek / strained / στραγγιστό -> 1822, "ground beef" tagged only "beef" -> 2004, "sour cream" tagged
only "creams" -> 8006, mac & cheese tagged only "pasta-dishes" -> 3206, root beer under "non-alcoholic-beers" -> 7202.

    .venv/bin/python -I stages/05-category-model/build_off_train.py [--per-category 1000]
      -> stages/05-category-model/out/off_train.json   training examples, "lang": "en" or "el" (git-ignored)
      -> stages/05-category-model/out/greek_test.json  held-out Greek-only products (git-ignored)
      -> docs/OFF-CATEGORY-MAPPING.md                   coverage per category
"""
import argparse
import collections
import hashlib
import json
import re
import sys
import time
from pathlib import Path

import pyarrow.parquet as pq

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT / "tools" / "categories"))
sys.path.insert(0, str(HERE))
import off_map  # noqa: E402
from bench import FAMILIES, NEVER, apply_rules  # noqa: E402
from text_variants import ingredients_text  # noqa: E402

PARQUET = ROOT / "openfoodfacts" / "food.parquet"
CATS = ROOT / "tools" / "categories" / "categories.json"
OUT = HERE / "out" / "off_train.json"
GREEK_TEST = HERE / "out" / "greek_test.json"
DOC = ROOT / "docs" / "OFF-CATEGORY-MAPPING.md"
NUTR = {"fat": "total_fat", "sugars": "total_sugars", "energy-kcal": "calories"}
FAMILY_CODES = {c for codes, _ in FAMILIES.values() for c in codes}
GREEK = re.compile("[\u0370-\u03ff\u1f00-\u1fff]")


def english_name(names):
    for n in names or ():
        if n["lang"] == "en" and n["text"]:
            t = re.sub(r"\s+", " ", n["text"]).strip()
            if 3 <= len(t) <= 100 and re.search(r"[A-Za-z]{3}", t):
                return t
    return None


def greek_name(names):
    """A Greek-script name: the "el" entry first, then any entry written in Greek letters."""
    names = [n for n in names or () if n["text"]]
    for n in sorted(names, key=lambda n: n["lang"] != "el"):
        t = re.sub(r"\s+", " ", n["text"]).strip()
        if 3 <= len(t) <= 100 and len(GREEK.findall(t)) >= 3:
            return t
    return None


name_key = off_map.name_key  # case- and accent-free: "ΚΟΥΛΟΥΡΙ" and "Κουλούρι" are the same name


def ingredients(entries, main_lang, langs):
    """OFF ingredients_text [{lang, text}] -> the first of `langs` available, cut near 300 characters ("" if none)."""
    found = {}
    for e in entries or ():
        lang = main_lang if e["lang"] == "main" else e["lang"]
        if e["text"] and lang not in found:
            found[lang] = e["text"]
    return next((ingredients_text(found[lg]) for lg in langs if lg in found), "")


def held_out(key):
    return int(hashlib.sha1(key.encode()).hexdigest()[:8], 16) % 10 == 0  # one Greek name in ten: test only


def nutrients(cell):
    out = {}
    for n in cell.as_py() or ():
        if n["name"] in NUTR and n["100g"] is not None:
            out[NUTR[n["name"]]] = float(n["100g"])
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--per-category", type=int, default=1000)
    args = ap.parse_args()
    t0 = time.time()
    f = pq.ParquetFile(PARQUET)
    tag_col = f.read(columns=["categories_tags"]).column("categories_tags").to_pylist()
    anc, n_tag = off_map.ancestors(tag_col)
    print(f"tag tree learned: {sum(len(v) for v in anc.values())} parent links among {len(n_tag)} mapped tags "
          f"({time.time() - t0:.0f}s)", flush=True)
    del tag_col

    sample = json.loads((HERE / "out" / "sample.json").read_text())
    test_codes = {p["ean"].lstrip("0") for p in sample if p.get("ean")}
    reasons = collections.Counter()
    labelled = collections.Counter()
    cands = collections.defaultdict(dict)  # code -> {lowercase name: (hash, barcode, name, ingredients)}
    cands_el = collections.defaultdict(dict)  # the same for Greek names
    test_el = {}  # name key -> (hash, barcode, name, code, nutrients): Greek-only products held out for testing
    moved = collections.Counter()  # name rule -> products relabelled
    for batch in f.iter_batches(batch_size=100_000, columns=["code", "product_name", "categories_tags", "nutriments",
                                                              "unique_scans_n", "ingredients_text", "lang"]):
        codes = batch.column("code").to_pylist()
        names = batch.column("product_name").to_pylist()
        tags = batch.column("categories_tags").to_pylist()
        nutr_col = batch.column("nutriments")
        scans = batch.column("unique_scans_n").to_pylist()
        ingr_col = batch.column("ingredients_text")
        main_lang = batch.column("lang").to_pylist()
        for i, tg in enumerate(tags):
            if not tg:
                continue
            short = [t[3:] for t in tg if t.startswith("en:")]
            need_kcal = any(t in off_map.BABY_CONTEXT for t in short)
            nutr = nutrients(nutr_col[i]) if need_kcal else None
            code, why = off_map.label(tg, anc, (nutr or {}).get("calories"))
            reasons[why] += 1
            if not code:
                continue
            code, rule = off_map.by_name(code, [n["text"] for n in names[i] or ()])
            if rule:
                moved[rule] += 1
            if code in FAMILY_CODES:
                nutr = nutr if nutr is not None else nutrients(nutr_col[i])
                code = apply_rules(code, nutr)
            labelled[code] += 1
            bc = (codes[i] or "").lstrip("0")
            if bc in test_codes or code in NEVER:
                continue
            h = (-(scans[i] or 0), hashlib.sha1(bc.encode()).hexdigest())  # most-scanned first: better-checked data
            name = english_name(names[i])
            if name:
                key = name.lower()
                if key not in cands[code] or h < cands[code][key][0]:
                    cands[code][key] = (h, bc, name, ingredients(ingr_col[i].as_py(), main_lang[i], ["en"]))
            gname = greek_name(names[i])
            if gname:
                key = name_key(gname)
                if not held_out(key):
                    if key not in cands_el[code] or h < cands_el[code][key][0]:
                        cands_el[code][key] = (h, bc, gname, ingredients(ingr_col[i].as_py(), main_lang[i], ["el", "en"]))
                elif not name and (key not in test_el or h < test_el[key][0]):  # realistic case: only a Greek name
                    test_el[key] = (h, bc, gname, code, nutr if nutr is not None else nutrients(nutr_col[i]))
    print(f"labelled {sum(labelled.values()):,} products ({time.time() - t0:.0f}s); relabelled by name rules: "
          + ", ".join(f"{k} {v:,}" for k, v in moved.most_common()), flush=True)

    examples = []
    for code, by_name in cands.items():
        for rank, (_, bc, name, ingr) in enumerate(sorted(by_name.values())[:args.per_category]):
            examples.append({"text": name, "code": code, "barcode": bc, "rank": rank, "ingr": ingr})
    for e in examples:
        e["lang"] = "en"
    n_en = len(examples)
    for code, by_name in cands_el.items():  # after the English ones, so the English part stays byte-identical
        for rank, (_, bc, name, ingr) in enumerate(sorted(by_name.values())[:args.per_category]):
            examples.append({"text": name, "code": code, "barcode": bc, "lang": "el", "rank": rank, "ingr": ingr})
    used = collections.Counter(e["code"] for e in examples if e["lang"] == "en")
    used_el = collections.Counter(e["code"] for e in examples if e["lang"] == "el")
    english = {c: len(v) for c, v in cands.items()}
    OUT.write_text(json.dumps({"version": "2026-11-19", "name_rules": moved, "per_category": args.per_category,
                               "examples": examples}, ensure_ascii=False, indent=0))
    GREEK_TEST.write_text(json.dumps({"version": "2026-11-19", "products": [
        {"text": name, "code": code, "barcode": bc, "nutr": nutr} for _, bc, name, code, nutr in sorted(test_el.values())]},
        ensure_ascii=False, indent=0))

    cats = json.loads(CATS.read_text())["categories"]
    tag_count = collections.Counter(c for c, _ in off_map.TAGS.values())
    for b in off_map.BABY.values():
        tag_count[b] += 0
    total = sum(reasons.values())
    L = ["# Open Food Facts tags → our categories", "",
         "Hand-written mapping of Open Food Facts (OFF) category tags to our 183 categories: "
         "`tools/categories/off_map.py` (rules in its header).",
         "This file is generated by `stages/05-category-model/build_off_train.py`.", "",
         "**Use:**",
         "1. Training examples for the category model (stage 05): real packaged products instead of only USDA's generic foods.",
         "2. Later: a direct label for OFF products in the catalogue whose tags are clear.", "",
         f"## Coverage ({time.strftime('%Y-%m-%d')}, OFF dump with {f.metadata.num_rows:,} products)", "",
         f"- **Mapped tags:** {len(off_map.TAGS):,} ({sum(s for _, s in off_map.TAGS.values()):,} strong, "
         f"{sum(not s for _, s in off_map.TAGS.values())} weak) + {len(off_map.BABY)} baby tags.",
         f"- **Products with category tags:** {total:,}.",
         f"- **Labelled:** {sum(labelled.values()):,} ({sum(labelled.values()) / total:.0%}): "
         f"strong tag {reasons['strong']:,} · weak tag only {reasons['weak']:,} · baby {reasons['baby']:,}.",
         f"- **Name rules** (`off_map.NAME_RULES`): when the tags stop at the general category, the product name decides. "
         "Products relabelled: " + "; ".join(f"{k} {v:,}" for k, v in moved.most_common()) + ".",
         f"- **Skipped:** no mapped tag {reasons['unmapped']:,} · conflicting tags {reasons['conflict']:,} · "
         f"non-food {reasons['non-food']:,} · unclear (blocked) {reasons['blocked']:,} · baby, unclear {reasons['baby-unclear']:,}.",
         f"- **Training examples:** up to {args.per_category} per category, English name, de-duplicated, never a "
         f"test-sample product: **{n_en:,}** in {len(used)} categories.",
         f"- **Greek training examples** (since 2026-11-18): up to {args.per_category} more per category from Greek "
         f"names: **{len(examples) - n_en:,}** in {len(used_el)} categories. One Greek name in ten is held out: "
         f"**{len(test_el):,}** products with only a Greek name form the Greek test set (`out/greek_test.json`).", "",
         "| Code | Category | Tags | OFF products labelled | With English name | Training examples | Greek examples |",
         "|---|---|---|---|---|---|---|"]
    for c in cats:
        k = c["code"]
        L.append(f"| {k} | {c['name']} | {tag_count.get(k, 0)} | {labelled.get(k, 0):,} | {english.get(k, 0):,} | "
                 f"{used.get(k, 0)} | {used_el.get(k, 0)} |")
    none = [f"{c['code']} {c['name']}" for c in cats
            if not used.get(c["code"]) and not used_el.get(c["code"]) and c["code"] not in NEVER]
    L += ["", f"**No OFF examples ({len(none)}):** " + "; ".join(none) + ". These still learn from USDA foods and our definitions."]
    DOC.write_text("\n".join(L) + "\n")
    print(f"examples {n_en:,} English in {len(used)} categories + {len(examples) - n_en:,} Greek in {len(used_el)} "
          f"categories -> {OUT}\nGreek test products {len(test_el):,} -> {GREEK_TEST}\n-> {DOC}")
    print("reasons:", dict(reasons.most_common()))
    rnd = collections.defaultdict(list)
    for e in examples:
        if len(rnd[e["code"]]) < 4:
            rnd[e["code"]].append(e["text"])
    for c in cats:
        if rnd.get(c["code"]):
            print(f"  {c['code']} {c['name'][:28]:28} | " + " · ".join(rnd[c["code"]]))


if __name__ == "__main__":
    sys.exit(main())
