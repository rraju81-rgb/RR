"""
A very small sheet-metal modeller on top of CadQuery.

A part is a tree of flat `Panel`s joined by `Bend`s. The same tree is evaluated
twice:

    fold()    -> 3D solids (panels + bend arcs) in the as-formed state
    unfold()  -> 2D faces  (panels + bend-allowance strips) = the laser blank

Because both come from one definition, the blank and the folded part cannot
drift apart.

Conventions
-----------
* Every panel has a local 2D frame (p, q). In 3D the frame is (O, eP, eQ, eN)
  with eP x eQ = eN. The sheet occupies 0..t along eN, so the face at n = 0 is
  the panel's *reference face*.
* A child is attached along a straight edge A->B given in the PARENT's local
  coordinates, with the outside of the parent to the LEFT of A->B.
  In the child's own frame that edge is the p-axis (q = 0) and the child grows
  towards +q.
* direction "up"   folds the child towards -eN (reference faces end up inside
                   the bend, radius r on the reference face),
  direction "down" folds towards +eN (reference face on the outside).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
import cadquery as cq
from OCP.BRepPrimAPI import BRepPrimAPI_MakeRevol
from OCP.gp import gp_Ax1, gp_Dir, gp_Pnt


# ----------------------------------------------------------------------------- 2D helpers
def unit(v):
    v = np.asarray(v, float)
    return v / np.linalg.norm(v)


def rot90(v):
    """Rotate a 2D vector +90 degrees (counter-clockwise)."""
    return np.array([-v[1], v[0]], float)


def rodrigues(v, axis, ang):
    axis = unit(axis)
    v = np.asarray(v, float)
    return v * math.cos(ang) + np.cross(axis, v) * math.sin(ang) + axis * np.dot(axis, v) * (1 - math.cos(ang))


def filleted_outline(pts, radii=None):
    """Closed polygon with optional per-vertex fillets.

    Returns a list of segments, each ('line', p0, p1) or ('arc', p0, pm, p1),
    chained head to tail.
    """
    n = len(pts)
    P = [np.asarray(p, float) for p in pts]
    radii = list(radii) if radii is not None else [0.0] * n
    corners = []
    used = [0.0] * n  # tangent length consumed at each vertex
    for i in range(n):
        V, A, B = P[i], P[i - 1], P[(i + 1) % n]
        rr = radii[i]
        if rr <= 1e-9:
            corners.append((V, None, V))
            continue
        a, b = unit(A - V), unit(B - V)
        ang = math.acos(float(np.clip(np.dot(a, b), -1.0, 1.0)))
        if ang > math.pi - 1e-6:
            corners.append((V, None, V))  # straight through, nothing to fillet
            continue
        half = ang / 2
        d = rr / math.tan(half)
        used[i] = d
        bis = unit(a + b)
        C = V + bis * (rr / math.sin(half))
        corners.append((V + a * d, C - bis * rr, V + b * d))
    for i in range(n):
        edge = np.linalg.norm(P[(i + 1) % n] - P[i])
        if used[i] + used[(i + 1) % n] > edge + 1e-6:
            raise ValueError(
                f"fillets at vertices {i} and {(i + 1) % n} need {used[i] + used[(i + 1) % n]:.3f} mm "
                f"but the edge is only {edge:.3f} mm long"
            )
    segs = []
    for i in range(n):
        t1, m, t2 = corners[i]
        if m is not None:
            segs.append(("arc", t1, m, t2))
        nxt = corners[(i + 1) % n][0]
        if np.linalg.norm(nxt - t2) > 1e-7:
            segs.append(("line", t2, nxt))
    return segs


def obround(center, length, width, angle_deg):
    """Slot with full-round ends. `length` is overall, tip to tip."""
    c = np.asarray(center, float)
    a = math.radians(angle_deg)
    d = np.array([math.cos(a), math.sin(a)])
    nrm = rot90(d)
    h = max((length - width) / 2.0, 0.0)
    w2 = width / 2.0
    if h < 1e-6:  # degenerate -> circle, as two half arcs
        p0, p1 = c - d * w2, c + d * w2
        return [("arc", p0, c - nrm * w2, p1), ("arc", p1, c + nrm * w2, p0)]
    p0, p1 = c - d * h - nrm * w2, c + d * h - nrm * w2
    p2, p3 = c + d * h + nrm * w2, c - d * h + nrm * w2
    return [
        ("line", p0, p1),
        ("arc", p1, c + d * (h + w2), p2),
        ("line", p2, p3),
        ("arc", p3, c - d * (h + w2), p0),
    ]


def wire_from_segs(segs):
    edges = []
    for s in segs:
        if s[0] == "line":
            edges.append(cq.Edge.makeLine(cq.Vector(s[1][0], s[1][1], 0), cq.Vector(s[2][0], s[2][1], 0)))
        else:
            edges.append(
                cq.Edge.makeThreePointArc(
                    cq.Vector(s[1][0], s[1][1], 0), cq.Vector(s[2][0], s[2][1], 0), cq.Vector(s[3][0], s[3][1], 0)
                )
            )
    return cq.Wire.assembleEdges(edges)


def segs_area(segs, samples=24):
    """Signed area enclosed by a segment chain (arcs sampled). Used for self-checks."""
    pts = segs_points(segs, samples)
    area = 0.0
    for i in range(len(pts)):
        x0, y0 = pts[i]
        x1, y1 = pts[(i + 1) % len(pts)]
        area += x0 * y1 - x1 * y0
    return area / 2.0


def segs_points(segs, samples=24):
    """Points round a closed segment chain, arcs sampled with `samples` steps."""
    pts = []
    for s in segs:
        if s[0] == "line":
            pts.append(s[1])
        else:
            p0, pm, p1 = (np.asarray(x, float) for x in s[1:])
            # circle through three points
            ax, ay = p0
            bx, by = pm
            cx, cy = p1
            dd = 2 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
            ux = ((ax**2 + ay**2) * (by - cy) + (bx**2 + by**2) * (cy - ay) + (cx**2 + cy**2) * (ay - by)) / dd
            uy = ((ax**2 + ay**2) * (cx - bx) + (bx**2 + by**2) * (ax - cx) + (cx**2 + cy**2) * (bx - ax)) / dd
            c = np.array([ux, uy])
            a0 = math.atan2(*(p0 - c)[::-1])
            am = math.atan2(*(pm - c)[::-1])
            a1 = math.atan2(*(p1 - c)[::-1])
            ccw = ((am - a0) % (2 * math.pi)) < ((a1 - a0) % (2 * math.pi))
            sweep = (a1 - a0) % (2 * math.pi) if ccw else -((a0 - a1) % (2 * math.pi))
            rad = np.linalg.norm(p0 - c)
            for k in range(samples):
                a = a0 + sweep * k / samples
                pts.append(c + rad * np.array([math.cos(a), math.sin(a)]))
    return pts


# ----------------------------------------------------------------------------- tree
@dataclass
class Bend:
    A: tuple
    B: tuple
    angle: float          # degrees, 0 = flat
    direction: str        # "up" | "down"
    child: "Panel"
    label: str

    @property
    def length(self):
        return float(np.linalg.norm(np.asarray(self.B, float) - np.asarray(self.A, float)))


@dataclass
class Panel:
    name: str
    pts: list
    radii: list | None = None
    cutouts: list = field(default_factory=list)   # each: list of segments (closed)
    children: list = field(default_factory=list)

    def attach(self, A, B, angle, direction, child, label):
        assert direction in ("up", "down")
        self.children.append(Bend(tuple(A), tuple(B), float(angle), direction, child, label))
        return child

    def outline(self):
        return filleted_outline(self.pts, self.radii)

    def face(self):
        outer = wire_from_segs(self.outline())
        inner = [wire_from_segs(c) for c in self.cutouts]
        return cq.Face.makeFromWires(outer, inner)

    def area(self):
        return abs(segs_area(self.outline())) - sum(abs(segs_area(c)) for c in self.cutouts)

    def walk(self):
        yield self
        for b in self.children:
            yield from b.child.walk()

    def bends(self):
        for b in self.children:
            yield b
            yield from b.child.bends()


# ----------------------------------------------------------------------------- fold (3D)
def fold(panel: Panel, frame, t: float, r: float, out=None, frames=None):
    """Return [(name, cq.Solid)] for the formed part. `frames` collects each panel's 3D frame."""
    if out is None:
        out = []
    if frames is None:
        frames = {}
    O, eP, eQ, eN = (np.asarray(v, float) for v in frame)
    frames[panel.name] = (O, eP, eQ, eN)
    plane = cq.Plane(origin=tuple(O), xDir=tuple(eP), normal=tuple(eN))
    face3d = panel.face().located(cq.Location(plane))
    out.append((panel.name, cq.Solid.extrudeLinear(face3d, cq.Vector(*(eN * t)))))

    for b in panel.children:
        A, B = np.asarray(b.A, float), np.asarray(b.B, float)
        e2 = unit(B - A)
        d2 = rot90(e2)
        A3 = O + A[0] * eP + A[1] * eQ
        B3 = O + B[0] * eP + B[1] * eQ
        e3 = e2[0] * eP + e2[1] * eQ
        d3 = d2[0] * eP + d2[1] * eQ
        th = math.radians(b.angle)
        if b.direction == "up":
            axis, C = -e3, A3 - r * eN
        else:
            axis, C = e3, A3 + (t + r) * eN

        if th > 1e-9:
            rect = cq.Wire.makePolygon(
                [cq.Vector(*A3), cq.Vector(*B3), cq.Vector(*(B3 + t * eN)), cq.Vector(*(A3 + t * eN))], close=True
            )
            rev = BRepPrimAPI_MakeRevol(
                cq.Face.makeFromWires(rect).wrapped, gp_Ax1(gp_Pnt(*C), gp_Dir(*axis)), th
            ).Shape()
            out.append((b.label, cq.Shape.cast(rev)))

        def rot(v, axis=axis, th=th):
            return rodrigues(v, axis, th)

        child_frame = (C + rot(A3 - C), e3, rot(d3), rot(eN))
        fold(b.child, child_frame, t, r, out, frames)
    return out, frames


