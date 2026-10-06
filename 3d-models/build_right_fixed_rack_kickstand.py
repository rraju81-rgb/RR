"""Fixed-rack kickstand v12: the user's right_fixed_rack_PRINT.stl (end wall trimmed to the display height, 297 mm) + ONE print-in-place hinge and a
solid kickstand strip on the back of its end wall. Single print, on its side (end wall on the bed, as supplied).
Rack frame: x = along the ledges from the end wall (print height), y = up the rack, z = forward from the back face.
Hinge (as v11): leg barrel on the bed, the rack's pin rises from the bed through it (0.7 mm gap) into a rack barrel
above (45-deg cone underside, 0.8 mm gap); the pin's cone foot is the end stop. Leg opens 0 or 35 deg only."""
import os, json, numpy as np, trimesh, manifold3d as mf
from scipy.optimize import brentq
from trimesh.creation import box, cylinder
from trimesh.transformations import rotation_matrix as RM
U = lambda *m: trimesh.boolean.union(list(m), engine='manifold')
D = lambda a, *b: trimesh.boolean.difference([a, U(*b)], engine='manifold')
I = lambda a, b: trimesh.boolean.intersection([a, b], engine='manifold').volume
SRC = os.environ.get('KS_RACK', 'reference_right_fixed_rack_PRINT.stl')
TO_RACK = np.array([[0, 0, 1, 0], [0, 1, 0, 0], [-1, 0, 0, 32], [0, 0, 0, 1]], float)   # supplied STL -> rack frame
YH = float(os.environ.get('KS_YH', 176)); ALPHA = float(os.environ.get('KS_ALPHA', 24.5)); PSI = 35.0
R_BAR, R_LEG, R_PIN = 5.0, 6.0, 2.5
G_RAD, G_CONE, GAP = 0.7, 0.8, 0.6
R_BORE = R_PIN + G_RAD
H = dict(y=YH, z=-GAP - R_LEG)
LB, PB = 18.0, 9.2                                   # leg barrel / rack barrel lengths (fit the 28 mm end-wall block)
XL = (0.0, LB); XP = (LB + G_CONE, LB + G_CONE + PB)
LEG_X = (0.0, float(os.environ.get('KS_LW', 80.0))); LT = float(os.environ.get('KS_LT', 6.0))
L_Z = (-GAP - LT, -GAP); FOOT_R = LT/2; ZM = (L_Z[0] + L_Z[1])/2
HEAD = (4.0, 1.5)


N = int(os.environ.get('KS_N', 6))                  # ledges kept from the supplied 6-ledge rack (3, 5 or 6)
YTOP = float(os.environ.get('KS_YTOP', 55.0*(N - 1) + 22.0))   # end wall cut flush with the top ledge
TAG = f'fixed_rack_{N}card'

def rack():
    m = trimesh.load(SRC); m.apply_transform(TO_RACK)
    if YTOP < m.bounds[1][1]:
        m = trimesh.boolean.intersection([m, box(bounds=[[-1, -1, -1], [200, YTOP, 50]])], engine='manifold')
    return m

def xcyl(r, y, z, xa, xb, sec=96):
    c = cylinder(radius=r, height=xb - xa, sections=sec)
    c.apply_transform(RM(np.pi/2, [0, 1, 0])); c.apply_translation([(xa + xb)/2, y, z]); return c

def xrev(prof):
    m = trimesh.creation.revolve(np.array(prof), sections=96)
    m.apply_transform(RM(np.pi/2, [0, 1, 0])); m.apply_translation([0, H['y'], H['z']])
    if m.volume < 0: m.invert()
    return m

rot = lambda deg: RM(np.radians(deg), [1, 0, 0], point=[0, H['y'], H['z']])
apply = lambda M, p: (M @ np.append(p, 1))[:3]

def tilt(alpha, body):
    a = np.radians(alpha); s, c = np.sin(a), np.cos(a)
    T = np.array([[1, 0, 0, 0], [0, s, -c, 0], [0, c, s, 0], [0, 0, 0, 1]], float)
    v = trimesh.transform_points(body.vertices, T)
    T[2, 3] -= v[:, 2].min(); T[1, 3] -= v[v[:, 2] < v[:, 2].min() + 0.3][:, 1].min(); return T

