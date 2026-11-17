# Category icons (draft)

**159 item icons for 183 categories** (147 core + 12 extra) + **16 group icons**.

- **Core:** make these. **Extra:** hard-to-draw catch-alls; if not made, the category shows its **group icon**. Making only core + group icons = **163 icons**.
- **Shared icons (14):** categories that look the same and differ only by a property (milk fat, sugar, diet) share one icon, optionally with a small **badge**.
- **Never shown:** 6489, 7702, 9602 (survey-only) and 9999 use the generic food icon.
- **Style:** neutral, international versions of each food. No brands, no country-specific packaging, no text except badges.
- Data: `tools/categories/icons.py` → `python3 -I tools/categories/build_icons.py` → this file + `tools/categories/icons.json`.

## Item icons

| Icon | What to draw | Tier | Categories |
|---|---|---|---|
| `milk` | glass of milk next to a milk carton | core | 1002 Milk, whole, 1004 Milk, reduced fat, 1006 Milk, lowfat, 1008 Milk, nonfat |
| `flavoured_milk` | brown chocolate-milk carton with a straw | core | 1202 Flavored milk, whole, 1204 Flavored milk, reduced fat, 1206 Flavored milk, lowfat, 1208 Flavored milk, nonfat |
| `milkshake` | tall milkshake glass with whipped cream and a straw | core | 1402 Milk shakes and other dairy drinks |
| `cheese` | cheese wedge with holes and a slice | core | 1602 Cheese |
| `cottage_cheese` | bowl of white curd cheese (cottage / ricotta) | core | 1604 Cottage/ricotta cheese |
| `yogurt` | yogurt pot with a spoon | core | 1820 Yogurt, regular, 1822 Yogurt, Greek, 1904 Plant-based yogurt |
| `plant_milk` | milk carton with a green leaf / oat sprig | core | 1902 Plant-based milk |
| `beef` | raw beef steak | core | 2002 Beef, excludes ground |
| `minced_meat` | pile of minced meat / raw patty | core | 2004 Ground beef |
| `pork` | pork chop | core | 2006 Pork |
| `lamb` | lamb chops with bone | core | 2008 Lamb, goat, game |
| `liver` | slice of liver | extra | 2010 Liver and organ meats |
| `chicken` | roast chicken drumstick | core | 2202 Chicken, whole pieces |
| `nuggets` | chicken nuggets with a small dip | core | 2204 Chicken patties, nuggets and tenders |
| `turkey` | roast turkey leg / whole small roast bird | core | 2206 Turkey, duck, other poultry |
| `fish` | whole fish | core | 2402 Fish |
| `shrimp` | shrimp / prawn | core | 2404 Shellfish |
| `egg` | fried egg and a whole egg | core | 2502 Eggs and omelets |
| `cold_cuts` | ham and salami slices on a board | core | 2602 Cold cuts and cured meats |
| `bacon` | bacon strips | core | 2604 Bacon |
| `frankfurter` | two hot dog sausages, no bun | core | 2606 Frankfurters |
| `sausage` | grilled sausage links | core | 2608 Sausages |
| `legumes` | bowl of beans, lentils and chickpeas | core | 2802 Beans, peas, legumes |
| `nuts` | almond, walnut and peanut | core | 2804 Nuts and seeds |
| `tofu` | tofu block with a green leaf | core | 2806 Soy and meat-alternative products |
| `nut_butter` | jar of nut butter with a knife | core | X07 Nut and seed butters |
| `meat_stew` | bowl of meat stew with chunks | core | 3002 Meat mixed dishes |
| `chicken_dish` | plate with chicken pieces and vegetables | extra | 3004 Poultry mixed dishes |
| `seafood_dish` | plate with fish cakes | extra | 3006 Seafood mixed dishes |
| `bean_dish` | bowl of lentil curry / bean stew with rice | extra | 3102 Bean, pea, legume dishes |
| `veg_dish` | vegetable bake / stuffed pepper | extra | 3104 Vegetable dishes |
| `rice_dish` | pan of mixed rice (paella-style) | core | 3202 Rice mixed dishes |
| `pasta_dish` | plate of spaghetti with tomato sauce | core | 3204 Pasta mixed dishes, excludes macaroni and cheese |
| `mac_cheese` | bowl of macaroni and cheese | core | 3206 Macaroni and cheese |
| `savoury_pastry` | savoury turnover / quiche slice | core | 3208 Turnovers and other grain-based items |
| `noodle_box` | noodle box with chopsticks (fried noodles / fried rice) | core | 3402 Fried rice and lo/chow mein |
| `stir_fry` | wok with chicken and broccoli | core | 3404 Stir-fry and soy-based sauce mixtures |
| `sushi` | sushi roll and a dumpling | core | 3406 Egg rolls, dumplings, sushi |
| `taco` | taco and a burrito | core | 3502 Burritos and tacos |
| `nachos` | nachos with melted cheese | core | 3504 Nachos |
| `quesadilla` | quesadilla wedges | extra | 3506 Other Mexican mixed dishes |
| `pizza` | pizza slice | core | 3602 Pizza |
| `burger` | beef burger | core | 3702 Burgers |
| `hot_dog` | hot dog in a bun | core | 3703 Frankfurter sandwiches |
| `chicken_sandwich` | crispy chicken fillet sandwich | core | 3704 Chicken fillet sandwiches |
| `breakfast_sandwich` | muffin sandwich with egg | core | 3706 Egg/breakfast sandwiches |
| `grilled_cheese` | toasted sandwich with melted cheese | core | 3720 Cheese sandwiches |
| `pbj_sandwich` | sandwich with peanut butter and jam | core | 3722 Peanut butter and jelly sandwiches |
| `fish_sandwich` | fish fillet sandwich | extra | 3730 Seafood sandwiches |
| `deli_sandwich` | sub / club sandwich with ham and lettuce | core | 3740 Deli and cured meat sandwiches |
| `meat_sandwich` | pulled meat / gyros-style wrap sandwich | extra | 3742 Meat and BBQ sandwiches |
| `veggie_burger` | burger with a green patty and a leaf | core | 3744 Vegetable sandwiches/burgers |
| `soup` | bowl of clear vegetable soup | core | 3804 Soups, broth-based |
| `cream_soup` | bowl of creamy soup | extra | 3806 Soups, cream-based |
| `ramen` | ramen bowl with chopsticks and half egg | core | 3808 Ramen and Asian broth-based soups |
| `rice` | bowl of rice | core | 4002 Rice |
| `pasta` | dry pasta shapes (penne, spaghetti bundle) | core | 4004 Pasta, noodles, cooked grains |
| `bread` | sliced bread loaf | core | 4202 Yeast breads |
| `bread_roll` | bread rolls / buns | core | 4204 Rolls and buns |
| `bagel` | bagel | core | 4206 Bagels and English muffins |
| `tortilla` | stack of tortillas / wraps | core | 4208 Tortillas |
| `muffin` | muffin | core | 4402 Biscuits, muffins, quick breads |
| `pancakes` | stack of pancakes with syrup | core | 4404 Pancakes, waffles, French toast |
| `cereal` | bowl of cereal with milk | core | 4602 Ready-to-eat cereal, higher sugar (>21.2g/100g), 4604 Ready-to-eat cereal, lower sugar (=<21.2g/100g) |
| `porridge` | bowl of porridge / oatmeal | core | 4802 Oatmeal, 4804 Grits and other cooked cereals |
| `flour` | flour bag with a wheat ear | core | X01 Flour |
| `potato_chips` | pile of potato crisps | core | 5002 Potato chips |
| `corn_chips` | tortilla chips / corn puffs | core | 5004 Tortilla, corn, other chips |
| `popcorn` | popcorn box | core | 5006 Popcorn |
| `pretzel` | pretzel | core | 5008 Pretzels/snack mix |
| `crackers` | square crackers / crispbread | core | 5202 Crackers, excludes saltines, 5204 Saltine crackers |
| `granola_bar` | granola bar with oats | core | 5402 Cereal bars |
| `protein_bar` | protein bar in a wrapper | core | 5404 Nutrition bars |
| `cake` | slice of layered cake | core | 5502 Cakes and pies |
| `cookie` | cookies / biscuits | core | 5504 Cookies and brownies |
| `pastry` | doughnut and a croissant | core | 5506 Doughnuts, sweet rolls, pastries |
| `chocolate` | chocolate bar | core | 5702 Candy containing chocolate |
| `candy` | wrapped candy, gummy bear and lollipop | core | 5704 Candy not containing chocolate |
| `ice_cream` | ice cream cone | core | 5802 Ice cream and frozen dairy desserts |
| `pudding` | pudding cup / flan | core | 5804 Pudding |
| `ice_lolly` | ice lolly / jelly dessert | core | 5806 Gelatins, ices, sorbets |
| `apple` | apple | core | 6002 Apples |
| `banana` | banana | core | 6004 Bananas |
| `grapes` | bunch of grapes | core | 6006 Grapes |
| `peach` | peach | core | 6008 Peaches and nectarines |
| `strawberry` | strawberry | core | 6009 Strawberries |
| `berries` | blueberries and raspberries | core | 6011 Blueberries and other berries |
| `citrus` | orange and lemon | core | 6012 Citrus fruits |
| `melon` | watermelon slice | core | 6014 Melons |
| `dried_fruit` | raisins, dates and dried apricots | core | 6016 Dried fruits |
| `mixed_fruit` | bowl of mixed fruit (cherries, kiwi, plum) | extra | 6018 Other fruits and fruit salads |
| `pear` | pear | core | 6020 Pears |
| `pineapple` | pineapple | core | 6022 Pineapple |
| `mango` | mango | core | 6024 Mango and papaya |
| `tomato` | tomato | core | 6402 Tomatoes |
| `carrot` | carrot | core | 6404 Carrots |
| `pepper` | red bell pepper and sweet potato | core | 6406 Other red and orange vegetables |
| `broccoli` | broccoli | core | 6407 Broccoli |
| `spinach` | spinach leaves | core | 6409 Spinach |
| `lettuce` | lettuce head / green salad | core | 6410 Lettuce and lettuce salads |
| `kale` | dark curly kale leaves | core | 6411 Other dark green vegetables |
| `green_beans` | green beans | core | 6412 String beans |
| `cabbage` | cabbage | core | 6413 Cabbage |
| `onion` | onion and spring onion | core | 6414 Onions |
| `corn` | corn cob | core | 6416 Corn |
| `peas` | pea pod | core | 6418 Other starchy vegetables |
| `mixed_veg` | cucumber, zucchini and mushroom | extra | 6420 Other vegetables and combinations |
| `onion_rings` | onion rings / fried vegetables | core | 6430 Fried vegetables |
| `coleslaw` | bowl of coleslaw / tomato-cucumber salad | core | 6432 Coleslaw, non-lettuce salads |
| `potato` | potatoes | core | 6802 White potatoes, baked or boiled |
| `fries` | French fries | core | 6804 French fries and other fried white potatoes |
| `mashed_potato` | bowl of mashed potatoes | core | 6806 Mashed potatoes and white potato mixtures |
| `orange_juice` | glass of orange juice | core | 7002 Citrus juice |
| `apple_juice` | glass of apple juice | core | 7004 Apple juice |
| `juice` | glass of red / purple fruit juice | core | 7006 Other fruit juice |
| `veg_juice` | glass of tomato juice with celery | core | 7008 Vegetable juice |
| `soft_drink` | soda can and a glass of cola | core | 7102 Diet soft drinks, 7202 Soft drinks |
| `fruit_drink` | juice box / lemonade | core | 7106 Other diet drinks, 7204 Fruit drinks |
| `energy_drink` | energy / sports drink can with a lightning bolt | core | 7104 Diet sport and energy drinks, 7206 Sport and energy drinks |
| `nutrition_shake` | ready-to-drink shake bottle | core | 7208 Nutritional beverages |
| `smoothie` | smoothie glass | core | 7220 Smoothies and grain drinks |
| `coffee` | coffee cup | core | 7302 Coffee |
| `tea` | tea cup with a tea bag | core | 7304 Tea |
| `iced_tea` | glass of iced tea with lemon | core | X10 Iced tea |
| `hot_chocolate` | mug of hot chocolate | core | X09 Hot chocolate and drink powders |
| `beer` | glass of beer | core | 7502 Beer |
| `wine` | glass of wine | core | 7504 Wine |
| `spirits` | spirit bottle and a cocktail glass | core | 7506 Liquor and cocktails |
| `water` | water bottle | core | 7704 Bottled water, 7804 Enhanced water |
| `sparkling_water` | bottle of sparkling water with bubbles | core | 7802 Flavored or carbonated water |
| `butter` | butter block | core | 8002 Butter and animal fats |
| `margarine` | tub of spread | core | 8004 Margarine |
| `sour_cream` | tub of sour cream with a dollop | core | 8006 Cream cheese, sour cream, whipped cream |
| `cream` | small jug of cream | core | 8008 Cream and cream substitutes |
| `mayonnaise` | mayonnaise jar | core | 8010 Mayonnaise |
| `dressing` | salad dressing bottle | core | 8012 Salad dressings and vegetable oils |
| `oil` | olive oil bottle | core | X06 Cooking oils |
| `ketchup` | ketchup bottle | core | 8402 Tomato-based condiments |
| `soy_sauce` | soy sauce bottle and dish | core | 8404 Soy-based condiments |
| `mustard` | mustard jar | core | 8406 Mustard and other condiments |
| `olives` | olives and a pickle | core | 8408 Olives, pickles, pickled vegetables |
| `pasta_sauce` | jar of tomato pasta sauce | core | 8410 Pasta sauces, tomato-based |
| `dip` | bowl of hummus / dip | extra | 8412 Dips, gravies, other sauces |
| `vinegar` | vinegar bottle | core | X05 Vinegar |
| `honey_sugar` | honey jar and sugar cubes | core | 8802 Sugars and honey |
| `sweetener` | sweetener tablets with a stevia leaf | core | 8804 Sugar substitutes |
| `jam` | jam jar | core | 8806 Jams, syrups, toppings |
| `choc_spread` | jar of chocolate spread | core | X08 Chocolate and sweet spreads |
| `baking` | whisk and baking-powder tin | core | X02 Baking ingredients and mixes |
| `spices` | salt and pepper shakers with a spice jar | core | X03 Salt, herbs and spices |
| `stock` | stock cube | core | X04 Stocks and bouillon |
| `baby_cereal` | baby bowl with a baby spoon | core | 9002 Baby food: cereals |
| `baby_food` | baby food pouch / jar | core | 9004 Baby food: fruit, 9006 Baby food: vegetables, 9007 Baby food: mixtures, 9008 Baby food: meat and dinners, 9010 Baby food: yogurt |
| `baby_snack` | baby puffs / teething biscuit | core | 9012 Baby food: snacks and sweets |
| `baby_drink` | baby sippy cup | core | 9202 Baby juice, 9204 Baby water |
| `formula` | formula tin with a baby bottle | core | 9402 Formula, ready-to-feed, 9404 Formula, prepared from powder |
| `protein_powder` | protein powder tub with a scoop | core | 9802 Protein and nutritional powders |
| `supplements` | pills and capsules | core | X11 Vitamins and supplements |
| `generic_food` | plate with knife and fork | core | 6489 Vegetables on a sandwich, 7702 Tap water, 9602 Human milk, 9999 Not included in a food category |

