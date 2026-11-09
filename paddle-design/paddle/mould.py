"""Two-half compression mould that forms the rib support itself, in carbon fibre.

The cavity between the two halves is the rib support: its closed frame, the solid handle and throat
zone and the wave walls.  Each half carries the wave as a row of teeth, the negative of the flutes
that open on its side: the bottom half (the tray) has the teeth of the bottom flutes standing in a
pocket of the paddle outline, the top half (the lid) has the teeth of the top flutes hanging from a
plug, a raised copy of the paddle outline on its underside.  Closing the lid slides the plug into the
pocket, which aligns the halves, and its teeth between the tray's teeth; the gaps between them are the
wave walls.  Chopped carbon fibre and epoxy ("forged carbon") laid in the tray flows into the frame,
the solid zone and the walls.  The pocket is deeper than the part by the plug height, so the plug
presses the charge down; the lid flange seating on the tray rim (hard stop) leaves the plug face at
the core height.

Every flute is longest where it opens and every wall is a function of x alone, so both halves pull
straight off the part.  Around the pocket: a lead-in chamfer, a land, a resin overflow groove with
vents, M6 bolt holes and pry notches.

Paddle coordinates (mm): the rib support fills z = -h .. +h (h = core height / 2); the tray runs from
z = -h - floor up to its rim at z = +h + plug, the lid's plug from z = +h to the rim, its flange from
the rim to rim + lid, and its teeth below z = +h.
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
    floor: float = 5.0           # tray material under the pocket floor (pressed flat on a platen)
    lid: float = 10.0            # lid flange (plate) above the rim
    plug: float = 2.0            # lid plug height = how far the pocket runs above the part
    clearance: float = 0.2       # sliding gap per side between the plug and the pocket wall
    lead_in: float = 0.5         # 45 deg chamfer on the pocket's top edge, guides the plug in
    flange: float = 22.0         # plate edge beyond the pocket edge
    land: float = 2.0            # flat between the pocket edge and the overflow groove
    groove_w: float = 2.0        # resin overflow groove in the tray rim
    groove_d: float = 1.5
    vent_w: float = 2.0          # vents from the groove to the outside
    vent_d: float = 0.8
    bolt_d: float = 6.6          # M6 clearance
    bolt_off: float = 12.0       # bolt line, measured from the pocket edge
    bolt_pitch: float = 60.0     # target spacing along the bolt line
    notch_w: float = 14.0        # pry notches either side of the parting face, at the plate edge
    notch_depth: float = 6.0
    notch_h: float = 2.5

    @property
    def h(self) -> float:
        """Half the core height: the rib support fills z = -h .. +h."""
        return C.core_t / 2

    @property
    def rim(self) -> float:
        """z of the parting face: the tray rim and the underside of the lid flange."""
        return self.h + self.plug

    @property
    def tray_height(self) -> float:
        return self.floor + C.core_t + self.plug

    @property
    def lid_height(self) -> float:
        """Lid flange + plug (the teeth add up to the core height below that)."""
        return self.lid + self.plug

    @property
    def height(self) -> float:
        """Both halves closed."""
        return self.floor + C.core_t + self.plug + self.lid


MOULD = MouldSpec()


@dataclass
class Layout:
    """Plan positions (x, y); notches and vents carry their outward normal (nx, ny)."""
    bolts: list[tuple[float, float]] = field(default_factory=list)
    notches: list[tuple[float, float, float, float]] = field(default_factory=list)
    vents: list[tuple[float, float, float, float]] = field(default_factory=list)


def ring(o: Outline, off: float):
    """Closed shapely ring of the body outline offset outwards by `off` (round joins)."""
    from shapely.geometry import Polygon
    return Polygon(o.polyline(0.5)).buffer(off, join_style=1, quad_segs=64).exterior


def layout(o: Outline, m: MouldSpec = MOULD) -> Layout:
    """Bolt, notch and vent positions, mirrored about x = 0.

    Bolts are spaced evenly along the bolt line from the tip centre to the handle-end centre on the
    right and mirrored.  The other flange features sit halfway between two bolts: notches on the
    straight sides, vents at the tip, taper and handle.  The plug aligns the halves, so there are no
    dowels, and the part is lifted out by hand, so there are no ejector holes."""
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


def _cyl(x: float, y: float, d: float, z0: float, z1: float):
    return Pos(x, y, z0) * Cylinder(d / 2, z1 - z0, align=(Align.CENTER, Align.CENTER, Align.MIN))


def mould_halves(o: Outline, m: MouldSpec = MOULD):
    """(tray, lid) in paddle coordinates, closed on the part: plug face at z = +h, flange on the rim."""
    h, rim = m.h, m.rim
    voids = flute_voids(o)
    plate = offset(outline_face(o, 0.0), m.flange, kind=Kind.ARC)
    tray = extrude(plate.moved(Pos(0, 0, -h - m.floor)), amount=m.floor + 2 * h + m.plug)
    tray = tray - extrude(outline_face(o, -h), amount=2 * h + m.plug + 1.0) + voids[-1]  # pocket + bottom teeth
    if m.lead_in > 0:
        tray = tray - extrude(outline_face(o, rim - m.lead_in), amount=m.lead_in + 1.0, taper=-45)
    plug = extrude(offset(outline_face(o, h), -m.clearance, kind=Kind.ARC), amount=m.plug + 0.5)
    lid = extrude(plate.moved(Pos(0, 0, rim)), amount=m.lid) + plug + voids[+1]          # flange + plug + top teeth
    groove = extrude(offset(outline_face(o, rim - m.groove_d), m.land + m.groove_w, kind=Kind.ARC) -
                     offset(outline_face(o, rim - m.groove_d), m.land, kind=Kind.ARC), amount=m.groove_d + 1.0)
    tray = tray - groove
    lay = layout(o, m)
    z_lo, z_hi = -h - m.floor - 1.0, rim + m.lid + 1.0
    for x, y in lay.bolts:
        tray, lid = tray - _cyl(x, y, m.bolt_d, z_lo, z_hi), lid - _cyl(x, y, m.bolt_d, z_lo, z_hi)
    for x, y, nx, ny in lay.notches:                 # (x, y) on the plate edge
        c = m.notch_depth / 2 - 0.5
        tray = tray - _slot(x - nx * c, y - ny * c, nx, ny, m.notch_depth + 1.0, m.notch_w, rim - m.notch_h, rim + 1.0)
        lid = lid - _slot(x - nx * c, y - ny * c, nx, ny, m.notch_depth + 1.0, m.notch_w, rim - 1.0, rim + m.notch_h)
    for x, y, nx, ny in lay.vents:                   # (x, y) on the bolt line: from the groove to the edge
        r0 = -(m.bolt_off - m.land - m.groove_w / 2)
        r1 = m.flange - m.bolt_off + 1.0
        c = (r0 + r1) / 2
        tray = tray - _slot(x + nx * c, y + ny * c, nx, ny, r1 - r0, m.vent_w, rim - m.vent_d, rim + 1.0)
    return tray, lid


def print_pose(half, top: bool, m: MouldSpec = MOULD):
    """A half in its print orientation: back face on the bed (z = 0), teeth pointing up."""
    if top:
        return Pos(0, 0, m.rim + m.lid) * Rot(0, 180, 0) * half
    return Pos(0, 0, m.h + m.floor) * half
