# Pickleball paddle designs – Elongated & Hybrid (REV C)

Two 39 cm paddles traced from your hand-made templates and sketches. Each is a carbon-fibre /
wave-rib sandwich, fitted with your rev-8 printed grip and locked by a screw in the butt. The repo
holds the engineering drawings, full-size templates, DXF cut profiles, print-ready STLs of the rib
support, the 3-D model (STEP / STL / 3MF), photoreal renders and a finite-element stress analysis.

![3D render](output/render/paddles_3d_hero.png)

## Specification

| | **Elongated** (PB-EL-001) | **Hybrid** (PB-HY-001) |
|---|---|---|
| Overall length (incl. the grip base) | 390 mm | 390 mm |
| Blade (face) length | 260 mm | 260 mm |
| Handle | 130 mm incl. the 5 mm grip base, body 30 × 16 mm | same |
| Blade width | **200 mm** | **190 mm** |
| Thickness | 16 mm: 4 mm carbon + 8 mm wave-rib core + 4 mm carbon | same |
| Head shape | Square head, **R48** tip corners | Domed head, **R150** crown + **R30** shoulders (dome rise 49.1 mm) |
| Blade → handle | R25 shoulder → 30° straight taper → R15 throat fillet | same |
| Straight sides | y = 202.2 … 342.0 mm from the butt | y = 199.3 … 340.9 mm from the butt |
| Body profile area | 491 cm² | 459 cm² |
| Grip | Printed PLA grip (rev 8, any of the ten designs), 135 mm long, slot 30.2 × 16.0 mm; 37.4 × 30.6 mm and about 114.5 mm (4½ in) round at mid-grip; DIN 7984 M3 screw lock | same |
| Mass with the grip (3D model) | 849 g, balance point 236 mm from the butt | 802 g, 230 mm |
| USA Pickleball L + W ≤ 609.6 mm (24 in) | 590 mm ✔ (19.6 mm margin) | 580 mm ✔ (29.6 mm margin) |
| USA Pickleball L ≤ 431.8 mm (17 in) | 390 mm ✔ | 390 mm ✔ |

Every profile is lines and tangent arcs, symmetric about the centre line. An edge guard counts
towards the USA Pickleball limits, so keep it within the margins above.

## Construction

| | |
|---|---|
| ![Cutaway](output/render/paddles_3d_cutaway.png) | ![Exploded view](output/render/paddles_3d_exploded_elongated.png) |
| ![Exploded view, hybrid](output/render/paddles_3d_exploded_hybrid.png) | ![Printed grip, M3 screw and insert](output/render/paddles_3d_handle.png) |

- **Face sheets.** Two identical 4 mm woven carbon/epoxy plates, cut to the body profile
  (`*_profile.dxf`, template sheet 2). Outer edges R0.8.
