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
    "diffuser_shell": "shell",
    "diffuser_clamp_upper": "anodised",
    "diffuser_clamp_lower": "anodised",
    "diffuser_screw_1": "steel",
    "diffuser_screw_2": "steel",
}

# exploded-view offsets in G (mm): guard parts fan out along the bar axis, the wind guard rides
# with the blade and opens up around it
EXPLODE = {
    "expander_cone": (-46, 0, 0),
    "expander_sleeve": (-24, 0, 0),
    "adapter": (0, 0, 0),
    "arm": (22, 0, 0),
    "blade": (44, 0, 0),
    "m5_screw_1": (66, 0, 0),
    "m5_screw_2": (66, 0, 0),
    "m6_bolt": (92, 0, 0),
    "diffuser_shell": (44, 18, 30),
    "diffuser_clamp_upper": (44, 0, 24),
    "diffuser_clamp_lower": (44, 0, -24),
    "diffuser_screw_1": (44, 0, -48),
    "diffuser_screw_2": (44, 0, -48),
}

LABEL = {
    "adapter": "Bar-end adapter",
    "arm": "Guard arm",
    "blade": "Carbon blade",
    "m6_bolt": "M6 x 45 cap screw",
    "m5_screw_1": "M5 x 14 button screw",
    "m5_screw_2": "M5 x 14 button screw",
    "expander_sleeve": "Expander sleeve (M)",
    "expander_cone": "Expander cone nut",
    "ref_handlebar": "Handlebar (reference)",
    "ref_grip": "Grip (reference)",
    "ref_lever": "Brake lever (reference)",
    "diffuser_shell": "Wind guard shell (right)",
    "diffuser_clamp_upper": "Wind guard clamp half",
    "diffuser_clamp_lower": "Wind guard clamp half",
    "diffuser_screw_1": "M4 x 25 screw, nyloc nut, sleeve",
    "diffuser_screw_2": "M4 x 25 screw, nyloc nut, sleeve",
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
        pos, idx = tessellate(wp, 0.02 if fine else 0.05, 0.12 if fine else 0.2)
        meshes.append(
            {
                "name": name,
                "label": LABEL[name],
                "group": group,
                "material": MATERIAL[name],
                "explode": EXPLODE.get(name, (0, 0, 0)),
                "slides": name == "blade" or name.startswith("diffuser"),
                "runSlide": name.startswith("diffuser"),
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
        "run_dir": p.run_dir,
        "clamp_range": p.clamp_range,
        "summary": summary,
        "meshes": meshes,
    }


if __name__ == "__main__":
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "scene.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    scene = build_scene()
    out.write_text(json.dumps(scene, separators=(",", ":")))
    print(f"wrote {out} ({out.stat().st_size / 1e6:.2f} MB)")
