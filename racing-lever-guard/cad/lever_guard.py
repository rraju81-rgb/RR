"""Parametric CAD model of a universal racing lever guard (brake / clutch lever protector).

Architecture (same as the "CNC aluminium + carbon finish" universal racing guards):

    bar-end adapter  (CNC 6061-T6, anodised colour)  -- sits on the open bar end,
                                                        expander or OEM thread inside the bar
    guard arm        (CNC 6061-T6, anodised colour)  -- Hirth face serration on the adapter
                                                        gives 10 deg angle steps
    guard blade      (carbon / carbon finish)        -- bolted to the arm through a slot,
                                                        +/-5 mm fore-aft adjustment; gusset
                                                        inside the bend takes crash loads
    expander         (cone nut + elastomer sleeve)   -- S / M / L sleeves cover 13-19 mm bar ID
    wind guard       (moulded shell + two-piece      -- clamp wraps the blade run and slides
                      CNC clamp)                        along it, locked by two M4 screws

Guard frame "G" used for every part (all dimensions in mm):
    origin  centre of the handlebar's open end face
    +X      along the bar axis, outward (out of the bar end)
    +Y      from the bar axis toward the lever, in the lever plane
    +Z      normal to the lever plane

One part set fits either side of the bike: the left guard is the right guard turned over
(rotated 180 deg about Y), because every part is symmetric about the lever plane (the two
diffuser clamp halves are the same part, one turned over). The wind guard shell is the
exception: it rises toward the rider's knuckles, so it comes as a mirror-image pair.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, replace

import cadquery as cq
from OCP.TopAbs import TopAbs_EDGE, TopAbs_FACE
from OCP.TopExp import TopExp
from OCP.TopTools import TopTools_IndexedDataMapOfShapeListOfShape


@dataclass(frozen=True)
class Params:
    # ---- handlebar --------------------------------------------------------------------------
    bar_od: float = 22.2  # 7/8" bar

    # ---- Hirth face serration between adapter and arm -----------------------------------------
    teeth: int = 36  # 360 / 36 = 10 deg angle steps
    serr_r_in: float = 7.5
    serr_r_out: float = 16.0

    # ---- bar-end adapter ----------------------------------------------------------------------
    body_d: float = 32.0
    pitch_x: float = 12.0  # serration pitch plane, measured from the bar end face
    spigot_d: float = 12.4  # centres in any bar with ID >= 12.5
    spigot_len: float = 6.0
    bolt_clear_d: float = 6.6  # M6 medium clearance, ISO 273
    groove_x: tuple[float, ...] = (4.0, 8.0)  # decorative V-grooves on the adapter
    groove_w: float = 1.0
    groove_depth: float = 0.5

    # ---- guard arm ----------------------------------------------------------------------------
    hub_outer_x: float = 24.0
    cbore_d: float = 11.0  # M6 ISO 4762 head is 10 x 6
    cbore_depth: float = 6.5
    neck_inner_x: float = 14.0
    neck_h: float = 22.0
    neck_end: float = 42.0
    neck_fillet_r: float = 6.0
    tap_d: float = 4.2  # M5 tap drill

    # ---- guard blade --------------------------------------------------------------------------
    blade_t: float = 6.0  # 6 = carbon / aluminium, 8 = 3D printed
    blade_h: float = 22.0
    blade_rear: float = 12.35  # rear end of the blade at the nominal position (puts the M5 holes at 24 / 36)
    blade_rear_r: float = 6.0
    slot_w: float = 5.3  # M5 clearance
    slot_margin: float = 4.0  # material behind / in front of the slot
    screw_pitch: float = 12.0  # spacing of the two M5 screws
    adjust: float = 5.0  # +/- fore-aft adjustment
    bend_r: float = 18.0  # bend radius on the blade centre line
    front_len: float = 100.0  # straight run in front of the lever
    front_toe_deg: float = 3.0  # run opens away from the bar toward its tip, following the lever line
    tip_r: float = 8.0
    edge_r: float = 0.6  # edge break on the blade
    haunch_len: float = 14.0  # gusset inside the bend runs out tangentially this far along the run
    haunch_seat_gap: float = 1.0  # the gusset's edge arc crosses the seat face this far past the bend start
    haunch_blend_r: float = 4.0  # blend from the seat face into the gusset's edge (no corner to crack from)

    # ---- expander -----------------------------------------------------------------------------
    sleeve_len: float = 20.0
    sleeve_recess_depth: float = 7.0
    sleeve_slit_w: float = 1.0
    sleeve_slit_len: float = 12.0
    cone_land: float = 3.0
    cone_half_angle_deg: float = 15.0
    cone_min_d: float = 8.0  # keeps >= 1 mm wall around the M6 thread
    cone_tap_d: float = 5.0  # M6 tap drill

    # ---- wind guard: one moulded / printed piece; a slotted mount on it slides along the run ----
    shell_t: float = 3.0  # wall
    shell_gap: float = 1.0  # flange rear edge to the blade's outer face
    shell_flange: float = 14.0  # flange runs this far ahead of the blade's outer face, then bends up
    shell_bend_r: float = 12.0  # flange-to-shield bend (centre line)
    shell_out: float = 14.0  # shell starts this far outboard of the mount's outboard end
    shell_len: float = 230.0  # outboard end to tip, along the run
    shell_crest: float = 84.0  # highest point above the blade's outer face, measured up on the bike
    shell_crease: tuple[float, float] = (60.0, -4.0)  # crease height at the outboard end / at the tip
    lever_deg: float = 30.0  # lever plane below horizontal: sets "up" and "forward" for the shell
    clamp_len: float = 40.0  # slotted mount length along the run
    clamp_wall: float = 3.0  # mount wall ahead of, over and under the blade
    clamp_back: float = 2.0  # mount wall on the blade's lever-side face (keeps >= 10 mm to the lever at slot -4)
    clamp_clear: float = 0.3  # slot clearance all round the blade
    clamp_screw_inset: float = 9.0  # grub screws from the mount ends
    clamp_boss_d: float = 11.0  # bosses under the mount for the M4 heat-set inserts
    clamp_boss_h: float = 6.0
    insert_d: float = 5.6  # hole for an M4 x 5.7 heat-set insert
    insert_len: float = 6.2
    clamp_pos: float = 15.0  # mount outboard end along the run, from the bend (see clamp_range)

    # ---- hardware -----------------------------------------------------------------------------
    m6_len: float = 45.0  # ISO 4762 M6 x 45 in expander mode
    m5_len: float = 14.0  # ISO 7380 M5 x 14 for the 6 mm blade
    m4_len: float = 8.0  # ISO 4029 M4 x 8 cup-point grub screw, up through the insert onto the blade

    # ---- derived ------------------------------------------------------------------------------
    @property
    def tan_g(self) -> float:
        """Flank slope of a 90 deg Hirth tooth: crest-to-root height = half the pitch."""
        return math.pi / (2 * self.teeth)

    @property
    def slot_len(self) -> float:
        return self.screw_pitch + self.slot_w + 2 * self.adjust

    @property
    def slot_center(self) -> float:
        return self.blade_rear + self.slot_margin + self.slot_len / 2

    @property
    def screw_v(self) -> tuple[float, float]:
        c = self.slot_center
        return (c - self.screw_pitch / 2, c + self.screw_pitch / 2)

    @property
    def bend_start(self) -> float:
        return self.blade_rear + self.slot_margin + self.slot_len + self.slot_margin

    @property
    def blade_seat_x(self) -> float:
        return self.hub_outer_x

    @property
    def blade_cx(self) -> float:
        """X of the blade centre line along its rear (bolted) section."""
        return self.blade_seat_x + self.blade_t / 2

    @property
    def bend_angle_deg(self) -> float:
        return 90.0 - self.front_toe_deg

    @property
    def bend_center(self) -> tuple[float, float]:
        return (self.blade_cx - self.bend_r, self.bend_start)

    @property
    def run_dir(self) -> tuple[float, float]:
        """Unit direction of the run in front of the lever (inboard, slightly forward)."""
        a = math.radians(self.front_toe_deg)
        return (-math.cos(a), math.sin(a))

    def run_point(self, s: float, offset: float = 0.0) -> tuple[float, float]:
        """Point on the run, s mm along it from the end of the bend; offset > 0 moves toward
        the lever side of the blade (offset = blade_t / 2 is the inner face)."""
        b = math.radians(self.bend_angle_deg)
        cx, cy = self.bend_center
        r = self.bend_r - offset
        dx, dy = self.run_dir
        return (cx + r * math.cos(b) + s * dx, cy + r * math.sin(b) + s * dy)

    @property
    def tip_x(self) -> float:
        return self.run_point(self.front_len)[0]

    @property
    def head_seat_x(self) -> float:
        return self.hub_outer_x - self.cbore_depth

    @property
    def clamp_range(self) -> tuple[float, float]:
        """Travel of the wind guard mount's outboard end along the run: from just past the bend
        gusset to where the mount still sits fully on the blade."""
        return (self.haunch_len + 1.0, self.front_len - self.clamp_len)

    @property
    def blade_path_len(self) -> float:
        return (
            (self.bend_start - self.blade_rear)
            + math.radians(self.bend_angle_deg) * self.bend_r
            + self.front_len
        )


# Elastomer sleeve sizes: name -> (sleeve OD, bar ID range it is meant for)
SLEEVES: dict[str, tuple[float, tuple[float, float]]] = {
    "S": (12.7, (13.0, 15.0)),
    "M": (14.7, (15.0, 17.0)),
    "L": (16.7, (17.0, 19.0)),
}


# ------------------------------------------------------------------------------------------------
# helpers
# ------------------------------------------------------------------------------------------------
def _revolve_x(profile: list[tuple[float, float]]) -> cq.Workplane:
    """Revolve a closed (x, r) profile around the X axis."""
    return cq.Workplane("XY").polyline(profile).close().revolve(360, (0, 0, 0), (1, 0, 0))


def _cyl_x(r: float, x0: float, x1: float) -> cq.Workplane:
    return cq.Workplane("YZ", origin=(x0, 0, 0)).circle(r).extrude(x1 - x0)


def _hirth_cutters(p: Params, facing: int, phase: float) -> cq.Shape:
    """Valley cutters of a 90 deg Hirth face serration whose pitch plane is X = p.pitch_x.

    facing=+1: teeth point toward +X (adapter); facing=-1: teeth point toward -X (arm hub).
    Ridges and roots run radially through the axis, so every flank is a plane -- the
    standard Hirth form that a V-cutter or grinder can produce.
    """
    n, tg, x0 = p.teeth, p.tan_g, p.pitch_x
    half = math.pi / n
    rho1, rho2 = 0.4, p.serr_r_out + 3.0
    cutters = []
    for k in range(n):
        th = phase + (k + 0.5) * 2 * half  # valley centre
        d = cq.Vector(0, math.cos(th), math.sin(th))
        t = cq.Vector(0, -math.sin(th), math.cos(th))
        wires = []
        for rho in (rho1, rho2):
            sc = rho * math.tan(half)
            root = x0 - facing * rho * tg
            crest = x0 + facing * (rho / math.cos(half)) * tg
            top = crest + facing * 3.0
            pts = [(0.0, root), (sc, crest), (sc, top), (-sc, top), (-sc, crest)]
            wires.append(
                cq.Wire.makePolygon(
                    [d * rho + t * s + cq.Vector(x, 0, 0) for s, x in pts], close=True
                )
            )
        cutters.append(cq.Solid.makeLoft(wires, ruled=True))
    return cq.Compound.makeCompound(cutters)


def _sharp_edges(shape: cq.Shape, min_angle_deg: float = 10.0) -> list[cq.Edge]:
    """Edges where the two adjacent faces meet at an angle (skips tangent seams, which
    make OCC fillets fail)."""
    emap = TopTools_IndexedDataMapOfShapeListOfShape()
    TopExp.MapShapesAndAncestors_s(shape.wrapped, TopAbs_EDGE, TopAbs_FACE, emap)
    out = []
    for i in range(1, emap.Extent() + 1):
        faces = emap.FindFromIndex(i)
        if faces.Extent() != 2:
            continue
        edge = cq.Edge(emap.FindKey(i))
        mid = edge.positionAt(0.5)
        try:
            n1 = cq.Face(faces.First()).normalAt(mid)
            n2 = cq.Face(faces.Last()).normalAt(mid)
        except Exception:
            continue
        if math.degrees(n1.getAngle(n2)) > min_angle_deg:
            out.append(edge)
    return out


def _fillet_sharp(wp: cq.Workplane, r: float, keep=lambda mid: True) -> cq.Workplane:
    """Fillet every sharp edge whose midpoint satisfies keep(); unchanged if OCC fails."""
    solid = wp.val()
    edges = [e for e in _sharp_edges(solid) if keep(e.positionAt(0.5))]
    try:
        out = solid.fillet(r, edges)
        if out.isValid():
            return cq.Workplane(obj=out)
    except Exception:
        pass
    return wp


# ------------------------------------------------------------------------------------------------
# parts
# ------------------------------------------------------------------------------------------------
def adapter(p: Params = Params(), spigot: bool = True) -> cq.Workplane:
    """Bar-end adapter. spigot=False gives the flat-faced version for bikes whose bar
    already has a threaded OEM bar-end insert (the guard bolt goes into that thread)."""
    rb, rs, rh = p.body_d / 2, p.spigot_d / 2, p.bolt_clear_d / 2
    top = p.pitch_x + p.serr_r_out * p.tan_g  # crest height at the outer radius
    prof: list[tuple[float, float]] = []
    if spigot:
        x_in = -p.spigot_len
        prof += [(x_in, rh), (x_in, rs - 0.5), (x_in + 0.5, rs), (0.0, rs)]
    else:
        prof += [(0.0, rh)]
    prof += [(0.0, rb - 0.8), (0.8, rb)]
    for gx in p.groove_x:  # decorative V-grooves
        prof += [(gx - p.groove_w / 2, rb), (gx, rb - p.groove_depth), (gx + p.groove_w / 2, rb)]
    prof += [(top - 0.5, rb), (top, rb - 0.5), (top, rh)]
    body = _revolve_x(prof)
    body = body.cut(_hirth_cutters(p, facing=+1, phase=0.0))
    relief_x = p.pitch_x - p.serr_r_in * p.tan_g - 0.3
    return body.cut(_cyl_x(p.serr_r_in, relief_x, top + 1))


def arm(p: Params = Params()) -> cq.Workplane:
    """Guard arm: serrated hub on the adapter + neck that carries the blade."""
    rb, rh = p.body_d / 2, p.bolt_clear_d / 2
    bottom = p.pitch_x - p.serr_r_out * p.tan_g
    hub = _revolve_x(
        [
            (bottom, rh),
            (bottom, rb - 0.5),
            (bottom + 0.5, rb),
            (p.hub_outer_x - 1.0, rb),
            (p.hub_outer_x, rb - 1.0),
            (p.hub_outer_x, rh),
        ]
    )
    hub = hub.cut(_hirth_cutters(p, facing=-1, phase=math.pi / p.teeth))
    relief_x = p.pitch_x + p.serr_r_in * p.tan_g + 0.3
    hub = hub.cut(_cyl_x(p.serr_r_in, bottom - 1, relief_x))

    # neck outline in the YZ plane (local x = Y, local y = Z): hub circle + neck with
    # concave fillets of radius neck_fillet_r and a full-round front end
    w, rf = p.neck_h / 2, p.neck_fillet_r
    yc = math.sqrt((rb + rf) ** 2 - (w + rf) ** 2)
    tan_hub = (yc * rb / (rb + rf), (w + rf) * rb / (rb + rf))
    a0 = math.atan2(tan_hub[1] - (w + rf), tan_hub[0] - yc)
    am = (a0 - math.pi / 2) / 2
    fil_mid = (yc + rf * math.cos(am), (w + rf) + rf * math.sin(am))
    end_c = p.neck_end - w
    neck = (
        cq.Workplane("YZ", origin=(p.neck_inner_x, 0, 0))
        .moveTo(tan_hub[0], tan_hub[1])
        .threePointArc((-rb, 0), (tan_hub[0], -tan_hub[1]))
        .threePointArc((fil_mid[0], -fil_mid[1]), (yc, -w))
        .lineTo(end_c, -w)
        .threePointArc((p.neck_end, 0), (end_c, w))
        .lineTo(yc, w)
        .threePointArc(fil_mid, tan_hub)
        .close()
        .extrude(p.hub_outer_x - p.neck_inner_x)
    )
    body = hub.union(neck)
    body = _fillet_sharp(body, 1.0, keep=lambda m: m.x > p.neck_inner_x - 0.01 and m.y > -rb)
    # M6 counterbore + through hole
    body = body.cut(_cyl_x(p.cbore_d / 2, p.head_seat_x, p.hub_outer_x + 1))
    body = body.cut(_cyl_x(rh, bottom - 1, p.hub_outer_x + 1))
    # two M5 tapped holes for the blade
    holes = (
        cq.Workplane("YZ", origin=(p.neck_inner_x - 1, 0, 0))
        .pushPoints([(v, 0) for v in p.screw_v])
        .circle(p.tap_d / 2)
        .extrude(p.hub_outer_x - p.neck_inner_x + 2)
    )
    return body.cut(holes)


def arc_mid(c: tuple[float, float], r: float, p1: tuple[float, float], p2: tuple[float, float]) -> tuple[float, float]:
    """Midpoint of the shorter arc from p1 to p2 on the circle with centre c and radius r."""
    a1 = math.atan2(p1[1] - c[1], p1[0] - c[0])
    a2 = math.atan2(p2[1] - c[1], p2[0] - c[0])
    a = a1 + math.remainder(a2 - a1, math.tau) / 2
    return (c[0] + r * math.cos(a), c[1] + r * math.sin(a))


def _haunch(p: Params) -> cq.Workplane:
    """Gusset filling the inside of the bend, where a fall loads the blade hardest.

    Its free edge is tangent all the way along: it leaves the seat face on a haunch_blend_r
    blend, follows an arc and runs out tangent to the run's inner face at s = haunch_len, so
    there is no corner or step for a crack to start from. The blend starts past the arm's neck
    with the blade at slot -adjust, so the gusset clears the arm at every slot position.
    """
    R = p.bend_r
    cxc, cyc = p.bend_center
    s, t, f = haunch_blend(p)
    b_pt = haunch_ends(p)[1]
    ox, oy, rho = haunch_circle(p)
    b = math.radians(p.bend_angle_deg)
    on_cl = lambda a: (cxc + R * math.cos(a), cyc + R * math.sin(a))  # noqa: E731
    # close the outline through the blade material: seat, bend and run centre lines
    wp = cq.Workplane("XY", origin=(0, 0, -p.blade_h / 2)).moveTo(*s)
    if s[1] < cyc:  # the blend starts on the straight seat
        a0 = 0.0
        wp = wp.lineTo(p.blade_cx, s[1]).lineTo(*on_cl(a0))
    else:
        a0 = math.asin((s[1] - cyc) / R)
        wp = wp.lineTo(*on_cl(a0))
    wp = (
        wp.threePointArc(on_cl((a0 + b) / 2), on_cl(b))
        .lineTo(*p.run_point(p.haunch_len, 0.0))
        .lineTo(*b_pt)
        .threePointArc(arc_mid((ox, oy), rho, b_pt, t), t)
    )
    if p.haunch_blend_r > 0:
        wp = wp.threePointArc(arc_mid(f, p.haunch_blend_r, t, s), s)
    return wp.close().extrude(p.blade_h)


def haunch_ends(p: Params) -> tuple[tuple[float, float], tuple[float, float]]:
    """A: where the gusset's edge arc crosses the seat face (rounded off by the blend, see
    haunch_blend); B: where the arc runs out on the run's inner face."""
    return (p.blade_seat_x, p.bend_start + p.haunch_seat_gap), p.run_point(p.haunch_len, p.blade_t / 2)


