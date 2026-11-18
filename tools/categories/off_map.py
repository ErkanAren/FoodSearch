"""Open Food Facts category tags -> our 183 categories (docs/CATEGORIES.md). Hand-written, 2026-11-17.

Used to (1) give the category model thousands of real packaged products to learn from (stage 05) and, later,
(2) label OFF products in the catalogue directly when their tags are clear.

Format of MAP: one line per category, "CODE tag tag ~tag ...". Tags are OFF English tags without "en:".
  tag     strong: decides the category on its own.
  ~tag    weak: a broad tag, used only when the product has no strong tag (e.g. ~meals-with-chicken -> 3004,
          but pasta-dishes -> 3204 wins: the dish type beats the protein).
Rules (see label()):
  - Products with a non-food tag are skipped.
  - OFF also gives every product all parent tags. A tag is dropped when a more specific tag of the same branch is
    present (cheeses -> 1602 is dropped when cream-cheeses -> 8006 is there). The tree is learned from the data:
    A is a parent of B when >= 90 % of B's products also carry A (ancestors()).
  - The remaining specific tags must agree. Strong tags that point to different categories, or (without a strong
    tag) weak tags that do, = conflicting tags -> skipped, not guessed.
  - A tag in BLOCK makes weak-only labels unreliable -> skipped unless a strong tag decides.
  - Baby products (any BABY_CONTEXT tag) only get baby categories (9002-9404), via BABY or by translating
    the normal label (fruit -> 9004, vegetables -> 9006, ...); otherwise skipped.
  - Families decided by nutrients (milk fat, cereal sugar, diet drinks) are finished by the same rules as the
    model's predictions (stage 05 bench.py: apply_rules).
"""

