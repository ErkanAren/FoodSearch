#!/usr/bin/env python3
"""Draft of the ≤ 255 food categories (for category icons), built from the data.

Catalogue = the ≈ 313k packaged OpenNutrition products (OFF barcodes), i.e. the whole catalogue, not one market.
  * ~30 parent GROUPS, defined by hand from OFF taxonomy anchor tags (assigned in priority order).
  * Specific categories = the most common "most specific" OFF category tags across the whole catalogue, skipping
    facet tags ("frozen", "snacks", "plant-based"...). No regional additions. Each one gets the parent group that
    most of its products fall into.
  * Coverage is measured with fallback: deepest selected category in the product's tag chain → its group → none.

    python3 -I tools/categories/build_draft.py      # ~2 min: scans the OFF parquet → docs/CATEGORIES-draft.md
"""
import collections
import csv
import sqlite3
import sys
from pathlib import Path

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parent.parent.parent
OUT_MD = ROOT / "docs" / "CATEGORIES-draft.md"
MAX_TOTAL = 255
JUNK = {"en:undefined", "en:null", "en:Undefined"}
FACETS = {  # describe a state / origin / use, not what the food is: never a category of their own
    "en:frozen-foods", "en:plant-based-foods-and-beverages", "en:plant-based-foods", "en:snacks", "en:sweet-snacks",
    "en:groceries", "en:canned-foods", "en:dried-products", "en:fermented-foods", "en:farming-products",
    "en:fresh-foods", "en:refrigerated-foods", "en:dried-products-to-be-rehydrated", "en:non-food-products",
    "en:open-beauty-facts", "en:food-additives", "en:dietary-supplements-for-sports", "en:frozen-plant-based-foods",
    "en:canned-plant-based-foods", "en:foods-for-specific-nutritional-requirements",
    "en:greek-cheeses", "en:greek-oils-and-fats", "en:olive-tree-products", "en:mexican-dinner-mixes",
    "en:licensed-products", "en:specific-products", "en:fruit-based-foods-and-beverages", "en:plant-based-beverages", "en:pastry-helpers", "en:cereals-and-potatoes", "en:fruits-and-vegetables-based-foods",
    "en:fruit-based-foods", "en:sweetened-beverages", "en:unsweetened-beverages", "en:carbonated-drinks",
    "en:frozen-meats", "en:frozen-seafood", "en:frozen-vegetables", "en:frozen-poultry", "en:canned-meats",
    "en:canned-vegetables", "en:canned-fruits", "en:artificially-sweetened-beverages", "en:fruit-based-beverages",
}
# (key, name, icon idea, anchor tags) — order = assignment priority (first match wins)
GROUPS = [
    ("baby", "Baby food", "🍼", ["en:baby-foods", "en:baby-milks"]),
    ("alcohol", "Alcoholic drinks", "🍷", ["en:alcoholic-beverages", "en:wines", "en:beers", "en:spirits"]),
    ("supplements", "Supplements & sports nutrition", "💊", ["en:dietary-supplements", "en:bodybuilding-supplements", "en:protein-powders"]),
    ("plantdrinks", "Plant-based drinks", "🌱", ["en:plant-based-milk-alternatives", "en:oat-based-drinks", "en:almond-based-drinks", "en:soy-based-drinks", "en:rice-based-drinks", "en:coconut-milks-and-creams"]),
    ("icecream", "Ice cream & frozen desserts", "🍦", ["en:ice-creams-and-sorbets", "en:frozen-desserts", "en:ice-creams"]),
    ("cheese", "Cheese", "🧀", ["en:cheeses"]),
    ("yogurt", "Yogurt", "🥛", ["en:yogurts"]),
    ("breakfast", "Breakfast cereals", "🥣", ["en:breakfast-cereals"]),
    ("bars", "Snack & cereal bars", "🍫", ["en:bars", "en:cereal-bars", "en:protein-bars"]),
    ("biscuits", "Biscuits, cakes & pastries", "🍪", ["en:biscuits-and-cakes", "en:biscuits", "en:cakes", "en:pastries", "en:cookies", "en:pie-dough", "en:baking-mixes"]),
    ("chocolate", "Chocolate", "🍫", ["en:chocolates", "en:cocoa-and-its-products", "en:chocolate-candies"]),
    ("sweets", "Sweets & candy", "🍬", ["en:confectioneries", "en:candies", "en:chewing-gum"]),
    ("desserts", "Desserts", "🍮", ["en:desserts"]),
    ("salty", "Salty snacks", "🥨", ["en:salty-snacks", "en:salted-snacks", "en:appetizers", "en:crackers", "en:chips-and-fries", "en:crisps", "en:popcorn", "en:pita-chips", "en:plantain-chips"]),
    ("meals", "Ready meals, pizza & soups", "🍱", ["en:meals", "en:pizzas-pies-and-quiches", "en:pizzas", "en:sandwiches", "en:soups", "en:salads", "en:prepared-salads"]),
    ("fats", "Oils, butter & fats", "🫒", ["en:fats", "en:vegetable-oils", "en:olive-oils", "en:butters", "en:oils"]),
    ("bread", "Bread & bakery", "🍞", ["en:breads", "en:viennoiseries", "en:rusks"]),
    ("pasta_rice", "Pasta, rice & grains", "🍝", ["en:pastas", "en:rices", "en:cereal-grains", "en:flours", "en:noodles", "en:cereals-and-their-products", "en:cereals"]),
    ("potatoes", "Potatoes", "🥔", ["en:potatoes", "en:potato-preparations"]),
    ("sauces", "Sauces, dips & condiments", "🫙", ["en:sauces", "en:condiments", "en:dressings", "en:dips", "en:vinegars", "en:salad-dressings"]),
    ("spreads", "Spreads, honey & jams", "🍯", ["en:spreads", "en:honeys", "en:jams", "en:sweet-spreads", "en:nut-butters", "en:fruit-and-vegetable-preserves"]),
    ("sweeteners", "Sugar & sweeteners", "🍯", ["en:sweeteners", "en:sugars", "en:syrups"]),
    ("spices", "Herbs, spices & baking", "🧂", ["en:spices", "en:herbs", "en:cooking-helpers", "en:baking-decorations", "en:salts", "en:seasonings"]),
    ("processedmeat", "Cold cuts & sausages", "🥓", ["en:prepared-meats", "en:sausages", "en:hams", "en:bacon", "en:salamis"]),
    ("meat", "Meat & poultry", "🥩", ["en:meats", "en:poultries", "en:meat-alternatives"]),
    ("fish", "Fish & seafood", "🐟", ["en:seafood", "en:fishes"]),
    ("eggs", "Eggs", "🥚", ["en:eggs"]),
    ("legumes", "Legumes", "🫘", ["en:legumes", "en:pulses", "en:legumes-and-their-products"]),
    ("nuts", "Nuts & seeds", "🥜", ["en:nuts", "en:seeds", "en:nuts-and-their-products"]),
    ("fruits", "Fruit", "🍎", ["en:fruits", "en:fruits-based-foods", "en:dried-fruits", "en:fruit-based-foods"]),
    ("vegetables", "Vegetables & olives", "🥦", ["en:vegetables", "en:vegetables-based-foods", "en:olives", "en:fruits-and-vegetables-based-foods"]),
    ("dairy", "Milk & cream", "🥛", ["en:dairies", "en:milks", "en:creams", "en:creamer", "en:milk-substitutes"]),
    ("drinks", "Drinks", "🥤", ["en:beverages", "en:waters", "en:sodas", "en:teas", "en:coffees", "en:fruit-juices"]),
    ("snacks", "Snacks (mixed)", "🍿", ["en:snacks", "en:sweet-snacks", "en:snacks-variety-packs"]),  # last: only when nothing more specific fits
]
REGIONAL_ADDITIONS = []  # none: categories are chosen for the whole catalogue (owner, 2026-11-16)
PARENT_OVERRIDE = {  # where the OFF tag chain puts a food in an unhelpful group
    "en:tahini": "spreads", "en:peanut-butters": "spreads", "en:almond-butters": "spreads", "en:nut-butters": "spreads",
    "en:taramasalata": "sauces", "en:iodised-salts": "spices", "en:bouillon-cubes": "spices",
    "en:roasted-peanuts": "nuts", "en:peanuts": "nuts", "en:refried-beans": "legumes", "en:canned-green-beans": "vegetables",
    "en:corned-beef": "meat", "en:penne-rigate": "pasta_rice", "en:tea-bags": "drinks",
}
NICE = {"en:greek-distilled-anis": "Ouzo & tsipouro (anise spirits)", "en:stuffed-vine-leaves": "Stuffed vine leaves (dolmades)",
        "en:tzatzikis": "Tzatziki", "en:feta": "Feta"}


