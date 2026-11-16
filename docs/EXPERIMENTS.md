# Experiments Log

One card per experiment. Write the **hypothesis before running**, then fill in the result and the **decision** it led to. Link results back to the KR they move (`OKRs.md`).

**Status:** ✅ done · 🔄 running · ⬜ planned · ❌ abandoned

| ID | Experiment | KR | Status |
|---|---|---|---|
| E0 | Profile both raw datasets | KR1.2, KR1.3 | ✅ |
| E1 | Slim extract (columns + basic filters) | KR2.1 | ⬜ |
| E2 | OFF serving double-scaling: size & recovery | KR2.2, KR2.5 | ⬜ |
| E3 | Carb definition classifier (total vs available) | KR2.3 | ⬜ |
| E4 | OFF ↔ OpenNutrition agreement on shared barcodes | KR2.5 | ⬜ |
| E5 | Greek-market subset deep-dive | KR3.1, KR3.2 | ⬜ |
| E6 | Generic-food base selection | KR3.3 | ⬜ |
| E7 | Portions / household measures | KR3.3 | ⬜ |
| E8 | Server search index (SQLite FTS5): size + speed | KR4.1, KR4.2 | 🔄 (laptop numbers done) |
| E9 | Greek / Greeklish search normalization | KR3.5 | ⬜ |
| E10 | Manual audit of 200 items | KR2.5 | ⬜ |
| E11 | OFF photo clean-up pilot (background removal) | KR5.1, KR5.2 | ✅ (31 % good, no-go) |
| E12 | AI image pilot for generic foods & Greek dishes | KR5.3, KR5.4 | ⬜ |
| E13 | Category icons for foods without a picture | KR5.5 | ⬜ |
| E14 | Product crop with OFF's ready-made models | KR5.1, KR5.2 | 🔄 |
| E15 | Hybrid search: BM25 + semantic (embeddings) | KR3.5, KR4.1 | 🔄 (results in: +3 points, gate not met; decision pending) |
| E16 | Greek queries on English-only products: offline Greek index vs query translation | KR3.5, KR4.1 | ✅ results in (offline word index wins); decision pending |

---

## E0: Profile both raw datasets ✅
- **Question:** What is in each file, how complete is it, and what is broken?
- **Method:** pyarrow row-group scan of `food.parquet` (columns: code, countries, names, nutriments, nutrition_data_per, quality tags, scans) and a csv/json scan of the OpenNutrition TSV. About 2 min in total.
- **Result:** see `DATASETS.md`. Headlines:
  - OFF 4.9 M products. 70 % have core nutrients, 64.5 % pass basic checks, fiber only 38 %.
  - Greek market ≈ 29 k products (18.8 k with core nutrients), only 4.9 k with a Greek name.
  - OpenNutrition grocery barcodes are 99.99 % OFF. Its real value is 5.3 k everyday + 3.8 k prepared + 4.2 k restaurant foods, with portions and synonyms.
  - The carb definition differs by region (Q-01). Some OFF per-serving rows are double-scaled (Q-02).
- **Decision:** OFF is the primary packaged source. OpenNutrition depends on D-1. Carb normalization is mandatory.

---

## E1: Slim extract ⬜
- **Hypothesis:** Keeping ~20 columns and flattening `nutriments` into ~12 nutrient columns shrinks 8 GB to **< 500 MB** (world) and **< 5 MB** (Greek union) and makes every later step take seconds.
- **Method:** DuckDB `COPY (SELECT … FROM 'food.parquet' WHERE …) TO 'work/off_slim.parquet'`. Unnest `nutriments` and pivot on `name` IN ('energy-kcal','carbohydrates','sugars','fiber','proteins','fat','saturated-fat','salt','sodium','polyols','alcohol','starch'). Filters: has name OR barcode, has ≥ 1 nutrient.
- **Metrics:** rows in/out, file size, runtime.
- **Result:** _TBD_
- **Decision:** _TBD_

