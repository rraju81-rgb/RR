"""Tabletop card display = rib-stiffened card rack + separate frame-holder style base (like FrameHolder.step).
Rack frame: x width, y up the card face, z towards the viewer. World: x, Y (back), Z (up)."""
import trimesh, numpy as np, json, shapely.geometry as sg
from trimesh.creation import box
src = open('table_stands.py').read().split('CONFIG = {')[0]; ns = {}; exec(src, ns)
U = lambda *m: trimesh.boolean.union(list(m), engine='manifold')
D = lambda a, *b: trimesh.boolean.difference([a, U(*b)], engine='manifold')
I = lambda a, b: trimesh.boolean.intersection([a, b], engine='manifold').volume
X0, X1 = ns['X0'], ns['X1']; XM = (X0 + X1)/2
RIB_D, RIB_W = 5.0, 10.0          # back ribs: depth behind the 3 mm panel, width
ZB = -3.0 - RIB_D                 # rack back plane (rib backs)
CLR = 0.4

def xz_prism(poly, y0, y1):
    m = trimesh.creation.extrude_polygon(sg.Polygon(poly), y1 - y0)
    m.apply_transform(np.array([[1, 0, 0, 0], [0, 0, 1, y0], [0, 1, 0, 0], [0, 0, 0, 1]], float))
    if m.volume < 0: m.invert()
    return m

def rack(N):
    ns['N'] = N; ns['LP'] = LP = max((N - 1)*55.0 + 22.0, 170.0)
    F = ns['face']()
    c = RIB_D                         # 45-deg chamfer on the side facing up in the side print
    ribs = [xz_prism([(X0, -3), (X0, ZB), (X0 + RIB_W, ZB), (X0 + RIB_W + c, -3)], 0, LP),            # edge ribs
            xz_prism([(X1, -3), (X1, ZB), (X1 - RIB_W, ZB), (X1 - RIB_W - c, -3)], 0, LP),
            xz_prism([(XM - RIB_W/2 - c, -3), (XM - RIB_W/2, ZB), (XM + RIB_W/2, ZB), (XM + RIB_W/2, -3)], 0, LP)]  # centre rib
    for yc in np.linspace(3, LP - 3, 4):                                                               # cross ribs
        ribs.append(box(bounds=[[X0, yc - 3, ZB], [X1, yc + 3, -3]]))
    return U(F, *ribs), LP

def base(LP, alpha=15.0, H_UP=None):
    """frame-holder base in the rack frame (before tilt): V-slot floor + front lip + two end back-rests"""
    H_UP = H_UP or 0.72*LP; UT = 6.0; FL = 6.0
    zf = 9.0                                                     # bottom tier front face
    floor = box(bounds=[[X0, -FL, ZB - CLR - UT], [X1, -CLR, zf + CLR + 4]])
    parts = [floor,                                                                      # slot floor (square to the face)
             box(bounds=[[X0, -FL, zf + CLR], [X1, 6.0, zf + CLR + 4]])]                # front lip, lower than the ledge lip
    for xa, xb in [(X0, X0 + RIB_W), (X1 - RIB_W, X1)]:                                 # back rests behind the edge ribs
        parts.append(box(bounds=[[xa, -FL, ZB - CLR - UT], [xb, H_UP, ZB - CLR]]))
    return U(*parts), H_UP, floor