def haunch_blend(p: Params) -> tuple[tuple[float, float], tuple[float, float], tuple[float, float]]:
    """Blend between the seat face and the gusset's edge arc: the circle of radius
    haunch_blend_r tangent to both. Returns its tangent point on the seat face (where the
    gusset starts), its tangent point on the edge arc, and its centre."""
    ox, oy, rho = haunch_circle(p)
    r = p.haunch_blend_r
    fx = p.blade_seat_x - r
    fy = oy + math.sqrt((rho - r) ** 2 - (fx - ox) ** 2)
    k = rho / (rho - r)
    return (p.blade_seat_x, fy), (ox + k * (fx - ox), oy + k * (fy - oy)), (fx, fy)


def haunch_circle(p: Params) -> tuple[float, float, float]:
    """Centre and radius of the gusset's free edge: the circle through A and B that is tangent
    to the run's inner face at B (centre on the lever side)."""
    (ax, ay), (bx, by) = haunch_ends(p)
    toe = math.radians(p.front_toe_deg)
    e2 = (math.sin(toe), math.cos(toe))  # run normal, pointing away from the lever
    dx, dy = bx - ax, by - ay
    rho = (dx * dx + dy * dy) / (2 * (dx * e2[0] + dy * e2[1]))
    return bx - rho * e2[0], by - rho * e2[1], rho


