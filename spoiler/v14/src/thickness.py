"""Largest sphere that fits inside a closed mesh (its diameter = the part's greatest thickness): coarse search with a
voxel distance transform, then exact distances to the surface at the best candidates."""
import numpy as np, trimesh
from scipy import ndimage as ndi
from trimesh.ray.ray_pyembree import RayMeshIntersector
from parity import fill_inside

def inside_grid(m, vox):
    lo = m.bounds[0] - 2 * vox; hi = m.bounds[1] + 2 * vox
    shape = np.ceil((hi - lo) / vox).astype(int)
    xs = lo[0] + (np.arange(shape[0]) + 0.5) * vox; zs = lo[2] + (np.arange(shape[2]) + 0.5) * vox
    jy = lambda y: np.clip(np.round((y - lo[1]) / vox - 0.5).astype(int), 0, shape[1])
    return fill_inside(RayMeshIntersector(m), xs, zs, lo[1] - 3.0, shape[1], jy), lo   # robust to rays along edges (parity.py)

def max_thickness(m, vox=0.4, n_cand=3000):
    """(greatest thickness in mm, centre of the largest inscribed sphere)"""
    inside, lo = inside_grid(m, vox)
    D = ndi.distance_transform_edt(inside) * vox
    flat = np.argsort(D.ravel())[-n_cand:]
    P = lo + (np.column_stack(np.unravel_index(flat, D.shape)) + 0.5) * vox
    _, d, _ = trimesh.proximity.closest_point(m, P)
    i = int(np.argmax(d))
    return 2 * float(d[i]), P[i]
