#!/usr/bin/env python3
"""Build the food category list: all USDA WWEIA categories (2021-2023, unmerged) + our additions.

Decision (owner, 2026-11-16): use WWEIA as the base and do NOT merge any of its categories; only add what it
lacks. Every product gets exactly one category. Processing state (fresh / frozen / canned / dried) and
"sugar-free" are tags, not categories.

    python3 -I tools/categories/build_list.py      # -> docs/CATEGORIES.md
Needs work/reference/wweia_2021_2023.xlsx (public, https://www.ars.usda.gov/Services/docs.htm?docid=23429).
"""
import sys
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parent.parent.parent
XLSX = ROOT / "work" / "reference" / "wweia_2021_2023.xlsx"
OUT_MD = ROOT / "docs" / "CATEGORIES.md"

GROUPS = [  # (group, sub-group, WWEIA code range by first two digits)
    ("Milk & dairy", "Milk", 10), ("Milk & dairy", "Flavored milk", 12), ("Milk & dairy", "Dairy drinks", 14),
    ("Milk & dairy", "Cheese", 16), ("Milk & dairy", "Yogurt", 18), ("Milk & dairy", "Plant-based alternatives", 19),
    ("Protein foods", "Meats", 20), ("Protein foods", "Poultry", 22), ("Protein foods", "Seafood", 24),
    ("Protein foods", "Eggs", 25), ("Protein foods", "Cured meats", 26), ("Protein foods", "Plant-based protein", 28),
    ("Mixed dishes", "Meat, poultry, seafood", 30), ("Mixed dishes", "Bean & vegetable", 31), ("Mixed dishes", "Grain-based", 32),
    ("Mixed dishes", "Asian", 34), ("Mixed dishes", "Mexican", 35), ("Mixed dishes", "Pizza", 36),
    ("Mixed dishes", "Sandwiches", 37), ("Mixed dishes", "Soups", 38),
    ("Grains", "Cooked grains", 40), ("Grains", "Breads, rolls, tortillas", 42), ("Grains", "Quick breads", 44),
    ("Grains", "Ready-to-eat cereals", 46), ("Grains", "Cooked cereals", 48),
    ("Snacks & sweets", "Savory snacks", 50), ("Snacks & sweets", "Crackers", 52), ("Snacks & sweets", "Bars", 54),
    ("Snacks & sweets", "Sweet bakery", 55), ("Snacks & sweets", "Candy", 57), ("Snacks & sweets", "Other desserts", 58),
    ("Fruit", "Fruits", 60), ("Vegetables", "Vegetables", 64), ("Vegetables", "White potatoes", 68),
    ("Beverages", "100% juice", 70), ("Beverages", "Diet drinks", 71), ("Beverages", "Sweetened drinks", 72),
    ("Beverages", "Coffee & tea", 73), ("Alcoholic beverages", "Alcohol", 75),
    ("Water", "Plain water", 77), ("Water", "Flavored/enhanced water", 78),
    ("Fats & oils", "Fats & oils", 80), ("Condiments & sauces", "Condiments & sauces", 84), ("Sugars", "Sugars", 88),
    ("Infant formula & baby food", "Baby food", 90), ("Infant formula & baby food", "Baby drinks", 92),
    ("Infant formula & baby food", "Infant formula", 94), ("Infant formula & baby food", "Human milk", 96),
    ("Other", "Protein & nutritional powders", 98), ("Other", "Not in a category", 99),
]
# Our additions: (code, name, group, sub-group, note). Where a WWEIA category's name also covers the item,
# the WWEIA category is narrowed ("excluding ...") rather than merged or renamed.
ADDITIONS = [
    ("X01", "Flour", "Grains", "Flour & baking", "New: grocery ingredient, not in WWEIA"),
    ("X02", "Baking ingredients and mixes", "Cooking & baking", "Cooking & baking", "New: baking powder, yeast, cake/pancake mixes, decorations"),
    ("X03", "Salt, herbs and spices", "Cooking & baking", "Cooking & baking", "New: not in WWEIA"),
    ("X04", "Stocks and bouillon", "Cooking & baking", "Cooking & baking", "New: WWEIA 8412 keeps gravies"),
    ("X05", "Vinegar", "Condiments & sauces", "Condiments & sauces", "New: narrows 8406 Mustard and other condiments"),
    ("X06", "Cooking oils", "Fats & oils", "Fats & oils", "New: narrows 8012 Salad dressings and vegetable oils to dressings"),
    ("X07", "Nut and seed butters", "Protein foods", "Plant-based protein", "New: narrows 2804 Nuts and seeds"),
    ("X08", "Chocolate and sweet spreads", "Sugars", "Sugars", "New: narrows 8806 Jams, syrups, toppings"),
    ("X09", "Hot chocolate and drink powders", "Beverages", "Powders & mixes", "New: not in WWEIA"),
    ("X10", "Iced tea", "Beverages", "Coffee & tea", "New: narrows 7304 Tea"),
    ("X11", "Vitamins and supplements", "Other", "Supplements", "New: WWEIA 9802 keeps protein and nutritional powders"),
]


