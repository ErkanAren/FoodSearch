# Stage 05: best free, non-generative model for assigning the 183 food categories

**Why:** every product needs one category (`docs/CATEGORIES.md`). Owner's constraints (2026-11-16/17): **no generative AI at all** (not even free local LLMs); run on this Mac first; start with 200 products; downloads up to ~6 GB are OK.
**Script:** `bench.py` (`run`, `score`). Models were fetched with `fetch_models.sh` (resumable curl), because the Hugging Face client's download hung for 2 h.
**Answer page:** http://127.0.0.1:8765/category-review. **Icon preview:** http://127.0.0.1:8765/icons

## Set-up

- **Sample:** 200 OpenNutrition products, fixed pseudo-random: 150 packaged + 17 everyday + 17 prepared + 16 restaurant. Product text = name + first sentence of the description.
- **Labelled foods** (training and test data, no human work):
  - USDA's 5,344 FNDDS foods with their WWEIA category;
  - plus 1,090 example phrases from our definitions (`CATEGORY-DEFINITIONS.md`), which also cover the X01–X11 additions;
  - since Result 3, also Open Food Facts products labelled by their tags. The training set in use is defined in `trainset.py`: set D since Result 7.
- **Methods per model:**
  - `zs`: zero-shot, nearest category description;
  - `knn`: the 10 nearest labelled foods vote;
  - `lr`: logistic regression on the labelled foods.
- **Same for every model:**
  - the deterministic nutrient rules (milk fat, cereal sugar > 21.2 g, diet drinks ≤ 1 g sugar);
  - never a survey-only category.
- **Models** (all free, MIT / Apache-2.0, ≈ 7.5 GB on disk in `work/models/`):

  | Key | Model | Size |
  |---|---|---|
  | `e5-small` | intfloat/multilingual-e5-small | 0.5 GB |
  | `qwen3-0.6b` | Qwen/Qwen3-Embedding-0.6B | 1.2 GB |
  | `e5-large-instruct` | intfloat/multilingual-e5-large-instruct | 1.1 GB |
  | `bge-m3` | BAAI/bge-m3 | 2.1 GB |
  | `arctic-l-v2` | Snowflake/snowflake-arctic-embed-l-v2.0 | 2.1 GB |

## Result 1: USDA foods (5-fold cross-validation, top-1 accuracy, 2026-11-17)

| Model | Zero-shot | kNN | **Classifier** | Products / s (M2 Max, GPU) |
|---|---|---|---|---|
| **arctic-l-v2** | **57.9 %** | **85.0 %** | **90.4 %** | **229** |
| bge-m3 | 49.4 % | 82.3 % | 88.5 % | 195 |
| qwen3-0.6b | 43.9 % | 82.0 % | 87.3 % | 71 |
| e5-small | 47.8 % | 80.2 % | 85.6 % | 208 |
| e5-large-instruct | 52.7 % | 83.7 % | 85.5 % | 165 |

- **The classifier always beats zero-shot by 30–40 points:** matching a product to a category *description* does not work well; learning from labelled foods does.
- **Arctic-embed-l-v2 is best on every method,** and also the fastest. All ≈ 327k products would take ≈ 25 min on this Mac.
- **Caveat:** USDA foods are generic, English, US foods. The real test is the owner's answers on the 200 sample products (mostly packaged), which is pending.
- **Bug fixed during the run:** e5-large-instruct returns float16 embeddings, which overflowed in the kNN weights (0 % at first). Embeddings are now cast to float32 and the weights shifted. Results of the other models are unchanged.

## Result 2: answers on the 200 products (2026-11-17)

**Who made the answer key:** 9 by the owner, 191 by Claude on the owner's request.
- Claude's answers follow `CATEGORY-DEFINITIONS.md`, made without looking at the model suggestions.
- 19 are marked "unsure" with the reason. They're listed in `out/answers_by_claude.json` and shown on the review page (filter "Claude was unsure").
- The owner can change any of them; the scores then update.

