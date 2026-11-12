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
| E8 | On-device packaging (SQLite + FTS5) | KR4.1, KR4.2 | ⬜ |
| E9 | Greek / Greeklish search normalization | KR3.5 | ⬜ |
| E10 | Manual audit of 200 items | KR2.5 | ⬜ |

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

## E8: On-device packaging ⬜
- **Hypothesis:** The Greek union (~20 k rows) + FTS5 fits in < 10 MB raw / < 5 MB zipped. The EU subset fits in < 150 MB, so it's not shippable in the APK and needs a download or API.
- **Method:** Build SQLite files for GR / GR+CY / EU. Measure size, then run FTS prefix queries on a test device.
- **Metrics:** MB, p50/p95 query ms.
- **Result:** _TBD_

## E9: Greek / Greeklish search normalization ⬜
- **Hypothesis:** Accent stripping + final-sigma folding + a Greeklish → Greek transliteration index raises top-5 hit rate on a 100-query set by ≥ 20 points vs a plain FTS.
- **Method:** Build the query set (real user-style queries: "fakes", "giaourti", "spanakopita", "σπανακοπιτα"). Compare plain vs normalized index.
- **Metrics:** top-1 / top-5 hit rate.
- **Result:** _TBD_

## E10: Manual audit ⬜
- **Method:** Random 200 items from the final Greek subset. Compare carbs, kcal and portion against the package photo (OFF images) or the producer's website.
- **Metrics:** % within ±1 g or ±10 % for carbs; error categories.
- **Result:** _TBD_

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