def bend_section(p: Params, gusset: bool = True) -> float:
    """Blade thickness across the middle of the bend (along its bisector from the bend centre)."""
    if not gusset or p.haunch_len <= 0:
        return p.blade_t
    ox, oy, rho = haunch_circle(p)
    cx, cy = p.bend_center
    a = math.radians(p.bend_angle_deg / 2)
    wx, wy = cx - ox, cy - oy
    b = wx * math.cos(a) + wy * math.sin(a)
    r_in = -b + math.sqrt(b * b - (wx * wx + wy * wy - rho * rho))
    return p.bend_r + p.blade_t / 2 - r_in


def blade(p: Params = Params(), shift: float = 0.0) -> cq.Workplane:
    """Carbon guard blade. shift moves it along Y inside its slot (-adjust .. +adjust)."""
    t, h, R = p.blade_t, p.blade_h, p.bend_r
    x0, cx = p.blade_seat_x, p.blade_cx
    v_rear, v_b = p.blade_rear, p.bend_start
    # rear (bolted) plate, drawn in the YZ plane and extruded outward along +X
    rear = (
        cq.Workplane("YZ", origin=(x0, 0, 0))
        .center((v_rear + v_b) / 2, 0)
        .rect(v_b - v_rear, h)
        .extrude(t)
        .edges("|X and <Y")
        .fillet(p.blade_rear_r)
    )
    # 90 deg bend: the t x h section revolved about an axis parallel to Z
    bend = (
        cq.Workplane("XZ", origin=(0, v_b, 0))
        .center(cx, 0)
        .rect(t, h)
        .revolve(p.bend_angle_deg, (-R, 0, 0), (-R, 1, 0))
    )
    # straight run in front of the lever: drawn as if the bend were 90 deg (thickness along Y),
    # then swung about the bend axis so it starts where the (90 - toe) deg bend ends
    x_end, y_run = cx - R, v_b + R
    front = (
        cq.Workplane("XZ", origin=(0, y_run + t / 2, 0))
        .center(x_end - p.front_len / 2, 0)
        .rect(p.front_len, h)
        .extrude(t)
        .edges("|Y and <X")
        .fillet(p.tip_r)
        .rotate((x_end, v_b, 0), (x_end, v_b, 1), -p.front_toe_deg)
    )
    body = rear.union(bend).union(front)
    if p.haunch_len > 0:
        body = body.union(_haunch(p))
    body = _fillet_sharp(body, p.edge_r)
    slot = (
        cq.Workplane("YZ", origin=(x0 - 1, 0, 0))
        .center(p.slot_center, 0)
        .slot2D(p.slot_len, p.slot_w, 0)
        .extrude(t + 2)
    )
    return body.cut(slot).translate((0, shift, 0))


