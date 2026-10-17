#!/usr/bin/env python3
"""Writes README.md, pulling every number from fitment_report.json / print_report.json / the 3MF files."""
import json
import re
import zipfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
fit = {r["name"]: r for r in json.loads((ROOT / "fitment_report.json").read_text())}
prt = {r["name"]: r for r in json.loads((ROOT / "print_report.json").read_text())}
P = json.loads((ROOT / "data" / "reference_profile.json").read_text())

DESC = {
    "01_vortex_grip": ("VORTEX GRIP", "8 + 8 counter-wound straps (36 deg helix) braided over/under; dark valleys between straps give multi-point contact."),
    "02_cellular_mod": ("CELLULAR MOD", "10 rows x 8 staggered cells, 1.4 mm gaps; cells on 3 heights, ~22% recessed as insert pockets (red in the preview)."),
    "03_tessel_block": ("TESSEL-BLOCK", "11 rows x 24 triangles (12 up + 12 down per row, 10.2 mm base), each a faceted pyramid; up-triangles stand taller than down-triangles."),
    "04_logic_grip": ("LOGIC-GRIP", "8 x 7 interlocking jigsaw pieces with mushroom knobs (2.9 mm neck, 4.2 mm head), 0.84 mm grooves, shallow dome tops."),
    "05_neuro_tread": ("NEURO-TREAD", "Periodic Delaunay 'neuron' graph: curved ~1.5 mm axon ridges and soma nodes at full height over a hex-packed bump base (2.7 mm pitch)."),
    "06_carbon_matrix": ("CARBON MATRIX", "Continuous 2/2 twill weave (2 mm tow pitch, every tow a rounded ridge that rises over / dives under) with smooth raised reinforcement patches."),
    "07_voronoi_core": ("VORONOI-CORE", "Lloyd-relaxed Voronoi rib lattice (2.6 mm ribs, rounded tops) around 54 recessed cells (about 1 mm deep); no through-windows any more - the body is solid."),
    "08_topo_flow": ("TOPO-FLOW", "Contour ridges of a terrain / wood-knot height field - continuous undulating lines flowing around four knots."),
    "09_ergo_contour": ("ERGO-CONTOUR", "Smooth hour-glass swell, palm pad on the back (about 1 mm proud; peak about 2.8 mm above the base line), four finger flutes and a thumb dish on the front face."),
    "10_hexa_mod": ("HEXA-MOD", "12-column hex pads (10.2 mm across flats), 1.7 mm gaps, four height levels (red = tallest, full 3.5 mm)."),
}


def pal3mf(n):
    with zipfile.ZipFile(ROOT / "3mf" / f"{n}.3mf") as z:
        return re.findall(r'<m:color color="#([0-9A-F]{6})FF"/>', z.read("3D/3dmodel.model").decode())


rows, wrows, prow, vrows, c3 = [], [], [], [], []
for n, (lab, txt) in DESC.items():
    f, p = fit[n], prt[n]
    w = p["weight_g"]
    rows.append(f"| {n[:2]} | **{lab}** | `stl/{n}.stl` | {txt} | {f['peak_texture_height_above_bore_mm']:.2f} |")
    wrows.append(f"| {lab} | {p['volume_cm3']:.1f} | **{w['PLA']:.1f}** | {w['PETG']:.1f} | {w['TPU']:.1f} | {w['ABS']:.1f} |")
    prow.append(f"| {lab} | {'PASS' if p['pass'] else 'FAIL'} | {p['bodies']} | {p['genus']} | {p['thin_lt_0.4mm_pct_of_volume']:.3f}% | "
                f"{p['max_bridge_span_mm']:.1f} mm | {p['downfacing_gt45deg_pct_of_surface']:.2f}% |")
    vrows.append(f"| {lab} | {'PASS' if f['pass'] else 'FAIL'} | {f['z_max']:.3f} | {f['max_over_reference_envelope_mm']:+.3f} | "
                 f"{f['foot_profile_err_mm']:.3f} | {'-' if f['min_wall_textured_zone_mm'] is None else format(f['min_wall_textured_zone_mm'], '.2f')} | "
                 f"{f['rim_min_wall_mm']:.2f} | {f['slot_measured_w_mm']:.2f} x {f['slot_measured_t_mm']:.2f} | {f['slot_intrusion_mm2']:.3f} | {f['screw_hole_dia_mm']:.2f} |")
    pl = pal3mf(n)
    c3.append(f"| {lab} | `3mf/{n}.3mf` | {(ROOT / '3mf' / f'{n}.3mf').stat().st_size / 1e6:.1f} MB | {len(pl)} | " + " ".join(f"`#{h}`" for h in pl) + " |")

b = P["cavity_bounds"]
fz, fe = np.array(P["foot_table"]).T
sizes = [p.stat().st_size / 1e6 for p in (ROOT / "stl").glob("*.stl")]
wmax = max(prt[n]["weight_g"]["PETG"] for n in DESC)
wmin = min(prt[n]["weight_g"]["PLA"] for n in DESC)
wpmax = max(prt[n]["weight_g"]["PLA"] for n in DESC)