MAP = """
1002 whole-milks whole-milk-uht evaporated-milks buttermilks
1004 ~milks ~cow-milks ~homogenized-milks ~uht-milks ~pasteurised-milks ~fresh-milks ~esl-milks ~lactose-free-milk
1006 semi-skimmed-milks semi-skimmed-milk-uht kefir
1008 skimmed-milks
1202 condensed-milks
1204 chocolate-milks flavoured-milks
1402 milkshakes
1602 ~cheeses ~cow-cheeses ~french-cheeses ~italian-cheeses ~hard-cheeses ~uncooked-pressed-cheeses ~soft-cheeses
     ~stretched-curd-cheeses ~firm-ripened-cheeses ~goat-cheeses ~sheep-s-milk-cheeses ~pasteurized-cheeses
     ~cheeses-from-the-united-kingdom ~cheeses-of-the-netherlands ~cheeses-from-england ~labeled-cheeses ~aoc-cheeses
     ~unpasteurised-cheeses ~semi-hard-cheeses ~mountain-cheeses ~greek-cheeses ~buffalo-cheeses
     ~cheeses-from-switzerland ~spanish-cheeses ~danish-cheeses ~cypriot-cheeses ~industrial-cheese
     ~cheeses-perishable ~soft-cheeses-with-bloomy-rind ~soft-cheeses-with-washed-rind ~soft-cheese-with-a-natural-rind
     ~blue-veined-cheeses ~french-blue-veined-cheeses ~extra-hard-cheeses
     cheddar-cheese mozzarella comte emmentaler gouda parmigiano-reggiano grana-padano feta camemberts sliced-cheeses
     grated-cheese processed-cheeses processed-cheese cheese-spreads raclette bries reblochon mimolette-cheese edam
     grated-emmentaler morbier roquefort-cheeses gorgonzolas cow-camemberts swiss-gruyeres pecorino cantal young-goudas
     maasdam saint-nectaire beaufort halloumi grilling-cheeses havarti burrata buffalo-mozzarella
     mozzarella-di-bufala-campana stracchino tomme-cheese-from-cow-s-milk french-emmentaler brie-de-meaux-cheeses
     cancoillottes
1604 cottage-cheeses ricotta quarks lean-quark ~fromages-blancs-petit-suisses-and-skyr
1820 ~yogurts ~cow-milk-yogurts ~fermented-dairy-desserts ~fermented-dairy-desserts-with-fruits
     ~plain-fermented-dairy-desserts ~flavoured-fermented-dairy-desserts ~fruit-yogurts ~plain-yogurts
     ~flavoured-yogurts ~bifidus-yogurts ~stirred-yogurts ~plain-stirred-yogurts ~whole-milk-yogurts ~sweetened-yogurts
     ~low-fat-yogurts ~strawberry-yogurts ~vanilla-yogurt ~sheep-milk-yogurts ~goat-milk-yogurts ~fruit-stirred-yogurts
     ~blueberry-yogurts ~fruit-yogurts-with-fruit-chunks
     drinkable-yogurts yogurt-drinks flavoured-yogurt-drinks
1822 greek-style-yogurts skyrs
1902 ~milk-substitutes ~cereal-based-drinks plant-based-milk-alternatives oat-based-drinks soy-based-drinks
     almond-based-drinks rice-based-drinks nut-based-drinks legume-based-drinks
1904 non-dairy-yogurts soy-milk-yogurts coconutmilk-yogurts fruit-soy-yogurts
2002 ~steaks ~beef beef-steaks veal-meat beef-stew-meat
2004 ~ground-meats ~meat-patties ground-beef-steaks ground-steaks fresh-ground-steaks fresh-ground-beef-steaks
     ground-beef-preparations beef-patties
2006 ~pork pork-ribs pork-filet-mignon pork-belly pork-roasts
2008 lamb-meat rabbit-meat
2010 ~offals liver-pates tripe gizzards foies-gras block-of-foie-gras whole-foies-gras foies-gras-from-ducks
     whole-foies-gras-from-ducks
2202 ~chickens ~cooked-chicken chicken-breasts chicken-thighs chicken-wings chicken-drumsticks whole-chickens
     chicken-cutlets
2204 chicken-nuggets poultry-nuggets breaded-chicken breaded-turkey breaded-turkey-cutlets cordons-bleus
2206 ~turkeys ~ducks ~turkey-breasts turkey-cutlets duck-breasts duck-fillets duck-confit
2402 ~fishes ~fatty-fishes ~lean-fishes ~fishes-and-their-products ~canned-fishes ~frozen-fishes salmons tunas
     canned-tunas tunas-in-oil tuna-in-olive-oil tunas-in-brine tunas-in-sunflower-oil albacore tuna-fillets tuna-chunks
     tropical-tunas yellowfin-tunas sardines canned-sardines sardines-in-oil sardines-in-olive-oil
     sardines-in-tomato-sauce sardines-in-sunflower-oil sardines-in-oil-and-chili mackerels mackerel-fillets
     tinned-mackerels smoked-salmons smoked-salmons-from-farming smoked-fishes smoked-trouts trouts cods cod-fillets
     salmon-fillets salmon-steaks wild-salmons herring herring-fillets canned-herrings anchovy anchovy-fillets
     marinated-anchovy-fillets marinated-anchovy-fillets-with-vegetable-oil pollocks fish-fillets fish-fingers
     breaded-fish fish-eggs
2404 crustaceans shrimps prawns shrimps-tails mussels mollusc canned-mussels mussels-with-escabeche calamari surimi
2502 ~eggs ~eggs-and-their-products chicken-eggs fresh-eggs free-range-chicken-eggs barn-chicken-eggs large-eggs
     medium-eggs cage-chicken-eggs organic-eggs extra-large-eggs variable-size-eggs-by-batch spanish-omelettes
     egg-salads
2602 ~hams ~italian-meat-products white-hams cured-hams dried-hams raw-cured-ham serrano-ham salami cured-sausages
     dry-sausages rosette-dry-sausage dry-sausage-pure-pork pork-salami chorizos mortadella bresaola coppa parma-ham
     cooked-ham-of-superior-quality braised-hams smoked-cured-hams white-smoked-hams meat-of-the-grisons beef-jerkies
     corned-beef poultry-hams cooked-chicken-breast-slices cooked-turkey-breast-slices dried-meats raw-cured-meats
2604 bacon lardons smoked-lardons smoked-bacon sliced-bacon pancetta
2606 frankfurter-sausages strasbourg-sausages
2608 ~sausages ~french-sausages ~german-sausages pork-sausages chipolatas toulouse-sausages chicken-sausages
     poultry-sausages smoked-sausages cooked-sausages garlic-sausage cervelat black-pudding sauteed-black-pudding
     chitterling-sausage sausage-meat
2802 ~legumes ~canned-legumes pulses legume-seeds common-beans canned-common-beans lentils green-lentils red-lentils
     canned-lentils chickpeas canned-chickpeas white-beans red-beans canned-red-kidney-beans canned-white-common-beans
     black-beans pinto-beans baked-beans-in-tomato-sauce soy-beans prepared-lentils edamame frozen-edamame
2804 ~nuts shelled-nuts almonds peanuts cashew-nuts pistachios walnuts hazelnuts shelled-almonds shelled-hazelnuts
     roasted-nuts salted-nuts roasted-peanuts salted-peanuts roasted-pistachios salted-pistachios walnut-kernels
     pecan-nuts brazil-nuts pine-nuts mixed-nuts salted-cashews roasted-cashew-nuts salted-almonds sunflower-seeds
     roasted-sunflower-seeds pumpkin-seeds shelled-pumpkin-seeds roasted-pumpkin-seeds flax-seeds chia
     cucurbitacea-seeds mixed-nuts-and-dried-fruits trail-mix grated-coconut chestnuts walnuts-halves-and-pieces
2806 ~meat-alternatives meat-analogues tofu plain-tofu smoked-tofu tempeh seitan textured-vegetable-protein
     textured-soy-protein vegetarian-patties vegetarian-sausages vegetarian-hot-dog-sausages vegetarian-balls
     vegetarian-nuggets vegan-patties vegetarian-hamburgers tofu-patties meat-analogues-from-soy-or-wheat-proteins
     meat-analogues-from-pea-proteins patties-from-soy-and-or-wheat-proteins prepared-meat-cuts-substitutes
     cheese-substitutes
3002 ~meals-with-meat ~meals-with-beef ~pork-meals ~meat-balls ~meatballs ~stews beef-dishes chili-con-carne
     cassoulets cassoulets-with-duck-confit beef-cottage-pies beef-stews moussaka meatloafs sausages-with-lentils
     sauerkraut-with-garnish tripe-dishes specialty-made-with-tripe
3004 ~meals-with-chicken ~meals-with-poultry ~poultry-meals chicken-curry duck-dishes shepherd-s-pie-with-duck
     chicken-salads
3006 ~meals-with-fish ~meals-with-salmon ~meals-with-shellfish ~salads-with-fish ~tuna-preparations tuna-salads
     cod-brandade fish-rillettes tuna-rillettes salmon-rillettes tuna-and-vegetable-salads
3102 legume-dishes lentil-dishes bean-dishes falafels chili-sin-carne lentil-salads
3104 ratatouille stuffed-tomatoes stuffed-peppers stuffed-vegetables prepared-eggplants
3202 ~rice-dishes paella risottos vegetable-risottos stuffed-vine-leaves rice-salads
3204 pasta-dishes prepared-lasagne meat-lasagnas bolognese-lasagne vegetarian-lasagne vegetable-lasagnas frozen-lasagne
     fish-lasagnas salmon-lasagne stuffed-pastas tortellini raviolis ravioli tortelloni meat-ravioli beef-ravioli
     cheese-ravioli pasta-stuffed-with-meat pasta-stuffed-with-cheese pasta-stuffed-with-vegetables canned-raviolis
     stuffed-pastas-in-sauce pasta-in-sauce pasta-salads pasta-salad-with-meat pasta-salad-with-chicken
     pasta-salad-with-fish vegetarian-pasta-salads cannelloni fresh-pasta-stuffed-with-cheese
     fresh-pasta-stuffed-with-meat fresh-pasta-stuffed-with-cheese-and-vegetables fresh-pasta-stuffed-with-vegetables
3206 macaroni-and-cheese
3208 ~pies quiches lorraine-quiche leek-quiche salted-pies meat-pies cheese-pies pork-pies vegetables-pies
     pate-in-crust samosas stuffing
3402 fried-rice pad-thai
3406 sushi-and-maki sushis nems spring-rolls gyoza vegetable-gyoza dumplings chinese-dumplings chinese-shrimp-dumplings
     frozen-dumplings egg-roll-with-cooked-shrimp pierogi
3502 burritos
3506 fajitas-kits
3602 pizzas frozen-pizzas vegetarian-pizzas cheese-pizzas pizzas-with-meat margherita-pizza margherita-pizzas
     pepperoni-pizzas four-cheese-pizza pizza-with-ham-and-cheese flammekueche
3702 ~hamburgers cheeseburgers beef-hamburgers mini-appetizer-hamburgers
3703 hot-dog-sandwiches
3704 poultry-sandwiches chicken-sandwiches chicken-wraps chicken-hamburgers
3706 egg-sandwiches breakfast-sandwich
3720 cheese-sandwiches emmental-cheese-sandwiches
3730 fish-sandwiches tuna-sandwiches salmon-sandwiches sandwich-with-tuna-and-vegetables
3740 sandwiches-filled-with-cold-cuts ham-sandwiches club-sandwiches toasted-ham-sandwich-topped-with-grated-cheese
     ham-and-cheese-sandwiches sandwiches-with-ham-and-emmental-cheese ham-and-butter-sandwiches bacon-sandwiches
     rosette-sandwiches
3744 raw-vegetable-sandwiches
3804 ~soups ~canned-soups ~reheatable-soups ~dehydrated-soups vegetable-soups tomato-soups fish-soups gazpacho cold-soups
3806 cream-soups cream-of-vegetable-soups cream-of-pumpkin-soups pumpkin-soups cream-of-leek-soups
3808 instant-noodles instant-noodle-soups flavoured-dehydrated-asian-noodles flavoured-asian-noodles pot-noodles
     dehydrated-asian-style-soup-with-noodles miso-soup
4002 ~rices long-grain-rices aromatic-rices indica-rices basmati-rices white-basmati-rices jasmine-rice brown-rices
     white-rices japonica-rices short-grain-rices medium-grain-rices parboiled-rices rices-for-risotto
4004 ~pastas ~cereal-pastas ~fresh-pasta ~noodles ~chinese-noodles dry-pastas durum-wheat-pasta dry-durum-wheat-pasta
     spaghetti penne penne-rigate fusilli rigatoni tagliatelle linguine orecchiette durum-wheat-spaghetti egg-pastas
     dry-egg-pastas egg-noodles rice-vermicelli rice-noodles dried-rice-noodles whole-wheat-noodles durum-wheat-noodles
     gluten-free-pasta whole-or-semi-whole-durum-wheat-pasta whole-durum-wheat-pasta lasagna-sheets
     durum-wheat-plates-for-lasagna quinoa bulgur groats wheat-groats buckwheat durum-wheat-semolinas-for-couscous
     spatzle gnocchi potato-gnocchi
4202 ~breads ~special-breads sliced-breads white-breads wholemeal-breads wheat-breads baguettes bread-loaves rye-breads
     wholemeal-sliced-breads multigrain-sliced-breads pains-de-campagne gluten-free-breads pre-baked-breads flatbreads
     wheat-flatbreads pitas piadina
4204 bread-rolls hamburger-buns hot-dog-buns milk-bread-rolls
4206 bagel-breads english-muffins
4208 tortillas
4402 muffins fruit-muffins
4404 crepes-and-pancakes crepes pancakes waffles crepes-and-galettes filled-crepes plain-buckwheat-crepes
     plain-sweet-crepes stuffed-waffles honey-stuffed-waffles
4602 ~breakfast-cereals ~cereal-flakes ~puffed-cereals mueslis crunchy-mueslis mueslis-with-fruits mueslis-with-chocolate
     chocolate-cereals cereals-with-fruits cereals-with-nuts extruded-cereals extruded-flakes filled-cereals
     crunchy-cereal-clusters
4604 corn-flakes
4802 ~rolled-flakes ~oat rolled-oats porridge porridge-with-fruits plain-porridge porridge-with-chocolate
5002 crisps potato-crisps salty-snacks-made-from-potato flavoured-potato-crisps potato-crisps-in-sunflower-oil
     stacked-extruded-potato-crisps
5004 corn-chips puffed-salty-snacks puffed-salty-snacks-made-from-maize puffed-salty-snacks-made-from-potato-and-soy
     cassava-crisps plantain-chips plantain-crisps sweet-potato-crisps
5006 popcorn salted-popcorn sugared-popcorn
5008 pretzel bread-pretzels
5202 crackers crackers-appetizers rusks toasts crispbreads extruded-crispbreads puffed-rice-cakes puffed-corn-cakes
     puffed-cereal-cakes breadsticks taralli croutons rice-crackers
5402 cereal-bars chocolate-cereal-bars fruits-cereal-bars nut-bars
5404 protein-bars energy-bars protein-energy-bars
5502 ~cakes ~sweet-pastries-and-pies chocolate-cakes chocolate-based-cakes pound-cake marble-cakes fruit-cakes filled-cakes
     molten-chocolate-cakes madeleines chocolate-madeleines gingerbreads gingerbread-blocks cheesecakes yule-log
     friands king-cakes puff-pastry-king-cakes tiramisu sweet-pies apple-pies fruit-tarts tartlets fruit-tartlets
     lemon-tarts lemon-tartlets lemon-meringue-pies strawberry-pies strawberry-tartlets raspberry-pies blueberry-pies
     pear-pies pumpkin-pies chocolate-pies tatin-tart tropezian-pies norman-style-pies baklava strudels babas rum-babas
     rum-baba sponge-sandwich-cake-filled-and-topped-with-strawberries
5504 ~biscuits chocolate-biscuits shortbread-cookies shortbread dry-biscuits filled-biscuits drop-cookies
     chocolate-chip-cookies wafers stuffed-wafers chocolate-stuffed-wafers vanilla-stuffed-wafers caramel-stuffed-wafers
     hazelnut-cream-stuffed-wafers nut-stuffed-wafers sandwich-biscuits flaky-biscuits oatmeal-biscuits oatmeal-cookies
     petit-beurre palmiers chocolate-sandwich-cookies cantucci almond-cookies speculoos macarons coconut-macaroons
     meringues digestives-covered-with-chocolate milk-chocolate-biscuits dark-chocolate-biscuits
     chocolate-covered-biscuits jaffa-cakes assortments-of-biscuits biscuits-or-cookies-variety-packs
     gluten-free-biscuits breakfast-biscuit brownies tartlet-biscuits-with-fruit-preparation
     tartlet-biscuits-with-chocolate biscuits-cookies-shelf-stable
5506 ~viennoiseries ~laminated-dough-pastries croissants butter-croissants filled-croissants chocolate-croissant brioches
     pure-butter-brioche brioche-filled-with-chocolate-drops brioche-filled-with-custard doughnuts jam-doughnuts
     sweet-fritters apple-turnovers panettone pandoro colomba eclairs cream-puff breads-with-raisins
5702 ~chocolates dark-chocolates milk-chocolates white-chocolates chocolate-candies candy-chocolate-bars filled-chocolates
     chocolate-eggs easter-eggs chocolate-molds assorted-chocolate-candies chocolates-with-hazelnuts
     chocolates-with-almonds chocolate-covered-nuts chocolate-truffles filled-milk-chocolates
     milk-chocolates-with-hazelnuts chocolate-covered-nuts-and-fruits chocolate-covered-fruits
     dark-chocolate-bar-with-more-than-70-cocoa dark-chocolates-with-almonds filled-dark-chocolates caramel-chocolates
     milk-chocolate-bar chocolate-bars dark-chocolate-bars bars-covered-with-chocolate dark-chocolates-with-hazelnuts
     filled-chocolate-eggs chocolates-with-sweeteners flavoured-chocolates salted-chocolates extra-fine-dark-chocolates
     chocolate-covered-almonds chocolate-covered-peanuts assorted-chocolates chocolate-filled-with-praline
     dark-chocolates-with-orange milk-chocolates-with-almonds chocolate-rabbits hollow-chocolate-eggs
     marshmallows-coated-with-chocolate chocolate-turron biscuit-with-a-chocolate-bar-covering
     white-chocolate-with-coconut-pieces
5704 ~candies ~turron gummi-candies gummy-bears acid-gummy-candies lollipops chewing-gums chewing-gum
     sugar-free-chewing-gum marshmallows caramels salted-butter-caramels nougats almond-turron creamy-almond-turron
     crunchy-almond-turron liquorice-candies hard-candies jelly-beans halva marzipan fruit-pastes fruit-confectioneries
     honey-candies calissons marrons-glaces
5802 ice-creams ~ice-creams-and-sorbets ice-cream-tubs ice-cream-bars ice-cream-cones vanilla-ice-cream-tubs
     chocolate-ice-cream-tubs ice-cream-sandwiches coated-ice-cream-bars ice-cream-bars-coated-with-chocolate
     plant-based-ice-creams frozen-cones ice-cream-logs ice-cream-log mochi-ice-cream frozen-yogurts tartufo
5804 ~puddings ~chocolate-desserts creamy-puddings entremets-mousses-and-creamy-puddings rice-puddings chocolate-mousses
     dairy-mousses sweet-mousses flans custard-puddings refrigerated-creamy-puddings chocolate-creamy-puddings
     refrigerated-chocolate-creamy-puddings vanilla-creamy-puddings vegan-creamy-puddings dairy-chocolate-desserts
     custards-and-pastry-creams light-custard-cream-with-vanilla custard-puddings-with-caramel-sauce
     vanilla-custard-puddings chocolate-custard-puddings
5806 sorbets lemon-sorbets strawberry-sorbets mango-sorbets raspberry-sorbets pear-sorbets multifruit-sorbets
     passion-fruit-sorbets apricot-sorbets lime-sorbets sorbets-on-stick sorbet-cones ice-pops jelly-desserts
6002 apples fresh-apples sweet-apples apple-compotes applesauces
6004 bananas
6006 grapes green-grapes
6008 peaches peaches-in-syrup nectarines
6009 strawberries
6011 ~berries blueberries raspberries fresh-raspberries frozen-berries cranberries cranberry-sauces
6012 ~citrus oranges lemons mandarins
6014 melons muskmelons fresh-muskmelons watermelons cantaloupe-melons
6016 dried-fruits ~dates-and-their-products raisins sultana-raisins dates deglet-noor-dates medjool-dates dried-apricots
     dried-prunes dried-figs dried-cranberries dried-mangoes dried-papayas dried-bananas mixed-dried-fruits
     dried-mixed-fruits dried-goji
6018 ~compotes ~fruits-in-syrup ~canned-fruits ~canned-fruits-in-juice ~fruits-puree-without-sugar-added fruit-salads
     fresh-fruit-salad fruit-salads-in-syrup kiwifruits cherries apricots coconuts compotes-to-drink
6020 pears
6022 pineapple pineapples canned-pineapples
6024 mangoes papayas
6402 tomatoes fresh-tomatoes cherry-tomatoes canned-tomatoes peeled-tomatoes tomato-purees strained-tomatoes
     tomato-pastes double-concentrate-tomato-paste concentrated-tomato-products tomato-pulps dried-tomatoes
     ~canned-tomato-products
6404 carrots fresh-carrots ~grated-carrots
6406 ~peppers ~pumpkin-and-squash-plant-products ~sweet-potatoes-and-their-products sweet-potatoes fresh-sweet-potatoes
     sweet-peppers pumpkins squash butternut-squashes red-kuri-squash
6407 broccoli
6409 spinachs frozen-spinachs
6410 lettuces leaf-salads corn-salad caesar-salads iceberg-lettuce rocket mix-of-salad-leaves romaine-lettuce
6411 chards
6412 green-beans canned-green-beans
6413 cabbages red-cabbage
6414 onions leeks shallots
6416 corn canned-corn canned-sweet-corn sweet-corn
6418 green-peas canned-peas peas
6420 mushrooms champignon-mushrooms canned-mushrooms fresh-mushrooms sliced-champignon-mushrooms
     canned-champignon-mushrooms dried-mushrooms asparagus white-asparagus canned-asparagus canned-white-asparagus
     artichokes artichoke-hearts canned-artichokes avocados cucumbers zucchini cauliflowers beetroot cooked-beetroots
     vacuum-packed-beetroot canned-beetroot radishes red-radishes aubergines celery brussels-sprouts mixed-vegetables
     frozen-mixed-vegetables fresh-mixed-vegetables vegetables-macedoines canned-peas-and-carrots sprouts
     dried-seaweeds
6430 breaded-onion-rings sweet-potato-fries
6432 coleslaw carrot-salads seasoned-grated-carrots tabbouleh eastern-tabbouleh vegetable-salads beets-salads
     cucumber-salads
6802 potatoes
6804 frozen-fried-potatoes fries potato-fries frozen-potato-fries rostis fried-potatoes hash-browns
6806 mashed-potatoes instant-mashed-potatoes potato-salads potato-gratin piemontese-salads piemontese-salads-with-ham
     tartiflettes
7002 orange-juices squeezed-orange-juices orange-juices-from-concentrate grapefruit-juices
7004 apple-juices squeezed-apple-juices apple-juices-from-concentrate
7006 ~fruit-juices ~squeezed-fruit-juices ~fruit-juices-from-concentrate ~squeezed-juices ~refrigerated-squeezed-juices
     multifruit-juices squeezed-multifruit-juices multifruit-juices-from-concentrate grape-juices pineapple-juices
     pomegranate-juices fruit-and-vegetable-juices cranberry-juices
7008 tomato-juices vegetable-juices carrot-juices beetroot-juices
7102 diet-sodas diet-cola-soft-drink
7104 energy-drink-without-sugar-and-with-artificial-sweeteners
7202 ~sodas ~soft-drinks ~flavoured-soft-drinks colas fruit-sodas carbonated-fruit-soft-drink orange-soft-drinks
     lemon-soft-drinks ginger-beer carbonated-soft-drinks-without-fruit-juice
7204 ~still-soft-drinks fruit-nectars apricot-nectars peach-nectars multifruit-nectars mango-nectars pear-nectars
     apple-nectars orange-nectars still-fruit-soft-drinks coconut-waters grenadine
     mint-syrups strawberry-syrups
7206 energy-drinks energy-drink-with-sugar dietary-drink-for-sport sports-drinks sports-drink electrolyte-drink
7208 protein-shakes protein-drink
7220 smoothies fruit-smoothies horchatas-de-chufa
7302 coffees coffee-capsules instant-coffees ground-coffees coffee-beans nespresso-compatible-coffee-capsules
     arabica-coffees decaffeinated-coffees coffee-drinks iced-coffees powdered-cappucino
7304 ~teas green-teas black-teas herbal-teas tea-bags tea-leaves herbal-teas-in-tea-bags flavoured-teas flavored-teas
     fruit-teas herbal-tea-blends flavored-black-teas rooibos mint-teas green-teas-with-mint kombuchas
7502 beers lagers ales pale-ales blonde-ales craft-beers wheat-beers amber-beers belgian-beers beers-from-germany
     french-beers country-specific-beers non-alcoholic-beers beers-with-fruits beer-based-alcoholic-beverages shandy
     ciders
7504 wines red-wines white-wines rose-wines sparkling-wines champagnes prosecco wines-from-france wines-from-italy
     wines-from-spain bordeaux-wines burgundy-wines
7506 hard-liquors distilled-beverages eaux-de-vie liqueurs whisky rums gins vodka artisanal-spirits
     premixed-alcoholic-beverages
7704 ~waters ~mineral-waters ~natural-mineral-waters spring-waters non-carbonated-natural-mineral-waters drinking-water
7802 ~flavored-waters carbonated-waters carbonated-mineral-waters carbonated-natural-mineral-waters
     flavored-sparkling-waters tonic-water
7804 vitamin-waters
8002 ~animal-fats ~milkfat butters unsalted-butters salted-butters half-salted-butter sweet-cream-butters butter-fat
8004 margarines light-margarines margarines-high-in-omega-3
8006 cream-cheeses mascarpone sour-creams cremes-fraiches whipped-creams fermented-creams smetana
8008 ~creams ~plant-based-creams uht-creams unfermented-creams plant-based-creams-for-cooking creamer
8010 ~emulsified-sauces mayonnaises light-mayonnaises aiolis tartare-sauces
8012 salad-dressings vinaigrettes caesar-salad-dressings
8402 ketchup tomato-ketchup curry-ketchups barbecue-sauces salsa
8404 soy-sauces teriyaki-sauces misos
8406 mustards dijon-mustards old-style-mustards hot-sauces sriracha-sauces harissa-sauces sweet-chili-sauces
     sweet-and-sour-sauces wasabi-pastes grated-horseradish fresh-horseradish chutneys fruit-chutneys onion-chutneys
     lemon-juice
8408 ~pickles ~fermented-vegetables plant-based-pickles olives green-olives black-olives pitted-olives
     green-stuffed-olives stuffed-olives green-pitted-olives black-pitted-olives whole-olives
     green-olives-stuffed-of-anchovies green-olives-stuffed-of-peppers green-olives-stuffed-of-almond pickled-cucumbers
     pickled-gherkins gherkins sweet-and-sour-gherkins pickled-vegetables pickled-beetroots sauerkrauts pickled-capers
     kimchi relish
8410 ~pasta-sauces ~meat-based-sauces tomato-sauces bolognese-sauces meat-based-pasta-sauces arrabbiata-sauces
     tomato-sauces-with-basil fried-tomato-sauces pizza-sauces
8412 ~meal-sauces dips hummus classic-hummus guacamoles tzatzikis taramasalata pestos green-pestos red-pestos
     curry-sauces curry-pastes red-curry-pastes green-curry-pastes yellow-curry-pastes cooking-sauces dehydrated-sauces
     eggplant-caviar tapenades black-tapenades green-tapenades cheese-sauces white-sauces bechamel-sauces gravy
     alfredo-sauces
8802 sugars brown-sugars cane-sugars cane-sugar granulated-sugars coconut-sugar beet-sugars honeys flower-honeys
     acacia-honeys honeys-from-france chestnut-honey lavender-honeys citrus-honeys forest-honeys linden-honeys
     rosemary-honeys orange-blossom-honeys thyme-honeys honeys-from-the-mountains agave-syrups
8804 sugar-substitutes tabletop-sweeteners artificial-sugar-substitutes natural-sugar-substitutes
8806 jams ~fruit-preserves berry-jams fruit-jams strawberry-jams apricot-jams raspberry-jams citrus-jams marmalades
     orange-jams cherry-jams mixed-fruit-jams figs-jams plum-jams peach-jams blueberry-jams bilberry-jams
     bilberries-jams mixed-jams tropical-fruit-jams mixed-berry-jams blackberry-jams maple-syrups dessert-sauces
     fruits-coulis
9802 protein-powders whey-powder protein-supplement whey
X01 flours cereal-flours wheat-flours common-wheat-flours whole-wheat-flours spelt-flours white-wheat-flours rice-flours
    buckwheat-flours legume-flours nut-flours cassava-flour cornmeal starches ~corn-semolinas ~cereal-semolinas
    ~wheat-semolinas ~durum-wheat-semolinas
X02 ~dessert-mixes ~pastry-helpers ~vanilla baking-mixes cake-mixes pancake-mixes baking-decorations sprinkles
    pie-dough puff-pastry-sheets shortcrust-pastry pizza-dough yeast baker-s-yeast baking-powder-or-raising-agent
    vanilla-extract gelatin bread-crumbs bread-coverings food-colorings thickeners mixes-for-jelly-desserts cocoa-powders
X03 ~spices ~herbs-and-spices ~herbs ~aromatic-plants salts sea-salts himalaya-salts unrefined-salts fleurs-de-sel
    french-salts black-peppers ground-black-peppers peppercorns ground-peppers paprika cinnamon cinnamon-powder turmeric
    turmeric-powder cumin curry-powders curry-powder chili-powders spice-blends spice-mix mixtures-of-herbs-and-spices
    mixed-herbs herbes-de-provence ground-dried-aromatic-plants ground-dried-vegetables
X04 ~broths ~vegetable-broths ~meat-broths ~poultry-broth ~beef-broth dehydrated-broths bouillon-cubes
    dehydrated-vegetable-bouillons liquid-broths
X05 vinegars balsamic-vinegars balsamic-vinegars-of-modena wine-vinegars cider-vinegars white-wine-vinegars
    glazes-with-vinegar
X06 ~vegetable-oils ~oils ~fruit-and-fruit-seed-oils olive-oils extra-virgin-olive-oils virgin-olive-oils sunflower-oils
    rapeseed-oils canola-oils coconut-oils nut-oils walnut-oils sesame-oils avocado-oils cereal-oils pumpkin-seed-oils
X07 ~oilseed-purees peanut-butters nut-butters almond-butters crunchy-peanut-butters tahini legume-butters
X08 chocolate-spreads hazelnut-spreads cocoa-and-hazelnuts-spreads milk-jams chestnut-spreads caramel-spreads
X09 ~cocoa-and-chocolate-powders instant-chocolate-powders
X10 iced-teas peach-flavored-iced-teas
X11 ~dietary-supplements vitamins vitamin-supplements vitamin-and-mineral-supplements multivitamin-and-mineral-supplements
    mineral-supplements vitamin-d-supplements spirulina spirulina-supplements flavoured-dietary-supplements royal-jelly
    honey-and-royal-jelly-mixtures supplements
"""

