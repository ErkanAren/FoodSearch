#!/usr/bin/env python3
"""Compare our food category list (v2, 115 categories) with USDA's WWEIA food categories (2021-2023, 172).

WWEIA = "What We Eat in America", USDA's category system for every food and drink people consume.
Source spreadsheet (public, US government): https://www.ars.usda.gov/Services/docs.htm?docid=23429
Expected at work/reference/wweia_2021_2023.xlsx (git-ignored).

    python3 -I tools/categories/compare_wweia.py      # -> docs/CATEGORIES-vs-WWEIA.md
"""
import collections
import sys
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parent.parent.parent
XLSX = ROOT / "work" / "reference" / "wweia_2021_2023.xlsx"
OUT_MD = ROOT / "docs" / "CATEGORIES-vs-WWEIA.md"

# Our list, v2 (2026-11-16): 21 groups, 115 categories
OURS = {
    "Dairy & eggs": ["Milk", "Flavoured milk & milkshakes", "Yogurt & fermented milk", "Cheese",
                     "Fresh cheese (cottage, ricotta, cream cheese)", "Cream & sour cream", "Butter", "Eggs"],
    "Plant-based": ["Plant-based milk", "Plant-based yogurt & desserts", "Tofu & meat alternatives"],
    "Meat & poultry": ["Red meat", "Poultry", "Breaded chicken & nuggets", "Cold cuts & cured meats", "Bacon", "Sausages & hot dogs"],
    "Fish & seafood": ["Fish", "Canned fish", "Shellfish"],
    "Fruit": ["Fresh fruit", "Dried fruit", "Canned & frozen fruit"],
    "Vegetables & legumes": ["Fresh vegetables", "Salad greens", "Canned & frozen vegetables", "Potatoes",
                             "Fries & potato products", "Legumes", "Olives & pickles"],
    "Nuts & seeds": ["Nuts & seeds", "Nut & seed butters"],
    "Bread & bakery": ["Bread", "Rolls, buns & bagels", "Flatbreads & tortillas", "Crackers & crispbreads"],
    "Grains & cereals": ["Rice", "Pasta", "Noodles", "Couscous, quinoa & other grains", "Flour", "Breakfast cereals", "Oats & porridge"],
    "Sweets & desserts": ["Cakes & pies", "Biscuits & cookies", "Doughnuts & sweet pastries", "Chocolate", "Candy & gum",
                          "Ice cream & frozen desserts", "Puddings & jelly desserts", "Cereal & granola bars"],
    "Salty snacks": ["Chips & crisps", "Popcorn", "Pretzels & snack mixes"],
    "Meals & dishes": ["Burgers", "Sandwiches", "Hot dogs", "Wraps, burritos & tacos", "Pizza", "Pasta dishes", "Rice dishes",
                       "Noodle dishes", "Sushi & dumplings", "Soups", "Stews & curries", "Salads", "Meat & poultry dishes",
                       "Fish & seafood dishes", "Vegetable & legume dishes", "Savoury pies & pastries", "Breakfast dishes"],
    "Sauces & condiments": ["Ketchup & tomato condiments", "Mustard & other condiments", "Mayonnaise", "Salad dressings",
                            "Pasta & cooking sauces", "Soy & Asian sauces", "Hot sauces", "Dips & savoury spreads"],
    "Sugar & sweet spreads": ["Sugar & honey", "Sweeteners", "Jams & syrups", "Chocolate & sweet spreads"],
    "Oils & fats": ["Olive oil", "Vegetable oils", "Margarine & cooking fats"],
    "Cooking & baking": ["Salt, herbs & spices", "Stocks, bouillon & gravy", "Vinegar", "Baking ingredients & mixes"],
    "Drinks": ["Water", "Sparkling & flavoured water", "Soft drinks", "Diet & zero soft drinks", "Juices (100%)",
               "Fruit drinks & nectars", "Smoothies", "Energy drinks", "Sports drinks", "Coffee", "Tea", "Iced tea",
               "Hot chocolate & drink powders"],
    "Alcohol": ["Beer", "Wine", "Spirits & liqueurs", "Cider, seltzers & mixed drinks"],
    "Baby & infant": ["Infant formula", "Baby food (purees & meals)", "Baby snacks, cereals & drinks"],
    "Sports & nutrition": ["Protein powders & shakes", "Protein & nutrition bars", "Nutrition drinks & meal replacements",
                           "Vitamins & supplements"],
    "Other": ["Other"],
}

