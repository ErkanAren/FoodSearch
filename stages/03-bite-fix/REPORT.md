# Trial 4: colour-based bite repair + partial-pack check (2026-11-16)

**Why:** in trial 3 (`stages/02-big-model/REPORT.md`, 64 % good), 5 of the 9 rejected cut-outs had a bite at the pack edge and 2 kept only part of the pack.
**Products:** the same 50. **Script:** `stages/00-trial-50/run_trial.py --variant bitefix`. Nothing downloaded.
**Review:** http://127.0.0.1:8765/photo-pilot?run=bitefix

## What changed vs trial 3

- **Bite repair:** gaps inside the mask's convex hull or the product box are filled when their colours look like the pack next to them rather than the background. It uses colour histograms at ≤ 512 px.
- **Partial-pack check:** the cut-out must span ≥ 90 % of the product box. First run: it caught no real case and broke one good image (biscuits on a shelf: the box includes the neighbouring packs). Demoted to a flag.
- **Rollback:** a repair that would trigger a *new* fallback is undone (`repair_reverted`). Added after the first run, where it sent Super Cookie to the crop.
- **Masks cached** (`out/masks/`, model alpha as lossless PNG). Post-processing changes now re-run in ≈ 1 min instead of ≈ 15.

## Results

**22 good of 48 rated. Trial 3 had 32 / 50.** A regression.

- 17 images changed vs trial 3, 15 of them rated:
  - **8 good → bad:** FAGE, Peeled Tomatoes, feta cubes, mayonnaise, milk, Choice 0 %, Camino negro, Iliada;
  - **7 bad → bad:** the bitten packs were not fixed well enough;
  - **0 bad → good.**
- **Why** (pixel comparison of trial 3 vs trial 4): the repair filled small bits of background whose colours resemble the pack. Examples: a grey shadow sliver under the FAGE tub, jagged pieces on the Iliada tin, background patches on the tomato can's rim, a sliver next to Choice 0 %. With the reviewer's strict bar, even a few wrong pixels make the image bad.
- **Speed:** ≈ 17 s per product in the first run; the masks were not cached yet and the machine was busy.

## Conclusion

- **No-go.** Colour-based repair is too crude.
- **Trial 3 stays the baseline.** The `bitefix` variant is kept in the script only as a record of this experiment.
- **Bites need a stronger segmentation model** (SAM 3 or a paid service), not post-processing.
- **Kept from this trial:** the mask cache, and the `touches_frame` / `partial_pack` flags as information for a judge.
