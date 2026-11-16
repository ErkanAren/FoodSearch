# Our food categories vs USDA WWEIA

**WWEIA** (What We Eat in America, 2021–2023) is USDA's category system for every food and drink people consume: **172 categories**. Ours (v2): **115 categories in 21 groups**. Built by `tools/categories/compare_wweia.py`. Source: [USDA ARS WWEIA Food Categories](https://www.ars.usda.gov/Services/docs.htm?docid=23429).

## In numbers

| | |
|---|---|
| Ours ↔ WWEIA, same category (1 to 1) | 44 |
| Ours combines several WWEIA categories | 27 ours ← 101 WWEIA |
| WWEIA category spread over several of ours | 19 |
| Ours only, not in WWEIA | 10 |
| WWEIA only (nothing of ours fits) | 0 (only *Human milk*, not a product) |

## Ours only (not in WWEIA)

WWEIA classifies food **as eaten**. It has no grocery ingredients, and it sorts fruit and vegetables by kind, not by fresh or canned.

Canned & frozen fruit, Canned & frozen vegetables, Flour, Stews & curries, Chocolate & sweet spreads, Salt, herbs & spices, Vinegar, Baking ingredients & mixes, Hot chocolate & drink powders, Vitamins & supplements

## Where ours is broader (several WWEIA categories → one of ours)

| Ours | WWEIA categories inside it |
|---|---|
| Milk | Milk, whole · Milk, reduced fat · Milk, lowfat · Milk, nonfat |
| Flavoured milk & milkshakes | Flavored milk, whole · Flavored milk, reduced fat · Flavored milk, lowfat · Flavored milk, nonfat · Milk shakes and other dairy drinks |
| Yogurt & fermented milk | Yogurt, regular · Yogurt, Greek |
| Red meat | Beef, excludes ground · Ground beef · Pork · Lamb, goat, game · Liver and organ meats |
| Poultry | Chicken, whole pieces · Turkey, duck, other poultry |
| Sausages & hot dogs | Frankfurters · Sausages |
| Fresh fruit | Apples · Bananas · Grapes · Peaches and nectarines · Strawberries · Blueberries and other berries · Citrus fruits · Melons · Other fruits and fruit salads · Pears · Pineapple · Mango and papaya |
| Fresh vegetables | Tomatoes · Carrots · Other red and orange vegetables · Broccoli · Spinach · Other dark green vegetables · String beans · Cabbage · Onions · Corn · Other starchy vegetables · Other vegetables and combinations · Vegetables on a sandwich |
| Potatoes | White potatoes, baked or boiled · Mashed potatoes and white potato mixtures |
| Rolls, buns & bagels | Rolls and buns · Bagels and English muffins |
| Crackers & crispbreads | Crackers, excludes saltines · Saltine crackers |
| Breakfast cereals | Ready-to-eat cereal, higher sugar (>21.2g/100g) · Ready-to-eat cereal, lower sugar (=<21.2g/100g) |
| Oats & porridge | Oatmeal · Grits and other cooked cereals |
| Chips & crisps | Potato chips · Tortilla, corn, other chips |
| Sandwiches | Chicken fillet sandwiches · Egg/breakfast sandwiches · Cheese sandwiches · Peanut butter and jelly sandwiches · Seafood sandwiches · Deli and cured meat sandwiches · Meat and BBQ sandwiches · Vegetable sandwiches/burgers |
| Wraps, burritos & tacos | Burritos and tacos · Nachos · Other Mexican mixed dishes |
| Pasta dishes | Pasta mixed dishes, excludes macaroni and cheese · Macaroni and cheese |
| Soups | Soups, broth-based · Soups, cream-based · Ramen and Asian broth-based soups |
| Meat & poultry dishes | Meat mixed dishes · Poultry mixed dishes · Stir-fry and soy-based sauce mixtures |
| Vegetable & legume dishes | Bean, pea, legume dishes · Vegetable dishes · Stir-fry and soy-based sauce mixtures · Fried vegetables |
| Water | Tap water · Bottled water |
| Sparkling & flavoured water | Flavored or carbonated water · Enhanced water |
| Diet & zero soft drinks | Diet soft drinks · Other diet drinks |
| Juices (100%) | Citrus juice · Apple juice · Other fruit juice · Vegetable juice |
| Infant formula | Formula, ready-to-feed · Formula, prepared from powder |
| Baby food (purees & meals) | Baby food: fruit · Baby food: vegetables · Baby food: mixtures · Baby food: meat and dinners · Baby food: yogurt |
| Baby snacks, cereals & drinks | Baby food: cereals · Baby food: snacks and sweets · Baby juice · Baby water |

