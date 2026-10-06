"""PITLANE fixed sliding rack: the user's 6-ledge rack (fused/reference/rack_6ledge_130_3mmholes.stl) with no hinge -
the ledges are solid with the wall mount, cards slide into the slot from the open end. Right-hand and mirrored left-hand version.
python3 build_fixed.py -> fixed/*.stl.  Frame: x right, y up, z out of the wall.  Units mm."""
import os, sys
import numpy as np, trimesh
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "legacy"))
from build_simple import box, cylz, union, diff, inter, prism_z
from build_liftoff import REF, W, SPX, spine_t, n, pitch, led_h, step, ch, front_ref, rear_ref, mirror, to_print_wall, LEFT_DY

H = 350.0                                                     # 35 cm wall mount (reference was 449)
holes = [(4.0, 28.0), (4.0, 138.0), (4.0, 303.0)]; hole_d = 3.0
blk = 21.6                                                    # end block (closed end of the card slot) = reference hinge block

def rack():
    ref = trimesh.load(REF)
    parts = [box(SPX, 14.0, 0, H, 0, spine_t)]
    cham = []
    for j in range(n):
        y0 = pitch * j; zf = front_ref(j)
        parts.append(inter([ref, box(16.0, W + 1, y0 - 0.01, y0 + led_h + 0.01, rear_ref(j) - 0.01, 60)]))   # ledge (as reference)
        parts.append(box(SPX, blk, y0, y0 + led_h, 0, zf + 5.3))                                           # solid stand-off + end stop
        for x_in, sgn in ((30.5, -1), (121.0, 1)):
            tri = [(x_in, y0 + 4.0), (x_in + sgn * ch, y0 + 4.0 + ch), (x_in + sgn * ch, y0 + 30), (x_in - sgn * 0.01, y0 + 30), (x_in - sgn * 0.01, y0 + 4.0)]
            cham.append(prism_z(tri, zf + 1.0, zf + 8.0))
    return diff(union(parts), cham + [cylz(x, y, -1, 50, hole_d / 2, 32) for x, y in holes])

if __name__ == "__main__":
    r = rack()
    os.makedirs("fixed", exist_ok=True)
    to_print_wall(r).export("fixed/right_fixed_rack_PRINT.stl")
    to_print_wall(mirror(r), True).export("fixed/left_fixed_rack_PRINT.stl")
    trimesh.util.concatenate([r, mirror(r, LEFT_DY)]).export("fixed/pair_assembled_demo.stl")
    print("fixed", r.is_watertight, len(r.split()), np.round(r.extents, 1), round(r.volume))
