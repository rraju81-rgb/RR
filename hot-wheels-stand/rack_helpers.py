import numpy as np, trimesh
from trimesh.transformations import rotation_matrix


def box(x0, x1, y0, y1, z0, z1):
    return trimesh.creation.box(bounds=[[min(x0, x1), min(y0, y1), min(z0, z1)], [max(x0, x1), max(y0, y1), max(z0, z1)]])


def cylz(z0, z1, x, y, d, sections=36):
    m = trimesh.creation.cylinder(radius=d / 2, height=abs(z1 - z0), sections=sections)
    m.apply_translation([x, y, (z0 + z1) / 2]); return m


def cylx(x0, x1, y, z, d, sections=36):
    m = trimesh.creation.cylinder(radius=d / 2, height=abs(x1 - x0), sections=sections)
    m.apply_transform(rotation_matrix(np.pi / 2, [0, 1, 0])); m.apply_translation([(x0 + x1) / 2, y, z]); return m


def cyly(y0, y1, x, z, d, sections=36):
    m = trimesh.creation.cylinder(radius=d / 2, height=abs(y1 - y0), sections=sections)
    m.apply_transform(rotation_matrix(np.pi / 2, [1, 0, 0])); m.apply_translation([x, (y0 + y1) / 2, z]); return m


def union(ms):
    ms = [m for m in ms if m is not None]
    return trimesh.boolean.union(ms, engine="manifold") if len(ms) > 1 else ms[0]


def diff(a, cuts):
    return trimesh.boolean.difference([a] + list(cuts), engine="manifold")


def hull_of(ms):
    return trimesh.convex.convex_hull(np.vstack([m.vertices for m in ms]))