## E2: OFF serving double-scaling ⬜
- **Hypothesis:** Rows with `nutrition_data_per = serving` where `100g ≈ value × 100 / serving_quantity` **and** the as-entered `value` passes all per-100 g rules (energy fit within 15 %) were really per-100 g. Using `value` as per-100 g recovers ≥ 80 % of them correctly.
- **Method:** On the serving rows, compute the energy fit for both interpretations (`value` as per-100 g vs `100g`) and pick the one that fits. Spot-check 50 against product photos (OFF image URLs).
- **Metrics:** % of serving rows affected (overall, US, GR), recovery precision on the 50-item check.
- **Result:** _TBD_
- **Decision:** recover · flag only · drop

## E3: Carb definition classifier ⬜
- **Hypothesis:** The country of sale + GS1 prefix classifies `total` vs `available` correctly for ≥ 98 % of rows. An **energy fit** confirms it: for `available` rows, `4·C + 2·Fib + 4·P + 9·F` fits kcal better than `4·C + 4·P + 9·F` (and the other way round for `total`).
- **Method:** Label by rule, then compare the energy residuals of both formulas on rows with fiber ≥ 3 g. Look at disagreements.
- **Metrics:** agreement rate; % of rows still `carb_def_unknown`.
- **Result:** _TBD_
- **Decision:** _TBD_

## E4: OFF ↔ OpenNutrition agreement ⬜
- **Hypothesis:** For the 313 k shared barcodes, kcal/carbs agree within ±5 % for ≥ 90 %. Where they disagree, OpenNutrition may have fixed OFF errors (it is "cleaned").
- **Method:** Join on normalized GTIN-13 and compare the core 4. For disagreements, check which side passes the validation rules.
- **Metrics:** agreement %; for disagreements, which source passes the rules more often.
- **Result:** _TBD_
- **Decision:** Is OpenNutrition grocery worth anything as a fixer?

## E5: Greek-market subset deep-dive ⬜
- **Question:** Which brands, categories and supermarkets are covered? What's missing (e.g. Greek bakery, dairy brands like ΦΑΓΕ, ΔΕΛΤΑ, ΜΕΒΓΑΛ…)?
- **Method:** Group the Greek union by brand, food group, store (`stores_tags`), name language. Compare against a list of the top 100 Greek supermarket brands.
- **Metrics:** brand coverage %, name language mix, % passing validation.
- **Result:** _TBD_

## E6: Generic-food base selection ⬜
- **Question:** Which source gives the best ~1,000 generic foods for Greek users, given the licensing decision D-1?
- **Candidates:** OpenNutrition `everyday` (5,299, with portions + synonyms) · USDA FoodData Central (CC0) · CIQUAL (FR, Etalab) · (Greek composition tables, check license).
- **Method:** Take 100 typical Greek-diet foods (ψωμί, φέτα, ελαιόλαδο, φακές, ρύζι, πατάτες, γιαούρτι, μέλι…) and check presence, portion availability and carbs value spread across sources.
- **Metrics:** hit rate per source, effort to add Greek names.
- **Result:** _TBD_

## E7: Portions / household measures ⬜
- **Hypothesis:** ≥ 60 % of OFF `serving_size` strings parse into grams with simple regexes ("30 g", "1 cup (240 ml)", "2 biscuits (25g)").
- **Method:** Regex parser + unit table (g, ml, oz, fl oz, cup…). Measure the parse rate. Also map OpenNutrition `serving.metric` directly.
- **Metrics:** parse rate (world, GR); % of foods with ≥ 1 portion.
- **Result:** _TBD_

## E8: Server search index (SQLite FTS5) 🔄
- **Changed 2026-11-13:** all code now runs on our backend and the app is online-only, so this is no longer about fitting a Greek subset into the APK. The new question: is SQLite FTS5 on the server fast and small enough that we don't need a separate search engine?
- **Hypothesis:** An FTS5 index over all products answers a query in < 10 ms and rebuilds in < 1 min.
- **Method:** FTS5 (`unicode61`, diacritics removed, prefix indexes for 2 and 3 letters) over the text already normalized by `norm()`. Time the build, single inserts and queries. Compare with the browser's old LIKE scan.
- **Metrics:** build seconds, MB, ms per query (mean / p95), ms per insert.
- **Result (2026-11-13, this Mac, not yet the server):**
  - All 353,413 products (OFF Greece + all OpenNutrition): **build 2.1 s, 68 MB.** Inserting one new product takes 0.7 ms, and it's searchable immediately.
  - Queries: **0.3–1.0 ms**, vs 270–790 ms for the old LIKE scan on the 326 k OpenNutrition table (≈ 1,000× faster).
  - Library-sized corpus (39,971 items, search lab): mean 0.5 ms, p95 1.5 ms.
  - Browser rebuild with one FTS5 index per tab: 68 s in total. The DB grew from ~850 to 957 MB.
