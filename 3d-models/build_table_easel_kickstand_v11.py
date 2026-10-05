"""Kickstand easel v11 (v10 with a wider leg strip): card panel + a lift-off hinge (after LiftOffHinge.stl) + a separate solid leg strip.
The panel carries the lower half of the hinge (10 mm barrel on a 5 mm pin); the leg carries the upper half
(10 mm barrel, 5.5 mm hole) and simply slides onto the pin, so the hinge can never fuse.
Two positions only: 0 deg (folded flat) and 35 deg (a stop tab on the leg barrel lands on the panel back).
Rack frame: x width, y up the panel, z out of the card face. The panel prints on its side (x up, stop wall
down); the leg prints standing on its barrel end; the pin prints standing on its head."""
import os, json, numpy as np, trimesh, manifold3d as mf, shapely.geometry as sg
from scipy.optimize import brentq
from trimesh.creation import box, cylinder
from trimesh.transformations import rotation_matrix as RM
SRC = os.environ.get('KS_STANDS', 'build_table_stands.py')
src = open(SRC).read().split('CONFIG = {')[0]; ns = {}; exec(src, ns)
U = lambda *m: trimesh.boolean.union(list(m), engine='manifold')
D = lambda a, *b: trimesh.boolean.difference([a, U(*b)], engine='manifold')
I = lambda a, b: trimesh.boolean.intersection([a, b], engine='manifold').volume
N = int(os.environ.get('KS_N', 3)); YH = float(os.environ.get('KS_YH', 90)); ALPHA = float(os.environ.get('KS_ALPHA', 26.5))
LP = max((N - 1)*55.0 + 22.0, 170.0); ns['N'], ns['LP'] = N, LP; TAG = f'{N}card'
X0, X1 = ns['X0'], ns['X1']
# --- lift-off hinge, dimensions as in LiftOffHinge.stl ---
R_BAR, R_PIN, R_HOLE, L_BAR = 5.0, 2.5, 2.75, 15.0       # 10 mm barrels, 5 mm pin, 5.5 mm hole, 15 mm barrels
GAP = 0.4                                                  # barrels / leg to panel back
H = dict(y=YH, z=-3.0 - GAP - R_BAR)
PB = float(os.environ.get('KS_PB', 8.0)); LB = float(os.environ.get('KS_LB', 24.0))   # panel / leg barrel lengths
XS = (X0, X0 + PB)                                         # stopper barrel (stop-wall end, on the bed)
XL = (XS[1] + 0.3, XS[1] + 0.3 + LB)                       # leg barrel
XP = (XL[1] + 0.3, XL[1] + 0.3 + PB)                       # main panel barrel
LW = float(os.environ.get('KS_LW', 80.0))
LEG_X = (X0, X0 + LW)                                      # solid strip, flush with the stop-wall end
L_Z = (-3.0 - GAP - 4.0, -3.0 - GAP); FOOT_R = 2.0         # 4 mm strip, 0.4 mm behind the panel back when folded
ZM = (L_Z[0] + L_Z[1])/2
PSI = 35.0
HEAD = (4.5, 2.5)                                          # pin head radius / thickness (sits outside the stopper barrel)
BARB = dict(r=3.2, len=0.6, cone=2.5, slot=1.6, slot_len=9.0)

def xcyl(r, y, z, xa, xb, sec=96):
    c = cylinder(radius=r, height=xb - xa, sections=sec)
    c.apply_transform(RM(np.pi/2, [0, 1, 0])); c.apply_translation([(xa + xb)/2, y, z]); return c

def xrev(prof):   # revolve an (r, x) profile about the hinge axis
    m = trimesh.creation.revolve(np.array(prof), sections=96)
    m.apply_transform(RM(np.pi/2, [0, 1, 0])); m.apply_translation([0, H['y'], H['z']])
    if m.volume < 0: m.invert()
    return m

rot = lambda deg: RM(np.radians(deg), [1, 0, 0], point=[0, H['y'], H['z']])
apply = lambda M, p: (M @ np.append(p, 1))[:3]

def tilt(alpha, panel):
    a = np.radians(alpha); s, c = np.sin(a), np.cos(a)
    T = np.array([[1, 0, 0, 0], [0, s, -c, 0], [0, c, s, 0], [0, 0, 0, 1]], float)
    v = trimesh.transform_points(panel.vertices, T)
    T[2, 3] -= v[:, 2].min(); T[1, 3] -= v[v[:, 2] < v[:, 2].min() + 0.3][:, 1].min(); return T

def foot_y(T):
    f = lambda yf: apply(T @ rot(PSI), np.array([LEG_X[0] + 20, yf, ZM]))[2] - FOOT_R
    return brentq(f, 2.0, YH - 10)

def clean(m, tol=1e-3):
    M = mf.Manifold(mf.Mesh(vert_properties=np.asarray(m.vertices, np.float32), tri_verts=np.asarray(m.faces, np.uint32))).simplify(tol)
    me = M.to_mesh(); return trimesh.Trimesh(np.asarray(me.vert_properties)[:, :3], np.asarray(me.tri_verts), process=True)

