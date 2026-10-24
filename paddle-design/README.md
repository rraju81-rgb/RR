# Pickleball paddle designs – Elongated & Hybrid (REV D)

Two 39 cm paddles traced from your hand-made templates and sketches. Each is a carbon-fibre /
wave-rib sandwich: two 0.3 mm carbon skins on a 10 mm 3D-printed rib support, pressed together
in a two-half compression mould. Your rev-8 printed grip goes on the handle and is locked by a screw
in the butt. The repo holds the engineering drawings, full-size templates, DXF cut profiles, the
print-ready rib support and mould, the 3-D model (STEP / STL / 3MF), photoreal renders and the
strength checks.

![3D render](output/render/paddles_3d_hero.png)

> **Before you build: the 0.3 mm skins are too thin for this core.** A hand check, calibrated on
> the earlier FEA, says the paddle would not survive the 500 N design impact. It also deflects
> about 15 times more than REV C. See [Strength](#strength) for the numbers and the lay-ups that
> pass. Every file here is parametric, so a different lay-up is a quick rebuild.

## Specification

| | **Elongated** (PB-EL-001) | **Hybrid** (PB-HY-001) |
|---|---|---|
| Overall length (incl. the grip base) | 390 mm | 390 mm |
| Blade (face) length | 260 mm | 260 mm |
| Handle | 130 mm incl. the 5 mm grip base, body 30 × 10.6 mm | same |
| Blade width | **200 mm** | **190 mm** |
| Thickness | **10.6 mm: 0.3 mm carbon + 10 mm wave-rib core + 0.3 mm carbon**, set by the mould | same |
| Head shape | Square head, **R48** tip corners | Domed head, **R150** crown + **R30** shoulders (dome rise 49.1 mm) |
| Blade → handle | R25 shoulder → 30° straight taper → R15 throat fillet | same |
| Straight sides | y = 202.2 … 342.0 mm from the butt | y = 199.3 … 340.9 mm from the butt |
| Body profile area | 491 cm² | 459 cm² |
| Grip | Printed PLA grip (rev 8), DIN 7984 M3 screw lock. **Its 16.0 mm slot must be regenerated for the 10.6 mm handle**, see [Printed grip](#printed-grip) | same |
| Mass with the grip (3D model) | 323 g, balance point 198 mm from the butt | 309 g, 192 mm |
| USA Pickleball L + W ≤ 609.6 mm (24 in) | 590 mm ✔ (19.6 mm margin) | 580 mm ✔ (29.6 mm margin) |
| USA Pickleball L ≤ 431.8 mm (17 in) | 390 mm ✔ | 390 mm ✔ |

Every profile is lines and tangent arcs, symmetric about the centre line. An edge guard counts
towards the USA Pickleball limits, so keep it within the margins above.

## Construction

| | |
|---|---|
| ![Cutaway](output/render/paddles_3d_cutaway.png) | ![Exploded view](output/render/paddles_3d_exploded_elongated.png) |
| ![Exploded view, hybrid](output/render/paddles_3d_exploded_hybrid.png) | ![Printed grip pulled off the handle: slot, end-wall slits and the M3 insert](output/render/paddles_3d_handle.png) |

- **Skins.** Two identical 0.3 mm woven carbon/epoxy skins, cut to the body profile
  (`*_profile.dxf`, template sheet 2). They are laminated onto the rib support in the mould and
  trimmed flush with its edge.
- **Rib support (the core), 10 mm, 3D-printed in PA-CF in one piece and printed flat** (sheet 3 of
  each drawing):
  - A closed 6 mm perimeter frame covers the whole side, as marked on your sketch.
  - Inside it is the sinusoidal wave rib from your sketch: pitch 18 mm, wall 1.6 mm, centre-line
    amplitude 5.2 mm. The flutes run along the paddle. The crests are cut flat where they meet the
    skins, which gives 4.28 mm wide bond lands on both faces. The wave walls connect the two faces.
  - The core is solid from its butt to y = 150 mm (handle and throat). Each flute starts with a
    45° run-out, 10 mm long, which prints without support.
- **Grip.** Your printed rev-8 grip slides over the handle. Its 5 mm solid base is the butt of the
  paddle, so the skins and the rib support start at y = 5 mm and the overall length stays 390 mm.
- **Screw lock.** A DIN 7984 M3 × 12 low-head screw goes up through the grip base into an M3 × 5.7
  brass heat-set insert in the butt of the rib support: bore Ø4.0 × 7, then Ø3.2 × 15 clearance.

## Rib support STL

`python tools/export_rib_support.py` writes one STL per paddle to
[`output/rib_support/`](output/rib_support). It is the whole rib support in one piece, lying flat
in its print orientation (z = 0 … 10 mm), centred on x = y = 0, in mm. It is a single closed body
and drops straight into the mould.

| File | Size (mm) | Mass, PA-CF (PETG / PLA) | Printer bed |
|---|---|---|---|
| `elongated_rib_support.stl` | 200 × 385 × 10 | 212 g (229 / 223 g) | ≥ 391 × 206 mm (400 mm class) |
| `hybrid_rib_support.stl` | 190 × 385 × 10 | 203 g (218 / 213 g) | ≥ 391 × 196 mm (400 mm class) |

Print it at 100 % infill (the 1.6 mm walls are 4 perimeters of a 0.4 mm nozzle), 0.2 mm layers and
no supports. Dry the PA-CF first, and check the thickness (10.0 ±0.1 mm) before moulding. The checks
(closed mesh, bodies, volume, bed fit) are in `rib_support_report.json`.

## Compression mould

| | |
|---|---|
| ![Compression mould, opened up](output/render/paddles_3d_mould.png) | ![Mould drawing](output/elongated/PB-EL-001_sheet4_compression_mould.png) |

`python tools/export_mould.py` writes the mould for each paddle to [`output/mould/`](output/mould):
`<design>_mould_half.stl` for printing and `.step` for machining. Sheet 4 of each drawing covers it.

- **How it works.** The mould is split on the paddle's mid-plane. Each half has a pocket in the
  shape of the paddle, 5.3 mm deep. When the two parting faces meet, the cavity is exactly 10.6 mm:
  skin 0.3 + rib support 10 + skin 0.3. You lay the bottom skin, the rib support and the top skin in
  the bottom half, close the top half over it, and press until the faces meet. The flange is a
  hard stop, so it sets the thickness.
- **One part, printed twice.** Every feature is symmetric, so the top half is the same part turned
  over. Each half is a single piece: 244.4 × 429.4 × 15.3 mm (Elongated) or 234.4 × 429.4 × 15.3 mm
  (Hybrid). It needs a ≥ 440 mm bed (500 × 500 class), or you can machine the STEP from aluminium or
  HDPE. A solid print is about 1.0–1.1 kg of PLA per half.
- **Features:**
  - The pocket is the body outline plus 0.2 mm clearance, so the printed rib support drops in, with
    a 1° draft for release.
  - A 2 mm pinch-off land surrounds the pocket. Beyond it is a resin overflow groove, 2 × 1 mm in
    each half, with 6 vents to the outside.
  - 18 × M6 bolt holes, 4 holes for Ø6 × 20 steel dowel pins and 2 pry notches to split the cured
    mould.
- **Moulding steps** (full list on sheet 4):
  1. Seal and polish the pocket floors and apply release (wax + PVA, or release film).
  2. Press the dowel pins into one half.
  3. Lay up in the bottom half: the skin (cut 0.5 mm undersize), wet out; the rib support (faces
     abraded, insert fitted with a screw in it); then the top skin, wet out.
  4. Close the top half and fit the bolts finger-tight.
  5. Press the mould between two flat, stiff platens (≥ 18 mm ply or aluminium, with clamps), in a
     press, or in a vacuum bag until the flanges meet, then tighten the bolts.
  6. Cure, split the mould at the pry notches and trim the flash.

  Bolts alone bow a printed mould and cannot press the middle of the blade.
- **Temperature.** PLA softens near 55 °C, so use a room-temperature-cure epoxy. For a warm
  post-cure, print the mould in PETG, ASA or PA-CF.
- **Fine-tuning.** If the cavity needs opening (for example for pre-cured skins plus glue lines),
  shim the flange with tape or foil.

## Printed grip

![Grip interface drawing](output/grip/PB-GR-002_printed_grip_interface.png)

The grip is your rev-8 printed grip (`pickleball_grips/` on branch `claude/kind-volta-vs8ck6`, commit
`c594433`). All ten designs share the same interface. Drawing
[`PB-GR-002`](output/grip/PB-GR-002_printed_grip_interface.pdf) shows how it fits:

- 135 mm long, with a solid 5 mm base, a 30.2 mm wide slot 130 mm deep with a 1 mm lead-in, and
  head walls at least 3.5 mm thick.
- Both end walls are slit over the top 20 mm, so the throat flare (from y = 130) can pass.
- The M3 screw goes through a Ø3.5 hole with a Ø6.2 × 2.2 counterbore, leaving 2.8 mm of PLA under
  the head. Tighten it by hand (about 0.5 N·m) with a low-strength threadlocker.

**The rev-8 slot no longer fits.** It is 16.0 mm thick, but the REV D handle is 10.6 mm, so the
grip would sit 5.4 mm loose. Since the grips are not printed yet, regenerate them on the grip
branch:
- set `SLOT_T = 10.6` in `pickleball_grips/scripts/grip_core.py`;
- make a new fit-test coupon at 10.2 / 10.6 / 11.0 mm.

The drawings still show the rev-8 grip (CARBON MATRIX, 61 g), so its sections show the gap.

## Strength

The CalculiX model meshes the skins as solid tetrahedra, and that doesn't work for a 0.3 mm skin.
So REV D was checked by hand (`python tools/hand_check.py` → `analysis/hand_check.json`). The method
has three parts:
1. The paddle is treated as a cantilever from the grip clamp, with skins and core section by section.
2. The skin between two bond lands is treated as a clamped strip under the ball's contact pressure,
   including membrane stretching.
3. The skin is checked for buckling between the lands.

The same method run on REV C (4 / 8 / 4) is compared with REV C's FEA results. Skin stress is scaled
by the FEA/beam ratio (×1.42) and deflection by ×1.66. Core stress is quoted as plain beam bending.

| 500 N ball impact | REV C 4 / 8 / 4 (FEA) | REV D 0.3 / 10 / 0.3 (hand check) | Allowable |
|---|---|---|---|
| Skin stress in the handle just above the grip, tip hit | 141 MPa (RF 3.6) | **1,310 MPa (RF 0.38)** | 500 MPa (compression) |
| Same, sweet-spot hit | – | **846 MPa (RF 0.59)** | 500 MPa |
| Core bending stress there, tip hit | 17.5 MPa (local peak) | **58 MPa (RF 0.77)** | 45 MPa |
| Skin between two lands, under the ball | ≈ 4 MPa | **556 MPa (RF 0.90)** | 500 MPa |
| Skin buckling between lands (blade, tip hit) | not critical | **264 MPa vs 95 MPa critical (RF 0.36)** | – |
| Tip deflection, tip hit | 3.85 mm | **≈ 57 mm** | – |

What this means:

1. **Stress at the handle.** The handle is only 30 mm wide, and with 0.3 mm skins the bending
   stress there is about 2.6 times what the carbon can take.
2. **Skin between the lands.** The lands are 18 mm apart. That leaves 13.7 mm of unsupported 0.3 mm
   skin, which bends under the ball and buckles in compression.
3. **Overall stiffness.** The paddle is very flexible, about 57 mm of tip deflection against 3.9 mm
   for REV C.
4. **At normal hits.** At a realistic 340 N peak hit (500 N includes a 1.5 safety factor), the
   handle skin (RF ≈ 0.56 tip, 0.87 sweet spot) and the buckling between lands (≈ 0.53) are still
   below 1.

Lay-ups that fix it (Elongated, the same method, wave amplitude kept at the core faces):

| Lay-up, wave pitch | Skins + rib support | Handle RF (tip / sweet spot) | Buckling RF | Skin-between-lands RF | Tip deflection |
|---|---|---|---|---|---|
| 0.3 / 10 / 0.3, λ18 (as built) | 46 + 214 g | 0.38 / 0.59 | 0.36 | 0.90 | 57 mm |
| 0.3 / 10 / 0.3, λ9 | 46 + 277 g | 0.38 / 0.59 | 1.80 | 3.5 | 57 mm |
| 0.6 / 10 / 0.6, λ12 | 91 + 242 g | 0.66 / 1.02 | 6.8 | 7.1 | 30 mm |
| 0.9 / 10 / 0.9, λ12 | 137 + 242 g | 0.94 / 1.46 | 22 | 16 | 20 mm |
| 1.2 / 10 / 1.2, λ18 (current wave) | 183 + 214 g | 1.23 / 1.91 | 21 | 11 | 15 mm |
| 0.3 skins + 0.9 doubler to y = 200, λ9 | 46 + 34 + 277 g | 1.23 / 1.91 | 4.3 | 3.5 | 19 mm |
| 0.9 / 14 / 0.9, λ12 | 137 + 327 g | 1.37 / 2.13 | 34 | 15 | 10 mm |

- **The handle and throat decide the skin thickness.** A finer wave pitch alone only fixes the blade.
- **Two lay-ups work:**
  - **4 plies (1.2 mm) per side on the 10 mm core**, which passes with the current wave;
  - **0.3 mm skins on the blade**, plus about 3 extra plies (0.9 mm, about 34 g) on the handle and
    throat up to y ≈ 200 mm, sunk into a printed recess in the rib support, with a 9 mm wave pitch.
    This is the lightest option that passes.
- **What a change involves.** `face_t`, `core_t` and `rib_pitch` in `paddle/geometry.py` drive
  everything, including the mould pocket depth.

The full FEA report, [`output/fea/paddle_stress_report.pdf`](output/fea/paddle_stress_report.pdf),
covers the REV C 4 / 8 / 4 lay-up. It stays as the reference the hand check is calibrated against.
To run the FEA on thin skins, the model's skins need shell or single-layer wedge elements.

## Output files

| File | What it is |
|---|---|
| [`output/paddle_drawing_set.pdf`](output/paddle_drawing_set.pdf) | All 9 drawing sheets in one PDF |
| `output/<design>/*_sheet1_general_arrangement.(pdf/svg/png)` | **General arrangement**, A3, 1:2, first angle: front view with the grip, side view with the 0.3/10/0.3 lay-up, section A–A through the wave core, section B–B through the grip, isometric view, notes |
| `output/<design>/*_sheet2_template_1to1.(pdf/svg/png)` | **Full-size body template**, A3 portrait, 1:1: tangent points, arc centres, coordinate table, core-frame and solid-zone reference lines, scale-check bars |
| `output/<design>/*_sheet3_rib_core.(pdf/svg/png)` | **Rib support**: plan view 1:2 with lands and flute run-outs, section C–C across the wave 2:1, section D–D through the run-out 2:1, print notes |
| `output/<design>/*_sheet4_compression_mould.(pdf/svg/png)` | **Compression mould**: parting-face plan 1:2, section X–X through the closed mould 1:2, edge detail Y 3:1, hardware, moulding steps |
| `output/grip/PB-GR-002_printed_grip_interface.(pdf/svg/png)` | **Printed grip – paddle interface** (both paddles): handle in the grip, sections E–E and G–G across the grip, section F–F through the screw, insert and bores, the fit-test coupon, bill of materials, notes |
| `output/<design>/*_profile.dxf` | 1:1 cut profile of the skins (mm) for CNC / laser: closed polyline with true arcs |
| `output/rib_support/<design>_rib_support.stl` | **Print-ready rib support**, one piece, plus `rib_support_report.json` |
| `output/mould/<design>_mould_half.stl` / `.step` | **Compression mould half** (print or machine 2), plus `mould_report.json` |
| `output/cad/<design>_assembly.step` | 3-D assembly: skins, rib support, screw and insert (named solids) |
| `output/cad/<design>_assembly.3mf` | The same assembly with the printed grip (a mesh, so it is not in the STEP) |
| `output/cad/<design>_rib_core.step` / `.stl`, `output/cad/<design>_<part>.stl` | The rib support and every other part, in mm |
| `output/render/paddles_3d_*.png` | Photoreal renders: hero, cutaway, exploded with the grip and screw (each design), handle close-up, the opened mould |
| `output/render/paddles_2d_render.(png/svg)` | 2-D presentation render (face and 3/4 views) |
| `analysis/hand_check.json`, `analysis/mass_properties.json` | REV D strength hand check (both lay-ups, calibration) and masses |
| `output/fea/paddle_stress_report.pdf`, `output/fea/fea_*.png`, `analysis/fea/*.json` | REV C FEA report, figures and raw results (4 / 8 / 4 lay-up) |
| `reference/grips/*.stl` | Copies of the CARBON MATRIX and VORTEX GRIP STLs and the fit-test coupon from the grip branch |
| [`reference/cad_outline_vs_your_templates.jpg`](reference/cad_outline_vs_your_templates.jpg) | The CAD outline overlaid on your template photos |

**Printing the template.** Print the sheet-2 PDF on A3 at **100 % / "Actual size"**, with no
fit-to-page. Check the 100 mm and 50 mm bars before cutting.

## How the shapes were derived

The specified dimensions (390 overall, 260 blade, 130 × 30 handle, 200 / 190 wide) are exact. The
radii and the taper angle were measured from your photos. The elongated values come from the white
template, segmented and scaled to 200 × 390. The hybrid values come from the pen sketch, rectified
to the 190 × 260 blade.

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
python tools/export_cad.py                # STEP / STL / 3MF + analysis/mass_properties.json
python tools/export_rib_support.py        # print-ready rib support, one piece
python tools/export_mould.py              # compression mould halves (STL + STEP)
python tools/hand_check.py                # strength hand check -> analysis/hand_check.json
python build.py                           # drawings (incl. the mould sheets), templates, DXF, 2-D render
python tools/render_3d.py                 # photoreal renders (Blender 4.x with Cycles on PATH)
python tools/export_cad.py --grip 03_tessel_block   # the 3-D files with another of the ten grips
```

A grip STL that is not in `reference/grips/` is copied from the grip branch the first time it is
needed, so fetch that branch first (`git fetch origin claude/kind-volta-vs8ck6`).

The inputs live in `paddle/geometry.py` and `paddle/mould.py`:

- **Outlines** (`ELONGATED`, `HYBRID`): length, width, handle, grip base, thickness, corner and dome
  radii, shoulder radius, taper angle and throat radius.
- **`Construction`**: skin and core thickness, frame width, wave pitch, wall and amplitude, solid
  zone, run-out and the insert bore.
- **`GripInterface`**: the printed grip's length, base, slot, slits, counterbore and screw.
- **`MouldSpec`**: clearance, draft, floor, flange, land, groove, vents, bolts, dowels and notches.
  The pocket depth follows the paddle thickness.

Every drawing, the 3-D model, the print files, the mould and the renders are recomputed from those
inputs. `geometry.check()` asserts that each outline is closed, tangent-continuous and exactly the
specified size, and that the specified thickness matches the lay-up.

## Revisions

- **A.** Outlines, general arrangement, full-size templates, DXF, 2-D render.
- **B.** Carbon / wave-rib sandwich construction, closed core frame, grip and screw-locked butt
  cap. Adds the rib-core and grip drawings, 3-D model, photoreal renders and the FEA stress
  analysis. The body now starts 4 mm above the butt-cap base, so the overall length stays 390 mm.
- **C.** Print-ready rib-support STLs. Your rev-8 printed grip replaces the REV B sleeve, wrap,
  collar and butt cap. The body now starts on the grip's 5 mm base, and a DIN 7984 M3 × 12 screw
  into an M3 insert locks the grip. Grip-interface drawing PB-GR-002.
- **D.** Lay-up 0.3 / 10 / 0.3 (10.6 mm thick, 323 / 309 g). The rib support is a single piece
  again (the two-piece dovetail version is gone). Adds the two-half compression mould: STL + STEP,
  drawing sheet 4 and a render. Adds the strength hand check, with alternative lay-ups. The rev-8
  grip slot (16.0) is flagged for regeneration at 10.6.
