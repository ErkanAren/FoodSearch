# Food categories

**183 categories = 172 USDA WWEIA (2021–2023, unchanged) + 11 additions (codes X..).** Maximum allowed: 255.

- **Base:** USDA *What We Eat in America* food categories, the category system for every food and drink people consume. Codes and names are USDA's; none merged (owner decision 2026-11-16). Source: [USDA ARS](https://www.ars.usda.gov/Services/docs.htm?docid=23429).
- **Additions:** grocery and other items WWEIA lacks. Where a WWEIA name also covers one, that WWEIA category is narrowed (see notes).
- **One category per product.** If nothing fits: 9999 *Not included in a food category*.
- **Tags, not categories:** processing state (fresh / frozen / canned / dried) and sugar-free / diet.
- **Display names:** WWEIA uses US wording (frankfurter, grits, saltines); the app can show friendlier names while keeping the code.
- Built by `tools/categories/build_list.py`; comparison with our earlier list in `CATEGORIES-vs-WWEIA.md`.

| Group | Sub-group | Code | Category | Note |
|---|---|---|---|---|
| **Milk & dairy** (15) | Milk | 1002 | Milk, whole |  |
|  | Milk | 1004 | Milk, reduced fat |  |
|  | Milk | 1006 | Milk, lowfat |  |
|  | Milk | 1008 | Milk, nonfat |  |
|  | Flavored milk | 1202 | Flavored milk, whole |  |
|  | Flavored milk | 1204 | Flavored milk, reduced fat |  |
|  | Flavored milk | 1206 | Flavored milk, lowfat |  |
|  | Flavored milk | 1208 | Flavored milk, nonfat |  |
|  | Dairy drinks | 1402 | Milk shakes and other dairy drinks |  |
|  | Cheese | 1602 | Cheese |  |
|  | Cheese | 1604 | Cottage/ricotta cheese |  |
|  | Yogurt | 1820 | Yogurt, regular |  |
|  | Yogurt | 1822 | Yogurt, Greek |  |
|  | Plant-based alternatives | 1902 | Plant-based milk |  |
|  | Plant-based alternatives | 1904 | Plant-based yogurt |  |
| **Protein foods** (19) | Meats | 2002 | Beef, excludes ground |  |
|  | Meats | 2004 | Ground beef |  |
|  | Meats | 2006 | Pork |  |
|  | Meats | 2008 | Lamb, goat, game |  |
|  | Meats | 2010 | Liver and organ meats |  |
|  | Poultry | 2202 | Chicken, whole pieces |  |
|  | Poultry | 2204 | Chicken patties, nuggets and tenders |  |
|  | Poultry | 2206 | Turkey, duck, other poultry |  |
|  | Seafood | 2402 | Fish |  |
|  | Seafood | 2404 | Shellfish |  |
|  | Eggs | 2502 | Eggs and omelets |  |
|  | Cured meats | 2602 | Cold cuts and cured meats |  |
|  | Cured meats | 2604 | Bacon |  |
|  | Cured meats | 2606 | Frankfurters |  |
|  | Cured meats | 2608 | Sausages |  |
|  | Plant-based protein | 2802 | Beans, peas, legumes |  |
|  | Plant-based protein | 2804 | Nuts and seeds |  |
|  | Plant-based protein | 2806 | Soy and meat-alternative products |  |
|  | Plant-based protein | X07 | Nut and seed butters | New: narrows 2804 Nuts and seeds |
| **Mixed dishes** (29) | Meat, poultry, seafood | 3002 | Meat mixed dishes |  |
|  | Meat, poultry, seafood | 3004 | Poultry mixed dishes |  |
|  | Meat, poultry, seafood | 3006 | Seafood mixed dishes |  |
|  | Bean & vegetable | 3102 | Bean, pea, legume dishes |  |
|  | Bean & vegetable | 3104 | Vegetable dishes |  |
|  | Grain-based | 3202 | Rice mixed dishes |  |
|  | Grain-based | 3204 | Pasta mixed dishes, excludes macaroni and cheese |  |
|  | Grain-based | 3206 | Macaroni and cheese |  |
|  | Grain-based | 3208 | Turnovers and other grain-based items |  |
|  | Asian | 3402 | Fried rice and lo/chow mein |  |
|  | Asian | 3404 | Stir-fry and soy-based sauce mixtures |  |
|  | Asian | 3406 | Egg rolls, dumplings, sushi |  |
|  | Mexican | 3502 | Burritos and tacos |  |
|  | Mexican | 3504 | Nachos |  |
|  | Mexican | 3506 | Other Mexican mixed dishes |  |
|  | Pizza | 3602 | Pizza |  |
|  | Sandwiches | 3702 | Burgers |  |
|  | Sandwiches | 3703 | Frankfurter sandwiches |  |
|  | Sandwiches | 3704 | Chicken fillet sandwiches |  |
|  | Sandwiches | 3706 | Egg/breakfast sandwiches |  |
|  | Sandwiches | 3720 | Cheese sandwiches |  |
|  | Sandwiches | 3722 | Peanut butter and jelly sandwiches |  |
|  | Sandwiches | 3730 | Seafood sandwiches |  |
|  | Sandwiches | 3740 | Deli and cured meat sandwiches |  |
|  | Sandwiches | 3742 | Meat and BBQ sandwiches |  |
|  | Sandwiches | 3744 | Vegetable sandwiches/burgers |  |
|  | Soups | 3804 | Soups, broth-based |  |
|  | Soups | 3806 | Soups, cream-based |  |
|  | Soups | 3808 | Ramen and Asian broth-based soups |  |
| **Grains** (13) | Cooked grains | 4002 | Rice |  |
|  | Cooked grains | 4004 | Pasta, noodles, cooked grains |  |
|  | Breads, rolls, tortillas | 4202 | Yeast breads |  |
|  | Breads, rolls, tortillas | 4204 | Rolls and buns |  |
|  | Breads, rolls, tortillas | 4206 | Bagels and English muffins |  |
|  | Breads, rolls, tortillas | 4208 | Tortillas |  |
|  | Quick breads | 4402 | Biscuits, muffins, quick breads |  |
|  | Quick breads | 4404 | Pancakes, waffles, French toast |  |
|  | Ready-to-eat cereals | 4602 | Ready-to-eat cereal, higher sugar (>21.2g/100g) |  |
|  | Ready-to-eat cereals | 4604 | Ready-to-eat cereal, lower sugar (=<21.2g/100g) |  |
|  | Cooked cereals | 4802 | Oatmeal |  |
|  | Cooked cereals | 4804 | Grits and other cooked cereals |  |
|  | Flour & baking | X01 | Flour | New: grocery ingredient, not in WWEIA |
| **Snacks & sweets** (16) | Savory snacks | 5002 | Potato chips |  |
|  | Savory snacks | 5004 | Tortilla, corn, other chips |  |
|  | Savory snacks | 5006 | Popcorn |  |
|  | Savory snacks | 5008 | Pretzels/snack mix |  |
|  | Crackers | 5202 | Crackers, excludes saltines |  |
|  | Crackers | 5204 | Saltine crackers |  |
|  | Bars | 5402 | Cereal bars |  |
|  | Bars | 5404 | Nutrition bars |  |
|  | Sweet bakery | 5502 | Cakes and pies |  |
|  | Sweet bakery | 5504 | Cookies and brownies |  |
|  | Sweet bakery | 5506 | Doughnuts, sweet rolls, pastries |  |
|  | Candy | 5702 | Candy containing chocolate |  |
|  | Candy | 5704 | Candy not containing chocolate |  |
|  | Other desserts | 5802 | Ice cream and frozen dairy desserts |  |
|  | Other desserts | 5804 | Pudding |  |
|  | Other desserts | 5806 | Gelatins, ices, sorbets |  |
| **Fruit** (13) | Fruits | 6002 | Apples |  |
|  | Fruits | 6004 | Bananas |  |
|  | Fruits | 6006 | Grapes |  |
|  | Fruits | 6008 | Peaches and nectarines |  |
|  | Fruits | 6009 | Strawberries |  |
|  | Fruits | 6011 | Blueberries and other berries |  |
|  | Fruits | 6012 | Citrus fruits |  |
|  | Fruits | 6014 | Melons |  |
|  | Fruits | 6016 | Dried fruits |  |
|  | Fruits | 6018 | Other fruits and fruit salads |  |
|  | Fruits | 6020 | Pears |  |
|  | Fruits | 6022 | Pineapple |  |
|  | Fruits | 6024 | Mango and papaya |  |
| **Vegetables** (19) | Vegetables | 6402 | Tomatoes |  |
|  | Vegetables | 6404 | Carrots |  |
|  | Vegetables | 6406 | Other red and orange vegetables |  |
|  | Vegetables | 6407 | Broccoli |  |
|  | Vegetables | 6409 | Spinach |  |
|  | Vegetables | 6410 | Lettuce and lettuce salads |  |
|  | Vegetables | 6411 | Other dark green vegetables |  |
|  | Vegetables | 6412 | String beans |  |
|  | Vegetables | 6413 | Cabbage |  |
|  | Vegetables | 6414 | Onions |  |
|  | Vegetables | 6416 | Corn |  |
|  | Vegetables | 6418 | Other starchy vegetables |  |
|  | Vegetables | 6420 | Other vegetables and combinations |  |
|  | Vegetables | 6430 | Fried vegetables |  |
|  | Vegetables | 6432 | Coleslaw, non-lettuce salads |  |
|  | Vegetables | 6489 | Vegetables on a sandwich |  |
|  | White potatoes | 6802 | White potatoes, baked or boiled |  |
|  | White potatoes | 6804 | French fries and other fried white potatoes |  |
|  | White potatoes | 6806 | Mashed potatoes and white potato mixtures |  |
| **Beverages** (16) | 100% juice | 7002 | Citrus juice |  |
|  | 100% juice | 7004 | Apple juice |  |
|  | 100% juice | 7006 | Other fruit juice |  |
|  | 100% juice | 7008 | Vegetable juice |  |
|  | Diet drinks | 7102 | Diet soft drinks |  |
|  | Diet drinks | 7104 | Diet sport and energy drinks |  |
|  | Diet drinks | 7106 | Other diet drinks |  |
|  | Sweetened drinks | 7202 | Soft drinks |  |
|  | Sweetened drinks | 7204 | Fruit drinks |  |
|  | Sweetened drinks | 7206 | Sport and energy drinks |  |
|  | Sweetened drinks | 7208 | Nutritional beverages |  |
|  | Sweetened drinks | 7220 | Smoothies and grain drinks |  |
|  | Coffee & tea | 7302 | Coffee |  |
|  | Coffee & tea | 7304 | Tea |  |
|  | Powders & mixes | X09 | Hot chocolate and drink powders | New: not in WWEIA |
|  | Coffee & tea | X10 | Iced tea | New: narrows 7304 Tea |
| **Alcoholic beverages** (3) | Alcohol | 7502 | Beer |  |
|  | Alcohol | 7504 | Wine |  |
|  | Alcohol | 7506 | Liquor and cocktails |  |
| **Water** (4) | Plain water | 7702 | Tap water |  |
|  | Plain water | 7704 | Bottled water |  |
|  | Flavored/enhanced water | 7802 | Flavored or carbonated water |  |
|  | Flavored/enhanced water | 7804 | Enhanced water |  |
| **Fats & oils** (7) | Fats & oils | 8002 | Butter and animal fats |  |
|  | Fats & oils | 8004 | Margarine |  |
|  | Fats & oils | 8006 | Cream cheese, sour cream, whipped cream |  |
|  | Fats & oils | 8008 | Cream and cream substitutes |  |
|  | Fats & oils | 8010 | Mayonnaise |  |
|  | Fats & oils | 8012 | Salad dressings and vegetable oils |  |
|  | Fats & oils | X06 | Cooking oils | New: narrows 8012 Salad dressings and vegetable oils to dressings |
| **Condiments & sauces** (7) | Condiments & sauces | 8402 | Tomato-based condiments |  |
|  | Condiments & sauces | 8404 | Soy-based condiments |  |
|  | Condiments & sauces | 8406 | Mustard and other condiments |  |
|  | Condiments & sauces | 8408 | Olives, pickles, pickled vegetables |  |
|  | Condiments & sauces | 8410 | Pasta sauces, tomato-based |  |
|  | Condiments & sauces | 8412 | Dips, gravies, other sauces |  |
|  | Condiments & sauces | X05 | Vinegar | New: narrows 8406 Mustard and other condiments |
| **Sugars** (4) | Sugars | 8802 | Sugars and honey |  |
|  | Sugars | 8804 | Sugar substitutes |  |
|  | Sugars | 8806 | Jams, syrups, toppings |  |
|  | Sugars | X08 | Chocolate and sweet spreads | New: narrows 8806 Jams, syrups, toppings |
| **Cooking & baking** (3) | Cooking & baking | X02 | Baking ingredients and mixes | New: baking powder, yeast, cake/pancake mixes, decorations |
|  | Cooking & baking | X03 | Salt, herbs and spices | New: not in WWEIA |
|  | Cooking & baking | X04 | Stocks and bouillon | New: WWEIA 8412 keeps gravies |
| **Infant formula & baby food** (12) | Baby food | 9002 | Baby food: cereals |  |
|  | Baby food | 9004 | Baby food: fruit |  |
|  | Baby food | 9006 | Baby food: vegetables |  |
|  | Baby food | 9007 | Baby food: mixtures |  |
|  | Baby food | 9008 | Baby food: meat and dinners |  |
|  | Baby food | 9010 | Baby food: yogurt |  |
|  | Baby food | 9012 | Baby food: snacks and sweets |  |
|  | Baby drinks | 9202 | Baby juice |  |
|  | Baby drinks | 9204 | Baby water |  |
|  | Infant formula | 9402 | Formula, ready-to-feed |  |
|  | Infant formula | 9404 | Formula, prepared from powder |  |
|  | Human milk | 9602 | Human milk |  |
| **Other** (3) | Protein & nutritional powders | 9802 | Protein and nutritional powders |  |
|  | Not in a category | 9999 | Not included in a food category |  |
|  | Supplements | X11 | Vitamins and supplements | New: WWEIA 9802 keeps protein and nutritional powders |
