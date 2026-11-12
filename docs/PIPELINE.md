# Clean Food Library: Pipeline & Target Spec

How raw data becomes the **KnowD1 food library**. This is the contract: if a row is in `out/`, it passed everything below.

---

## 1. Folder layout (proposed)

```
Foods/
├── README.md                         ← start here
├── docs/                             ← these files
├── openfoodfacts/food.parquet        ← RAW, read-only (8.0 GB)
├── opennutrition-dataset-2025.1/     ← RAW, read-only (269 MB)
├── scripts/                          ← numbered pipeline steps (01_…, 02_…)
├── work/                             ← intermediate parquet files, disposable
└── out/                              ← knowd1_foods.sqlite + qa_report.md
```

Rules: never edit raw files. Every step reads from the previous stage and writes a new file. The whole build must be re-runnable from raw with one command.

**Tooling:** Python 3.11 + **DuckDB** (SQL directly on the 8 GB parquet without loading it into RAM). Install with `pip install duckdb` in a project venv. `pyarrow 11` and `pandas 2.0` are already available in anaconda but are slower for this.

---

## 2. Stages

| # | Stage | Input → Output | What happens |
|---|---|---|---|
| 0 | **Raw** | downloads | Untouched. Record download date + version in `DATASETS.md`. |
| 1 | **Extract** | raw → `work/off_slim.parquet`, `work/on_slim.parquet` | Keep only needed columns. Drop OFF `obsolete`, rows with no name and rows with no nutrition. Flatten OFF `nutriments` list into columns. Parse OpenNutrition JSON columns. |
| 2 | **Normalize** | → `work/*_norm.parquet` | Map both sources to the **target schema** (§3). Units, barcodes, names, language, **carb definition** (§4). |
| 3 | **Validate** | → `work/*_valid.parquet` + `work/quarantine.parquet` | Apply **hard rules** (fail → quarantine with reason) and **soft rules** (pass, but add flags). Compute `quality_score`. |
| 4 | **Dedupe & merge** | → `work/merged.parquet` | Join on normalized barcode. Pick a winner per field (§6). Generic foods are deduped by name + nutrient similarity. |
| 5 | **Enrich** | → `work/enriched.parquet` | Category mapping, portions/household measures, Greek names & aliases, search keys. |
| 6 | **Export** | → `out/knowd1_foods.sqlite` | SQLite + FTS5 search index. Region subsets (GR / EU / world). Check against the size budget. |
| 7 | **QA report** | → `out/qa_report.md` | Counts per stage, drop reasons, flag rates, random sample for manual review. |

---

## 3. Target schema (v0.1 draft)

### `food`
| Column | Type | Notes |
|---|---|---|
| `id` | TEXT PK | Stable: `kd_` + short hash of (`source`, `source_id`) |
| `kind` | TEXT | `generic` · `packaged` · `restaurant` · `recipe` |
| `name` | TEXT | Display name in `name_lang` |
| `name_lang` | TEXT | `el`, `en`, … |
| `name_en` | TEXT | Always filled if possible (fallback for search) |
| `name_el` | TEXT | Greek name if known |
| `brand` | TEXT | Packaged only |
| `barcode` | TEXT | Normalized GTIN, zero-padded to 13 (or 14). Packaged only |
| `category` | TEXT | Our own ~20-group taxonomy (mapped from OFF `food_groups_tags` / OpenNutrition type + labels) |
| `countries` | TEXT[] | From OFF `countries_tags` |
| `basis` | TEXT | `100g` or `100ml` |
| `energy_kcal` | REAL | per basis |
| `carbs_available_g` | REAL | **The number used for carb counting** (excludes fiber) |
| `carbs_total_g` | REAL | Includes fiber (US-style), if known |
| `carbs_definition_src` | TEXT | What the source reported: `available` or `total` |
| `fiber_g` `sugars_g` `protein_g` `fat_g` `sat_fat_g` `salt_g` | REAL | per basis, nullable except protein/fat |
| `polyols_g` | REAL | Optional (sugar alcohols) |
| `density_g_ml` | REAL | Optional, for liquids |
| `quality_score` | INT | 0–100 (§5) |
| `quality_flags` | TEXT[] | e.g. `fiber_unknown`, `energy_mismatch_soft`, `serving_basis_suspect` |
| `popularity` | INT | OFF `unique_scans_n` (for search ranking) |
| `source` | TEXT | `off` · `opennutrition` · `usda` · `knowd1` |
| `source_id` | TEXT | OFF `code`, OpenNutrition `id`, … |
| `source_updated_at` | INT | OFF `last_modified_t` |
| `license` | TEXT | `ODbL` · `ODbL+OpenNutrition-DbCL` · … (see LICENSING.md) |

### `portion`
| Column | Type | Notes |
|---|---|---|
| `food_id` | TEXT FK | |
| `label` / `label_el` | TEXT | "1 cup", "1 slice", "1 medium" / Greek |
| `grams` | REAL | Grams (or ml) per portion |
| `is_default` | BOOL | Default serving shown in UI |
| `origin` | TEXT | `label` (pack) · `source_db` · `curated` |

