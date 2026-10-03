# Polo Oettinger-style roof spoiler v5: mechanical analysis and print package

Inputs: `input/v5_TOP.stl` and `input/v5_BOTTOM.stl`. Each is one closed body, 1,300 × 147 × 292 mm overall.
Axes: X is the width of the car, Y is up and +Z points to the rear (the direction of airflow).

## 1. What was analysed

**Solver.** Finite-element analysis in CalculiX, using quadratic tetrahedra (C3D10). The model is half the part, with a symmetry plane at x = 0: 85.7k elements, 155k nodes and 465k degrees of freedom.

**Joint and mounting.**
- TOP and BOTTOM are bonded together along their glue overlap (a tied contact). 85% of the overlap nodes tied; the rest are at the edges of the band.
- The whole underside facing the car is held by springs that represent the double-sided tape: 1.1 mm VHB at 60% coverage, 291 cm² of taped area for the full part.
- The end fins (|x| > 545 mm) are left **unbonded**. This is the worst case, because the fin fit to the body is the least certain part of the car model.

**Material: ASA.** The printed-ASA allowables below are assumptions, not datasheet values:

| | 23 °C | 80 °C |
|---|---|---|
| E | 1.8 GPa | 1.1 GPa |
| In-layer tensile | 37 MPa | ~20 MPa |
| Across-layer (layer adhesion) | 20 MPa | ~11 MPa |

- CTE is 95 × 10⁻⁶/K against 12 × 10⁻⁶/K for the steel roof.
- At −30 °C, E is 2.2 GPa.

## 2. Results

Stresses are the smoothed hot-spot values. Single-node spikes at sharp mesh corners are excluded.

| Load case | Peak stress | Max deflection | Notes |
|---|---|---|---|
| Aero at **250 km/h** (q = 2.95 kPa, conservative Cp map, plus gravity) | 4 MPa at the fin roots; 1.5–3 MPa in the skin over the cavity | 2.8 mm at the fin tip | Total lift about 950 N. It scales with speed²: about 255 N at 130 km/h. |
| 150 N push down on the rear lip, centre | 0.7 MPa | 0.03 mm | No concern |
| 100 N pull up on the rear lip, centre | 1.1 MPa | 0.05 mm | Tape peak 0.43 MPa, local |
| 50 N down on a fin tip (hand load) | 6–7 MPa at the fin root | 5.3 mm | The fin feels springy if it isn't taped |
| 50 N outward on a fin tip | 6–7 MPa at the fin root | 5.6 mm | Same as above |
| **Hot roof, 80 °C** (installed at 20 °C) | −3.6 MPa compression in the skin | 0.6 mm skin lift | A geometrically nonlinear run matches the linear one, so **the skin doesn't wrinkle or buckle**. Tape shear strain at the outer ends is 154% (1.7 mm slip). |
| **Cold, −30 °C**, stiff tape (upper bound) | **12–14 MPa spanwise tension** | — | **This case governs.** The part shrinks against the steel roof. It scales at about 0.27 MPa per °C below the installation temperature. |

Figures: `docs/lc1.png` (aero), `docs/lc4.png` (fin hand load), `docs/cold_sxx.png` (cold).

### Safety factors (assumed allowables)

- Aero at 250 km/h, hot roof: 11 / 4 ≈ **2.7** across layers at the fin root.
- Fin hand load at 23 °C: 20 / 7 ≈ **2.9**. At 80 °C: ≈ **1.6**.
- Cold −30 °C, across layers (the sections print on end, so spanwise stress crosses the layer lines): 20 / 14 ≈ **1.4**.
  - This is an upper bound. It assumes fully stiff tape with no viscoelastic relaxation.
  - If it never gets below 0 °C where you are, the stress drops to about 5 MPa, a factor of about 4.
- Tape at 250 km/h:
  - Average peel stress is only 5 kPa.
  - The local peak is 0.65 MPa at the front corner where the unbonded fin begins, against about 0.69 MPa normal tensile strength for VHB 5952. That spot needs tape or sealant (see section 4).
  - At 180 km/h the peak is 0.34 MPa.

### What the analysis changed in the print design

1. **Joints get overlapping splices, not plain butt joints.** In the cold case every seam carries about 35 N/mm, and a butt joint across a 2.5 mm wall is the weak link. Each seam gets a 24 mm wide, 2 mm thick splice that follows the inner skin. That puts the glue line in shear at about 3 MPa.
2. **TOP and BOTTOM seams are staggered by about 108 mm**, so each piece bridges the other's seams.
3. **Sections print standing on end.** The outer skin is then made of perimeters, so there are no stair-step layer lines on the top surface. The cost is the across-layer load in the cold case, which the splices and solvent-welded seams cover.
4. **No internal ribs were added**, as you asked before. The main body is lightly stressed (under 3 MPa at 250 km/h), so ribs aren't needed. The fins are the springy part. The fix for them is tape, not ribs.

