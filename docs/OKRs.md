# OKRs: KnowD1 Clean Food Library

**Cycle:** 2026-Q4 (2026-11-12 → 2026-12-31) · **Owner:** ___ · **Last check-in:** 2026-11-12

> **How to use (Google-style OKRs)**
> - **Objective** = qualitative "what & why". **Key Result** = measurable "how we know". Tasks/initiatives are *not* KRs.
> - Each KR has a **baseline → target** and gets a **score from 0.0 to 1.0** at the end of the cycle.
> - **Committed** OKRs are expected to hit 1.0. **Aspirational** OKRs count as a success at **~0.7**.
> - Update the "Current" column at each weekly check-in (§ Check-in log). Don't rewrite targets mid-cycle; note why in the log instead.
> - **Assumption to confirm:** carbs are the most important nutrient for KnowD1 users (carb counting), and the first market is **Greece / Cyprus**.
> - All targets below are **proposals**. Adjust them before the cycle starts.

---

## O1: Know our raw data inside-out *(committed)*

| KR | Baseline | Target | Current | Score |
|---|---|---|---|---|
| **KR1.1** Both source datasets downloaded and versioned in `DATASETS.md` | 0 / 2 | 2 / 2 | **2 / 2** | 1.0 |
| **KR1.2** Data dictionary + coverage profile written for both sources | none | done | **done** (`DATASETS.md`) | 1.0 |
| **KR1.3** Data-quality issues catalogued, each with a detection rule | 0 | ≥ 10 | **15** (Q-01…Q-15) | 1.0 |
| **KR1.4** Licensing decision D-1 made and recorded | open | decided | open | 0.0 |

**Tasks**
- [x] Downloaded Open Food Facts: `food.parquet` from Hugging Face (8.0 GB, 4,906,869 products)
- [x] Downloaded OpenNutrition dataset 2025.1 (326,759 foods)
- [x] Profile both datasets (E0)
- [x] Write docs: `README.md`, `DATASETS.md`, `PIPELINE.md`, `EXPERIMENTS.md`, `LICENSING.md`, `OKRs.md`
- [ ] Decide D-1 (use OpenNutrition in the shipped app or not), see `LICENSING.md`

---

## O2: Build a clean, trustworthy food library v0.1 *(committed)*

| KR | Baseline | Target | Current | Score |
|---|---|---|---|---|
| **KR2.1** The whole pipeline rebuilds `out/` from raw with **one command** in **< 30 min** | no pipeline | yes, < 30 min | — | |
| **KR2.2** Rows in `out/` violating hard rules H01–H09 (automated test) | n/a | **0** | — | |
| **KR2.3** Rows with `carbs_available_g` **and** `carbs_definition_src` filled | 0 % | **100 %** | — | |
| **KR2.4** Rows carrying `source`, `source_id`, `license` | 0 % | **100 %** | — | |
| **KR2.5** Manual audit: 200 random Greek-market items checked against the package photo, carbs within ±1 g or ±10 % | n/a | **≥ 95 %** | — | |

**Tasks**
- [ ] Set up a project venv with `duckdb`, `pyarrow`, `pandas`
- [ ] E1: slim extract of OFF + OpenNutrition → `work/`
- [ ] E2: quantify and try to fix the OFF serving double-scaling bug
- [ ] E3: carb-definition classifier + energy-fit check
- [ ] Implement validation rules H01–H09 / S01–S08 + quarantine report
- [ ] E4: OFF ↔ OpenNutrition value agreement on shared barcodes
- [ ] Export `out/knowd1_foods.sqlite` + `out/qa_report.md`

---

## O3: Make it feel local for Greek users *(aspirational)*

| KR | Baseline | Target | Current | Score |
|---|---|---|---|---|
| **KR3.1** Greek-market packaged products in the library that pass validation | 18,832 with core nutrients (before validation) | **≥ 15,000** | — | |
| **KR3.2** Greek-market products with a **Greek name** | 4,925 | **≥ 10,000** | 4,925 | |
| **KR3.3** Generic everyday foods with a Greek name **and** ≥ 1 household portion in grams | 0 | **≥ 1,000** | 0 | |
| **KR3.4** Traditional Greek dishes with carbs per portion (μουσακάς, παστίτσιο, σπανακόπιτα, γεμιστά, φασολάδα, γύρος πίτα…) | 0 | **≥ 150** | 0 | |
| **KR3.5** Search test set (100 queries in Greek, Greeklish and English): right item in top 5 | n/a | **≥ 90 %** | — | |

**Tasks**
- [ ] E5: Greek subset deep-dive (name languages, brands, categories, gaps)
- [ ] E6: pick a generic-food base (OpenNutrition everyday vs USDA vs CIQUAL) after D-1
- [ ] E7: portions: parse OFF `serving_size`, map OpenNutrition `serving`, build a curated Greek portion list (κουταλιά, φλιτζάνι, φέτα, μερίδα…)
- [ ] E9: search normalization (accents/τόνοι, final ς, Greeklish transliteration)
- [ ] Find a source for Greek dishes (recipe-based calculation or a licensed composition table)

---

## O4: Ship it inside KnowD1 *(aspirational)*

| KR | Baseline | Target | Current | Score |
|---|---|---|---|---|
| **KR4.1** On-device Greek subset (SQLite + FTS5) size, compressed | n/a | **≤ 20 MB** | — | |
| **KR4.2** Prefix search p95 latency on a mid-range Android phone | n/a | **< 100 ms** | — | |
| **KR4.3** Attribution + ODbL obligations implemented per `LICENSING.md` | 0 % | 100 % | — | |
| **KR4.4** Documented refresh process (re-download → rebuild → diff report) | none | runs monthly | — | |

**Tasks**
- [ ] E8: SQLite/FTS5 packaging experiment (GR / EU / world sizes + latency)
- [ ] Barcode-scan fallback to the OFF API for products not in the local DB
- [ ] Add attribution strings to the About screen (+ per-screen if D-1 = B)

---

## Scoring guide

| Score | Meaning |
|---|---|
| 1.0 | Fully achieved |
| 0.7 | Good progress. **Success for an aspirational KR** |
| 0.3 | Some progress, well short |
| 0.0 | No progress |

Objective score = average of its KRs.

---

## Check-in log

| Date | Notes | O1 | O2 | O3 | O4 |
|---|---|---|---|---|---|
| 2026-11-12 | Both datasets downloaded and profiled. Docs written. Key findings: carb-definition mismatch (Q-01), OFF serving double-scaling (Q-02), OpenNutrition grocery ≈ OFF subset, Greek names scarce (Q-09). | 0.75 | 0.0 | 0.0 | 0.0 |