| Model | Method | **Top-1** | Top-3 | Packaged top-1 | (USDA CV) | Products / s |
|---|---|---|---|---|---|---|
| **qwen3-0.6b** | classifier | **61.0 %** | **83.0 %** | 59.3 % | 87.3 % | 71 |
| **arctic-l-v2** | kNN | 60.0 % | 73.5 % | 60.0 % | 85.0 % | 229 |
| qwen3-0.6b | kNN | 58.5 % | 82.0 % | 56.0 % | 82.0 % | 71 |
| e5-large-instruct | classifier | 57.5 % | 79.0 % | 55.3 % | 85.5 % | 165 |
| bge-m3 | kNN | 54.5 % | 74.5 % | 54.7 % | 82.3 % | 195 |
| arctic-l-v2 | classifier | 53.5 % | 75.5 % | 51.3 % | 90.4 % | 229 |
| best zero-shot (arctic-l-v2) | zero-shot | 42.5 % | 68.5 % | 37.3 % | 57.9 % | 229 |

- **On real products the models score ≈ 60 %, not ≈ 90 %.** The USDA test was optimistic: those are generic foods, written the same way as the training data. Our products are branded, packaged and named differently.
- **The right answer is in the top 3 for 83 %** (qwen3 classifier).
- **Typical errors:**
  - categories with few training examples: iodized salt → *Saltine crackers*; olive oil → *Liquor and cocktails*, because X03 and X06 have only a handful of example phrases;
  - near neighbours: sausage sandwich → BBQ sandwiches; fried rice → rice dishes; chocolate sorbet → ice cream; kefir → Greek yogurt;
  - brand noise in names ("Sta St Harv Evoo by Star").
- **By type (qwen3 classifier):** packaged 89 / 150, everyday 11 / 17, prepared 10 / 17, restaurant 12 / 16.
- **Hot sauce (decided by the owner):** 8406 *Mustard and other condiments*, as in USDA. The owner's answer was changed from 8412, and 8412 now lists hot sauce under "not here". Scores above are after this change.

## Result 3: plus real packaged products as training data (2026-11-17)

**What changed:** the models also learn from **29,460 real packaged products**, up to 200 per category.
- The products are labelled through their Open Food Facts category tags with a hand-written mapping of 1,569 tags (`tools/categories/off_map.py`, coverage in `docs/OFF-CATEGORY-MAPPING.md`).
- The mapping labels 1.39 M of the 1.97 M OFF products that have tags. Products with contradictory tags (38.8k) are skipped, not guessed.
- Script: `build_off_train.py`, then `bench.py run --off --no-cv`. Embedding the 35.9k labelled foods took 5 min (Qwen3) and 1.3 min (Arctic); each classifier trained in under 20 s.
- **Still no OFF examples for 9 categories:** stir-fry, nachos, breakfast sandwiches, PB&J, BBQ sandwiches, grits, saltines, mixed baby food, ready-to-feed formula.

| Model | Method | **Top-1** | Top-3 | Packaged top-1 | Before (Result 2) |
|---|---|---|---|---|---|
| **qwen3-0.6b + OFF** | classifier | **65.0 %** | **85.5 %** | 62.7 % | 61.0 % / 83.0 % |
| qwen3-0.6b + OFF | kNN | 63.5 % | 81.5 % | 62.7 % | 58.5 % |
| arctic-l-v2 + OFF | kNN | 62.0 % | 76.0 % | 62.7 % | 60.0 % |
| arctic-l-v2 + OFF | classifier | 61.0 % | 78.0 % | 59.3 % | 53.5 % |
| **3-model vote** (qwen3 classifier + qwen3 kNN + arctic kNN) | rank vote | **69.5 %** | 87.5 % | | |

- **+4 points for the best single model.** 29 products were fixed and 21 broke, so the gain is real but small for 200 test products.
- **Removing "by Brand" from names did not help** (65.0 % either way). The models already ignore it.
- **The vote is the best so far, at ≈ 70 %.** Caveat: the combination was picked on these same 200 products, so the true number is probably a little lower.
- **Agreement is a usable confidence signal:**
  - when Qwen3 (classifier) and Arctic (kNN) give the same answer, which happens for 62 % of products, they are right **85 %** of the time;
  - when all three agree (56 % of products), they are right **88 %** of the time.