## 3. Print files (`print/`), 20 parts, about 2.06 kg ASA

Every file is one watertight body with zero self-intersections, already oriented and placed for a 256 × 256 × 256 mm bed (Bambu X1C, P1S, P1P or A1).

| Part | Qty | Print size (mm) | Orientation |
|---|---|---|---|
| `TOP_L3` / `TOP_R3` (fin ends) | 2 | 222 × 222 × 217 | Inboard cut face on the bed. Tree supports for the hidden cavity end-cap only. |
| `TOP_L2` / `TOP_R2` | 2 | 203 × 202 × 216 | Inboard cut face on the bed. No supports. |
| `TOP_L1` / `TOP_R1` | 2 | 194 × 194 × 217 | Inboard cut face on the bed. No supports. |
| `BOTTOM_C` | 1 | 114 × 114 × 216 | On a cut face. No supports. |
| `BOTTOM_L1` / `BOTTOM_R1` | 2 | 131 × 131 × 215 | On a cut face. No supports. |
| `BOTTOM_L2` / `BOTTOM_R2` | 2 | 148 × 148 × 215 | On a cut face. Minimal supports. |
| `SPLICE_TOP_x…` (joints at x = 0, ±217, ±433) | 5 | about 100 × 100 × 7–11 | Lying flat, tree supports (hidden glue face) |
| `SPLICE_BOTTOM_x…` (joints at x = ±108, ±323) | 4 | about 100 × 100 × 15–19 | Lying flat, tree supports |

`print/assembled_ref/` holds the same parts in car coordinates, for checking the assembly in the slicer. `print/parts_report.json` has the per-part checks:
- splice-to-skin clearance at least 0.13 mm
- clearance to the other skin about 1 mm
- zero interference anywhere

### Suggested Bambu Studio settings (ASA)

- **Printer setup:** 0.4 mm nozzle, 0.16 mm layers, textured PEI with glue stick, bed 100–105 °C, door closed with the chamber warm, part fan 10–30%.
- **Walls:** 4 walls, which makes the 2.5 mm skin fully solid. Use 6 walls on `TOP_L3` and `TOP_R3` (fin root). Infill 40% gyroid for the few thicker zones.
- **Brim:** 8–10 mm outer brim on every section. They are tall, thin parts, so print them one at a time, centred on the bed.
- **Seam:** aligned, placed on the underside or rear edge (in the slicer, rotate the seam to the face that sits against the car).
- **Speed:** slow the outer wall to about 100 mm/s for the best skin. Watch the first 20 mm of each tall part for any wobble.

## 4. Assembly and mounting

1. Sand the cut faces flat and dry-fit everything on the car. Put cling film on the roof first and use it as the assembly jig, so the curvature matches.
2. **Join the TOP:**
   - Solvent-weld the butt faces with ASA/ABS slurry in acetone, or use a structural 2K epoxy or methacrylate.
   - From the open underside, glue each `SPLICE_TOP` across its seam (same adhesive).
   - Work from the centre out.
3. **Join the BOTTOM** the same way, with each `SPLICE_BOTTOM` on the top face across its seam.
4. Glue the BOTTOM into the TOP pocket (3 mm overlap, 0.2 mm glue gap). Fill, sand, prime and paint the seams.
5. **Mount:**
   - Clean with IPA and use 3M 94 adhesion promoter on both surfaces.
   - Use 3M VHB 5952, or an automotive attachment tape of at least 1.1 mm, with as much coverage as possible.
   - **Run the tape continuously along the front edge** so air can't get underneath.
   - **Also tape or bead-bond the fin undersides** where they meet the body. That removes the 0.65 MPa corner peak and the 5 mm fin springiness.
   - Install at 15–25 °C, press firmly and leave it 72 h before a car wash or highway driving.

## 5. Limits of this analysis

- Aero pressures use a conservative Cp envelope (suction −1.2 on top, +1 on windward faces), not CFD.
- The roof and tailgate shape comes from the earlier VW-dimension car model, not a scan. Dry-fit before the final bond.
- The tape is modelled as linear springs. Real VHB is viscoelastic and relaxes thermal stresses over hours, so the thermal cases are on the safe side.
- Material allowables are typical published values for printed ASA. Your filament and settings may differ. A test bar printed on end, pulled by hand, will show quickly whether your layer adhesion is good.
- Mesh: the surface was decimated to 30k + 14k triangles for the FEA. Volume changed by less than 0.01%.

Scripts that reproduce everything are in `work/*.py`. The pipeline runs `halve → dec → tg → classify → build_inp → ccx → post_*`, then `build_print` and `make_parts` for the print files.
