"""Match part 'ends' (tabbed or flat cut faces) and score them, incl. skin-continuity across the cut."""
import os, sys, pickle, itertools, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from faces import register2d, mirror_poly, transform_from_match, iou_after
from ends import part_ends
from shapely import affinity

def end_faces(e):
    """Return (outer_face, recessed_face_or_None). Levels relative to outermost along n."""
    dmax = max(f['d'] for f in e['faces'])
    outer = [f for f in e['faces'] if dmax - f['d'] < 0.6]
    rec = [f for f in e['faces'] if 17.5 < dmax - f['d'] < 20.5]
    o = max(outer, key=lambda f: f['area']) if outer else None
    r = max(rec, key=lambda f: f['area']) if rec else None
    return o, r

def apply(T, X):
    return X @ T[:3, :3].T + T[:3, 3]

def face_in_plane_poly(fB, T, fA):
    """Project face fB (of part B) transformed by T into fA's plane frame -> shapely poly (A frame coords)."""
    from shapely.geometry import Polygon
    from shapely.ops import unary_union
    tris = fB['tris_world']
    tw = apply(T, tris.reshape(-1, 3)).reshape(-1, 3, 3) - fA['o']
    polys = [Polygon(np.c_[t @ fA['u'], t @ fA['v']]).buffer(1e-4) for t in tw]
    return unary_union(polys).buffer(-1e-4), float(np.abs((tw @ fA['n'])).mean())

def boundary_skin(m, faces):
    """For the joint face set: boundary edge midpoints and normal of the adjacent (non-joint) face."""
    S = np.zeros(len(m.faces), bool); S[faces] = True
    adj = m.face_adjacency; e = m.face_adjacency_edges
    inS = S[adj]
    bd = np.where(inS[:, 0] ^ inS[:, 1])[0]
    other = np.where(inS[bd, 0], adj[bd, 1], adj[bd, 0])
    mid = m.vertices[e[bd]].mean(1)
    return mid, m.face_normals[other]

def skin_continuity(mA, fA_all, mB, fB_all, T):
    """Mean angle (deg) between skin normals of A and B at matching joint-boundary points."""
    pa, na = boundary_skin(mA, fA_all)
    pb, nb = boundary_skin(mB, fB_all)
    pb = apply(T, pb); nb = nb @ T[:3, :3].T
    from scipy.spatial import cKDTree
    tr = cKDTree(pb)
    dist, idx = tr.query(pa)
    ok = dist < 1.0
    if ok.sum() < 5:
        return 90.0, 0.0
    # only skin faces (not tab walls): normals roughly perpendicular to joint normal
    ang = np.degrees(np.arccos(np.clip(np.einsum('ij,ij->i', na[ok], nb[idx[ok]]), -1, 1)))
    return float(np.median(ang)), float(ok.mean())
