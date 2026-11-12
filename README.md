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
| [`docs/IMAGES.md`](docs/IMAGES.md) | Food image strategy: options, decision, clean-up and AI-image specs, category icons |
| [`docs/LICENSING.md`](docs/LICENSING.md) | ODbL / OpenNutrition attribution obligations + open decision D-1 |

## Data browser (local web page)

Two tabs: **Open Food Facts (sold in Greece or Greek 520–521 barcode, 26,654 products)** and **OpenNutrition (all 326 k foods)**. Raw values, searchable.

```bash
python3 -I tools/browser/foods_browser.py build   # one-time, ~1 min → work/browser.sqlite (~850 MB, git-ignored)
python3 -I tools/browser/foods_browser.py serve   # open http://127.0.0.1:8765
```

**Search is deterministic.** The same query always returns the same rows in the same order:
- **Matching:** every word you type must appear somewhere in the name or brand. OpenNutrition matches name + alternate names.
- **Normalization:** case and Greek accents are ignored, so `φέτα` = `φετα` = `ΦΕΤΑ`. Punctuation counts as a space, so `coca cola` = `coca-cola`.
- **Barcodes:** typing only 8–14 digits does an exact barcode lookup (leading zeros ignored, filters ignored).
- **Order:** results are sorted A→Z by name, then by ID. There's no fuzzy matching and no ranking.
- **Filters:** OFF by market (sold in Greece / Greek barcode); OpenNutrition by type (everyday / prepared / restaurant / grocery).
- **Shareable views:** the URL keeps the tab, query, filter, page and open item, so a view can be reloaded or shared.

**Photos:**
- Every row shows a thumbnail. The detail view shows the front, nutrition-table, ingredients and packaging photos.
- Photos load live from images.openfoodfacts.org, so they need internet. They are CC BY-SA (see `docs/LICENSING.md`).
- OpenNutrition has no images of its own. Its grocery items reuse the Open Food Facts photo for the same barcode.
- Coverage: 21,294 of 26,654 OFF products and 101,484 OpenNutrition grocery items have a photo.
- Items without a photo, or whose photo fails to load, show the default image `tools/browser/no-image.svg`.

Re-run `build` after downloading new raw data.

## Photo pilots (experiments E11 and E14)

Two ways to turn Greek OFF front photos into square catalogue images, tried on the same 200 products:

- **E11 cut-out:** removes the background (rembg). Reviewed: 31 % good, no-go. Review page: http://127.0.0.1:8765/photo-pilot
- **E14 crop:** Open Food Facts' own ready-made models find the product and check that the photo really is a front. The original is cropped to the product and placed on white. Review page: http://127.0.0.1:8765/photo-pilot?run=crop (shows the original, the cut-out with your verdict, and the crop)

```bash
python3 -m venv .venv && .venv/bin/pip install -r tools/photos/requirements.txt   # once
.venv/bin/python -I tools/photos/cleanup_pilot.py    # E11: 200 products → work/photo_pilot/
.venv/bin/python -I tools/photos/crop_pilot.py       # E14: same 200 → work/photo_pilot_crop/ (model download commands are in the script)
```

Verdicts are saved to `review.json` in each run's folder. See `docs/IMAGES.md` §4 and `docs/EXPERIMENTS.md` (E11, E14).

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
├── tools/browser/                  # local data browser (build + serve) + photo pilot page
├── tools/photos/                   # photo clean-up pilot (E11)
├── scripts/                        # (to create) pipeline steps 01_…, 02_…
├── work/                           # intermediate files (browser.sqlite lives here)
└── out/                            # (to create) knowd1_foods.sqlite, qa_report.md
```

## Attribution (required when data is displayed)

- © Open Food Facts contributors: https://world.openfoodfacts.org (ODbL)
- OpenNutrition: https://www.opennutrition.app (ODbL + per-screen attribution, see `docs/LICENSING.md`)
