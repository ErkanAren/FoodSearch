#!/usr/bin/env python3
"""Check the icon plan and render it.

    python3 -I tools/categories/build_icons.py
      -> docs/CATEGORY-ICONS.md       (readable plan: icon list + category -> icon table)
      -> tools/categories/icons.json  (machine-readable mapping for the app)

Checks: every category has an icon, every icon used exists, no icon is defined but unused.
"""
import collections
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE))
from icons import EMOJI, GROUP_EMOJI, GROUP_ICONS, ICONS, MAP  # noqa: E402

CATS = HERE / "categories.json"
OUT_MD = ROOT / "docs" / "CATEGORY-ICONS.md"
OUT_JSON = HERE / "icons.json"


def main():
    cats = json.loads(CATS.read_text())["categories"]
    codes = {c["code"] for c in cats}
    assert codes == set(MAP), f"missing: {sorted(codes - set(MAP))}; unknown: {sorted(set(MAP) - codes)}"
    used = {icon for icon, _ in MAP.values()}
    assert used <= set(ICONS), f"undefined icons: {sorted(used - set(ICONS))}"
    unused = set(ICONS) - used
    assert not unused, f"icons defined but unused: {sorted(unused)}"
    assert set(EMOJI) == set(ICONS), f"emoji missing for: {sorted(set(ICONS) - set(EMOJI))}"
    groups = {c["group"] for c in cats}
    assert groups <= set(GROUP_ICONS), f"groups without an icon: {sorted(groups - set(GROUP_ICONS))}"

    users = collections.defaultdict(list)
    for c in cats:
        users[MAP[c["code"]][0]].append(c["code"])
    core = [i for i in ICONS if ICONS[i][1] == "core"]
    extra = [i for i in ICONS if ICONS[i][1] == "extra"]
    shared = {i: v for i, v in users.items() if len(v) > 1}

    OUT_JSON.write_text(json.dumps({
        "version": "2026-11-17",
        "icons": {i: {"draw": d, "tier": t, "categories": users[i], "preview_emoji": EMOJI[i][0],
                      "existing_emoji_fits": EMOJI[i][1]} for i, (d, t) in ICONS.items()},
        "group_icons": {g: {"draw": d, "preview_emoji": GROUP_EMOJI[g]} for g, d in GROUP_ICONS.items()},
        "categories": {c["code"]: {"icon": MAP[c["code"]][0], "badge": MAP[c["code"]][1],
                                   "fallback_group_icon": c["group"]} for c in cats},
    }, ensure_ascii=False, indent=1))

    L = ["# Category icons (draft)", "",
         f"**{len(ICONS)} item icons for {len(cats)} categories** ({len(core)} core + {len(extra)} extra) + "
         f"**{len(GROUP_ICONS)} group icons**.", "",
         "- **Core:** make these. **Extra:** hard-to-draw catch-alls; if not made, the category shows its **group icon**. "
         f"Making only core + group icons = **{len(core) + len(GROUP_ICONS)} icons**.",
         f"- **Shared icons ({len(shared)}):** categories that look the same and differ only by a property (milk fat, sugar, diet) "
         "share one icon, optionally with a small **badge**.",
         "- **Never shown:** 6489, 7702, 9602 (survey-only) and 9999 use the generic food icon.",
         "- **Style:** neutral, international versions of each food. No brands, no country-specific packaging, no text except badges.",
         "- Data: `tools/categories/icons.py` → `python3 -I tools/categories/build_icons.py` → this file + `tools/categories/icons.json`.", "",
         "## Item icons", "", "| Icon | What to draw | Tier | Categories |", "|---|---|---|---|"]
    names = {c["code"]: c["name"] for c in cats}
    for i, (d, t) in ICONS.items():
        L.append(f"| `{i}` | {d} | {t} | {', '.join(f'{c} {names[c]}' for c in users[i])} |")
    L += ["", "## Group icons", "", "| Group | What to draw |", "|---|---|"]
    for g, d in GROUP_ICONS.items():
        L.append(f"| {g} | {d} |")
    L += ["", "## Category → icon", "", "| Group | Code | Category | Icon | Badge |", "|---|---|---|---|---|"]
    last = None
    for c in cats:
        icon, badge = MAP[c["code"]]
        L.append(f"| {c['group'] if c['group'] != last else ''} | {c['code']} | {c['name']} | `{icon}`{' (extra)' if ICONS[icon][1] == 'extra' else ''} | {badge or ''} |")
        last = c["group"]
    OUT_MD.write_text("\n".join(L) + "\n")
    print(f"{len(cats)} categories -> {len(ICONS)} item icons ({len(core)} core, {len(extra)} extra) + {len(GROUP_ICONS)} group icons")
    print(f"shared icons: {len(shared)} -> " + ", ".join(f"{i}×{len(v)}" for i, v in sorted(shared.items(), key=lambda x: -len(x[1]))))
    print(f"badges: {sum(1 for _, b in MAP.values() if b)} categories")
    exact = sum(1 for i in ICONS if EMOJI[i][1])
    print(f"existing emoji fits: {exact} icons · needs a custom icon: {len(ICONS) - exact}")
    print(f"-> {OUT_MD}\n-> {OUT_JSON}")


if __name__ == "__main__":
    sys.exit(main())
