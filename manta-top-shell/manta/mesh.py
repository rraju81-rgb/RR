"""Lightweight triangle-mesh container used by the builder and exporters."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


@dataclass
class Part:
    """A named surface (or closed body) with per-face material ids."""

    name: str
    vertices: np.ndarray  # (N, 3) float64, design coordinates [mm]
    faces: np.ndarray  # (M, 3) int64
    face_mat: np.ndarray  # (M,) int, index into ``materials``
    materials: list[str] = field(default_factory=list)
    is_shell: bool = True  # part of the top shell (vs. reference context)
    normals: np.ndarray | None = None  # optional smooth per-vertex normals

    def copy(self) -> "Part":
        return Part(self.name, self.vertices.copy(), self.faces.copy(), self.face_mat.copy(),
                    list(self.materials), self.is_shell,
                    None if self.normals is None else self.normals.copy())

    def shading_normals(self):
        return self.vertex_normals() if self.normals is None else self.normals

    @property
    def n_faces(self) -> int:
        return len(self.faces)

    def face_normals(self, normalize=True):
        v = self.vertices
        f = self.faces
        n = np.cross(v[f[:, 1]] - v[f[:, 0]], v[f[:, 2]] - v[f[:, 0]])
        if normalize:
            ln = np.linalg.norm(n, axis=1, keepdims=True)
            n = n / np.maximum(ln, 1e-30)
        return n

    def face_areas(self):
        return 0.5 * np.linalg.norm(self.face_normals(False), axis=1)

    def vertex_normals(self):
        fn = self.face_normals(False)  # area weighted
        vn = np.zeros_like(self.vertices)
        for k in range(3):
            np.add.at(vn, self.faces[:, k], fn)
        ln = np.linalg.norm(vn, axis=1, keepdims=True)
        return vn / np.maximum(ln, 1e-30)

    def material_name(self, i):
        return self.materials[i]


def merge_parts(name: str, parts: list[Part], is_shell=True) -> Part:
    mats: list[str] = []
    V, F, M, N = [], [], [], []
    off = 0
    for p in parts:
        N.append(p.shading_normals())
        remap = []
        for m in p.materials:
            if m not in mats:
                mats.append(m)
            remap.append(mats.index(m))
        V.append(p.vertices)
        F.append(p.faces + off)
        M.append(np.asarray(remap)[p.face_mat])
        off += len(p.vertices)
    return Part(name, np.vstack(V), np.vstack(F), np.concatenate(M), mats, is_shell, np.vstack(N))


def mirror_y(part: Part) -> Part:
    """Return the part mirrored across y = 0 merged with itself (symmetric body)."""
    v = part.vertices
    on_plane = np.abs(v[:, 1]) < 1e-9
    n = len(v)
    mv = v.copy()
    mv[:, 1] *= -1
    # mirrored vertex index: plane vertices map to themselves
    idx = np.arange(n) + n
    idx[on_plane] = np.arange(n)[on_plane]
    mf = idx[part.faces][:, ::-1]
    V = np.vstack([v, mv])
    F = np.vstack([part.faces, mf])
    M = np.concatenate([part.face_mat, part.face_mat])
    n = part.shading_normals()
    mn = n.copy()
    mn[:, 1] *= -1
    N = np.vstack([n, mn])
    # drop unused duplicated plane vertices
    used = np.zeros(len(V), bool)
    used[F.ravel()] = True
    remap = np.cumsum(used) - 1
    return Part(part.name, V[used], remap[F], M, list(part.materials), part.is_shell, N[used])
