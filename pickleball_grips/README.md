# Pickleball paddle grips - ten designs, one fitment

Ten printable grip sleeves generated from the catalog image, all built on the **exact fitment of
`reference/PickleballGrip_1.3mf`** (your pickleball handle sleeve).  Only the outer surface differs.
Revision 2: smooth finish, solid 100 %-infill shells, and every grip <= 50 g.

![catalog](renders/catalog.png)

## Weight (100 % infill, so mass = volume x density)

| Design | Volume cm3 | PLA 1.24 g | PETG 1.27 g | TPU 1.21 g | ABS 1.04 g |
|---|---|---|---|---|---|
| VORTEX GRIP | 37.5 | **46.5** | 47.6 | 45.3 | 39.0 |
| CELLULAR MOD | 38.5 | **47.7** | 48.9 | 46.6 | 40.0 |
| TESSEL-BLOCK | 37.5 | **46.4** | 47.6 | 45.3 | 38.9 |
| LOGIC-GRIP | 38.7 | **48.0** | 49.2 | 46.9 | 40.3 |
| NEURO-TREAD | 37.5 | **46.5** | 47.6 | 45.4 | 39.0 |
| CARBON MATRIX | 38.8 | **48.1** | 49.2 | 46.9 | 40.3 |
| VORONOI-CORE | 32.4 | **40.2** | 41.2 | 39.2 | 33.7 |
| TOPO-FLOW | 38.5 | **47.8** | 48.9 | 46.6 | 40.1 |
| ERGO-CONTOUR | 37.9 | **47.0** | 48.1 | 45.8 | 39.4 |
| HEXA-MOD | 37.9 | **47.0** | 48.2 | 45.9 | 39.4 |

All ten are **40-49 g** - none exceeds 50 g in any of the four common materials (densities in g/cm3).  Slicers land within
a few percent of volume x density, so budget +-3 %.  How the weight was cut without changing the designs is under *What changed*.

## What is identical on all ten (measured from your 3MF)

| Feature | Value |
|---|---|
| Overall height | **132.823 mm** (open top, flat rim) |
| Bore (cavity) | octagonal, **32.06 x 26.04 mm**, area 751.021 mm2, constant along z, floor at **z = 5.0** mm |
| Bore outline | the reference polygon itself (76 vertices, copied verbatim - no re-modelling) |
| Foot / butt flare | z 0-20: outer skin 5.29 (at z = 2) -> 3.54 mm from the bore (at z = 20), ~2 mm bottom fillet, flat closed butt (max 42.6 x 36.6 mm) - unchanged |
| Outer envelope | no grip ever exceeds the reference's own outer envelope (crest 3.5 mm from the bore) |

Reference bounding box 42.64 x 36.62 x 132.823 mm; all ten grips: 42.63 x 36.61 x 132.82 mm.

## What changed in this revision

**1. Smooth finish.**  A close-up audit (flat-shaded and at silhouettes) found: stair-stepped / comb-like edges on steep features
(vortex straps, hex pads, neural ridges, tessel creases), a carbon weave built from hard cell switches, shading streaks on hard
creases (Voronoi window walls), and - a real design bug - Logic-Grip's jigsaw knobs collapsing into thin stalks.  Fixes: 3 x 3 supersampled
texture, Gaussian rounding of the height field (0.25 mm, far below the nozzle), a second rounding after the 45-degree overhang limiter
(that limiter ran per column on the row grid and left 0.25 mm teeth on diagonal edges), shorter-diagonal triangle splitting, gentler wall
angles on the vortex straps and neural ridges, a continuous twill for the carbon weave, bigger knobs and narrower grooves for the jigsaw,
and crease-aware normals in the renders.  A little residual stepping remains on the very steepest walls right at the octagon's rounded
corners (~0.3 mm, under the nozzle diameter).

