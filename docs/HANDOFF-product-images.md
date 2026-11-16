# Handoff: clean product images for a food catalogue

## 1. The problem

We are building a food catalogue for a nutrition app where users log what they eat and how much. **Every food should show a clear, consistent, correctly licensed picture.** A picture must never mislead about the portion size.

There are two kinds of foods:

| | Packaged products (with a barcode) | Generic foods and cooked dishes |
|---|---|---|
| How many | ≈ 27,000 in the current regional catalogue | ≈ 1,000 generic foods + ≈ 150 dishes (planned) |
| Photos today | ≈ 20,500 have a crowd-sourced "front of pack" photo. ≈ 5,400 have none | None |
| Need | Turn amateur photos into clean catalogue images | Create images from scratch |

**This handoff is mostly about packaged products**, where the experiments so far took place.

### The source photos
- They are crowd-sourced phone photos and are very mixed. Problems include: hand-held shots, supermarket shelves and kitchen tables in the background, angled or crumpled packs, glare, dark photos, the product cut off by the frame, and sometimes the back label or nutrition table uploaded as the "front".
- The photos are under a **share-alike license** (attribution required, and edited images must be shared under the same license).
- Typical size is 2,000–4,000 px on the long side, ≈ 0.6 MB each.

### Target output (one per product)
- A 512 × 512 JPEG (quality 88) on a white background, with the product centred and a small margin.
- It must show the **whole front of the pack**, upright. There must be no missing pieces, no hands, no other objects, and it must be the correct side of the pack.
- The images are served from a CDN and cached on the device, not bundled in the app.

### Quality bar
A human reviewer rates each image **good or bad** with the question "would I put this in the app as is?". The bar is strict: a small bite missing from the pack edge, a leftover finger or lid, or the wrong side of the pack all make it bad.

**Target: ≥ 85 % of processed images rated good.** And no broken image may ever be shown: when in doubt, fall back to something safe.

---

## 2. What has been tried

### Experiment A: background removal ("cut-out"). Result: 31 % good, no-go
- **Pipeline:**
  1. EXIF-rotate the photo and downscale it to a 1024 px long side.
  2. Remove the background with `rembg` 2.0.87 using the `birefnet-general-lite` model. It was better than `isnet-general-use`, which was 7× faster but faded or cut parts of packs.
  3. Turn the result into a mask (alpha > 10) and crop to the mask's bounding box.
  4. Pad to a square with an 8 % margin and paste onto white at 512 × 512.
- **Speed:** 6.1 s per photo on a laptop CPU (p95 7.5 s), giving ≈ 30 KB per image.
- **Human review of 200 random products:** **62 good / 138 bad (31 %)**.
- **Failure types:**
  1. Parts of the pack are cut away: a corner, a bite out of the middle, the top of a box.
  2. The model cuts out the **food illustrated on the pack** instead of the pack (a chip from a chips bag, a bowl of cereal from a cereal box, a pizza from a pizza box). These models look for the most salient object, and that is often the printed food.
  3. Leftovers are kept: hands, lids, coasters, a second product behind.
  4. The source photo itself is bad: the product is cut off by the frame, crumpled or angled, dark, or shows the back label instead of the front.
- **Automatic quality flags didn't work.** We flagged: foreground < 3 % or > 97 % of the photo, foreground filling < 35 % of its bounding box, > 25 % semi-transparent mask pixels, and original < 400 px. 12 of the 13 flagged images were bad, but the flags caught only **12 of the 138** bad ones.
- **Mask statistics can't separate good from bad either.** The best simple rule on fill and soft-edge ratio picks a set that is only 48 % good.
- **Lesson:** judging from small thumbnails gave a false ≈ 87 % estimate. **Always review at full size.**

### Experiment B: detection-based crop (no background removal). Result: review in progress
- **Idea:** don't cut the product out. Crop the original photo to the product's bounding box and centre it on white. The pack can never be broken, at the cost of some original background around non-rectangular packs.
- **Models:** two small off-the-shelf models, fine-tuned by the photo source's own community on these kinds of photos. Both are AGPL-3.0, which is fine because we run them offline and ship only the images.
  - **Product detector:** YOLOv8n, ONNX, 12 MB, one class `product`.
    - Input: 1 × 3 × 640 × 640, letterboxed with grey 114, RGB / 255.
    - Output: (1, 5, 8400) = cx, cy, w, h, score. **The coordinates are fractions of the 640 input, not pixels.**
    - We take the highest-score box and treat a score < 0.25 as "no product found".
  - **Front-of-pack classifier:** YOLO11n-cls, ONNX, 6 MB, softmax over [front, other], 95 % reported accuracy.
    - Preprocessing: longest side 448, centre-pad to 448 × 448 with black, RGB / 255.