- **Decision:** FTS5 + BM25 is the keyword half of search. The browser was switched on 2026-11-13. Still to measure: the real server, under concurrent load.

## E9: Greek / Greeklish search normalization ⬜
- **Hypothesis:** Accent stripping + final-sigma folding + a Greeklish → Greek transliteration index raises top-5 hit rate on a 100-query set by ≥ 20 points vs a plain FTS.
- **Method:** Build the query set (real user-style queries: "fakes", "giaourti", "spanakopita", "σπανακοπιτα"). Compare plain vs normalized index.
- **Metrics:** top-1 / top-5 hit rate.
- **Note (2026-11-13):** the query set now exists (`tools/search/queries.json`, see E15), and accent stripping + final-sigma folding are already in `norm()`. With BM25 alone, **Greeklish queries already reach 87 % hit@5 (13 of 15)**, because many Greek OFF products are named in Greeklish ("Giaourti", "Mousakas", "Fakes psiles", "Psomi Sitou"). The +20-point hypothesis can't hold on this set. Only `rizi` and `patates` still miss. Real user queries may be harder.
- **Result:** _TBD_

## E10: Manual audit ⬜
- **Method:** Random 200 items from the final Greek subset. Compare carbs, kcal and portion against the package photo (OFF images) or the producer's website.
- **Metrics:** % within ±1 g or ±10 % for carbs; error categories.
- **Result:** _TBD_

