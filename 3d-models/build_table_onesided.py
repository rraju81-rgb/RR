"""One-sided card stand (3 or 5 cards): card face + light diamond-lattice back leg + lattice base. One print, on its side."""
import trimesh, numpy as np, json, shapely.geometry as sg
from trimesh.creation import box
src = open('table_stands.py').read().split('CONFIG = {')[0]; ns = {}; exec(src, ns)
U = lambda *m: trimesh.boolean.union(list(m), engine='manifold')
D = lambda a, *b: trimesh.boolean.difference([a, U(*b)], engine='manifold')
X0, X1 = ns['X0'], ns['X1']; W = X1 - X0

def lattice_plate(p0, p1, t, side=+1, margin=8.0):
    """plate from p0 to p1 in (Y,Z), thickness t to one side, full width, two staggered columns of 45-deg diamonds"""
    p0, p1 = np.array(p0, float), np.array(p1, float); L = np.linalg.norm(p1 - p0); d = (p1 - p0)/L
    n = np.array([-d[1], d[0]]) * side
    outline = sg.box(0, X0, L, X1)
    h = W/4 - 5.0                                         # diamond half-diagonal
    holes = []
    for col, xc in enumerate([X0 + W/4, X0 + 3*W/4]):
        s = margin + h + (0 if col == 0 else h + 3)       # staggered columns
        while s + h + margin <= L:
            holes.append(sg.Polygon([(s - h, xc), (s, xc + h), (s + h, xc), (s, xc - h)])); s += 2*h + 6
    poly = outline.difference(sg.MultiPolygon(holes) if holes else sg.Polygon())
    m = trimesh.creation.extrude_polygon(poly, t)         # local (s, x, thickness)
    M = np.array([[0, 1, 0, 0], [d[0], 0, n[0], p0[0]], [d[1], 0, n[1], p0[1]], [0, 0, 0, 1]], float)
    m.apply_transform(M)
    if m.volume < 0: m.invert()
    return m

def build(N, rear=58.0, toe=0.0):
    ns['N'] = N; ns['LP'] = LP = max((N - 1)*55.0 + 22.0, 170.0)
    F = ns['face'](); F.apply_transform(ns['TILT'])
    lift = 1.5 - F.bounds[0, 2]; F.apply_translation([0, 0, lift])
    Wp = lambda y, z: ns['to_world'](y, z) + [0, lift]
    yf = F.bounds[0, 1] - toe
    P = Wp(LP - 10, -3.0)                                  # leg meets the panel back 10 mm below its top
    foot = np.array([P[0] + rear, 0.0])
    leg = lattice_plate(P, foot, 4.0, side=-1)
    leg = U(leg, box(bounds=[[X0, foot[0] - 6, 0], [X1, foot[0] + 2, 3.0]]))   # foot pad
    base = lattice_plate([yf, 0], [foot[0] + 2, 0], 3.0, side=+1, margin=10)
    body = U(F, leg, base)
    body.apply_translation([-X0, 0, 0])
    return body, lift, LP

def analyse(body, lift, N, LP):
    rho = 1.24e-3; I = lambda a, b: trimesh.boolean.intersection([a, b], engine='manifold').volume
    ns['N'], ns['LP'] = N, LP
    cards = ns['card_slabs'](lift, None, +1)
    clash = sum(I(body, c) for c in cards)
    slide = 0.0
    for k in range(N):
        zg = 3.7 + 4.6*k + 0.3
        p = box(bounds=[[1.5 - X0, 55*k + 3.2, zg], [X1 - X0 + 150 + 108, 55*k + 3.2 + 165, zg + 0.5]])
        p.apply_transform(ns['TILT']); p.apply_translation([0, 0, lift]); slide += I(body, p)
    stop = min(I(body, trimesh.Trimesh(c.vertices - [2.0, 0, 0], c.faces)) for c in cards)
    pts = [(body.volume*rho, *body.center_mass)] + [(m, 60, y, z) for m, y, z in ns['card_masses'](lift, None, +1)]
    out = {}
    for case, pp in [('empty', pts[:1]), ('full', pts)]:
        M = sum(p[0] for p in pp); com = sum(p[0]*np.array(p[1:]) for p in pp)/M
        yf, yr = body.bounds[0, 1], body.bounds[1, 1]
        out[case] = dict(mass_g=round(M), com_height=round(com[2], 1),
                         tip_front_deg=round(np.degrees(np.arctan2(com[1] - yf, com[2])), 1),
                         tip_rear_deg=round(np.degrees(np.arctan2(yr - com[1], com[2])), 1))
    return dict(cards=N, size_mm=[round(e, 1) for e in body.extents], filament_g=round(body.volume*rho),
                watertight=bool(body.is_watertight), parts=len(body.split()), card_clash_mm3=round(clash, 3),
                side_slide_blocked_mm3=round(slide, 3), card_stop_min_mm3=round(stop, 1), stability=out)

if __name__ == '__main__':
    rep = {}
    for N, toe in [(3, 0.0), (5, 0.0)]:
        body, lift, LP = build(N, toe=toe)
        r = analyse(body, lift, N, LP)
        if r['stability']['full']['tip_front_deg'] < 18:          # tall version: add a front toe until >= 18 deg
            for toe in np.arange(5, 41, 5):
                body, lift, LP = build(N, toe=toe); r = analyse(body, lift, N, LP)
                if r['stability']['full']['tip_front_deg'] >= 18: break
        r['front_toe_mm'] = float(toe); rep[f'{N}card'] = r
        body.export(f'table_onesided_{N}card.stl'); np.save(f'_os_{N}.npy', [lift, LP])
    print(json.dumps(rep, indent=1)); json.dump(rep, open('onesided_report.json', 'w'), indent=1)
