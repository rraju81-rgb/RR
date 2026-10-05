# Usage: KS_N=3 KS_YH=90 KS_ALPHA=26.5 python3 build_table_easel_kickstand_v6.py   |   KS_N=5 KS_YH=140 KS_ALPHA=25 ...
# Uses the tier/face geometry from build_table_stands.py in the same folder.
"""Kickstand easel v6: card panel + ONE small centred print-in-place hinge + an A-frame kickstand that folds down.
No base plate. The hinge has two positions, 0 (flat) and 35 deg (a stop tab on the leg lands on the panel back).
Rack frame (as printed, folded): x width, y up the panel, z out of the card face. Prints on its side (x up)."""
import os, json, numpy as np, trimesh, manifold3d as mf, shapely.geometry as sg
from scipy.optimize import brentq
from trimesh.creation import box, cylinder
from trimesh.transformations import rotation_matrix as RM
src = open('build_table_stands.py').read().split('CONFIG = {')[0]; ns = {}; exec(src, ns)
U = lambda *m: trimesh.boolean.union(list(m), engine='manifold')
D = lambda a, *b: trimesh.boolean.difference([a, U(*b)], engine='manifold')
I = lambda a, b: trimesh.boolean.intersection([a, b], engine='manifold').volume
N = int(os.environ.get('KS_N', 3)); YH = float(os.environ.get('KS_YH', 80)); ALPHA = float(os.environ.get('KS_ALPHA', 20))
LP = max((N - 1)*55.0 + 22.0, 170.0); ns['N'], ns['LP'] = N, LP; TAG = f'{N}card'
X0, X1 = ns['X0'], ns['X1']; XC = (X0 + X1)/2
GN = 0.5; GA = GN*np.sqrt(2)
H = dict(y=YH, z=-7.5, R=4.0, pin=1.75)       # small hinge: 8 mm knuckles, 3.5 mm pin, axis set back so the panel is not cut
HX = (XC - 18, XC + 18)                        # 36 mm wide, 3 knuckles (panel - leg - panel)
L_Z = (-6.5, -3.5); L_Y0 = 2.0; FOOT_R = 1.5   # leg folded flat 0.5 mm behind the panel back
FOOT = np.array([XC, 0.0, -5.0])   # foot centre z; its y is solved per stand

def xcyl(r, y, z, xa, xb, sec=64):
    c = cylinder(radius=r, height=xb - xa, sections=sec)
    c.apply_transform(RM(np.pi/2, [0, 1, 0])); c.apply_translation([(xa + xb)/2, y, z]); return c

def _knuckle(xs, k, r_in, r_out, grow=0.0):
    R, n = H['R'], len(xs) - 1
    hb = lambda r: (xs[0] - (GN if grow else 0)) if k == 0 else xs[k] + (R - r) + (0 if grow else GA)
    ht = lambda r: (xs[n] + (GN if grow else 0)) if k == n - 1 else xs[k + 1] + (R - r) + (GA if grow else 0)
    ro = min(r_out, R + 5)
    prof = [(r_in, hb(r_in)), (r_out, hb(ro)), (r_out, ht(ro)), (r_in, ht(r_in)), (r_in, hb(r_in))]
    m = trimesh.creation.revolve(np.array(prof), sections=96)
    m.apply_transform(RM(np.pi/2, [0, 1, 0])); m.apply_translation([0, H['y'], H['z']])
    if m.volume < 0: m.invert()
    return m

def hinge(fixed, mover, xa, xb, nseg=3, webs=()):
    xs = np.linspace(xa, xb, nseg + 1); R, rp = H['R'], H['pin']; rb = rp + GN
    fk, mk, fenv, menv = [], [], [], []
    for k in range(nseg):
        if k % 2 == 0:
            fk += [_knuckle(xs, k, rb, R), _knuckle(xs, k, 1.0, rb + 0.05)]; fenv.append(_knuckle(xs, k, 1.0, R + GN, grow=1))
        else:
            mk.append(_knuckle(xs, k, rb, R)); menv.append(_knuckle(xs, k, 1.0, R + GN, grow=1))
    fixed = U(D(U(fixed, *webs), *menv), *fk, xcyl(rp, H['y'], H['z'], xa + 0.6, xb - 0.6))
    mover = D(U(D(mover, *fenv), *mk), xcyl(rb, H['y'], H['z'], xa - 1, xb + 1))
    return fixed, mover