# Baby products: only baby categories. Tags that say "this is for babies":
BABY_CONTEXT = {
    "baby-foods", "baby-milks", "snacks-and-desserts-for-babies", "main-meals-for-babies", "infant-formulas",
    "cereals-for-babies", "baby-fruit-desserts", "baby-dishes", "dairy-dessert-for-baby", "biscuits-for-babies",
    "baby-drinks", "baby-milks-in-powder", "baby-follow-on-milk-from-5-months", "evening-meals-for-babies",
    "meat-menus-for-babies", "ready-to-feed-baby-milks", "baby-formula", "from-4-months", "from-6-months",
    "from-8-months", "from-10-months", "from-12-months-old", "from-18-months",
}
BABY = {  # specific baby tags (strong)
    "cereals-for-babies": "9002", "baby-fruit-desserts": "9004", "main-meals-for-babies": "9008",
    "baby-dishes": "9008", "evening-meals-for-babies": "9008", "meat-menus-for-babies": "9008",
    "dairy-dessert-for-baby": "9010", "biscuits-for-babies": "9012",
    "ready-to-feed-baby-milks": "9402", "baby-milks-in-powder": "9404",
    "baby-milks": "FORMULA", "infant-formulas": "FORMULA", "baby-formula": "FORMULA",
    "baby-follow-on-milk-from-5-months": "FORMULA",
}
BABY_FROM = [  # normal label -> baby category, by code prefix (first match wins)
    (("64", "68"), "9006"), (("60",), "9004"), (("1820", "1822", "1904"), "9010"), (("70",), "9202"),
    (("7704", "7802"), "9204"), (("4602", "4604", "4802", "4804"), "9002"), (("5504", "5202", "5402"), "9012"),
    (("30", "31", "32"), "9008"),
]
NON_FOOD = {
    "non-food-products", "open-beauty-facts", "open-products-facts", "non-open-products-facts", "open-pet-food-facts",
    "dog-and-cat-food", "cat-food", "hair", "hygiene", "home-garden", "shampoos", "soaps", "deodorants", "toothpastes",
    "perfumes", "body", "face", "suncare", "sunscreen", "in-sun-protections", "health-beauty", "household-supplies",
    "baby-wipes", "incorrect-product-type", "oil-perfumes",
}
BLOCK = {"fresh-cheeses", "fermented-milk-drinks", "dairy-drinks", "soured-milks", "milk-powders"}


