# OKRs: KnowD1 Clean Food Library

**Cycle:** 2026-Q4 (2026-11-12 → 2026-12-31) · **Owner:** ___ · **Last check-in:** 2026-11-13

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
- [x] Local data browser with two tabs (OFF GR + CY | OpenNutrition) and deterministic search: `tools/browser/`
- [x] Browser search switched from a LIKE scan to SQLite FTS5 with BM25 ranking (2026-11-13)
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
| **KR3.5** Search test set (100 queries in Greek, Greeklish and English): right item in top 5 | 83 % (old LIKE search, draft set) | **≥ 90 %** | 91 % (BM25, **draft** set, not yet reviewed) | |

**Tasks**
- [ ] E5: Greek subset deep-dive (name languages, brands, categories, gaps)
- [ ] E6: pick a generic-food base (OpenNutrition everyday vs USDA vs CIQUAL) after D-1
- [ ] E7: portions: parse OFF `serving_size`, map OpenNutrition `serving`, build a curated Greek portion list (κουταλιά, φλιτζάνι, φέτα, μερίδα…)
- [x] Draft search test set (100 queries) + scoring tool: `tools/search/` (2026-11-13)
- [ ] Review the test set and add real user queries (needed before KR3.5 can be scored)
- [ ] E9: search normalization (accents/τόνοι, final ς, Greeklish transliteration)
- [ ] E15: hybrid search (BM25 + semantic embeddings): does it beat BM25 alone?
- [ ] Find a source for Greek dishes (recipe-based calculation or a licensed composition table)

---

## O4: Serve it to KnowD1 from our backend *(aspirational)*

Everything in this repo runs on our server. The app is online-only and calls our search API (decision 2026-11-13; KR4.1 and KR4.2 were rewritten from on-device targets, see the check-in log).

| KR | Baseline | Target | Current | Score |
|---|---|---|---|---|
| **KR4.1** Search API p95 response time, measured on the server (without network) | n/a | **< 100 ms** | no API yet. BM25 alone: 1.5 ms p95 on this Mac (E8) | |
| **KR4.2** Full search-index rebuild from `out/` (keyword index + vectors if E15 ships them), all products | n/a | **< 30 min** | keyword index: 2.1 s for 353 k products (E8) | |
| **KR4.3** Attribution + ODbL obligations implemented per `LICENSING.md` | 0 % | 100 % | — | |
| **KR4.4** Documented refresh process (re-download → rebuild → diff report) | none | runs monthly | — | |

**Tasks**
- [ ] E8: measure the FTS5 search index on the real server, including concurrent load (laptop numbers done)
- [ ] Search API service: keyword search now, hybrid if E15 says so
- [ ] Barcode-scan fallback to the OFF API for products not in our database
- [ ] Add attribution strings to the About screen (+ per-screen if D-1 = B)

---

## O5: Every food has a clear, trustworthy picture *(aspirational)*

Strategy and specs: `IMAGES.md`.

| KR | Baseline | Target | Current | Score |
|---|---|---|---|---|
| **KR5.1** Greek packaged products with a **cleaned front photo** that passed review | 0 (20,525 have a raw front photo) | **≥ 18,000** | 0 | |
| **KR5.2** Clean-up pilot: share of cleaned photos rated "good" in human review | n/a | **≥ 85 %** | **31 %** (62 / 200) | |
| **KR5.3** Generic foods & Greek dishes with an **approved** image (AI or other) showing the default portion | 0 | **100 %** of the curated list | 0 | |
| **KR5.4** Images shown with a portion that doesn't match the stored grams (found in review) | n/a | **0** | — | |
| **KR5.5** Foods without any picture that show a **category icon** instead of the generic plate | 0 % | **100 %** | 0 % | |

**Tasks**
- [x] Write the image strategy (`IMAGES.md`)
- [x] Create the project venv (`.venv`) with `rembg` for background removal
- [x] E11: photo clean-up pilot run on 200 Greek products (birefnet-general-lite, 6.1 s per photo, 13 flagged)
- [x] E11: human review of the 200 at `/photo-pilot`: 31 % good → **no-go** for an unattended full run
- [ ] E11b: better cut-outs and/or an automatic judge, scored against the 200 verdicts (**parked**; try OFF's ready-made crop + front-photo models first, see E11)
- [x] E14: product crop with OFF's ready-made models, run on the same 200 (0.08 s per photo, 20 flagged)
- [ ] E14: human review at `/photo-pilot?run=crop`, then decide crop vs cut-out
- [ ] E12: AI image pilot (30 Greek dishes / generic foods). Needs a provider choice + API key
- [ ] E13: category icon set + mapping from OFF food groups
- [ ] Attribution line for cleaned OFF photos on the detail screen (CC BY-SA)
- [ ] In-app "add a photo" flow that uploads to Open Food Facts

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
| 2026-11-12 (pm) | Data browser built (Greece only, with photos). Image strategy written (O5, `IMAGES.md`). E11 photo clean-up pilot run on 200 products and reviewed: only 31 % good, so no-go for an unattended full run; next is E11b. | 0.75 | 0.0 | 0.0 | 0.0 |
| 2026-11-13 | **Architecture decision: all code runs on our backend, and the app is online-only.** So O4's on-device KRs no longer applied. KR4.1 (APK size ≤ 20 MB) became search API p95 < 100 ms on the server. KR4.2 (phone latency) became full index rebuild < 30 min. Search: the browser moved from a LIKE scan to FTS5 + BM25, which is ~1,000× faster on 326 k rows. A draft 100-query test set and the search lab (E15) are built: BM25 reaches 91 % hit@5 vs 83 % for the old search. KR3.5 is not scored until the test set is reviewed. | 0.75 | 0.0 | 0.0 | 0.0 |
