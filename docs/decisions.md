# Decisions log

Newest first. One entry per decision. Who decided, what, why, and what it unblocks.

| Date | Decision | By | Why / notes |
|---|---|---|---|
| 2026-11-16 | **Food categories = USDA WWEIA (172, unmerged) + 11 additions = 183** (`CATEGORIES.md`). One category per product, assigned to all ≈ 327k products, likely by generative AI with the list as fixed choices (max 255). Processing state and sugar-free are tags, not categories | Product owner | Compared with our own 115-list, FoodEx2 (EU) and HYDRIA (GR, uses FoodEx2): `CATEGORIES-vs-WWEIA.md` |
| 2026-11-16 | **A category icon is an acceptable fallback** for any product without a good photo (answers handoff v2 §5 Q1) | Product owner | Unblocks the "judge → show photo or icon" design. Icon-set size: under discussion for the ≈ 300k catalogue |
| 2026-11-16 | **Local automatic judge (CLIP embedding + logistic regression): no-go.** Ranking AUC 0.70–0.77 on 324 rated images; never reaches 90 % precision (≈ 70 % at best). CLIP sees *what* the product is, not small defects. **Next proposed:** vision-LLM judge scored against the same verdicts (needs provider + API key) | Assistant (measured), owner to confirm next step | `stages/04-judge/REPORT.md` |
| 2026-11-16 | **Trial 4 (colour-based bite repair): no-go**, 22 / 48 good vs 32 / 50 in trial 3. The repair added background slivers that made good images bad. **Trial 3 stays the baseline** | Product owner (review) | `stages/03-bite-fix/REPORT.md` |
| 2026-11-16 | **Trial 3 (full BiRefNet + gap filling + soft edges): best so far, 32 / 50 good (64 %)**. Cans and bottles 92 %, other packs 63 %. 13.4 s per product on this Mac (≈ 2× trial 2), so a GPU is required for 300k. Still a no-go for a full run. **Next step open:** better bite detection, automatic judge, paid benchmark, GPU speed test, or split the 85 % target into quality + coverage | Product owner (review) | `stages/02-big-model/REPORT.md`. Real catalogue size is ≈ 300,000 products (said 2026-11-16) |
| 2026-11-15 | **Trial 2 (box-limited cut-out for every pack type): no-go for a full run.** 25 / 50 good (50 %). Cans and bottles 85 %, other packs 39 %. **Next step still open:** SAM 3 test, a paid cut-out benchmark (recommended first), or ship cut-out for cans and bottles + crop elsewhere | Product owner (review) | `stages/01-cutout-all/REPORT.md` |
| 2026-11-15 | **Trial 1 (v2 pipeline as in the handoff): no-go** as is. 20 / 50 good (40 %). The box-limited cut-out scored 85 % on cans and bottles; the crop only 26 % | Product owner (review) | `stages/00-trial-50/REPORT.md`. Led to trial 2 |
| 2026-11-15 | Run a quick end-to-end **trial of the v2 image pipeline on 50 products** before the staged rollout in `HANDOFF-product-images-v2.md` | Product owner | Check speed and quality first. Result: `stages/00-trial-50/REPORT.md` (review pending) |
| 2026-11-15 | Trial assumptions, **not confirmed**: app language order Greek → English for picking `front_<lang>`; a category icon is the fallback | — | Handoff v2 §5 questions 1 and 3 are still open |
| 2026-11-13 | All code runs on our backend; the app is online-only | Product owner | See `OKRs.md` check-in log |
| 2026-11-12 | E11 background removal: **no-go** for an unattended full run (31 % good) | Product owner (review) | `EXPERIMENTS.md` E11 |