- **Remaining errors:**
  - close neighbours: frozen yogurt → yogurt, ricotta → cream cheese, breakfast burrito → burritos, broth → stock;
  - mixes and kits: muffin mix → muffins, drink mix → juice;
  - short or odd names: "Pecan Halves" → peaches, "Sta St Harv Evoo" → oatmeal, "Root Beer" → sugar.

## Result 4: which product text? (2026-11-17, owner's request, no new training)

Same models and training data as Result 3; only the text of the 200 products changes (`text_variants.py`).
- **title:** the name.
- **title+desc:** name + first sentence of the description (the text used so far).
- **title+desc+ingr:** the same + `Ingredients of this product: <list>`, cut at a comma near 300 characters. 179 of the 200 products have ingredients; packaged products almost never have a description (2 / 150).

| Model / method | title | title+desc | title+desc+ingr | Packaged: desc → +ingr | Other 50: desc → +ingr |
|---|---|---|---|---|---|
| qwen3 classifier | 63.0 % | **65.0 %** | **65.0 %** | 62.7 → 60.7 % | 72 → **78 %** |
| qwen3 kNN | 63.5 % | 63.5 % | 63.5 % | 62.7 → 62.7 % | 66 → 66 % |
| arctic kNN | 58.5 % | 62.0 % | **65.5 %** | 62.7 → **68.7 %** | 60 → 56 % |
| arctic classifier | 55.0 % | 51.5 % | 58.5 % | 47.3 → 56.7 % | 64 → 64 % |
| **3-model vote** | 67.5 % | **69.5 %** | **69.5 %** | 68.0 → 68.7 % | 74 → 72 % |

- **The description helps** prepared, restaurant and everyday foods: qwen3 classifier 62 → 72 % on those 50 products. It doesn't matter for packaged products, which have none.
- **Ingredients: no gain overall for the best set-up** (the vote stays at 69.5 %; qwen3 classifier at 65 %). They help some models and products and hurt others, by 1–9 products of 200:
  - **Arctic kNN on packaged products gains the most:** +9 products.
  - **qwen3 classifier on packaged products loses** 3.
  - Some of these moves are within noise for 200 products.
- **Caveat:** the training examples are names only, so with ingredients the test text no longer looks like the training text. Adding ingredients to the training examples too might change this, but that needs new training.
- **Owner's concern partly confirmed:** ingredients don't make it fail worse overall, but they don't clearly help either.

## Result 5: plus Greek product names (2026-11-18, owner's request)

**Why:** in the live tester, "Κουλούρι κανέλας" (cinnamon koulouri, Greek name only) came out as corn / Greek yogurt / pineapple. The models had learned only from English names, so they matched Greek words by look and sound ("Kukuruz", "Ananas kolutovi").

**What changed:** `build_off_train.py` also keeps up to 200 products per category with a **Greek name**, labelled by the same OFF tag mapping: **1,311 Greek examples in 115 categories**. The English examples are unchanged (byte-identical).
- **Greek test set:** one Greek name in ten (fixed by a hash of the name) is never trained on. From that tenth, the **98 products with only a Greek name** form the test (`out/greek_test.json`).
- **Caveat:** their answers come from OFF tags, not from a person. Script: `eval_greek.py` (same models, trained without and with the Greek examples).

| Model / method | Greek-only products: English names only | **+ Greek names** |
|---|---|---|
| **3-model vote** | 12.2 % (top-3 39.8 %) | **69.4 % (80.6 %)** |
| Qwen3 classifier | 11.2 % (22.4 %) | 59.2 % (72.4 %) |
| Qwen3 kNN | 8.2 % (23.5 %) | 66.3 % (78.6 %) |
| Arctic kNN | 30.6 % (45.9 %) | 67.3 % (81.6 %) |
| Arctic classifier | 21.4 % (34.7 %) | 55.1 % (73.5 %) |

