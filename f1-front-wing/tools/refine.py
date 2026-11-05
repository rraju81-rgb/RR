"""ICP refinement of joint transforms using the cut boundary vertices shared by both sides of a cut."""
import numpy as np
from scipy.spatial import cKDTree

def boundary_vertices(m, faces):
    S = np.zeros(len(m.faces), bool); S[faces] = True
    adj = m.face_adjacency; e = m.face_adjacency_edges
    inS = S[adj]
    bd = np.where(inS[:, 0] ^ inS[:, 1])[0]
    vid = np.unique(e[bd].ravel())
    return m.vertices[vid]

def kabsch(X, Y):
    """Find R,t minimizing |R X + t - Y|."""
    cx, cy = X.mean(0), Y.mean(0)
    H = (X - cx).T @ (Y - cy)
    U, S, Vt = np.linalg.svd(H)
    D = np.eye(3); D[2, 2] = np.sign(np.linalg.det(Vt.T @ U.T))
    R = Vt.T @ D @ U.T
    return R, cy - R @ cx

def icp_refine(bA, bB, T, iters=50, max_d=1.5):
    """Refine T (maps B coords -> A coords) so transformed bB lands on bA."""
    tree = cKDTree(bA)
    T = T.copy()
    for it in range(iters):
        Xb = bB @ T[:3, :3].T + T[:3, 3]
        d, idx = tree.query(Xb)
        ok = d < max_d
        if ok.sum() < 6:
            break
        R, t = kabsch(Xb[ok], bA[idx[ok]])
        dT = np.eye(4); dT[:3, :3] = R; dT[:3, 3] = t
        T = dT @ T
        if np.linalg.norm(t) < 1e-6 and np.arccos(np.clip((np.trace(R) - 1) / 2, -1, 1)) < 1e-7:
            break
        max_d = max(0.2, max_d * 0.8)
    Xb = bB @ T[:3, :3].T + T[:3, 3]
    d, _ = tree.query(Xb)
    return T, float(np.sqrt(np.mean(np.minimum(d, 1.0) ** 2))), float(np.mean(d < 0.05))

def icp_refine_exact(bA, bB, T, stages=((1.5, 30), (0.3, 30), (0.08, 40), (0.03, 40))):
    """Coarse-to-fine trimmed ICP: final stages only use (near-)coincident vertex pairs."""
    tree = cKDTree(bA)
    T = T.copy()
    for max_d, iters in stages:
        for it in range(iters):
            Xb = bB @ T[:3, :3].T + T[:3, 3]
            d, idx = tree.query(Xb)
            ok = d < max_d
            if ok.sum() < 6:
                break
            R, t = kabsch(Xb[ok], bA[idx[ok]])
            dT = np.eye(4); dT[:3, :3] = R; dT[:3, 3] = t
            T = dT @ T
            if np.linalg.norm(t) < 1e-7:
                break
    Xb = bB @ T[:3, :3].T + T[:3, 3]
    d, _ = tree.query(Xb)
    ok = d < 0.03
    return T, float(np.sqrt(np.mean(d[ok] ** 2))) if ok.any() else 9.9, float(ok.mean())
