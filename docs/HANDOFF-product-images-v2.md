# Handoff v2: clean product images at catalogue scale (≈ 300,000 products)

Follows `HANDOFF-product-images.md` (Experiments A and B). Read that first; this file does not repeat it.

## How to run this handoff (instructions for the agent)

Work **one stage at a time** (section 2). Never start the next stage on your own.

1. **Start:** read both handoffs. Find the existing assets: gold set (200 products, photos, verdict JSON), review tool, Experiment A/B scripts. If you can't find them, ask for their paths before doing anything else.
2. **Per stage:**
   - Put everything in `stages/<NN>-<name>/`: scripts, outputs, manifest.
   - Finish with `stages/<NN>-<name>/REPORT.md`: what ran, the gate numbers, reason-code counts (section 3), surprises, and your go / no-go proposal.
   - **Stop and wait** for an explicit "go" from the human. Record the decision in `docs/decisions.md`.
3. **Human-only steps:** image reviews are done by a person in the review tool. Prepare the batch, say how many images and roughly how long it takes (≈ 3 s per image), then wait for the verdict JSON. Never fill in verdicts yourself or with the judge before Stage 4.
4. **Ask before spending money or bandwidth:** GPU rental, paid API calls (judge, Photoroom), and any download beyond the gold set. Give a cost and time estimate first.
5. **Scope:** only the gold set until Gate 4. A fresh sample at Stage 5. The full catalogue only at Stage 6, after a "go".
6. **Before Stage 3**, section 5 questions 1–3 must be answered. If they aren't, ask.
7. **Environment:** Python 3.11 venv, pinned `requirements.txt`. All state goes in `state.sqlite` (section 4). Make every script resumable.

## 0. Goal and decisions so far

