# KnowD1 Foods: Clean Food Library

Goal: turn two open datasets into a **clean, trustworthy, carb-accurate food library** for the KnowD1 Android app. The focus is Greek-market users and carb counting.

## Status (2026-11-12)

- [x] Downloaded **Open Food Facts**: `openfoodfacts/food.parquet` (8.0 GB, 4,906,869 products) from [Hugging Face](https://huggingface.co/datasets/openfoodfacts/product-database/resolve/main/food.parquet). This is the simplified version of the JSONL dump.
- [x] Downloaded **OpenNutrition** 2025.1: `opennutrition-dataset-2025.1/` (269 MB, 326,759 foods)
- [x] Profiled both and wrote these docs
- [ ] Licensing decision D-1 → `docs/LICENSING.md`
- [ ] Build pipeline v0.1 → `docs/PIPELINE.md`

## Docs

| File | What's in it |
|---|---|
| [`docs/OKRs.md`](docs/OKRs.md) | Objectives & Key Results for this cycle. Targets, progress, check-in log |
| [`docs/DATASETS.md`](docs/DATASETS.md) | What each dataset contains: columns, coverage numbers, Greek-market stats, **known issues Q-01…Q-15** |
| [`docs/PIPELINE.md`](docs/PIPELINE.md) | Stages raw → clean, **target schema**, **carb normalization**, validation rules, merge priority |
| [`docs/EXPERIMENTS.md`](docs/EXPERIMENTS.md) | Experiment cards E0–E10 (hypothesis → result → decision) |
| [`docs/LICENSING.md`](docs/LICENSING.md) | ODbL / OpenNutrition attribution obligations + open decision D-1 |

## Five things to know first

1. **OFF is the main source for packaged foods.** 99.99 % of OpenNutrition's 313 k grocery items are OFF barcodes.
2. **OpenNutrition's real value** is its 5,299 curated *everyday* generic foods (with household portions + synonyms), plus prepared and restaurant items. Its license, however, requires an attribution link **on every screen** that shows its data.
3. **"Carbohydrates" is not one number.** US/CA labels and OpenNutrition include fiber. EU labels don't. We store `carbs_available_g` explicitly.
4. **Some OFF per-serving rows are double-scaled** (e.g. 220 g carbs per 100 g). Validation rules catch the obvious cases.
5. **Greek market ≈ 29 k products, 18.8 k with nutrition, only 4.9 k with Greek names.** Greek names, portions and dishes need enrichment.

## Folder layout

```
Foods/
├── README.md
├── docs/                           # documentation (this)
├── openfoodfacts/food.parquet      # RAW, read-only
├── opennutrition-dataset-2025.1/   # RAW, read-only
├── scripts/                        # (to create) pipeline steps 01_…, 02_…
├── work/                           # (to create) intermediate files
└── out/                            # (to create) knowd1_foods.sqlite, qa_report.md
```

## Attribution (required when data is displayed)

- © Open Food Facts contributors: https://world.openfoodfacts.org (ODbL)
- OpenNutrition: https://www.opennutrition.app (ODbL + per-screen attribution, see `docs/LICENSING.md`)
