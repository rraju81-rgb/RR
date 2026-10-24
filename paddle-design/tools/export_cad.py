#!/usr/bin/env python3
"""Export the 3-D model of both paddles with the printed grip, and the mass properties.

    python tools/export_cad.py [--grip 06_carbon_matrix]

Writes to output/cad/:
  <design>_assembly.step     face sheets, rib core, M3 screw and insert (named B-rep solids)
  <design>_assembly.3mf      the same plus the printed grip, in place, as one multi-part file for viewers/slicers
  <design>_<part>.stl        every B-rep part in mm (the grip STLs themselves are in reference/grips/)
and analysis/mass_properties.json (mass, balance point, swing weight; grip in PLA at 100 % infill).
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import trimesh  # noqa: E402
from build123d import export_step  # noqa: E402

from paddle import cad, grip  # noqa: E402
from paddle.geometry import DESIGNS, GRIP, build  # noqa: E402

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("--grip", default=grip.DEFAULT, choices=sorted(grip.DESIGNS))
a = ap.parse_args()

out = ROOT / "output" / "cad"
out.mkdir(parents=True, exist_ok=True)
for old in out.glob("*"):                      # parts of the previous grip hardware must not linger
    old.unlink()
g = grip.load(a.grip)
mass = {"grip": dict(design=a.grip, name=grip.DESIGNS[a.grip], material=f"PLA {GRIP.pla_density} g/cm3, 100 % infill")}
for sp in DESIGNS:
    parts = cad.assembly(build(sp))
    core = next(p for p in parts if p.name == "rib_core")
    export_step(core.shape, str(out / f"{sp.key}_rib_core.step"))      # before cad.export re-parents the parts
    scene = trimesh.Scene()
    for p in parts:
        v, f = cad.tessellate(p.shape, 0.03, 0.15)
        scene.add_geometry(trimesh.Trimesh(v, f, process=True), node_name=p.name, geom_name=p.name)
    scene.add_geometry(g, node_name=f"grip_{a.grip}", geom_name=f"grip_{a.grip}")
    scene.export(str(out / f"{sp.key}_assembly.3mf"))
    cad.export(parts, sp.key, out)
    mp = cad.mass_properties(parts, meshes=[("grip", g, GRIP.pla_density)])
    mp["parts"] = {k: {kk: round(vv, 2) if isinstance(vv, float) else vv for kk, vv in v.items()}
                   for k, v in mp["parts"].items()}
    mass[sp.key] = {k: round(v, 1) if isinstance(v, float) else v for k, v in mp.items()}
    print(f"{sp.name:9s} {mass[sp.key]['mass_g']:.0f} g with the {grip.DESIGNS[a.grip]} grip, balance "
          f"{mass[sp.key]['balance_mm']:.0f} mm, swing weight {mass[sp.key]['swing_weight_kgcm2']:.0f} kg cm2 -> {out}")
(ROOT / "analysis" / "mass_properties.json").write_text(json.dumps(mass, indent=1))