def assemble(N, alpha=15.0, rear=None, toe=0.0, H_UP=None):
    R, LP = rack(N); Bm, H_UP, floor = base(LP, alpha, H_UP)
    T = ns['TILT'].copy()
    for m in (R, Bm, floor): m.apply_transform(T)
    lift = -floor.bounds[0, 2]                    # slot floor's lowest corner sits on the table (no raised slot)
    for m in (R, Bm, floor): m.apply_translation([0, 0, lift])
    # fill the wedge between the tilted slot floor and the table: hull of the floor block and its shadow on the table
    v = floor.vertices; shadow = v.copy(); shadow[:, 2] = 0.0
    fill = trimesh.convex.convex_hull(np.vstack([v, shadow]))
    Bm = trimesh.boolean.intersection([U(Bm, fill), box(bounds=[[-50, -100, 0.0], [300, 400, 400]])], engine='manifold')
    # world-horizontal parts: floor pad under the slot, two feet and fillet gussets (like the frame holder)
    yb = Bm.bounds[0, 1]; ytop = Bm.bounds[1, 1]
    if rear is None: rear = 0.62*H_UP
    yr = ytop + rear - 40
    parts = [Bm, box(bounds=[[X0, yb - toe, 0], [X1, ytop - 0.5*H_UP*np.sin(np.radians(alpha)) + 6, 5.0]])]   # floor pad (+ front toe)
    a = np.radians(alpha); sa, ca = np.sin(a), np.cos(a); z_back = ZB - CLR - 6.0    # back rest rear face (rack frame)
    def yback_at(zw):                                   # world Y of the back rest's rear face at world height zw
        y = (zw - lift - z_back*sa)/ca; return y*sa - z_back*ca
    for xa, xb in [(X0, X0 + RIB_W), (X1 - RIB_W, X1)]:
        parts.append(box(bounds=[[xa, yb, 0], [xb, yr, 5.0]]))                          # foot
        # gusset: triangle between the back rest and the foot (rounded look via 3 steps)
        zg = 45.0; yback = yback_at(zg)
        tri = sg.Polygon([(yback_at(3.0) - 1.5, 3.0), (yback - 1.5, zg), (yback + 38, 4.0), (yback + 38, 3.0)])   # front edge on the back rest
        g = trimesh.creation.extrude_polygon(tri, xb - xa)
        g.apply_transform(np.array([[0, 0, 1, xa], [1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 0, 1]], float))
        if g.volume < 0: g.invert()
        parts.append(g)
    Bm = U(*parts)
    return R, Bm, lift, LP

def analyse(R, Bm, lift, N, LP):
    ns['N'], ns['LP'] = N, LP; rho = 1.24e-3
    cards = ns['card_slabs'](lift, None, +1)
    res = dict(rack_watertight=bool(R.is_watertight), rack_parts=len(R.split()), base_watertight=bool(Bm.is_watertight), base_parts=len(Bm.split()),
               rack_size=[round(e, 1) for e in R.extents], base_size=[round(e, 1) for e in Bm.extents],
               rack_g=round(R.volume*rho), base_g=round(Bm.volume*rho),
               rack_base_overlap=round(I(R, Bm), 3),
               rack_seated=round(I(trimesh.Trimesh(R.vertices + [0, 0.6, -0.6], R.faces), Bm), 2),     # pushed back/down: must touch
               card_clash=round(sum(I(c, R) + I(c, Bm) for c in cards), 3))
    slide = 0.0
    for k in range(N):
        zg = 3.7 + 4.6*k + 0.3
        p = box(bounds=[[1.5 - X0 + X0, 55*k + 3.2, zg], [X1 + 150 + 108, 55*k + 3.2 + 165, zg + 0.5]])
        p.apply_transform(ns['TILT']); p.apply_translation([0, 0, lift]); slide += I(R, p) + I(Bm, p)
    res['side_slide_blocked'] = round(slide, 3)
    allm = trimesh.util.concatenate([R, Bm])
    pts = [(R.volume*rho, *R.center_mass), (Bm.volume*rho, *Bm.center_mass)] + [(m, 55, y, z) for m, y, z in ns['card_masses'](lift, None, +1)]
    yf, yr = Bm.bounds[0, 1], Bm.bounds[1, 1]
    for case, pp in [('empty', pts[:2]), ('full', pts)]:
        M = sum(p[0] for p in pp); com = sum(p[0]*np.array(p[1:]) for p in pp)/M
        res[case] = dict(mass_g=round(M), tip_front=round(np.degrees(np.arctan2(com[1] - yf, com[2])), 1),
                         tip_rear=round(np.degrees(np.arctan2(yr - com[1], com[2])), 1))
    res['standing_size'] = [round(e, 1) for e in allm.extents]
    return res

if __name__ == '__main__':
    rep = {}
    for N in (3, 5):
        for toe in [0.0, 8.0, 16.0, 24.0]:               # smallest front toe that gives >= 18 deg front tip angle, loaded
            R, Bm, lift, LP = assemble(N, toe=toe)
            r = analyse(R, Bm, lift, N, LP)
            if r['full']['tip_front'] >= 18.0: break
        r['front_toe_mm'] = toe; rep[f'{N}card'] = r; print(N, json.dumps(r))
        # rack as printed: on its side, stop wall down (x up); base as used (upright)
        Rp = R.copy(); Rp.apply_translation(-Rp.bounds[0]); Rp.export(f'table_rack_{N}card.stl')
        Bp = Bm.copy(); Bp.apply_translation(-Bp.bounds[0]); Bp.export(f'table_base_{N}card.stl')
        np.save(f'_rb_{N}.npy', [lift, LP]); R.export(f'_rb_rack_{N}.stl'); Bm.export(f'_rb_base_{N}.stl')
    json.dump(rep, open('rack_base_report.json', 'w'), indent=1)
