# Trial 50: v2 image pipeline, end to end (2026-11-15)

**Why:** before the staged rollout in `docs/HANDOFF-product-images-v2.md`, check on 50 products whether the whole pipeline is fast and works well.
**Products:** the first 50 of the 200-product gold set (the same sample as E11 / E14).
**Script:** `run_trial.py` (resumable, downloads cached). **Review:** http://127.0.0.1:8765/photo-pilot?run=trial50

## What ran

1. **Best-of-N front.** Every uploaded photo of each product (286 photos, 1–121 per product, median 2) was downloaded from the S3 archive at 400 px, with its OCR file. Each photo was:
   - turned upright using the OCR text direction,
   - scored with the front classifier, the product detector, sharpness and resolution.

   The best one wins. On near-ties we keep the OFF-selected front, then prefer the newest upload, then Greek → English.
2. **Pack-type router.** It uses `packaging_shapes` from the product data when present (only 6 % of Greek products have it). Otherwise it uses zero-shot CLIP (OFF's `clip-vit-base-patch32` ONNX). Below 50 % confidence the type is `other`.
3. **Processor by type:**

   | Type | Method | Falls back to the crop when |
   |---|---|---|
   | Box | Perspective rectification | Bad corners, > 25 % distortion |
   | Can / bottle | Cut-out inside the detector box (BiRefNet-lite + hole filling) | The mask covers < 50 % of the box, or has a bite (solidity < 0.90) |
   | Everything else | Detection crop (E14) | — |

   - **SAM 3 was replaced in this trial.** Its weights need manual approval on Hugging Face and a GPU. Its license does allow commercial use of outputs.
   - **No AI judge:** you review the 50 instead.

## Results (automatic part)

| | |
|---|---|
| Processed | 50 / 50 |
| Methods | crop 34 · cut-out 13 · rectify 1 · icon 2 |
| Best-of-N changed the photo | 5 (2 clear wins: the OFF "front" was the back label / ingredient list) |
| Rotated upright with OCR | 5 |
| Not in the S3 archive yet (`s3_lag`) | **3 of 50 (6 %)**, fetched from the OFF web server instead |
| Icon (no usable front photo) | 2. Both had been rated bad before; one front looked fine to the eye (classifier miss) |

### Speed (cold run, this Mac's CPU)

| Step | Total for 50 | Per product |
|---|---|---|
| Download all candidates (400 px + OCR, 4 parallel) | 75 s | 1.5 s |
| Score candidates | 16 s | 0.3 s |
| Download winners (full size, in the background) | hidden | — |
| Route (CLIP) | 7 s | 0.15 s |
| Process | 141 s | 2.8 s (crop ≈ 0.2 s, cut-out ≈ 6–9 s) |
| **Whole run** | **4 min 11 s** | **≈ 5 s** |

Extrapolations:
- **20,525 Greek products ≈ 28 h** on this Mac as is. Cut-outs are ≈ 85 % of the processing time, so a GPU for cut-outs, or fewer cut-outs, is the main speed lever. Downloads would come from a bulk S3 sync.
- **≈ 300,000 products:** ≈ 17 days on this CPU. That needs a rented GPU for the cut-outs.

### Reason codes
- **Problems:** `router_unsure` 11 · `no_front` 2 · `bad_quad` 2 · `printed_food` 1 · `mask_notch` 1 · `person_or_nsfw` 1
- **Info:** `router_clip` 45 · `lang_variant` 7 · `rotated` 5 · `front_changed` 5 · `s3_lag` 3

## Problems found and fixed during the trial

1. **Router v1 sent most products to `multipack` / `loose`.** Rewording the prompts as product photos and taking the best prompt per type (v2) helped. Even so, it is **≈ 60 % right by eye**:
   - box: precise (7 of 8) but finds only half of the real boxes;
   - can: 3 of 3;
   - bottle: ~6 of 10.

   **Zero-shot CLIP will not pass Gate 2 (≥ 90 %).** A small classifier trained on hand-labelled pack types is needed.
2. **"Newest upload wins ties" swapped clean OFF fronts for hand-held photos.** Now a near-tie keeps the OFF-selected front.
3. **Cut-outs that bite into the pack** (sardine can) are now caught by a solidity check and fall back to the crop.
4. **Safe-search "racy" flagged a cola bottle.** Now only `adult` and `violence` count.
5. **S3 lag:** the archive was missing 3 of 50 products. There is now a web-server fallback for those, labelled `s3_lag`.

## Still open

- **The router misroutes some products.** The penne bag was routed to `can` with 88 % confidence, and the cut-out took a bite out of it. Misroutes into cut-out are the riskiest error.
- **Box rectification ran only once** (4 routed, 2 bad quads, 1 printed-food fallback). Too few to judge.
- **Not built yet:** the AI judge (Stage 4), the OCR "wrong object" check, and duplicate-image linking.

## Human review (2026-11-15)

**20 of 50 good (40 %).** On the same 50 products the E11 whole-photo cut-out scored 14 of 50 (28 %). Better, but far from the 85 % target.

| Method | Good | Note |
|---|---|---|
| **Cut-out inside the detector box** (cans / bottles) | **11 / 13 (85 %)** | Bottles 9 / 10. The 2 bad ones: a milk carton routed as a bottle, and the penne bag routed as a can |
| Crop (everything else) | 9 / 34 (26 %) | The reviewer rejects most crops: original background is left around the pack |
| Box rectification | 0 / 1 | Too few to judge |
| Icon placeholder | 0 / 2 | Expected: a placeholder, not a real icon |

- **Rotation with OCR worked on all 5.** The 4 rejected ones are crops with background or crumpled packs, not rotation errors.
- **Best-of-N changed the photo 5 times:** 3 good, 2 bad.
- **Flags caught 13 of the 30 bad images.**

**What this tells us:**
1. **The reviewer wants a clean cut-out on white.** The crop is only a safe fallback, not a look they accept.
2. **Limiting the cut-out to the detector box, plus the shape checks, made it work: 85 % vs 31 % for E11's whole-photo cut-out.** The box keeps the model on the product, and the checks send broken masks to the fallback.

## Gate

- **Result: no-go for the full v2 pipeline as is** (40 %).
- **Proposal (next trial, same 50):** use the **box-limited cut-out for every pack type**, not only cans and bottles. Keep the checks and fall back to the crop.
  - Only the ≈ 37 changed images need a new review (≈ 3 min).
  - If this reaches ≥ 80 %, the pack-type router and the box rectification can be **dropped**, which makes the pipeline simpler.
  - Cost: ≈ 7 s per product on this Mac's CPU, ≈ 40 h for the 20,525 Greek products, or much less on a GPU.
- **Follow-up done:** trial 2, `stages/01-cutout-all/REPORT.md`. Result: 50 % good. The cut-out works for cans and bottles but not for other packs.
