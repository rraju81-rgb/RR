#!/usr/bin/env python3
"""Writes README.md, pulling the verification numbers from fitment_report.json."""
import json
from pathlib import Path

import re
import zipfile

import numpy as np

ROOT = Path(__file__).resolve().parent
rep = {r["name"]: r for r in json.loads((ROOT / "fitment_report.json").read_text())}
P = json.loads((ROOT / "data" / "reference_profile.json").read_text())

DESC = {
    "01_vortex_grip": ("VORTEX GRIP", "8 + 8 counter-wound straps (36 deg helix) braided over/under; dark valleys between straps give multi-point contact.", "straps 0.7-1.0 relief, valleys 0.1"),
    "02_cellular_mod": ("CELLULAR MOD", "9 rows x 8 staggered cells, 1.4 mm gaps; cells on 3 heights, ~22% recessed as insert pockets (red in the preview).", "pockets ~1 mm deep"),
    "03_tessel_block": ("TESSEL-BLOCK", "10 rows x 24 triangles (12 up + 12 down per row, 10.2 mm base), each a faceted pyramid; up-triangles stand taller than down-triangles.", "V-grooves between facets"),
    "04_logic_grip": ("LOGIC-GRIP", "8 x 6 interlocking jigsaw pieces with mushroom knobs, 1.1 mm grooves, shallow dome tops.", "random knob directions (seeded)"),
    "05_neuro_tread": ("NEURO-TREAD", "Periodic Delaunay 'neuron' graph: curved 1.5 mm axon ridges, soma nodes, over a hex-packed bump base (2.7 mm pitch).", "network at crest, base ~0.3-0.5"),
    "06_carbon_matrix": ("CARBON MATRIX", "2/2 twill weave (2 mm tow pitch) with smooth raised reinforcement patches (selective reinforcing).", "weave 0.5-0.7, patches 0.95"),
    "07_voronoi_core": ("VORONOI-CORE", "Lloyd-relaxed Voronoi rib lattice (2.6 mm ribs, rounded tops); 54 cells cut clean through the wall for weight and airflow.", "54 through-windows"),
    "08_topo_flow": ("TOPO-FLOW", "Contour ridges of a terrain/wood-knot height field - continuous undulating lines flowing around four knots.", "contour ridge period ~2-7 mm"),
    "09_ergo_contour": ("ERGO-CONTOUR", "Smooth hour-glass swell, palm pad on the back, four finger flutes and a thumb dish on the front face.", "0.28-1.0 relief, no sharp edges"),
    "10_hexa_mod": ("HEXA-MOD", "12-column hex pads (10.2 mm across flats), 1.7 mm gaps, four height levels (red = tallest).", "levels 0.50 / 0.68 / 0.84 / 1.0"),
}

rows = []
for n, (lab, txt, note) in DESC.items():
    r = rep[n]
    rows.append(f"| {n[:2]} | **{lab}** | `stl/{n}.stl` | {txt} | {r['volume_cm3']} | {r['tris']:,} |")

vrows = []
for n, (lab, _, _) in DESC.items():
    r = rep[n]
    vrows.append(f"| {lab} | {'PASS' if r['pass'] else 'FAIL'} | {'yes' if r['watertight'] else 'NO'} | {r['z_max']:.3f} | "
                 f"{r['max_over_reference_envelope_mm']:+.3f} | {r['foot_profile_err_mm']:.3f} / {r['taper_profile_err_mm']:.3f} | "
                 f"{r['bore_wall_on_surface_pct']:.0f}% | {r['bore_intrusion_mm2']:.3f} |")

def pal3mf(n):
    with zipfile.ZipFile(ROOT / "3mf" / f"{n}.3mf") as z:
        return re.findall(r'<m:color color="#([0-9A-F]{6})FF"/>', z.read("3D/3dmodel.model").decode())


c3 = []
for n, (lab, _, _) in DESC.items():
    p = pal3mf(n)
    c3.append(f"| {lab} | `3mf/{n}.3mf` | {(ROOT / '3mf' / f'{n}.3mf').stat().st_size / 1e6:.1f} MB | {len(p)} | " + " ".join(f"`#{h}`" for h in p) + " |")