- **Greek-only products went from almost always wrong to ≈ 70 % right**, about the level of English products. The vote fixed 57 and broke 1.
- **Agreement still works as confidence:** all 3 agree on 56 of the 98, and then they are right 91 % of the time (before: 7 products).
- **The 200 English test products did not get worse:** the vote stays at 69.5 % top-1 and 87.5 % top-3 (title + description). Qwen3 classifier alone: 65.0 → 63.0 % (4 products, within noise). Predictions before this change: `out/text_variants_before_greek.json`.
- **The owner's example improved but is not solved:** "Κουλούρι κανέλας" → 5504 *Cookies and brownies*, with low confidence (2 of 3 agree). "Κουλούρι Θεσσαλονίκης" (a bread ring) → also cookies, which is wrong. The training data has many κουλουράκια (cookies) but only 3 tagged koulouri breads.
- **Label problem found:** 63 of the 94 Greek strained yogurts (στραγγιστό) carry only the OFF tag "yogurts", so the mapping labels them *Yogurt, regular* (1820) instead of *Yogurt, Greek* (1822). This affects training and the Greek test alike.

## Result 6: label straight from Open Food Facts tags, no model? (2026-11-18, owner's request)

**Idea:** a catalogue product that is in Open Food Facts (OFF) with clear category tags gets its category from the tag mapping (`tools/categories/off_map.py` + the nutrient rules), with no model. Script: `tag_shortcut.py` (24 s) → `out/tag_labels.json`.

**Accuracy on the 150 packaged test products** (the 50 others have no barcode):

| Tag outcome | Products | Tags right | Vote right (same products) |
|---|---|---|---|
| **Strong tag** (a specific tag, e.g. "cheddar-cheese") | 20 | **18 (90 %)** | 13 (65 %) |
| Weak tag only (a general one, e.g. "cheeses", "yogurts") | 27 | 16 (59 %) | 17 (63 %) |
| Only broad tags ("snacks", "sauces"…), unmapped | 84 | — | 59 (70 %) |
| In OFF but no tags | 19 | — | 14 (74 %) |

- **Strong tags beat the models** (90 % vs 65 %). Using them first, then the vote: **72.0 %** on the 200 vs 69.5 % for the vote alone (+5 products). Caveat: only 20 products.
- **Weak tags are no better than the models.** Most of their errors are fixable details: Greek yogurts tagged only "yogurts" (3), ricotta and Neufchâtel tagged only "cheeses" (2), a zero-sugar soda (OFF had no sugar value), sparkling water mapped to bottled water.

**Coverage of the catalogue:**

| | Products | Strong tag | Weak tag | Broad tags only | No tags | No barcode |
|---|---|---|---|---|---|---|
| OpenNutrition | 326,759 | 57,427 (18 %) | 61,021 (19 %) | 153,196 (47 %) | 40,180 (12 %) | 13,317 (4 %, all non-packaged) |
| Greek-market OFF | 26,654 | 6,340 (24 %) | 2,092 (8 %) | 2,319 (9 %) | 15,608 (59 %) | — |

- **Almost every packaged OpenNutrition product is in OFF** (313k of 313k barcodes), but **only 18 % have a tag specific enough** to trust.
- **Mapping more tags won't help much:** the 153k "unmapped" products carry only broad tags (snacks 26k, "undefined" 31k, confectioneries 11k, sauces 9k, frozen desserts 8k…). 50 tags cover 98 % of them, and none of them alone picks one of our 183 categories.
- **But broad tags can narrow the choice:** "confectioneries" rules out everything except candy, "sauces" everything except sauces and condiments. Used as a filter on the models' answers, they could fix errors like "Pecan Halves" → peaches. Not tested yet; needs no retraining.

## Result 7: retrain with more and cleaner examples (2026-11-18, owner's request)

**What changed.** The training examples are built by `build_off_train.py`, and the training sets are defined in `trainset.py`. Script: `retrain.py` (88 min the first time, mostly embedding 143k new texts per model; texts are cached per model in `out/store_*`).