## Where WWEIA is broader (one WWEIA category → several of ours)

| WWEIA | Ours |
|---|---|
| Fish | Fish · Canned fish |
| Eggs and omelets | Eggs · Breakfast dishes |
| Nuts and seeds | Nuts & seeds · Nut & seed butters |
| Fried rice and lo/chow mein | Rice dishes · Noodle dishes |
| Stir-fry and soy-based sauce mixtures | Meat & poultry dishes · Vegetable & legume dishes |
| Vegetable sandwiches/burgers | Sandwiches · Burgers |
| Ramen and Asian broth-based soups | Soups · Noodle dishes |
| Pasta, noodles, cooked grains | Pasta · Noodles · Couscous, quinoa & other grains |
| Biscuits, muffins, quick breads | Cakes & pies · Bread |
| Gelatins, ices, sorbets | Puddings & jelly desserts · Ice cream & frozen desserts |
| Lettuce and lettuce salads | Salad greens · Salads |
| Diet sport and energy drinks | Energy drinks · Sports drinks |
| Sport and energy drinks | Energy drinks · Sports drinks |
| Tea | Tea · Iced tea |
| Liquor and cocktails | Spirits & liqueurs · Cider, seltzers & mixed drinks |
| Butter and animal fats | Butter · Margarine & cooking fats |
| Cream cheese, sour cream, whipped cream | Fresh cheese (cottage, ricotta, cream cheese) · Cream & sour cream |
| Salad dressings and vegetable oils | Salad dressings · Vegetable oils · Olive oil |
| Dips, gravies, other sauces | Dips & savoury spreads · Stocks, bouillon & gravy · Hot sauces |

## Full mapping by our group

