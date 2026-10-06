"""PITLANE fused rack: the user's 6-ledge rack (fused/reference/rack_6ledge_130_3mmholes.stl) turned into a working
wall-mounted hinge rack that prints as ONE piece. Wall spine + hinge knuckles + pins are one solid; every ledge turns on a
print-in-place 5 mm pin (0.4-0.5 mm gaps), so nothing can fall off. Ledge bodies are taken from the reference STL itself.
python3 build_fused.py -> fused/pitlane_fused_rack.stl (same frame as the reference: x right, y up, z out of the wall)
                          fused/pitlane_fused_rack_PRINT.stl (print orientation: the spine's left side face on the bed)
Units mm."""
import os, sys
import numpy as np, trimesh
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "legacy"))
from build_simple import box, cylz, cyly, union, diff, inter, hull, prism_z

REF = "fused/reference/rack_6ledge_130_3mmholes.stl"
H, W = 449.0, 130.0                       # overall height / width (as the reference)
spine_w, spine_t = 14.0, 6.0              # spine 14 x 6 (as the reference)
holes = [(7.0, 28.0), (7.0, 138.0), (7.0, 303.0)]; hole_d = 3.0
n, pitch, led_h = 6, 55.0, 22.0           # 6 ledges, 55 mm apart, 22 mm tall (as the reference)
step = 4.6                                # each ledge 4.6 mm further out (as the reference)
DZ = 2.7                                  # all ledges moved 2.7 mm forward so the bottom ledge's hinge barrel clears the wall
ax_x, bar_r = 6.7, 6.7                    # hinge axis x and barrel radius (as the reference barrel)
pin_r, hole_r = 2.5, 2.9                  # 5 mm pin, 0.4 mm radial gap (print-in-place)
gap = 0.5                                 # axial gap knuckle / barrel
kn_h = 4.0                                # knuckle height (bottom and top of each ledge band)
cr_r = bar_r + 0.4                        # cradle cut in the spine / stand-off around each barrel
so_w = 17.0                               # stand-off width (x) behind each ledge: 0 degree stop
ch = 6.0                                  # 45 deg chamfer on the inner top edge of both front corner posts
flat = 0.6                                # flat on the barrel bottom (sits on the bed when printed side-down)
tab = 1.2                                 # snap-off print tabs (hold each ledge upright while printing; break on first swing)

def yb(j): return pitch * j
def front_ref(j): return 3.7 + step * j            # front face of the rear wall (reference)
def rear_ref(j): return 0.0 if j == 0 else 1.3 + step * j   # back face of the rear wall (reference)
def zc(j): return front_ref(j) + 0.78 + DZ          # hinge axis z (reference barrel centre + DZ)

def wall():
    parts = [box(0, spine_w, 0, H, 0, spine_t)]
    for j in range(n):
        y0 = yb(j); z = zc(j)
        if j:
            parts.append(box(0, so_w, y0, y0 + led_h, 0, rear_ref(j) + DZ - 0.4))          # stand-off, 0.4 mm behind the ledge
        for ya, yz in ((y0, y0 + kn_h), (y0 + led_h - kn_h, y0 + led_h)):                  # knuckles (bottom + top)
            parts += [cyly(ax_x, z, ya, yz, bar_r, 64), box(ax_x - bar_r, ax_x + bar_r, ya, yz, 0, z)]
        parts.append(cyly(ax_x, z, y0, y0 + led_h, pin_r, 48))                              # pin, fused to both knuckles
    w = union(parts)
    cuts = [cylz(x, y, -1, 50, hole_d / 2, 32) for x, y in holes]
    for j in range(n):                                                                   # cradle for the turning barrel
        cuts.append(cyly(ax_x, zc(j), yb(j) + kn_h, yb(j) + led_h - kn_h, cr_r, 72))
    w = diff(w, cuts)
    return union([w] + [cyly(ax_x, zc(j), yb(j), yb(j) + led_h, pin_r, 48) for j in range(n)])

