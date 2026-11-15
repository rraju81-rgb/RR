#!/usr/bin/env python3
"""
Split mould for the carbon-fibre cap (forged carbon compression moulding, or a wet layup).

The carbon part is the first model (1.5 mm wall, same inside) with one change for moulding: the bent-out ear
is replaced by a solid lug in the same place, on the same screw (params.carbon_variant). A two-part mould
forms the lug with plain pockets; a pin on the core forms its slot. The keeper tabs' tip corners are moulded
square (their R1.5 rounding faces sideways and down, which no rigid split mould can release) and are filed
round afterwards.

Three mould pieces:
    core    forms every inside surface, and the lug's slot with a pin on an arm; slides out along -x,
            through the cap's open root end, taking the slot pin with it
    top     forms the outside above the parting plane (mid-height of the lamp); lifts off in +z
    bottom  forms the outside below it; the part is lifted out of it last

Demoulding order: core (-x), top half (+z), then lift the part out of the bottom half.

    out/mould/mould_top.stl, mould_bottom.stl, mould_core.stl   3D printing, already oriented
    out/mould/*.step                                            assembly position, for CNC
    out/mould/mould_assembly.step                               everything in place
    out/mould/part_carbon.stl                                   the finished carbon part
    out/mould/summary.json                                      checks and sizes

Usage:  python3 mould.py
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import cadquery as cq

from build import OUT, run_checks
from model import CapGeometry, make_lamp
from params import Design, carbon_variant
from sheetmetal import obround, wire_from_segs

MOULD_OUT = OUT / "mould"
DOCS = OUT.parent / "docs"

WALL = 12.0          # mould wall around the part
BOLT_D = 6.6         # clearance for M6 clamp bolts
DOWEL_D = 6.1        # 6 mm dowel pins
TOL = 1e-3           # mm3: overlap volumes below this are coincident faces, not clashes


def box(x0, x1, y0, y1, z0, z1):
    return cq.Solid.makeBox(x1 - x0, y1 - y0, z1 - z0, cq.Vector(x0, y0, z0))


def vol(shape):
    return sum(s.Volume() for s in shape.Solids()) if shape is not None and shape.Solids() else 0.0


def tidy(shape):
    """Merge coplanar faces where OpenCascade can; keep the shape as it is where it can't."""
    try:
        out = shape.clean()
        return out if out.isValid() else shape
    except Exception:
        return shape


def valid(shape):
    """Return the shape, repaired by OpenCascade's shape fixer only if it fails the validity check."""
    return shape if shape.isValid() else shape.fix()


def fuse(shapes):
    acc = shapes[0]
    for s in shapes[1:]:
        acc = acc.fuse(s)
    return tidy(acc)


def largest_solid(shape):
    return max(shape.Solids(), key=lambda s: s.Volume())


def moulded_design() -> Design:
    """The carbon part as it leaves the mould: keeper-tab tip corners square, to be filed to R1.5."""
    d = carbon_variant()
    d.cap.tab_corner_r = 0.0
    return d


