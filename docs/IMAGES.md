# Food Images: Strategy

Goal: **every food in KnowD1 shows a clear, consistent, correctly licensed picture.** Pictures must never mislead about portion size; this is a carb-counting app.

Related: OKR **O5** (`OKRs.md`) · experiments **E11–E13** (`EXPERIMENTS.md`) · licenses (`LICENSING.md`).

---

## 1. The problem has two halves

| | Packaged products (barcode) | Generic foods & dishes |
|---|---|---|
| Source | Open Food Facts, Greece subset | OpenNutrition `everyday` (5,299), curated generic list (KR3.3, ≥ 1,000), Greek dishes (KR3.4, ≥ 150) |
| Photos today | Some (amateur) | **None** |
| Needed | Clean up + fill gaps | Create from scratch |

### Packaged: Greek OFF products (26,654, counted 2026-11-12)

| Photo type | Products | % |
|---|---:|---:|
| Any photo | 21,294 | 79.9 % |
| **Front** | **20,525** | **77.0 %** |
| …front photo in Greek (`front_el`) | 4,609 | 17.3 % |
| Nutrition table | 11,840 | 44.4 % |
| Ingredients | 8,553 | 32.1 % |
| Packaging | 2,227 | 8.4 % |
| Photos but **no front** (list thumbnail would show a label or ingredient list) | 769 | 2.9 % |
| **No photo at all** | **5,360** | **20.1 %** |

Typical quality problems: hand-held shots, cluttered supermarket backgrounds, angled packs, glare, very different framing from photo to photo.

---

## 2. Options considered

