# Datasets: What We Have

All numbers come from a full profiling pass over the raw files on **2026-11-12** (experiment **E0** in `EXPERIMENTS.md`). OFF scan time: about 110 s on this Mac with pyarrow.

---

## 1. Inventory

| | Open Food Facts (OFF) | OpenNutrition (ON) |
|---|---|---|
| Path | `openfoodfacts/food.parquet` | `opennutrition-dataset-2025.1/opennutrition_foods.tsv` |
| Origin | https://huggingface.co/datasets/openfoodfacts/product-database (`food.parquet`, a simplified version of the JSONL dump) | https://www.opennutrition.app, release **2025.1** |
| Downloaded | 2026-11-12 | 2026-11-12 |
| Size | **8.0 GB** | **269 MB** |
| Rows | **4,906,869** products | **326,759** foods |
| Format | Parquet, 145 columns, 4,792 row groups | TSV, 13 columns, several JSON-encoded |
| What it is | Crowd-sourced **packaged products**, worldwide, keyed by barcode | **Generic foods** (from national food composition DBs) + US packaged + US restaurant chains + prepared dishes |
| License | ODbL / DbCL | ODbL / **modified** DbCL. See `LICENSING.md` |

---

## 2. Open Food Facts (`food.parquet`)

### 2.1 Columns we care about

| Group | Columns | Notes |
|---|---|---|
| Identity | `code` | Barcode as a string. Keep leading zeros. Normalize to GTIN-13 for joins |
| Names | `product_name`, `generic_name` | `list<struct<lang, text>>`. Pseudo-language **`main`** = the product's main-language name (4.54 M rows). Real languages are also present (`en` 2.05 M, `fr` 1.42 M…) |
| Brand | `brands`, `brands_tags` | |
| Market | `countries_tags`, `lang` | `countries_tags` = **where it is sold**, not where it was made |
| Category | `categories_tags`, `food_groups_tags`, `categories_properties.ciqual_food_code` | `food_groups_tags` is a clean 2-level taxonomy (good base for our categories) |
| Nutrition | `nutriments` | `list<struct<name, value, 100g, serving, unit, prepared_*>>`. Use the **`100g`** field. `value` is "as entered" |
| Nutrition basis | `nutrition_data_per` | `100g` / `serving` / null. See issue Q-02 |
| Serving | `serving_size` (text), `serving_quantity` | Text needs parsing ("30 g", "1 cup (240 ml)") |
| Quality | `completeness`, `data_quality_errors_tags`, `data_quality_warnings_tags`, `states_tags`, `obsolete` | OFF's own checks are useful as flags |
| Popularity | `unique_scans_n`, `scans_n`, `popularity_key` | Ranking signal for search |
| Freshness | `last_modified_t`, `created_t` | Unix seconds |
| Ingredients/allergens | `ingredients_text`, `allergens_tags`, `traces_tags` | Not needed for v0.1 |

Columns we can ignore for the library: images, packaging*, environmental score, editors/photographers, `emb_codes`, `owner_fields`, etc.

### 2.2 Coverage (whole file)

| Metric | Rows | % |
|---|---:|---:|
| Total products | 4,906,869 | 100 % |
| Has a product name | 4,607,736 | 93.9 % |
| Has **all core 4** (kcal, carbs, protein, fat) per 100 g | 3,453,012 | 70.4 % |
| Has sugars | 3,283,120 | 66.9 % |
| Has salt | 3,064,836 | 62.5 % |
| Has **fiber** | 1,885,871 | **38.4 %** |
| Has `serving_quantity` | 1,575,819 | 32.1 % |
| Scanned by ≥ 1 user (`unique_scans_n > 0`) | 1,814,998 | 37.0 % |
| `obsolete = true` | 0 | (this export already excludes them) |
| `no_nutrition_data = true` | 5,174 | 0.1 % |
| **Passes basic checks** (name + core 4 + energy within ±25 % + no value > 100 + mass sum ≤ 105) | **3,166,506** | **64.5 %** |

### 2.3 Countries (products sold in)

France 1,296,604 · United States 1,000,656 · Germany 438,803 · Spain 362,959 · Italy 273,933 · UK 200,555 · Canada 130,471 · … · **Greece 14,813** · Cyprus 3,050