| Group | Our category | WWEIA categories |
|---|---|---|
| Dairy & eggs | Milk | Milk, whole · Milk, reduced fat · Milk, lowfat · Milk, nonfat |
| Dairy & eggs | Flavoured milk & milkshakes | Flavored milk, whole · Flavored milk, reduced fat · Flavored milk, lowfat · Flavored milk, nonfat · Milk shakes and other dairy drinks |
| Dairy & eggs | Yogurt & fermented milk | Yogurt, regular · Yogurt, Greek |
| Dairy & eggs | Cheese | Cheese |
| Dairy & eggs | Fresh cheese (cottage, ricotta, cream cheese) | Cottage/ricotta cheese · Cream cheese, sour cream, whipped cream |
| Dairy & eggs | Cream & sour cream | Cream cheese, sour cream, whipped cream · Cream and cream substitutes |
| Dairy & eggs | Butter | Butter and animal fats |
| Dairy & eggs | Eggs | Eggs and omelets |
| Plant-based | Plant-based milk | Plant-based milk |
| Plant-based | Plant-based yogurt & desserts | Plant-based yogurt |
| Plant-based | Tofu & meat alternatives | Soy and meat-alternative products |
| Meat & poultry | Red meat | Beef, excludes ground · Ground beef · Pork · Lamb, goat, game · Liver and organ meats |
| Meat & poultry | Poultry | Chicken, whole pieces · Turkey, duck, other poultry |
| Meat & poultry | Breaded chicken & nuggets | Chicken patties, nuggets and tenders |
| Meat & poultry | Cold cuts & cured meats | Cold cuts and cured meats |
| Meat & poultry | Bacon | Bacon |
| Meat & poultry | Sausages & hot dogs | Frankfurters · Sausages |
| Fish & seafood | Fish | Fish |
| Fish & seafood | Canned fish | Fish |
| Fish & seafood | Shellfish | Shellfish |
| Fruit | Fresh fruit | Apples · Bananas · Grapes · Peaches and nectarines · Strawberries · Blueberries and other berries · Citrus fruits · Melons · Other fruits and fruit salads · Pears · Pineapple · Mango and papaya |
| Fruit | Dried fruit | Dried fruits |
| Fruit | Canned & frozen fruit | — |
| Vegetables & legumes | Fresh vegetables | Tomatoes · Carrots · Other red and orange vegetables · Broccoli · Spinach · Other dark green vegetables · String beans · Cabbage · Onions · Corn · Other starchy vegetables · Other vegetables and combinations · Vegetables on a sandwich |
| Vegetables & legumes | Salad greens | Lettuce and lettuce salads |
| Vegetables & legumes | Canned & frozen vegetables | — |
| Vegetables & legumes | Potatoes | White potatoes, baked or boiled · Mashed potatoes and white potato mixtures |
| Vegetables & legumes | Fries & potato products | French fries and other fried white potatoes |
| Vegetables & legumes | Legumes | Beans, peas, legumes |
| Vegetables & legumes | Olives & pickles | Olives, pickles, pickled vegetables |
| Nuts & seeds | Nuts & seeds | Nuts and seeds |
| Nuts & seeds | Nut & seed butters | Nuts and seeds |
| Bread & bakery | Bread | Yeast breads · Biscuits, muffins, quick breads |
| Bread & bakery | Rolls, buns & bagels | Rolls and buns · Bagels and English muffins |
| Bread & bakery | Flatbreads & tortillas | Tortillas |
| Bread & bakery | Crackers & crispbreads | Crackers, excludes saltines · Saltine crackers |
| Grains & cereals | Rice | Rice |
| Grains & cereals | Pasta | Pasta, noodles, cooked grains |
| Grains & cereals | Noodles | Pasta, noodles, cooked grains |
| Grains & cereals | Couscous, quinoa & other grains | Pasta, noodles, cooked grains |
| Grains & cereals | Flour | — |
| Grains & cereals | Breakfast cereals | Ready-to-eat cereal, higher sugar (>21.2g/100g) · Ready-to-eat cereal, lower sugar (=<21.2g/100g) |
| Grains & cereals | Oats & porridge | Oatmeal · Grits and other cooked cereals |
| Sweets & desserts | Cakes & pies | Biscuits, muffins, quick breads · Cakes and pies |
| Sweets & desserts | Biscuits & cookies | Cookies and brownies |
| Sweets & desserts | Doughnuts & sweet pastries | Doughnuts, sweet rolls, pastries |
| Sweets & desserts | Chocolate | Candy containing chocolate |
| Sweets & desserts | Candy & gum | Candy not containing chocolate |
| Sweets & desserts | Ice cream & frozen desserts | Ice cream and frozen dairy desserts · Gelatins, ices, sorbets |
| Sweets & desserts | Puddings & jelly desserts | Pudding · Gelatins, ices, sorbets |
| Sweets & desserts | Cereal & granola bars | Cereal bars |
| Salty snacks | Chips & crisps | Potato chips · Tortilla, corn, other chips |
| Salty snacks | Popcorn | Popcorn |
| Salty snacks | Pretzels & snack mixes | Pretzels/snack mix |
| Meals & dishes | Burgers | Burgers · Vegetable sandwiches/burgers |
| Meals & dishes | Sandwiches | Chicken fillet sandwiches · Egg/breakfast sandwiches · Cheese sandwiches · Peanut butter and jelly sandwiches · Seafood sandwiches · Deli and cured meat sandwiches · Meat and BBQ sandwiches · Vegetable sandwiches/burgers |
| Meals & dishes | Hot dogs | Frankfurter sandwiches |
| Meals & dishes | Wraps, burritos & tacos | Burritos and tacos · Nachos · Other Mexican mixed dishes |
| Meals & dishes | Pizza | Pizza |
| Meals & dishes | Pasta dishes | Pasta mixed dishes, excludes macaroni and cheese · Macaroni and cheese |
| Meals & dishes | Rice dishes | Rice mixed dishes · Fried rice and lo/chow mein |
| Meals & dishes | Noodle dishes | Fried rice and lo/chow mein · Ramen and Asian broth-based soups |
| Meals & dishes | Sushi & dumplings | Egg rolls, dumplings, sushi |
| Meals & dishes | Soups | Soups, broth-based · Soups, cream-based · Ramen and Asian broth-based soups |
| Meals & dishes | Stews & curries | — |
| Meals & dishes | Salads | Lettuce and lettuce salads · Coleslaw, non-lettuce salads |
| Meals & dishes | Meat & poultry dishes | Meat mixed dishes · Poultry mixed dishes · Stir-fry and soy-based sauce mixtures |
| Meals & dishes | Fish & seafood dishes | Seafood mixed dishes |
| Meals & dishes | Vegetable & legume dishes | Bean, pea, legume dishes · Vegetable dishes · Stir-fry and soy-based sauce mixtures · Fried vegetables |
| Meals & dishes | Savoury pies & pastries | Turnovers and other grain-based items |
| Meals & dishes | Breakfast dishes | Eggs and omelets · Pancakes, waffles, French toast |
| Sauces & condiments | Ketchup & tomato condiments | Tomato-based condiments |
| Sauces & condiments | Mustard & other condiments | Mustard and other condiments |
| Sauces & condiments | Mayonnaise | Mayonnaise |
| Sauces & condiments | Salad dressings | Salad dressings and vegetable oils |
| Sauces & condiments | Pasta & cooking sauces | Pasta sauces, tomato-based |
| Sauces & condiments | Soy & Asian sauces | Soy-based condiments |
| Sauces & condiments | Hot sauces | Dips, gravies, other sauces |
| Sauces & condiments | Dips & savoury spreads | Dips, gravies, other sauces |
| Sugar & sweet spreads | Sugar & honey | Sugars and honey |
| Sugar & sweet spreads | Sweeteners | Sugar substitutes |
| Sugar & sweet spreads | Jams & syrups | Jams, syrups, toppings |
| Sugar & sweet spreads | Chocolate & sweet spreads | — |
| Oils & fats | Olive oil | Salad dressings and vegetable oils |
| Oils & fats | Vegetable oils | Salad dressings and vegetable oils |
| Oils & fats | Margarine & cooking fats | Butter and animal fats · Margarine |
| Cooking & baking | Salt, herbs & spices | — |
| Cooking & baking | Stocks, bouillon & gravy | Dips, gravies, other sauces |
| Cooking & baking | Vinegar | — |
| Cooking & baking | Baking ingredients & mixes | — |
| Drinks | Water | Tap water · Bottled water |
| Drinks | Sparkling & flavoured water | Flavored or carbonated water · Enhanced water |
| Drinks | Soft drinks | Soft drinks |
| Drinks | Diet & zero soft drinks | Diet soft drinks · Other diet drinks |
| Drinks | Juices (100%) | Citrus juice · Apple juice · Other fruit juice · Vegetable juice |
| Drinks | Fruit drinks & nectars | Fruit drinks |
| Drinks | Smoothies | Smoothies and grain drinks |
| Drinks | Energy drinks | Diet sport and energy drinks · Sport and energy drinks |
| Drinks | Sports drinks | Diet sport and energy drinks · Sport and energy drinks |
| Drinks | Coffee | Coffee |
| Drinks | Tea | Tea |
| Drinks | Iced tea | Tea |
| Drinks | Hot chocolate & drink powders | — |
| Alcohol | Beer | Beer |
| Alcohol | Wine | Wine |
| Alcohol | Spirits & liqueurs | Liquor and cocktails |
| Alcohol | Cider, seltzers & mixed drinks | Liquor and cocktails |
| Baby & infant | Infant formula | Formula, ready-to-feed · Formula, prepared from powder |
| Baby & infant | Baby food (purees & meals) | Baby food: fruit · Baby food: vegetables · Baby food: mixtures · Baby food: meat and dinners · Baby food: yogurt |
| Baby & infant | Baby snacks, cereals & drinks | Baby food: cereals · Baby food: snacks and sweets · Baby juice · Baby water |
| Sports & nutrition | Protein powders & shakes | Protein and nutritional powders |
| Sports & nutrition | Protein & nutrition bars | Nutrition bars |
| Sports & nutrition | Nutrition drinks & meal replacements | Nutritional beverages |
| Sports & nutrition | Vitamins & supplements | — |
| Other | Other | Not included in a food category |