## E11: OFF photo clean-up pilot ✅
- **Hypothesis:** Open-source background removal turns ≥ 85 % of Greek OFF front photos into clean, catalogue-style 512 px images (white background, centred), good enough for the app list. Automatic flags catch most failures.
- **Method:** `tools/photos/cleanup_pilot.py`. Deterministic sample of **200** Greek products with a front photo (sorted by SHA-1 of the barcode, so it's random-like but repeatable). Download the full photo → rembg → crop / square / white → auto-QA flags. Review before/after in the browser at `/photo-pilot` (good / bad buttons).
- **Metrics:** % rated good, % flagged, flag precision (flagged ∩ bad / flagged), seconds per image, output KB per image.
- **Model choice (8-photo test):** `isnet-general-use` takes 0.9 s per photo but fades or cuts parts of packs. `birefnet-general-lite` takes 6.6 s per photo and gives crisp, complete packs. **Picked birefnet-general-lite.**
- **Result (2026-11-12, automatic part):** 200/200 downloaded and processed. **6.1 s per photo** on this Mac's CPU (p95 7.5 s). Output **30 KB** per 512 px JPEG. **13 auto-flagged** (fragmented 7, soft_edges 5, low_res 4, fg_small 1). Raw downloads 125 MB (≈ 0.6 MB per photo).
- **Result (human review of all 200, 2026-11-12):** **62 good, 138 bad → 31 % good.** Far below the 85 % target. (An earlier rough look at small thumbnails guessed ≈ 87 %. That was wrong: at full size most rejects have real defects.)
  - **Auto-flags are precise but miss almost everything:** 12 of the 13 flagged were bad, but they caught only **12 of 138** bad images (9 %).
  - **Mask metrics can't tell good from bad either:** the best simple rule on fill and soft edges keeps a set that is only 48 % good.
  - Failure types seen at full size:
    1. **Parts of the pack cut away:** a corner, a bite out of the middle, the top of a box.
    2. **The food printed on the pack is cut out instead of the pack** (Doritos chip, granola, pizza, cereal bowl).
    3. **Leftovers kept:** hands, lids, coasters, a second product behind.
    4. **The source photo itself is bad:** product cut off by the photo frame, crumpled or angled packs, dark photos, or the back label / nutrition table uploaded as "front" (contributor error).
- **Scale estimate:** 20,525 front photos × 6.1 s ≈ **35 h** CPU on this Mac (2–3 overnight runs, or faster with GPU / CoreML). ≈ 12 GB of raw downloads, ≈ 600 MB of cleaned output.
- **Ideas to test next (E11b):**
  - Safe fallback: for flagged or rejected images, **don't remove the background**. Just crop and pad the original to the square canvas.
  - Second-opinion flag: also run isnet and flag images where the two masks disagree (low overlap). This should catch most unflagged failures.
  - Prompted segmentation ("product package") with a text-guided detector + SAM, to stop the model from cutting out the food printed on the pack.
  - **Automatic judge** checked against the 200 human verdicts: an image-embedding classifier, or a vision model given the review rules. Auto-accept only the images it is very sure about. The rest get the safe fallback or a human look.
- **Decision (2026-11-12): no-go** for an unattended full run. Keep the **62 approved** images. The 200 verdicts in `work/photo_pilot/review.json` become the **gold set** for scoring the next attempt (E11b) without starting the review from zero.
- **E11b parked (2026-11-12):** too costly to scale for now (≈ 6 s per photo on CPU, plus human review). Ready-made options found on Hugging Face, to try first:
  - [`openfoodfacts/crop-detection`](https://huggingface.co/openfoodfacts/crop-detection) (YOLOv8n, AGPL-3.0): finds the product's edges in an OFF photo. Cropping to that box and padding on white keeps the pack intact, with no background removal. A tiny model, fast on CPU.
  - [`openfoodfacts/front_image_classification`](https://huggingface.co/openfoodfacts/front_image_classification) (YOLO11n, 95 % accuracy, AGPL-3.0): tells a front photo from any other. It catches back labels uploaded as "front".
  - Other background-removal models: BiRefNet full size and BEN2 (both MIT). RMBG-2.0 needs a commercial license from BRIA.
  - There is no ready-made set of clean product photos.
  - AGPL models are fine for offline processing in our pipeline: we ship the resulting photos, not the model.

## E12: AI image pilot ⬜
- **Hypothesis:** One prompt template produces approvable images (right dish, realistic portion, consistent style) for ≥ 80 % of 30 test items (15 Greek dishes + 15 generic foods), at < $0.10 per approved image.
- **Method:** 3 variants per item with one provider, then review with the checklist in `IMAGES.md` §5. Optionally compare 2 providers on the same 30 items.
- **Metrics:** approval rate, portion-mismatch count, cost and time per approved image.
- **Needs:** provider choice + API key.

## E13: Category icons ⬜
- **Hypothesis:** ~20 icons cover ≥ 95 % of Greek OFF products via their first `food_groups_tags` value, plus OpenNutrition types and labels.
- **Method:** Map food groups to icons (Fluent Emoji, MIT) and count unmapped products.
- **Metrics:** coverage %, number of icons needed.

## E14: Product crop with OFF's ready-made models 🔄
- **Hypothesis:** Cropping the original photo to the product (no background removal) never breaks the pack. It gives far more usable images than the E11 cut-out (31 %), and is fast enough to run on all Greek products on this Mac.
- **Method:** `tools/photos/crop_pilot.py`, on the **same 200 products as E11** so the two methods compare photo by photo.
  1. [`openfoodfacts/front_image_classification`](https://huggingface.co/openfoodfacts/front_image_classification) (YOLO11n-cls, ONNX, 6 MB) scores whether the photo is really a front.
  2. [`openfoodfacts/crop-detection`](https://huggingface.co/openfoodfacts/crop-detection) (YOLOv8n, ONNX, 12 MB) finds the product box.
  3. Crop to the box (+ 2 %) and centre it on a 512 × 512 white square (5 % margin).
  - Flags: `no_box`, `not_front` (front score < 50 %), `small_box` (< 15 % of the photo), `low_res`.
  - Review at `/photo-pilot?run=crop`. Each card shows the original, the E11 cut-out with its verdict, and the crop.
- **Metrics:** % rated good; % good with either method (best of E11 and E14); flag precision; seconds per image.
- **Result (2026-11-12, automatic part):** 200/200 processed. **0.08 s per photo** (≈ 75× faster than E11). All 20,525 Greek front photos would take ≈ 30–40 min of processing, plus downloading ≈ 12 GB of photos. 38 KB per image. 20 flagged (`not_front` 16, `low_res` 4, `no_box` 1). **15 of the 16 `not_front` photos were also rated bad in E11**, so the front check looks useful on its own.
- **Result (human review):** _pending_
- **Decision:** _after the review_. If the crop is clearly better than the cut-out, it becomes the default for packaged products, with the `not_front` photos replaced by a category icon or another photo.

## E15: Hybrid search (BM25 + semantic) 🔄
- **Question:** Does adding semantic search (embedding vectors) to BM25 find the right food more often? And is it worth running a model on the server?
- **Hypothesis:** BM25 handles brands, exact names and prefixes. Semantic search adds what BM25 can't reach: Greek queries for foods that only have English names (all of OpenNutrition), synonyms and descriptive queries. A mix of the two raises hit@5 by **≥ 5 points** over BM25 alone, within the latency budget (p95 < 100 ms). The mix is either a weighted sum (starting at 0.25 BM25 / 0.75 semantic, after per-query rescaling) or reciprocal rank fusion (RRF).
- **Setup:** `tools/search/search_lab.py` + `tools/search/queries.json` (commands in the README).
  - **Corpus (39,971 items)**, roughly the future library: OFF Greek market (26,654) + OpenNutrition everyday / prepared / restaurant (13,317). OpenNutrition grocery is left out because those items are OFF barcodes.
  - **Test set: 100 queries in 7 kinds:** Greek generic 20, English generic 20, brand 20, Greek dish 12, Greeklish 15, typo / prefix 8, descriptive 5. Each query describes a correct result with regexes on the product name, so new products count automatically. **A draft written by Claude from the data. It needs a human review plus real user queries, and is likely easier than real traffic.**
  - **+20 queries (2026-11-16), kind `greek_to_english`:** Greek words for foods that exist mostly or only with English names (OpenNutrition), e.g. `καρπουζι` → "Watermelon", `αρνι` → "Lamb Chops". This is the case semantic search is meant to fix. The set now has 120 queries.
  - **Metrics:** hit@1, hit@5 (= KR3.5), MRR@10, ms per query. Semantic timings include embedding the query on the CPU, as on a plain server.
- **Plan:**
  1. ✅ Baseline: old LIKE search vs FTS5 BM25.
  2. ✅ Embed the corpus with `multilingual-e5-small` (cheap baseline) and `Qwen3-Embedding-0.6B`. Score semantic-only.
  3. ✅ Fusion: RRF vs weighted sum, sweeping the BM25 weight from 0 to 1 (including 0.25).
  4. 🔄 Decide (proposal below).
- **Result 1: BM25 baseline (2026-11-13)**

  | Method | hit@1 | hit@5 | MRR@10 | p95 ms |
  |---|---|---|---|---|
  | `like` (old browser search, A→Z) | 61 % | 83 % | 0.71 | 6.6 |
  | `bm25` (FTS5, every word as a prefix) | **83 %** | **91 %** | **0.87** | 1.5 |
  | `bm25_or` (+ any-word fill-up) | 83 % | 91 % | 0.87 | 0.7 |

  - hit@5 by kind for `bm25`: English generic 100 %, brand 100 %, Greek generic 90 %, Greeklish 87 %, Greek dish 83 %, descriptive 80 %, typo / prefix 75 %.
  - The 9 BM25 misses, grouped by what would fix them:
    - **Cross-language** (`ντοματα` → "Tomatoes", `χωριατικη σαλατα` → "Greek Salad"): semantic search.
    - **Typos** (`nutela`, `kinder beuno`): fuzzy matching or semantic search.
    - **Greeklish generic** (`rizi`, `patates`): Greeklish → Greek conversion (E9).
    - **Ranking** (`πορτοκαλι`: juice ranks before the fruit; `γεμιστα`: filled biscuits rank before the dish): ranking boosts, e.g. exact full-name match or generic foods first.
    - **Descriptive** (`χωρις ζαχαρη σοκολατα`): no product has all three words. Semantic search.
  - The any-word fill-up (`bm25_or`) changed nothing on this set.
  - **Test-set lesson:** the first run scored BM25 at only 82 %, because the regexes didn't know Greeklish product names. Those were correct results judged as wrong. Fixing the regexes gave 91 %. When a query looks like a miss, check the top 5 in `details.json` before blaming search.
- **Result 2: semantic and hybrid (2026-11-16, 120 queries, M2 Max)**

  | Method | hit@1 | hit@5 | MRR@10 | mean ms | p95 ms |
  |---|---|---|---|---|---|
  | `bm25` | 77 % | 85 % | 0.80 | 3.6 | 4.5 |
  | `dense:e5-small` (semantic only) | 63 % | 87 % | 0.73 | 14 | 18 |
  | `dense:qwen3-0.6b` (semantic only) | 69 % | 86 % | 0.76 | 142 | 189 |
  | `rrf:e5-small` | **79 %** | **88 %** | **0.83** | 16 | 31 |
  | `rrf:qwen3-0.6b` | 78 % | 88 % | 0.82 | 144 | 183 |
  | `mix:qwen3-0.6b:0.25` (0.25 BM25 + 0.75 semantic) | 76 % | 88 % | 0.81 | 141 | 179 |
  | `mix:qwen3-0.6b:0.75` | 79 % | 87 % | 0.82 | 142 | 184 |

  - **Where hybrid helps (hit@5, BM25 → RRF):** Greeklish 87 → 100 %, typo / prefix 75 → 88 % (e5) or 100 % (Qwen3), Greek dish 83 → 92 %. Brand, English generic, Greek generic and descriptive queries are unchanged.
  - **Where it doesn't: Greek → English stays at 55 %** with both models. Semantic search alone is worse there (45 %). Both models favour items written in the same script as the query: `αρνι` (lamb) finds "Αριάνι" (a yogurt drink), `εσπρεσο` finds "Greek Cheese", and `καρπουζι` finds carob products. The English items ("Watermelon", "Cucumber", "Zucchini") never reach the top 10. **The main reason for semantic search is not solved by these two models.**
  - **Weight sweep (BM25 weight W from 0 to 1):** hit@5 stays flat at 86–88 % for any W from 0.1 to 0.9, for both models. hit@1 rises with more BM25 weight: e5-small goes from 75 % at W = 0.25 to 80 % at W = 0.75–0.9. The suggested 0.25 / 0.75 is fine for hit@5 but loses top-1 accuracy. RRF is as good as the best weight without any tuning. Full tables: `work/search_lab/sweep_*.md`.
  - **Qwen3-0.6B gives no gain over e5-small and is ~10× slower.** A query takes ~140 ms on the CPU, over the 100 ms budget, so it would need a GPU server.
  - **Cost:**

    | Model | Embed 40 k items (Mac GPU) | Vectors for 40 k | Estimate for 300 k items |
    |---|---|---|---|
    | e5-small | 18 s (2,169 items/s) | 61 MB | ≈ 2.5 min; ≈ 460 MB float32 (≈ 115 MB as int8) |
    | Qwen3-0.6B | 7.9 min (84 items/s) | 164 MB | ≈ 1 h; ≈ 1.2 GB float32 |

    Models: 1.6 GB of downloads in `work/models/hf`. Comparing a query with all vectors is a few ms even at 300 k, so the query model sets the speed.
- **Result 3: all OpenNutrition products (2026-11-16, 326,759 items, `--corpus opennutrition`)**
  - **109 of 120 queries are answerable.** The 11 without a correct item are Greek brands OpenNutrition doesn't carry (ΜΕΒΓΑΛ, ΔΕΛΤΑ, Caprice, Zagori, Βίκος, Lacta, ΙΟΝ, Μπάρμπα Στάθης, Παπαδοπούλου, Tsakiris) and μπουγάτσα.

  | Method | hit@1 | hit@5 | MRR@10 | mean ms | p95 ms |
  |---|---|---|---|---|---|
  | `like` (old search) | 21 % | 30 % | 0.25 | 51 | 69 |
  | `bm25` | 27 % | 32 % | 0.29 | 3 | 10 |
  | `dense:e5-small` | 39 % | 50 % | 0.43 | 27 | 32 |
  | `rrf:e5-small` | **42 %** | **51 %** | **0.46** | 41 | 59 |
  | `mix:e5-small:0.25` | 43 % | 50 % | 0.46 | 38 | 55 |
  | `mix:e5-small:0.75` | 39 % | 50 % | 0.43 | 39 | 54 |

  - **BM25 alone collapses here (32 %), because OpenNutrition has no Greek text at all.** Every Greek query (generic, dishes, Greek → English) gets 0 % with BM25.
  - **Semantic search helps much more on this set (+19 points)**:
    - Greek dishes 0 → 55 % (`μουσακας` → "Moussaka").
    - Typos 25 → 62 %.
    - English generic foods 75 → 90 %: `banana` → "Banana" first, where BM25 buries it under "Banana Muffins".
  - **It still mostly fails on Greek words:** Greek generic 15 %, Greek → English 10 %. It mostly matches on spelling: `αρνι` → "Bread by Arnie's", `καρπουζι` → "Carbmastee by Kroger", `γιαουρτι` → "Fioretti". Some do work: `φετα` → "Feta by Odyssey".
  - Cost: embedding 326,759 items with e5-small took 84 s on the Mac GPU (3,892 items/s), and the vectors take 502 MB. Qwen3-0.6B would take about 65 min.
  - **Conclusion for an OpenNutrition-only catalogue:** semantic search is clearly worth it, but Greek queries need translation to reach English-only products. Either translate the query to English before searching, or add Greek names to the products.

- **Decision (proposed 2026-11-16, waiting for sign-off, written for the `library` set):** the gate was "≥ +5 points hit@5 or fixes most cross-language misses". Hybrid gives **+3 points** and fixes **none** of the cross-language misses, so the gate is **not met**. Proposal:
  1. **Don't ship Qwen3-0.6B** (no quality gain, over the latency budget).
  2. **Keep BM25 as the search, and fix the cross-language gap with data instead of a model:** add Greek names and synonyms to OpenNutrition's generic foods (KR3.3), so BM25 finds `καρπουζι` directly. One-off translation, then human review.
  3. **Get the Greeklish and typo gains without a model first:** Greeklish → Greek conversion (E9) and fuzzy matching (e.g. an FTS5 trigram index). If those fall short, `rrf:e5-small` is a cheap add-on (~15 ms per query, 18 s to embed 40 k items).
  4. Optional before deciding: try a model known for strong cross-language retrieval (e.g. BGE-M3), or translate the query to English before searching.

## E16: Greek queries on English-only products ✅ (decision pending)
- **Question:** OpenNutrition has no Greek text, so Greek queries fail (E15 result 3: 0 % with BM25). Is it better to translate the products to Greek once (offline), or to translate each Greek query to English at search time? And what does each cost per search when there are many users?
- **Hypothesis:** an offline Greek index gives most of the gain with no extra work per search. Translating at search time costs a model call per Greek query and is less accurate on short, unaccented queries.
- **Setup:** `--corpus opennutrition` (326,759 items, 109 answerable test queries). Translation models are Marian / OPUS-MT, run locally.
  - **Offline, English → Greek** (`translate` command, `opus-mt-tc-big-en-el`, CC-BY-4.0):
    - `words`: every distinct English word in the names (28,754) translated once; a product's Greek text = its words' translations.
    - `names`: every distinct product name without "by Brand" (211,348) translated in context.
    - Both are indexed as an extra FTS5 index with a light Greek stemmer: one ending removed, stems of 4+ letters match as prefixes, shorter stems only as whole words, each word once per product.
  - **At search time, Greek → English** (`opus-mt_tiny_ell-eng`, 51 MB, Apache-2.0): only for queries in Greek script.
  - `opus-mt-tc-big-el-en` was also tried at search time. It output garbage with transformers 5.23 and was dropped.
  - Speed measured on **one CPU core** (`--threads 1`), so it shows per-core capacity.
- **Result (2026-11-16):**

  | Method | hit@1 | hit@5 | MRR@10 | mean ms (1 core) | p95 ms | ≈ searches/s per core |
  |---|---|---|---|---|---|---|
  | `bm25` (current) | 27 % | 32 % | 0.29 | 1.6 | 5.5 | ~600 |
  | `rrf:e5-small` (E15 hybrid) | 42 % | 51 % | 0.46 | 33 | 47 | ~30 |
  | **`kw_el:words`** (keyword + offline Greek index, **no model**) | 65 % | **77 %** | 0.70 | **2.5** | 5.5 | **~400** |
  | `kw_el:names` | 55 % | 73 % | 0.63 | 1.7 | 4.9 | ~600 |
  | **`hyb_el:words:e5-small`** (+ semantic) | **71 %** | **83 %** | **0.76** | 26 | 39 | ~38 |
  | `hyb_el:names:e5-small` | 65 % | 80 % | 0.71 | 26 | 39 | ~39 |
  | `kw_mt:el-en-tiny` (query translated at search time) | 42 % | 52 % | 0.46 | 7.3 | 19 | ~140 |
  | `hyb_mt:el-en-tiny:e5-small` | 55 % | 65 % | 0.59 | 39 | 68 | ~26 |

  - **By kind, `kw_el:words` vs `bm25`:** Greek generic 0 → **100 %**, Greek → English 0 → **95 %**, Greek dishes 0 → 64 %, typos 25 → 62 %. English and brand queries are unchanged.
  - **Query translation at search time is worse and costs more:** the tiny model handles single words but garbles short phrases typed without accents (`φακες σουπα` → "Fifts of a suffocation", `μοσχαρισιος κιμας` → "vesicular ves").
  - **Words beat full names** even though the name translations read better. Word translations use one consistent Greek word per food. Remaining word-level errors come from missing context: "ground" → "έδαφος" (soil), "ice" → "πάγος" (frozen water), "orange" → the colour.
  - Two indexing bugs found and fixed on the way:
    - Repeated words in translated names let "Banana Pops, Banana" outrank "Banana". Fixed by counting each word once per product.
    - 3-letter stems matched as prefixes, so `γαλα` → `γαλ` found `γαλοπούλα` (turkey). Fixed by matching short stems only as whole words.
  - **Still weak:** Greeklish (33 % without semantic, 60 % with), so E9 transliteration is still needed. In the hybrid, the semantic side adds noise to Greek queries (`αρνι` still pulls in "Arnie's").
  - **Cost (one-off, this Mac's GPU):**
    - Words: 51 s (559 per second).
    - Names: 11.4 min (308 per second).
    - Model downloads: ≈ 1.3 GB more in `work/models/hf` (2.7 GB in total with E15).
    - The corpus DB with both Greek indexes: 291 MB.
    - New or changed products only need their new words translated.
- **Decision (proposed, waiting for sign-off):**
  1. **Ship the offline Greek word index** (`kw_el:words`). It's the biggest gain (32 → 77 %) with no model at search time: ~2.5 ms on one core, roughly 400 searches per second per core.
  2. **Add e5-small hybrid on top only if the server can afford ~26 ms per search** (≈ 38 per second per core): it brings 77 → 83 %.
  3. **Don't translate queries at search time** (worse and slower).
  4. **Next:** review the word translations (fix "ground", "ice", "orange"…, about 1–2 h for the top 3,000 words, which cover 93 % of word occurrences), Greeklish → Greek (E9), and ranking boosts (generic foods first).

---

### Card template
```
## Exx: <title> ⬜
- **Hypothesis:** 
- **Method:** 
- **Metrics:** 
- **Result:** 
- **Decision:** 
```
