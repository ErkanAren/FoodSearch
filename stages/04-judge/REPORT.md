# Stage 04: can a local automatic judge learn the reviewer's verdicts? (2026-11-16)

**Why:** at ≈ 300,000 products nobody can review every image. A judge must decide which images are good enough to show. Bad ones get a fallback (crop or category icon), so no broken image reaches the app.
**Script:** `judge_test.py`. Free and local: nothing downloaded, no API, no new review needed.

## Data

- **Every image with a human verdict:** E11 (200), E14 (5), trials 1–4 (≈ 190).
  - Icon placeholders are excluded.
  - Identical images are counted once (file hash).
- **Result: 324 unique images, 37 % good, 200 products.**
- **The reviewer is consistent:** no identical image ever got two different verdicts.

## Method

- **Features:** OFF's CLIP image embedding (ONNX, already on disk) plus 5 simple statistics (object size, fill, fragments, outline length).
- **Model:** logistic regression. Also tried kNN and other regularisation strengths.
- **Fair test:** cross-validation grouped by product, so a product's images are never in training and test at once. 5 random splits.
- **Honest threshold:** chosen inside each training fold to reach the target precision, then applied to the unseen fold.

## Results

| | |
|---|---|
| Ranking quality (AUC, 0.5 = random, 1.0 = perfect) | **0.70–0.77** depending on settings |
| Precision when accepting only the top 10 % / 20 % / 30 % | **≈ 0.6–0.75 / ≈ 0.6–0.7 / ≈ 0.6** |
| Target 95 % (or 90 %) good among accepted images | **never reached**, at any threshold |
| On trial 2–4 images only (the kind we would ship) | AUC 0.72 |

The best settings only lift precision from 37 % (accept everything) to ≈ 70 % (accept the top 10–20 %).

## Why it fails

- **CLIP embeddings describe *what* the product is** (a yogurt tub, a bag of crisps).
- **The reviewer rejects *small defects*:** a bite at the edge, a background sliver, a ragged outline, a finger.
- **Global embeddings barely see those**, and 324 examples are far too few to learn them.

## Conclusion

- **No-go for a local CLIP-based judge.** It cannot guarantee that shown images are good.
- **A judge that looks at details is needed:**
  1. **Vision LLM judge** (e.g. Claude), given the review rules and both the original photo and the cut-out. Scored against the same 324 verdicts before any wider use. Needs a provider choice and an API key; the cost per image is to be priced before running. *Recommended next.*
  2. Defect-specific features, comparing the cut-out with the original photo (missing area at the edges, slivers). Custom engineering with uncertain gain.
  3. Many more human labels (thousands). Slow.