def rot(deg):   # leg rotation about the hinge axis; + swings the foot away from the panel
    return RM(np.radians(deg), [1, 0, 0], point=[0, H['y'], H['z']])
apply = lambda M, p: (M @ np.append(p, 1))[:3]

def tilt(alpha, panel):
    """rack -> world: panel leaning back by alpha, its lowest point on the table (Z=0), front contact at Y=0"""
    a = np.radians(alpha); s, c = np.sin(a), np.cos(a)
    T = np.array([[1, 0, 0, 0], [0, s, -c, 0], [0, c, s, 0], [0, 0, 0, 1]], float)
    v = trimesh.transform_points(panel.vertices, T)
    T[2, 3] -= v[:, 2].min(); T[1, 3] -= v[v[:, 2] < v[:, 2].min() + 0.3][:, 1].min(); return T

def open_angle(T):   # leg rotation that puts the foot (bottom of the foot cylinder) on the table
    f = lambda psi: apply(T @ rot(psi), FOOT)[2] - FOOT_R
    return brentq(f, 1, 170)

def clean(m, tol=1e-3):
    M = mf.Manifold(mf.Mesh(vert_properties=np.asarray(m.vertices, np.float32), tri_verts=np.asarray(m.faces, np.uint32))).simplify(tol)
    me = M.to_mesh(); return trimesh.Trimesh(np.asarray(me.vert_properties)[:, :3], np.asarray(me.tri_verts), process=True)

PSI = 35.0                                     # the only two hinge positions: 0 (flat) and PSI (open, hard stop)
XS = np.linspace(*HX, 4)                       # 3 equal knuckles: panel | leg | panel  (symmetric)

def foot_y(T):
    """foot centre height on the leg that puts the foot on the table when the leg is open PSI"""
    f = lambda yf: apply(T @ rot(PSI), np.array([XC, yf, FOOT[2]]))[2] - FOOT_R
    return brentq(f, 2.0, YH - 10)

W_STRUT = 8.0
def halfplane(a, b, below=True, big=1000):
    """region y <= a*x + b (below) or y >= a*x + b, clipped to a big box"""
    xs = np.array([-big, big]); ys = a*xs + b
    return sg.Polygon([(xs[0], ys[0]), (xs[1], ys[1]), (big, -1e5 if below else 1e5), (-big, -1e5 if below else 1e5)])

def leg_outline(yf):
    """A-frame kickstand: full width at the foot, 45-deg sides up to the middle knuckle.
    Every edge is either along y or at 45 deg, so the leg prints on its side (x up) without support."""
    w, r2 = W_STRUT, W_STRUT*np.sqrt(2)
    c_out, d_out = YH - (XS[1] + GA), YH + (XS[2] - GA)          # outer struts: y = x + c_out, y = -x + d_out
    yb = YH - (XS[1] + GA - X0)
    outer = sg.Polygon([(X0, yf), (X1, yf), (X1, d_out - X1), (XS[2] - GA, YH), (XS[1] + GA, YH), (X0, yb)])
    c_in, d_in, ytop = c_out - r2, d_out - r2, YH - H['R'] - 10
    inner = halfplane(1, c_in).intersection(halfplane(-1, d_in)).intersection(sg.box(X0 + w, yf + w, X1 - w, ytop))
    c1, d1 = yf - X0, yf + X1                                       # hole 1: triangle on the foot bar
    holes = [inner.intersection(halfplane(1, c1)).intersection(halfplane(-1, d1))]
    y2 = (c1 + d1)/2 + w
    if y2 + 10 < ytop:                                              # tall (5-card) leg: a crossbar and a second opening, like a letter A
        holes.append(inner.intersection(sg.box(-1e3, y2, 1e3, 1e3)))
    holes = [h for h in holes if h.area > 60]
    from shapely.ops import unary_union
    return (outer.difference(unary_union(holes)) if holes else outer).simplify(0.01).buffer(0)

