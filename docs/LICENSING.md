# Licensing & Attribution

> **Not legal advice.** This summarizes the license files we downloaded plus well-known terms. Before shipping, have a person who can make legal decisions confirm decision **D-1** below.

## TL;DR

| Source | Database license | Contents license | Attribution | Share-alike on our derived DB? |
|---|---|---|---|---|
| **Open Food Facts** (`openfoodfacts/food.parquet`) | ODbL 1.0 | DbCL 1.0 (images: CC BY-SA 3.0) | "© Open Food Facts contributors" + link to https://world.openfoodfacts.org | **Yes** |
| **OpenNutrition** (`opennutrition-dataset-2025.1/`) | ODbL 1.0 | **Modified** DbCL 1.0 | "OpenNutrition" + link to https://www.opennutrition.app **on every screen that shows its data**, in the Play Store listing, on the website and in the in-app legal/about section | **Yes** |

**The OpenNutrition requirement is the one that affects the product.** Its modified DbCL (`LICENSE-DbCL.txt` §2.2) explicitly says a single "About" or "Terms" credit is **not enough**. If any OpenNutrition-derived value appears on a food search, food detail or meal log screen, that screen needs a visible "OpenNutrition" link.

## What ODbL means for a "clean food library"

- Our cleaned or merged library is a **Derivative Database** of each ODbL source it uses.
- If we **publicly use** it (ship it inside the APK, serve it from an API, etc.), we must make the derivative database, or the method used to build it, available under **ODbL**.
- Screens, reports and charts made from it are **Produced Works**. They only need an attribution notice, not ODbL.
- ODbL §4.5 **Collective Database**: a separate, independent database (e.g. KnowD1's own curated Greek dishes typed from scratch) can sit next to the ODbL one without becoming ODbL. Data copied or corrected *from* the ODbL sources is derivative.

## Practical rules for this project

1. Keep a `source` and `source_id` on **every row** of the clean library, so we always know which license applies.
2. Keep KnowD1-authored data (not derived from OFF or OpenNutrition) in a **separate table or file** if we want to keep it proprietary.
3. Plan to publish the open-derived layer (e.g. GitHub or Hugging Face, under ODbL). The build scripts can serve as the "method" too.
4. Do **not** ship OFF product images unless we also handle CC BY-SA attribution per image.
5. Add the attribution strings to the app's About screen now. Add per-screen attribution if OpenNutrition data is used (see D-1).

## Open decision

### D-1: Do we use OpenNutrition data in the shipped app?

| Option | Pros | Cons |
|---|---|---|
| **A. OFF only** for packaged products, plus **public-domain or permissive generic-food sources** (e.g. USDA FoodData Central, which is CC0; CIQUAL, under Licence Ouverte/Etalab 2.0) | No per-screen attribution, simpler UI | More work to build generic foods and household portions ourselves |
| **B. OFF + OpenNutrition "everyday" foods** | 5,299 well-curated generic foods with portions, quickly | "OpenNutrition" link on every screen that shows them |
| **C. OpenNutrition for research only** (benchmarks, gap analysis), nothing shipped | Free to learn from it | Doesn't save build effort |

OpenNutrition's 5,299 "everyday" foods are themselves compiled from USDA SR/Foundation Foods, the Canadian Nutrient File, Frida (Denmark) and the Australian Nutrient Database (see each row's `source` JSON). Going to those **upstream** sources directly may give the same data under friendlier terms. **Verify each upstream license** before relying on it.

**Status:** ☐ undecided. Owner: ___ · Decide by: ___