**2. Solid shell.**  Base wall 1.2 mm (exactly 3 x 0.4 mm perimeters) everywhere; the top rim is kept >= 0.8 mm (2 x 0.4 mm) instead of the
reference's 0.36 mm taper (see *Printing notes*); one closed body per grip, no internal voids; slice-simulated every 0.20 mm layer.

**3. Weight.**  The floor, foot and envelope your reference dictates already make a bare wall-only sleeve 28.6 cm3 (35.5 g in PLA), and every
0.1 of average relief adds ~3 g - so the relief budget for <= 50 g is tight.  Levers used: base wall 1.5 -> 1.2 mm; texture carried up the neck
to z = 116 (as your honeycomb was) instead of a solid collar; and lowering plateau heights on the designs with large flat tops.  Every design
keeps its structure, grooves, counts and accents.  **The trade-off:** plateau-type designs now peak at 2.7-3.1 mm above the bore instead of ~3.3-3.5 mm,
so the gripping surface is up to ~0.6 mm thinner per side on those (peak heights below).  NEURO-TREAD, VORONOI-CORE and HEXA-MOD still reach the full 3.5 mm.

## The ten grips

| # | Design | File | Concept | Peak height above bore, mm |
|---|---|---|---|---|
| 01 | **VORTEX GRIP** | `stl/01_vortex_grip.stl` | 8 + 8 counter-wound straps (36 deg helix) braided over/under; dark valleys between straps give multi-point contact. | 2.85 |
| 02 | **CELLULAR MOD** | `stl/02_cellular_mod.stl` | 10 rows x 8 staggered cells, 1.4 mm gaps; cells on 3 heights, ~22% recessed as insert pockets (red in the preview). | 3.04 |
| 03 | **TESSEL-BLOCK** | `stl/03_tessel_block.stl` | 11 rows x 24 triangles (12 up + 12 down per row, 10.2 mm base), each a faceted pyramid; up-triangles stand taller than down-triangles. | 3.44 |
| 04 | **LOGIC-GRIP** | `stl/04_logic_grip.stl` | 8 x 7 interlocking jigsaw pieces with mushroom knobs (2.9 mm neck, 4.2 mm head), 0.84 mm grooves, shallow dome tops. | 2.81 |
| 05 | **NEURO-TREAD** | `stl/05_neuro_tread.stl` | Periodic Delaunay 'neuron' graph: curved ~1.5 mm axon ridges and soma nodes at full height over a hex-packed bump base (2.7 mm pitch). | 3.50 |
| 06 | **CARBON MATRIX** | `stl/06_carbon_matrix.stl` | Continuous 2/2 twill weave (2 mm tow pitch, every tow a rounded ridge that rises over / dives under) with smooth raised reinforcement patches. | 2.73 |
| 07 | **VORONOI-CORE** | `stl/07_voronoi_core.stl` | Lloyd-relaxed Voronoi rib lattice (2.6 mm ribs, rounded tops); 54 windows cut clean through the wall for weight and airflow. | 3.50 |
| 08 | **TOPO-FLOW** | `stl/08_topo_flow.stl` | Contour ridges of a terrain / wood-knot height field - continuous undulating lines flowing around four knots. | 3.11 |
| 09 | **ERGO-CONTOUR** | `stl/09_ergo_contour.stl` | Smooth hour-glass swell, palm pad on the back (about 1 mm proud; peak about 2.8 mm above the bore), four finger flutes and a thumb dish on the front face. | 2.76 |
| 10 | **HEXA-MOD** | `stl/10_hexa_mod.stl` | 12-column hex pads (10.2 mm across flats), 1.7 mm gaps, four height levels (red = tallest, full 3.5 mm). | 3.50 |

Close-ups: `renders/<id>_detail.png`; four-way turntable line-ups: `renders/<id>_lineup.png`;
hero shots: `renders/<id>_hero.png`.  Colours in the renders are **preview only** - the STLs are single-material.

## Specification sheets (`specs/`)