class Mould:
    def __init__(self, d: Design):
        self.d = d
        lamp, cap = d.lamp, d.cap
        self.g = g = CapGeometry(d)
        assert g.lug, "the mould is built for the carbon variant with a moulded lug"
        self.part, self.parts, self.frames = g.folded()
        self.finished_design = carbon_variant()
        self.finished = CapGeometry(self.finished_design).folded()               # finished part, rounded tab corners
        H = lamp.H
        self.zc = zc = H / 2
        self.y_in = g.y_back_inner                                             # back wall inner face, plan view
        self.z_ib, self.z_it = -cap.gap_z, H + cap.gap_z                       # plate inner faces
        self.x_ti = lamp.L + cap.gap_tip                                       # tip wall inner face
        self.x_to = g.x_tip_plate                                              # tip wall outer face
        pb = self.part.BoundingBox()
        self.pb = pb

        # mould block
        self.y_front = pb.ymin - 6.0                                           # front face of the core
        self.bx0, self.bx1 = pb.xmin - 14.0, pb.xmax + 14.0
        self.by0, self.by1 = self.y_front - 22.0, pb.ymax + 22.0
        self.bz0, self.bz1 = pb.zmin - WALL, pb.zmax + WALL
        self.x_start = self.bx0 - 22.0                                         # end of the core's handle

        self.core = self._core()
        self.features, self.groove = self._features()
        self.top, self.bottom = self._halves()
        self.validity = {k: (len(v.Solids()), v.isValid()) for k, v in
                         dict(core=self.core, top=self.top, bottom=self.bottom).items()}

    # ------------------------------------------------------------------ core
    def _core_section(self):
        """(y, z) outline of the core as true lines and arcs, constant along x: the cavity, the space under and
        in front of the keeper tabs, and a block in front of the lens. Its back edge is trimmed later by the
        back wall."""
        g, cap, H = self.g, self.d.cap, self.d.lamp.H
        r, th = cap.r, math.radians(cap.tab_angle)
        yt, zt = g.y_tab, self.z_it
        c = np.array([yt, zt - r])                                   # axis of the tab bend's inner surface
        a0 = np.array([yt, zt])
        am = c + r * np.array([-math.sin(th / 2), math.cos(th / 2)])
        a1 = c + r * np.array([-math.sin(th), math.cos(th)])
        p_in = a1 + cap.tab_flat * np.array([-math.cos(th), -math.sin(th)])     # inner corner of the tab's end
        p_out = p_in + cap.t * np.array([-math.sin(th), math.cos(th)])          # outer corner of the tab's end
        assert np.allclose(p_in, g.tab_profile()[-1], atol=1e-9)
        y_back = self.y_in(self.x_start - 2) + 5.0
        P = lambda v: (float(v[0]), float(v[1]))
        top = [("line", (y_back, zt), P(a0)), ("arc", P(a0), P(am), P(a1)), ("line", P(a1), P(p_in)),
               ("line", P(p_in), P(p_out)), ("line", P(p_out), (self.y_front, float(p_out[1])))]
        mir = lambda q: (q[0], H - q[1])
        bottom = [("line", mir(sg[2]), mir(sg[1])) if sg[0] == "line" else ("arc", mir(sg[3]), mir(sg[2]), mir(sg[1]))
                  for sg in reversed(top)]
        front = [("line", (self.y_front, float(p_out[1])), mir((self.y_front, float(p_out[1]))))]
        back = [("line", mir((y_back, zt)), (y_back, zt))]
        return top + front + bottom + back

    def _core(self):
        g, cap = self.g, self.d.cap
        r, zc = cap.r, self.zc
        x0, x1 = self.x_start, self.x_to
        plane = cq.Plane(origin=(x0, 0, 0), xDir=(0, 1, 0), normal=(1, 0, 0))
        face = cq.Face.makeFromWires(wire_from_segs(self._core_section())).located(cq.Location(plane))
        prism = cq.Solid.extrudeLinear(face, cq.Vector(x1 - x0, 0, 0))
        Y0 = self.y_front - 50
        back = (cq.Workplane("XY").workplane(offset=-100)
                .polyline([(x0 - 1, Y0), (x1 + 1, Y0), (x1 + 1, self.y_in(x1 + 1)), (x0 - 1, self.y_in(x0 - 1))])
                .close().extrude(200).val())
        k = prism.intersect(back)
        # round the two back edges with the part's inside bend radius, along the whole core
        xm = (x0 + x1) / 2
        sel = [cq.selectors.BoxSelector((xm - 1, self.y_in(xm) - 1, z - 0.5), (xm + 1, self.y_in(xm) + 1, z + 0.5))
               for z in (self.z_it, self.z_ib)]
        wk = cq.Workplane("XY").add(k)
        for s in sel:
            wk = wk.edges(s).fillet(r)
        k = wk.val()
        # tip zone: beyond the tip wall's inner face, behind where its flat meets the bend to the back wall.
        # There the core keeps only the columns over the part (the thin ledges between the tip wall and the
        # plates). Anything else lies in the +x shadow of that bend, so the core could not come out past it,
        # or sits under a mould half, so the core could not be laid into the half. It goes to the halves.
        y_t5 = float(self.frames["TIP"][0][1])       # where the tip wall's flat meets that bend
        zone = box(self.x_ti, x1 + 1, y_t5, self.y_in(x0) + 10, -100, 100)
        core = k.cut(self.part).cut(zone.cut(self._plan_prism(zone)))
        core = core.cut(box(x0 - 1, self.bx0, self.y_in(self.bx0), 1000, -100, 100))   # straight handle outside
        # arm from the handle through the block, behind the cap's back wall, to the lug; it carries the pin
        # that forms the lug's slot
        xl, _ya, yc, _zl, _R = g.lug_geometry()
        hl, hw = cap.ear_slot_len / 2, cap.ear_slot_w / 2
        arm = box(x0, xl, self.y_in(xl) - 0.5, yc + hl + 3.0, zc - hw - 3.0, zc + hw + 3.0)
        pplane = cq.Plane(origin=(xl - 0.5, 0, 0), xDir=(0, 1, 0), normal=(1, 0, 0))
        slot = cq.Face.makeFromWires(wire_from_segs(obround((yc, zc), cap.ear_slot_len, cap.ear_slot_w, 0)))
        pin = cq.Solid.extrudeLinear(slot.located(cq.Location(pplane)), cq.Vector(0.5 + cap.lug_len + 1.0, 0, 0))
        # shoulder outside the block: stops the core moving towards the tip under clamping pressure
        bx0 = self.bx0
        shoulder = box(bx0 - 12, bx0, self.y_front, self.y_in(bx0), self.z_ib - 4, self.z_it + 4)
        return valid(largest_solid(core.fuse(arm).fuse(pin).fuse(shoulder)))

    def _plan_prism(self, zone):
        """Vertical prism over the part's outline in plan, inside `zone`: the part's sections through the middle
        of the tip-wall band and of both plates, extruded over the full height."""
        t = self.d.cap.t
        local = self.part.intersect(zone)
        prisms = []
        for z in (self.zc, self.z_it + t / 2, self.z_ib - t / 2):
            plane = cq.Face.makePlane(4000, 4000, cq.Vector(0, 0, z), cq.Vector(0, 0, 1))
            for f in local.intersect(plane).Faces():
                prisms.append(cq.Solid.extrudeLinear(f.moved(cq.Location(cq.Vector(0, 0, -100 - z))), cq.Vector(0, 0, 200)))
        return fuse(prisms)

    # ------------------------------------------------------------------ block features
    def _features(self):
        zc = self.zc
        xs = (self.bx0 + 12, self.bx1 - 12)
        yf, yb = self.y_front - 11, self.by1 - 11
        bolts = [cq.Solid.makeCylinder(BOLT_D / 2, self.bz1 - self.bz0 + 2, cq.Vector(x, y, self.bz0 - 1))
                 for x in xs for y in (yf, yb)]
        xm = (self.bx0 + self.bx1) / 2
        dowels = [cq.Solid.makeCylinder(DOWEL_D / 2, 20, cq.Vector(xm, y, zc - 10)) for y in (yf, yb)]
        notches = [box(xm + dx - 6, xm + dx + 6, y0, y1, zc - 1.5, zc + 1.5)
                   for dx in (-30, 30) for (y0, y1) in ((self.by0 - 1, self.by0 + 4), (self.by1 - 4, self.by1 + 1))]
        feats = fuse(bolts + dowels + notches)
        # overflow groove in the bottom half's parting face, 3 mm outside the cavity
        plane = cq.Face.makePlane(4000, 4000, cq.Vector(0, 0, zc), cq.Vector(0, 0, 1))
        faces = self.part.fuse(self.core).intersect(plane).Faces()
        f = faces[0]
        for x in faces[1:]:
            f = f.fuse(x)
        outer = max(tidy(f).Faces(), key=lambda q: q.Area()).outerWire()
        ring = cq.Face.makeFromWires(outer.offset2D(5.0, "arc")[0], [outer.offset2D(3.0, "arc")[0]])
        groove = cq.Solid.extrudeLinear(ring, cq.Vector(0, 0, -1.5))
        groove = groove.intersect(box(self.bx0, self.bx1, self.by0, self.by1, self.bz0, self.bz1))
        return feats, groove

    def _halves(self):
        zc = self.zc
        block = box(self.bx0, self.bx1, self.by0, self.by1, self.bz0, self.bz1)
        region = block.cut(self.part).cut(self.core).cut(self.features)
        top = largest_solid(region.intersect(box(self.bx0 - 1, self.bx1 + 1, self.by0 - 1, self.by1 + 1, zc, self.bz1 + 1)))
        bot = region.intersect(box(self.bx0 - 1, self.bx1 + 1, self.by0 - 1, self.by1 + 1, self.bz0 - 1, zc))
        bot = largest_solid(bot.cut(self.groove))
        return valid(top), valid(bot)

    # ------------------------------------------------------------------ checks
    def checks(self):
        rows = []

        def add(name, value, req, ok):
            rows.append(dict(check=name, value=value, requirement=req, ok=bool(ok)))

        # the finished carbon part still fits the lamp (same checks as the steel cap)
        fd = self.finished_design
        fg = CapGeometry(fd)
        fpart, fparts, fframes = fg.folded()
        frows, _ = run_checks(fd, fg, fpart, fparts, fframes, make_lamp(fd, fg.ear_hole_centre(fframes)))
        for r in frows:
            add("Fit: " + r["check"], r["value"], r["requirement"], r["ok"])

        P = {k: v.copy() for k, v in dict(part=self.part, core=self.core, top=self.top, bottom=self.bottom).items()}
        part, core, top, bottom = (P[k] for k in ("part", "core", "top", "bottom"))
        finished = self.finished[0].copy()
        missing = vol(finished.cut(part))
        add("Cavity contains all of the finished carbon part", f"{missing:.4f} mm3 missing", f"< {TOL}", missing < TOL)
        extra = part.cut(finished)
        n_corners = 4 * len(self.d.cap.tab_x)
        z = [s.BoundingBox() for s in extra.Solids()]
        at_tips = all(b.zmax > self.z_it - 4 or b.zmin < self.z_ib + 4 for b in z) and all(b.ymax < 0 for b in z)
        add("Only extra material: square tab tip corners", f"{vol(extra):.2f} mm3 in {len(z)} corners",
            f"{n_corners} corners, at the tab tips", len(z) == n_corners and at_tips)
        for k in ("core", "top", "bottom"):
            s = self.validity[k]
            add(f"{k} is one valid solid", f"{s[0]} solid, valid {s[1]}", "1, True", s[0] == 1 and s[1])
        names = list(P)
        worst = 0.0
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                worst = max(worst, vol(P[names[i]].intersect(P[names[j]])))
        add("No two pieces overlap (part, core, top, bottom)", f"largest overlap {worst:.4f} mm3", f"< {TOL}", worst < TOL)
        block = box(self.bx0, self.bx1, self.by0, self.by1, self.bz0, self.bz1)
        rest = block.cut(top).cut(bottom).cut(core).cut(part).cut(self.features.copy()).cut(self.groove.copy())
        add("Pieces and part fill the block exactly (no voids)", f"left over {vol(rest):.4f} mm3", f"< {TOL}", vol(rest) < TOL)

        def sweep(moving, obstacles, vec, dists):
            obst = fuse(obstacles)
            return max(vol(moving.moved(cq.Location(cq.Vector(*(np.array(vec) * s)))).intersect(obst)) for s in dists)

        lift = [0.25, 0.5, 1, 2, 4, 8, 16, 30, 60]
        clash = sweep(core, [bottom], (0, 0, 1), lift)
        add("Loading: core drops straight into the bottom half", f"clash {clash:.4f} mm3", f"< {TOL}", clash < TOL)
        clash = sweep(top, [core, bottom], (0, 0, 1), lift)
        add("Loading: top half closes straight down over the core", f"clash {clash:.4f} mm3", f"< {TOL}", clash < TOL)
        L_core = self.x_to - self.x_start + 5
        clash = sweep(core, [part, top, bottom], (-1, 0, 0), [0.5, 1, 2, 4, 8, 16, 32, 64, L_core])
        add("Demould 1: core (with the slot pin) pulls out (-x), halves still closed", f"clash {clash:.4f} mm3", f"< {TOL}", clash < TOL)
        clash = sweep(top, [part, bottom], (0, 0, 1), lift)
        add("Demould 2: top half lifts off (+z)", f"clash {clash:.4f} mm3", f"< {TOL}", clash < TOL)
        clash = sweep(part, [bottom], (0, 0, 1), lift)
        add("Demould 3: part lifts out of the bottom half (+z)", f"clash {clash:.4f} mm3", f"< {TOL}", clash < TOL)
        return rows