# WWEIA category -> our category (or several, when WWEIA's category spans more than one of ours)
MAP = {
    "Milk, whole": "Milk", "Milk, reduced fat": "Milk", "Milk, lowfat": "Milk", "Milk, nonfat": "Milk",
    "Flavored milk, whole": "Flavoured milk & milkshakes", "Flavored milk, reduced fat": "Flavoured milk & milkshakes",
    "Flavored milk, lowfat": "Flavoured milk & milkshakes", "Flavored milk, nonfat": "Flavoured milk & milkshakes",
    "Milk shakes and other dairy drinks": "Flavoured milk & milkshakes",
    "Cheese": "Cheese", "Cottage/ricotta cheese": "Fresh cheese (cottage, ricotta, cream cheese)",
    "Yogurt, regular": "Yogurt & fermented milk", "Yogurt, Greek": "Yogurt & fermented milk",
    "Plant-based milk": "Plant-based milk", "Plant-based yogurt": "Plant-based yogurt & desserts",
    "Beef, excludes ground": "Red meat", "Ground beef": "Red meat", "Pork": "Red meat", "Lamb, goat, game": "Red meat",
    "Liver and organ meats": "Red meat",
    "Chicken, whole pieces": "Poultry", "Chicken patties, nuggets and tenders": "Breaded chicken & nuggets",
    "Turkey, duck, other poultry": "Poultry",
    "Fish": ["Fish", "Canned fish"], "Shellfish": "Shellfish", "Eggs and omelets": ["Eggs", "Breakfast dishes"],
    "Cold cuts and cured meats": "Cold cuts & cured meats", "Bacon": "Bacon", "Frankfurters": "Sausages & hot dogs",
    "Sausages": "Sausages & hot dogs",
    "Beans, peas, legumes": "Legumes", "Nuts and seeds": ["Nuts & seeds", "Nut & seed butters"],
    "Soy and meat-alternative products": "Tofu & meat alternatives",
    "Meat mixed dishes": "Meat & poultry dishes", "Poultry mixed dishes": "Meat & poultry dishes",
    "Seafood mixed dishes": "Fish & seafood dishes",
    "Bean, pea, legume dishes": "Vegetable & legume dishes", "Vegetable dishes": "Vegetable & legume dishes",
    "Rice mixed dishes": "Rice dishes", "Pasta mixed dishes, excludes macaroni and cheese": "Pasta dishes",
    "Macaroni and cheese": "Pasta dishes", "Turnovers and other grain-based items": "Savoury pies & pastries",
    "Fried rice and lo/chow mein": ["Rice dishes", "Noodle dishes"],
    "Stir-fry and soy-based sauce mixtures": ["Meat & poultry dishes", "Vegetable & legume dishes"],
    "Egg rolls, dumplings, sushi": "Sushi & dumplings",
    "Burritos and tacos": "Wraps, burritos & tacos", "Nachos": "Wraps, burritos & tacos",
    "Other Mexican mixed dishes": "Wraps, burritos & tacos",
    "Pizza": "Pizza",
    "Burgers": "Burgers", "Frankfurter sandwiches": "Hot dogs", "Chicken fillet sandwiches": "Sandwiches",
    "Egg/breakfast sandwiches": "Sandwiches", "Cheese sandwiches": "Sandwiches",
    "Peanut butter and jelly sandwiches": "Sandwiches", "Seafood sandwiches": "Sandwiches",
    "Deli and cured meat sandwiches": "Sandwiches", "Meat and BBQ sandwiches": "Sandwiches",
    "Vegetable sandwiches/burgers": ["Sandwiches", "Burgers"],
    "Soups, broth-based": "Soups", "Soups, cream-based": "Soups", "Ramen and Asian broth-based soups": ["Soups", "Noodle dishes"],
    "Rice": "Rice", "Pasta, noodles, cooked grains": ["Pasta", "Noodles", "Couscous, quinoa & other grains"],
    "Yeast breads": "Bread", "Rolls and buns": "Rolls, buns & bagels", "Bagels and English muffins": "Rolls, buns & bagels",
    "Tortillas": "Flatbreads & tortillas",
    "Biscuits, muffins, quick breads": ["Cakes & pies", "Bread"], "Pancakes, waffles, French toast": "Breakfast dishes",
    "Ready-to-eat cereal, higher sugar (>21.2g/100g)": "Breakfast cereals",
    "Ready-to-eat cereal, lower sugar (=<21.2g/100g)": "Breakfast cereals",
    "Oatmeal": "Oats & porridge", "Grits and other cooked cereals": "Oats & porridge",
    "Potato chips": "Chips & crisps", "Tortilla, corn, other chips": "Chips & crisps", "Popcorn": "Popcorn",
    "Pretzels/snack mix": "Pretzels & snack mixes",
    "Crackers, excludes saltines": "Crackers & crispbreads", "Saltine crackers": "Crackers & crispbreads",
    "Cereal bars": "Cereal & granola bars", "Nutrition bars": "Protein & nutrition bars",
    "Cakes and pies": "Cakes & pies", "Cookies and brownies": "Biscuits & cookies",
    "Doughnuts, sweet rolls, pastries": "Doughnuts & sweet pastries",
    "Candy containing chocolate": "Chocolate", "Candy not containing chocolate": "Candy & gum",
    "Ice cream and frozen dairy desserts": "Ice cream & frozen desserts", "Pudding": "Puddings & jelly desserts",
    "Gelatins, ices, sorbets": ["Puddings & jelly desserts", "Ice cream & frozen desserts"],
    "Apples": "Fresh fruit", "Bananas": "Fresh fruit", "Grapes": "Fresh fruit", "Peaches and nectarines": "Fresh fruit",
    "Strawberries": "Fresh fruit", "Blueberries and other berries": "Fresh fruit", "Citrus fruits": "Fresh fruit",
    "Melons": "Fresh fruit", "Dried fruits": "Dried fruit", "Other fruits and fruit salads": "Fresh fruit",
    "Pears": "Fresh fruit", "Pineapple": "Fresh fruit", "Mango and papaya": "Fresh fruit",
    "Tomatoes": "Fresh vegetables", "Carrots": "Fresh vegetables", "Other red and orange vegetables": "Fresh vegetables",
    "Broccoli": "Fresh vegetables", "Spinach": "Fresh vegetables", "Lettuce and lettuce salads": ["Salad greens", "Salads"],
    "Other dark green vegetables": "Fresh vegetables", "String beans": "Fresh vegetables", "Cabbage": "Fresh vegetables",
    "Onions": "Fresh vegetables", "Corn": "Fresh vegetables", "Other starchy vegetables": "Fresh vegetables",
    "Other vegetables and combinations": "Fresh vegetables", "Fried vegetables": "Vegetable & legume dishes",
    "Coleslaw, non-lettuce salads": "Salads", "Vegetables on a sandwich": "Fresh vegetables",
    "White potatoes, baked or boiled": "Potatoes", "French fries and other fried white potatoes": "Fries & potato products",
    "Mashed potatoes and white potato mixtures": "Potatoes",
    "Citrus juice": "Juices (100%)", "Apple juice": "Juices (100%)", "Other fruit juice": "Juices (100%)",
    "Vegetable juice": "Juices (100%)",
    "Diet soft drinks": "Diet & zero soft drinks", "Diet sport and energy drinks": ["Energy drinks", "Sports drinks"],
    "Other diet drinks": "Diet & zero soft drinks",
    "Soft drinks": "Soft drinks", "Fruit drinks": "Fruit drinks & nectars", "Sport and energy drinks": ["Energy drinks", "Sports drinks"],
    "Nutritional beverages": "Nutrition drinks & meal replacements", "Smoothies and grain drinks": "Smoothies",
    "Coffee": "Coffee", "Tea": ["Tea", "Iced tea"],
    "Beer": "Beer", "Wine": "Wine", "Liquor and cocktails": ["Spirits & liqueurs", "Cider, seltzers & mixed drinks"],
    "Tap water": "Water", "Bottled water": "Water", "Flavored or carbonated water": "Sparkling & flavoured water",
    "Enhanced water": "Sparkling & flavoured water",
    "Butter and animal fats": ["Butter", "Margarine & cooking fats"], "Margarine": "Margarine & cooking fats",
    "Cream cheese, sour cream, whipped cream": ["Fresh cheese (cottage, ricotta, cream cheese)", "Cream & sour cream"],
    "Cream and cream substitutes": "Cream & sour cream", "Mayonnaise": "Mayonnaise",
    "Salad dressings and vegetable oils": ["Salad dressings", "Vegetable oils", "Olive oil"],
    "Tomato-based condiments": "Ketchup & tomato condiments", "Soy-based condiments": "Soy & Asian sauces",
    "Mustard and other condiments": "Mustard & other condiments", "Olives, pickles, pickled vegetables": "Olives & pickles",
    "Pasta sauces, tomato-based": "Pasta & cooking sauces",
    "Dips, gravies, other sauces": ["Dips & savoury spreads", "Stocks, bouillon & gravy", "Hot sauces"],
    "Sugars and honey": "Sugar & honey", "Sugar substitutes": "Sweeteners", "Jams, syrups, toppings": "Jams & syrups",
    "Baby food: cereals": "Baby snacks, cereals & drinks", "Baby food: fruit": "Baby food (purees & meals)",
    "Baby food: vegetables": "Baby food (purees & meals)", "Baby food: mixtures": "Baby food (purees & meals)",
    "Baby food: meat and dinners": "Baby food (purees & meals)", "Baby food: yogurt": "Baby food (purees & meals)",
    "Baby food: snacks and sweets": "Baby snacks, cereals & drinks",
    "Baby juice": "Baby snacks, cereals & drinks", "Baby water": "Baby snacks, cereals & drinks",
    "Formula, ready-to-feed": "Infant formula", "Formula, prepared from powder": "Infant formula",
    "Human milk": None,  # not a product
    "Protein and nutritional powders": "Protein powders & shakes",
    "Not included in a food category": "Other",
}