def cone_small_d(p: Params, size: str) -> float:
    big = SLEEVES[size][0] - 1.2
    taper = 2 * p.sleeve_recess_depth * math.tan(math.radians(p.cone_half_angle_deg))
    return max(p.cone_min_d, big - taper)


def expander_sleeve(p: Params, size: str) -> cq.Workplane:
    """Elastomer (TPU 85-95A / NBR) expander sleeve, seated behind the adapter spigot."""
    od = SLEEVES[size][0]
    x1 = -p.spigot_len
    x0 = x1 - p.sleeve_len
    cone_big = od - 1.2
    body = _revolve_x(
        [
            (x0 + p.sleeve_recess_depth, p.bolt_clear_d / 2),
            (x0 + p.sleeve_recess_depth, (cone_small_d(p, size) + 0.4) / 2),  # conical recess
            (x0, (cone_big + 0.2) / 2),
            (x0, od / 2 - 0.4),
            (x0 + 0.4, od / 2),
            (x1 - 0.4, od / 2),
            (x1, od / 2 - 0.4),
            (x1, p.bolt_clear_d / 2),
        ]
    )
    for ang in (0, 90):  # 4 slits from the far end let the sleeve open up evenly
        slit = (
            cq.Workplane("XY")
            .box(p.sleeve_slit_len * 2, p.sleeve_slit_w, od + 2)
            .translate((x0, 0, 0))
            .rotate((0, 0, 0), (1, 0, 0), ang)
        )
        body = body.cut(slit)
    return body