One 4-page A4 sheet per grip plus a 45-page book with a comparison, the reference fitment and the notes:

| Page | Content |
|---|---|
| 1 Overview | hero render, at-a-glance dimensions, weights (PLA/PETG/TPU/ABS), colourway, print profile, verification |
| 2 Technical drawing | third-angle top / front / side views at true 1:1 with dimensions, section marks A-A, B-B, C-C, title block |
| 3 Sections & profiles | dimensioned sections at z 10 / 60 / 128 mm, offset and area against height, dimension tables |
| 4 Views & surface | four-way turntable, close-ups, unrolled height map, design parameters, print verification |

`specs/01_vortex_grip_spec.pdf` ... `specs/10_hexa_mod_spec.pdf` and `specs/PickleballGrips_SpecBook.pdf` (bookmarked, clickable contents).
Every number on the sheets is measured from the STL files (`scripts/spec_data.py`), not copied from design intent.  Page 2 of each sheet
is true size when printed at 100 % (do not "fit to page").  Regenerate with:

```
cd scripts
python3 render_spec_assets.py      # hero / line-up / ortho / close-up renders -> specs/assets/ (headless Chromium)
python3 spec_data.py               # measurements -> specs/assets/<id>/data.json, relief.png
python3 build_specs.py             # -> specs/*.pdf   (needs reportlab and the Liberation Sans fonts)
```

## Brochure (`brochure/PickleballGrips_Brochure.pdf`)

A 2-page A4 pitch brochure / poster for single-colour PLA printing: page 1 is a dark poster (the ten grips as a hero, a short note on
the handle, ten PLA colour options), page 2 is a catalogue (two views, a surface close-up and a line of design inspiration for every
design).  All renders are one colour each (white vertex colours x one PLA tint), so they show what a one-colour print looks like.

```
cd scripts
python3 render_brochure_assets.py   # tinted renders -> brochure/assets/   (headless Chromium)
python3 build_brochure.py           # artwork + layout -> brochure/PickleballGrips_Brochure.pdf
```

## Print readiness (`scripts/verify_print.py`, data in `print_report.json`)

Each STL is sliced at the mid-plane of every 0.20 mm layer (664 layers).

| Design | Result | Bodies | Genus | Material < 0.4 mm wide | Longest bridge | Down-facing > 45 deg |
|---|---|---|---|---|---|---|
| VORTEX GRIP | PASS | 1 | 0 | 0.000% | 0.0 mm | 0.00% |
| CELLULAR MOD | PASS | 1 | 0 | 0.000% | 0.0 mm | 0.00% |
| TESSEL-BLOCK | PASS | 1 | 0 | 0.000% | 0.0 mm | 0.00% |
| LOGIC-GRIP | PASS | 1 | 0 | 0.000% | 0.0 mm | 0.00% |
| NEURO-TREAD | PASS | 1 | 0 | 0.000% | 0.0 mm | 0.00% |
| CARBON MATRIX | PASS | 1 | 0 | 0.000% | 0.0 mm | 0.00% |
| VORONOI-CORE | PASS | 1 | 54 | 0.000% | 3.8 mm | 5.26% |
| TOPO-FLOW | PASS | 1 | 0 | 0.000% | 0.0 mm | 0.00% |
| ERGO-CONTOUR | PASS | 1 | 0 | 0.000% | 0.0 mm | 0.00% |
| HEXA-MOD | PASS | 1 | 0 | 0.000% | 0.0 mm | 0.00% |

* *Bodies / genus* - one closed body each, no enclosed voids; genus 0 = a plain sleeve, VORONOI-CORE's 54 = its 54 windows.
* *Material < 0.4 mm wide* - share of volume that a 0.4 mm nozzle line cannot hold (opening test on every layer; corner tips under 0.02 mm2 ignored).
* *Longest bridge* - the widest unsupported run in any layer (material more than 0.35 mm past the layer below).  The textured skins are limited to
  45 degrees so they never bridge; VORONOI-CORE's window roofs were trimmed to <= 60 degrees / <= 4 mm flat, which cut the worst bridge from 12 mm to under 4 mm.