# ----------------------------------------------------------------------------- unfold (2D)
def unfold(panel: Panel, bend_allowance, M=None, T=None, faces=None, lines=None, placed=None):
    """Lay the tree flat.

    bend_allowance(angle_deg) -> strip width.
    Returns (faces, bend_lines, placed) where
      faces      = [(name, cq.Face)] panels and bend strips in blank coordinates
      bend_lines = [dict(label, a, b, angle, direction, tangents=(..))]
      placed     = {panel name: (M, T)} so callers can map local -> blank coords
    """
    if M is None:
        M, T = np.eye(2), np.zeros(2)
    if faces is None:
        faces, lines, placed = [], [], {}
    placed[panel.name] = (M.copy(), T.copy())
    ang = math.degrees(math.atan2(M[1, 0], M[0, 0]))
    faces.append((panel.name, panel.face().moved(cq.Location(cq.Vector(T[0], T[1], 0), cq.Vector(0, 0, 1), ang))))

    for b in panel.children:
        A, B = np.asarray(b.A, float), np.asarray(b.B, float)
        e2 = unit(B - A)
        d2 = rot90(e2)
        Af, Bf = M @ A + T, M @ B + T
        ef, df = M @ e2, M @ d2
        ba = bend_allowance(b.angle)
        if ba > 1e-9:
            strip = cq.Wire.makePolygon(
                [cq.Vector(*Af, 0), cq.Vector(*Bf, 0), cq.Vector(*(Bf + ba * df), 0), cq.Vector(*(Af + ba * df), 0)],
                close=True,
            )
            faces.append((b.label, cq.Face.makeFromWires(strip)))
        lines.append(
            dict(
                label=b.label,
                a=Af + ba / 2 * df,
                b=Bf + ba / 2 * df,
                angle=b.angle,
                direction=b.direction,
                allowance=ba,
                tangents=((Af, Bf), (Af + ba * df, Bf + ba * df)),
            )
        )
        unfold(b.child, bend_allowance, np.column_stack([ef, df]), Af + ba * df, faces, lines, placed)
    return faces, lines, placed


def fuse_all(shapes):
    """Boolean-union a list of shapes and merge co-planar faces."""
    acc = shapes[0]
    for s in shapes[1:]:
        acc = acc.fuse(s)
    return acc.clean()