- **Rib support (the core), 8 mm, 3D-printed in PA-CF and printed flat** (sheet 3 of each drawing):
  - A closed 6 mm perimeter frame covers the whole side, as marked on your sketch.
  - Inside it is the sinusoidal wave rib from your sketch: pitch 18 mm, wall 1.6 mm, centre-line
    amplitude 4 mm. The flutes run along the paddle. The crests are cut flat where they meet the
    sheets, which gives 4.25 mm wide bond lands on both faces. The wave walls connect the two faces.
  - The core is solid from its butt to y = 150 mm (handle and throat). Each flute starts with a
    45° run-out, which prints without support.
  - Print-ready STLs, in one piece or two: see [Rib support STLs](#rib-support-stls).
- **Grip.** Your printed rev-8 grip slides over the handle: see [Printed grip](#printed-grip). Its
  5 mm solid base is the butt of the paddle, so the sheets and the rib support start at y = 5 mm and
  the overall length stays 390 mm.
- **Screw lock.** A DIN 7984 M3 × 12 low-head screw goes up through the grip base into an M3 × 5.7
  brass heat-set insert in the butt of the rib support: bore Ø4.0 × 7, then Ø3.2 × 15 clearance, so
  an M3 × 16 also fits.

## Rib support STLs

![Rib support, two-piece print](output/render/paddles_3d_rib_support.png)

`python tools/export_rib_support.py` writes them to [`output/rib_support/`](output/rib_support).
Each file lies flat in its print orientation (z = 0 … 8 mm), centred on x = y = 0, in mm, and is a
single closed body.

| File | Size (mm) | Mass, PA-CF (PETG / PLA) | Printer bed |
|---|---|---|---|
| `elongated_rib_support_1piece.stl` | 200 × 385 × 8 | 178 g (192 / 187 g) | ≥ 391 × 206 mm (large format) |
| `elongated_rib_support_2piece_A.stl` + `_B.stl` | 200 × 237.4 and 200 × 152.4 | 99 + 95 g | 256 × 256 or 250 × 210 mm |
| `hybrid_rib_support_1piece.stl` | 190 × 385 × 8 | 170 g (183 / 179 g) | ≥ 391 × 196 mm (large format) |
| `hybrid_rib_support_2piece_A.stl` + `_B.stl` | 190 × 237.4 and 190 × 152.4 | 98 + 87 g | 256 × 256 or 250 × 210 mm |

- **One piece.** The rib support exactly as drawn on sheet 3, with the M3 insert bore in the butt.
  It is 385 mm long, so it needs a large-format printer.
- **Two pieces.** For a normal 256 mm bed. The joint is at y = 240 mm, across the blade, where a
  7 mm solid band runs across the flutes. The flutes run out into the band at 63°, which prints
  without support. The band is cut by a dovetail joint: tabs on piece A (handle and lower blade),
  sockets in piece B (tip), 20 mm pitch, 5 mm deep, kept 4 mm clear of the frame, 0.1 mm clearance per
  side. Drop B onto A's tabs (they lock in the plane), glue the joint with the same epoxy, then bond
  the face sheets, which bridge the joint. The band adds 15–16 g.
- **Printing.** 100 % infill (the 1.6 mm walls are 4 perimeters of a 0.4 mm nozzle), 0.2 mm layers,
  no supports. Dry the PA-CF first. PETG or PLA are fine for a fit check, but the analysis assumes
  PA-CF.
- Checks (closed mesh, bodies, volume, size, bed fit) are in `rib_support_report.json`.

## Printed grip

![Grip interface drawing](output/grip/PB-GR-002_printed_grip_interface.png)

The grip is your rev-8 printed grip (`pickleball_grips/` on branch `claude/kind-volta-vs8ck6`, commit
`c594433`). All ten designs share the same interface, so any of them fits either paddle. Drawing
[`PB-GR-002`](output/grip/PB-GR-002_printed_grip_interface.pdf) shows how it fits:

- 135 mm long, with a solid 5 mm base. The slot is 30.2 × 16.0 mm and 130 mm deep, with a 1 mm
  lead-in. The head walls are at least 3.5 mm thick.
- Both end walls are slit over the top 20 mm (y = 115 … 135). The paddle's throat starts to flare at
  y = 130, inside the grip's head, and the slits let the flare pass.
- The screw goes through a Ø3.5 hole with a Ø6.2 × 2.2 counterbore, which leaves 2.8 mm of PLA under
  the head. Tighten it by hand (about 0.5 N·m) with a low-strength threadlocker so the base doesn't
  crack.
- The drawings and masses use CARBON MATRIX: 61 g in PLA, 37.4 × 30.6 mm and about 114.5 mm (4½ in)
  round at mid-grip. The renders show CARBON MATRIX on the Elongated and VORTEX GRIP on the Hybrid.

**Check the fit before printing all ten.** The slot (16.0 mm) is the same as the nominal handle
thickness (4 + 8 + 4 = 16 ±0.3 mm). The real thickness depends on the sheets and the two glue lines,
and the earlier 16.2 mm slot was loose. Measure the bonded handle, then print the fit-test coupon
(`reference/grips/fit_test_slot.stl`: slots 15.6 / 16.0 / 16.4 mm, marked by one, two and three
grooves; also drawn on PB-GR-002) and try the handle in each slot. If 15.6 or 16.4 fits better,
regenerate the grips with `SLOT_T` in `pickleball_grips/scripts/grip_core.py`.

## Stress analysis

[`output/fea/paddle_stress_report.pdf`](output/fea/paddle_stress_report.pdf) is the full report:
model, materials, load cases, contour plots, the design iteration, mass and recommendations.

- **Method.** Linear static analysis in CalculiX: a half model with ≈0.9 M degrees of freedom and
  quadratic tetrahedra, the grip clamped, and a 500 N ball impact on a Ø30 mm patch. The impact
  is applied once at the sweet spot (y = 265 mm) and once at the tip (y = 345 mm). Modal analysis
  uses the same support.
- **REV C.** The changes (printed grip, M3 insert, body from y = 5 mm instead of 4 mm) are all at the
  butt, below or inside the clamped band (y = 14 … 112 mm), so the results below stand. The report's
  mass table is updated.

| Tip impact, 500 N (worst case) | Elongated | Hybrid | Allowable |
|---|---|---|---|
| Deflection (sweet spot / tip) | 2.25 / 3.85 mm | 2.24 / 3.84 mm | – |
| Carbon face sheets, fibre stress | 141 MPa (RF 3.6) | 137 MPa (RF 3.7) | 500–600 MPa |
| Printed core, von Mises | 17.5 MPa (RF 2.6) | 17.6 MPa (RF 2.6) | 45 MPa |
| Bond line, peel | 4.8 MPa (RF 1.03) | 4.9 MPa (RF 1.03) | 5 MPa |
| Bond line, shear: 99th percentile in the hot band | 5.4 MPa (RF 1.49) | 5.5 MPa (RF 1.45) | 8 MPa |
| Bond line, shear: local peak | 10.1 MPa (RF 0.80) | 10.1 MPa (RF 0.79) | 8 MPa |
| First bending mode (grip held) | 105 Hz | 112 Hz | – |

![Bond-line shear](output/fea/fea_bond_shear.png)

What the results mean:

1. **The carbon and the core have large margins.** The face-sheet stress concentrates in the
   throat. That is why the R15 throat fillet matters.
2. **The adhesive bond between the core and the sheets is the critical item.** The first core
   design had square flute ends, and the bond peeled there at 15.2 MPa (RF 0.33). The 45° run-out
   and wider lands bring peel down to 4.9 MPa.
3. **Bond shear still peaks locally.** It reaches 10.1 MPa on the centre lands just above the solid
   zone, where the blade's shear funnels into the 30 mm throat. Across that band the value is
   about 5.5 MPa. Use a structural epoxy rated for nylon, abrade and prime both surfaces, leave a
   fillet along every land edge, and confirm the bond strength with lap-shear coupons. If needed,
   thicken the centre walls or extend the solid zone (see §7 of the report).
4. **Weight.** With the grip the paddles weigh 849 g and 802 g, about 3.6–3.8 × a typical 210–240 g
   paddle. The two 4 mm carbon sheets alone account for 71–72 %. A playable paddle would need about
   0.5–1 mm sheets on a lighter, thicker core. As drawn it is very strong, but suited to a prototype
   or a training paddle.

## Output files

| File | What it is |
|---|---|
| [`output/paddle_drawing_set.pdf`](output/paddle_drawing_set.pdf) | All 7 drawing sheets in one PDF |
| `output/<design>/*_sheet1_general_arrangement.(pdf/svg/png)` | **General arrangement**, A3, 1:2, first angle: front view with the grip, side view with the 4/8/4 lay-up, section A–A through the wave core, section B–B through the grip, isometric view, notes |
| `output/<design>/*_sheet2_template_1to1.(pdf/svg/png)` | **Full-size body template**, A3 portrait, 1:1: tangent points, arc centres, coordinate table, core-frame and solid-zone reference lines, scale-check bars |
| `output/<design>/*_sheet3_rib_core.(pdf/svg/png)` | **Rib support**: plan view 1:2 with lands, flute run-outs and the two-piece joint line, section C–C across the wave 2:1, section D–D through the run-out 2:1, print and bonding notes |
| `output/grip/PB-GR-002_printed_grip_interface.(pdf/svg/png)` | **Printed grip – paddle interface** (both paddles): handle in the grip, sections E–E and G–G across the grip, section F–F through the screw, insert and bores, the fit-test coupon, bill of materials, notes |
| `output/<design>/*_profile.dxf` | 1:1 cut profile of the face sheets (mm) for CNC / laser: closed polyline with true arcs |
| `output/rib_support/<design>_rib_support_1piece.stl`, `…_2piece_A.stl`, `…_2piece_B.stl` | **Print-ready rib support**, one piece or two, plus `rib_support_report.json` |
| `output/cad/<design>_assembly.step` | 3-D assembly: sheets, rib support, screw and insert (named solids) |
| `output/cad/<design>_assembly.3mf` | The same assembly with the printed grip (a mesh, so it is not in the STEP) |
| `output/cad/<design>_rib_core.step` / `.stl`, `output/cad/<design>_<part>.stl` | The rib support as one piece, and every other part, in mm |
| `output/render/paddles_3d_*.png` | Photoreal renders: hero, cutaway, exploded (each design), handle close-up, two-piece rib support |
| `output/render/paddles_2d_render.(png/svg)` | 2-D presentation render (face and 3/4 views) |
| `output/fea/paddle_stress_report.pdf`, `output/fea/fea_*.png` | Stress report and its figures |
| `analysis/fea/*.json`, `analysis/mass_properties.json` | Raw results: peak stresses with locations, reserve factors, bond profile, frequencies, masses |
| `reference/grips/*.stl` | Copies of the CARBON MATRIX and VORTEX GRIP STLs and the fit-test coupon from the grip branch (used by the drawings, the 3MF and the renders) |
| [`reference/cad_outline_vs_your_templates.jpg`](reference/cad_outline_vs_your_templates.jpg) | The CAD outline overlaid on your template photos |

**Printing the template.** Print the sheet-2 PDF on A3 at **100 % / "Actual size"**, with no
fit-to-page. Check the 100 mm and 50 mm bars before cutting.

## How the shapes were derived

The specified dimensions (390 overall, 260 blade, 130 × 30 handle, 200 / 190 wide, 16 thick) are
exact. The radii and the taper angle were measured from your photos. The elongated values come from
the white template, segmented and scaled to 200 × 390. The hybrid values come from the pen sketch,
rectified to the 190 × 260 blade.

| Feature | Measured (left / right) | Used |
|---|---|---|
| Elongated tip corners | R47.6 / R47.8 | R48 |
| Hybrid crown | ≈R150 | R150 |
| Hybrid crown shoulders | R26.6 / R27.4 | R30 |
| Bottom shoulder radius | R21.7 / R26.0 (EL), R25.0 / R27.3 (HY) | R25 |
| Taper angle | 29.1° / 30.2° (EL), 28.2° / 30.6° (HY) | 30° |
| Throat | EL: hidden under tape, almost sharp; HY: ≈R15 | R15 |

The CAD outline matches your elongated template's corners and sides to within about 1 mm, and your
hybrid sketch to about 1 mm RMS everywhere. On the **elongated**, the bottom taper sits about 5 mm
higher than the paper template. That is because the CAD keeps the straight handle at exactly 130 mm
and adds the same R15 throat fillet as the hybrid. Your template's throat is almost a sharp corner,
which concentrates stress, and your pencil arcs show you were already considering R12–R25 there. If
you want the taper exactly where the template is, set `throat_r` to about 6 mm.

## Regenerating / changing the design

```bash
pip install -r requirements.txt
python -m playwright install chromium     # one-off, for PDF/PNG export
python build.py                           # drawings, templates, DXF, 2-D render
python tools/export_rib_support.py        # print-ready rib-support STLs, one piece and two
python tools/export_cad.py                # STEP / STL / 3MF + analysis/mass_properties.json
python tools/export_cad.py --grip 03_tessel_block   # the same with another of the ten grips
python tools/render_3d.py                 # photoreal renders (Blender 4.x with Cycles on PATH)
# stress analysis (gmsh + CalculiX; a static case needs about 11 GB RAM and 10 min on 4 cores)
python tools/run_fea_case.py elongated WORK/static_elongated
python tools/run_fea_case.py hybrid    WORK/static_hybrid
python tools/run_fea_case.py elongated WORK/modal_elongated --modes 6 --mesh 3.0 5.0
python tools/run_fea_case.py hybrid    WORK/modal_hybrid    --modes 6 --mesh 3.0 5.0
python tools/run_fea_case.py elongated WORK/baseline_elongated --set rib_amp=3.6 runout_len=0   # optional
python tools/fea_report.py --work WORK
```

A grip STL that is not in `reference/grips/` is copied from the grip branch the first time it is
needed, so fetch that branch first (`git fetch origin claude/kind-volta-vs8ck6`).

The inputs live in `paddle/geometry.py`:

- **Outlines** (`ELONGATED`, `HYBRID`): length, width, handle, grip base, corner and dome radii,
  shoulder radius, taper angle and throat radius.
- **`Construction`**: sheet and core thickness, frame width, wave pitch, wall and amplitude,
  solid zone, run-out and the insert bore.
- **`GripInterface`**: the printed grip's length, base, slot, slits, counterbore and screw.

Every drawing, the 3-D model, the renders and the analysis are recomputed from those inputs.
`geometry.check()` asserts that each outline is closed, tangent-continuous and exactly the
specified size.

## Revisions

- **A.** Outlines, general arrangement, full-size templates, DXF, 2-D render.
- **B.** Carbon / wave-rib sandwich construction, closed core frame, grip and screw-locked butt
  cap. Adds the rib-core and grip drawings, 3-D model, photoreal renders and the FEA stress
  analysis. The body now starts 4 mm above the butt-cap base, so the overall length stays 390 mm.
- **C.** Print-ready rib-support STLs, in one piece or in two with a dovetail joint for a 256 mm bed.
  Your rev-8 printed grip replaces the REV B sleeve, wrap, collar and butt cap. The body now starts
  on the grip's 5 mm base, and a DIN 7984 M3 × 12 screw into an M3 insert locks the grip. New
  grip-interface drawing PB-GR-002 replaces PB-GR-001. Drawings, 3-D files, renders, masses and the
  report are updated.
