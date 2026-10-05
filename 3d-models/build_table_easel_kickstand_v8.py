"""Kickstand easel v8: card panel + a lift-off hinge (after LiftOffHinge.stl) + a separate solid leg strip.
The panel carries the lower half of the hinge (10 mm barrel on a 5 mm pin); the leg carries the upper half
(10 mm barrel, 5.5 mm hole) and simply slides onto the pin, so the hinge can never fuse.
Two positions only: 0 deg (folded flat) and 35 deg (a stop tab on the leg barrel lands on the panel back).
A small cleat at the stop-wall end keeps the folded leg from sliding off the pin.
Rack frame: x width, y up the panel, z out of the card face. The panel prints on its side (x up, stop wall
down); the leg prints standing on its end (x up, barrel on the bed)."""
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
XL = (X0 + 3.0, X0 + 3.0 + L_BAR)                          # leg barrel (lower, nearer the stop wall)
XP = (XL[1] + 0.3, XL[1] + 0.3 + L_BAR)                    # panel barrel (upper); the pin runs down from it to the bed
LEG_X = (XL[0], XL[0] + 40.0)                              # 40 mm solid strip
L_Z = (-3.0 - GAP - 4.0, -3.0 - GAP); FOOT_R = 2.0         # 4 mm strip, 0.4 mm behind the panel back when folded
ZM = (L_Z[0] + L_Z[1])/2
PSI = 35.0
CLEAT = (X0, XL[0] - 0.4)                                  # cleat x range (on the bed, below the leg)

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

def leg_profile(yf, ang):
    """(y, z) outline of the leg strip below the hinge, rotated by ang (for the cleat lock test)"""
    p = sg.box(yf - FOOT_R, L_Z[0], YH - R_BAR - 0.6, L_Z[1])
    a = np.radians(ang); yc, zc = H['y'], H['z']
    from shapely import affinity
    return affinity.rotate(p, ang, origin=(yc, zc))

def cleat_box(yf):
    """cleat on the panel back at the stop-wall end; its top is set so the strip clears it only when the leg is
    fully open (~30-35 deg): folded, the leg can't slide off the pin; fully open, it slides off for printing/storage"""
    zc = (L_Z[0] - 1.0, -3.0)
    def free(ytop, ang):
        return not leg_profile(yf, ang).intersects(sg.box(yf + 5, zc[0], ytop, zc[1]))
    # highest cleat top that still lets the leg out at 33 deg
    ytop = brentq(lambda yt: (1 if free(yt, 33.0) else -1) - 0.5, yf + 10, YH - R_BAR - 1, xtol=0.05)
    ytop -= 0.3
    unlock = brentq(lambda a: (1 if free(ytop, a) else -1) - 0.5, 0.0, 35.0, xtol=0.05)
    return box(bounds=[[CLEAT[0], yf + 5, zc[0]], [CLEAT[1], ytop, zc[1]]]), ytop, unlock

def build(yf):
    panel = ns['face']()
    # panel half of the hinge: barrel + pin running down to the bed + web to the panel back.
    # Barrel and web undersides are 45-deg cones (prints on its side without support).
    x0 = XP[0]
    body = U(xcyl(R_BAR, H['y'], H['z'], XP[0], XP[1]),
             box(bounds=[[XP[0], H['y'] - 4, H['z']], [XP[1], H['y'] + 4, -2.9]]))
    cone = xrev([(0, x0), (R_PIN, x0), (R_PIN + 40, x0 + 40), (0, x0 + 40), (0, x0)])
    body = trimesh.boolean.intersection([body, cone], engine='manifold')
    pin = xcyl(R_PIN, H['y'], H['z'], X0, XP[0] + 1)
    cl, ytop, unlock = cleat_box(yf)
    panel = U(panel, body, pin, cl)
    # leg: solid strip + barrel with the 5.5 mm hole + stop tab + rounded foot
    leg = box(bounds=[[LEG_X[0], yf, L_Z[0]], [LEG_X[1], H['y'], L_Z[1]]])
    leg = U(leg, xcyl(FOOT_R, yf, ZM, *LEG_X))
    leg = D(leg, box(bounds=[[XL[1], H['y'] - R_BAR - 0.6, -30], [LEG_X[1] + 1, H['y'] + 30, 5]]))   # clear of the panel barrel
    tab = box(bounds=[[XL[0], H['y'], -3.0 - 5.0], [XL[1], H['y'] + R_BAR + 4, -3.0]])
    tab.apply_transform(rot(-PSI))                                   # lands flat on the panel back at PSI
    leg = U(leg, xcyl(R_BAR, H['y'], H['z'], *XL), tab)
    leg = D(leg, xcyl(R_HOLE, H['y'], H['z'], XL[0] - 1, XL[1] + 1),
            box(bounds=[[XL[0] - 5, H['y'] - 30, -30], [XL[0], H['y'] + 30, 5]]))   # nothing below the barrel's end
    return clean(panel), clean(leg), dict(cleat_top_y=round(ytop, 2), unlock_deg=round(unlock, 1))

def stop_angle(panel, leg, lo=0.5, hi=60.0):
    hit = lambda a: I(trimesh.Trimesh(trimesh.transform_points(leg.vertices, rot(a)), leg.faces), panel) > 0.05
    if not hit(hi): return None
    for _ in range(24):
        mid = (lo + hi)/2; lo, hi = (lo, mid) if hit(mid) else (mid, hi)
    return hi

if __name__ == '__main__':
    P0 = ns['face'](); T = tilt(ALPHA, P0); yf = foot_y(T)
    panel, leg, info = build(yf); s = stop_angle(panel, leg)
    print(f'{TAG}: hinge y={YH}, lean {ALPHA}, foot y={yf:.2f}, stop at {s:.2f} deg, {info}')
    for nme, m in [('panel', panel), ('leg', leg)]:
        print(nme, m.is_watertight, len(m.split()), np.round(m.bounds, 1).tolist()); m.export(f'_ks8_{TAG}_{nme}.stl')
    # print-ready files: panel lying on its stop wall (x up), leg standing on its barrel end (x up)
    p = panel.copy(); p.apply_translation([-X0, 0, 0]); p.export(f'table_kickstand_{TAG}_v8_panel.stl')
    l = leg.copy(); l.apply_translation(-l.bounds[0]); l.export(f'table_kickstand_{TAG}_v8_leg.stl')
    json.dump(dict(N=N, YH=YH, alpha=ALPHA, psi=PSI, stop=s, foot_y=yf, **info), open(f'_ks8_{TAG}.json', 'w'))
