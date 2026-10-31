"""Turn the zero-thickness shell surface into a closed, printable solid."""

from __future__ import annotations

import numpy as np

from .mesh import Part


def edge_face_counts(faces):
    e = np.vstack([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]])
    e.sort(axis=1)
    uniq, counts = np.unique(e, axis=0, return_counts=True)
    return uniq, counts


def boundary_edges(faces):
    """Directed boundary edges (as they appear in their single face)."""
    d = np.vstack([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]])
    s = np.sort(d, axis=1)
    _, inv, counts = np.unique(s, axis=0, return_inverse=True, return_counts=True)
    inv = inv.reshape(-1)
    return d[counts[inv] == 1]


def vertex_curvature(part: Part, normals):
    """Max normal-change-per-length over incident edges (1/mm)."""
    f = part.faces
    v = part.vertices
    e = np.vstack([f[:, [0, 1]], f[:, [1, 2]], f[:, [2, 0]]])
    dn = np.linalg.norm(normals[e[:, 0]] - normals[e[:, 1]], axis=1)
    dl = np.maximum(np.linalg.norm(v[e[:, 0]] - v[e[:, 1]], axis=1), 1e-9)
    k = dn / dl
    out = np.zeros(len(v))
    np.maximum.at(out, e[:, 0], k)
    np.maximum.at(out, e[:, 1], k)
    return out


def thicken(part: Part, thickness: float, name=None, min_ratio=0.3) -> Part:
    """Offset the surface inward (against its outward normals) and close the rims.

    Where the surface curves tighter than the requested thickness (convex
    shoulders, trailing-edge lips) the local offset is limited to 85 % of the
    radius of curvature so the inner skin cannot fold through itself.
    """
    n = part.vertex_normals()
    kappa = vertex_curvature(part, n)
    t = np.minimum(thickness, 0.85 / np.maximum(kappa, 1e-9))
    t = np.maximum(t, min_ratio * thickness)
    inner = part.vertices - n * t[:, None]
    nv = len(part.vertices)
    V = np.vstack([part.vertices, inner])
    F_out = part.faces
    F_in = part.faces[:, ::-1] + nv
    be = boundary_edges(part.faces)
    a, b = be[:, 0], be[:, 1]
    # rim: outer edge a->b belongs to an outward face; close with inner b'->a'
    rim = np.vstack([np.column_stack([b, a, a + nv]), np.column_stack([b, a + nv, b + nv])])
    F = np.vstack([F_out, F_in, rim])
    M = np.concatenate([part.face_mat, part.face_mat, np.zeros(len(rim), int)])
    return Part(name or f"{part.name}_solid", V, F, M, list(part.materials), part.is_shell)