def expander_cone(p: Params, size: str) -> cq.Workplane:
    """Cone nut (6061-T6 or steel, tapped M6) seated in the sleeve's far-end recess."""
    big = SLEEVES[size][0] - 1.2
    x_seat = -p.spigot_len - p.sleeve_len  # far face of the sleeve
    xs = x_seat + p.sleeve_recess_depth  # small end of the taper
    xl = x_seat - p.cone_land
    r_t = p.cone_tap_d / 2
    return _revolve_x(
        [
            (xl, r_t),
            (xl, big / 2 - 0.4),
            (xl + 0.4, big / 2),
            (x_seat, big / 2),
            (xs, cone_small_d(p, size) / 2),
            (xs, r_t),
        ]
    )


# ------------------------------------------------------------------------------------------------
# wind guard: moulded shell with a slotted mount that slides along the blade run
# ------------------------------------------------------------------------------------------------
def run_frame(p: Params, s: float, shift: float = 0.0) -> cq.Location:
    """Frame on the outer face of the blade run, s mm along it from the bend: local x runs
    inboard along the run, local y points toward the lever (0 = outer face, blade_t = inner
    face), local z = Z. Parts below are drawn in this frame and moved into G with it."""
    ox, oy = p.run_point(s, -p.blade_t / 2)
    dx, dy = p.run_dir
    return cq.Plane(origin=(ox, oy + shift, 0), xDir=(dx, dy, 0), normal=(0, 0, 1)).location


