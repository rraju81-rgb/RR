"""Parametric 2-D geometry of the paddle outline.

Coordinate system (mm)
    x : across the paddle, 0 on the centre line, + to the right (face view)
    y : along the paddle, 0 at the butt end of the handle, + towards the tip
    z : through the thickness, 0 on the mid-plane

The outline is a closed loop of straight lines and tangent (G1) arcs listed
counter-clockwise.  Every value that is not an input parameter (tangent points,
arc centres, the side-straight length, ...) is derived here, so changing one
parameter keeps the whole profile consistent.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

Pt = tuple[float, float]


def _pt(c: Pt, r: float, a: float) -> Pt:
    return (c[0] + r * math.cos(a), c[1] + r * math.sin(a))


def _mx(p: Pt) -> Pt:
    return (-p[0], p[1])


@dataclass(frozen=True)
class Line:
    p0: Pt
    p1: Pt

    @property
    def length(self) -> float:
        return math.dist(self.p0, self.p1)

    def tangent(self, t: float) -> Pt:
        dx, dy = self.p1[0] - self.p0[0], self.p1[1] - self.p0[1]
        n = math.hypot(dx, dy)
        return (dx / n, dy / n)

    def sample(self, step: float) -> list[Pt]:
        n = max(1, math.ceil(self.length / step))
        return [(self.p0[0] + (self.p1[0] - self.p0[0]) * i / n,
                 self.p0[1] + (self.p1[1] - self.p0[1]) * i / n) for i in range(n + 1)]

    def mirrored(self) -> "Line":
        return Line(_mx(self.p1), _mx(self.p0))

    def area_term(self) -> float:
        return 0.5 * (self.p0[0] * self.p1[1] - self.p1[0] * self.p0[1])


@dataclass(frozen=True)
class Arc:
    c: Pt
    r: float
    a0: float       # start angle [rad]
    sweep: float    # signed sweep [rad], + = counter-clockwise

    @property
    def a1(self) -> float:
        return self.a0 + self.sweep

    @property
    def p0(self) -> Pt:
        return _pt(self.c, self.r, self.a0)

    @property
    def p1(self) -> Pt:
        return _pt(self.c, self.r, self.a1)

    @property
    def length(self) -> float:
        return abs(self.sweep) * self.r

    @property
    def ccw(self) -> bool:
        return self.sweep > 0

    def point(self, t: float) -> Pt:
        return _pt(self.c, self.r, self.a0 + t * self.sweep)

    def tangent(self, t: float) -> Pt:
        a = self.a0 + t * self.sweep
        s = 1.0 if self.sweep > 0 else -1.0
        return (-math.sin(a) * s, math.cos(a) * s)

    def sample(self, step: float) -> list[Pt]:
        n = max(2, math.ceil(self.length / step))
        return [self.point(i / n) for i in range(n + 1)]

    def mirrored(self) -> "Arc":
        return Arc(_mx(self.c), self.r, math.pi - self.a1, self.sweep)

    def area_term(self) -> float:
        (x0, y0), (x1, y1) = self.p0, self.p1
        return 0.5 * (self.r ** 2 * self.sweep + self.c[0] * (y1 - y0) - self.c[1] * (x1 - x0))


Segment = Line | Arc


@dataclass(frozen=True)
class PaddleSpec:
    """Design inputs.  All lengths in mm, angles in degrees."""
    key: str
    name: str
    drawing_no: str
    length: float = 390.0           # overall length incl. butt cap, butt to tip
    width: float = 200.0            # blade width
    handle_length: float = 130.0    # handle incl. butt cap: butt to the end of the straight 30 mm section
    handle_width: float = 30.0
    thickness: float = 16.0
    cap_length: float = 4.0         # butt-cap base below the body: plates + core start at y = cap_length
    head: str = "square"            # "square" (corner radii) or "dome"
    corner_r: float = 48.0          # square head: tip corner radius
    dome_r: float = 150.0           # dome head: crown radius
    dome_shoulder_r: float = 30.0   # dome head: crown-to-side blend radius
    shoulder_r: float = 25.0        # convex radius where the side turns into the taper
    taper_deg: float = 30.0         # taper below horizontal, side -> handle
    throat_r: float = 15.0          # concave fillet blending taper into the handle

    @property
    def blade_length(self) -> float:
        return self.length - self.handle_length

    @property
    def body_length(self) -> float:
        """Length of the face plates / rib core (overall length minus the butt-cap base)."""
        return self.length - self.cap_length


@dataclass(frozen=True)
class Construction:
    """Sandwich lay-up, wave-rib core and grip hardware shared by both paddles (mm)."""
    face_t: float = 4.0          # carbon-fibre face sheet, top and bottom (identical parts)
    core_t: float = 8.0          # rib core height between the face sheets
    frame_w: float = 6.0         # closed perimeter frame of the rib core (covers the whole side)
    rib_pitch: float = 18.0      # wave length (crest to crest) across the width
    rib_t: float = 1.6           # wave-rib wall thickness
    rib_amp: float = 4.0         # wave centre-line amplitude; crests are cut flat at the faces = bond lands
                                 # (4.0 -> 4.25 mm wide lands; the first FEA iteration used 3.6 -> 3.13 mm)
    solid_to: float = 150.0      # core is solid from the butt up to this height (handle + throat)
    runout_len: float = 8.0      # flute run-out: 45 deg taper (printable without support) so the core
                                 # meets each face sheet in a thin wedge, not a square step; 0 = square
    insert_d: float = 5.6        # M4 heat-set insert bore (OD 5.6, L 8.1) in the butt end of the core
    insert_depth: float = 10.0
    screw_relief_d: float = 4.5  # clearance bore beyond the insert for the screw tip
    screw_relief_depth: float = 16.0
    # grip hardware
    sleeve_clear: float = 0.2    # per side, between handle core and sleeve
    sleeve_wall: float = 1.8
    sleeve_r: float = 3.0        # outer corner radius of the sleeve
    wrap_t: float = 0.75         # replacement grip tape
    collar_h: float = 10.0
    collar_wall: float = 1.25
    cap_skirt: float = 6.0       # butt-cap skirt over the sleeve end
    cap_wall: float = 1.5
    cb_d: float = 8.0            # counterbore for ISO 7380 M4 button head (head 7.6 x 2.2)
    cb_depth: float = 2.4
    cap_hole_d: float = 4.5
    screw_len: float = 12.0      # ISO 7380 M4 x 12

    @property
    def thickness(self) -> float:
        return 2 * self.face_t + self.core_t


CONSTRUCTION = Construction()


def grip_dims(sp: PaddleSpec) -> dict[str, float]:
    """Key sizes of the grip hardware (all derived from the handle core and CONSTRUCTION)."""
    C = CONSTRUCTION
    sw = sp.handle_width + 2 * (C.sleeve_clear + C.sleeve_wall)
    st = sp.thickness + 2 * (C.sleeve_clear + C.sleeve_wall)
    ww, wt = sw + 2 * C.wrap_t, st + 2 * C.wrap_t
    wr = C.sleeve_r + C.wrap_t
    cw, ct = sw + 2 * C.cap_wall, st + 2 * C.cap_wall
    kw, kt = ww + 2 * C.collar_wall, wt + 2 * C.collar_wall
    collar_top = sp.handle_length - 1.0
    d = dict(sleeve_w=sw, sleeve_t=st, sleeve_bot=sp.cap_length, sleeve_top=collar_top,
             wrap_w=ww, wrap_t=wt, wrap_r=wr, wrap_bot=sp.cap_length + C.cap_skirt, wrap_top=collar_top - C.collar_h,
             cap_w=cw, cap_t=ct, cap_r=C.sleeve_r + C.cap_wall, collar_w=kw, collar_t=kt,
             collar_r=wr + C.collar_wall, collar_bot=collar_top - C.collar_h, collar_top=collar_top)
    # grip circumference on the wrap (rounded rectangle perimeter)
    d["grip_circumference"] = 2 * (ww + wt) - 8 * wr + 2 * math.pi * wr
    return d


ELONGATED = PaddleSpec(key="elongated", name="ELONGATED", drawing_no="PB-EL-001",
                       width=200.0, head="square", corner_r=48.0)
HYBRID = PaddleSpec(key="hybrid", name="HYBRID", drawing_no="PB-HY-001",
                    width=190.0, head="dome", dome_r=150.0, dome_shoulder_r=30.0)
DESIGNS = (ELONGATED, HYBRID)


@dataclass
class Outline:
    spec: PaddleSpec
    segments: list[Segment]
    pts: dict[str, Pt] = field(default_factory=dict)        # right-hand key points
    centres: dict[str, tuple[Pt, float]] = field(default_factory=dict)  # name -> (centre, R)
    info: dict[str, float] = field(default_factory=dict)

    # -- derived properties ------------------------------------------------
    @property
    def area(self) -> float:
        return sum(s.area_term() for s in self.segments)

    @property
    def perimeter(self) -> float:
        return sum(s.length for s in self.segments)

    def polyline(self, step: float = 0.5) -> list[Pt]:
        out: list[Pt] = []
        for s in self.segments:
            pts = s.sample(step)
            out.extend(pts if not out else pts[1:])
        return out[:-1]  # closed: last == first

    def bbox(self) -> tuple[float, float, float, float]:
        p = self.polyline(0.2)
        xs, ys = [q[0] for q in p], [q[1] for q in p]
        return min(xs), min(ys), max(xs), max(ys)

    def half_width_at(self, y: float) -> float:
        """Half width of the profile at height y (max |x| of the outline crossing)."""
        best = 0.0
        p = self.polyline(0.1)
        for (x0, y0), (x1, y1) in zip(p, p[1:] + p[:1]):
            if (y0 - y) * (y1 - y) <= 0 and y0 != y1:
                x = x0 + (x1 - x0) * (y - y0) / (y1 - y0)
                best = max(best, abs(x))
        return best

    def distance_to(self, q: Pt) -> float:
        best = math.inf
        for s in self.segments:
            if isinstance(s, Line):
                (x0, y0), (x1, y1) = s.p0, s.p1
                dx, dy = x1 - x0, y1 - y0
                t = max(0.0, min(1.0, ((q[0] - x0) * dx + (q[1] - y0) * dy) / (dx * dx + dy * dy)))
                d = math.hypot(q[0] - x0 - t * dx, q[1] - y0 - t * dy)
            else:
                a = math.atan2(q[1] - s.c[1], q[0] - s.c[0])
                lo, hi = sorted((s.a0, s.a1))
                k = (a - lo) % (2 * math.pi)
                if k <= hi - lo + 1e-12:
                    d = abs(math.hypot(q[0] - s.c[0], q[1] - s.c[1]) - s.r)
                else:
                    d = min(math.dist(q, s.p0), math.dist(q, s.p1))
            best = min(best, d)
        return best


def _taper(spec: PaddleSpec) -> dict:
    """Convex shoulder arc -> straight taper -> concave throat fillet (right side)."""
    a, h, t = spec.width / 2, spec.handle_width / 2, spec.handle_length
    r1, r2, b = spec.shoulder_r, spec.throat_r, math.radians(spec.taper_deg)
    sb, cb, tb = math.sin(b), math.cos(b), math.tan(b)
    y1 = t + (r1 + r2) * cb + tb * (a - h - (r1 + r2) * (1 - sb))   # side tangent height
    p2 = (h + r2 - r2 * sb, t + r2 * cb)                          # throat fillet -> taper
    p1 = (a - r1 + r1 * sb, y1 - r1 * cb)                         # taper -> shoulder arc
    if p1[0] < p2[0]:
        raise ValueError(f"{spec.key}: shoulder and throat radii overlap - taper line has negative length")
    return dict(y1=y1, p1=p1, p2=p2, c_throat=(h + r2, t), c_shoulder=(a - r1, y1))


def build(spec: PaddleSpec) -> Outline:
    """Outline of the paddle body (face plates / rib core); the butt cap fills y = 0 .. cap_length."""
    a, h, t, L = spec.width / 2, spec.handle_width / 2, spec.handle_length, spec.length
    y0 = spec.cap_length
    b = math.radians(spec.taper_deg)
    tp = _taper(spec)
    y1, p1, p2 = tp["y1"], tp["p1"], tp["p2"]

    right: list[Segment] = [
        Line((h, y0), (h, t)),                                               # handle side
        Arc(tp["c_throat"], spec.throat_r, math.pi, -(math.pi / 2 - b)),      # throat fillet (concave)
        Line(p2, p1),                                                        # taper
        Arc(tp["c_shoulder"], spec.shoulder_r, -(math.pi / 2 - b), math.pi / 2 - b),  # shoulder (convex)
    ]
    pts = {"butt": (h, y0), "throat": (h, t), "taper_lo": p2, "taper_hi": p1, "side_lo": (a, y1)}
    centres = {"throat": (tp["c_throat"], spec.throat_r), "shoulder": (tp["c_shoulder"], spec.shoulder_r)}
    info: dict[str, float] = {}

    if spec.head == "square":
        rc = spec.corner_r
        y_top = L - rc
        if y_top < y1:
            raise ValueError(f"{spec.key}: corner radius too large for the side length")
        cc = (a - rc, L - rc)
        right += [Line((a, y1), (a, y_top)),
                  Arc(cc, rc, 0.0, math.pi / 2),
                  Line((a - rc, L), (0.0, L))]
        pts.update(side_hi=(a, y_top), crown=(a - rc, L))
        centres["corner"] = (cc, rc)
    elif spec.head == "dome":
        rd, rs = spec.dome_r, spec.dome_shoulder_r
        cd = (0.0, L - rd)
        dx = a - rs
        ys = cd[1] + math.sqrt((rd - rs) ** 2 - dx ** 2)
        cs = (dx, ys)
        th = math.atan2(cs[1] - cd[1], cs[0] - cd[0])
        tpt = _pt(cd, rd, th)
        if ys < y1:
            raise ValueError(f"{spec.key}: dome too deep for the side length")
        right += [Line((a, y1), (a, ys)),
                  Arc(cs, rs, 0.0, th),
                  Arc(cd, rd, th, math.pi / 2 - th)]
        pts.update(side_hi=(a, ys), crown=tpt)
        centres.update(dome_shoulder=(cs, rs), dome=(cd, rd))
        info["dome_rise"] = L - ys
    else:
        raise ValueError(spec.head)

    # left half: mirror and reverse, then merge the two half-lines on the centre line
    left = [s.mirrored() for s in reversed(right)]
    segs: list[Segment] = []
    for s in right[:-1] if spec.head == "square" else right:
        segs.append(s)
    if spec.head == "square":
        segs.append(Line(right[-1].p0, left[0].p1))           # full-width tip edge
        segs.extend(left[1:])
    else:
        segs.extend(left)
    segs.append(Line(left[-1].p1, right[0].p0))               # butt edge (-h,y0) -> (h,y0)

    info.update(
        side_straight=pts["side_hi"][1] - y1,
        taper_length=math.dist(p1, p2),
        shoulder_tangent_y=y1,
        side_top_y=pts["side_hi"][1],
        # where the taper line (extended) meets the handle edge / the blade side
        throat_vertex_y=p2[1] - (p2[0] - h) * math.tan(b),
        shoulder_vertex_y=p1[1] + (a - p1[0]) * math.tan(b),
    )
    o = Outline(spec, segs, pts, centres, info)
    check(o)
    return o


def check(o: Outline) -> None:
    """Assert the loop is closed, G1-continuous and has the specified size."""
    segs = o.segments
    for s0, s1 in zip(segs, segs[1:] + segs[:1]):
        assert math.dist(s0.p1, s1.p0) < 1e-6, ("gap", s0, s1)
    # tangent continuity everywhere except the four butt corners / two tip corners of the square edge
    kinks = 0
    for s0, s1 in zip(segs, segs[1:] + segs[:1]):
        t0, t1 = s0.tangent(1.0), s1.tangent(0.0)
        if abs(t0[0] * t1[1] - t0[1] * t1[0]) > 1e-6 or t0[0] * t1[0] + t0[1] * t1[1] < 0:
            kinks += 1
    assert kinks == 2, f"expected only the 2 butt corners, found {kinks} corners"
    x0, y0, x1, y1 = o.bbox()
    sp = o.spec
    assert abs((x1 - x0) - sp.width) < 1e-3 and abs(y0 - sp.cap_length) < 1e-3 and abs(y1 - sp.length) < 1e-3, \
        (x0, y0, x1, y1)
    assert o.area > 0, "outline must be counter-clockwise"


if __name__ == "__main__":
    for sp in DESIGNS:
        o = build(sp)
        print(f"{sp.name:10s} area={o.area/100:7.1f} cm2  perimeter={o.perimeter:6.1f} mm")
        for k, v in o.pts.items():
            print(f"   {k:10s} ({v[0]:7.2f}, {v[1]:7.2f})")
        for k, (c, r) in o.centres.items():
            print(f"   centre {k:14s} R{r:<6g} ({c[0]:7.2f}, {c[1]:7.2f})")
        for k, v in o.info.items():
            print(f"   {k:20s} {v:8.2f}")