Two fixes, in every set below:
- **Strained-yogurt rule.** OFF yogurts whose name says Greek, strained, skyr, labneh, στραγγιστό or ελληνικό are now labelled 1822 *Yogurt, Greek* instead of 1820 (2,033 products).
- **Egg and breakfast sandwiches.** The OFF tags "egg-sandwiches" and "breakfast-sandwich" now map to 3706 (1,571 mapped tags).

Each training set adds one change to the set before it:

| Set | Change | Labelled foods |
|---|---|---|
| A | as before: up to 200 OFF products per category | 37,244 |
| B | up to **1,000** per category: 108,240 English names in 171 categories, plus 1,307 Greek names in 115 | 115,981 |
| C | **+ ingredients**: the 60 % of examples that have them appear a second time as "name. Ingredients of this product: …", the same form as the test text | 181,809 |
| D | **+ automatic cleaning**: drop an OFF example when, for both models, at most 1 of its 10 nearest labelled foods shares its category and at least 6 agree on one other category. 2,456 of 109,547 dropped (2.2 %) | 177,875 |

**Top-1 accuracy (top-3 in brackets).** The 200 test products use the answer key. The Greek column uses the 98 Greek-only products, whose answers come from OFF tags.

| Set | Vote, title + description | **Vote, + ingredients** | Qwen3 classifier, + ingredients | Arctic classifier, + ingredients | Greek-only, vote |
|---|---|---|---|---|---|
| A | 69.0 % (87.5 %) | 69.5 % (86.5 %) | 65.5 % | 55.0 % | **68.4 %** (79.6 %) |
| B | 68.5 % (83.5 %) | 67.5 % (86.0 %) | 64.0 % | 60.5 % | 64.3 % (82.7 %) |
| C | 69.5 % (84.0 %) | **72.0 % (88.5 %)** | **71.5 %** | **68.5 %** | 62.2 % (83.7 %) |
| **D (adopted)** | 69.0 % (85.5 %) | **72.0 % (88.5 %)** | 71.0 % | 67.5 % | 63.3 % (82.7 %) |

**Findings**
- **The vote on names + descriptions did not move.** It was 68.5–69.5 % in all four sets. Product by product, each set fixed about as many products as it broke (D vs A: 12 fixed, 12 broken).
- **Ingredients in the training text help, once the products' ingredients are used too.**
  - With the ingredients in the product text, the vote went from 69.5 % to **72.0 %** (top-3 86.5 → 88.5 %).
  - The Qwen3 classifier went from 65.5 to 71.0 %, and the Arctic classifier from 55.0 to 67.5 %.
  - This answers the caveat in Result 4: ingredients didn't help before because the training examples had none.
  - It matters for the catalogue: **95 % of OpenNutrition products have ingredients** (all packaged, prepared and restaurant items, none of the 5,299 everyday foods), and so do 179 of the 200 test products.
- **More examples alone (B) didn't help.** Single models gained a little on names: Qwen3 classifier 64.5 → 67 %. The vote didn't, and with ingredients B is slightly worse than A.
- **The "all 3 agree" group grew and stayed reliable** (with ingredients, A → D):
  - all 3 agree on 109 → **123** of the 200 products, and are right 91 % → 89 % of the time;
  - with title + description only: 113 → 117 products, right 87 % → 91 %.
- **Cleaning had no measurable effect** (C vs D: within 2 products on every test). It is kept because what it drops is mostly real tag errors:
  - real errors: dark chocolate tagged *plant-based milk*, smoked hake fillets tagged *cookies*, panko tagged *apples*, SKYR tagged *plant-based yogurt*;
  - debatable: granola sugar level, Navarin d'agneau.
  - All dropped examples are in `out/clean_drop.json`. The label dropped most was X11 *Vitamins and supplements* (91).
