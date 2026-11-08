"""Shut-line ribbons, door handles, mirrors and number plates on the procedural body."""
import numpy as np, trimesh
from trimesh.ray.ray_pyembree import RayMeshIntersector
from car_body import Z_F, Y_G

def surf_points(R, pts2d, side, mode):
    """project 2D points onto the body. mode 'side': (s,h) rays along -x*side; 'rear': (x,h) rays along -z"""
    P = np.asarray(pts2d, float)
    if mode == 'side':
        O = np.column_stack([np.full(len(P), side * 1500.0), P[:, 1] + Y_G, P[:, 0] + Z_F]); D = np.tile([-side, 0, 0.0], (len(P), 1))
    else:
        O = np.column_stack([P[:, 0], P[:, 1] + Y_G, np.full(len(P), Z_F + 5000.0)]); D = np.tile([0, 0, -1.0], (len(P), 1))
    loc, ir, it = R.intersects_location(O, D, multiple_hits=False)
    out = np.full((len(P), 3), np.nan); nrm = np.full((len(P), 3), np.nan)
    out[ir] = loc; nrm[ir] = R.mesh.face_normals[it]
    ok = np.isfinite(out[:, 0])
    return out[ok], nrm[ok]

def ribbon(p, n, width=2.6, lift=0.35):
    t = np.gradient(p, axis=0); t /= np.linalg.norm(t, axis=1)[:, None] + 1e-12
    b = np.cross(n, t); b /= np.linalg.norm(b, axis=1)[:, None] + 1e-12
    c = p + n * lift
    V = np.vstack([c + b * width / 2, c - b * width / 2]); m = len(p); F = []
    for i in range(m - 1):
        F += [[i, i + 1, m + i + 1], [i, m + i + 1, m + i]]
    return trimesh.Trimesh(V, np.array(F), process=False)

def dense(poly, step=4.0):
    P = np.asarray(poly, float); out = [P[0]]
    for a, b in zip(P[:-1], P[1:]):
        k = max(1, int(np.ceil(np.linalg.norm(b - a) / step)))
        out += list(a + (b - a) * (np.arange(1, k + 1) / k)[:, None])
    return np.array(out)

SIDE_LINES = [
    [(1206, 275), (1208, 520), (1212, 760), (1218, 950), (1240, 985)],                       # front door, front edge
    [(2226, 262), (2227, 600), (2229, 990)],                                                  # B-pillar door gap
    [(3334, 1036), (3300, 900), (3262, 760), (3232, 690), (3180, 640), (3120, 560), (3082, 460), (3066, 330), (3064, 262)],  # rear door rear edge
    [(1206, 272), (2226, 262), (3064, 262)],                                                  # door bottoms
]
REAR_LINES = [
    [(-505, 1008), (-512, 900), (-520, 760), (-526, 660)], [(505, 1008), (512, 900), (520, 760), (526, 660)],   # tailgate sides
    [(-526, 655), (-300, 652), (0, 651), (300, 652), (526, 655)],                                                 # tailgate bottom / bumper top
    [(-760, 640), (-500, 622), (0, 616), (500, 622), (760, 640)],                                                 # bumper split
]
def build(car):
    R = RayMeshIntersector(car)
    rib = []
    for side in (-1, 1):
        for L in SIDE_LINES:
            p, n = surf_points(R, dense(L), side, 'side')
            if len(p) > 3: rib.append(ribbon(p, n))
    for L in REAR_LINES:
        p, n = surf_points(R, dense(L), 0, 'rear')
        if len(p) > 3: rib.append(ribbon(p, n))
    ribbons = trimesh.util.concatenate(rib)
    # door handles (body colour) on the shoulder line
    handles = []
    for side in (-1, 1):
        for sc in (2075.0, 3105.0):
            p, n = surf_points(R, [(sc, 925.0)], side, 'side')
            if not len(p): continue
            hb = trimesh.creation.capsule(height=95, radius=11, count=[16, 16])     # axis along z (car length)
            hb.apply_scale([0.6, 1.0, 1.0]); hb.apply_translation(p[0] + n[0] * 4.0); handles.append(hb)
    handles = trimesh.util.concatenate(handles)
    # mirrors: head on the door's front-top corner
    mirrors = []
    for side in (-1, 1):
        p, n = surf_points(R, [(1330.0, 1010.0)], side, 'side')
        if not len(p): continue
        # rounded wedge housing: superellipsoid, wider outboard, flat rear face (glass side) facing -z (forward)... rear-facing
        g = trimesh.creation.icosphere(subdivisions=5, radius=1.0); v = g.vertices.copy()
        e = 0.45; v = np.sign(v) * np.abs(v) ** e                      # superellipsoid (boxier)
        v *= np.array([105.0, 62.0, 52.0])                              # half sizes: outboard, height, depth
        v[:, 2] = np.where(v[:, 2] > 0, v[:, 2] * 0.35, v[:, 2])         # flatten the glass (rear) side
        v[:, 1] += 0.18 * v[:, 0] * side                                 # slight upward sweep outboard
        g.vertices = v
        arm = trimesh.creation.box(extents=[70, 24, 60]); arm.apply_translation([-side * 95, -40, -5])
        mm = trimesh.util.concatenate([g, arm]); mm.apply_translation(p[0] + np.array([side * 120.0, 55.0, 10.0])); mirrors.append(mm)
    mirrors = trimesh.util.concatenate(mirrors)
    # number plates (front + rear), 520 x 112, 3 mm, on the bumper/tailgate surface
    plates = []
    for mode, pt in [('rear', (0.0, 770.0))]:
        p, n = surf_points(R, [pt], 0, mode)
        if not len(p): continue
        pl = trimesh.creation.box(extents=[520, 112, 3]); pl.apply_translation(p[0] + np.array([0, 0, 2.0])); plates.append(pl)
    plates = trimesh.util.concatenate(plates) if plates else None
    return dict(ribbons=ribbons, handles=handles, mirrors=mirrors, plates=plates)
