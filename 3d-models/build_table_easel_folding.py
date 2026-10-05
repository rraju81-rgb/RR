"""Folding easel, 3 cards: card panel + base (bottom hinge) + back leg (top hinge), print-in-place.
Rack frame (as printed, folded): x width, y up the panel, z out of the card face. Prints on its side (x up)."""
import trimesh, numpy as np, json
from scipy.optimize import brentq
from trimesh.creation import box, cylinder
from trimesh.transformations import rotation_matrix as RM
src = open('table_stands.py').read().split('CONFIG = {')[0]; ns = {}; exec(src, ns)
U = lambda *m: trimesh.boolean.union([x for x in m], engine='manifold')
D = lambda a, *b: trimesh.boolean.difference([a, U(*b)], engine='manifold')
N, LP = 3, 170.0                          # 3 tiers; panel covers the bottom card's full 165 mm
ns['N'], ns['LP'] = N, LP
X0, X1, G = ns['X0'], ns['X1'], 0.4
# hinge 1 (panel <-> base, bottom) and hinge 2 (panel <-> leg, top)
H1 = dict(y=3.5, z=-3.75, R=3.75, pin=1.6)
H2 = dict(y=LP-6.0, z=-6.0, R=6.0, pin=2.0)
B_Z = (-7.5, -3.5); B_Y1 = LP - 13.0      # base plate, folded behind the panel
L_Z = (-11.5, -8.5); L_Y0 = 2.0           # leg, folded behind the base
FOOT_R, GROOVE_R = 1.5, 2.0
SEG = np.linspace(X0, X1, 8)              # 7 knuckle segments; panel owns 0,2,4,6 (both ends), mover owns 1,3,5

def xcyl(r, y, z, xa, xb, sec=64):
    c = cylinder(radius=r, height=xb - xa, sections=sec)
    c.apply_transform(RM(np.pi/2, [0, 1, 0])); c.apply_translation([(xa + xb)/2, y, z]); return c

def hinge(fixed, mover, H):
    """alternate knuckles along x, 0.4 mm axial and radial gaps, pin fixed to `fixed`, bore in `mover`"""
    fk, mk, fcarve, mcarve = [], [], [], []
    for i in range(7):
        a, b = SEG[i], SEG[i+1]
        a_in = a + (G/2 if i > 0 else 0); b_in = b - (G/2 if i < 6 else 0)
        if i % 2 == 0:
            fk.append(xcyl(H['R'], H['y'], H['z'], a_in, b_in)); mcarve.append(xcyl(H['R'] + G, H['y'], H['z'], a - G/2 - (1 if i == 0 else 0), b + G/2 + (1 if i == 6 else 0)))
        else:
            mk.append(xcyl(H['R'], H['y'], H['z'], a_in, b_in)); fcarve.append(xcyl(H['R'] + G, H['y'], H['z'], a - G/2, b + G/2))
    fixed = U(D(fixed, *fcarve), *fk, xcyl(H['pin'], H['y'], H['z'], X0 + 0.6, X1 - 0.6))
    mover = D(U(D(mover, *mcarve), *mk), xcyl(H['pin'] + G + 0.05, H['y'], H['z'], X0 - 1, X1 + 1))
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
    for alpha in range(10, 61, 5):          # 5 deg skipped: cards could tip forward
        psi, fy = leg_angle(alpha)
        if psi is None: continue
        s = fy                                          # distance behind hinge 1 = distance along the base
        ok = 10 < s < LB - 6 and all(abs(s - g[1]) >= 6 for g in grooves)
        print(f'alpha {alpha:2d} deg: base rot {base_angle(alpha):5.1f}, leg rot {psi:5.1f}, foot {s:6.1f} mm behind hinge  {"-> groove" if ok else "skip"}')
        if ok: grooves.append((alpha, s))
    json.dump(grooves, open('_easel_grooves.json', 'w'))

    # ---- bodies (folded, as printed) ----
    panel = ns['face']()
    base = box(bounds=[[X0, H1['y'], B_Z[0]], [X1, B_Y1, B_Z[1]]])
    base = D(base, *[xcyl(GROOVE_R, H1['y'] + s, B_Z[1], X0 - 1, X1 + 1) for _, s in grooves])
    leg_plate = box(bounds=[[X0, L_Y0, L_Z[0]], [X1, H2['y'], L_Z[1]]])
    # edge rails on the leg's back face (thin web, thick edges), 45-deg inner chamfer for the side print
    import shapely.geometry as sg
    rz0, rz1, RW, RH = L_Z[0], L_Z[0] - 5.0, 10.0, 5.0
    ry0, ry1 = L_Y0 + 12.0, H2['y'] - 8.0
    rails = []
    for poly in [[(X0, rz0), (X0, rz1), (X0 + RW, rz1), (X0 + RW + RH, rz0)], [(X1, rz0), (X1, rz1), (X1 - RW, rz1), (X1 - RW - RH, rz0)]]:
        m = trimesh.creation.extrude_polygon(sg.Polygon(poly), ry1 - ry0)        # (x, z) polygon, length along y
        m.apply_transform(np.array([[1, 0, 0, 0], [0, 0, 1, ry0], [0, 1, 0, 0], [0, 0, 0, 1]], float))
        if m.volume < 0: m.invert()
        rails.append(m)
    rails += [box(bounds=[[X0, ry0, rz1], [X1, ry0 + RW, rz0]]), box(bounds=[[X0, ry1 - RW, rz1], [X1, ry1, rz0]])]
    win = []
    leg = U(leg_plate, *rails, xcyl(FOOT_R, L_Y0, FOOT[2], X0, X1))
    panel, base = hinge(panel, base, H1)
    panel, leg = hinge(panel, leg, H2)
    for nme, m in [('panel', panel), ('base', base), ('leg', leg)]:
        print(nme, m.is_watertight, len(m.split()), np.round(m.bounds, 1).tolist())
        m.export(f'_easel_{nme}.stl')
    allm = trimesh.util.concatenate([panel, base, leg]); allm.apply_translation([-X0, 0, 0])
    allm.export('table_easel_3card_folding.stl'); print('folded print size', np.round(allm.extents, 1).tolist())
