#!/usr/bin/env python3
"""Fit-test coupon for the paddle slot: an 8 mm tall block with three through-slots, 30.2 mm wide and 12.2 / 12.5 / 12.8 mm
thick (one, two and three grooves on the +x end face).  Print it upright like a grip (a few minutes) and push the paddle handle
through: the slot that slides on snugly gives PADDLE_T (+ SLOT_CLEAR) for grip_core.py.

usage:  python3 make_fit_test.py          -> ../stl/fit_test_slot.stl
"""
import sys
from pathlib import Path

import numpy as np
import trimesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
from grip_core import PADDLE_W, SLOT_CLEAR, SLOT_R, MOUTH_CHAMFER, write_stl  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
THICK = (12.2, 12.5, 12.8)     # mm - slot thicknesses to try (the grip uses PADDLE_T + SLOT_CLEAR = 12.2)
WALL, HEIGHT = 3.5, 8.0        # mm


def main():
    import manifold3d as m3d
    from shapely.geometry import box
    w = PADDLE_W + SLOT_CLEAR
    ys, y = [], WALL
    for t in THICK:
        ys.append((y, y + t))
        y += t + WALL
    W, D = w + 2 * WALL, y
    body = m3d.Manifold.cube((W, D, HEIGHT))
    cuts = []
    for k, (y0, y1) in enumerate(ys):
        slot = box(WALL + SLOT_R, y0 + SLOT_R, WALL + w - SLOT_R, y1 - SLOT_R).buffer(SLOT_R, 16)
        pm = trimesh.creation.extrude_polygon(slot, HEIGHT + 2.0)
        pm.apply_translation((0, 0, -1.0))
        cuts.append(m3d.Manifold(m3d.Mesh(np.asarray(pm.vertices, np.float32), np.asarray(pm.faces, np.uint32))))
        # 45 degree lead-in at the top of each slot, like the grip's mouth
        top = slot.buffer(MOUTH_CHAMFER + 0.1, 16)
        pts = np.vstack([np.c_[np.asarray(top.exterior.coords)[:-1], np.full(len(top.exterior.coords) - 1, HEIGHT + 0.1)],
                         np.c_[np.asarray(slot.exterior.coords)[:-1], np.full(len(slot.exterior.coords) - 1, HEIGHT - MOUTH_CHAMFER)]])
        hull = trimesh.convex.convex_hull(pts)
        cuts.append(m3d.Manifold(m3d.Mesh(np.asarray(hull.vertices, np.float32), np.asarray(hull.faces, np.uint32))))
        # k + 1 grooves on the +x end face, beside this slot
        yc = (y0 + y1) / 2
        for g in range(k + 1):
            cuts.append(m3d.Manifold.cube((2.0, 0.8, HEIGHT + 2.0)).translate((W - 1.0, yc + (g - k / 2) * 2.0 - 0.4, -1.0)))
    res = m3d.Manifold.batch_boolean([body] + cuts, m3d.OpType.Subtract).to_mesh()
    V = np.asarray(res.vert_properties[:, :3], np.float64)
    V[:, 0] -= W / 2
    V[:, 1] -= D / 2
    Fc = np.asarray(res.tri_verts, np.int32)
    out = ROOT / "stl" / "fit_test_slot.stl"
    write_stl(out, V, Fc)
    m = trimesh.Trimesh(V, Fc, process=True)
    print(f"wrote {out}  {W:.1f} x {D:.1f} x {HEIGHT:.0f} mm  watertight={m.is_watertight}  {m.volume / 1000 * 1.24:.1f} g PLA  "
          f"slots {' / '.join(f'{t:.1f}' for t in THICK)} mm")


if __name__ == "__main__":
    main()