## Group icons

| Group | What to draw |
|---|---|
| Milk & dairy | milk bottle and cheese wedge |
| Protein foods | steak and an egg |
| Mixed dishes | covered dish / plate of food |
| Grains | bread loaf and wheat ear |
| Snacks & sweets | cookie and candy |
| Fruit | apple and banana |
| Vegetables | carrot and broccoli |
| Beverages | glass with a straw |
| Alcoholic beverages | beer and wine glass |
| Water | water bottle |
| Fats & oils | butter and oil bottle |
| Condiments & sauces | sauce bottle |
| Sugars | sugar cubes and honey |
| Cooking & baking | whisk and spice jar |
| Infant formula & baby food | baby bottle |
| Other | plate with knife and fork |

## Category → icon

| Group | Code | Category | Icon | Badge |
|---|---|---|---|---|
| Milk & dairy | 1002 | Milk, whole | `milk` | whole |
|  | 1004 | Milk, reduced fat | `milk` | 2% |
|  | 1006 | Milk, lowfat | `milk` | 1% |
|  | 1008 | Milk, nonfat | `milk` | skim |
|  | 1202 | Flavored milk, whole | `flavoured_milk` | whole |
|  | 1204 | Flavored milk, reduced fat | `flavoured_milk` | 2% |
|  | 1206 | Flavored milk, lowfat | `flavoured_milk` | 1% |
|  | 1208 | Flavored milk, nonfat | `flavoured_milk` | skim |
|  | 1402 | Milk shakes and other dairy drinks | `milkshake` |  |
|  | 1602 | Cheese | `cheese` |  |
|  | 1604 | Cottage/ricotta cheese | `cottage_cheese` |  |
|  | 1820 | Yogurt, regular | `yogurt` |  |
|  | 1822 | Yogurt, Greek | `yogurt` | Greek |
|  | 1902 | Plant-based milk | `plant_milk` |  |
|  | 1904 | Plant-based yogurt | `yogurt` | plant |
| Protein foods | 2002 | Beef, excludes ground | `beef` |  |
|  | 2004 | Ground beef | `minced_meat` |  |
|  | 2006 | Pork | `pork` |  |
|  | 2008 | Lamb, goat, game | `lamb` |  |
|  | 2010 | Liver and organ meats | `liver` (extra) |  |
|  | 2202 | Chicken, whole pieces | `chicken` |  |
|  | 2204 | Chicken patties, nuggets and tenders | `nuggets` |  |
|  | 2206 | Turkey, duck, other poultry | `turkey` |  |
|  | 2402 | Fish | `fish` |  |
|  | 2404 | Shellfish | `shrimp` |  |
|  | 2502 | Eggs and omelets | `egg` |  |
|  | 2602 | Cold cuts and cured meats | `cold_cuts` |  |
|  | 2604 | Bacon | `bacon` |  |
|  | 2606 | Frankfurters | `frankfurter` |  |
|  | 2608 | Sausages | `sausage` |  |
|  | 2802 | Beans, peas, legumes | `legumes` |  |
|  | 2804 | Nuts and seeds | `nuts` |  |
|  | 2806 | Soy and meat-alternative products | `tofu` |  |
| Mixed dishes | 3002 | Meat mixed dishes | `meat_stew` |  |
|  | 3004 | Poultry mixed dishes | `chicken_dish` (extra) |  |
|  | 3006 | Seafood mixed dishes | `seafood_dish` (extra) |  |
|  | 3102 | Bean, pea, legume dishes | `bean_dish` (extra) |  |
|  | 3104 | Vegetable dishes | `veg_dish` (extra) |  |
|  | 3202 | Rice mixed dishes | `rice_dish` |  |
|  | 3204 | Pasta mixed dishes, excludes macaroni and cheese | `pasta_dish` |  |
|  | 3206 | Macaroni and cheese | `mac_cheese` |  |
|  | 3208 | Turnovers and other grain-based items | `savoury_pastry` |  |
|  | 3402 | Fried rice and lo/chow mein | `noodle_box` |  |
|  | 3404 | Stir-fry and soy-based sauce mixtures | `stir_fry` |  |
|  | 3406 | Egg rolls, dumplings, sushi | `sushi` |  |
|  | 3502 | Burritos and tacos | `taco` |  |
|  | 3504 | Nachos | `nachos` |  |
|  | 3506 | Other Mexican mixed dishes | `quesadilla` (extra) |  |
|  | 3602 | Pizza | `pizza` |  |
|  | 3702 | Burgers | `burger` |  |
|  | 3703 | Frankfurter sandwiches | `hot_dog` |  |
|  | 3704 | Chicken fillet sandwiches | `chicken_sandwich` |  |
|  | 3706 | Egg/breakfast sandwiches | `breakfast_sandwich` |  |
|  | 3720 | Cheese sandwiches | `grilled_cheese` |  |
|  | 3722 | Peanut butter and jelly sandwiches | `pbj_sandwich` |  |
|  | 3730 | Seafood sandwiches | `fish_sandwich` (extra) |  |
|  | 3740 | Deli and cured meat sandwiches | `deli_sandwich` |  |
|  | 3742 | Meat and BBQ sandwiches | `meat_sandwich` (extra) |  |
|  | 3744 | Vegetable sandwiches/burgers | `veggie_burger` |  |
|  | 3804 | Soups, broth-based | `soup` |  |
|  | 3806 | Soups, cream-based | `cream_soup` (extra) |  |
|  | 3808 | Ramen and Asian broth-based soups | `ramen` |  |
| Grains | 4002 | Rice | `rice` |  |
|  | 4004 | Pasta, noodles, cooked grains | `pasta` |  |
|  | 4202 | Yeast breads | `bread` |  |
|  | 4204 | Rolls and buns | `bread_roll` |  |
|  | 4206 | Bagels and English muffins | `bagel` |  |
|  | 4208 | Tortillas | `tortilla` |  |
|  | 4402 | Biscuits, muffins, quick breads | `muffin` |  |
|  | 4404 | Pancakes, waffles, French toast | `pancakes` |  |
|  | 4602 | Ready-to-eat cereal, higher sugar (>21.2g/100g) | `cereal` | sweet |
|  | 4604 | Ready-to-eat cereal, lower sugar (=<21.2g/100g) | `cereal` |  |
|  | 4802 | Oatmeal | `porridge` |  |
|  | 4804 | Grits and other cooked cereals | `porridge` |  |
| Snacks & sweets | 5002 | Potato chips | `potato_chips` |  |
|  | 5004 | Tortilla, corn, other chips | `corn_chips` |  |
|  | 5006 | Popcorn | `popcorn` |  |
|  | 5008 | Pretzels/snack mix | `pretzel` |  |
|  | 5202 | Crackers, excludes saltines | `crackers` |  |
|  | 5204 | Saltine crackers | `crackers` |  |
|  | 5402 | Cereal bars | `granola_bar` |  |
|  | 5404 | Nutrition bars | `protein_bar` |  |
|  | 5502 | Cakes and pies | `cake` |  |
|  | 5504 | Cookies and brownies | `cookie` |  |
|  | 5506 | Doughnuts, sweet rolls, pastries | `pastry` |  |
|  | 5702 | Candy containing chocolate | `chocolate` |  |
|  | 5704 | Candy not containing chocolate | `candy` |  |
|  | 5802 | Ice cream and frozen dairy desserts | `ice_cream` |  |
|  | 5804 | Pudding | `pudding` |  |
|  | 5806 | Gelatins, ices, sorbets | `ice_lolly` |  |
| Fruit | 6002 | Apples | `apple` |  |
|  | 6004 | Bananas | `banana` |  |
|  | 6006 | Grapes | `grapes` |  |
|  | 6008 | Peaches and nectarines | `peach` |  |
|  | 6009 | Strawberries | `strawberry` |  |
|  | 6011 | Blueberries and other berries | `berries` |  |
|  | 6012 | Citrus fruits | `citrus` |  |
|  | 6014 | Melons | `melon` |  |
|  | 6016 | Dried fruits | `dried_fruit` |  |
|  | 6018 | Other fruits and fruit salads | `mixed_fruit` (extra) |  |
|  | 6020 | Pears | `pear` |  |
|  | 6022 | Pineapple | `pineapple` |  |
|  | 6024 | Mango and papaya | `mango` |  |
| Vegetables | 6402 | Tomatoes | `tomato` |  |
|  | 6404 | Carrots | `carrot` |  |
|  | 6406 | Other red and orange vegetables | `pepper` |  |
|  | 6407 | Broccoli | `broccoli` |  |
|  | 6409 | Spinach | `spinach` |  |
|  | 6410 | Lettuce and lettuce salads | `lettuce` |  |
|  | 6411 | Other dark green vegetables | `kale` |  |
|  | 6412 | String beans | `green_beans` |  |
|  | 6413 | Cabbage | `cabbage` |  |
|  | 6414 | Onions | `onion` |  |
|  | 6416 | Corn | `corn` |  |
|  | 6418 | Other starchy vegetables | `peas` |  |
|  | 6420 | Other vegetables and combinations | `mixed_veg` (extra) |  |
|  | 6430 | Fried vegetables | `onion_rings` |  |
|  | 6432 | Coleslaw, non-lettuce salads | `coleslaw` |  |
|  | 6489 | Vegetables on a sandwich | `generic_food` |  |
|  | 6802 | White potatoes, baked or boiled | `potato` |  |
|  | 6804 | French fries and other fried white potatoes | `fries` |  |
|  | 6806 | Mashed potatoes and white potato mixtures | `mashed_potato` |  |
| Beverages | 7002 | Citrus juice | `orange_juice` |  |
|  | 7004 | Apple juice | `apple_juice` |  |
|  | 7006 | Other fruit juice | `juice` |  |
|  | 7008 | Vegetable juice | `veg_juice` |  |
|  | 7102 | Diet soft drinks | `soft_drink` | zero |
|  | 7104 | Diet sport and energy drinks | `energy_drink` | zero |
|  | 7106 | Other diet drinks | `fruit_drink` | zero |
|  | 7202 | Soft drinks | `soft_drink` |  |
|  | 7204 | Fruit drinks | `fruit_drink` |  |
|  | 7206 | Sport and energy drinks | `energy_drink` |  |
|  | 7208 | Nutritional beverages | `nutrition_shake` |  |
|  | 7220 | Smoothies and grain drinks | `smoothie` |  |
|  | 7302 | Coffee | `coffee` |  |
|  | 7304 | Tea | `tea` |  |
| Alcoholic beverages | 7502 | Beer | `beer` |  |
|  | 7504 | Wine | `wine` |  |
|  | 7506 | Liquor and cocktails | `spirits` |  |
| Water | 7702 | Tap water | `generic_food` |  |
|  | 7704 | Bottled water | `water` |  |
|  | 7802 | Flavored or carbonated water | `sparkling_water` |  |
|  | 7804 | Enhanced water | `water` | +vitamins |
| Fats & oils | 8002 | Butter and animal fats | `butter` |  |
|  | 8004 | Margarine | `margarine` |  |
|  | 8006 | Cream cheese, sour cream, whipped cream | `sour_cream` |  |
|  | 8008 | Cream and cream substitutes | `cream` |  |
|  | 8010 | Mayonnaise | `mayonnaise` |  |
|  | 8012 | Salad dressings and vegetable oils | `dressing` |  |
| Condiments & sauces | 8402 | Tomato-based condiments | `ketchup` |  |
|  | 8404 | Soy-based condiments | `soy_sauce` |  |
|  | 8406 | Mustard and other condiments | `mustard` |  |
|  | 8408 | Olives, pickles, pickled vegetables | `olives` |  |
|  | 8410 | Pasta sauces, tomato-based | `pasta_sauce` |  |
|  | 8412 | Dips, gravies, other sauces | `dip` (extra) |  |
| Sugars | 8802 | Sugars and honey | `honey_sugar` |  |
|  | 8804 | Sugar substitutes | `sweetener` |  |
|  | 8806 | Jams, syrups, toppings | `jam` |  |
| Infant formula & baby food | 9002 | Baby food: cereals | `baby_cereal` |  |
|  | 9004 | Baby food: fruit | `baby_food` | fruit |
|  | 9006 | Baby food: vegetables | `baby_food` | veg |
|  | 9007 | Baby food: mixtures | `baby_food` | mixed |
|  | 9008 | Baby food: meat and dinners | `baby_food` | meal |
|  | 9010 | Baby food: yogurt | `baby_food` | yogurt |
|  | 9012 | Baby food: snacks and sweets | `baby_snack` |  |
|  | 9202 | Baby juice | `baby_drink` |  |
|  | 9204 | Baby water | `baby_drink` |  |
|  | 9402 | Formula, ready-to-feed | `formula` | liquid |
|  | 9404 | Formula, prepared from powder | `formula` | powder |
|  | 9602 | Human milk | `generic_food` |  |
| Other | 9802 | Protein and nutritional powders | `protein_powder` |  |
|  | 9999 | Not included in a food category | `generic_food` |  |
| Grains | X01 | Flour | `flour` |  |
| Cooking & baking | X02 | Baking ingredients and mixes | `baking` |  |
|  | X03 | Salt, herbs and spices | `spices` |  |
|  | X04 | Stocks and bouillon | `stock` |  |
| Condiments & sauces | X05 | Vinegar | `vinegar` |  |
| Fats & oils | X06 | Cooking oils | `oil` |  |
| Protein foods | X07 | Nut and seed butters | `nut_butter` |  |
| Sugars | X08 | Chocolate and sweet spreads | `choc_spread` |  |
| Beverages | X09 | Hot chocolate and drink powders | `hot_chocolate` |  |
|  | X10 | Iced tea | `iced_tea` |  |
| Other | X11 | Vitamins and supplements | `supplements` |  |