### `food_search` (FTS5)
`food_id`, `text`, `lang`. Contains the name, brand, aliases and accent-stripped / Greeklish variants.

---

## 4. Carbohydrate normalization ⚠️ (most important for KnowD1)

Sources do **not** agree on what "carbohydrates" means:

| Region / source | "Carbohydrate" on the label / in the DB | Example: cooked lentils / 100 g |
|---|---|---|
| **EU, UK, AU/NZ** labels | **Available** carbs (fiber excluded) | ≈ 12 g carbs + 7.9 g fiber |
| **US, Canada** labels (most of OFF's US products, all OpenNutrition grocery) | **Total** carbs (fiber **included**) | 20.1 g carbs (incl. 7.9 g fiber) |
| **OpenNutrition** `everyday` (USDA/CNF "by difference") | **Total** | `Lentils, Cooked`: 20.1 carbs, 7.9 fiber ✔ verified |

**Rule:**
1. Decide `carbs_definition_src` per row:
   - OpenNutrition → `total`.
   - OFF → by sold-in countries: if `countries_tags` ⊂ {US, CA, PR, MX…} → `total`. If any EU/UK/AU/NZ country → `available`. Mixed or unknown → use the **GS1 barcode prefix** as a hint (`000–139` US/CA, `520–521` Greece, `529` Cyprus, `30–37` France, `40–44` Germany…). If still unknown → flag `carb_def_unknown`.
2. `total` → `carbs_available_g = carbs_total_g − fiber_g`. If fiber is missing, keep the total, flag `fiber_unknown` and lower the quality score.
3. `available` → `carbs_total_g = carbs_available_g + fiber_g` (when fiber is known).
4. Experiment E3 checks this rule with an energy fit (EU uses 2 kcal/g for fiber, 4 kcal/g for available carbs).

---

## 5. Validation rules

All values are per 100 g / 100 ml **after** normalization.

### Hard rules → quarantine (row is dropped, reason is kept)
| Code | Rule |
|---|---|
| `H01_no_name` | No usable name in any language |
| `H02_core_missing` | Missing any of: energy kcal, carbs, protein, fat |
| `H03_negative` | Any nutrient < 0 |
| `H04_over_100` | carbs, protein, fat, sugars or fiber > 100 |
| `H05_mass_sum` | carbs + protein + fat + (fiber if `available`) + salt > 105 |
| `H06_energy_max` | energy > 900 kcal |
| `H07_part_gt_whole` | sugars > carbs + 0.5 **or** sat_fat > fat + 0.5 |
| `H08_energy_mismatch` | \|kcal − (4·C + 4·P + 9·F + 2·Fib + 7·Alc)\| / kcal > 25 % (only when kcal ≥ 20) |
| `H09_obsolete` | OFF `obsolete = true` |

### Soft rules → keep, add flag, lower `quality_score`
| Code | Rule |
|---|---|
| `S01_energy_mismatch_soft` | Energy mismatch 15–25 % |
| `S02_serving_basis_suspect` | OFF `nutrition_data_per = serving` (see DATASETS.md, the "double-scaling" bug) |
| `S03_fiber_unknown` | No fiber value (affects available carbs) |
| `S04_no_serving` | No serving size / portion |
| `S05_unpopular` | OFF `unique_scans_n` = 0 / null |
| `S06_off_dq_errors` | OFF `data_quality_errors_tags` not empty |
| `S07_low_completeness` | OFF `completeness` < 0.5 |
| `S08_no_source` | OpenNutrition `everyday` row with an empty `source` (1,910 rows); `prepared` rows also have no source (likely estimated) |

### `quality_score` (draft)
Start at 100: −15 per soft flag (S02 −30), +10 if `popularity` ≥ 10, cap at [0, 100]. Search ranks by text match, then quality, then popularity.

---

## 6. Merge priority (field level)

| Data | 1st choice | 2nd | 3rd |
|---|---|---|---|
| Packaged product nutrition | OFF, if it passed validation and `nutrition_data_per = 100g` | OpenNutrition grocery (same barcode) | OFF with flag S02 |
| Packaged name (Greek market) | OFF `product_name` lang `el` | OFF `en` | OpenNutrition name (strip the " by Brand" suffix) |
| Generic foods | Curated KnowD1 list | OpenNutrition `everyday` / USDA / CIQUAL (depends on LICENSING D-1) | — |
| Portions | Pack label `serving_size` | OpenNutrition `serving` | Curated |

---

## 7. Size & performance budget (to confirm in E8)

- Greek-market subset with FTS shipped **inside the APK** ≤ 20 MB compressed.
- Rest of the world → online lookup by barcode (OFF API) or a downloadable pack.
- Search: < 100 ms for a 3-letter prefix on a mid-range Android phone.