def teardrop_hole(j, y0, y1):                      # hole along y, 45 deg point toward +x (= up when printed side-down)
    z = zc(j); pts = [(ax_x + hole_r * np.cos(a), z + hole_r * np.sin(a)) for a in np.linspace(0, 2 * np.pi, 40, endpoint=False)]
    pts += [(ax_x + hole_r * np.sqrt(2), z)]
    return hull([(x, y, zz) for y in (y0, y1) for x, zz in pts])

def ledge(j, ref):
    y0 = yb(j)
    body = inter([ref, box(11.5, W + 1, y0 - 0.01, y0 + led_h + 0.01, rear_ref(j) - 0.01, 60)])
    body.apply_translation([0, 0, DZ])
    zf = front_ref(j) + DZ                                                                  # chamfers on the front corner posts
    cham = []
    for x_in, sgn in ((30.5, -1), (121.0, 1)):                                             # left post inner edge, right post inner edge
        tri = [(x_in, y0 + 4.0), (x_in + sgn * ch, y0 + 4.0 + ch), (x_in + sgn * ch, y0 + 30), (x_in - sgn * 0.01, y0 + 30), (x_in - sgn * 0.01, y0 + 4.0)]
        cham.append(prism_z(tri, zf + 1.0, zf + 8.0))
    barrel = cyly(ax_x, zc(j), y0 + kn_h + gap, y0 + led_h - kn_h - gap, bar_r, 72)
    clear = [box(-1, spine_w + 0.4, y0 - 1, y0 + led_h + 1, -1, spine_t + 0.4)]                # spine (+0.4)
    if j: clear.append(box(-1, so_w + 0.4, y0 - 1, y0 + led_h + 1, -1, rear_ref(j) + DZ))     # stand-off (0.4 gap already)
    for ya, yz in ((y0 - 1, y0 + kn_h + gap), (y0 + led_h - kn_h - gap, y0 + led_h + 1)):    # knuckles (+0.5)
        clear += [cyly(ax_x, zc(j), ya, yz, bar_r + gap, 72), box(ax_x - bar_r - gap, ax_x + bar_r + gap, ya, yz, -1, zc(j))]
    barrel = diff(barrel, [box(-5, flat, y0 - 1, y0 + led_h + 1, -1, 60)])
    l = diff(union([body, barrel]), clear + cham + [teardrop_hole(j, y0 - 1, y0 + led_h + 1)])
    return l

def tabs(j):                                       # 2 snap-off tabs bridging the 0.4 mm gap to the wall piece
    y0 = yb(j); out = []
    for y in (y0 + 1.5, y0 + led_h - 1.5 - tab):
        if j: out.append(box(15.0, 15.0 + tab, y, y + tab, rear_ref(j) + DZ - 0.45, rear_ref(j) + DZ + 0.05))
        else: out.append(box(spine_w - 0.05, spine_w + 0.45, y, y + tab, 3.5, 3.5 + tab))
    return out

def build():
    ref = trimesh.load(REF)
    w = wall(); ls = [ledge(j, ref) for j in range(n)]
    return w, ls

if __name__ == "__main__":
    w, ls = build()
    allp = union([w] + ls + sum([tabs(j) for j in range(n)], []))            # one printable body (tabs tie the ledges on)
    os.makedirs("fused", exist_ok=True)
    allp.export("fused/pitlane_fused_rack.stl")
    pr = allp.copy(); pr.apply_transform(trimesh.transformations.rotation_matrix(-np.pi / 2, [0, 1, 0])); pr.apply_translation(-pr.bounds[0])
    pr.export("fused/pitlane_fused_rack_PRINT.stl")
    print("wall watertight", w.is_watertight, "ledges", [l.is_watertight for l in ls], "print body watertight", allp.is_watertight, "bodies", len(allp.split()), "size", np.round(allp.extents, 1))
