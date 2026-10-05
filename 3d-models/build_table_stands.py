"""Tabletop Hot Wheels card stands, built from the wall-rack tier geometry.
Rack frame: x = width, y = up along the card face, z = out of the face (towards the viewer).
World frame: x = width, Y = depth (+ = away from viewer), Z = up. Prints on its side (x vertical), no supports."""
import trimesh, numpy as np, json, shapely.geometry as sg
from trimesh.creation import box
U = lambda *m: trimesh.boolean.union(list(m), engine='manifold')

# ---- parameters -------------------------------------------------------------------------
CARD_W, CARD_H = 108.0, 165.0          # Hot Wheels mainline card
W_IN   = CARD_W + 3.0                  # 1.5 mm side clearance -> card sits fully inside
CHEEK  = 5.0                           # end wall / bracket thickness
N      = 4                             # tiers per face
PITCH, STEP = 55.0, 4.6                # same shingle geometry as the wall rack
ALPHA  = np.radians(15.0)              # face tilted back from vertical
PANEL  = 3.0                           # back panel thickness
LP     = (N-1)*PITCH + 22.0            # panel length along the face (to the top ledge's back wall)
BASE_T = 3.0
STOP_T = 8.0                           # solid left end wall: holds every ledge and stops the card
X0, X1 = -STOP_T, W_IN                 # right end fully open so cards slide in from the side

def tier(k):
    y0 = PITCH*k
    zb = 0.0 if k == 0 else 1.3 + STEP*k        # ledge back (clear of the cards passing behind it)
    zg, zl, zf = 3.7 + STEP*k, 5.5 + STEP*k, 9.0 + STEP*k
    parts = [box(bounds=[[0, y0, zb], [W_IN, y0+3, zf]]),            # floor
             box(bounds=[[0, y0, zb], [W_IN, y0+22, zg]]),           # back wall
             box(bounds=[[0, y0, zl], [W_IN, y0+4, zf]]),            # front lip (4 mm)
             box(bounds=[[0, y0, zg+1.3], [9, y0+10, zf]]),          # 10 mm corner supports (groove 1.3 mm here)
             box(bounds=[[W_IN-9, y0, zg+1.3], [W_IN, y0+10, zf]]),
             box(bounds=[[X0, y0, -PANEL], [0, min(y0+PITCH, LP), zf]])]   # left end wall segment (card stop)
    return parts

def face():
    return U(box(bounds=[[X0, 0, -PANEL], [X1, LP, 0]]), box(bounds=[[X0, 0, -PANEL], [0, LP, 4.0]]),
             *[p for k in range(N) for p in tier(k)])

s, c = np.sin(ALPHA), np.cos(ALPHA)
TILT = np.array([[1,0,0,0],[0,s,-c,0],[0,c,s,0],[0,0,0,1]], float)   # rack (x,y,z) -> world (x,Y,Z)
to_world = lambda y, z: np.array([y*s - z*c, y*c + z*s])

def prism(poly2d, x0=X0, x1=X1):
    """extrude a (Y,Z) polygon along x"""
    m = trimesh.creation.extrude_polygon(sg.Polygon(poly2d), x1 - x0)
    m.apply_transform(np.array([[0,0,1,x0],[1,0,0,0],[0,1,0,0],[0,0,0,1]], float)); return m

def strut(p, q, t, x0=X0, x1=X1):
    ls = sg.LineString([p, q]).buffer(t/2, cap_style=2, join_style=2)
    return prism(list(ls.exterior.coords), x0, x1)

def build(variant):
    F = face(); F.apply_transform(TILT)
    lift = 1.5 - F.bounds[0, 2]; F.apply_translation([0, 0, lift])
    W = lambda y, z: to_world(y, z) + [0, lift]
    y_front = F.bounds[0, 1]
    top_back = W(LP, -PANEL)                       # top of the panel's back face
    if variant == 'A':
        P = W(LP - 12, -PANEL)                     # rear leg leaves the panel 12 mm below its top
        y_rear = P[0] + 62.0                       # foot position (from the stability study below)
        legs = [strut(P, [y_rear, 1.5], 4.0, X0, X0+22), strut(P, [y_rear, 1.5], 4.0, X1-22, X1)]
        base = box(bounds=[[X0, y_front, 0], [X1, y_rear+2, BASE_T]])
        body = U(F, base, *legs)
        faces = [(F, +1)]
    else:
        # mirror the face about the plane through its top edge -> panels meet at the apex
        yc = top_back[0] - 1.0
        Fm = F.copy(); Fm.apply_transform(np.array([[1,0,0,0],[0,-1,0,2*yc],[0,0,1,0],[0,0,0,1]], float))
        if Fm.volume < 0: Fm.invert()
        base = box(bounds=[[X0, y_front, 0], [X1, 2*yc - y_front, BASE_T]])
        apex = box(bounds=[[X0, yc-3, top_back[1]-6], [X1, yc+3, top_back[1]]])
        body = U(F, Fm, base, apex)
        faces = [(F, +1), (Fm, -1)]
    body.apply_translation([-X0, 0, 0])            # x from 0
    return body, lift, yc if variant == 'B' else None