### 2.4 Greek market

| | 🇬🇷 Greece | 🇨🇾 Cyprus |
|---|---:|---:|
| Products (`countries_tags`) | 14,813 | 3,050 |
| With core 4 nutrients | 9,415 | 2,056 |
| **Pass basic checks** | **8,722** | **1,955** |
| With fiber | 5,551 | 979 |
| Name in **Greek** (`el`) | 3,713 | 316 |
| Name in English | 7,677 | 2,149 |
| Greek GS1 barcode prefix (520–521) | 9,923 | 400 |
| Scanned ≥ 1 | 10,594 | 1,663 |
| Has `serving_size` text | 6,296 | 1,321 |
| `nutrition_data_per` 100g / serving / null | 5,959 / 952 / 7,900 | 1,366 / 275 / 1,409 |
| Sold **only** in this country | 12,616 | 2,660 |

- **Greek-market union** (tagged Greece **or** Cyprus **or** Greek GS1 barcode 520/521): **29,037 products**, **18,832** with core nutrients, but only **4,925** with a name in Greek script.
- Greek GS1 barcodes worldwide: 21,653 (many Greek products are only tagged with export countries).
- Greek data is fresh: last modified in 2026: 8,877 · 2025: 3,055 · 2024: 1,506 · older: ~1,375.
- Top Greek food groups: sugary snacks 1,079 · cereals & potatoes 1,064 · milk & dairy 878 · beverages 685 · fats & sauces 358 · salty snacks 322.

### 2.5 Other distributions

- `nutrition_data_per`: null **2,553,489** (52 %) · `100g` 1,827,975 · `serving` 523,801 · `100ml` 1,559 · ~30 junk values (Thai text, "bottle", "Amount per serving: …").
- OFF's own top data-quality errors: energy-kcal mismatch (77,781 + 32,634), nutrient total > 105 g (25,934), energy > 3,800 kJ (15,019), carbs > 105 (12,557), salt ≠ sodium × 2.5 (7,595).
- Product `lang`: en 2.06 M · fr 1.39 M · es 386 k · de 361 k · it 257 k · …

---

## 3. OpenNutrition (`opennutrition_foods.tsv`)

### 3.1 Columns

| Column | Type | Notes |
|---|---|---|
| `id` | text | `fd_…` |
| `name` | text | English only. Grocery names are always "`<Product> by <Brand>`" |
| `alternate_names` | JSON array | Synonyms. Great for search (everyday/prepared only) |
| `description` | text | Marketing-style text (AI-written style) |
| `type` | enum | `everyday` · `grocery` · `prepared` · `restaurant` |
| `source` | JSON array | `{database, reference, id, name, url}`. Only `everyday` rows have one |
| `serving` | JSON | `{"common": {"unit": "cup", "quantity": 1}, "metric": {"unit": "g", "quantity": 160}}`, i.e. a **household measure + grams** |
| `nutrition_100g` | JSON | Up to 97 nutrient keys (`calories`, `carbohydrates`, `protein`, `total_fat`, `dietary_fiber`, `total_sugars`, `added_sugars`, `sugar_alcohols`, `net_carbs`…) |
| `ean_13` | text | Grocery only |
| `labels` | JSON array | `cooked`, `raw`, `sweetened`, `dry`, `canned`, `frozen`… |
| `package_size` | JSON | |
| `ingredients` | text | |
| `ingredient_analysis` | JSON | Allergens etc. |

### 3.2 By type