def _box(x0, x1, y0, y1, z0, z1) -> cq.Workplane:
    return cq.Workplane("XY").box(x1 - x0, y1 - y0, z1 - z0, centered=False).translate((x0, y0, z0))


def _slot(p: Params) -> tuple[float, float, float]:
    """Slot half-height and its y limits (front, lever side) in the run frame."""
    c = p.clamp_clear
    return p.blade_h / 2 + c, -c, p.blade_t + c


def _clamp_screw_xy(p: Params) -> list[tuple[float, float]]:
    return [(p.clamp_screw_inset, p.blade_t / 2), (p.clamp_len - p.clamp_screw_inset, p.blade_t / 2)]


def _boss_face(p: Params) -> float:
    return -(_slot(p)[0] + p.clamp_wall + p.clamp_boss_h)


def mount_local(p: Params) -> cq.Workplane:
    """Slotted mount in the run frame: a sleeve closed all round the blade run, which slides
    through it, with two bosses underneath for the M4 heat-set inserts and grub screws that lock
    it. It is moulded / printed in one piece with the shell (see wind_guard_local)."""
    h, y0, y1 = _slot(p)
    w, L = p.clamp_wall, p.clamp_len
    body = _box(0, L, y0 - w, y1 + p.clamp_back, -(h + w), h + w).edges("|X").fillet(1.0)
    for x, y in _clamp_screw_xy(p):
        body = body.union(
            cq.Workplane("XY", origin=(x, y, _boss_face(p))).circle(p.clamp_boss_d / 2).extrude(p.clamp_boss_h + w / 2)
        )
    body = body.cut(_box(-1, L + 1, y0, y1, -h, h))
    for x, y in _clamp_screw_xy(p):
        body = body.cut(cq.Workplane("XY", origin=(x, y, _boss_face(p) - 1)).circle(p.insert_d / 2).extrude(p.insert_len + 1))
        body = body.cut(cq.Workplane("XY", origin=(x, y, _boss_face(p))).circle(2.1).extrude(p.clamp_boss_h + w + 1))
    return body


# Front-view outline of the wind guard, as (distance along the run from the shell's outboard
# end, height "up" on the bike above the blade's outer face) for shell_len = 230 and
# shell_crest = 84; scaled to the parameters. Points below 0 shape the rounded tip.
_SHELL_TOP = [(0, 2), (6, 38), (16, 61), (30, 75), (54, 84), (89, 82), (126, 70), (162, 49),
              (190, 26), (211, 5), (222, -3), (228, -9), (230, -16)]
_SHELL_X = (0, 29, 64, 104, 144, 184, 242)  # loft sections, same scale
_SHELL_RA, _SHELL_RK, _SHELL_RB, _SHELL_KINK = 140.0, 4.0, 250.0, 12.0  # panel radii, crease


def _arc_pt(c: tuple[float, float], r: float, ang: float) -> tuple[float, float]:
    return (c[0] + r * math.cos(math.radians(ang)), c[1] + r * math.sin(math.radians(ang)))


def _shell_profile(p: Params, phi0: float, sig_a: float, sig_b: float):
    """Centre line of one shell section in the run frame's (y, z) plane, as arcs
    (centre, radius, start angle, sweep), all turning the same way: the bend from the flange up
    to heading phi0, the lower panel, the crease and the upper panel."""
    pieces, head, p0 = [], 180.0, (-p.shell_flange, 0.0)
    for r, turn in ((p.shell_bend_r, 180.0 - phi0), (_SHELL_RA, sig_a), (_SHELL_RK, _SHELL_KINK), (_SHELL_RB, sig_b)):
        hy, hz = math.cos(math.radians(head)), math.sin(math.radians(head))
        c = (p0[0] + r * hz, p0[1] - r * hy)  # centre on the rider's side of the heading
        pieces.append((c, r, head + 90.0, turn))
        head -= turn
        p0 = _arc_pt(c, r, head + 90.0)
    return pieces


def _shell_up(p: Params, yz: tuple[float, float]) -> float:
    """Height of a run-frame (y, z) point "up" on the bike, above the blade's outer face."""
    a = math.radians(p.lever_deg)
    return yz[0] * math.sin(a) + yz[1] * math.cos(a)


def _shell_section(p: Params, x: float, phi0: float, sig_a: float, sig_b: float) -> cq.Wire:
    t2, pcs = p.shell_t / 2, _shell_profile(p, phi0, sig_a, sig_b)
    wp = cq.Workplane("YZ", origin=(x, 0, 0)).moveTo(-p.shell_flange, -t2)
    for c, r, a0, turn in pcs:  # front face, flange up to the top
        wp = wp.threePointArc(_arc_pt(c, r + t2, a0 - turn / 2), _arc_pt(c, r + t2, a0 - turn))
    c, r, a0, turn = pcs[-1]
    wp = wp.lineTo(*_arc_pt(c, r - t2, a0 - turn))
    for c, r, a0, turn in reversed(pcs):  # rider's side back down
        wp = wp.threePointArc(_arc_pt(c, r - t2, a0 - turn / 2), _arc_pt(c, r - t2, a0))
    return wp.close().val()