def card_masses(lift, mirror_yc=None, side=+1):
    """per card: 30 g car in the blister (50 mm up, 12 mm proud), 10 g card+blister at card centre"""
    pts = []
    for k in range(N):
        zg = 3.7 + STEP*k + 0.5
        for m, yl, dz in [(30.0, PITCH*k + 3 + 50, 12.0), (10.0, PITCH*k + 3 + CARD_H/2, 0.0)]:
            Y, Z = to_world(yl, zg + dz); Z += lift
            if side < 0: Y = 2*mirror_yc - Y
            pts.append((m, Y, Z))
    return pts

def card_slabs(lift, mirror_yc=None, side=+1):
    out = []
    for k in range(N):
        zg = 3.7 + STEP*k + 0.3
        b = box(bounds=[[1.5 - X0, PITCH*k + 3.2, zg], [1.5 + CARD_W - X0, PITCH*k + 3.2 + CARD_H, zg + 0.5]])
        b.apply_transform(TILT); b.apply_translation([0, 0, lift])
        if side < 0: b.apply_transform(np.array([[1,0,0,0],[0,-1,0,2*mirror_yc],[0,0,1,0],[0,0,0,1]], float))
        out.append(b)
    return out

report = {}
CONFIG = {'A': dict(N=4, LP=(4-1)*PITCH + 22.0),     # easel: panel just covers the 4 tiers
          'B': dict(N=3, LP=232.0)}                 # A-frame: apex raised so the two faces' cards never cross
for v in 'AB':
    N, LP = CONFIG[v]['N'], CONFIG[v]['LP']
    body, lift, yc = build(v)
    body.export(f'table_stand_{v}.stl')
    rho = 1.24e-3                                   # PLA g/mm^3
    stand_g = body.volume * rho
    sides = [+1] if v == 'A' else [+1, -1]
    cases = {'empty': []}
    for sd in sides: cases.setdefault('full', []).extend(card_masses(lift, yc, sd))
    if v == 'B': cases['one side full'] = card_masses(lift, yc, +1)
    ymin, ymax = body.bounds[0, 1], body.bounds[1, 1]
    res = {}
    for name, pts in cases.items():
        M = stand_g + sum(p[0] for p in pts)
        cy = (stand_g*body.center_mass[1] + sum(p[0]*p[1] for p in pts)) / M
        cz = (stand_g*body.center_mass[2] + sum(p[0]*p[2] for p in pts)) / M
        dF, dR = cy - ymin, ymax - cy
        res[name] = dict(mass_g=round(M, 1), com_Y=round(cy, 1), com_Z=round(cz, 1),
                         margin_front_mm=round(dF, 1), margin_rear_mm=round(dR, 1),
                         tip_angle_front_deg=round(np.degrees(np.arctan2(dF, cz)), 1),
                         tip_angle_rear_deg=round(np.degrees(np.arctan2(dR, cz)), 1),
                         push_at_top_to_tip_N=round(M/1000*9.81*min(dF, dR)/body.bounds[1, 2], 2))
    # card clearance: every card slab must be free of the stand
    clash = sum(trimesh.boolean.intersection([body, cs], engine='manifold').volume
                for sd in sides for cs in card_slabs(lift, yc, sd))
    slide = 0.0
    for sd in sides:
        for k in range(N):
            zg = 3.7 + STEP*k + 0.3
            p = box(bounds=[[1.5 - X0, PITCH*k + 3.2, zg], [W_IN - X0 + 150 + CARD_W, PITCH*k + 3.2 + CARD_H, zg + 0.5]])
            p.apply_transform(TILT); p.apply_translation([0, 0, lift])
            if sd < 0: p.apply_transform(np.array([[1,0,0,0],[0,-1,0,2*yc],[0,0,1,0],[0,0,0,1]], float))
            slide += trimesh.boolean.intersection([body, p], engine='manifold').volume
    stop_gap = None
    cross = 0.0
    if v == 'B':
        fr, rr = card_slabs(lift, yc, +1), card_slabs(lift, yc, -1)
        cross = sum(trimesh.boolean.intersection([a, b], engine='manifold').volume for a in fr for b in rr)
    report[v] = dict(side_slide_path_blocked_mm3=round(slide, 3), front_vs_rear_card_clash_mm3=round(cross, 3), tiers_per_face=N, panel_len_mm=LP, watertight=bool(body.is_watertight), parts=len(body.split()),
                     size_mm=[round(e, 1) for e in body.extents], print_on_side_footprint_mm=[round(body.extents[1], 1), round(body.extents[2], 1)],
                     print_height_mm=round(body.extents[0], 1), filament_g_solid=round(stand_g, 1),
                     cards=len(sides)*N, card_clash_mm3=round(clash, 3), stability=res)
    np.save(f'_tbl_{v}.npy', np.array([lift, yc if yc is not None else np.nan]))
print(json.dumps(report, indent=1))
json.dump(report, open('table_stands_report.json', 'w'), indent=1)
