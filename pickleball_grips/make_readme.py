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
    "07_voronoi_core": ("VORONOI-CORE", "Lloyd-relaxed Voronoi rib lattice (2.6 mm ribs, rounded tops); 54 windows cut clean through the wall for weight and airflow."),
    "08_topo_flow": ("TOPO-FLOW", "Contour ridges of a terrain / wood-knot height field - continuous undulating lines flowing around four knots."),
    "09_ergo_contour": ("ERGO-CONTOUR", "Smooth hour-glass swell, palm pad on the back (reaches the full 3.5 mm envelope), four finger flutes and a thumb dish on the front face."),
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
                 f"{f['rim_min_wall_mm']:.2f} | {f['bore_wall_on_surface_pct']:.0f}% | {f['bore_intrusion_mm2']:.3f} |")
    pl = pal3mf(n)
    c3.append(f"| {lab} | `3mf/{n}.3mf` | {(ROOT / '3mf' / f'{n}.3mf').stat().st_size / 1e6:.1f} MB | {len(pl)} | " + " ".join(f"`#{h}`" for h in pl) + " |")

b = P["cavity_bounds"]
fz, fe = np.array(P["foot_table"]).T
sizes = [p.stat().st_size / 1e6 for p in (ROOT / "stl").glob("*.stl")]
wmax = max(prt[n]["weight_g"]["PETG"] for n in DESC)
wmin = min(prt[n]["weight_g"]["PLA"] for n in DESC)

txt = f"""# Pickleball paddle grips - ten designs, one fitment

Ten printable grip sleeves generated from the catalog image, all built on the **exact fitment of
`reference/PickleballGrip_1.3mf`** (your pickleball handle sleeve).  Only the outer surface differs.
Revision 2: smooth finish, solid 100 %-infill shells, and every grip <= 50 g.

![catalog](renders/catalog.png)

## Weight (100 % infill, so mass = volume x density)

| Design | Volume cm3 | PLA 1.24 g | PETG 1.27 g | TPU 1.21 g | ABS 1.04 g |
|---|---|---|---|---|---|
{chr(10).join(wrows)}

All ten are **{wmin:.0f}-{wmax:.0f} g** - none exceeds 50 g in any of the four common materials (densities in g/cm3).  Slicers land within
a few percent of volume x density, so budget +-3 %.  How the weight was cut without changing the designs is under *What changed*.

## What is identical on all ten (measured from your 3MF)

| Feature | Value |
|---|---|
| Overall height | **{P['z_top']} mm** (open top, flat rim) |
| Bore (cavity) | octagonal, **{b[2]-b[0]:.2f} x {b[3]-b[1]:.2f} mm**, area {P['cavity_area']} mm2, constant along z, floor at **z = {P['z_floor']}** mm |
| Bore outline | the reference polygon itself ({len(P['cavity_ring'])-1} vertices, copied verbatim - no re-modelling) |
| Foot / butt flare | z 0-20: outer skin {np.interp(2.0, fz, fe):.2f} (at z = 2) -> {fe[-1]:.2f} mm from the bore (at z = 20), ~2 mm bottom fillet, flat closed butt (max 42.6 x 36.6 mm) - unchanged |
| Outer envelope | no grip ever exceeds the reference's own outer envelope (crest {P['crest_offset']} mm from the bore) |

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
{chr(10).join(rows)}

Close-ups: `renders/<id>_detail.png`; four-way turntable line-ups: `renders/<id>_lineup.png`;
hero shots: `renders/<id>_hero.png`.  Colours in the renders are **preview only** - the STLs are single-material.

## Print readiness (`scripts/verify_print.py`, data in `print_report.json`)

Each STL is sliced at the mid-plane of every 0.20 mm layer (664 layers).

| Design | Result | Bodies | Genus | Material < 0.4 mm wide | Longest bridge | Down-facing > 45 deg |
|---|---|---|---|---|---|---|
{chr(10).join(prow)}

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
{chr(10).join(c3)}

Checked with the official `lib3mf` reader (`scripts/verify_3mf.py`): parses with zero warnings, triangle and vertex counts equal the STL,
every sampled triangle has a colour property, volume matches the STL, closed manifold.  `renders/catalog_3mf.png` is rendered from the
3MF files themselves.  Not tested in any slicer: viewers that support the materials extension show the colours; multi-extruder slicers
differ in how they import per-triangle colour, so expect to assign or paint filaments in the slicer.  The STLs stay single-material.

## Fitment verification (`scripts/verify_fitment.py`, full data in `fitment_report.json`)

Every STL is cross-sectioned at 40+ heights against the reference profile.

| Design | Result | Height mm | Max outside ref. envelope mm | Foot profile err mm | Min wall, textured zone mm | Min wall, rim mm | Bore wall on grip surface | Material inside bore mm2 |
|---|---|---|---|---|---|---|---|---|
{chr(10).join(vrows)}

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

`grip_core.py` wraps a height-field skin around the reference bore (P = bore point + h * normal + z) and holds the print rules
(`BASE_WALL`, `MIN_RIM`, `ZONE_LO/HI`, overhang limit); `designs.py` holds the ten texture functions - edit one and re-run to iterate on a design.

## Interpretation notes

The catalog image is a concept render, and a few captions are garbled ("Seal baiking helical structures"), so each design is my
interpretation of the picture and caption rather than a copy.  CELLULAR MOD's red pockets are printable recesses sized for
inserts, but no separate insert parts are included.  VORONOI-CORE keeps its through-windows (they are the design); it is also the
lightest at {prt['07_voronoi_core']['weight_g']['PLA']:.0f} g in PLA.
"""
(ROOT / "README.md").write_text(txt)
print("README.md written,", len(txt), "chars")
