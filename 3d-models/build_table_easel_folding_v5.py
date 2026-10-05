"""Folding easel v5 (40 mm leg strip, cone-jointed 0.5 mm hinges), 3 or 5 cards: card panel + base (bottom hinge) + back leg (top hinge), print-in-place.
Rack frame (as printed, folded): x width, y up the panel, z out of the card face. Prints on its side (x up)."""
import trimesh, numpy as np, json
from scipy.optimize import brentq
from trimesh.creation import box, cylinder
from trimesh.transformations import rotation_matrix as RM
src = open('table_stands.py').read().split('CONFIG = {')[0]; ns = {}; exec(src, ns)
U = lambda *m: trimesh.boolean.union([x for x in m], engine='manifold')
D = lambda a, *b: trimesh.boolean.difference([a, U(*b)], engine='manifold')
import sys, os
N = int(os.environ.get('EASEL_N', 3)); YH = float(os.environ.get('EASEL_YH', 125)); BASE_END = float(os.environ.get('EASEL_BASE_END', 117))
LP = max((N - 1)*55.0 + 22.0, 170.0)      # panel covers the bottom card's full 165 mm
TAGN = f'{N}card'
ns['N'], ns['LP'] = N, LP
X0, X1, G = ns['X0'], ns['X1'], 0.4
# hinge 1 (panel <-> base, bottom) and hinge 2 (panel <-> leg, top)
H1 = dict(y=3.5, z=-3.75, R=3.75, pin=1.6)      # base hinge, full width
H2 = dict(y=YH, z=-9.5, R=6.0, pin=2.5)     # leg hinge: only under the 40 mm leg strip; pin 5 mm (v4: 4 mm)
LEG_W = 40.0                              # back leg narrowed from the full 119 mm to a 40 mm strip at the stop-wall end
B_Z = (-7.5, -3.5); B_Y1 = BASE_END        # base plate, folded behind the panel (40 mm shorter than v3)
L_Z = (-11.5, -8.5); L_Y0 = 2.0           # leg, folded behind the base
FOOT_R, GROOVE_R = 1.5, 2.0
SEG = np.linspace(X0, X1, 8)              # 7 knuckle segments; panel owns 0,2,4,6 (both ends), mover owns 1,3,5

def xcyl(r, y, z, xa, xb, sec=64):
    c = cylinder(radius=r, height=xb - xa, sections=sec)
    c.apply_transform(RM(np.pi/2, [0, 1, 0])); c.apply_translation([(xa + xb)/2, y, z]); return c

GN = 0.5                                  # normal clearance on every hinge surface (v4: 0.4 mm flat gaps)
GA = GN*np.sqrt(2)                        # the same clearance measured along the axis on a 45-deg joint

def _knuckle(H, xs, k, r_in, r_out, grow=0.0):
    """knuckle k between interfaces xs[k], xs[k+1] (axis along x). Interior joints are 45-deg cones:
    the lower knuckle ends in a convex cone, the upper one starts with the matching concave cone GA higher.
    grow > 0 gives the clearance envelope (all surfaces pushed out by GN)."""
    R, n = H['R'], len(xs) - 1
    def hb(r):   # bottom surface height at radius r
        if k == 0: return xs[0] - (GN if grow else 0)
        return xs[k] + (R - r) + (0 if grow else GA)
    def ht(r):   # top surface height at radius r
        if k == n - 1: return xs[n] + (GN if grow else 0)
        return xs[k + 1] + (R - r) + (GA if grow else 0)
    prof = [(r_in, hb(r_in)), (r_out, hb(min(r_out, R + 5))), (r_out, ht(min(r_out, R + 5))), (r_in, ht(r_in)), (r_in, hb(r_in))]
    m = trimesh.creation.revolve(np.array(prof), sections=96)
    m.apply_transform(RM(np.pi/2, [0, 1, 0])); m.apply_translation([0, H['y'], H['z']])
    if m.volume < 0: m.invert()
    return m

def hinge(fixed, mover, H, xa=None, xb=None, nseg=7, webs=None):
    """print-in-place hinge over x = xa..xb with nseg alternating knuckles (fixed owns the even ones, incl. both ends).
    Pin (radius H['pin']) belongs to `fixed`; `mover` knuckles have a bore with GN clearance."""
    xa = X0 if xa is None else xa; xb = X1 if xb is None else xb
    xs = np.linspace(xa, xb, nseg + 1); R, rp = H['R'], H['pin']; rb = rp + GN
    fk, mk, fenv, menv = [], [], [], []
    for k in range(nseg):
        if k % 2 == 0:
            fk.append(_knuckle(H, xs, k, rb, R)); fk.append(_knuckle(H, xs, k, 1.0, rb + 0.05))        # solid to the pin (r<1 is inside the pin)
            fenv.append(_knuckle(H, xs, k, 1.0, R + GN, grow=1))
        else:
            mk.append(_knuckle(H, xs, k, rb, R)); menv.append(_knuckle(H, xs, k, 1.0, R + GN, grow=1))
    if webs is not None: fixed = U(fixed, *webs)
    fixed = U(D(fixed, *menv), *fk, xcyl(rp, H['y'], H['z'], xa + 0.6, xb - 0.6))
    mover = D(U(D(mover, *fenv), *mk), xcyl(rb, H['y'], H['z'], xa - 1, xb + 1))
    return fixed, mover

def rot(H, deg):   # rotation about a hinge axis (x), +deg turns +y towards +z
    return RM(np.radians(deg), [1, 0, 0], point=[0, H['y'], H['z']])