def build(yf):
    panel = ns['face']()
    poly = leg_outline(yf)
    leg = trimesh.creation.extrude_polygon(poly, L_Z[1] - L_Z[0]); leg.apply_translation([0, 0, L_Z[0]])
    leg = U(leg, xcyl(FOOT_R, yf, FOOT[2], X0, X1))                 # full-width rounded foot
    # the leg stays clear of the two panel knuckles' webs (it is carried by the middle knuckle)
    leg = D(leg, box(bounds=[[X0 - 1, H['y'] - GN, -20], [XS[1] + GA, H['y'] + 20, 0]]),
                 box(bounds=[[XS[2] - GA, H['y'] - GN, -20], [X1 + 1, H['y'] + 20, 0]]))
    # stop tab on the middle knuckle: modelled in the OPEN pose with its face flat on the panel back,
    # then rotated back to the printed (flat) pose -> it lands face-to-face on the panel exactly at PSI.
    # Its underside (low-x side, as printed) is a 45-deg cone continuing the knuckle's cone joint.
    tab = box(bounds=[[XS[1], H['y'], -3.0 - 4.0], [XS[2] + 0.3, H['y'] + H['R'] + 5, -3.0]])
    tab.apply_transform(rot(-PSI))
    x0 = XS[1] + GA
    cone = trimesh.creation.revolve(np.array([(0, x0), (H['R'], x0), (H['R'] + 30, x0 + 30), (0, x0 + 30), (0, x0)]), sections=96)
    cone.apply_transform(RM(np.pi/2, [0, 1, 0])); cone.apply_translation([0, H['y'], H['z']])
    if cone.volume < 0: cone.invert()
    tab = trimesh.boolean.intersection([tab, cone], engine='manifold')
    leg = U(leg, tab)
    webs = [box(bounds=[[XS[0], H['y'], H['z']], [XS[1] - 1.0, H['y'] + 3, -2.9]]),
            box(bounds=[[XS[2] + 1.0, H['y'], H['z']], [XS[3], H['y'] + 3, -2.9]])]
    panel, leg = hinge(panel, leg, *HX, nseg=3, webs=webs)
    return clean(panel), clean(leg)

def stop_angle(panel, leg, lo=1.0, hi=175.0):
    """first leg rotation at which the leg touches the panel (the stop)"""
    hit = lambda a: I(trimesh.Trimesh(trimesh.transform_points(leg.vertices, rot(a)), leg.faces), panel) > 0.05
    if not hit(hi): return None
    for _ in range(24):
        mid = (lo + hi)/2
        lo, hi = (lo, mid) if hit(mid) else (mid, hi)
    return hi

if __name__ == '__main__':
    P0 = ns['face'](); T = tilt(ALPHA, P0); yf = foot_y(T)
    print(f'{TAG}: hinge y={YH}, lean {ALPHA} deg, leg open {PSI} deg -> foot centre y={yf:.2f}')
    panel, leg = build(yf); s = stop_angle(panel, leg, 0.5, 60.0)
    print(f'first contact leg/panel at {s:.2f} deg (target {PSI})')
    for nme, m in [('panel', panel), ('leg', leg)]:
        print(nme, m.is_watertight, len(m.split()), np.round(m.bounds, 1).tolist()); m.export(f'_ks_{TAG}_{nme}.stl')
    allm = trimesh.util.concatenate([panel, leg]); allm.apply_translation([-X0, 0, 0]); allm.export(f'table_kickstand_{TAG}_v6.stl')
    json.dump(dict(N=N, YH=YH, alpha=ALPHA, psi=PSI, stop=s, foot_y=yf), open(f'_ks_{TAG}.json', 'w'))