b = P["cavity_bounds"]
fz, fe = np.array(P["foot_table"]).T
sizes = [p.stat().st_size / 1e6 for p in (ROOT / "stl").glob("*.stl")]
txt = f"""# Pickleball paddle grips - ten designs, one fitment

Ten printable grip sleeves generated from the catalog image, all built on the **exact fitment of
`reference/PickleballGrip_1.3mf`** (your pickleball handle sleeve).  Only the outer surface differs.

![catalog](renders/catalog.png)

## What is identical on all ten (measured from your 3MF)

| Feature | Value |
|---|---|
| Overall height | **{P['z_top']} mm** (open top, flat rim) |
| Bore (cavity) | octagonal, **{b[2]-b[0]:.2f} x {b[3]-b[1]:.2f} mm**, area {P['cavity_area']} mm2, constant along z, floor at **z = {P['z_floor']}** mm |
| Bore outline | the reference polygon itself ({len(P['cavity_ring'])-1} vertices, copied verbatim - no re-modelling) |
| Foot / butt flare | z 0-20: outer skin {np.interp(2.0, fz, fe):.2f} (at z = 2) -> {fe[-1]:.2f} mm from the bore (at z = 20), ~2 mm bottom fillet, flat closed butt (max 42.6 x 36.6 mm) |
| Textured zone | z 23-108 (smooth collars z 20-23 and 108-112): base wall **{P['wall_offset']} mm**, crest **{P['crest_offset']} mm** from the bore |
| Top taper | z 110 -> {P['z_top']}: skin tapers from {P['crest_offset']} mm to {P['taper_table'][-1][1]:.2f} mm from the bore (same curve as the reference) |

Reference bounding box 42.64 x 36.62 x 132.823 mm; all ten grips: 42.63 x 36.61 x 132.82 mm.

## The ten grips

| # | Design | File | Concept | Volume cm3 | Triangles |
|---|---|---|---|---|---|
{chr(10).join(rows)}

Close-ups: `renders/<id>_detail.png`; four-way turntable line-ups: `renders/<id>_lineup.png`;
hero shots: `renders/<id>_hero.png`.  Colours in the renders are **preview only** - the STLs are single-material.

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

Every STL is cross-sectioned at 40 heights against the reference profile.

| Design | Result | Watertight | Height mm | Max outside ref. envelope mm | Foot / taper profile err mm | Bore wall on grip surface | Material inside bore mm2 |
|---|---|---|---|---|---|---|---|
{chr(10).join(vrows)}

* *Max outside ref. envelope* - how far the outer skin ever exceeds the reference's own outer envelope (positive = bigger).
* *Bore wall on grip surface* - share of sampled reference-bore points that lie on the grip's surface.  100% = the bore
  is identical; VORONOI-CORE is lower **by design** because its windows open the wall (the bore itself is unchanged).
* *Material inside bore* - area of material within the bore shrunk by 0.1 mm, worst case over 40 heights (must be 0).
* Floor at z = 5 and open top confirmed on all ten; each STL is one closed manifold body (VORONOI-CORE has 54 through-windows).

![fit overlay](renders/fit_overlay.png)

## Printing notes

* Print **upright, butt-end down** (same orientation as the reference).  Outer skins are limited to 45 degrees of
  overhang (each texture grows outward by at most 1 mm per mm of height), so they should print without supports.
  VORONOI-CORE's windows have angled roofs that must bridge a few mm - fine for most printers, but preview the slice.
* Grooves, gaps and ribs are 1.0 mm or wider; the finest texture is the carbon weave (2 mm tow pitch, ~0.3 mm relief).
* **Inherited from your reference:** the tapered top ends in a rim only ~0.36 mm thick, thinner than one 0.4 mm line.  I kept it
  identical so the fit and feel at the throat are unchanged; if your slicer complains, thicken the last ~3 mm.
* Surfaces are sampled every 0.25 mm; the STLs are {min(sizes):.0f}-{max(sizes):.0f} MB each ({sum(sizes):.0f} MB total).  `python3 scripts/generate_grips.py --res 0.35` makes lighter files.
* These are geometry-verified (watertight, cross-section-checked against your 3MF) but I have not run them through a slicer
  or printed them - do a preview slice before committing filament.

## Regenerating

```
pip install numpy scipy trimesh shapely manifold3d pillow mapbox_earcut matplotlib playwright lib3mf
cd scripts
python3 extract_reference_profile.py          # reference 3MF -> data/reference_profile.json
python3 generate_grips.py                     # -> stl/*.stl   (~15 s)
python3 verify_fitment.py                     # -> fitment_report.json
python3 export_3mf.py && python3 verify_3mf.py   # -> 3mf/*.3mf (colored), validated with lib3mf
npm install && python3 render_grips.py --catalog   # -> renders/*.png (headless Chromium + three.js)
python3 make_fit_overlay.py
```

`grip_core.py` wraps a height-field skin around the reference bore (P = bore point + h * normal + z), `designs.py` holds the ten texture
functions - edit one and re-run to iterate on a design.  Numbers above (relief levels, counts, sizes) are the constants in that file.

## Interpretation notes

The catalog image is a concept render, and a few captions are garbled ("Seal baiking helical structures"), so each design is my
interpretation of the picture and caption rather than a copy.  CELLULAR MOD's red pockets are printable recesses sized for
inserts, but no separate insert parts are included.
"""
(ROOT / "README.md").write_text(txt)
print("README.md written,", len(txt), "chars")