def print_oriented(shape, how):
    """Lay a mould piece on the bed in its best printing orientation, centred on the origin."""
    if how == "flip":            # top half: parting face up
        shape = shape.rotate((0, 0, 0), (1, 0, 0), 180)
    elif how == "front-down":    # core: its flat front face on the bed, layer lines along the pull direction
        shape = shape.rotate((0, 0, 0), (1, 0, 0), 90)
    bb = shape.BoundingBox()
    return shape.translate((-(bb.xmin + bb.xmax) / 2, -(bb.ymin + bb.ymax) / 2, -bb.zmin))


def build_mould(out: Path = MOULD_OUT):
    out.mkdir(parents=True, exist_ok=True)
    for stale in ("mould_pin.stl", "mould_pin.step", "part_as_moulded.stl"):     # from the four-piece version
        (out / stale).unlink(missing_ok=True)
    m = Mould(moulded_design())

    pieces = dict(top=(m.top, "flip"), bottom=(m.bottom, "as is"), core=(m.core, "front-down"))
    for name, (shape, how) in pieces.items():
        cq.exporters.export(shape, str(out / f"mould_{name}.step"))
        cq.exporters.export(print_oriented(shape.copy(), how), str(out / f"mould_{name}.stl"),
                            tolerance=0.01, angularTolerance=0.1)
    asm = cq.Assembly(name="indicator_cap_mould")
    colors = dict(top=(0.55, 0.65, 0.78), bottom=(0.62, 0.66, 0.72), core=(0.93, 0.62, 0.22))
    for name, (shape, _how) in pieces.items():
        asm.add(shape, name=f"mould_{name}", color=cq.Color(*colors[name], 1.0))
    asm.add(m.part, name="part_as_moulded", color=cq.Color(0.08, 0.08, 0.09, 1.0))
    asm.save(str(out / "mould_assembly.step"))
    fin = m.finished[0]
    cq.exporters.export(fin, str(out / "part_carbon.stl"), tolerance=0.01, angularTolerance=0.1)
    cq.exporters.export(fin, str(out / "part_carbon.step"))

    def size(s):
        b = s.BoundingBox()
        return [round(b.xlen, 1), round(b.ylen, 1), round(b.zlen, 1)]

    part_v = m.part.Volume()
    cap = m.d.cap
    summary = dict(
        part=("Carbon variant of the first model: 1.5 mm wall, same inside; the bent ear is replaced by a solid "
              f"{cap.lug_len:.0f} mm lug on the same screw. Keeper-tab tip corners are moulded square and filed to R1.5."),
        part_volume_mm3=round(part_v, 1),
        forged_carbon_part_g=round(fin.Volume() * 1.5e-3, 1),
        charge_g=dict(fibre=round(part_v * 0.5 * 1.8e-3 * 1.2, 1), resin=round(part_v * 0.5 * 1.15e-3 * 1.2, 1),
                      note="50 % fibre by volume, 20 % extra for flash"),
        block_mm=[round(m.bx1 - m.bx0, 1), round(m.by1 - m.by0, 1), round(m.bz1 - m.bz0, 1)],
        parting_plane_z=m.zc,
        pieces={k: dict(size=size(s), volume_cm3=round(s.Volume() / 1000, 1)) for k, (s, _h) in pieces.items()},
        hardware="4 x M6 bolts with washers and nuts, 2 x 6 mm dowel pins",
        demould_order=["core out along -x (brings the slot pin with it)", "top half up",
                       "lift the part out of the bottom half"],
    )
    rows = m.checks()
    summary["checks"] = rows
    summary["all_checks_pass"] = all(r["ok"] for r in rows)
    (out / "summary.json").write_text(json.dumps(summary, indent=2))
    return m, summary


