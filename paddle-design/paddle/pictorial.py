"""Orthographic pictorial (isometric / 3-4 view) of the extruded paddle profile.

The paddle is the outline extruded through its thickness (z = -t/2 .. +t/2).
`project` returns painter-ordered primitives with hidden surfaces removed:
visible side walls (far to near) and the visible face on top.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from .geometry import Outline, Pt

Vec = tuple[float, float, float]


def _norm(v: Vec) -> Vec:
    n = math.sqrt(sum(c * c for c in v))
    return (v[0] / n, v[1] / n, v[2] / n)


def _dot(a: Vec, b: Vec) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _cross(a: Vec, b: Vec) -> Vec:
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def frame_from(view_dir: Vec, up: Vec = (0.0, 0.0, 1.0)) -> tuple[Vec, Vec, Vec]:
    """Screen basis (right, up, towards-viewer) for a viewer looking along -view_dir."""
    w = _norm(view_dir)
    u = _norm(_cross(up, w))
    v = _cross(w, u)
    return u, v, w


# paddle lying face-up, seen from front-right-above: tip to the upper right, butt to the lower left
ISOMETRIC = frame_from((1.0, -1.0, 1.0), up=(0.0, 0.0, 1.0))


def three_quarter(yaw: float = -32.0, pitch: float = 18.0, roll: float = 0.0) -> tuple[Vec, Vec, Vec]:
    """Paddle standing up (y vertical), turned by `yaw` and seen from `pitch` above."""
    cy, sy = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    cp, sp = math.cos(math.radians(pitch)), math.sin(math.radians(pitch))
    # rows of R = Rx(pitch) . Ry(yaw)
    u = (cy, 0.0, sy)
    v = (sy * sp, cp, -cy * sp)
    w = (-sy * cp, sp, cy * cp)
    if roll:
        cr, sr = math.cos(math.radians(roll)), math.sin(math.radians(roll))
        u, v = (tuple(cr * a - sr * b for a, b in zip(u, v)), tuple(sr * a + cr * b for a, b in zip(u, v)))
    return u, v, w


@dataclass
class Wall:
    quad: list[Pt]          # projected (u, v), v up
    depth: float
    normal: Vec
    back_edge: tuple[Pt, Pt]
    silhouette: list[tuple[Pt, Pt]]


@dataclass
class Pictorial:
    walls: list[Wall]       # visible walls, far -> near
    face: list[Pt]          # visible face outline (projected)
    face_normal: Vec
    bbox: tuple[float, float, float, float]


def project(o: Outline, frame: tuple[Vec, Vec, Vec], step: float = 2.0) -> Pictorial:
    U, V, W = frame
    t = o.spec.thickness / 2
    ring = o.polyline(step)
    n = len(ring)

    def pr(x: float, y: float, z: float) -> tuple[float, float, float]:
        p = (x, y, z)
        return _dot(U, p), _dot(V, p), _dot(W, p)

    # which face looks at the viewer?
    zf = t if W[2] > 0 else -t
    face_normal = (0.0, 0.0, 1.0 if zf > 0 else -1.0)
    front = [pr(x, y, zf) for x, y in ring]
    back = [pr(x, y, -zf) for x, y in ring]

    vis = []
    normals = []
    for i in range(n):
        (x0, y0), (x1, y1) = ring[i], ring[(i + 1) % n]
        nx, ny = y1 - y0, -(x1 - x0)                 # outward normal of a CCW loop
        L = math.hypot(nx, ny) or 1.0
        nrm = (nx / L, ny / L, 0.0)
        normals.append(nrm)
        vis.append(_dot(nrm, W) > 1e-9)

    walls: list[Wall] = []
    for i in range(n):
        if not vis[i]:
            continue
        j = (i + 1) % n
        q = [front[i][:2], front[j][:2], back[j][:2], back[i][:2]]
        depth = (front[i][2] + front[j][2] + back[i][2] + back[j][2]) / 4
        sil = []
        if not vis[i - 1]:
            sil.append((front[i][:2], back[i][:2]))
        if not vis[j]:
            sil.append((front[j][:2], back[j][:2]))
        walls.append(Wall(q, depth, normals[i], (back[i][:2], back[j][:2]), sil))
    walls.sort(key=lambda w: w.depth)
    pts = [p[:2] for p in front + back]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return Pictorial(walls, [p[:2] for p in front], face_normal, (min(xs), min(ys), max(xs), max(ys)))
