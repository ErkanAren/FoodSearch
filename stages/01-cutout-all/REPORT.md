# Trial 2: box-limited cut-out for every pack type (2026-11-15)

**Why:** in trial 1 (`stages/00-trial-50/REPORT.md`) the cut-out limited to the detected product box scored **11 / 13 (85 %)** on cans and bottles. The crop was only 26 % good. Question: does that cut-out also work for bags, boxes, tubs and jars? If yes, the pack-type router and the box rectification can be dropped.
**Products:** the same 50 as trial 1.
**Script:** `stages/00-trial-50/run_trial.py --variant cutout-all`. It reuses trial 1's cached photos; nothing was downloaded.
**Review:** http://127.0.0.1:8765/photo-pilot?run=cutoutall

## What ran

- **Same steps as trial 1:** best-of-N front (with the same choices) and OCR rotation.
- **No router:** every product with a detected box gets the box-limited cut-out (BiRefNet-lite + hole filling).
- **Fallback to the trial 1 crop** when:
  - the mask covers < 50 % of the box (`printed_food`),
  - it has a bite (solidity < 0.90, `mask_notch`),
  - or it finds two similar objects (`multi_instance`).
- **Carried-over verdicts:** for images byte-identical to trial 1 (31 of 50), the trial 1 verdict was copied and labelled `same_as_trial1`. The reviewer kept all 31 unchanged and rated the 19 new images.

## Results

**25 of 50 good (50 %).**

| Same 50 products | Good |
|---|---|
| E11: whole-photo cut-out | 14 (28 %) |
| Trial 1: router + per-type method, crop for the rest | 20 (40 %) |
| **Trial 2: box-limited cut-out for every type** | **25 (50 %)** |
| Best of trial 1 and trial 2 per product | 26 (52 %) |

| Group | Good |
|---|---|
| Cut-outs, cans and bottles (same images as trial 1) | 11 / 13 (85 %) |
| **Cut-outs, other packs (new in trial 2)** | **7 / 18 (39 %)** |
| Crop fallbacks (`mask_notch` 9, `printed_food` 7, `multi_instance` 1) | 7 / 17 (41 %) |
| Icon placeholders | 0 / 2 |

- **Trial 1 → 2:** 6 bad → good, 1 good → bad (the oat-biscuit box: its good crop became a cut-out with a bitten corner).
- **Speed:** 6 min for 50, **≈ 7 s per product** on this Mac's CPU. Processing is 95 % of that, all of it the cut-out model. That gives ≈ 40 h for 20,525 products on this CPU.

## Why the new cut-outs failed (11 rejected, checked by eye)

1. **Bites at the pack edge, where the printed food or a hand touches the edge:** granola box, oat-biscuit box, milk carton, Loumini, feta tub. The solidity check catches large bites only.
2. **Soft, crumpled or see-through packs get ragged edges:** salad-cheese pack, vacuum-packed halloumi, honey jar, wet-wipes pack, a clear bag.
3. **Leftovers:** fingers, a spoon.

## Conclusion

- **The free local models reach ≈ 50 % on this sample.** They are good for cans and bottles (85 %) and weak for everything else (≈ 40 %).
- **Segmentation quality on soft packs and boxes is the bottleneck.** Stricter checks would only move more products to the crop, which the reviewer mostly rejects.
- **Gate: no-go** for a full run with this pipeline.

## Options (none started; waiting for a decision)

1. **SAM 3 with a box prompt** (the handoff v2 plan). Needs Hugging Face access approval from Meta and a GPU: a few dollars rented for 50 images, or slow on this Mac.
2. **A paid cut-out service as a benchmark** (e.g. Photoroom) on the same 50, ≈ $1–2 (price to check). It tells us whether 85 % is reachable with these amateur photos at all. *Recommended first.*
3. **Ship what works today:** cut-out for cans and bottles, crop elsewhere (≈ 50 % overall).

**Follow-up done:** trial 3 (full BiRefNet + gap filling + soft edges), `stages/02-big-model/REPORT.md`. Result: **64 %** good.
