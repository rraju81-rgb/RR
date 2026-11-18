# Spec sheet: Ducktail roof spoiler (finished part)

A one-page A4 specification of the **finished spoiler as fitted to the car**: the final six-piece design, bonded and painted. It covers only the final part, not the earlier designs or the printing details.

| File | What it is |
|---|---|
| `Polo_Roof_Spoiler_Spec_Sheet.pdf` | The spec sheet (A4, vector text, embedded fonts) |
| `Polo_Roof_Spoiler_Spec_Sheet.png` | The same page as an image (about 2060 × 2920 px) |
| `spec_sheet.tpl.html` | Layout and fixed text; `{{...}}` fields are filled in by `src/build_spec.py` |
| `img/drawing.png` | Dimensioned plan view, side view and centre-line section (`src/drawing.py`, from `../v6/out/E2.stl`) |
| `img/hero.jpg` | Crop of the brochure hero render |

**Where the numbers come from** (nothing is typed by hand):
- Dimensions, chord, thickness, lip angle and plan area are measured from the finished spoiler solid (`spoiler_geometry.json`).
- The aerodynamic table comes from the CFD wind test in `../aero/` (`../aero/results/aero_results.json`): 100 km/h, with and without the spoiler.
- Weight, material, finish and fitting match the brochure and `../v8/README.md`.

**Rebuild** from `spoiler/`: `python3 spec/src/drawing.py`, then `python3 spec/src/build_spec.py` (writes the PDF and PNG; needs Node.js with Playwright).

**Before you share it:** the aerodynamic figures are from a simulation of our modelled car, not a wind-tunnel or road test, and the sheet says so. The fitment line assumes the dry-fit on a real Polo 6R / 6C confirms the fit.
