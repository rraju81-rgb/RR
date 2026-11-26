"""Stack compression mould that forms both rib supports in carbon fibre: three plates, one press.

The main plate holds both cavities: the Elongated rib support is a pocket in its top face and the
Hybrid one a pocket in its bottom face, each as deep as the core, with a solid web between them.
In each pocket stand the teeth of that paddle's bottom flutes.  The top clamp plate carries the
Elongated's top-flute teeth and the bottom clamp plate the Hybrid's; closing the stack slides each
set of teeth between the main plate's, and the gaps between them form the rib (the webs and lands of
the square wave).  A clamp plate seats flat on the main plate, so each cavity is exactly the rib
support: its closed frame, the solid handle and throat zone and the rib.  Chopped carbon fibre and epoxy ("forged carbon") packed
into each cavity is pressed into shape when the stack is pressed shut.

Every flute is longest where it opens (its ramp) and, for the square wave, widest there too (the web
draft), and nothing changes along a flute but the ramp, so the plates pull straight off the parts.  Around each pocket: a land and a resin overflow groove with vents; through
all three plates: M6 bolts; at both parting faces: pry notches.

World coordinates (mm): the main plate runs z = -face .. +face (face = main / 2) with the web in the
middle.  The Elongated rib fills z = face - core .. face the right way up; the Hybrid rib fills
z = -face .. -face + core upside down (mirrored in z, which for a paddle symmetric in x is the same
as turned over).  The top clamp plate runs z = face .. face + clamp, the bottom one
z = -face - clamp .. -face.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from build123d import Align, Box, Cylinder, Kind, Plane, Pos, Rot, extrude, mirror, offset

from .cad import flute_voids, outline_face
from .geometry import CONSTRUCTION as C
from .geometry import Outline

TOP, BOTTOM = "elongated", "hybrid"   # which paddle is moulded in the top / bottom face of the main plate


@dataclass(frozen=True)
class MouldSpec:
    main: float = 30.0           # main plate: top cavity + web + bottom cavity
    clamp: float = 10.0          # top and bottom clamp plates beyond the parting face; with their teeth
                                 # each is a ~20 mm part, and the closed stack is main + 2 x clamp = 50
    flange: float = 22.0         # plate edge beyond the larger pocket's edge
    land: float = 2.0            # flat between a pocket edge and its overflow groove
    groove_w: float = 2.0        # resin overflow groove around each pocket
    groove_d: float = 1.5
    vent_w: float = 2.0          # vents from a groove to the outside
    vent_d: float = 0.8
    bolt_d: float = 6.6          # M6 clearance, through all three plates
    bolt_off: float = 12.0       # bolt line, measured from the larger pocket's edge
    bolt_pitch: float = 60.0     # target spacing along the bolt line
    notch_w: float = 14.0        # pry notches either side of each parting face, at the plate edge
    notch_depth: float = 6.0
    notch_h: float = 2.5

    @property
    def h(self) -> float:
        """Half the core height: in paddle coordinates the rib support fills z = -h .. +h."""
        return C.core_t / 2

    @property
    def face(self) -> float:
        """z of the main plate's faces (+face top, -face bottom), the parting faces."""
        return self.main / 2

    @property
    def web(self) -> float:
        """Solid main plate between the two pockets."""
        return self.main - 2 * C.core_t

    @property
    def shift(self) -> float:
        """Mid-planes of the two ribs at z = +shift (top) and -shift (bottom)."""
        return self.face - self.h

    @property
    def teeth(self) -> float:
        """How far a clamp plate's teeth reach below its face: the depth of the top flutes."""
        from . import wave
        return C.core_t - wave.under_land_wall()

    @property
    def height(self) -> float:
        """The closed stack."""
        return self.main + 2 * self.clamp


MOULD = MouldSpec()


@dataclass
class Layout:
    """Plan positions (x, y) on the shared bolt line; notches and vents carry their outward normal."""
    bolts: list[tuple[float, float]] = field(default_factory=list)
    notches: list[tuple[float, float, float, float]] = field(default_factory=list)   # on the plate edge
    vents: list[tuple[float, float, float, float]] = field(default_factory=list)     # on the bolt line


def ring(o: Outline, off: float):
    """Closed shapely ring of the body outline offset outwards by `off` (round joins)."""
    from shapely.geometry import Polygon
    return Polygon(o.polyline(0.5)).buffer(off, join_style=1, quad_segs=64).exterior


def union_ring(outlines, off: float):
    """Closed shapely ring around all the outlines, offset outwards by `off`."""
    from shapely.geometry import Polygon
    from shapely.ops import unary_union
    return unary_union([Polygon(ring(o, off)) for o in outlines]).exterior


def layout(outlines, m: MouldSpec = MOULD) -> Layout:
    """Bolt, notch and vent positions around both pockets, mirrored about x = 0.

    Bolts are spaced evenly along the bolt line (offset from the outline of both paddles) from the tip
    centre to the handle-end centre on the right, and mirrored.  The other flange features sit halfway
    between two bolts: notches on the straight sides, vents at the tip, taper and handle."""
    from shapely.geometry import Point
    body = union_ring(outlines, 0.0)
    path = union_ring(outlines, m.bolt_off)
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


def vent_span(o: Outline, vent: tuple[float, float, float, float], m: MouldSpec = MOULD):
    """(start, end) in plan of a vent: from paddle o's groove to the plate edge, along the vent normal."""
    from shapely.geometry import Point
    x, y, nx, ny = vent
    g = ring(o, m.land + m.groove_w / 2)
    q = g.interpolate(g.project(Point(x, y)))
    e = m.flange - m.bolt_off + 1.0
    return (q.x, q.y), (x + nx * e, y + ny * e)