def barrel_with_web(xa, xb, cone_under):
    b = U(xcyl(R_BAR, H['y'], H['z'], xa, xb), box(bounds=[[xa, H['y'] - 4, H['z']], [xb, H['y'] + 4, -2.9]]))
    if cone_under:   # 45-deg underside (as printed on its side) instead of a flat overhang
        b = trimesh.boolean.intersection([b, xrev([(0, xa), (R_HOLE, xa), (R_HOLE + 40, xa + 40), (0, xa + 40), (0, xa)])], engine='manifold')
    return b

def make_pin():
    """headed 5 mm pin with a split, barbed tip that snaps out past the main barrel"""
    xt = XP[1] + 0.2                                             # barb's flat back face just outside the barrel
    prof = [(0, XS[0] - HEAD[1]), (HEAD[0], XS[0] - HEAD[1]), (HEAD[0], XS[0] - 0.2), (R_PIN, XS[0] - 0.2),
            (R_PIN, xt), (BARB['r'], xt), (BARB['r'], xt + BARB['len']), (R_PIN - 0.4, xt + BARB['len'] + BARB['cone']),
            (0, xt + BARB['len'] + BARB['cone'])]
    pin = xrev(prof)
    xe = xt + BARB['len'] + BARB['cone']
    slot = box(bounds=[[xe - BARB['slot_len'], H['y'] - 5, H['z'] - BARB['slot']/2], [xe + 1, H['y'] + 5, H['z'] + BARB['slot']/2]])
    return D(pin, slot)

def build(yf):
    panel = ns['face']()
    holes = xcyl(R_HOLE, H['y'], H['z'], X0 - 1, XP[1] + 1)
    panel = D(U(panel, barrel_with_web(*XS, False), barrel_with_web(*XP, True)), holes)
    # leg: solid strip + barrel + stop tab + rounded foot
    leg = box(bounds=[[LEG_X[0], yf, L_Z[0]], [LEG_X[1], H['y'], L_Z[1]]])
    leg = U(leg, xcyl(FOOT_R, yf, ZM, *LEG_X))
    clear = lambda xa, xb: box(bounds=[[xa, H['y'] - R_BAR - 0.6, -30], [xb, H['y'] + 30, 5]])
    leg = D(leg, clear(LEG_X[0] - 1, XL[0]), clear(XL[1], LEG_X[1] + 1))       # clear of both panel barrels
    tab = box(bounds=[[XL[0], H['y'], -3.0 - 5.0], [XL[1], H['y'] + R_BAR + 4, -3.0]])
    tab.apply_transform(rot(-PSI))                                   # lands flat on the panel back at PSI
    # the leg prints standing on its stop-wall end: everything above the strip's notch (barrel, tab and the
    # strip next to the barrel) starts with a 45-deg cone underside instead of a flat overhang
    x0, yn = XL[0], H['y'] - R_BAR - 0.6
    upper = box(bounds=[[x0 - 1, yn, -30], [LEG_X[1] + 1, H['y'] + 30, 5]])
    top = U(xcyl(R_BAR, H['y'], H['z'], *XL), tab, trimesh.boolean.intersection([leg, upper], engine='manifold'))
    top = trimesh.boolean.intersection([top, xrev([(0, x0), (R_HOLE, x0), (R_HOLE + 40, x0 + 40), (0, x0 + 40), (0, x0)])], engine='manifold')
    leg = U(D(leg, upper), top)
    leg = D(leg, xcyl(R_HOLE, H['y'], H['z'], XL[0] - 1, XL[1] + 1))
    return clean(panel), clean(leg), clean(make_pin())

def stop_angle(panel, leg, lo=0.5, hi=60.0):
    hit = lambda a: I(trimesh.Trimesh(trimesh.transform_points(leg.vertices, rot(a)), leg.faces), panel) > 0.05
    if not hit(hi): return None
    for _ in range(24):
        mid = (lo + hi)/2; lo, hi = (lo, mid) if hit(mid) else (mid, hi)
    return hi

if __name__ == '__main__':
    P0 = ns['face'](); T = tilt(ALPHA, P0); yf = foot_y(T)
    panel, leg, pin = build(yf); s = stop_angle(U(panel, pin), leg)
    print(f'{TAG}: hinge y={YH}, lean {ALPHA}, foot y={yf:.2f}, stop at {s:.2f} deg')
    for nme, m in [('panel', panel), ('leg', leg), ('pin', pin)]:
        print(nme, m.is_watertight, len(m.split()), np.round(m.bounds, 1).tolist()); m.export(f'_ks11_{TAG}_{nme}.stl')
    # print-ready: panel on its stop wall (x up); leg on its barrel end (x up); pin standing on its head (x up)
    p = panel.copy(); p.apply_translation([-X0, 0, 0]); p.export(f'table_kickstand_{TAG}_v11_panel.stl')
    l = leg.copy(); l.apply_translation(-l.bounds[0]); l.export(f'table_kickstand_{TAG}_v11_leg.stl')
    q = pin.copy(); q.apply_translation(-q.bounds[0]); q.export(f'table_kickstand_{TAG}_v11_pin.stl')
    json.dump(dict(N=N, YH=YH, alpha=ALPHA, psi=PSI, stop=s, foot_y=yf), open(f'_ks11_{TAG}.json', 'w'))