def main():
    ws = openpyxl.load_workbook(XLSX, read_only=True).worksheets[0]
    wweia = {}
    for row in list(ws.iter_rows(values_only=True))[1:]:
        wweia[int(row[2])] = row[3]
    prefix_group = {p: (g, s) for g, s, p in GROUPS}
    rows = []  # (group, sub-group, code, name, note)
    for code in sorted(wweia):
        g, s = prefix_group[code // 100]
        rows.append((g, s, str(code), wweia[code], ""))
    order = []
    for g, _, _ in GROUPS:
        if g not in order:
            order.append(g)
    for code, name, g, s, note in ADDITIONS:
        if g not in order:
            order.insert(order.index("Infant formula & baby food"), g)
        rows.append((g, s, code, name, note))
    rows.sort(key=lambda r: (order.index(r[0]), r[2] if not r[2].startswith("X") else "9" + r[2]))
    total = len(rows)
    L = ["# Food categories", "",
         f"**{total} categories = {len(wweia)} USDA WWEIA (2021–2023, unchanged) + {len(ADDITIONS)} additions (codes X..).** "
         "Maximum allowed: 255.", "",
         "- **Base:** USDA *What We Eat in America* food categories, the category system for every food and drink people consume. "
         "Codes and names are USDA's; none merged (owner decision 2026-11-16). "
         "Source: [USDA ARS](https://www.ars.usda.gov/Services/docs.htm?docid=23429).",
         "- **Additions:** grocery and other items WWEIA lacks. Where a WWEIA name also covers one, that WWEIA category is narrowed (see notes).",
         "- **One category per product.** If nothing fits: 9999 *Not included in a food category*.",
         "- **Tags, not categories:** processing state (fresh / frozen / canned / dried) and sugar-free / diet.",
         "- **Display names:** WWEIA uses US wording (frankfurter, grits, saltines); the app can show friendlier names while keeping the code.",
         "- Built by `tools/categories/build_list.py`; comparison with our earlier list in `CATEGORIES-vs-WWEIA.md`.", "",
         "| Group | Sub-group | Code | Category | Note |", "|---|---|---|---|---|"]
    last = None
    counts = {g: sum(1 for r in rows if r[0] == g) for g in order}
    for g, s, code, name, note in rows:
        L.append(f"| {f'**{g}** ({counts[g]})' if g != last else ''} | {s} | {code} | {name} | {note} |")
        last = g
    OUT_MD.write_text("\n".join(L) + "\n")
    print(f"{total} categories ({len(wweia)} WWEIA + {len(ADDITIONS)} additions) -> {OUT_MD}")
    print({g: counts[g] for g in order})


if __name__ == "__main__":
    sys.exit(main())
