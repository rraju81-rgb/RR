"""PITLANE lift-off rack: the user's 6-ledge rack (fused/reference/rack_6ledge_130_3mmholes.stl) with SEPARATE ledges that
drop onto lift-off hinge pins, using the user's hinge (liftoff/reference/LiftOffHinge.stl):
  - the hinge's PIN half (knuckle 10 x 15 + pin 5 x 15) is fused into the wall body below every ledge,
  - the hinge's SOCKET half (ring 10.2 x 15 with a 5.5 hole) is fused onto the hinge end of every ledge.
The hinge leaves (flat screw plates) are replaced by a solid bracket (wall) and a web (ledge).
python3 build_liftoff.py -> liftoff/*.stl.  Frame: x right, y up, z out of the wall.  Units mm."""
import os, sys
import numpy as np, trimesh
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "legacy"))
from build_simple import box, cylz, cyly, union, diff, inter, hull, prism_z

REF, HINGE = "fused/reference/rack_6ledge_130_3mmholes.stl", "liftoff/reference/LiftOffHinge.stl"
W, H0 = 130.0, 449.0                      # reference width / height
Y0 = 15.0                                 # everything moved up 15 mm: the bottom ledge gets a pin knuckle below it
H = H0 + Y0                               # 464 mm spine
SPX, spine_w, spine_t = -6.0, 14.0, 6.0   # spine x[-6, 14] = 20 mm wide (widened 6 mm towards the back edge, ledges unchanged)
holes = [(4.0, 28.0 + Y0), (4.0, 138.0 + Y0), (4.0, 303.0 + Y0)]; hole_d = 3.0
pin_r, pch = 2.5, 1.0                     # pin radius (STL), pin-root chamfer
LEFT_DY = -55.0 / 2                      # left-hand rack hangs half a pitch lower: its ledges sit between the right rack's
n, pitch, led_h, step = 6, 55.0, 22.0, 4.6
DZ = 4.1                                  # ledges 4.1 mm further out so the hinge rings clear the spine
ax_x = 6.7
kn_h = 15.0                               # hinge knuckle / socket height (from the STL)
cr = 5.1 + 0.5                            # cradle cut around each socket ring (ring r 5.1 + 0.5)
so_w = 17.0
ch = 6.0                                  # 45 deg chamfer on the inner top edge of both front corner posts
lift = kn_h + 0.5                         # lift needed to take a ledge off

def yb(j): return Y0 + pitch * j
def front_ref(j): return 3.7 + step * j
def rear_ref(j): return 0.0 if j == 0 else 1.3 + step * j
def zc(j): return front_ref(j) + 0.78 + DZ

def hinge_parts():
    """split the user's hinge into its pin half and socket half; return (knuckle+pin solid, socket ring solid, centres) in STL frame"""
    m = trimesh.load(HINGE)
    b1, b2 = sorted(m.split(only_watertight=False), key=lambda b: b.bounds[0][1])
    c1 = np.array([(b1.bounds[0][0] + 0) * 0, 0, 0])
    # knuckle centre: from the pin cross-section; socket centre: from the hole cross-section
    def centre(b, z):
        s = b.section(plane_origin=(0, 0, z), plane_normal=(0, 0, 1)); d = min(s.discrete, key=lambda d: np.ptp(np.array(d)[:, 0]))
        d = np.array(d); return np.array([(d[:, 0].min() + d[:, 0].max()) / 2, (d[:, 1].min() + d[:, 1].max()) / 2])
    cp = centre(b1, 22.0)                                                     # pin centre
    cs = centre(b2, 7.0)                                                      # hole centre (inner loop of the ring)
    pin_half = inter([b1, cylz(cp[0], cp[1], -1, 40, 5.05, 96)])                # knuckle + pin, leaf removed
    socket = inter([b2, cylz(cs[0], cs[1], -1, 40, 5.15, 96)])                  # ring, leaf removed
    return pin_half, socket, cp, cs

def to_rack(m, c, y_bottom, j):
    """STL frame (axis z, centre c, bottom z=0) -> rack frame (axis y at x=ax_x, z=zc(j), bottom at y_bottom)"""
    m = m.copy()
    T = np.array([[1, 0, 0, 0], [0, 0, 1, 0], [0, -1, 0, 0], [0, 0, 0, 1]], float)   # (x, y, z) -> (x, z, -y)
    m.apply_transform(T)
    m.apply_translation([ax_x - c[0], y_bottom, zc(j) + c[1]])
    return m

PIN_HALF, SOCKET, CP, CS = hinge_parts()

def pin_root(j):                          # 45 deg chamfer where the pin meets the knuckle (stronger pin root)
    y0 = yb(j)
    return hull(np.vstack([cyly(ax_x, zc(j), y0 - 0.5, y0, pin_r + pch, 64).vertices, cyly(ax_x, zc(j), y0 + pch - 0.01, y0 + pch, pin_r, 64).vertices]))

