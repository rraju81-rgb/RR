"""Kickstand easel v11: ONE print-in-place print. Card panel + a 3-part hinge + a solid 6 mm leg strip.
Leg barrel (24 mm, 12 mm across) and strip start on the bed at the stop-wall end. The panel's pin rises from the bed
through the leg barrel (0.7 mm radial gap) into an 8 mm panel barrel above; the pin's cone-shaped foot is the end stop.
Every surface printed over a gap is a 45-deg cone with a 0.8 mm gap, so nothing bridges flat over the moving part.
Two positions only: 0 deg (folded) and 35 deg (stop tab on the panel back).
Rack frame: x width, y up the panel, z out of the card face. Prints on its side (x up, stop wall down)."""
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
R_BAR, R_LEG, R_PIN = 5.0, 6.0, 2.5                        # panel barrel 10 mm, leg barrel 12 mm, pin 5 mm
G_RAD, G_CONE, GAP = 0.7, 0.8, 0.6                          # print gaps: pin/bore, cone & barrel ends, leg/panel back
R_BORE = R_PIN + G_RAD
H = dict(y=YH, z=-3.0 - GAP - R_LEG)
LB, PB = 24.0, 8.0
XL = (X0, X0 + LB)                                          # leg barrel, on the bed
XP = (XL[1] + G_CONE, XL[1] + G_CONE + PB)                  # panel barrel above it
LEG_X = (X0, X0 + 40.0)                                     # 40 mm strip, flush with the stop-wall end
LT = float(os.environ.get('KS_LT', 6.0))                    # strip thickness
L_Z = (-3.0 - GAP - LT, -3.0 - GAP); FOOT_R = LT/2
ZM = (L_Z[0] + L_Z[1])/2
HEAD = (4.0, 1.5)                                           # pin foot: cone r 4 at the bed -> r 2.5 at 1.5 mm
PSI = 35.0
HEAD = (4.5, 2.5)                                          # pin head radius / thickness (sits outside the stopper barrel)

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

def cone_from(x0, r0):
    """region above a 45-deg cone starting at radius r0, height x0: x >= x0 + max(0, r - r0)"""
    return xrev([(0, x0), (r0, x0), (r0 + 60, x0 + 60), (0, x0 + 60), (0, x0)])

def build(yf):
    panel = ns['face']()
    # panel barrel + web, underside a 45-deg cone growing out of the pin (no flat overhang over the leg)
    bar = U(xcyl(R_BAR, H['y'], H['z'], *XP), box(bounds=[[XP[0], H['y'] - 4, H['z']], [XP[1], H['y'] + 4, -2.9]]))
    bar = trimesh.boolean.intersection([bar, cone_from(XP[0], R_PIN)], engine='manifold')
    pin = xcyl(R_PIN, H['y'], H['z'], X0, XP[0] + 1)
    foot = xrev([(0, X0), (HEAD[0], X0), (R_PIN, X0 + HEAD[1]), (0, X0 + HEAD[1]), (0, X0)])
    panel = U(panel, bar, pin, foot)
    # leg: barrel + 6 mm strip + rounded foot + stop tab, all starting on the bed
    leg = box(bounds=[[LEG_X[0], yf, L_Z[0]], [LEG_X[1], H['y'], L_Z[1]]])
    leg = U(leg, xcyl(FOOT_R, yf, ZM, *LEG_X))
    leg = D(leg, box(bounds=[[XL[1], H['y'] - R_BAR - GAP, -30], [LEG_X[1] + 1, H['y'] + 30, 5]]))   # clear of the panel barrel
    tab = box(bounds=[[XL[0], H['y'], -3.0 - 6.0], [XL[1], H['y'] + R_LEG + 4, -3.0]])
    tab.apply_transform(rot(-PSI))                                   # lands flat on the panel back at PSI
    leg = U(leg, xcyl(R_LEG, H['y'], H['z'], *XL), tab)
    # bore, and the pin foot's envelope (0.8 mm normal gap on the 45-deg cone; the leg overhangs it at 45 deg)
    dh = G_CONE*np.sqrt(2)
    env = xrev([(0, X0 - 1), (HEAD[0] + dh + 1, X0 - 1), (R_PIN + dh, X0 + HEAD[1]), (R_BORE, X0 + HEAD[1] + (R_PIN + dh - R_BORE)),
                (R_BORE, XL[1] + 1), (0, XL[1] + 1), (0, X0 - 1)])
    leg = D(leg, env)
    return clean(panel), clean(leg)

def stop_angle(panel, leg, lo=0.5, hi=60.0):
    hit = lambda a: I(trimesh.Trimesh(trimesh.transform_points(leg.vertices, rot(a)), leg.faces), panel) > 0.05
    if not hit(hi): return None
    for _ in range(24):
        mid = (lo + hi)/2; lo, hi = (lo, mid) if hit(mid) else (mid, hi)
    return hi

if __name__ == '__main__':
    P0 = ns['face'](); T = tilt(ALPHA, P0); yf = foot_y(T)
    panel, leg = build(yf); s = stop_angle(panel, leg)
    print(f'{TAG}: hinge y={YH}, lean {ALPHA}, foot y={yf:.2f}, stop at {s:.2f} deg')
    for nme, m in [('panel', panel), ('leg', leg)]:
        print(nme, m.is_watertight, len(m.split()), np.round(m.bounds, 1).tolist()); m.export(f'_ks11_{TAG}_{nme}.stl')
    allm = trimesh.util.concatenate([panel, leg]); allm.apply_translation([-X0, 0, 0]); allm.export(f'table_kickstand_{TAG}_v11.stl')
    json.dump(dict(N=N, YH=YH, alpha=ALPHA, psi=PSI, stop=s, foot_y=yf), open(f'_ks11_{TAG}.json', 'w'))
