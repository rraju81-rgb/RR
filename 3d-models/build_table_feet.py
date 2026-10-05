"""Clip-on table feet for the wall racks. Rack frame: x along the ledges, y up, z out of the wall (front = +z).
The rack drops straight down into each foot; nothing is fixed, so it lifts out to go back on the wall."""
import trimesh, numpy as np, json, shapely.geometry as sg, shapely.ops as so
from trimesh.creation import box
U = lambda *m: trimesh.boolean.union(list(m), engine='manifold')
D = lambda a, b: trimesh.boolean.difference([a, b], engine='manifold')
CLR, BASE, WALL = 0.3, 4.0, 3.0
Z_BACK, Z_FRONT = -80.0, 115.0           # foot length behind / in front of the wall plane (from the stability study)

def silhouette(rack, x0, x1, y0, y1):
    """XZ outline of the rack between heights y0..y1 and x0..x1, grown by CLR: what the socket must swallow"""
    part = trimesh.boolean.intersection([rack, box(bounds=[[x0, y0, -50], [x1, y1, 80]])], engine='manifold')
    tris = [sg.Polygon(t[:, [0, 2]]) for t in part.triangles]
    poly = so.unary_union([t.buffer(0.01) for t in tris if t.area > 1e-6]).buffer(CLR, join_style=2)
    return poly.intersection(sg.box(x0 - 5, -60, x1 + 5, 90))

def xz_prism(poly, y0, y1):
    """extrude an XZ polygon between heights y0..y1"""
    m = trimesh.creation.extrude_polygon(poly, y1 - y0)            # in XY, height along Z
    m.apply_transform(np.array([[1,0,0,0],[0,0,1,y0],[0,1,0,0],[0,0,0,1]], float))   # (x, z_poly, h) -> (x, h, z)
    if m.volume < 0: m.invert()
    return m

def foot(rack, x0, x1, depth, y_floor, tip_stop=None):
    """base strip on the table + socket block (pocket floor at y_floor, `depth` deep) + two gussets"""
    sil = silhouette(rack, x0 - 1, x1 + 1, y_floor, y_floor + depth)
    zmin, zmax = sil.bounds[1] - WALL, sil.bounds[3] + WALL
    ytab = y_floor - BASE                                           # table surface
    base = box(bounds=[[x0, ytab, Z_BACK], [x1, y_floor, Z_FRONT]])
    block = box(bounds=[[x0, ytab, zmin], [x1, y_floor + depth, zmax]])
    g = []
    for za, zb in [(zmin, Z_BACK + 8), (zmax, Z_FRONT - 8)]:            # triangular ribs, centred on the foot width
        tri = sg.Polygon([(za, y_floor), (za, y_floor + depth), (zb, y_floor)])
        m = trimesh.creation.extrude_polygon(tri, 4.0)                 # (z, y) polygon, thickness along x
        m.apply_transform(np.array([[0,0,1,(x0+x1)/2-2],[0,1,0,0],[1,0,0,0],[0,0,0,1]], float))
        if m.volume < 0: m.invert()
        g.append(m)
    pocket = xz_prism(sil, y_floor, y_floor + depth + 5)
    body = D(U(base, block, *g), pocket)
    if tip_stop is not None:
        # end stop just past the ledge tip, no higher than the ledge floor (3 mm): the card slides in above it
        lz0, lz1 = sil.bounds[1] + CLR, sil.bounds[3] - CLR
        body = U(body, box(bounds=[[tip_stop + CLR, ytab, zmin], [tip_stop + CLR + 4, y_floor + 2.6, zmax]]),
                 box(bounds=[[x1 - 1, ytab, Z_BACK], [tip_stop + CLR + 4, y_floor, Z_FRONT]]))   # base continues under the stop
    return body, ytab

out, report = {}, {}
racks = {'plain': 'rack_6ledge_130_3mmholes.stl', 'hinged': 'rack_v2_hinged_134.stl'}
for name, f in racks.items():
    r = trimesh.load(f)
    if name == 'hinged':                                            # moving + fixed bodies: use the whole as-printed shape
        r = trimesh.boolean.union(r.split(), engine='manifold')
    ybot = r.bounds[0, 1]
    left, ytab = foot(r, -6.0, 20.0, 15.0, ybot)                    # spine socket, stays left of the card groove (x>21.7)
    out[f'foot_left_{name}'] = (left, ytab)
    L = r.bounds[1, 0]                                              # ledge tip (130 plain / 134 hinged)
    right, _ = foot(r, L - 22.0, L, 12.0, 0.0, tip_stop=L)
    if ybot < 0:   # hinged rack's spine shelf hangs 4.4 mm below the ledges: raise the cradle so the rack stands level
        right = U(right, box(bounds=[[L - 22.0, ybot - BASE, Z_BACK], [L + CLR + 4, -BASE, Z_FRONT]]))           # cradle under the bottom ledge tip + end stop
    out[f'foot_right_{name}'] = (right, ybot - BASE)                # same table height as the left foot
for k, (m, ytab) in out.items():
    m2 = m.copy(); m2.apply_translation([0, -ytab, 0])              # table at y=0 in the exported part
    m2.export(f'{k}.stl'); print(k, m2.is_watertight, len(m2.split()), np.round(m2.extents, 1).tolist(), round(m2.volume*1.24e-3, 1), 'g')