def _slot(cx: float, cy: float, nx: float, ny: float, length: float, width: float, z0: float, z1: float):
    """Box `length` along the plan direction (nx, ny), `width` across it, from z0 to z1, centred on (cx, cy)."""
    ang = math.degrees(math.atan2(ny, nx))
    return Pos(cx, cy, z0) * Rot(0, 0, ang) * Box(length, width, z1 - z0, align=(Align.CENTER, Align.CENTER, Align.MIN))


def _cyl(x: float, y: float, d: float, z0: float, z1: float):
    return Pos(x, y, z0) * Cylinder(d / 2, z1 - z0, align=(Align.CENTER, Align.CENTER, Align.MIN))


def place(shape, top: bool, m: MouldSpec = MOULD):
    """A shape in paddle coordinates (rib at z = -h .. +h) moved to its cavity in the stack."""
    return Pos(0, 0, m.shift) * shape if top else Pos(0, 0, -m.shift) * mirror(shape, about=Plane.XY)


def mould_stack(top: Outline, bottom: Outline, m: MouldSpec = MOULD):
    """(top plate, main plate, bottom plate) in world coordinates, closed on both rib supports."""
    h, f, c = m.h, m.face, m.clamp
    if m.web <= 0:
        raise ValueError(f"main plate {m.main} mm leaves no web between two {C.core_t} mm pockets")
    lay = layout((top, bottom), m)
    plate = offset(outline_face(top, 0.0), m.flange, kind=Kind.ARC)
    if bottom is not top:
        plate = plate + offset(outline_face(bottom, 0.0), m.flange, kind=Kind.ARC)
    main = extrude(plate.moved(Pos(0, 0, -f)), amount=m.main)
    top_plate = extrude(plate.moved(Pos(0, 0, f)), amount=c)
    bottom_plate = extrude(plate.moved(Pos(0, 0, -f - c)), amount=c)
    for o, up in ((top, True), (bottom, False)):
        voids = flute_voids(o)
        pocket = extrude(outline_face(o, -h), amount=2 * h + 1.0)
        groove = extrude(offset(outline_face(o, h - m.groove_d), m.land + m.groove_w, kind=Kind.ARC) -
                         offset(outline_face(o, h - m.groove_d), m.land, kind=Kind.ARC), amount=m.groove_d + 1.0)
        main = main - place(pocket, up, m) + place(voids[-1], up, m) - place(groove, up, m)   # pocket + teeth
        teeth = place(voids[+1], up, m)                                                       # the other teeth
        if up:
            top_plate = top_plate + teeth
        else:
            bottom_plate = bottom_plate + teeth
        for v in lay.vents:
            (qx, qy), (rx, ry) = vent_span(o, v, m)
            ln = math.hypot(rx - qx, ry - qy)
            main = main - place(_slot((qx + rx) / 2, (qy + ry) / 2, (rx - qx) / ln, (ry - qy) / ln, ln, m.vent_w,
                                      h - m.vent_d, h + 1.0), up, m)
        for x, y, nx, ny in lay.notches:             # (x, y) on the plate edge
            cn = m.notch_depth / 2 - 0.5
            main = main - place(_slot(x - nx * cn, y - ny * cn, nx, ny, m.notch_depth + 1.0, m.notch_w,
                                      h - m.notch_h, h + 1.0), up, m)
            clamp_notch = place(_slot(x - nx * cn, y - ny * cn, nx, ny, m.notch_depth + 1.0, m.notch_w,
                                      h - 1.0, h + m.notch_h), up, m)
            if up:
                top_plate = top_plate - clamp_notch
            else:
                bottom_plate = bottom_plate - clamp_notch
    z_lo, z_hi = -f - c - 1.0, f + c + 1.0
    for x, y in lay.bolts:
        hole = _cyl(x, y, m.bolt_d, z_lo, z_hi)
        top_plate, main, bottom_plate = top_plate - hole, main - hole, bottom_plate - hole
    return top_plate, main, bottom_plate


def main_halves(main, m: MouldSpec = MOULD):
    """The main plate split through the middle of the web, for printing each half cavity-up:
    (upper half with the top cavity, lower half with the bottom cavity), in world coordinates."""
    big = 2000.0
    upper = main & Pos(0, 0, 0) * Box(big, big, m.face + 1.0, align=(Align.CENTER, Align.CENTER, Align.MIN))
    lower = main & Pos(0, 0, -m.face - 1.0) * Box(big, big, m.face + 1.0, align=(Align.CENTER, Align.CENTER, Align.MIN))
    return upper, lower


def print_pose(shape, part: str, m: MouldSpec = MOULD):
    """A plate in its print orientation, back face on the bed (z = 0), teeth pointing up.

    part: "top" or "bottom" (clamp plates), "main" (one piece, top cavity up), "upper" / "lower"
    (the main plate halves from main_halves)."""
    f, c = m.face, m.clamp
    if part == "top":
        return Pos(0, 0, f + c) * Rot(0, 180, 0) * shape
    if part == "bottom":
        return Pos(0, 0, f + c) * shape
    if part == "main":
        return Pos(0, 0, f) * shape
    if part == "upper":
        return shape
    if part == "lower":
        return Rot(0, 180, 0) * shape
    raise ValueError(part)