txt = f"""# Pickleball paddle grips - ten designs, one paddle slot

Ten printable grip sleeves generated from the catalog image.  The outer envelope comes from `reference/PickleballGrip_1.3mf`; only the
outer surface differs between designs.  **Revision 3: every grip is a solid body whose only cavities are a 30.2 x 16.2 mm paddle slot
(the measured 30 x 16 mm flat handle of your paddle + 0.2 mm) and a 3.5 mm screw hole through the butt (M3 allen / socket-head screw).**

![catalog](renders/catalog.png)

## Weight (100 % infill, so mass = volume x density)

| Design | Volume cm3 | PLA 1.24 g | PETG 1.27 g | TPU 1.21 g | ABS 1.04 g |
|---|---|---|---|---|---|
{chr(10).join(wrows)}

All ten are **{wmin:.0f}-{wpmax:.0f} g in PLA** (up to {wmax:.0f} g in PETG; densities in g/cm3).  Slicers land within a few percent of volume x density,
so budget +-3 %.  **This is about twice the revision-2 weight (40-49 g):** filling the old 32 x 26 mm bore down to a 30 x 16 mm slot adds about 33 cm3
per grip.  Lowering the infill helps only so far: with 4 perimeters the shell alone is about 52 g, so 15-25 % infill still lands around 57-61 g
(rough estimate from layer sections, not a slicer result).  A <= 50 g part would also need fewer perimeters or a smaller outer envelope.

## What is identical on all ten

| Feature | Value |
|---|---|
| Overall height | **{P['z_top']} mm** (flat top, slot opening) |
| Paddle slot | **30.2 x 16.2 mm** rounded rectangle (corner radius 0.3 mm) = measured tongue 30 x 16 mm + 0.2 mm clearance; wide axis along x; floor at **z = {P['z_floor']}** mm; open at the top |
| Screw hole | **3.5 mm** round, on the slot axis, through the 5 mm butt (z 0 - 5) for an M3 socket-head (allen) screw; no counterbore |
| Body | solid - no other cavity, no through-windows |
| Foot / butt flare | z 0-20: outer skin {np.interp(2.0, fz, fe):.2f} (at z = 2) -> {fe[-1]:.2f} mm from the reference bore line (at z = 20), ~2 mm bottom fillet, flat closed butt (max 42.6 x 36.6 mm) - unchanged |
| Outer envelope | no grip ever exceeds the reference's own outer envelope (crest {P['crest_offset']} mm from the reference bore line) |

Reference bounding box 42.64 x 36.62 x 132.823 mm; all ten grips: 42.63 x 36.61 x 132.82 mm.  "Base line" below = the reference's 32.06 x 26.04 mm
octagonal bore outline, which is now inside the solid body and only serves as the datum the outer skin is measured from.

**The slot size is a ruler measurement.**  Measure your paddle's handle with calipers; if it is not 30 x 16 mm change `PADDLE_W`, `PADDLE_T`
(and `SLOT_CLEAR`, 0.2 mm in total) in `scripts/grip_core.py` and run `generate_grips.py` again.  Printed holes come out slightly small, so
test-print one grip before the rest.  The screw hole has no counterbore: the head of an M3 screw (5.5 mm) will stand 3 mm proud of the butt unless you add one.

## What changed in revision 3

* **Interior:** the 32.06 x 26.04 mm octagonal bore is filled; the only cavity is the 30.2 x 16.2 mm slot (z 5 to the top), so the grip no longer
  rattles on your flat paddle handle (the gaps marked on your photos).
* **Screw hole:** one 3.5 mm hole through the butt on the slot axis, to pin the grip to the paddle with an M3 allen screw.
* **VORONOI-CORE:** with a solid body its through-windows are gone; its 54 cells stay as recesses about 1 mm deep between the rounded ribs (floors 2.46 mm above the base line, crests 3.5 mm).
* **Weight:** roughly doubled (see above).
* Unchanged from revision 2: the outer skin of every design (smooth finish, textures, heights), the reference envelope, one closed body per grip.

Earlier revisions: rev 1 = ten designs + colour 3MFs; rev 2 = smooth finish, 1.2 mm base walls, <= 50 g each.

## The ten grips

| # | Design | File | Concept | Peak height above base line, mm |
|---|---|---|---|---|
{chr(10).join(rows)}

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

## Design brochures (`brochure/designs/`)

Ten 2-page A4 brochures, one per design, for single-colour PLA printing - page 1 is a dark poster (hero, the design story, a close-up,
the handle note, the whole grip in ten PLA colours), page 2 is a light catalogue (two views, a half-section cutaway, the grip on an
illustrative generic paddle, four surface images, the inspiration behind the design, and all ten designs).

```
cd scripts
python3 render_brochure_assets.py   # tinted hero / close-up renders
python3 render_design_assets.py     # cutaway, rim view, unrolled relief, colour row, paddle mock-up, four turns
python3 build_design_brochures.py   # -> brochure/designs/<id>_brochure.pdf
```

## Print readiness (`scripts/verify_print.py`, data in `print_report.json`)

Each STL is sliced at the mid-plane of every 0.20 mm layer (665 layers).

| Design | Result | Bodies | Genus | Material < 0.4 mm wide | Longest bridge | Down-facing > 45 deg |
|---|---|---|---|---|---|---|
{chr(10).join(prow)}

* *Bodies / genus* - one closed body each, no enclosed voids; genus 1 = the screw hole joining the slot to the outside.
* *Material < 0.4 mm wide* - share of volume that a 0.4 mm nozzle line cannot hold (opening test on every layer; corner tips under 0.02 mm2 ignored).
* *Longest bridge* - the widest unsupported run in any layer (material more than 0.35 mm past the layer below).  The textured skins are limited to
  45 degrees so they never bridge, and the slot and screw hole are vertical, so nothing needs support.

## Colored 3MF (`3mf/`)

Each grip is also exported as a colored 3MF, `3mf/<id>.3mf`, using the 3MF Materials extension (`<m:colorgroup>` with a colour
on every triangle - the same mechanism your reference file uses).  Geometry is identical to the matching STL: same coordinates,
millimetres, z up, and the same triangle count.  Colours are a small print palette (not the shaded preview colours), and the
slot/floor/butt take the design's collar colour so no colour change is buried inside the part.  A thumbnail is embedded.

| Design | File | Size | Colours | Palette |
|---|---|---|---|---|
{chr(10).join(c3)}

Checked with the official `lib3mf` reader (`scripts/verify_3mf.py`): parses with zero warnings, triangle and vertex counts equal the STL,
every sampled triangle has a colour property, volume matches the STL, closed manifold.  `renders/catalog_3mf.png` is rendered from the
3MF files themselves.  Not tested in any slicer: viewers that support the materials extension show the colours; multi-extruder slicers
differ in how they import per-triangle colour, so expect to assign or paint filaments in the slicer.  The STLs stay single-material.

## Fitment verification (`scripts/verify_fitment.py`, full data in `fitment_report.json`)

Every STL is cross-sectioned at 40+ heights against the reference profile.

| Design | Result | Height mm | Max outside ref. envelope mm | Foot profile err mm | Min relief floor, textured zone mm | Min skin at the neck mm | Slot measured mm | Material inside slot mm2 | Screw hole mm |
|---|---|---|---|---|---|---|---|---|---|
{chr(10).join(vrows)}

* *Max outside ref. envelope* - how far the outer skin ever exceeds the reference's own outer envelope (must be ~0).  The one deliberate
  exception is the neck, below.
* *Slot measured* - width x depth of the single cavity at z = 60; it must be one cavity at all 40 sampled heights and equal the slot outline.
* *Material inside slot* - area of material within the slot shrunk by 0.05 mm, worst case over 40 heights (must be 0).
* *Screw hole* - mean diameter over z 0.4 - 4.6 (must be round, on the slot axis, with the floor solid around it).
* *Min relief floor* - lowest the textured skin ever gets above the reference bore line (design value 1.2 mm).

![fit overlay](renders/fit_overlay.png)

## Printing notes

* Print **upright, butt-end down**, 100 % infill, 0.20 mm layers (as planned).  Nothing needs supports.  Each grip is {min(prt[n]['weight_g']['PLA'] for n in DESC):.0f}-{wpmax:.0f} g in PLA.
* **Deliberate deviation from your reference - the neck outline.**  Your 3MF tapers to a 0.36 mm rim, thinner than one 0.4 mm line.  All ten keep the
  reference taper curve down to 0.8 mm and then hold 0.8 mm, so the
  top ~7 mm of the neck is up to **{fit['01_vortex_grip']['rim_added_vs_reference_mm']:.2f} mm larger** than the reference at the very rim.  If that
  region must match your paddle exactly, change `MIN_RIM` in `scripts/grip_core.py` (the weight change is ~0.2 cm3).
* Weights are volume x density; the STLs are {min(sizes):.0f}-{max(sizes):.0f} MB each ({sum(sizes):.0f} MB total).  `python3 scripts/generate_grips.py --res 0.35` makes lighter files.
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

`grip_core.py` wraps a height-field skin around the reference bore line (P = bore point + h * normal + z), fills the body, carves the paddle slot and
screw hole (`PADDLE_W/T`, `SLOT_CLEAR`, `HOLE_D`) and holds the print rules (`BASE_WALL`, `MIN_RIM`, `ZONE_LO/HI`, overhang limit); `designs.py` holds the ten texture functions - edit one and re-run to iterate on a design.

## Interpretation notes

The catalog image is a concept render, and a few captions are garbled ("Seal baiking helical structures"), so each design is my
interpretation of the picture and caption rather than a copy.  CELLULAR MOD's red pockets are printable recesses sized for
inserts, but no separate insert parts are included.  VORONOI-CORE lost its through-windows when the body became solid; its cells are
recessed about 1 mm between the ribs instead.
"""
(ROOT / "README.md").write_text(txt)
print("README.md written,", len(txt), "chars")
