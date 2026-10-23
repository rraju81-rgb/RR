"""Tessellate the guard and the reference bike parts into one JSON scene for the 3D viewer.

    python scene.py out/scene.json

Each mesh is stored in the guard frame G (see cad/lever_guard.py) as base64 float32
positions + uint32 triangle indices. Vertices are not shared between CAD faces, so smooth
normals computed in the viewer keep the machined edges crisp.
"""

from __future__ import annotations

import base64
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "cad"))

import lever_guard as lg  # noqa: E402

MATERIAL = {
    "adapter": "anodised",
    "arm": "anodised",
    "blade": "carbon",
    "m6_bolt": "steel",
    "m5_screw_1": "steel",
    "m5_screw_2": "steel",
    "expander_sleeve": "rubber",
    "expander_cone": "alu",
    "ref_handlebar": "bar",
    "ref_grip": "grip",
    "ref_lever": "lever",
}

# exploded-view offsets along the bar axis (mm)
EXPLODE = {
    "expander_cone": -46,
    "expander_sleeve": -24,
    "adapter": 0,
    "arm": 22,
    "blade": 44,
    "m5_screw_1": 66,
    "m5_screw_2": 66,
    "m6_bolt": 92,
}

LABEL = {
    "adapter": "Bar-end adapter",
    "arm": "Guard arm",
    "blade": "Carbon blade",
    "m6_bolt": "M6 x 45 cap screw",
    "m5_screw_1": "M5 x 12 button screw",
    "m5_screw_2": "M5 x 12 button screw",
    "expander_sleeve": "Expander sleeve (M)",
    "expander_cone": "Expander cone nut",
    "ref_handlebar": "Handlebar (reference)",
    "ref_grip": "Grip (reference)",
    "ref_lever": "Brake lever (reference)",
}


def b64(a: np.ndarray) -> str:
    return base64.b64encode(np.ascontiguousarray(a).tobytes()).decode("ascii")


def tessellate(wp, tol: float, ang: float) -> tuple[np.ndarray, np.ndarray]:
    verts, tris = wp.val().tessellate(tol, ang)
    pos = np.array([(v.x, v.y, v.z) for v in verts], dtype="<f4")
    idx = np.array(tris, dtype="<u4").reshape(-1)
    return pos, idx


def build_scene(p: lg.Params = lg.Params()) -> dict:
    items = [(n, wp, "guard") for n, wp, _ in lg.guard_parts(p, size="M")]
    items += [(n, wp, "reference") for n, wp, _ in lg.reference_parts(p)]
    meshes = []
    for name, wp, group in items:
        fine = group == "guard"
        pos, idx = tessellate(wp, 0.01 if fine else 0.05, 0.08 if fine else 0.2)
        meshes.append(
            {
                "name": name,
                "label": LABEL[name],
                "group": group,
                "material": MATERIAL[name],
                "explode": EXPLODE.get(name, 0),
                "slides": name == "blade",
                "positions": b64(pos),
                "indices": b64(idx),
                "triangles": int(len(idx) // 3),
            }
        )
        print(f"  {name:16s} {len(idx) // 3:7d} triangles")
    summary_path = HERE.parent / "exports" / "summary.json"
    summary = json.loads(summary_path.read_text()) if summary_path.exists() else {}
    return {
        "frame": "G: X out of the bar end, Y toward the lever, Z normal to the lever plane (mm)",
        "teeth": p.teeth,
        "adjust": p.adjust,
        "summary": summary,
        "meshes": meshes,
    }


if __name__ == "__main__":
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "scene.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    scene = build_scene()
    out.write_text(json.dumps(scene, separators=(",", ":")))
    print(f"wrote {out} ({out.stat().st_size / 1e6:.2f} MB)")