- **Pipeline:**
  1. Score the photo for "front".
  2. Detect the product box.
  3. Grow the box by 2 %, crop the full-resolution original, and fit it on a 512 × 512 white square with a 5 % margin.
  - Flags: `no_box`, `not_front` (P(front) < 0.5), `small_box` (box < 15 % of the photo), `low_res`.
- **Run on the same 200 products as Experiment A**, so the two methods compare photo by photo:
  - **0.08 s per photo** (≈ 75× faster), ≈ 38 KB per image.
  - 20 flagged: `not_front` 16, `low_res` 4, `no_box` 1.
  - **15 of the 16 `not_front` photos had also been rated bad in Experiment A.** The front classifier is a useful filter on its own.
  - A quick look shows that packs stay whole where the cut-out broke them. The weak spot is leftover background beside bottles and odd-shaped packs.
- **Human review:** only 5 of 200 rated so far (all good). This is the next decision point.

### Other options considered (not tried)
| Option | Notes |
|---|---|
| Better background removal: BiRefNet full size, BEN2 (both MIT) | Slower. Probably still fails on the "printed food" problem |
| Prompted segmentation: text-guided detector + SAM, prompt "product package" | Aimed at the printed-food problem. Heavier setup |
| Mask disagreement: run two segmentation models and flag low overlap | A cheap automatic failure signal |
| RMBG-2.0 | **Avoid:** needs a commercial license |
| Official brand packshots | Best quality, but needs deals. Scraping retailer sites without permission is not allowed |
| Users add photos in the app | Fills gaps over time |
| Category icons (≈ 20, e.g. Fluent Emoji, MIT) | Fallback for products without a usable photo |

---

## 3. Assets available

- **Gold set:** 200 randomly sampled products (fixed, repeatable sample), each with:
  - the original photo,
  - the Experiment A cut-out with a human verdict (62 good / 138 bad),
  - the Experiment B crop with its model scores (front probability, box confidence, box area). Human verdicts are pending.
- **Review tool:** a local web page that shows the original, the cut-out with its verdict, and the crop side by side, with ✓ Good / ✗ Bad buttons. It computes % good, flag precision, missed failures and "% good with either method". Verdicts are saved as JSON (`{product_id: "good" | "bad"}`).
- **Scripts** for both pipelines (Python 3.11, `onnxruntime`, `pillow`, `numpy`, `rembg`), with outputs and a manifest per run.

## 4. Constraints

- **Compute:** a laptop CPU today. A rented GPU is possible for bigger runs. ≈ 20,500 photos: Experiment A ≈ 35 h on CPU, Experiment B ≈ 30–40 min plus ≈ 12 GB of downloads.
- **Download politely:** at most 4 parallel requests, a generic User-Agent, and cache everything.
- **Human review is the real bottleneck.** At ≈ 3 s per image, 20,000 images is ≈ 17 h of clicking, and a future catalogue of ≈ 300,000 would be ≈ 250 h. **Any approach that scales needs an automatic judge**, with humans looking only at the uncertain cases.
- **Licensing:** derived images keep the share-alike license and need an attribution line ("Photo: <source> contributors, <license>, edited"). Use only models whose licenses allow commercial use, and don't ship AGPL models inside the app.
- **Provenance:** for each image, store the source URL, source image ID and revision, the method or model, and the date. When the source photo changes, re-process it.

## 5. Suggested next steps

1. **Finish the Experiment B review** on the 200. Compare crop vs cut-out vs "best of either".
2. **Choose the default per product:** for example the crop by default, the cut-out only where an automatic judge is confident, and a category icon when `not_front` or `no_box`.
3. **Build an automatic judge** and check it against the human verdicts. Options: an image-embedding classifier (CLIP / SigLIP plus logistic regression) or a vision LLM given the review rules. Goal: auto-accept at **≥ 95 % precision** and send the rest to fallback or human review.
4. **Confirm on a fresh sample of 200** before the full run.
5. Later:
   - **Generic foods and dishes:** AI-generated images from one fixed prompt template (same plate, background, light and angle). The image must **show the stored default portion** (e.g. "1 slice ≈ 30 g"). Each image needs a human review and a stored `is_ai_generated` flag. Planned pilot: 30 items × 3 variants, with approval rate and cost per approved image as the metrics.
   - **Category icons** for everything else.
