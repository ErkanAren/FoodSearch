# Trial 3: full BiRefNet + gap filling + soft edges (2026-11-16)

**Why:** trial 2 (`stages/01-cutout-all/REPORT.md`) reached 50 %. It was good on cans and bottles but weak on other packs: bites at the pack edge, ragged edges on soft packs. Question: does a bigger model plus a few free post-processing steps fix that, and how slow is it?
**Products:** the same 50 as trials 1 and 2.
**Script:** `stages/00-trial-50/run_trial.py --variant big`. Only new download: the full BiRefNet model (973 MB, checksum verified).
**Review:** http://127.0.0.1:8765/photo-pilot?run=bigmodel

## What changed vs trial 2

- **Main model:** `birefnet-general` (full size) instead of `birefnet-general-lite`. Same box-limited input, max 1024 px.
- **Gap filling:** a second model (`isnet-general-use`, already on disk) fills parts the main mask missed, but **only inside the main mask's convex hull**. That closes bites without letting in background beside bottle necks. It usually added < 0.5 %; on the sardine can it added 3.8 % and closed the bite.
- **Soft edges:** solid inside, the model's soft alpha in a thin band along the outline.
- **Same checks and crop fallback as trial 2.** The 12 images byte-identical to trial 2 kept their trial 2 verdicts (`same_as_trial2`); the reviewer kept all 12 unchanged and rated the other 38.

## Results

**32 of 50 good (64 %).**

| Same 50 products | Good |
|---|---|
| E11: whole-photo cut-out | 14 (28 %) |
| Trial 1: router + per-type method | 20 (40 %) |
| Trial 2: lite cut-out for every type | 25 (50 %) |
| **Trial 3: full BiRefNet + gap filling + soft edges** | **32 (64 %)** |
| Best of trials 1–3 per product | 35 (70 %) |

| Group | Trial 2 | **Trial 3** |
|---|---|---|
| Cut-outs, cans and bottles | 11 / 13 | **12 / 13 (92 %)** |
| Cut-outs, other packs | 7 / 18 (39 %) | **15 / 24 (63 %)** |
| Crop fallbacks | 7 / 17 | 5 / 11 (`mask_notch` 5, `printed_food` 3, `multi_instance` 3) |
| Icon placeholders | 0 / 2 | 0 / 2 |

- **Trial 2 → 3:** 9 bad → good, 2 good → bad (Purè di patate and protein granola, both with a new bite).
- **Flags:** 14 flagged, 8 of them bad.

### Speed (this Mac's CPU)

| | Seconds per product |
|---|---|
| Full BiRefNet | 11.9 |
| Gap-filling model (isnet) | 1.3 |
| **Whole product, end to end** | **13.4** (≈ 2× trial 2) |

Extrapolations:
- **20,525 Greek products ≈ 3 days on this CPU. 300,000 ≈ 45 days**, so a GPU is required. GPU throughput is not measured yet.

## Why the 9 rejected cut-outs failed (checked by eye)

1. **Bites at the pack edge (5):** Purè di patate, protein granola (big), oat biscuits, Loumini, sardines. The solidity check (< 0.90) misses medium bites.
2. **Only part of the pack (2):**
   - Penne: the pack fills the photo, and only the bottom half was kept.
   - Doritos: the right side was lost.
3. **The source photo itself (2):** a crumpled salad-cheese pack, and a pizza box with the lid flap open.

## Conclusion

- **Every step helped:** 28 % → 40 % → 50 % → **64 %**. Cans and bottles are solved (92 %). Other packs are at 63 %.
- **85 % of all products with a good photo looks out of reach** with free models and these photos: even the best trial per product is only 70 %. Part of the gap is bad source photos that no model can fix.
- **Gate: no-go for a full run yet**, but this is the best pipeline so far and the base for the next step.

## Options (none started; waiting for a decision)

1. **Better bite / partial-pack detection** (free, same 50). For example, compare the mask with the detector box along each edge, and flag a pack that touches the photo border.
2. **Automatic judge:** pick cut-out / crop / icon per product, trained or calibrated on the 300+ human verdicts so far. Needed anyway at 300k scale.
3. **Paid cut-out benchmark** on the same 50, to see if it does better on bites and partial packs.
4. **GPU speed test**, for a real 300k cost estimate.
5. **Product question:** split the 85 % target into **quality of shown photos** (e.g. ≥ 95 % good, with a judge) and **coverage** (share of products with a photo; the rest get a category icon).