## Colored 3MF (`3mf/`)

Each grip is also exported as a colored 3MF, `3mf/<id>.3mf`, using the 3MF Materials extension (`<m:colorgroup>` with a colour
on every triangle - the same mechanism your reference file uses).  Geometry is identical to the matching STL: same coordinates,
millimetres, z up, and the same triangle count.  Colours are a small print palette (not the shaded preview colours), and the
bore/floor/butt take the design's collar colour so no colour change is buried inside the part.  A thumbnail is embedded.

| Design | File | Size | Colours | Palette |
|---|---|---|---|---|
| VORTEX GRIP | `3mf/01_vortex_grip.3mf` | 4.5 MB | 2 | `#3A225C` `#9C6CDE` |
| CELLULAR MOD | `3mf/02_cellular_mod.3mf` | 3.3 MB | 3 | `#464648` `#969692` `#C81E22` |
| TESSEL-BLOCK | `3mf/03_tessel_block.3mf` | 4.6 MB | 3 | `#848482` `#E8742A` `#387AC4` |
| LOGIC-GRIP | `3mf/04_logic_grip.3mf` | 4.6 MB | 3 | `#323236` `#2A3C8A` `#9EA4AA` |
| NEURO-TREAD | `3mf/05_neuro_tread.3mf` | 4.8 MB | 2 | `#18181A` `#CE1820` |
| CARBON MATRIX | `3mf/06_carbon_matrix.3mf` | 4.7 MB | 2 | `#1C1C20` `#80848A` |
| VORONOI-CORE | `3mf/07_voronoi_core.3mf` | 2.3 MB | 1 | `#8A54E4` |
| TOPO-FLOW | `3mf/08_topo_flow.3mf` | 4.8 MB | 3 | `#D6AC80` `#A8744E` `#784828` |
| ERGO-CONTOUR | `3mf/09_ergo_contour.3mf` | 0.8 MB | 1 | `#424248` |
| HEXA-MOD | `3mf/10_hexa_mod.3mf` | 3.8 MB | 5 | `#1C1C1E` `#464A4E` `#74787E` `#B0B4BA` `#D63A28` |

Checked with the official `lib3mf` reader (`scripts/verify_3mf.py`): parses with zero warnings, triangle and vertex counts equal the STL,
every sampled triangle has a colour property, volume matches the STL, closed manifold.  `renders/catalog_3mf.png` is rendered from the
3MF files themselves.  Not tested in any slicer: viewers that support the materials extension show the colours; multi-extruder slicers
differ in how they import per-triangle colour, so expect to assign or paint filaments in the slicer.  The STLs stay single-material.

## Fitment verification (`scripts/verify_fitment.py`, full data in `fitment_report.json`)

Every STL is cross-sectioned at 40+ heights against the reference profile.

| Design | Result | Height mm | Max outside ref. envelope mm | Foot profile err mm | Min wall, textured zone mm | Min wall, rim mm | Bore wall on grip surface | Material inside bore mm2 |
|---|---|---|---|---|---|---|---|---|
| VORTEX GRIP | PASS | 132.823 | +0.001 | 0.007 | 1.25 | 0.79 | 100% | 0.000 |
| CELLULAR MOD | PASS | 132.823 | +0.001 | 0.007 | 1.20 | 0.80 | 100% | 0.000 |
| TESSEL-BLOCK | PASS | 132.823 | +0.001 | 0.007 | 1.39 | 0.79 | 100% | 0.000 |
| LOGIC-GRIP | PASS | 132.823 | +0.001 | 0.007 | 1.21 | 0.79 | 100% | 0.000 |
| NEURO-TREAD | PASS | 132.823 | +0.001 | 0.007 | 1.33 | 0.79 | 100% | 0.000 |
| CARBON MATRIX | PASS | 132.823 | +0.001 | 0.007 | 1.63 | 0.79 | 100% | 0.000 |
| VORONOI-CORE | PASS | 132.823 | +0.003 | 0.007 | - | 0.80 | 63% | 0.000 |
| TOPO-FLOW | PASS | 132.823 | +0.001 | 0.007 | 1.48 | 0.79 | 100% | 0.000 |
| ERGO-CONTOUR | PASS | 132.823 | +0.001 | 0.007 | 1.29 | 0.80 | 100% | 0.000 |
| HEXA-MOD | PASS | 132.823 | +0.001 | 0.007 | 1.20 | 0.79 | 100% | 0.000 |