def wind_guard_local(p: Params, left: bool = False) -> cq.Workplane:
    """Moulded wind guard shell in the run frame (right-hand; left=True gives the mirror image).

    A flat flange, joined to the slotted mount that rides on the blade, bends up into a shield that stands in front
    of the hand on the bike, convex to the wind and curling back over the knuckles. A crease runs
    from the high outboard end down to the pointed tip. The shield is lofted through sections
    that lean back more at both ends, so it wraps round the hand, then trimmed to its front-view
    outline.
    """
    kx, ku, x0 = p.shell_len / 230.0, p.shell_crest / 84.0, -p.shell_out
    top = [(x0 + xs * kx, u * ku if u > 0 else u) for xs, u in _SHELL_TOP]

    def top_u(x: float) -> float:
        if x <= top[0][0]:
            return top[0][1]
        for (xa, ua), (xb, ub) in zip(top, top[1:]):
            if xa <= x <= xb:
                return ua + (ub - ua) * (x - xa) / (xb - xa)
        return top[-1][1]

    def top_of(phi0, sig_a, sig_b, piece):
        c, r, a0, turn = _shell_profile(p, phi0, sig_a, sig_b)[piece]
        return _shell_up(p, _arc_pt(c, r, a0 - turn))

    wires, n = [], len(_SHELL_X) - 1
    for i, xs in enumerate(_SHELL_X):
        x, f = x0 + xs * kx, i / n
        phi0 = 96.0 - p.lever_deg - 5 * (1 - min(1.0, f / 0.35)) ** 2 - 5 * max(0.0, (f - 0.6) / 0.4) ** 2
        crease = p.shell_crease[0] + (p.shell_crease[1] - p.shell_crease[0]) * xs / 226.0
        need = max(top_u(x), top_u(x - 20), top_u(x + 20), 20.0) + 8.0
        sig_a = 2.0
        while top_of(phi0, sig_a, 2.0, 1) < crease and sig_a < 60:
            sig_a += 0.5
        sig_b = 2.0
        while top_of(phi0, sig_a, sig_b, 3) < need and sig_b < 60:
            sig_b += 1.0
        wires.append(_shell_section(p, x, phi0, sig_a, sig_b))
    shell = cq.Workplane(obj=cq.Solid.makeLoft(wires, False))

    a = math.radians(p.lever_deg)  # trim to the outline seen from the front of the bike
    front = cq.Plane(origin=(0, 0, 0), xDir=(1, 0, 0), normal=(0, -math.cos(a), math.sin(a)))
    x_far = x0 + 260 * kx
    outline = (
        cq.Workplane(front).moveTo(x_far, -60).lineTo(x0 - 26, -60).lineTo(x0 - 26, -14)
        .spline(top, includeCurrent=True).lineTo(x_far, -60).close().extrude(300, both=True)
    )
    shell = shell.intersect(outline)

    y0, ys, fl_end, t = -p.shell_gap, -p.shell_flange, p.clamp_len + 20.0, p.shell_t
    flange = (
        cq.Workplane("XY").moveTo(x0, y0).lineTo(fl_end - 16, y0)
        .threePointArc((fl_end - 5, y0 - 4.5), (fl_end, ys)).lineTo(x0, ys).close()
        .extrude(t).translate((0, 0, -t / 2))
    )
    shell = shell.union(flange).union(mount_local(p))
    return shell.mirror("XY") if left else shell


def m4_grub_insert_local(p: Params, x: float, y: float) -> cq.Workplane:
    """M4 x 5.7 brass heat-set insert in the boss and an ISO 4029 M4 cup-point grub screw
    turned up through it until its tip bears on the blade's lower edge."""
    zb = _boss_face(p)
    insert = (
        cq.Workplane("XY", origin=(x, y, zb)).circle(p.insert_d / 2).extrude(p.insert_len - 0.5)
        .cut(cq.Workplane("XY", origin=(x, y, zb - 1)).circle(2.0).extrude(p.insert_len + 1))
    )
    grub = cq.Workplane("XY", origin=(x, y, -p.blade_h / 2 - p.m4_len)).circle(2.0).extrude(p.m4_len)
    return insert.union(grub)


def diffuser_parts(p: Params = Params(), pos: float | None = None, shift: float = 0.0):
    """Wind guard (shell with its slotted mount) and the two insert + grub screw sets, placed on
    the blade in G."""
    loc = run_frame(p, p.clamp_pos if pos is None else pos, shift)
    place = lambda wp: cq.Workplane(obj=wp.val().moved(loc))  # noqa: E731
    items = [("diffuser_shell", place(wind_guard_local(p)))]
    for i, (x, y) in enumerate(_clamp_screw_xy(p)):
        items.append((f"diffuser_screw_{i + 1}", place(m4_grub_insert_local(p, x, y))))
    return items


# ------------------------------------------------------------------------------------------------
# hardware (visual stand-ins, dimensions per ISO)
# ------------------------------------------------------------------------------------------------
def m6_shcs(p: Params) -> cq.Workplane:
    """ISO 4762 M6 socket head cap screw, head seated in the arm counterbore."""
    x_seat = p.head_seat_x
    head = _cyl_x(5.0, x_seat, x_seat + 6.0).faces(">X").edges().chamfer(0.5)
    head = head.cut(
        cq.Workplane("YZ", origin=(x_seat + 3.0, 0, 0))
        .polygon(6, 5.0 / math.cos(math.pi / 6))
        .extrude(3.1)
    )
    shank = _cyl_x(3.0, x_seat - p.m6_len, x_seat).faces("<X").chamfer(0.5)
    return head.union(shank)