def foot_y(T):
    f = lambda yf: apply(T @ rot(PSI), np.array([LEG_X[1]/2, yf, ZM]))[2] - FOOT_R
    return brentq(f, 2.0, YH - 10)

def clean(m, tol=1e-3):
    M = mf.Manifold(mf.Mesh(vert_properties=np.asarray(m.vertices, np.float32), tri_verts=np.asarray(m.faces, np.uint32))).simplify(tol)
    me = M.to_mesh(); return trimesh.Trimesh(np.asarray(me.vert_properties)[:, :3], np.asarray(me.tri_verts), process=True)

def cone_from(x0, r0):
    return xrev([(0, x0), (r0, x0), (r0 + 60, x0 + 60), (0, x0 + 60), (0, x0)])

def build(yf):
    R = rack()
    bar = U(xcyl(R_BAR, H['y'], H['z'], *XP), box(bounds=[[XP[0], H['y'] - 4, H['z']], [XP[1], H['y'] + 4, 0.5]]))
    bar = trimesh.boolean.intersection([bar, cone_from(XP[0], R_PIN)], engine='manifold')
    pin = xcyl(R_PIN, H['y'], H['z'], 0.0, XP[0] + 1)
    foot = xrev([(0, 0.0), (HEAD[0], 0.0), (R_PIN, HEAD[1]), (0, HEAD[1]), (0, 0.0)])
    fixed = U(R, bar, pin, foot)
    leg = box(bounds=[[LEG_X[0], yf, L_Z[0]], [LEG_X[1], H['y'], L_Z[1]]])
    leg = U(leg, xcyl(FOOT_R, yf, ZM, *LEG_X))
    leg = D(leg, box(bounds=[[XL[1], H['y'] - R_BAR - GAP, -30], [LEG_X[1] + 1, H['y'] + 30, 5]]))
    tab = box(bounds=[[XL[0], H['y'], -6.0], [XL[1], H['y'] + R_LEG + 4, 0.0]])
    tab.apply_transform(rot(-PSI))                                   # lands flat on the end wall's back at PSI
    leg = U(leg, xcyl(R_LEG, H['y'], H['z'], *XL), tab)
    dh = G_CONE*np.sqrt(2)
    env = xrev([(0, -1), (HEAD[0] + dh + 1, -1), (R_PIN + dh, HEAD[1]), (R_BORE, HEAD[1] + (R_PIN + dh - R_BORE)),
                (R_BORE, XL[1] + 1), (0, XL[1] + 1), (0, -1)])
    leg = D(leg, env)
    return clean(fixed), clean(leg)

def stop_angle(fixed, leg, lo=0.5, hi=60.0):
    hit = lambda a: I(trimesh.Trimesh(trimesh.transform_points(leg.vertices, rot(a)), leg.faces), fixed) > 0.05
    if not hit(hi): return None
    for _ in range(24):
        mid = (lo + hi)/2; lo, hi = (lo, mid) if hit(mid) else (mid, hi)
    return hi

if __name__ == '__main__':
    T = tilt(ALPHA, rack()); yf = foot_y(T)
    fixed, leg = build(yf); s = stop_angle(fixed, leg)
    print(f'hinge y={YH}, lean {ALPHA}, foot y={yf:.2f}, stop at {s:.2f} deg')
    for nme, m in [('rack', fixed), ('leg', leg)]:
        print(nme, m.is_watertight, len(m.split()), np.round(m.bounds, 1).tolist()); m.export(f'_ks12_{N}_{nme}.stl')
    # back to the supplied STL's own frame and placement (prints exactly as the original)
    back = lambda m: clean(m.copy().apply_transform(np.linalg.inv(TO_RACK)))
    allm = trimesh.util.concatenate([back(fixed), back(leg)])
    allm.export(f'right_fixed_rack_{N}card_kickstand_PRINT.stl')
    json.dump(dict(YH=YH, alpha=ALPHA, psi=PSI, stop=s, foot_y=yf), open(f'_ks12_{N}.json', 'w'))
