"""Two-half compression mould that forms the rib support itself, in carbon fibre.

The cavity between the two halves is the rib support: its closed frame, the solid handle and throat
zone and the wave walls.  Each half carries the wave as a row of teeth, the negative of the flutes
that open on its side: the bottom half (the tray) has the teeth of the bottom flutes standing in a
pocket of the paddle outline, the top half (the lid) has the teeth of the top flutes hanging from its
underside.  Closing the lid slides its teeth between the tray's teeth; the gaps between them are the
wave walls.  Chopped carbon fibre and epoxy ("forged carbon") laid in the tray flows into the frame,
the solid zone and the walls, and the lid seating on the tray rim (hard stop) sets the core height.

Every flute is longest where it opens and every wall is a function of x alone, so both halves pull
straight off the part.  Around the pocket: a pinch-off land, a resin overflow groove with vents,
M6 bolt holes, dowel-pin holes, pry notches; ejector holes through the tray floor.

Paddle coordinates (mm): the rib support fills z = -h .. +h (h = core height / 2); the tray runs from
z = -h - floor up to its rim at z = +h, the lid from z = +h to +h + lid with its teeth below.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from build123d import Align, Box, Cylinder, Kind, Pos, Rot, extrude, offset

from .cad import flute_voids, outline_face
from .geometry import CONSTRUCTION as C
from .geometry import Outline


@dataclass(frozen=True)
class MouldSpec:
    floor: float = 10.0          # tray material under the pocket floor
    lid: float = 10.0            # lid plate above the rim
    flange: float = 22.0         # plate edge beyond the pocket edge
    land: float = 2.0            # pinch-off land between the pocket and the overflow groove
    groove_w: float = 2.0        # resin overflow groove in the tray rim
    groove_d: float = 1.5
    vent_w: float = 2.0          # vents from the groove to the outside
    vent_d: float = 0.8
    bolt_d: float = 6.6          # M6 clearance
    bolt_off: float = 12.0       # bolt line, measured from the pocket edge
    bolt_pitch: float = 60.0     # target spacing along the bolt line
    dowel_d: float = 6.2         # Ø6 x 16 steel dowel pins, 8 mm into each half
    dowel_depth: float = 8.5
    notch_w: float = 14.0        # pry notches either side of the parting face, at the plate edge
    notch_depth: float = 6.0
    notch_h: float = 2.5
    ejector_d: float = 4.2       # through the tray floor into the solid zone and the tip frame

    @property
    def h(self) -> float:
        """Half the core height: the rib support fills z = -h .. +h."""
        return C.core_t / 2

    @property
    def tray_height(self) -> float:
        return self.floor + C.core_t

    @property
    def height(self) -> float:
        """Both halves closed."""
        return self.floor + C.core_t + self.lid


MOULD = MouldSpec()


@dataclass
class Layout:
    """Plan positions (x, y); notches and vents carry their outward normal (nx, ny)."""
    bolts: list[tuple[float, float]] = field(default_factory=list)
    dowels: list[tuple[float, float]] = field(default_factory=list)
    notches: list[tuple[float, float, float, float]] = field(default_factory=list)
    vents: list[tuple[float, float, float, float]] = field(default_factory=list)
    ejectors: list[tuple[float, float]] = field(default_factory=list)


def ring(o: Outline, off: float):
    """Closed shapely ring of the body outline offset outwards by `off` (round joins)."""
    from shapely.geometry import Polygon
    return Polygon(o.polyline(0.5)).buffer(off, join_style=1, quad_segs=64).exterior


def layout(o: Outline, m: MouldSpec = MOULD) -> Layout:
    """Bolt, dowel, notch, vent and ejector positions, mirrored about x = 0.

    Bolts are spaced evenly along the bolt line from the tip centre to the handle-end centre on the
    right and mirrored.  The other flange features sit halfway between two bolts: dowels near the upper
    corners and the lower blade, notches on the straight sides, vents at the tip, taper and handle."""
    from shapely.geometry import Point
    body = ring(o, 0.0)
    path = ring(o, m.bolt_off)
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
    sp = o.spec
    out.ejectors = [(0.0, y) for y in (sp.cap_length + 25.0, 75.0, C.solid_to - 25.0)] + \
                   [(0.0, sp.length - C.frame_w / 2)]
    return out


def _slot(cx: float, cy: float, nx: float, ny: float, length: float, width: float, z0: float, z1: float):
    """Box `length` along the plan direction (nx, ny), `width` across it, from z0 to z1, centred on (cx, cy)."""
    ang = math.degrees(math.atan2(ny, nx))
    return Pos(cx, cy, z0) * Rot(0, 0, ang) * Box(length, width, z1 - z0, align=(Align.CENTER, Align.CENTER, Align.MIN))


def _cyl(x: float, y: float, d: float, z0: float, z1: float):
    return Pos(x, y, z0) * Cylinder(d / 2, z1 - z0, align=(Align.CENTER, Align.CENTER, Align.MIN))


def mould_halves(o: Outline, m: MouldSpec = MOULD):
    """(tray, lid) in paddle coordinates, closed on the part: tray rim and lid underside at z = +h."""
    h = m.h
    voids = flute_voids(o)
    plate = offset(outline_face(o, 0.0), m.flange, kind=Kind.ARC)
    tray = extrude(plate.moved(Pos(0, 0, -h - m.floor)), amount=m.floor + 2 * h)
    tray = tray - extrude(outline_face(o, -h), amount=2 * h + 1.0) + voids[-1]        # pocket + bottom teeth
    lid = extrude(plate.moved(Pos(0, 0, h)), amount=m.lid) + voids[+1]                  # lid + top teeth
    groove = extrude(offset(outline_face(o, h - m.groove_d), m.land + m.groove_w, kind=Kind.ARC) -
                     offset(outline_face(o, h - m.groove_d), m.land, kind=Kind.ARC), amount=m.groove_d + 1.0)
    tray = tray - groove
    lay = layout(o, m)
    z_lo, z_hi = -h - m.floor - 1.0, h + m.lid + 1.0
    for x, y in lay.bolts:
        tray, lid = tray - _cyl(x, y, m.bolt_d, z_lo, z_hi), lid - _cyl(x, y, m.bolt_d, z_lo, z_hi)
    for x, y in lay.dowels:
        tray = tray - _cyl(x, y, m.dowel_d, h - m.dowel_depth, h + 1.0)
        lid = lid - _cyl(x, y, m.dowel_d, h - 1.0, h + m.dowel_depth)
    for x, y, nx, ny in lay.notches:                 # (x, y) on the plate edge
        c = m.notch_depth / 2 - 0.5
        tray = tray - _slot(x - nx * c, y - ny * c, nx, ny, m.notch_depth + 1.0, m.notch_w, h - m.notch_h, h + 1.0)
        lid = lid - _slot(x - nx * c, y - ny * c, nx, ny, m.notch_depth + 1.0, m.notch_w, h - 1.0, h + m.notch_h)
    for x, y, nx, ny in lay.vents:                   # (x, y) on the bolt line: from the groove to the edge
        r0 = -(m.bolt_off - m.land - m.groove_w / 2)
        r1 = m.flange - m.bolt_off + 1.0
        c = (r0 + r1) / 2
        tray = tray - _slot(x + nx * c, y + ny * c, nx, ny, r1 - r0, m.vent_w, h - m.vent_d, h + 1.0)
    for x, y in lay.ejectors:
        tray = tray - _cyl(x, y, m.ejector_d, z_lo, -h + 0.01)
    return tray, lid


def print_pose(half, top: bool, m: MouldSpec = MOULD):
    """A half in its print orientation: back face on the bed (z = 0), teeth pointing up."""
    if top:
        return Pos(0, 0, m.h + m.lid) * Rot(0, 180, 0) * half
    return Pos(0, 0, m.h + m.floor) * half


def dowel_pins(o: Outline, m: MouldSpec = MOULD, length: float = 16.0):
    """Ø6 x 16 steel dowel pins standing in the tray rim (for the renders)."""
    pins = None
    for x, y in layout(o, m).dowels:
        p = _cyl(x, y, 6.0, m.h - length / 2, m.h + length / 2)
        pins = p if pins is None else pins + p
    return pins