* *Max outside ref. envelope* - how far the outer skin ever exceeds the reference's own outer envelope (must be ~0).  The one deliberate
  exception is the rim, below.
* *Bore wall on grip surface* - share of sampled reference-bore points that lie on the grip's surface.  100% = the bore
  is identical; VORONOI-CORE is lower **by design** because its windows open the wall (the bore itself is unchanged).
* *Material inside bore* - area of material within the bore shrunk by 0.1 mm, worst case over 40 heights (must be 0).
* Floor at z = 5 and open top confirmed on all ten.

![fit overlay](renders/fit_overlay.png)

## Printing notes

* Print **upright, butt-end down**, 100 % infill, 0.20 mm layers (as planned).  Nothing needs supports; VORONOI-CORE's windows bridge <= 4 mm.
* **Deliberate deviation from your reference - the rim.**  Your 3MF tapers to a 0.36 mm rim, thinner than one 0.4 mm line; a slicer would print it
  as a lone thin line or drop it, which defeats a solid shell.  All ten keep the reference taper curve down to 0.8 mm and then hold 0.8 mm, so the
  top ~7 mm of the neck is up to **0.40 mm larger** than the reference at the very rim.  If that
  region must match your paddle exactly, change `MIN_RIM` in `scripts/grip_core.py` (the weight change is ~0.2 cm3).
* Weights are volume x density; the STLs are 3-20 MB each (164 MB total).  `python3 scripts/generate_grips.py --res 0.35` makes lighter files.
* These are geometry-verified but I have not run them through a slicer or printed them - do a preview slice before committing filament.

## Regenerating

```
pip install numpy scipy trimesh shapely manifold3d pillow mapbox_earcut matplotlib playwright lib3mf scikit-image
cd scripts
python3 extract_reference_profile.py          # reference 3MF -> data/reference_profile.json
python3 generate_grips.py                     # -> stl/*.stl   (~30 s)
python3 verify_fitment.py                     # -> fitment_report.json
python3 verify_print.py                       # -> print_report.json (slices every 0.2 mm layer, ~8 min)
npm install && python3 render_grips.py --catalog   # -> renders/*.png (headless Chromium + three.js)
python3 export_3mf.py && python3 verify_3mf.py     # -> 3mf/*.3mf (colored), validated with lib3mf
python3 render_grips.py --source 3mf --catalog     # -> renders/catalog_3mf.png
python3 make_fit_overlay.py && python3 ../make_readme.py
```

`grip_core.py` wraps a height-field skin around the reference bore (P = bore point + h * normal + z) and holds the print rules
(`BASE_WALL`, `MIN_RIM`, `ZONE_LO/HI`, overhang limit); `designs.py` holds the ten texture functions - edit one and re-run to iterate on a design.

## Interpretation notes

The catalog image is a concept render, and a few captions are garbled ("Seal baiking helical structures"), so each design is my
interpretation of the picture and caption rather than a copy.  CELLULAR MOD's red pockets are printable recesses sized for
inserts, but no separate insert parts are included.  VORONOI-CORE keeps its through-windows (they are the design); it is also the
lightest at 40 g in PLA.