def section_paths(shape, x=None, z=None):
    """Cross-section of a solid in the plane x = const, as (y, z) loops, or z = const, as (x, y) loops.
    Per face: outer loop first, then holes."""
    from figures import wire_points
    if z is None:
        corners, uv = [(x, -500, -500), (x, 500, -500), (x, 500, 500), (x, -500, 500)], (lambda p: (p[1], p[2]))
    else:
        corners, uv = [(-500, -500, z), (500, -500, z), (500, 500, z), (-500, 500, z)], (lambda p: (p[0], p[1]))
    big = cq.Face.makeFromWires(cq.Wire.makePolygon([cq.Vector(*c) for c in corners], close=True))
    out = []
    for f in big.intersect(shape).Faces():
        loops = [f.outerWire()] + list(f.innerWires())
        out.append([[uv(p) for p in wire_points(w)] for w in loops])
    return out


def fig_sections(m: Mould, path: Path):
    """Two cuts through the closed mould (at a keeper tab; through the lug and the core's slot pin) and a plan
    of the bottom half with the core and the part in it."""
    from drawing import View
    from figures import Fig

    cap = m.d.cap
    F = Fig(780, 1058)
    k = 4.85
    W = (m.by1 - m.by0) * k
    Hh = (m.bz1 - m.bz0) * k
    pieces = [("m-top", m.top), ("m-bot", m.bottom), ("m-core", m.core), ("m-part", m.part)]
    ca = math.cos(m.g.al)
    xl, _ya, yc, _zl, R = m.g.lug_geometry()

    def draw(view, x=None, z=None):
        for cls, shp in pieces:
            for loops in section_paths(shp.copy(), x=x, z=z):
                d = " ".join("M" + " L".join(f"{view.xy(*q)[0]:.2f},{view.xy(*q)[1]:.2f}" for q in loop) + " Z"
                             for loop in loops)
                F.add(f'<path class="{cls}" d="{d}" fill-rule="evenodd"/>')
        if z is None:
            a, b = view.xy(m.by0 - 3, m.zc), view.xy(m.by1 + 3, m.zc)
            F.line(a[0], a[1], b[0], b[1], "parting")

    def callout(view, u, v, X, Y, lines):
        x0, y0 = view.xy(u, v)
        F.line(x0, y0, X - 6, Y - 4, "dim")
        F.arrow(x0, y0, math.atan2(y0 - (Y - 4), x0 - (X - 6)), 1.5)
        for i, t in enumerate(lines):
            F.text(X, Y + i * 15, t, "dimtxt" if i == 0 else "small")

    xa = cap.tab_x[0]
    F.text(20, 24, f"A  CUT AT A KEEPER TAB ({xa:.0f} mm FROM THE ROOT FACE), LOOKING FROM THE TIP", "label")
    va = View(F, 24, 40 + Hh, k, m.by0, m.bz0)
    draw(va, xa)
    X = 24 + W + 22
    callout(va, m.by1 - 18, m.bz1 - 7, X, 70, ["Top half", "2nd: lifts off upward"])
    callout(va, 8.0, m.zc + 2, X, 122, ["Core", "1st: slides out along the", "lamp axis (into the page)"])
    callout(va, m.y_in(xa) + 0.75 / ca, m.zc - 3, X, 188, ["Carbon part, 1.5 mm"])
    callout(va, m.by1 - 18, m.bz0 + 7, X, 228, ["Bottom half", "3rd: lift the part out of it"])
    callout(va, m.y_in(xa) + cap.t / ca + 4.0, m.zc - 0.75, X, 272, ["Overflow groove", "excess resin runs out here"])

    bolt_x = m.bx0 + 12                          # cut through the lug, clear of the clamp bolt holes
    xb = max(xl + cap.lug_len / 2, bolt_x + BOLT_D / 2 + 0.2)
    oy = 360
    F.text(20, oy - 16, "B  CUT THROUGH THE LUG AND THE CORE'S SLOT PIN", "label")
    vb = View(F, 24, oy + Hh, k, m.by0, m.bz0)
    draw(vb, xb)
    callout(vb, yc + R * 0.55, m.zc + R * 0.55, X, oy + 40, ["Lug of the part", "solid, replaces the bent ear;", "same screw, same place"])
    callout(vb, yc, m.zc, X, oy + 112, ["Slot pin on the core", "forms the slot; comes out", "with the core"])

    # C: plan just below the parting plane, top half off
    kc = 3.3
    u0 = m.x_start - 14
    oc = 672
    F.text(20, oc - 16, "C  PLAN JUST BELOW THE PARTING PLANE: TOP HALF OFF, LENS SIDE AT THE BOTTOM", "label")
    vc = View(F, 24, oc + (m.by1 - m.by0) * kc, kc, u0, m.by0)
    draw(vc, z=m.zc - 0.5)
    yh = (m.y_front + m.y_in(m.bx0)) / 2                        # middle of the core's handle
    p0, p1 = vc.xy(m.x_start - 1.5, yh), vc.xy(m.x_start - 12, yh)
    F.line(p0[0], p0[1], p1[0], p1[1], "dim")
    F.arrow(p1[0], p1[1], math.pi, 1.6)
    F.text(p1[0], p1[1] - 8, "pull", "dimtxt")
    hl = cap.ear_slot_len / 2
    callout(vc, m.bx0 + 8, yc + hl + 1.5, X, oc + 12, ["Arm on the core", "runs behind the cap's back", "wall to the lug"])
    callout(vc, xl + cap.lug_len / 2, yc, X, oc + 80, ["Slot pin", "inside the lug's slot"])
    callout(vc, 40, m.y_in(40) + 0.75 / ca, X, oc + 132, ["Carbon part", "back wall, tip wall and lug"])
    callout(vc, 30, 6, X, oc + 184, ["Core", "comes out to the left by its", "handle, before the top half"])
    callout(vc, m.bx1 - 12, m.y_front - 11 + BOLT_D / 2, X, oc + 250, ["Bottom half", "bolt and dowel holes,", "overflow groove"])
    F.text(20, 1044, "Red dashed line (A, B): parting plane at mid-height of the lamp. Dowel pins align the halves; 4 bolts clamp them.", "small")
    F.write(path, "Cross-sections and a plan of the mould")


if __name__ == "__main__":
    m, s = build_mould()
    print(f"block {s['block_mm']} mm, parting plane z = {s['parting_plane_z']}")
    for k, v in s["pieces"].items():
        print(f"  {k:7s} {v['size']} mm  {v['volume_cm3']} cm3")
    print(f"part {s['part_volume_mm3']} mm3 as moulded -> {s['forged_carbon_part_g']} g finished; charge {s['charge_g']}")
    for r in s["checks"]:
        print(f"  [{'ok' if r['ok'] else 'FAIL'}] {r['check']}: {r['value']}  (need {r['requirement']})")
    print("ALL CHECKS PASS" if s["all_checks_pass"] else "*** CHECK FAILURES ***")
    fig_sections(m, DOCS / "fig_mould_section.svg")
