"""Two-half compression mould: presses the carbon skins onto the printed rib support at the finished thickness.

The sandwich (bottom skin + rib support + top skin) lies between two mould halves split on its
mid-plane.  Each half has a pocket of the body outline (plus clearance) exactly half the paddle
thickness deep, so when the parting faces meet (hard stop) the cavity is the finished thickness.
Around the pocket are a pinch-off land, a resin overflow groove with vents to the outside, M6 bolt
holes, holes for steel dowel pins, and pry notches to split the cured mould.  Every feature is
symmetric about x = 0, so the same part turned over (180 deg about the y axis) is the top half:
the one STL is printed twice.

Paddle coordinates (mm): the bottom half's parting face is z = 0, its pocket floor z = -T/2 (the
outer face of the bottom skin) and its back z = -(T/2 + floor).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from build123d import Align, Box, Cylinder, Kind, Pos, Rot, extrude, offset

from .cad import outline_face
from .geometry import CONSTRUCTION as C
from .geometry import Outline


@dataclass(frozen=True)
class MouldSpec:
    clearance: float = 0.2       # pocket outline beyond the body outline, so the rib support drops in
    draft: float = 1.0           # deg on the pocket walls, wider at the parting face
    floor: float = 10.0          # plate under the pocket floor
    flange: float = 22.0         # plate edge beyond the pocket edge
    land: float = 2.0            # pinch-off land between the pocket and the overflow groove
    groove_w: float = 2.0        # resin overflow groove; the other half's groove faces it
    groove_d: float = 1.0
    vent_w: float = 2.0          # vents from the groove to the outside
    vent_d: float = 0.6
    bolt_d: float = 6.6          # M6 clearance
    bolt_off: float = 12.0       # bolt line, measured from the pocket edge
    bolt_pitch: float = 60.0     # target spacing along the bolt line
    dowel_d: float = 6.2         # Ø6 x 20 steel dowel pins, 10 mm into each half
    dowel_depth: float = 10.5
    notch_w: float = 14.0        # pry notches on the parting face at the plate edge
    notch_depth: float = 6.0
    notch_h: float = 2.5

    @property
    def depth(self) -> float:
        """Pocket depth of one half: half the finished paddle thickness."""
        return C.thickness / 2

    @property
    def height(self) -> float:
        return self.depth + self.floor


MOULD = MouldSpec()


@dataclass
class Layout:
    """Plan positions (x, y) on the parting face; notches and vents carry their outward normal (nx, ny)."""
    bolts: list[tuple[float, float]] = field(default_factory=list)
    dowels: list[tuple[float, float]] = field(default_factory=list)
    notches: list[tuple[float, float, float, float]] = field(default_factory=list)
    vents: list[tuple[float, float, float, float]] = field(default_factory=list)


def ring(o: Outline, off: float):
    """Closed shapely ring of the body outline offset outwards by `off` (round joins)."""
    from shapely.geometry import Polygon
    return Polygon(o.polyline(0.5)).buffer(off, join_style=1, quad_segs=64).exterior


def layout(o: Outline, m: MouldSpec = MOULD) -> Layout:
    """Bolt, dowel, notch and vent positions, mirrored about x = 0.

    Bolts are spaced evenly along the bolt line from the tip centre to the handle-end centre on the
    right and mirrored.  The other features sit halfway between two bolts: dowels near the upper
    corners and the lower blade, notches on the straight sides, vents at the tip, taper and handle."""
    from shapely.geometry import Point
    body = ring(o, 0.0)
    path = ring(o, m.clearance + m.bolt_off)
    L = path.length
    x0, y0, x1, y1 = path.bounds
    d_top, d_bot = path.project(Point(0.0, y1)), path.project(Point(0.0, y0))
    sgn = 1 if path.interpolate((d_top + 1.0) % L).x > 0 else -1      # walk down the right-hand side
    right = (sgn * (d_bot - d_top)) % L
    n = max(4, round(right / m.bolt_pitch))

    def at(s: float):
        p = path.interpolate((d_top + sgn * s) % L)
        q = body.interpolate(body.project(p))
        nx, ny = p.x - q.x, p.y - q.y
        r = math.hypot(nx, ny)
        return p.x, p.y, nx / r, ny / r

    out = Layout()
    for k in range(n + 1):
        x, y, _, _ = at(k * right / n)
        out.bolts.append((0.0 if k in (0, n) else x, y))
        if 0 < k < n:
            out.bolts.append((-x, y))
    mids = [at((k + 0.5) * right / n) for k in range(n)]

    def pick(frac: float, used: set) -> tuple:
        k = min((k for k in range(n) if k not in used), key=lambda k: abs((k + 0.5) / n - frac))
        used.add(k)
        return mids[k]
    used: set[int] = set()
    for frac in (0.17, 0.62):
        x, y, _, _ = pick(frac, used)
        out.dowels += [(x, y), (-x, y)]
    x, y, nx, ny = pick(0.40, used)
    e = m.flange - m.bolt_off                                       # bolt line -> plate edge
    out.notches += [(x + nx * e, y + ny * e, nx, ny), (-x - nx * e, y + ny * e, -nx, ny)]
    for frac in (0.0, 0.80, 0.97):
        x, y, nx, ny = pick(frac, used)
        out.vents += [(x, y, nx, ny), (-x, y, -nx, ny)]
    return out


def _slot(cx: float, cy: float, nx: float, ny: float, length: float, width: float, z0: float, z1: float):
    """Box `length` along the plan direction (nx, ny), `width` across it, from z0 to z1, centred on (cx, cy)."""
    ang = math.degrees(math.atan2(ny, nx))
    return Pos(cx, cy, z0) * Rot(0, 0, ang) * Box(length, width, z1 - z0, align=(Align.CENTER, Align.CENTER, Align.MIN))


def mould_half(o: Outline, m: MouldSpec = MOULD):
    """The bottom half in paddle coordinates (parting face z = 0, pocket opening upwards)."""
    D, H = m.depth, m.height
    plate = extrude(offset(outline_face(o, -H), m.clearance + m.flange, kind=Kind.ARC), amount=H)
    pocket = extrude(offset(outline_face(o, -D), m.clearance, kind=Kind.ARC), amount=D + 1.0, dir=(0, 0, 1),
                     taper=-m.draft)
    g_in = m.clearance + m.land
    groove = extrude(offset(outline_face(o, -m.groove_d), g_in + m.groove_w, kind=Kind.ARC) -
                     offset(outline_face(o, -m.groove_d), g_in, kind=Kind.ARC), amount=m.groove_d + 1.0)
    half = plate - pocket - groove
    lay = layout(o, m)
    cuts = []
    for x, y in lay.bolts:
        cuts.append(Pos(x, y, -H - 1.0) * Cylinder(m.bolt_d / 2, H + 2.0, align=(Align.CENTER, Align.CENTER, Align.MIN)))
    for x, y in lay.dowels:
        cuts.append(Pos(x, y, -m.dowel_depth) *
                    Cylinder(m.dowel_d / 2, m.dowel_depth + 1.0, align=(Align.CENTER, Align.CENTER, Align.MIN)))
    for x, y, nx, ny in lay.notches:                 # (x, y) on the plate edge
        c = m.notch_depth / 2 - 0.5
        cuts.append(_slot(x - nx * c, y - ny * c, nx, ny, m.notch_depth + 1.0, m.notch_w, -m.notch_h, 1.0))
    for x, y, nx, ny in lay.vents:                   # (x, y) on the bolt line: run from the groove to the edge
        r0 = -(m.bolt_off - m.land - m.groove_w / 2)
        r1 = m.flange - m.bolt_off + 1.0
        c = (r0 + r1) / 2
        cuts.append(_slot(x + nx * c, y + ny * c, nx, ny, r1 - r0, m.vent_w, -m.vent_d, 1.0))
    for c in cuts:
        half = half - c
    return half


def top_half(bottom):
    """The same part turned over about the y axis: the top half in paddle coordinates."""
    return Rot(0, 180, 0) * bottom


def dowel_pins(o: Outline, m: MouldSpec = MOULD, length: float = 20.0):
    """Ø6 x 20 steel dowel pins standing in the bottom half (for the renders)."""
    pins = None
    for x, y in layout(o, m).dowels:
        p = Pos(x, y, -m.dowel_depth) * Cylinder(3.0, length, align=(Align.CENTER, Align.CENTER, Align.MIN))
        pins = p if pins is None else pins + p
    return pins