- **Goal:** every product in the ≈ 300,000 Open Food Facts (OFF) catalogue gets an app-ready image: 512 × 512 JPEG (q 88), white background, whole front of pack, upright, nothing else in frame. Target ≥ 85 % "good" on human review, no broken image ever shown.
- **Not doing:**
  - Retailer / Amazon images (copyright, ToS).
  - Fully AI-generated packshots (label text gets invented; a nutrition app can't show a wrong pack).
  - Pure background removal as the default (Experiment A: 31 % good).
- **Assumed (confirm):** a category icon is an acceptable fallback for products whose photos can't be fixed.
- **Language / stack:** Python 3.11, same as the existing scripts. `onnxruntime`, `pillow`, `numpy`, `opencv-python`, PyTorch only for SAM 3. One SQLite file as the state store. No workflow engine.

## 1. Pipeline at a glance

```
OFF images (AWS S3)  →  [1] pick best front photo per product
                     →  [2] route by pack type
                     →  [3] process per type
                           box        → perspective rectify (flat front card)
                           can/bottle → SAM 3 cut-out (text + box prompt)
                           bag/other  → detection crop (Experiment B)
                     →  [4] automatic judge (vision LLM, batch API)
                     →  accept → CDN   |   uncertain → human queue   |   reject → category icon
```

Every step writes its result and a `reason` code to SQLite (section 4), so each product's path is traceable and any step can be re-run alone.

## 2. Stages

Each stage ends at a **gate**: a measured number and a go / no-go decision. Do not start the next stage before the gate is passed and written down in `docs/decisions.md`.

All measurements use the existing **gold set of 200** unless stated. Review at full size (lesson from Experiment A).

### Stage 0. Inventory and baseline (no new models)
1. Finish the human review of Experiment B on the 200 (195 left, ≈ 10 min).
2. Get data with `aws s3 sync --no-sign-request` from the `openfoodfacts-images` bucket (eu-west-3) instead of the OFF web server. The bucket syncs monthly, so it lags OFF by up to a month.
3. From the OFF product dump, count over the full catalogue:
   - products with 0 images, with ≥ 1 front image, with ≥ 2 front candidates (any image, not only the selected one);
   - `packaging_shapes` / `packaging` coverage and the distribution of shapes;
   - share of products with OCR JSON available (it ships in the same bucket).
- **Gate 0:** Experiment B % good is known; we know how much of the catalogue each later stage can reach. Write the numbers down.

### Stage 1. Best-of-N front selection
1. For each product, score **every** uploaded image with the front classifier (Experiment B) plus cheap quality signals: resolution, blur (variance of Laplacian), detector box score, box area.
2. Pick the best candidate. Tie-break: prefer the newest upload (pack redesigns), then the app's language (`front_<lang>`).
3. Re-run the Experiment B crop on the picked image and review the 200 again.
- **Gate 1:** % good with best-of-N vs with OFF's selected front. Keep the selector if it is better.

### Stage 2. Pack-type router
1. Classes: `box`, `can`, `bottle`, `bag`, `jar_tub`, `multipack`, `loose` (fresh / unpackaged), `other`.
2. Source of truth, in order: OFF `packaging_shapes` if present → zero-shot image classifier (CLIP / SigLIP) → `other`.
3. Hand-label the type on the 200 and measure router accuracy.
- **Gate 2:** router accuracy ≥ 90 % on `box`, `can`, `bottle`. Misroutes must fall back to the crop, never to a worse method.

### Stage 3. Per-type processors (each one gated on its own)
- **3a. Box: perspective rectification.** Find the front face's 4 corners (from a segmentation mask → polygon approximation), warp with `cv2.getPerspectiveTransform`, place flat on white with a soft shadow. Sanity checks: output aspect ratio within plausible range; reject if the quad is not convex or a side is < 30 % of the opposite side.
- **3b. Can / bottle: SAM 3 cut-out.** Prompt with text ("can", "bottle") **and** the detector box. Pick the mask that best overlaps the box. Fill interior holes (fixes "cut out the printed food"). First, **check SAM 3's license allows commercial use of outputs.** If it doesn't, use the crop.
- **3c. Everything else:** Experiment B crop.
- **Gate 3 (per processor):** % good on its type in the 200 is higher than the crop on the same products. Otherwise that type keeps the crop.
- Note: SAM 3 needs a GPU. Measure seconds / image on a rented GPU and extrapolate cost to the full catalogue before going further.

### Stage 4. Automatic judge
1. Vision LLM with the review rules as the prompt, temperature 0, output `{verdict: good|bad, reasons: [...], confidence: 0–1}`. Store model name and prompt version with each verdict.
2. Calibrate on every human verdict collected so far (Experiments A, B, Stages 1–3: several hundred labelled images).
3. Choose the threshold where auto-accept precision is ≥ 95 %. Report recall (how much gets auto-accepted).
4. Price it on the batch API before running. Rough public figures are ≈ $0.001–0.002 per image for cheap vision models; **verify on the official price page**.
- **Gate 4:** precision ≥ 95 % at a recall that keeps the human queue under the agreed budget (hours of clicking).

### Stage 5. Fresh confirmation
- New random 200 products (not the gold set), full pipeline end to end, human review.
- **Gate 5:** ≥ 85 % of auto-accepted images good, and the reject / icon share is acceptable.

### Stage 6. Full run
- Sync S3 → run Stages 1–3 (CPU for detection, rented GPU only for SAM 3) → batch judge → human queue for the uncertain band → upload to CDN.
- Resumable: every step skips rows already done for the same `pipeline_version`.

### Stage 7. Keeping it fresh (monthly)
- Delta sync, re-process products whose source image changed, propagate deletions (section 3, D1).

## 3. Edge cases (each one has a reason code so it can be counted)

Report counts per reason code after every stage. A code that grows unexpectedly is the first thing to look at.

### Source and data
| Code | Case | Handling |
|---|---|---|
| `no_image` | Product has no photo at all | Category icon |
| `no_front` | Photos exist, none classified as front | Icon. Do not fall back to a back label |
| `low_res` | Best candidate < 400 px long side | Icon (or crop if judge says good) |
| `stale_pack` | Newer front photo exists but scored worse (redesign) | Prefer the newest if it passes the judge; log both |
| `lang_variant` | Several `front_<lang>` images | Prefer app language, then newest |
| `source_changed` | OFF image id / revision changed since processing | Re-process; key = barcode + image id + revision + pipeline version |
| `source_deleted` | Image removed on OFF (e.g. privacy: a person in the photo) | **Remove from the CDN too** and fall back. This is the most important one to automate |
| `s3_lag` | Image on OFF but not yet in the monthly S3 sync | Pick it up next month; don't hammer the web server |
| `barcode_norm` | EAN-8 / UPC-A / leading zeros map to a different folder path | Normalise per OFF's documented path rule; test with all three formats |
| `dup_image` | Same image file used for several barcodes (variants, merges) | Process once, link many; flag if flavours differ |
| `retail_copy` | Uploaded image is clearly a retailer/brand packshot (watermark, logo overlay) | Reject; licence is doubtful |
| `person_or_nsfw` | Face or inappropriate content in frame | Reject; check OFF/Robotoff image flags |

### Product and pack
| Code | Case | Handling |
|---|---|---|
| `multipack` | 6-pack, tray of cans, box of sachets | Crop only. Never put a multipack onto a single-can template |
| `loose` | Fresh produce, deli, in-store weighed items (often `2…` barcodes) | Crop or icon; no pack template |
| `transparent` | Clear bottle, salad bag, window boxes | Crop; masks fail here |
| `white_on_white` | White pack on white output background | Add soft shadow or thin grey border so edges show |
| `glare` | Metallic / foil / glossy reflection over the label | Prefer another candidate; else judge decides |
| `extreme_aspect` | Spaghetti pack, gum, baguette (aspect > 3:1) | Fit on long side; allow smaller fill; judge with that rule |
| `tiny_in_hand` | Small item held in hand | Crop usually keeps fingers → judge rejects → next candidate |
| `crumpled` | Crushed bag, bent box | No rectification; crop; judge decides |

### Processing
| Code | Case | Handling |
|---|---|---|
| `rotated` | Pack photographed sideways or EXIF wrong | Use OCR text orientation (OCR JSON is in the S3 bucket) to rotate before anything else |
| `wrong_object` | Detector picks the neighbouring product on a shelf | Box must contain the OCR'd product name / brand if available; else judge |
| `printed_food` | Mask selects the food illustration, not the pack | SAM 3 box prompt + hole filling; judge catches the rest |
| `multi_instance` | SAM 3 returns several masks (two cans) | Take the one with best box overlap; if > 2 similar, re-route to `multipack` |
| `bad_quad` | Rectification corners wrong (rounded box, open lid, side visible) | Reject quad by geometry checks → crop |
| `aspect_distort` | Rectified box stretched (misleads size) | Compare to detector box aspect; reject if off by > 25 % |
| `router_wrong` | Type misrouted | Fallback chain always ends at the crop, never at a riskier method |

### Judge and review
| Code | Case | Handling |
|---|---|---|
| `judge_uncertain` | Confidence in the middle band | Human queue (capped); over cap → icon |
| `judge_drift` | Model or prompt changed between runs | Verdicts store model + prompt version; re-calibrate on the gold set after any change |
| `judge_vs_human` | Human overrides judge | Log the pair; add to the calibration set |

### Delivery
| Code | Case | Handling |
|---|---|---|
| `cdn_stale` | Device keeps an old cached image after re-processing | Content-hash in the file name (`<barcode>-<hash8>.jpg`); never overwrite a URL |
| `icon_missing_category` | Product has no category for the icon | Generic "food" icon |
| `attribution` | Every derived image needs a credit line | Store `Photo: Open Food Facts contributors, CC BY-SA, edited` + source URL with the image |

## 4. State store (SQLite)

One row per product, plus a candidates table.

`products`: `barcode`, `chosen_image_id`, `image_rev`, `pack_type`, `type_source` (`off` / `clip`), `method` (`rectify` / `sam3` / `crop` / `icon`), `judge_verdict`, `judge_conf`, `judge_model`, `prompt_version`, `human_verdict`, `reason_codes` (JSON list), `output_path`, `output_hash`, `source_url`, `pipeline_version`, `processed_at`.

`candidates`: `barcode`, `image_id`, `rev`, `lang`, `uploaded_at`, `p_front`, `box_score`, `box_area`, `blur`, `width`, `height`, `rank`.

Re-run rule: a step skips a product when its inputs and `pipeline_version` are unchanged.

## 5. Open questions (owner: product)

1. Is the category icon an acceptable fallback, and what share of icons is acceptable?
2. SAM 3 licence: does it allow commercial use of the generated images?
3. App language(s), for picking `front_<lang>`.
4. Judge provider and budget; human review hours available for the uncertain band.

## 6. Sources

- OFF images on AWS: https://openfoodfacts.github.io/openfoodfacts-server/api/aws-images-dataset
- AWS registry: https://registry.opendata.aws/openfoodfacts-images/
- OFF image download rules: https://openfoodfacts.github.io/openfoodfacts-server/api/how-to-download-images
- Robotoff image flagging: https://openfoodfacts.github.io/robotoff/references/predictions/image-flagging
- SAM 3: https://ai.meta.com/blog/segment-anything-model-3 · https://github.com/facebookresearch/sam3
- Photoroom / Wolt (vendor case, for comparison): https://www.photoroom.com/ms/customer-stories/wolt
