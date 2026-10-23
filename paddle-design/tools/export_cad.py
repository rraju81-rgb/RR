#!/usr/bin/env python3
"""Export the 3-D model of both paddles and its mass properties.

    python tools/export_cad.py

Writes output/cad/<design>_assembly.step (all parts, named), output/cad/<design>_rib_core.step,
one STL per part (mm) and analysis/mass_properties.json (mass, balance point, swing weight).
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from build123d import export_step  # noqa: E402

from paddle import cad  # noqa: E402
from paddle.geometry import DESIGNS, build  # noqa: E402

out = ROOT / "output" / "cad"
mass = {}
for sp in DESIGNS:
    parts = cad.assembly(build(sp))
    out.mkdir(parents=True, exist_ok=True)
    core = next(p for p in parts if p.name == "rib_core")
    export_step(core.shape, str(out / f"{sp.key}_rib_core.step"))      # before cad.export re-parents the parts
    cad.export(parts, sp.key, out)
    mp = cad.mass_properties(parts)
    mp["parts"] = {k: {kk: round(vv, 2) if isinstance(vv, float) else vv for kk, vv in v.items()}
                   for k, v in mp["parts"].items()}
    mass[sp.key] = {k: round(v, 1) if isinstance(v, float) else v for k, v in mp.items()}
    print(f"{sp.name:9s} {mass[sp.key]['mass_g']:.0f} g, balance {mass[sp.key]['balance_mm']:.0f} mm, "
          f"swing weight {mass[sp.key]['swing_weight_kgcm2']:.0f} kg cm2 -> {out}")
(ROOT / "analysis" / "mass_properties.json").write_text(json.dumps(mass, indent=1))
