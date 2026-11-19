#!/usr/bin/env python3
"""Stage 05, step 1 of the plan (owner, 2026-11-18): label products straight from their Open Food Facts tags, no model.

For every catalogue product we look for category tags in Open Food Facts (OFF):
  * OpenNutrition products (≈ 327k): by barcode (only packaged products have one);
  * Greek-market OFF products (26.7k, the food browser's OFF tab): their own tags.
Tags are turned into a category with the hand-written mapping (tools/categories/off_map.py), its name rules
(off_map.NAME_RULES, the same as for the training labels) and the same nutrient rules as the models. Products whose tags conflict or don't map are left to the models.

Measures:
  1. accuracy against the answer key on the 200 test products, next to the 3-model vote;
  2. how much of the catalogue the shortcut covers.

    .venv/bin/python -I stages/05-category-model/tag_shortcut.py
      -> out/tag_labels.json   {"on": {OpenNutrition id: [code, reason]}, "off": {barcode: [code, reason]}} (git-ignored)
      -> a summary on screen
"""
import collections
import csv
import json
import sqlite3
import sys
import time
from pathlib import Path

import pyarrow.parquet as pq

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT / "tools" / "categories"))
sys.path.insert(0, str(HERE))
import off_map  # noqa: E402
from bench import NEVER, ON_TSV, OUT, apply_rules  # noqa: E402
from build_off_train import FAMILY_CODES, PARQUET, nutrients  # noqa: E402
from vote import VOTE, VOTE_ORIGINAL, rank_vote  # noqa: E402

BROWSER_DB = ROOT / "work" / "browser.sqlite"


def code_norm(code):  # same as tools/browser/foods_browser.py
    code = (code or "").strip()
    return (code.lstrip("0") or code) if code.isdigit() else code