| Type | Rows | Has source | Alt. names | Fiber | Rich (≥ 30 nutrients) | Notes |
|---|---:|---:|---:|---:|---:|---|
| **everyday** | **5,299** | 3,389 | 5,299 | 5,299 | 5,299 | **The gem.** Generic foods with portions, from USDA SR Legacy / Foundation, Canadian Nutrient File, Frida (DK), Australian Nutrient DB |
| prepared | 3,836 | **0** | 3,835 | 3,836 | 3,836 | Generic dishes ("Chicken Tenders", "Multigrain Bread"). No source, so probably estimated |
| grocery | 313,442 | 0 | 3,618 | 262,388 | 4,687 | US packaged products. **99.99 % are also in OFF** (see §4) |
| restaurant | 4,182 | 0 | 0 | 4,181 | 4,182 | US chains (Jamba, Denny's, Tim Hortons…) |

- The core 4 nutrients are present on **100 %** of rows. Sodium 99.8 %, sugars 94.7 %, fiber 84.4 % (whole file).
- Serving units: g 159,685 · cup 34,680 · oz 25,121 · ml 21,956 · tbsp 17,193 · piece 8,131 · bar · slice · tsp · fl oz…
- Out-of-range carbs: 274 rows. Energy mismatch > 25 %: 8,663 of 303,494 checked (2.9 %).

---

## 4. Overlap between the two

- OpenNutrition grocery barcodes: **313,256** distinct. **313,214 (99.99 %) exist in OFF.** OpenNutrition grocery is a re-processed US subset of OFF, so for packaged foods **OFF is the primary source**. ON grocery is useful only to cross-check values (experiment E4).
- Unique value of OpenNutrition = **everyday (5,299) + prepared (3,836) + restaurant (4,182)**, plus **household portions** and **synonyms**.

---

## 5. Known data issues (catalogue)

| ID | Issue | Size | Detection | Handling (see `PIPELINE.md`) |
|---|---|---|---|---|
| **Q-01** | **"Carbohydrates" means different things.** US/CA (and all OpenNutrition rows) = **total carbs incl. fiber**. EU/UK/AU = **available carbs** (fiber excluded). Verified: ON `Lentils, Cooked` = 20.1 g carbs incl. 7.9 g fiber | Every row | Country tags, GS1 prefix, source | §4 carb normalization → `carbs_available_g` |
| **Q-02** | **OFF "serving double-scaling"**: some rows with `nutrition_data_per = serving` were entered with per-100 g values, so OFF multiplied them again. E.g. `0011110747228` oatmeal: carbs `value` 72.7 → `100g` **220** | 34,511 of 508,504 `serving` rows exceed 100 g (6.8 % vs 2.4 % for `100g` rows). True size unknown (cases under 100 aren't caught) | `100g ≈ value × 100 / serving_quantity` **and** `value` is plausible per 100 g | Flag S02. Recovery tested in E2 |
| Q-03 | `nutrition_data_per` is null for 52 % of rows | 2,553,489 | null | Trust the OFF-computed `100g` field + validation |
| Q-04 | Energy doesn't match macros (> 25 %) | 128,463 (3.9 % of checked) | Atwater check | H08 / S01 |
| Q-05 | Carbs > 100 g / 100 g | 14,760 | range | H04 |
| Q-06 | Sugars > carbs | 3,204 | compare | H07 |
| Q-07 | Negative nutrient values (excluding scores) | 1,382 | < 0 | H03 |
| Q-08 | **Fiber missing** on 62 % of OFF rows. Blocks total → available conversion for US-style rows | 3.0 M | null | S03 + flag |
| Q-09 | **Greek names are rare**: only 4,925 of 29,037 Greek-market products have a Greek-script name | ~24 k | Unicode range check | Enrichment / manual curation (O3) |
| Q-10 | Names are multilingual lists with a pseudo-lang `main` | all | — | Name picker: `el` → `main` (if Greek script) → `en` → any |
| Q-11 | Barcodes: leading zeros, UPC-A (12) vs EAN-13, internal store codes (`2xx`) | many | length/prefix | Normalize to GTIN-13. Drop `020–029` / `200–299` in-store codes from barcode lookup |
| Q-12 | OpenNutrition `prepared` (3,836) and 1,910 `everyday` rows have **no source** | 5,746 | empty `source` | S08, lower quality score |
| Q-13 | OpenNutrition `grocery` duplicates OFF | 313,214 | barcode join | Use only for cross-checks |
| Q-14 | Junk `nutrition_data_per` values (Thai text, "bottle"…) | ~30 | not in {100g, 100ml, serving} | Treat as unknown |
| Q-15 | `countries_tags` = where it is **sold**, so international brands (Coca-Cola, Nutella, Lindt) dominate Greek "popular" lists | — | — | Rank by popularity *and* Greek GS1 / Greek name |
