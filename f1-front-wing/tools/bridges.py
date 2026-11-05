"""Small webs that tie neighbouring wing elements together so the wing prints as one solid."""
import numpy as np, trimesh
from scipy.spatial import cKDTree, ConvexHull

def plane_frame(n):
    ref = np.array([0, 0, 1.0]) if abs(n[2]) < 0.9 else np.array([1.0, 0, 0])
    u = np.cross(n, ref); u /= np.linalg.norm(u); v = np.cross(n, u)
    return u, v

def bridge(m1, m2, n, origin, thickness=5.0, patch=6.0):
    """Web between meshes m1, m2 in the plane through `origin` with normal n (span direction)."""
    s1 = m1.section(plane_origin=origin, plane_normal=n)
    s2 = m2.section(plane_origin=origin, plane_normal=n)
    if s1 is None or s2 is None:
        return None, None
    u, v = plane_frame(n)
    P1 = np.vstack(s1.discrete); P2 = np.vstack(s2.discrete)
    # densify outlines
    def dense(P):
        out = []
        for a, b in zip(P[:-1], P[1:]):
            k = max(1, int(np.linalg.norm(b - a) / 0.3))
            out.append(a + (b - a) * np.linspace(0, 1, k, endpoint=False)[:, None])
        return np.vstack(out)
    P1 = dense(P1); P2 = dense(P2)
    d, idx = cKDTree(P2).query(P1)
    i = np.argmin(d); p1, p2 = P1[i], P2[idx[i]]
    loc = np.vstack([P1[np.linalg.norm(P1 - p1, axis=1) < patch], P2[np.linalg.norm(P2 - p2, axis=1) < patch]])
    q = np.c_[(loc - origin) @ u, (loc - origin) @ v]
    hull = q[ConvexHull(q).vertices]
    ring = origin + hull[:, :1] * u + hull[:, 1:] * v
    pts = np.vstack([ring - n * thickness / 2, ring + n * thickness / 2])
    return trimesh.convex.convex_hull(pts), float(d[i])
