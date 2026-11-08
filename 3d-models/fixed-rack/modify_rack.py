#!/usr/bin/env python3
"""
Applies the design fixes to the fixed card rack and writes new print-ready STLs.

Input : original/left_fixed_rack_PRINT.stl   (right rack is an exact X-mirror of it)
Output: left_fixed_rack_PRINT_v2.stl, right_fixed_rack_PRINT_v2.stl

Model layout (print orientation, mm):
  * Rail along Y (0..350), x 0..6, z 0..20, with three M3 mounting holes along X.
  * 6 tiers k = 0..5, at y0 = 55*k, each stepped out by dx = 4.6*k in X:
      - spacer block   x 0..9+dx, y y0..y0+22, z 0..27.6
      - arm plate      x 1.3+dx..3.7+dx (2.4 mm thick), z 27.6..136
      - hook / lip     x 5.05+dx..9+dx; card slot = gap x 3.7+dx..5.05+dx
        at the root (z 27.6..36.5) and at the tip (z 127..136).

Changes:
  1. Card-slot root rebuilt + chamfers (strength):
     - the original root gusset of every lip floated 0.1 mm above the block
       (z 27.6 -> 27.7) and had a loose 0.1 mm sliver at z 36.5, so the lip
       was barely fused to the block -> it snapped there. Rebuilt as one
       solid piece that sits directly on the block.
     - 45 deg root chamfer on the outside of the lip (2.5 mm).
     - 0.5 mm chamfers in both bottom corners of the card slot (removes the
       sharp notch the crack started from).
     - 3 mm x 45 deg chamfer where the 2.4 mm arm plate meets the block on the
       rail side (1.2 mm on tier 0 where there is less room). The card side of
       the plate is left flat so the card still sits flush.
  2. Material removed from the wide upper tiers (k = 3, 4, 5): the solid
     spacer block becomes an open L -- 6 mm floor on the bed + a solid column
     under the arm, meeting at a plain 90 deg corner (prints without
     supports or bridges).
  3. Print-support fixes:
     - mounting holes turned into 45 deg teardrops (no drooping hole roof).
     - 0.45 mm flat ledge where the groove narrows into the tip slot (z 127)
       replaced by a 45 deg ramp.
"""
import math
import os
import sys

import manifold3d as mf
import numpy as np
import trimesh

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "original", "left_fixed_rack_PRINT.stl")

N_TIERS = 6
PITCH_Y = 55.0
STEP_X = 4.6
BLOCK_TOP = 27.6
RAIL_W = 6.0
TOTAL_W = 32.0

# local (tier) coordinates, x' = x - dx, y' = y - y0
PLATE_IN = 1.3        # rail-side face of arm plate
PLATE_OUT = 3.7       # card-side face of arm plate
LIP_IN = 5.05         # inner face of lip (slot = PLATE_OUT..LIP_IN)
LIP_IN_GROOVE = 5.5   # groove wall above the root slot
LIP_OUT = 9.0         # outer face of lip == block edge

PLATE_ROOT_CHAMFER = 3.0
LIP_ROOT_CHAMFER = 2.5
SLOT_CHAMFER = 0.5
E = 0.05              # boolean overlap
FLOOR = 6.0           # floor thickness of the L-shaped spacer
COLUMN_LAND = 1.0     # flat land between column edge and plate chamfer
RAIL_H = 20.0         # rail height

HOLES_Y = (28.0, 138.0, 303.0)
HOLE_Z = 10.0
HOLE_R = 1.5


def load(path):
    m = trimesh.load(path)
    return mf.Manifold(mf.Mesh(
        vert_properties=np.asarray(m.vertices, dtype=np.float32),
        tri_verts=np.asarray(m.faces, dtype=np.uint32)))


def hull(points):
    return mf.Manifold.hull_points([tuple(map(float, p)) for p in points])


def box(x0, x1, y0, y1, z0, z1):
    return mf.Manifold.cube((x1 - x0, y1 - y0, z1 - z0)).translate((x0, y0, z0))


def prism_x(poly_yz, x0, x1):
    return hull([(x, y, z) for (y, z) in poly_yz for x in (x0, x1)])


def prism_y(poly_xz, y0, y1):
    return hull([(x, y, z) for (x, z) in poly_xz for y in (y0, y1)])


def union_all(parts):
    return mf.Manifold.batch_boolean(parts, mf.OpType.Add) if parts else mf.Manifold()