def main():
    ws = openpyxl.load_workbook(XLSX, read_only=True).worksheets[0]
    wweia, foods = {}, collections.Counter()
    for row in list(ws.iter_rows(values_only=True))[1:]:
        wweia[row[2]] = row[3]
        foods[row[3]] += 1  # number of FNDDS foods in the category (how big it is in USDA's own database)
    names = [wweia[k] for k in sorted(wweia)]
    missing = [n for n in names if n not in MAP]
    assert not missing, f"unmapped WWEIA categories: {missing}"
    ours = [c for cats in OURS.values() for c in cats]
    assert len(ours) == len(set(ours)) == 115, len(ours)
    for n, t in MAP.items():
        for c in ([t] if isinstance(t, str) else (t or [])):
            assert c in ours, f"{n} -> unknown category {c}"

    back = collections.defaultdict(list)
    for n in names:
        t = MAP[n]
        for c in ([t] if isinstance(t, str) else (t or [])):
            back[c].append(n)
    ours_only = [c for c in ours if not back[c]]
    one_to_one = [c for c in ours if len(back[c]) == 1 and isinstance(MAP[back[c][0]], str)]
    merged = [c for c in ours if len([n for n in back[c] if isinstance(MAP[n], str)]) > 1]
    split = [n for n in names if isinstance(MAP[n], list)]

    L = ["# Our food categories vs USDA WWEIA", "",
         "**WWEIA** (What We Eat in America, 2021–2023) is USDA's category system for every food and drink people consume: "
         f"**{len(names)} categories**. Ours (v2): **115 categories in 21 groups**. Built by `tools/categories/compare_wweia.py`. "
         "Source: [USDA ARS WWEIA Food Categories](https://www.ars.usda.gov/Services/docs.htm?docid=23429).", "",
         "## In numbers", "",
         "| | |", "|---|---|",
         f"| Ours ↔ WWEIA, same category (1 to 1) | {len(one_to_one)} |",
         f"| Ours combines several WWEIA categories | {len(merged)} ours ← {sum(len(back[c]) for c in merged)} WWEIA |",
         f"| WWEIA category spread over several of ours | {len(split)} |",
         f"| Ours only, not in WWEIA | {len(ours_only)} |",
         "| WWEIA only (nothing of ours fits) | 0 (only *Human milk*, not a product) |", "",
         "## Ours only (not in WWEIA)", "",
         "WWEIA classifies food **as eaten**. It has no grocery ingredients, and it sorts fruit and vegetables by kind, not by fresh or canned.", "",
         ", ".join(ours_only), "",
         "## Where ours is broader (several WWEIA categories → one of ours)", "",
         "| Ours | WWEIA categories inside it |", "|---|---|"]
    for c in merged:
        L.append(f"| {c} | {' · '.join(back[c])} |")
    L += ["", "## Where WWEIA is broader (one WWEIA category → several of ours)", "", "| WWEIA | Ours |", "|---|---|"]
    for n in split:
        L.append(f"| {n} | {' · '.join(MAP[n])} |")
    L += ["", "## Full mapping by our group", "", "| Group | Our category | WWEIA categories |", "|---|---|---|"]
    for g, cats in OURS.items():
        for c in cats:
            L.append(f"| {g} | {c} | {' · '.join(back[c]) or '—'} |")
    OUT_MD.write_text("\n".join(L) + "\n")
    print(f"WWEIA {len(names)} | ours 115 | 1:1 {len(one_to_one)} | merged {len(merged)} ours <- {sum(len(back[c]) for c in merged)} WWEIA | split {len(split)} | ours-only {len(ours_only)}")
    print("ours only:", ours_only)
    print("merged:", [(c, len(back[c])) for c in merged])
    print("split:", split)
    print("written", OUT_MD)


if __name__ == "__main__":
    sys.exit(main())