def m5_button(p: Params, v: float) -> cq.Workplane:
    """ISO 7380 M5 button head screw (dk 9.5, k 2.75) on an ISO 7089 washer."""
    x_top = p.blade_seat_x + p.blade_t
    x_base = x_top + 1.0
    washer = _cyl_x(5.0, x_top, x_base).cut(_cyl_x(2.65, x_top - 1, x_base + 1))
    rs = (4.75**2 + 2.75**2) / (2 * 2.75)  # dome radius through the rim and the crown
    phi = math.atan2(4.75, rs - 2.75) / 2
    head = (
        cq.Workplane("XY")
        .moveTo(x_base, 0)
        .lineTo(x_base, 4.75)
        .threePointArc((x_base - rs + 2.75 + rs * math.cos(phi), rs * math.sin(phi)), (x_base + 2.75, 0))
        .close()
        .revolve(360, (0, 0, 0), (1, 0, 0))
    )
    head = head.cut(
        cq.Workplane("YZ", origin=(x_base + 1.3, 0, 0))
        .polygon(6, 3.0 / math.cos(math.pi / 6))
        .extrude(2.0)
    )
    shank = _cyl_x(2.5, x_base - p.m5_len, x_base)
    return washer.union(head).union(shank).translate((0, v, 0))


# ------------------------------------------------------------------------------------------------
# reference bike parts (approximate, only for fit checks and pictures)
# ------------------------------------------------------------------------------------------------
def ref_handlebar(p: Params, bar_id: float = 15.0) -> cq.Workplane:
    return _cyl_x(p.bar_od / 2, -330, 0).cut(_cyl_x(bar_id / 2, -331, 1))


def ref_grip() -> cq.Workplane:
    """Open-ended grip, flush with the bar end."""
    return _revolve_x(
        [(-128, 11.2), (-128, 20.0), (-124, 20.0), (-124, 16.5), (-1.0, 15.5), (0.0, 14.5), (0.0, 11.2)]
    )


def ref_lever() -> cq.Workplane:
    """Typical sport-bike brake lever: pivot ~170 mm inboard, tip ~15 mm inboard of the bar
    end, front face of the tip ~48 mm ahead of the bar axis (mid reach-adjuster setting)."""
    outline = [
        (-178, 42), (-160, 40), (-120, 37), (-60, 35), (-24, 35), (-15, 39), (-15, 45),
        (-22, 48), (-60, 50), (-120, 53), (-150, 58), (-170, 66), (-182, 60),
    ]
    lever = cq.Workplane("XY").polyline(outline).close().extrude(12).translate((0, 0, -6))
    boss = cq.Workplane("XY").circle(10).extrude(16).translate((-172, 52, -8))
    perch = (
        cq.Workplane("XY")
        .box(46, 40, 30)
        .translate((-200, 35, 0))
        .union(_revolve_x([(-222, 11.2), (-222, 19), (-182, 19), (-182, 11.2)]))
    )
    return lever.union(boss).union(perch)


# ------------------------------------------------------------------------------------------------
# assembly
# ------------------------------------------------------------------------------------------------
ANODISE = {
    "red": (0.78, 0.06, 0.08),
    "blue": (0.05, 0.25, 0.75),
    "gold": (0.85, 0.62, 0.17),
    "black": (0.08, 0.08, 0.09),
    "silver": (0.78, 0.79, 0.80),
}
CARBON_RGB = (0.10, 0.10, 0.11)
STEEL_RGB = (0.25, 0.25, 0.27)


def guard_parts(p: Params = Params(), size: str = "M", shift: float = 0.0, spigot: bool = True,
                colour: str = "red", diffuser: bool = True, clamp_pos: float | None = None):
    """All parts of one guard in the G frame: list of (name, Workplane, rgb)."""
    parts = [
        ("adapter", adapter(p, spigot), ANODISE[colour]),
        ("arm", arm(p), ANODISE[colour]),
        ("blade", blade(p, shift), CARBON_RGB),
        ("m6_bolt", m6_shcs(p), STEEL_RGB),
    ]
    for i, v in enumerate(p.screw_v):
        parts.append((f"m5_screw_{i + 1}", m5_button(p, v), STEEL_RGB))
    if spigot:
        parts += [
            ("expander_sleeve", expander_sleeve(p, size), (0.12, 0.12, 0.12)),
            ("expander_cone", expander_cone(p, size), (0.70, 0.70, 0.72)),
        ]
    if diffuser:
        for name, wp in diffuser_parts(p, clamp_pos, shift):
            rgb = STEEL_RGB if "screw" in name else ANODISE[colour]
            parts.append((name, wp, rgb))
    return parts


def reference_parts(p: Params = Params()):
    return [
        ("ref_handlebar", ref_handlebar(p), (0.55, 0.56, 0.58)),
        ("ref_grip", ref_grip(), (0.16, 0.16, 0.17)),
        ("ref_lever", ref_lever(), (0.62, 0.63, 0.66)),
    ]


def assembly(p: Params = Params(), with_reference: bool = True, **kw) -> cq.Assembly:
    assy = cq.Assembly(name="racing_lever_guard")
    items = guard_parts(p, **kw) + (reference_parts(p) if with_reference else [])
    for name, wp, rgb in items:
        assy.add(wp, name=name, color=cq.Color(*rgb))
    return assy


# 3D-printed variant: thicker blade, one size longer M5 screws
PRINT_PARAMS = replace(Params(), blade_t=8.0, m5_len=16.0)