def parse():
    """-> {tag: (code, strong: bool)}; raises on a tag listed twice."""
    out, code = {}, None
    for line in MAP.strip().splitlines():
        parts = line.split()
        if not parts:
            continue
        if not line[0].isspace():
            code, parts = parts[0], parts[1:]
        for t in parts:
            strong = not t.startswith("~")
            t = t.lstrip("~")
            if t in out:
                raise ValueError(f"tag listed twice: {t} ({out[t][0]} and {code})")
            out[t] = (code, strong)
    return out


TAGS = parse()


def _baby(code, tags, kcal):
    for t in tags:
        b = BABY.get(t)
        if b == "FORMULA":
            return "9404"  # powder unless tagged ready-to-feed: OFF often stores prepared values, so kcal can't tell
        if b:
            return b
    if code:
        for prefixes, baby in BABY_FROM:
            if code.startswith(prefixes) and not code.startswith("9"):
                return baby
    return None


def ancestors(tag_lists, min_share=0.9):
    """Learn the tag tree from products: {tag: set of its parent tags}, mapped tags only.
    tag_lists: iterable of OFF category tag lists (with "en:")."""
    import collections
    n, pair = collections.Counter(), collections.Counter()
    for tags in tag_lists:
        m = [t[3:] for t in tags or () if t.startswith("en:") and t[3:] in TAGS]
        n.update(m)
        for a in m:
            for b in m:
                if a != b:
                    pair[a, b] += 1
    anc = collections.defaultdict(set)
    for (a, b), k in pair.items():
        if n[a] > n[b] and k >= min_share * n[b]:  # a is on (almost) every product of b -> a is b's parent
            anc[b].add(a)
    return dict(anc), dict(n)


def label(tags, anc, kcal=None):
    """tags: OFF category tags of one product (with "en:"); anc: from ancestors(); kcal: energy per 100 g.
    -> (code or None, reason). The nutrient-family rules are applied by the caller."""
    short = [t[3:] for t in tags if t.startswith("en:")]
    if any(t in NON_FOOD for t in short):
        return None, "non-food"
    mapped = [t for t in short if t in TAGS]
    parents = set().union(*(anc.get(t, ()) for t in mapped)) if mapped else set()
    leaves = [t for t in mapped if t not in parents]
    strong = {TAGS[t][0] for t in leaves if TAGS[t][1]}
    weak = {TAGS[t][0] for t in leaves if not TAGS[t][1]}
    code, reason = None, "unmapped"
    if len(strong) > 1:
        return None, "conflict"
    if strong:
        code, reason = strong.pop(), "strong"
    elif any(t in BLOCK for t in short):
        reason = "blocked"
    elif len(weak) > 1:
        return None, "conflict"
    elif weak:
        code, reason = weak.pop(), "weak"
    if any(t in BABY_CONTEXT for t in short):
        b = _baby(code, short, kcal)
        return (b, "baby") if b else (None, "baby-unclear")
    return (code, reason) if code else (None, reason)
