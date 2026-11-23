"""Largest sphere that fits inside a closed mesh (its diameter = the part's greatest thickness): coarse search with a
voxel distance transform, then exact distances to the surface at the best candidates."""
import numpy as np, trimesh
from scipy import ndimage as ndi
from trimesh.ray.ray_pyembree import RayMeshIntersector

def inside_grid(m, vox):
    lo = m.bounds[0] - 2 * vox; hi = m.bounds[1] + 2 * vox
    shape = np.ceil((hi - lo) / vox).astype(int)
    xs = lo[0] + (np.arange(shape[0]) + 0.5) * vox; zs = lo[2] + (np.arange(shape[2]) + 0.5) * vox
    X, Z = np.meshgrid(xs, zs, indexing='ij')
    O = np.column_stack([X.ravel(), np.full(X.size, lo[1] - 3.0), Z.ravel()])
    loc, ir, it = RayMeshIntersector(m).intersects_location(O, np.tile([0, 1.0, 0], (len(O), 1)), multiple_hits=True)
    inside = np.zeros(shape, bool)
    order = np.lexsort((loc[:, 1], ir)); ir, ys = ir[order], loc[order, 1]
    st = np.flatnonzero(np.r_[True, ir[1:] != ir[:-1]]); en = np.r_[st[1:], len(ir)]
    jy = lambda y: np.clip(np.round((y - lo[1]) / vox - 0.5).astype(int), 0, shape[1])
    for s, e in zip(st, en):
        if (e - s) % 2: continue
        i, k = np.unravel_index(ir[s], X.shape)
        for a, b in zip(ys[s:e:2], ys[s + 1:e:2]): inside[i, jy(a):jy(b), k] = True
    return inside, lo

def max_thickness(m, vox=0.4, n_cand=3000):
    """(greatest thickness in mm, centre of the largest inscribed sphere)"""
    inside, lo = inside_grid(m, vox)
    D = ndi.distance_transform_edt(inside) * vox
    flat = np.argsort(D.ravel())[-n_cand:]
    P = lo + (np.column_stack(np.unravel_index(flat, D.shape)) + 0.5) * vox
    _, d, _ = trimesh.proximity.closest_point(m, P)
    i = int(np.argmax(d))
    return 2 * float(d[i]), P[i]