def main():
    t0 = time.time()
    csv.field_size_limit(10 ** 9)
    on_type, on_by_code = {}, collections.defaultdict(list)
    with open(ON_TSV, newline="") as f:
        for r in csv.DictReader(f, delimiter="\t", quoting=csv.QUOTE_NONE):
            on_type[r["id"]] = r["type"]
            if r["ean_13"]:
                on_by_code[code_norm(r["ean_13"])].append(r["id"])
    con = sqlite3.connect(BROWSER_DB.as_uri() + "?mode=ro", uri=True)
    greek = {c for (c,) in con.execute("SELECT code_norm FROM off")}
    con.close()
    want = set(on_by_code) | greek
    print(f"OpenNutrition {len(on_type):,} products, {sum(len(v) for v in on_by_code.values()):,} with a barcode · "
          f"Greek OFF {len(greek):,} ({time.time() - t0:.0f}s)", flush=True)

    pf = pq.ParquetFile(PARQUET)
    anc, _ = off_map.ancestors(pf.read(columns=["categories_tags"]).column("categories_tags").to_pylist())
    found = {}  # barcode -> (code or None, reason); "no-tags" when OFF has the product but no category tags
    for batch in pf.iter_batches(batch_size=200_000, columns=["code", "product_name", "categories_tags", "nutriments"]):
        codes = batch.column("code").to_pylist()
        tags = batch.column("categories_tags").to_pylist()
        names = batch.column("product_name").to_pylist()
        nutr_col = batch.column("nutriments")
        for i, c in enumerate(codes):
            bc = code_norm(c)
            if bc not in want or (bc in found and found[bc][0]):  # keep the first labelled copy of a barcode
                continue
            if not tags[i]:
                found.setdefault(bc, (None, "no-tags"))
                continue
            nutr = nutrients(nutr_col[i])
            code, why = off_map.label(tags[i], anc, nutr.get("calories"))
            code, _ = off_map.by_name(code, [n["text"] for n in names[i] or ()])  # same name rules as the training labels
            if code in FAMILY_CODES:
                code = apply_rules(code, nutr)
            if code in NEVER:
                code, why = None, "survey-only"
            found[bc] = (code, why)
    print(f"OFF scanned ({time.time() - t0:.0f}s)", flush=True)

    on_labels = {pid: found[bc] for bc, pids in on_by_code.items() if bc in found for pid in pids}
    off_labels = {bc: found.get(bc, (None, "not-in-dump")) for bc in greek}
    (OUT / "tag_labels.json").write_text(json.dumps({"on": on_labels, "off": off_labels}, ensure_ascii=False))

    # 1. accuracy on the 200 test products
    sample = json.loads((OUT / "sample.json").read_text())
    truth = json.loads((OUT / "review.json").read_text())
    tv = json.loads((OUT / "text_variants.json").read_text())["predictions"]
    VOTE_USED = VOTE if all(f"{k}|title+desc" in tv for k, _ in VOTE) else VOTE_ORIGINAL
    vote = {p["id"]: [c for c, _ in rank_vote([tv[f"{k}|title+desc"][m][p["id"]] for k, m in VOTE_USED])][0] for p in sample}
    rows = collections.Counter()
    by_reason = collections.defaultdict(lambda: [0, 0, 0])  # reason -> [n, tags right, vote right]
    wrong = []
    for p in sample:
        pid, ans = p["id"], truth.get(p["id"])
        if not ans:
            continue
        kind = "packaged" if p["type"] == "grocery" else "other"
        code, why = on_labels.get(pid, (None, "no barcode" if not p.get("ean") else "not in OFF"))
        rows[kind, "n"] += 1
        rows[kind, "vote right"] += vote[pid] == ans
        rows[kind, "combined right"] += (code or vote[pid]) == ans
        if code:
            rows[kind, "tag label"] += 1
            rows[kind, "tag right"] += code == ans
            rows[kind, "vote right where tagged"] += vote[pid] == ans
            if code != ans:
                wrong.append((p["name"], code, ans, why))
        by_reason[why][0] += 1
        by_reason[why][1] += bool(code) and code == ans
        by_reason[why][2] += vote[pid] == ans
    print("\n== 1. Test products (answer key)")
    for kind in ("packaged", "other"):
        n, t = rows[kind, "n"], rows[kind, "tag label"]
        if not n:
            continue
        print(f"{kind}: {n} products · tags give a label for {t} ({t / n:.0%})"
              + (f" · right {rows[kind, 'tag right']}/{t} = {rows[kind, 'tag right'] / t:.0%}"
                 f" (vote on the same: {rows[kind, 'vote right where tagged'] / t:.0%})" if t else "")
              + f" · tags, else vote: {rows[kind, 'combined right'] / n:.1%} vs vote alone {rows[kind, 'vote right'] / n:.1%}")
    n_all = rows["packaged", "n"] + rows["other", "n"]
    print(f"all {n_all}: tags, else vote {(rows['packaged', 'combined right'] + rows['other', 'combined right']) / n_all:.1%}"
          f" vs vote alone {(rows['packaged', 'vote right'] + rows['other', 'vote right']) / n_all:.1%}")
    print("by tag outcome: " + " · ".join(f"{r}: {v[0]} (tags right {v[1]}, vote right {v[2]})"
                                           for r, v in sorted(by_reason.items(), key=lambda x: -x[1][0])))
    cats = {c["code"]: c["name"] for c in json.loads((ROOT / "tools/categories/categories.json").read_text())["categories"]}
    for name, code, ans, why in wrong:
        print(f"  tags wrong ({why}): {name} | tags {code} {cats[code]} · answer {ans} {cats[ans]}")

    # 2. coverage of the catalogue
    print("\n== 2. Catalogue coverage")
    for label, labels, total in (("OpenNutrition", on_labels, len(on_type)), ("Greek OFF", off_labels, len(greek))):
        reasons = collections.Counter(why for _, why in labels.values())
        done = sum(1 for c, _ in labels.values() if c)
        print(f"{label}: {total:,} products · found in OFF {sum(1 for _, w in labels.values() if w != 'not-in-dump'):,}"
              f" · labelled by tags {done:,} ({done / total:.1%}) · " + ", ".join(f"{r} {n:,}" for r, n in reasons.most_common()))
    by_type = collections.Counter(on_type[pid] for pid, (c, _) in on_labels.items() if c)
    print("OpenNutrition labelled by type: " + ", ".join(f"{t} {by_type[t]:,} of {n:,}"
                                                         for t, n in collections.Counter(on_type.values()).most_common()))
    print(f"done in {time.time() - t0:.0f}s -> {OUT / 'tag_labels.json'}")


if __name__ == "__main__":
    sys.exit(main())