| # | Approach | Best for | Consistency | Cost | License | Catch |
|---|---|---|---|---|---|---|
| 1 | Open Food Facts photos as-is | Packaged | Low | Free | CC BY-SA 3.0, credit per photo | Amateur, 20 % missing |
| 2 | **Automatic clean-up of OFF photos** (background removal → crop → square white canvas) | Packaged | High | Free (open-source models, run locally) | Still CC BY-SA; edits must be shared alike | Some cut-outs fail and need review |
| 3 | Official brand packshots (brand partnerships, GS1 product-data services) | Packaged | Best | Deal / paid | Per agreement | Slow. Copying images from Greek supermarket sites is not allowed without permission |
| 4 | Users add photos (scan → photo → upload to OFF via API) | Packaged gaps | Varies | Free | CC BY-SA via OFF | Needs active users |
| 5 | Icon/emoji sets: Fluent Emoji (MIT), Noto Emoji (Apache 2.0), Twemoji (CC BY 4.0) | Category fallback | Very high | Free | Permissive | ~100–150 foods only; illustrations |
| 6 | Free stock (Unsplash, Pexels) | Generic | Mixed | Free | Permissive (no competing image library) | Manual search; few Greek dishes |
| 7 | Paid stock (Shutterstock, Adobe Stock) | Generic | High per image, mixed overall | Paid | Commercial | Cost; mixed styles |
| 8 | Food-API vendors with images (Nutritionix, Spoonacular, Edamam, FatSecret) | Generic | OK | Subscription | Tied to their API terms | Lock-in; often no storing |
| 9 | **AI image generation** (OpenAI image models, Google Imagen/Gemini, Flux, self-hosted Stable Diffusion) | Generic + Greek dishes | Very high (one template) | Cents per image | Generally usable commercially (check each provider's terms) | Can be wrong → **human review mandatory** |
| 10 | Diabetes portion photo atlases (e.g. *Carbs & Cals*) | Portion photos | Built for this | Licensing deal | Commercial | Only if they license |

**Matching technique (for any "find an image for this name" step):** use an image–text similarity model (CLIP / SigLIP) to rank candidates against the food name. Then filter out small or blurry images, drop near-duplicates (perceptual hash) and send the top picks to a human review screen.

---

## 3. Decision (proposed)

| Food kind | Picture source | Fallback |
|---|---|---|
| Packaged, has a **front** photo | OFF front photo, **cleaned** (option 2) | Original OFF photo if the clean-up fails review |
| Packaged, no front photo | Category icon now; ask users to add a photo later (option 4) | — |
| Generic foods & Greek dishes | **AI-generated**, one style, **showing the default portion**, human-approved (option 9) | Category icon |
| Anything without an image | **Category icon** (~20 icons mapped from OFF `food_groups_tags`; option 5) instead of one generic plate | `no-image.svg` |

Why: it covers 100 % of foods with one consistent look, costs little, keeps licenses clean, and nothing ships without review.

---

## 4. Spec: OFF photo clean-up (option 2)

1. **Select:** the product's `front` photo, preferring `front_el` → product language → `front_en` → any `front_*`. **Never** use a nutrition or ingredients photo as the list thumbnail.
2. **Download** the `full` size from images.openfoodfacts.org (polite: ≤ 4 parallel requests, generic User-Agent, cache locally).
3. **Prepare:** apply EXIF rotation, convert to RGB, downscale so the longest side is ≤ 1024 px.
4. **Remove the background** with an open-source model through `rembg`. Experiment E11 picks the model (speed vs edge quality).
5. **Compose:** crop to the object (alpha > 10), pad to a square with an 8 % margin, place on white `#FFFFFF`, export **512 × 512 JPEG** (q 88).
6. **Auto-QA** (flags the image for a closer look; it never decides alone):
   - `fg_small`: object covers < 3 % of the photo, so the mask probably lost the product.
   - `fg_huge`: object covers > 97 % of the photo, so the background was not removed.
   - `fragmented`: object fills < 35 % of its own bounding box (scattered pieces).
   - `soft_edges`: > 25 % of object pixels are semi-transparent (fuzzy mask).
   - `low_res`: original longest side < 400 px.
7. **Human review:** good / bad, in the browser's photo pilot page.
8. **Keep provenance:** source URL, OFF image key + revision, model, date. When the OFF photo revision changes, re-process.
9. **Attribution:** "Photo: Open Food Facts contributors, CC BY-SA 3.0, background removed", on the food detail screen. Cleaned images are adaptations, so they are shared under CC BY-SA too.

---

## 5. Spec: AI images for generic foods & dishes (option 9)

- **One prompt template.** Example: *"Top-down photo of {food}, {default portion description}, on a plain white round plate, neutral light-grey background, soft daylight, no text, no logos, no hands"*. Keep everything except `{food}` and `{portion}` fixed.
- **Portion rule:** the picture shows the **default portion stored in the `portion` table** (e.g. "1 slice ≈ 30 g", "1 cup cooked ≈ 160 g"). If it can't be shown faithfully, show the food without a plate-sized portion (e.g. a single item) and say so in review.
- **Review checklist:** right food / dish · realistic Greek preparation · portion matches the stored grams · no text, logos or hands · style matches the others. A dietitian signs off on dishes.
- **Metadata per image:** model, version, prompt, seed or settings, date, reviewer, verdict.
- **Label:** keep an `is_ai_generated` flag in the data. Whether to show it in the UI is a product decision.
- Pilot first (E12): 30 items, 3 variants each, then measure the approval rate and cost.

---

## 6. Category icons (option 5)

About 20 icons mapped from OFF `food_groups_tags` level 1 and 2: dairy, cheese, yogurt, bread, cereals, pasta & rice, legumes, fruit, vegetables, meat, fish, eggs, sweets, chocolate, biscuits & cakes, salty snacks, sauces & fats, drinks, sweetened drinks, alcohol. Source: Fluent Emoji (MIT), with the license notice in the app's About screen. See E13.

---

## 7. Size & delivery

- 512 px JPEG ≈ 30–60 KB, so 20 k packaged images ≈ 1 GB. **Don't ship them in the APK.** Serve them from a CDN/bucket and cache on the device. Ship only the category icons (a few KB) inside the app.
- A thumbnail list can use a 256 px variant (≈ 10–20 KB).
