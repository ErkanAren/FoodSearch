#!/usr/bin/env python3
"""Check the category definitions and render them for people and for the AI classifier.

    python3 -I tools/categories/build_definitions.py
      -> docs/CATEGORY-DEFINITIONS.md   (readable)
      -> tools/categories/categories.json (the classifier's fixed choice list + instructions)

Checks: every one of the 183 categories (172 WWEIA + X01–X11) has a definition, and every code referenced in a
rule or "not" note exists. USDA example foods (the most reported FNDDS foods per category) are added from
work/reference/wweia_2021_2023.xlsx.
"""
import collections
import json
import re
import sys
from pathlib import Path

import openpyxl

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE))
from build_list import ADDITIONS, GROUPS, XLSX  # noqa: E402
from definitions import DEFS, GLOBAL_RULES  # noqa: E402

OUT_MD = ROOT / "docs" / "CATEGORY-DEFINITIONS.md"
OUT_JSON = HERE / "categories.json"
VERSION = "2026-11-16"
NO_EXAMPLES = {"6489", "7702", "9602", "9999"}  # survey-only or last resort


def short(desc):
    parts = [p.strip() for p in desc.split(",")]
    return re.sub(r"\s+", " ", ", ".join(parts[:2]) if len(parts) > 1 and len(parts[0]) < 12 else parts[0])


def main():
    ws = openpyxl.load_workbook(XLSX, read_only=True).worksheets[0]
    names, foods = {}, collections.defaultdict(list)
    for code, desc, cn, cd, d1, d2 in list(ws.iter_rows(values_only=True))[1:]:
        names[str(cn)] = cd
        foods[str(cn)].append(((d1 or 0) + (d2 or 0), str(desc)))
    prefix = {p: (g, s) for g, s, p in GROUPS}
    cats = []
    for code in sorted(names, key=int):
        g, s = prefix[int(code) // 100]
        cats.append({"code": code, "name": names[code], "group": g, "subgroup": s})
    for code, name, g, s, _ in ADDITIONS:
        cats.append({"code": code, "name": name, "group": g, "subgroup": s})
    codes = {c["code"] for c in cats}

    # --- checks
    missing, extra = codes - set(DEFS), set(DEFS) - codes
    assert not missing and not extra, f"missing definitions: {sorted(missing)}; unknown codes: {sorted(extra)}"
    ref = re.compile(r"\b(\d{4}|X\d{2})\b")
    bad = []
    for code, d in DEFS.items():
        for field in ("d", "inc", "exc"):
            bad += [(code, r) for r in ref.findall(d[field]) if r not in codes]
    for title, text in GLOBAL_RULES:
        bad += [(title, r) for r in ref.findall(text) if r not in codes]
    assert not bad, f"references to unknown codes: {bad}"

    for c in cats:
        d = DEFS[c["code"]]
        c.update(definition=d["d"], includes=d["inc"], excludes=d["exc"])
        if c["code"] in foods and c["code"] not in NO_EXAMPLES:
            seen, ex = set(), []
            for _, desc in sorted(foods[c["code"]], reverse=True):
                s = short(desc)
                if s.lower() not in seen:
                    seen.add(s.lower())
                    ex.append(s)
                if len(ex) == 6:
                    break
            c["usda_examples"] = ex
        c["assignable"] = c["code"] not in {"6489", "7702", "9602"}

    OUT_JSON.write_text(json.dumps({
        "version": VERSION,
        "source": "USDA WWEIA food categories 2021-2023 (unmerged) + KnowD1 additions X01-X11",
        "rules": [{"title": t, "text": x} for t, x in GLOBAL_RULES],
        "categories": cats,
    }, ensure_ascii=False, indent=1))

    groups = []
    for c in cats:
        if c["group"] not in groups:
            groups.append(c["group"])
    L = ["# Food category definitions", "",
         f"Version {VERSION}. **{len(cats)} categories** (`CATEGORIES.md`): 172 USDA WWEIA + 11 additions (X01–X11). "
         "These definitions are the instructions for the AI that will assign one category to every product. "
         "Borderline foods follow USDA's own placements where USDA has them; deviations are marked *(differs from USDA)*. "
         "Machine-readable copy: `tools/categories/categories.json`. Edit `tools/categories/definitions.py` and re-run "
         "`python3 -I tools/categories/build_definitions.py`.", "",
         "## Rules for every product", ""]
    for i, (t, x) in enumerate(GLOBAL_RULES, 1):
        L.append(f"{i}. **{t}.** {x}")
    L.append("")
    for g in groups:
        members = [c for c in cats if c["group"] == g]
        L += [f"## {g} ({len(members)})", ""]
        for c in members:
            line = f"- **{c['code']} {c['name']}**: {c['definition']}"
            if c["includes"] and c["includes"] != "—":
                line += f"<br>*Includes:* {c['includes']}."
            if c["excludes"]:
                line += f"<br>*Not:* {c['excludes']}."
            if c.get("usda_examples"):
                line += f"<br>*USDA examples:* {' · '.join(c['usda_examples'])}"
            L.append(line)
        L.append("")
    OUT_MD.write_text("\n".join(L))

    prompt_chars = sum(len(c["code"]) + len(c["name"]) + len(c["definition"]) + len(c["includes"]) + len(c["excludes"]) + 12 for c in cats) \
        + sum(len(t) + len(x) for t, x in GLOBAL_RULES)
    print(f"{len(cats)} categories defined, all references valid")
    print(f"-> {OUT_MD}\n-> {OUT_JSON}")
    print(f"instruction size ≈ {prompt_chars:,} characters ≈ {prompt_chars // 4:,} tokens (without USDA examples)")


if __name__ == "__main__":
    sys.exit(main())