def tilt(alpha_deg):   # rack -> world (Y back, Z up), panel leaning back by alpha, hinge 1 at Y=0, Z=3.75
    a = np.radians(alpha_deg); s, c = np.sin(a), np.cos(a)
    T = np.array([[1,0,0,0],[0,s,-c,0],[0,c,s,0],[0,0,0,1]], float)
    h = T @ [0, H1['y'], H1['z'], 1]
    T[1, 3] -= h[1]; T[2, 3] += 3.75 - h[2]; return T

apply = lambda M, p: (M @ np.append(p, 1))[:3]
FOOT = np.array([0, L_Y0, (L_Z[0] + L_Z[1])/2])

def base_angle(alpha):   # base rotation that lays it flat behind the panel
    f = lambda phi: apply(tilt(alpha) @ rot(H1, -phi), [0, H1['y'] + 100, H1['z']])[2] - 3.75
    return brentq(f, 1, 179)
def leg_angle(alpha):    # leg rotation that puts the foot centre 0.5 mm below the base top, behind the plumb line
    T = tilt(alpha)
    fz = lambda psi: apply(T @ rot(H2, psi), FOOT)[2] - 3.5
    plumb = alpha                                   # leg vertical when rotated by alpha
    if fz(plumb) > 0: return None, None
    psi = brentq(fz, plumb, 170)
    return psi, apply(T @ rot(H2, psi), FOOT)[1]

if __name__ == '__main__':
    # ---- design: which display angles fit on the base ----
    LB = B_Y1 - H1['y']
    grooves = []
    for alpha in [float(a) for a in os.environ.get('EASEL_ANGLES', '12.5,15,17.5,20').split(',')]:   # 4 settings, each >= 18 deg forward tip when loaded
        psi, fy = leg_angle(alpha)
        if psi is None: continue
        s = fy                                          # distance behind hinge 1 = distance along the base
        ok = 10 < s < LB - 5 and all(abs(s - g[1]) >= 6 for g in grooves)
        print(f'alpha {alpha:4.1f} deg: base rot {base_angle(alpha):5.1f}, leg rot {psi:5.1f}, foot {s:6.1f} mm behind hinge  {"-> groove" if ok else "skip"}')
        if ok: grooves.append((alpha, s))
    json.dump(grooves, open(f'_easel5_grooves_{TAGN}.json', 'w'))
    assert len(grooves) == len(os.environ.get('EASEL_ANGLES', '12.5,15,17.5,20').split(',')), f'only {len(grooves)} grooves fit'

    # ---- bodies (folded, as printed) ----
    panel = ns['face']()
    base = box(bounds=[[X0, H1['y'], B_Z[0]], [X1, B_Y1, B_Z[1]]])
    base = D(base, *[xcyl(GROOVE_R, H1['y'] + s, B_Z[1], X0 - 1, X1 + 1) for _, s in grooves])
    XL1 = X0 + LEG_W
    leg_plate = box(bounds=[[X0, L_Y0, L_Z[0]], [XL1, H2['y'], L_Z[1]]])
    # edge rails on the leg's back face (thin web, thick edges), 45-deg inner chamfer for the side print
    import shapely.geometry as sg
    rz0, rz1, RW, RH = L_Z[0], L_Z[0] - 5.0, 8.0, 5.0
    ry0, ry1 = L_Y0 + 12.0, H2['y'] - 11.0
    rails = []
    for poly in [[(X0, rz0), (X0, rz1), (X0 + RW, rz1), (X0 + RW + RH, rz0)], [(XL1, rz0), (XL1, rz1), (XL1 - RW, rz1), (XL1 - RW - RH, rz0)]]:
        m = trimesh.creation.extrude_polygon(sg.Polygon(poly), ry1 - ry0)        # (x, z) polygon, length along y
        m.apply_transform(np.array([[1, 0, 0, 0], [0, 0, 1, ry0], [0, 1, 0, 0], [0, 0, 0, 1]], float))
        if m.volume < 0: m.invert()
        rails.append(m)
    rails += [box(bounds=[[X0, ry0, rz1], [XL1, ry0 + RW, rz0]]), box(bounds=[[X0, ry1 - RW, rz1], [XL1, ry1, rz0]])]
    win = []
    leg = U(leg_plate, *rails, xcyl(FOOT_R, L_Y0, FOOT[2], X0, XL1))
    panel, base = hinge(panel, base, H1, nseg=7)
    webs = [box(bounds=[[X0, H2['y'] - 4, H2['z']], [XL1, H2['y'] + 4, -2.9]])]     # ties the leg hinge to the panel (moving knuckles carved out)
    panel, leg = hinge(panel, leg, H2, X0, XL1, nseg=5, webs=webs)
    import manifold3d as mf
    def clean(m, tol=1e-3):   # drop boolean sliver faces that would collapse when written as 32-bit STL
        M = mf.Manifold(mf.Mesh(vert_properties=np.asarray(m.vertices, np.float32), tri_verts=np.asarray(m.faces, np.uint32))).simplify(tol)
        me = M.to_mesh(); return trimesh.Trimesh(np.asarray(me.vert_properties)[:, :3], np.asarray(me.tri_verts), process=True)
    panel, base, leg = clean(panel), clean(base), clean(leg)
    for nme, m in [('panel', panel), ('base', base), ('leg', leg)]:
        print(nme, m.is_watertight, len(m.split()), np.round(m.bounds, 1).tolist())
        m.export(f'_easel5_{TAGN}_{nme}.stl')
    allm = trimesh.util.concatenate([panel, base, leg]); allm.apply_translation([-X0, 0, 0])
    allm.export(f'table_easel_{TAGN}_folding_v5.stl'); print('folded print size', np.round(allm.extents, 1).tolist())