def nice(tag):
    return NICE.get(tag) or tag[3:].replace("-", " ").capitalize()


def group_of(tags):
    tagset = set(tags)
    for key, _, _, anchors in GROUPS:
        if tagset.intersection(anchors):
            return key
    return None


def load():
    csv.field_size_limit(10 ** 9)
    on = set()
    with open(ROOT / "opennutrition-dataset-2025.1" / "opennutrition_foods.tsv", newline="") as f:
        for r in csv.DictReader(f, delimiter="\t"):
            e = (r["ean_13"] or "").strip()
            if e:
                on.add(e.lstrip("0") or e)
    con = sqlite3.connect((ROOT / "work" / "browser.sqlite").as_uri() + "?mode=ro", uri=True)
    gr = {(c.lstrip("0") or c) for (c,) in con.execute("SELECT id FROM off")}
    want = pa.array(list(on | gr))
    pf = pq.ParquetFile(ROOT / "openfoodfacts" / "food.parquet")
    rows = []
    for i in range(pf.num_row_groups):
        codes = pc.utf8_ltrim(pf.read_row_group(i, columns=["code"]).column("code"), "0")
        m = pc.is_in(codes, value_set=want)
        if not pc.any(m).as_py():
            continue
        cats = pf.read_row_group(i, columns=["categories_tags"]).filter(m).column("categories_tags").to_pylist()
        for c, ct in zip(codes.filter(m).to_pylist(), cats):
            tags = [t for t in (ct or []) if t not in JUNK and t.startswith("en:") and " " not in t and t.lower() == t]
            rows.append((c in on, c in gr, tags))
    return rows