def build_left():
    part = load(SRC)
    adds, subs = [], []

    for k in range(N_TIERS):
        dx, y0 = STEP_X * k, PITCH_Y * k
        X = lambda v: v + dx
        Y = lambda v: v + y0

        # --- 1a. rebuild card-slot root (lip + gusset) as clean solid --------
        # Cut faces never coincide with existing faces and every added piece
        # overlaps solid material by E, so no zero-thickness seams are left.
        subs.append(box(X(PLATE_OUT) + E, X(LIP_OUT) + 1.0, Y(-0.01), Y(10.6),
                        BLOCK_TOP + E, 37.0))
        adds.append(box(X(PLATE_OUT) - E, X(LIP_OUT) - E, Y(E), Y(3) + E,
                        BLOCK_TOP - E, 37.0 + 4 * E))
        c = LIP_ROOT_CHAMFER
        adds.append(prism_x([(Y(3) - E, BLOCK_TOP - E), (Y(10 + c), BLOCK_TOP - E),
                             (Y(10), 30.5), (Y(4), 36.5), (Y(3) - E, 36.5)],
                            X(LIP_IN), X(LIP_OUT) - E))
        adds.append(box(X(LIP_IN_GROOVE) - E, X(LIP_OUT) - E, Y(3) - E, Y(4) + E,
                        36.5 - E, 37.0 + 4 * E))

        # --- 1b. 0.5 mm chamfers in the bottom corners of the card slot -----
        s = SLOT_CHAMFER
        adds.append(prism_y([(X(PLATE_OUT) - E, BLOCK_TOP - E),
                             (X(PLATE_OUT) + s + E, BLOCK_TOP - E),
                             (X(PLATE_OUT) - E, BLOCK_TOP + s + E)], Y(3), Y(10)))
        adds.append(prism_y([(X(LIP_IN) + E, BLOCK_TOP - E),
                             (X(LIP_IN) - s - E, BLOCK_TOP - E),
                             (X(LIP_IN) + E, BLOCK_TOP + s + E)], Y(3), Y(10)))

        # --- 1c. arm-plate root chamfer on the rail side ---------------------
        pc = PLATE_ROOT_CHAMFER if k > 0 else 1.2
        adds.append(prism_y([(X(PLATE_IN) + E, BLOCK_TOP - E),
                             (X(PLATE_IN) - pc - E, BLOCK_TOP - E),
                             (X(PLATE_IN) + E, BLOCK_TOP + pc + E)], Y(0), Y(22)))

        # --- 3b. 45 deg ramp under the 0.45 mm ledge at the tip slot --------
        r = LIP_IN_GROOVE - LIP_IN
        adds.append(prism_y([(X(LIP_IN) - E, 127.0 + E), (X(LIP_IN_GROOVE) + E, 127.0 + E),
                             (X(LIP_IN_GROOVE) + E, 127.0 - r - 2 * E)],
                            Y(3) - E, Y(4) - E))

        # --- 2. open L-shaped spacer on the wide tiers ----------------------
        # Everything between the rail and the arm is cut away from the top,
        # leaving a floor on the bed + a solid column under the arm that meet
        # at a plain 90 deg corner (no enclosed window, no overhangs).
        xc = X(PLATE_IN) - pc - COLUMN_LAND      # inner face of the column
        if xc - RAIL_W >= 4.0:
            # above the rail: lower the block back to rail height
            subs.append(box(-1.0, xc, Y(-0.5), Y(22.5), RAIL_H - E, 140.0))
            # between rail and column: down to the floor
            subs.append(box(RAIL_W - E, xc, Y(-0.5), Y(22.5), FLOOR, 140.0))

    # --- 3a. teardrop mounting holes (point up, 45 deg) ----------------------
    a = HOLE_R / math.sqrt(2)
    for hy in HOLES_Y:
        subs.append(prism_x([(hy - a, HOLE_Z + a), (hy + a, HOLE_Z + a),
                             (hy, HOLE_Z + HOLE_R * math.sqrt(2)), (hy, HOLE_Z)],
                            -1.0, RAIL_W + 1.0))

    # removal first (clears the defective root geometry), then additions
    part = part - union_all(subs)
    part = part + union_all(adds)
    return part


def to_trimesh(man):
    mesh = man.to_mesh()
    return trimesh.Trimesh(np.asarray(mesh.vert_properties)[:, :3],
                           np.asarray(mesh.tri_verts), process=False)


def main():
    left = build_left()
    if left.status() != mf.Error.NoError:
        sys.exit(f"boolean failed: {left.status()}")
    right = left.mirror((1, 0, 0)).translate((TOTAL_W, 0, 0))

    for name, man in (("left", left), ("right", right)):
        t = to_trimesh(man)
        out = os.path.join(HERE, f"{name}_fixed_rack_PRINT_v2.stl")
        t.export(out)
        print(f"{name}: watertight={t.is_watertight} bodies={len(t.split(only_watertight=False))} "
              f"volume={t.volume:.0f} mm3 bounds={np.round(t.bounds, 2).tolist()} -> {out}")


if __name__ == "__main__":
    main()