def wall():
    parts = [box(SPX, spine_w, 0, H, 0, spine_t)]
    for j in range(n):
        y0 = yb(j); z = zc(j)
        if j: parts.append(box(SPX, so_w, y0, y0 + led_h, 0, rear_ref(j) + DZ - 0.4))          # stand-off = 0 degree stop
        parts.append(box(SPX, ax_x + 5.0, y0 - kn_h, y0, 0, z + 5.0))                         # bracket under the knuckle
        parts.append(to_rack(PIN_HALF, CP, y0 - kn_h, j))                                    # user's knuckle + pin
    w = union(parts)
    cuts = [cylz(x, y, -1, 50, hole_d / 2, 32) for x, y in holes]
    for j in range(n):                                                                      # cradle the ring turns in
        cuts.append(cyly(ax_x, zc(j), yb(j), yb(j) + kn_h + lift + 1, cr, 72))   # tall enough to lift the ring out
        cuts.append(box(ax_x - cr, ax_x + cr, yb(j), yb(j) + kn_h + lift + 1, zc(j), 60))   # open U: lifted ledge pulls straight out
    w = diff(w, cuts)
    keep = [to_rack(PIN_HALF, CP, yb(j) - kn_h, j) for j in range(n)] + [pin_root(j) for j in range(n)]
    return union([w] + keep)

def ledge(j, ref):
    y0 = yb(j)
    body = inter([ref, box(11.5, W + 1, y0 - Y0 - 0.01, y0 - Y0 + led_h + 0.01, rear_ref(j) - 0.01, 60)])
    body.apply_translation([0, Y0, DZ])
    zf = front_ref(j) + DZ
    cham = []
    for x_in, sgn in ((30.5, -1), (121.0, 1)):
        tri = [(x_in, y0 + 4.0), (x_in + sgn * ch, y0 + 4.0 + ch), (x_in + sgn * ch, y0 + 30), (x_in - sgn * 0.01, y0 + 30), (x_in - sgn * 0.01, y0 + 4.0)]
        cham.append(prism_z(tri, zf + 1.0, zf + 8.0))
    ring = to_rack(SOCKET, CS, y0, j)
    web = box(ax_x + 3.0, 12.5, y0, y0 + kn_h, rear_ref(j) + DZ, zc(j) + 4.0)                 # joins the ring to the ledge
    hole = to_rack(cylz(CS[0], CS[1], -1, 40, 2.75, 64), CS, y0, j)                            # keep the STL's 5.5 mm hole clear
    csk = hull(np.vstack([cyly(ax_x, zc(j), y0 - 0.5, y0, 2.75 + pch, 64).vertices, cyly(ax_x, zc(j), y0 + pch - 0.01, y0 + pch, 2.75, 64).vertices]))  # matches the pin-root chamfer
    clear = [box(SPX - 1, spine_w + 0.4, y0 - 1, y0 + led_h + 1, -1, spine_t + 0.4)]
    if j: clear.append(box(SPX - 1, so_w + 0.4, y0 - 1, y0 + led_h + 1, -1, rear_ref(j) + DZ))
    l = union([diff(union([body, web]), clear + cham), ring])                                   # ring turns in the wall's cradle
    l = diff(l, [hole, csk])
    l = diff(l, [box(-5, 30, y0 - 5, y0, -5, 80)])                                            # flat bottom at the knuckle top
    return l

def mirror(m, dy=0.0):
    """left-hand copy: mirror about the spine's back edge x = SPX (spines sit back to back) and drop it dy"""
    m = m.copy(); M = np.eye(4); M[0, 0] = -1; M[0, 3] = 2 * SPX; m.apply_transform(M); m.apply_translation([0, dy, 0])
    if m.volume < 0: m.invert()
    return m

def build():
    ref = trimesh.load(REF)
    return wall(), [ledge(j, ref) for j in range(n)]

def to_print_wall(m, left=False):   # on the spine's flat back edge, pins horizontal
    m = m.copy(); m.apply_transform(trimesh.transformations.rotation_matrix((1 if left else -1) * np.pi / 2, [0, 1, 0])); m.apply_translation(-m.bounds[0]); return m
def to_print_ledge(m):         # standing on its bottom face (y up -> z up): socket ring vertical, like the hinge STL
    m = m.copy(); m.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0])); m.apply_translation(-m.bounds[0]); return m

if __name__ == "__main__":
    w, ls = build()
    os.makedirs("liftoff", exist_ok=True)
    for f in os.listdir("liftoff"):
        if f.endswith(".stl"): os.remove(os.path.join("liftoff", f))
    for side in ("right", "left"):
        L = side == "left"
        ww = mirror(w) if L else w; ll = [mirror(l) for l in ls] if L else ls
        to_print_wall(ww, L).export(f"liftoff/{side}_wall_body_PRINT.stl")
        plate, x = [], 0.0
        for j, l in enumerate(ll):
            p = to_print_ledge(l); p.export(f"liftoff/{side}_ledge_{j+1}_PRINT.stl"); p.apply_translation([0, x, 0]); plate.append(p); x += p.extents[1] + 5
        trimesh.util.concatenate(plate).export(f"liftoff/{side}_ledges_all_6_PRINT.stl")
        print(side, "wall", ww.is_watertight, len(ww.split()), np.round(ww.extents, 1), round(ww.volume), "| ledges", [l.is_watertight and len(l.split()) == 1 for l in ll])
    pair = [w] + ls + [mirror(m, LEFT_DY) for m in [w] + ls]
    trimesh.util.concatenate(pair).export("liftoff/pair_assembled_demo.stl")