def main():
    rows = load()
    anchors = {t for _, _, _, a in GROUPS for t in a}
    last_on, last_gr = collections.Counter(), collections.Counter()
    group_votes = collections.defaultdict(collections.Counter)
    for ion, igr, tags in rows:
        if not tags:
            continue
        spec = next((t for t in reversed(tags) if t not in FACETS), None)
        if spec is None:
            continue
        g = group_of(tags)
        if ion:
            last_on[spec] += 1
        if igr:
            last_gr[spec] += 1
        for t in tags:
            group_votes[t][g] += 1
    parent = {t: v.most_common(1)[0][0] for t, v in group_votes.items()}
    parent.update({t: g for t, g in PARENT_OVERRIDE.items() if t in parent})

    n_specific = MAX_TOTAL - len(GROUPS)
    chosen = [t for t in REGIONAL_ADDITIONS if parent.get(t)]
    for t, _ in last_on.most_common():
        if len(chosen) >= n_specific:
            break
        if t in chosen or t in anchors or t in FACETS or parent.get(t) is None:
            continue
        chosen.append(t)
    chosen_set = set(chosen)

    # coverage with fallback: deepest chosen tag -> group -> none
    cov = {"on": collections.Counter(), "gr": collections.Counter()}
    for ion, igr, tags in rows:
        spec = next((t for t in reversed(tags) if t in chosen_set), None)
        level = "specific" if spec else ("group" if group_of(tags) else "none")
        if ion:
            cov["on"][level] += 1
        if igr:
            cov["gr"][level] += 1

    nonecat = collections.Counter()
    for ion, igr, tags in rows:
        if ion and tags and not any(t in chosen_set for t in tags) and not group_of(tags):
            nonecat[tags[-1]] += 1
    nocat = sum(1 for ion, _, tags in rows if ion and not tags)
    print(f"ON products with no usable category at all: {nocat}; categorised but no group: {sum(nonecat.values())}")
    print("top tags of categorised-but-ungrouped:", nonecat.most_common(30))
    by_group = collections.defaultdict(list)
    for t in chosen:
        by_group[parent[t]].append(t)
    for g in by_group:
        by_group[g].sort(key=lambda t: -last_on[t])

    def pct(c, k):
        return f"{100 * c[k] / max(sum(c.values()), 1):.0f} %"

    lines = [
        "# Food categories (draft, 255)",
        "",
        "Draft built from the data by `tools/categories/build_draft.py`. Every product gets the **most specific category it can**, falls back to its **group**, and then to a generic food icon.",
        "",
        f"**{len(GROUPS)} groups + {len(chosen)} specific categories = {len(GROUPS) + len(chosen)}**, chosen by product count across the whole catalogue (≈ 313k packaged products).",
        "",
        "| Coverage | Specific category | Group only | No category yet |",
        "|---|---|---|---|",
        f"| ≈ 313k packaged products (worldwide) | {pct(cov['on'], 'specific')} | {pct(cov['on'], 'group')} | {pct(cov['on'], 'none')} |",
        "",
        "\"No category yet\" means the product has no usable OFF category. Those products need a category predicted from the name or photo, as do the 13k generic foods.",
        "",
        "Counts: products whose most specific category is this one.",
        "",
    ]
    for key, name, icon, _ in GROUPS:
        tags = by_group.get(key, [])
        lines.append(f"## {icon} {name} ({len(tags)})")
        lines.append("")
        lines.append(", ".join(f"{nice(t)} ({last_on[t]:,})" for t in tags) or "_(group only)_")
        lines.append("")
    OUT_MD.write_text("\n".join(lines))
    print("\n".join(lines[:12]))
    print(f"written {OUT_MD}")
    for key, name, icon, _ in GROUPS:
        tags = by_group.get(key, [])
        print(f"{icon} {name} ({len(tags)}): " + ", ".join(nice(t) for t in tags))


if __name__ == "__main__":
    sys.exit(main())
