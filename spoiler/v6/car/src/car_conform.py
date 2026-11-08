"""Conform the car body under the spoiler: every car vertex under the spoiler's contact surface moves along its own
normal so the gap is exactly GAP (tape), and the correction fades to zero over FADE mm outside the covered area."""
import numpy as np, trimesh, scipy.sparse as sp
from trimesh.ray.ray_pyembree import RayMeshIntersector
GAP, FADE, ZMAX = 1.5, 70.0, 230.0

def contact_patch(E, car):
    """car-facing spoiler faces in the contact zone: underside (normal down) or fin inner faces (normal inboard)"""
    c = E.triangles_center; n = E.face_normals
    under = n[:, 1] < -0.2
    fin_in = (np.abs(c[:, 0]) > 500) & (n[:, 0] * np.sign(c[:, 0]) < -0.25) & (n[:, 1] < 0.35)
    keep = np.nonzero((c[:, 2] <= ZMAX) & (under | fin_in))[0]
    return E.submesh([keep], append=True)

def conform(car, E):
    patch = contact_patch(E, car)
    Rp = RayMeshIntersector(patch)
    V = car.vertices.copy(); N = car.vertex_normals.copy()
    roi = np.nonzero((V[:, 2] > -120) & (V[:, 2] < ZMAX + 40) & (V[:, 1] > -170))[0]
    delta = np.zeros(len(V)); fixed = np.zeros(len(V), bool)
    import igl
    VE = np.asarray(E.vertices, np.float64); FE = np.asarray(E.faces, np.int64)
    # coverage: inside the spoiler, or the outward normal ray meets the contact patch within 60 mm
    S_roi = igl.signed_distance(V[roi], VE, FE)[0]
    inside = np.zeros(len(V), bool); inside[roi] = S_roi < 0
    loc, ir, it = Rp.intersects_location(V[roi] + N[roi] * 0.01, N[roi], multiple_hits=False)
    t = np.linalg.norm(loc - V[roi][ir], axis=1)
    hit = np.zeros(len(roi), bool); hit[ir[t < 60]] = True
    rear_facing = N[roi][:, 2] > 0.40          # rear window / tailgate: never part of the contact correction
    cov = (hit | (S_roi < 0)) & ~rear_facing
    ii = np.nonzero(inside)[0]
    # correction from the smooth signed distance (not from the ray length): gap becomes GAP
    delta[roi[cov]] = S_roi[cov] - GAP; fixed[roi[cov]] = True
    print('covered vertices', fixed.sum(), ' inside', len(ii), ' delta range %.1f..%.1f' % (delta[fixed].min(), delta[fixed].max()))
    # fade band: diffuse delta into nearby free vertices (Jacobi), zero beyond FADE
    from scipy.spatial import cKDTree
    tree = cKDTree(V[fixed]); dist, _ = tree.query(V, distance_upper_bound=FADE + 10)
    band = (~fixed) & (dist < FADE) & (N[:, 2] < 0.40)
    edges = car.edges_unique
    A = sp.coo_matrix((np.ones(len(edges) * 2), (np.r_[edges[:, 0], edges[:, 1]], np.r_[edges[:, 1], edges[:, 0]])), shape=(len(V), len(V))).tocsr()
    deg = np.asarray(A.sum(1)).ravel()
    d = delta.copy()
    for it_ in range(300):
        dn = (A @ d) / np.maximum(deg, 1)
        d = np.where(band, dn, d)
        d = np.where(fixed, delta, d)
    w = np.clip(1 - dist / FADE, 0, 1); w = w * w * (3 - 2 * w)
    d = np.where(band, d * w, d)
    # also smooth inside the covered region a little (ray noise at patch edges)
    for it_ in range(6):
        dn = (A @ d) / np.maximum(deg, 1)
        d = np.where(fixed, 0.5 * d + 0.5 * dn, d)
    # smooth the whole correction field (removes ray noise at the patch edges)
    reg = fixed | band
    for it_ in range(12):
        dn = (A @ d) / np.maximum(deg, 1)
        d = np.where(reg, 0.5 * d + 0.5 * dn, d)
    V2 = V + N * d[:, None]
    # de-intersection: nothing of the car may be inside or closer than MINGAP to the spoiler; intruders are
    # snapped to the car-facing side (contact patch) of the spoiler
    import igl
    from scipy.spatial import cKDTree
    MINGAP = 1.2
    VE = np.asarray(E.vertices, np.float64); FE = np.asarray(E.faces, np.int64)
    kd = cKDTree(VE)
    for rnd in range(3):
        dd, _ = kd.query(V2, distance_upper_bound=12.0)
        cand = np.nonzero(np.isfinite(dd))[0]
        S = igl.signed_distance(V2[cand], VE, FE)[0]
        m_ = (S < 0) | ((S < MINGAP) & fixed[cand])
        bad = cand[m_]
        if not len(bad): break
        V2[bad] -= N[bad] * ((MINGAP - S[m_]) * 1.05)[:, None]      # along the car's own (smooth) normal
        print('  de-intersection round', rnd, 'moved', len(bad), 'max depth %.1f' % (MINGAP - S[m_]).max())
    # light smoothing of the total displacement, then a last push-out
    D = V2 - V
    for it_ in range(4):
        D = np.where(reg[:, None] | (np.linalg.norm(D, axis=1) > 0)[:, None], 0.5 * D + 0.5 * (A @ D) / np.maximum(deg, 1)[:, None], D)
    V2 = V + D
    dd, _ = kd.query(V2, distance_upper_bound=12.0); cand = np.nonzero(np.isfinite(dd))[0]
    S = igl.signed_distance(V2[cand], VE, FE)[0]; m_ = (S < 0) | ((S < MINGAP) & fixed[cand])
    V2[cand[m_]] -= N[cand[m_]] * ((MINGAP - S[m_]) * 1.05)[:, None]
    print('  final push-out', int(m_.sum()))
    # untangle: relax the displacement around faces that tilted > 60 deg (folds at wedges/fin corners)
    F_ = car.faces; nb = car.face_normals
    for rnd in range(4):
        tri = V2[F_]; nc = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]); nc /= np.linalg.norm(nc, axis=1)[:, None] + 1e-12
        badf = np.nonzero((nb * nc).sum(1) < 0.5)[0]
        if not len(badf): break
        vv = np.unique(F_[badf]); ring = np.unique(np.concatenate([vv, (A[vv].nonzero()[1])]))
        Dd = V2 - V
        for it_ in range(15):
            Dn = (A @ Dd) / np.maximum(deg, 1)[:, None]
            Dd[ring] = 0.3 * Dd[ring] + 0.7 * Dn[ring]
        V2 = V + Dd
        print('  untangle round', rnd, 'bad faces', len(badf))
    dd, _ = kd.query(V2, distance_upper_bound=12.0); cand = np.nonzero(np.isfinite(dd))[0]
    S = igl.signed_distance(V2[cand], VE, FE)[0]; m_ = S < 0
    V2[cand[m_]] -= N[cand[m_]] * ((MINGAP - S[m_]) * 1.05)[:, None]
    print('  post-untangle push-out', int(m_.sum()))
    out = trimesh.Trimesh(V2, car.faces.copy(), process=False)
    out.metadata['covered'] = fixed
    return out, d

if __name__ == '__main__':
    import sys
    src, dst = sys.argv[1], sys.argv[2]
    car = trimesh.load(src); E = trimesh.load('v6/out/E2.stl')
    out, d = conform(car, E)
    out.export(dst)
    print('moved vertices', int((np.abs(d) > 0.01).sum()), 'max |d| %.1f' % np.abs(d).max())