- **Strained yogurts now come out as 1822.** That is all 4 Greek or strained yogurts in the 200, and 4 of the 5 in the Greek test that the tags call Greek. The one missed, "Γιαούρτι 2%", doesn't say strained in its name.
- **The breakfast-sandwich tags didn't fix the breakfast burrito.** "Egg, Cheese & Uncured Bacon Breakfast Burrito" still comes out as *Burritos and tacos*, which is arguably also right.
- **Strong OFF tags vs the models:** on the 20 test products with a strong tag, the vote is now right on 15 (was 13); the tags are right on 18.
- **Greek-only products may have got worse:** 68.4 → 63.3 % top-1 (D vs A: 2 fixed, 7 broken). Top-3 improved, 79.6 → 82.7 %.
  - The likely cause: the 1.3k Greek examples now sit among 110k English ones instead of 29k. The classifiers lose most (Arctic classifier 53 → 45 %), while Arctic kNN improves (64 → 67 %).
  - It's not conclusive: 9 products changed, and the answers come from tags. A sign test gives p ≈ 0.18.
- **Other vote line-ups** (any 3 or all 4 members, any one first) scored 65–73 % on D. The best ones gain 1 product over the current vote. That is noise, and picked on the test itself, so **the vote is unchanged**.
- **Why the vote is stuck: 47 of the 200 are wrong in all four sets.** More examples don't fix these. They are mostly:
  - neighbouring categories: cream- vs broth-based soup, "other diet drinks" vs diet soft drinks, sorbet vs ice cream, candy vs cookies;
  - names that say very little: "100% Juice", "Blissful by Lyrical Foods", " by Woodstock".
- **The 200-product test is now the limit.** A difference under ≈ 5 points (10 products) can't be told from noise. Further tuning needs a bigger test set.

**Adopted: set D** (`trainset.CURRENT`). It ties A on names and is the best with ingredients, which almost the whole catalogue has. It also has the most products where all 3 models agree, and it has cleaner labels. The live tester and the results page now use it. The predictions are in `out/retrain.json` and, for the results page, `out/text_variants.json`.

## Conclusion so far

- **Best free set-up:** Qwen3-Embedding-0.6B (classifier) as the main model, with Arctic-embed-l-v2 as a second opinion.
  - Since 2026-11-18 (set D), trained on: USDA foods, our definitions, and up to 1,000 OFF-labelled products per category (108k with English names, 1.3k with Greek names), each also with its ingredients when it has them.
  - **≈ 71 % alone and 72 % as a vote, with name + description + ingredients.** 88.5 % of the time, the right answer is in the vote's top 3.
  - **≈ 89 % right where all 3 models agree**, which is ≈ 60 % of products.
- **Not good enough to run unattended on everything.** It may be good enough for "accept when the models agree, look again at the rest".
- **More training data no longer moves the vote.** The remaining errors are mostly neighbouring categories and names that say little. And the 200-product test can't show gains smaller than ≈ 5 points.

**Possible next steps (no LLM, free), owner to choose:**
1. **A bigger test set.** Use a few thousand OpenNutrition products whose OFF tags are strong (≈ 90 % right, 57k available) and that are not in the training data. That would show 1–2 point differences, which the 200 can't. It's needed before any more tuning.
2. **Decide the workflow:** auto-accept when all 3 models agree (≈ 60 % of products, ≈ 89 % right), and send the rest to review or a second pass.
3. **Strong OFF tags first:** for the products that have one (18 % of OpenNutrition, ≈ 90 % right), as measured in Result 6. Weak tags are no better than the models.
4. **Broad OFF tags as a filter** on the models' choices, e.g. "confectioneries" → candy categories only. This covers the 153k products with only broad tags. No retraining needed; measurable on the 84 such test products.
5. **More nutrient rules for neighbouring categories**, e.g. cream- vs broth-based soups by fat.
6. **Rebalance the Greek examples** (give the 1.3k Greek names more weight in the classifiers), if the Greek drop in Result 7 is confirmed.

**Live pages:**
- results on the 200 products: http://127.0.0.1:8765/category-results
- live tester: http://127.0.0.1:8765/category-test (needs `serve_models.py` running)
