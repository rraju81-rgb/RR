#!/usr/bin/env python3
"""
Split mould for the carbon-fibre cap (forged carbon compression moulding, or a wet layup).

The carbon part is the first model (1.5 mm wall, same inside) with the bent-out ear replaced by a solid lug in the
same place, on the same screw (params.carbon_variant).

Three mould pieces, stacked from the back of the lamp to the front. Seen from above with the lug at the top, the
way the part lies on a print bed:
    top     the back of the cap, the lug, the top and bottom faces of the cap and the tip end;
            comes off towards the back of the lamp (+y)
    middle  the inside of the cap, plus the lug's slot, formed by a pin on an arm behind the back wall
    bottom  the front: the keeper tabs (outside, ends and rounded corners) and the front edges;
            comes off towards the front (-y)

Demoulding: bottom piece off (-y), top piece off (+y), then the cap slides off the middle mould along the lamp
axis (+x), the way it slides off the lamp. Loading uses the same paths in reverse.

The three slashes in each plate are closed holes across both opening directions, so no piece could pull out of
them: the plates are moulded plain and the slashes are cut afterwards (optional). Everything else comes out of the
mould finished, including the keeper tabs' rounded corners.

    out/mould/mould_top.stl, mould_middle.stl, mould_bottom.stl   3D printing, already oriented
    out/mould/*.step                                               assembly position, for CNC
    out/mould/mould_assembly.step                                  everything in place
    out/mould/part_carbon.stl                                      the finished carbon part
    out/mould/summary.json                                         checks and sizes

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

WALL = 12.0          # mould wall in front of and behind the part
WALL_Z = 20.0        # above and below the part: room for the clamp bolts outside the overflow groove
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
    """The carbon part as it leaves the mould: plain plates (the slashes are cut afterwards)."""
    d = carbon_variant()
    d.cap.slot_x = ()
    return d


class Mould:
    def __init__(self, d: Design):
        self.d = d
        lamp, cap = d.lamp, d.cap
        self.g = g = CapGeometry(d)
        assert g.lug, "the mould is built for the carbon variant with a moulded lug"
        self.part, self.parts, self.frames = g.folded()
        self.finished_design = carbon_variant()
        self.finished = CapGeometry(self.finished_design).folded()               # finished part, with the slashes
        H = lamp.H
        self.zc = H / 2
        self.y_in = g.y_back_inner                                             # back wall inner face, plan view
        self.z_ib, self.z_it = -cap.gap_z, H + cap.gap_z                       # plate inner faces
        self.x_ti = lamp.L + cap.gap_tip                                       # tip wall inner face
        self.x_to = g.x_tip_plate                                              # tip wall outer face
        self.p_in = np.array(g.tab_profile()[-1])                              # inner corner of the top tab's end
        self.y_core_front = float(self.p_in[0])                                # front face of the middle mould
        # top/bottom parting plane: behind the plates' rounded front corners, which face partly forwards
        self.y_p = g.y_edge + cap.r_corner + 0.5
        pb = self.part.BoundingBox()
        self.pb = pb

        # mould block
        self.bx0, self.bx1 = pb.xmin - 14.0, pb.xmax + 14.0
        self.by0, self.by1 = pb.ymin - WALL, pb.ymax + WALL
        self.bz0, self.bz1 = pb.zmin - WALL_Z, pb.zmax + WALL_Z
        self.x_start = self.bx0 - 22.0                                         # end of the middle mould's handle

        self.core = self._core()
        self.fills = self._corner_fills()
        self.part = tidy(self.part.fuse(self.fills))
        self.features, self.groove = self._features()
        self.top, self.bottom = self._pieces()
        self.validity = {k: (len(v.Solids()), v.isValid()) for k, v in
                         dict(middle=self.core, top=self.top, bottom=self.bottom).items()}

    # ------------------------------------------------------------------ middle mould
    def _core_section(self):
        """(y, z) outline of the middle mould as true lines and arcs, constant along x: the inside of the cap up to
        the keeper tabs' inner faces, closed at the front by a flat face through the tabs' tip corners. Its back
        edge is trimmed later by the back wall."""
        g, cap, H = self.g, self.d.cap, self.d.lamp.H
        r, th = cap.r, math.radians(cap.tab_angle)
        yt, zt = g.y_tab, self.z_it
        c = np.array([yt, zt - r])                                   # axis of the tab bend's inner surface
        a0 = np.array([yt, zt])
        am = c + r * np.array([-math.sin(th / 2), math.cos(th / 2)])
        a1 = c + r * np.array([-math.sin(th), math.cos(th)])
        p_in = a1 + cap.tab_flat * np.array([-math.cos(th), -math.sin(th)])     # inner corner of the tab's end
        assert np.allclose(p_in, self.p_in, atol=1e-9)
        y_back = self.y_in(self.x_start - 2) + 5.0
        P = lambda v: (float(v[0]), float(v[1]))
        mir = lambda q: (q[0], H - q[1])
        top = [("line", (y_back, zt), P(a0)), ("arc", P(a0), P(am), P(a1)), ("line", P(a1), P(p_in))]
        bottom = [("line", mir(sg[2]), mir(sg[1])) if sg[0] == "line" else ("arc", mir(sg[3]), mir(sg[2]), mir(sg[1]))
                  for sg in reversed(top)]
        front = [("line", P(p_in), mir(P(p_in)))]
        back = [("line", mir((y_back, zt)), (y_back, zt))]
        return top + front + bottom + back

    def _core(self):
        g, cap, H = self.g, self.d.cap, self.d.lamp.H
        r, zc = cap.r, self.zc
        x0, x1 = self.x_start, self.x_to
        plane = cq.Plane(origin=(x0, 0, 0), xDir=(0, 1, 0), normal=(1, 0, 0))
        face = cq.Face.makeFromWires(wire_from_segs(self._core_section())).located(cq.Location(plane))
        prism = cq.Solid.extrudeLinear(face, cq.Vector(x1 - x0, 0, 0))
        Y0 = self.y_core_front - 50
        back = (cq.Workplane("XY").workplane(offset=-100)
                .polyline([(x0 - 1, Y0), (x1 + 1, Y0), (x1 + 1, self.y_in(x1 + 1)), (x0 - 1, self.y_in(x0 - 1))])
                .close().extrude(200).val())
        k = prism.intersect(back)
        # round the two back edges with the part's inside bend radius, along the whole length
        xm = (x0 + x1) / 2
        sel = [cq.selectors.BoxSelector((xm - 1, self.y_in(xm) - 1, z - 0.5), (xm + 1, self.y_in(xm) + 1, z + 0.5))
               for z in (self.z_it, self.z_ib)]
        wk = cq.Workplane("XY").add(k)
        for s in sel:
            wk = wk.edges(s).fillet(r)
        k = wk.val()
        # tip zone: beyond the tip wall's inner face, behind where its flat meets the bend to the back wall.
        # There the middle mould keeps only the columns over the part (the thin ledges between the tip wall and the
        # plates). Anything else lies in the +x shadow of that bend, so the cap could not slide off past it.
        y_t5 = float(self.frames["TIP"][0][1])       # where the tip wall's flat meets that bend
        zone = box(self.x_ti, x1 + 1, y_t5, self.y_in(x0) + 10, -100, 100)
        core = k.cut(self.part).cut(zone.cut(self._plan_prism(zone)))
        core = core.cut(box(x0 - 1, self.bx0, self.y_in(self.bx0), 1000, -100, 100))   # straight handle outside
        # arm from the handle, behind the cap's back wall, to the lug; its pin forms the lug's slot and ends flush
        # with the lug's far face, so the top piece can lift straight off past it
        xl, _ya, yc, _zl, _R = g.lug_geometry()
        hl, hw = cap.ear_slot_len / 2, cap.ear_slot_w / 2
        arm = box(x0, xl, self.y_in(xl) - 0.5, yc + hl + 3.0, zc - hw - 3.0, zc + hw + 3.0)
        pplane = cq.Plane(origin=(xl - 0.5, 0, 0), xDir=(0, 1, 0), normal=(1, 0, 0))
        slot = cq.Face.makeFromWires(wire_from_segs(obround((yc, zc), cap.ear_slot_len, cap.ear_slot_w, 0)))
        pin = cq.Solid.extrudeLinear(slot.located(cq.Location(pplane)), cq.Vector(0.5 + cap.lug_len, 0, 0))
        # keys: a rib across the top and the bottom face near the root end. The top and bottom pieces close over
        # them, so the middle mould can't slide along the lamp axis while the mould is shut.
        kx0, kx1 = self.bx0 + 3.0, self.bx0 + 9.0
        yk = self.y_in(kx1)
        zt_tip = float(self.p_in[1])
        keys = [box(kx0, kx1, self.y_core_front, yk, zt_tip, self.z_it + 3.0),
                box(kx0, kx1, self.y_core_front, yk, self.z_ib - 3.0, H - zt_tip)]
        return valid(largest_solid(fuse([core, arm, pin] + keys)))

    def _corner_fills(self):
        """At the back-tip corner, outside the tip-wall band, the back wall and the two plate bends end square to the
        tapered back wall: their end faces, and the sloping relief cut along the back wall's top edge, lean towards
        the front (by up to 9 degrees) and would hook the top piece as it lifts off backwards. Fill the thin wedge in
        front of each such face (under 0.5 mm) so that nothing the top piece touches faces forwards."""
        prisms = []
        for f in self.part.Faces():
            if f.geomType() != "PLANE":
                continue
            c = f.Center()
            if not (self.x_ti - 6 < c.x < self.x_to and c.y > self.y_p):
                continue
            n = f.normalAt(c)
            if -0.5 < n.y < -1e-6 and n.x > 0.1:          # faces the relief (+x) and leans forwards (-y)
                prisms.append(cq.Solid.extrudeLinear(f, cq.Vector(0, -3, 0)))
        assert prisms, "expected the leaning faces at the back-tip corner"
        return fuse(prisms).cut(self.core).cut(self.part)

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
        yp = self.y_p

        def along_y(x, z, dia, y0, length):
            return cq.Solid.makeCylinder(dia / 2, length, cq.Vector(x, y0, z), cq.Vector(0, 1, 0))

        xs = (self.bx0 + 8.0, self.x_to - 8.0)            # both inside the bottom piece's length
        zs = (self.bz0 + 8.0, self.bz1 - 8.0)
        bolts = [along_y(x, z, BOLT_D, self.by0 - 1, self.by1 - self.by0 + 2) for x in xs for z in zs]
        xm = (self.bx0 + self.x_to) / 2
        dowels = [along_y(xm, z, DOWEL_D, yp - 10, 20) for z in zs]
        notches = [box(xm + dx - 6, xm + dx + 6, yp - 1.5, yp + 1.5, z0, z1)
                   for dx in (-30, 30) for (z0, z1) in ((self.bz0 - 1, self.bz0 + 4), (self.bz1 - 4, self.bz1 + 1))]
        feats = fuse(bolts + dowels + notches)
        # overflow groove in the bottom piece's parting face, 3 mm outside the cavity
        plane = cq.Face.makePlane(4000, 4000, cq.Vector(0, yp, 0), cq.Vector(0, 1, 0))
        faces = self.part.fuse(self.core).intersect(plane).Faces()
        f = faces[0]
        for q in faces[1:]:
            f = f.fuse(q)
        outer = max(tidy(f).Faces(), key=lambda q: q.Area()).outerWire()
        ring = cq.Face.makeFromWires(outer.offset2D(5.0, "arc")[0], [outer.offset2D(3.0, "arc")[0]])
        groove = cq.Solid.extrudeLinear(ring, cq.Vector(0, -1.5, 0))
        groove = groove.intersect(box(self.bx0, self.x_to, self.by0, self.by1, self.bz0, self.bz1))
        return feats, groove

    def _pieces(self):
        block = box(self.bx0, self.bx1, self.by0, self.by1, self.bz0, self.bz1)
        region = block.cut(self.part).cut(self.core).cut(self.features)
        front = box(self.bx0 - 1, self.x_to, self.by0 - 1, self.y_p, self.bz0 - 1, self.bz1 + 1)
        bottom = largest_solid(region.intersect(front).cut(self.groove))
        top = largest_solid(region.cut(front))                 # the back, and the whole tip end
        return valid(top), valid(bottom)

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

        P = {k: v.copy() for k, v in dict(part=self.part, middle=self.core, top=self.top, bottom=self.bottom).items()}
        part, core, top, bottom = (P[k] for k in ("part", "middle", "top", "bottom"))
        finished = self.finished[0].copy()
        missing = vol(finished.cut(part))
        add("Cavity contains all of the finished carbon part", f"{missing:.4f} mm3 missing", f"< {TOL}", missing < TOL)
        extra = part.cut(finished)
        n_slash = 2 * len(fd.cap.slot_x)
        slashes = [s for s in extra.Solids() if s.Volume() > 5.0]
        wedges = [s for s in extra.Solids() if s.Volume() <= 5.0]
        in_plates = all(b.zmin > self.z_it - 0.01 or b.zmax < self.z_ib + 0.01 for b in (s.BoundingBox() for s in slashes))
        at_corner = all(b.xmin > self.x_ti - 6 and b.ymin > self.y_p for b in (s.BoundingBox() for s in wedges))
        add("Extra material: the slashes (cut after moulding)", f"{sum(s.Volume() for s in slashes):.1f} mm3 in "
            f"{len(slashes)} slots", f"{n_slash} slots, in the plates", len(slashes) == n_slash and in_plates)
        add("Extra material: corner fills at the back-tip corner", f"{sum(s.Volume() for s in wedges):.2f} mm3 in "
            f"{len(wedges)} wedges", "< 2 mm3, at that corner", sum(s.Volume() for s in wedges) < 2.0 and at_corner)
        for k in ("middle", "top", "bottom"):
            s = self.validity[k]
            add(f"{k} is one valid solid", f"{s[0]} solid, valid {s[1]}", "1, True", s[0] == 1 and s[1])
        names = list(P)
        worst = 0.0
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                worst = max(worst, vol(P[names[i]].intersect(P[names[j]])))
        add("No two pieces overlap (part, middle, top, bottom)", f"largest overlap {worst:.4f} mm3", f"< {TOL}", worst < TOL)
        block = box(self.bx0, self.bx1, self.by0, self.by1, self.bz0, self.bz1)
        rest = block.cut(top).cut(bottom).cut(core).cut(part).cut(self.features.copy()).cut(self.groove.copy())
        add("Pieces and part fill the block exactly (no voids)", f"left over {vol(rest):.4f} mm3", f"< {TOL}", vol(rest) < TOL)

        def sweep(moving, obstacles, vec, dists):
            obst = fuse(obstacles)
            return max(vol(moving.moved(cq.Location(cq.Vector(*(np.array(vec) * s)))).intersect(obst)) for s in dists)

        lift = [0.25, 0.5, 1, 2, 4, 8, 16, 30, 60, 90]
        clash = sweep(bottom, [part, core, top], (0, -1, 0), lift)
        add("Demould 1: bottom piece comes off forwards (-y)", f"clash {clash:.4f} mm3", f"< {TOL}", clash < TOL)
        clash = sweep(top, [part, core], (0, 1, 0), lift)
        add("Demould 2: top piece comes off backwards (+y)", f"clash {clash:.4f} mm3", f"< {TOL}", clash < TOL)
        slide = [0.25, 0.5, 1, 2, 3, 4, 6, 8, 12, 16, 24, 32, 48, 64, self.x_to - self.pb.xmin + 3]
        clash = sweep(part, [core], (1, 0, 0), slide)
        add("Demould 3: cap slides off the middle mould along the lamp (+x)", f"clash {clash:.4f} mm3", f"< {TOL}", clash < TOL)
        clash = sweep(top, [part, core, bottom], (0, 1, 0), lift)
        add("Either order: top piece also comes off first", f"clash {clash:.4f} mm3", f"< {TOL}", clash < TOL)
        return rows


def print_oriented(shape, how):
    """Lay a mould piece on the bed in its printing orientation, centred on the origin."""
    if how == "back-down":       # top piece: back face on the bed, cavity facing up
        shape = shape.rotate((0, 0, 0), (1, 0, 0), -90)
    elif how == "front-down":    # bottom piece (cavity up) and middle mould (layer lines along the slide)
        shape = shape.rotate((0, 0, 0), (1, 0, 0), 90)
    bb = shape.BoundingBox()
    return shape.translate((-(bb.xmin + bb.xmax) / 2, -(bb.ymin + bb.ymax) / 2, -bb.zmin))


def build_mould(out: Path = MOULD_OUT):
    out.mkdir(parents=True, exist_ok=True)
    for stale in ("mould_pin.stl", "mould_pin.step", "part_as_moulded.stl", "mould_core.stl", "mould_core.step"):
        (out / stale).unlink(missing_ok=True)          # from earlier versions
    m = Mould(moulded_design())

    pieces = dict(top=(m.top, "back-down"), middle=(m.core, "front-down"), bottom=(m.bottom, "front-down"))
    for name, (shape, how) in pieces.items():
        cq.exporters.export(shape, str(out / f"mould_{name}.step"))
        cq.exporters.export(print_oriented(shape.copy(), how), str(out / f"mould_{name}.stl"),
                            tolerance=0.01, angularTolerance=0.1)
    asm = cq.Assembly(name="indicator_cap_mould")
    colors = dict(top=(0.55, 0.65, 0.78), middle=(0.93, 0.62, 0.22), bottom=(0.62, 0.66, 0.72))
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
              f"{cap.lug_len:.0f} mm lug on the same screw. Moulded with plain plates: the slashes are cut afterwards."),
        layout="top piece (back, lug, top and bottom faces, tip end) / middle mould (inside) / bottom piece (front, tabs)",
        part_volume_mm3=round(part_v, 1),
        forged_carbon_part_g=round(fin.Volume() * 1.5e-3, 1),
        charge_g=dict(fibre=round(part_v * 0.5 * 1.8e-3 * 1.2, 1), resin=round(part_v * 0.5 * 1.15e-3 * 1.2, 1),
                      note="50 % fibre by volume, 20 % extra for flash"),
        block_mm=[round(m.bx1 - m.bx0, 1), round(m.by1 - m.by0, 1), round(m.bz1 - m.bz0, 1)],
        parting_plane_y=round(m.y_p, 2),
        pieces={k: dict(size=size(s), volume_cm3=round(s.Volume() / 1000, 1)) for k, (s, _h) in pieces.items()},
        hardware="4 x M6 bolts 90 mm long (or threaded rod) with washers and nuts, 2 x 6 mm dowel pins",
        demould_order=["bottom piece off, forwards", "top piece off, backwards",
                       "slide the cap off the middle mould along the lamp axis, towards the tip"],
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
    """A plan at mid-height of the lamp, lug side up, and a section at a keeper tab, back of the lamp up."""
    from drawing import View
    from figures import Fig

    cap = m.d.cap
    F = Fig(780, 762)
    pieces = [("m-top", m.top), ("m-bot", m.bottom), ("m-core", m.core), ("m-part", m.part)]
    ca = math.cos(m.g.al)
    xl, _ya, yc, _zl, _R = m.g.lug_geometry()
    yp = m.y_p

    def draw(view, x=None, z=None, swap=False):
        for cls, shp in pieces:
            for loops in section_paths(shp.copy(), x=x, z=z):
                if swap:
                    loops = [[(q[1], q[0]) for q in loop] for loop in loops]
                d = " ".join("M" + " L".join(f"{view.xy(*q)[0]:.2f},{view.xy(*q)[1]:.2f}" for q in loop) + " Z"
                             for loop in loops)
                F.add(f'<path class="{cls}" d="{d}" fill-rule="evenodd"/>')

    def callout(view, u, v, X, Y, lines):
        x0, y0 = view.xy(u, v)
        F.line(x0, y0, X - 6, Y - 4, "dim")
        F.arrow(x0, y0, math.atan2(y0 - (Y - 4), x0 - (X - 6)), 1.5)
        for i, t in enumerate(lines):
            F.text(X, Y + i * 15, t, "dimtxt" if i == 0 else "small")

    def move_arrow(view, u, v, du, dv, text):
        a, b = view.xy(u, v), view.xy(u + du, v + dv)
        F.line(a[0], a[1], b[0], b[1], "dim")
        F.arrow(b[0], b[1], math.atan2(b[1] - a[1], b[0] - a[0]), 1.6)
        F.text(b[0] + 8, b[1] + 4, text, "dimtxt")

    # A: plan at mid-height of the lamp, lug side up (as the part lies on a print bed, seen from above)
    ka = 3.25
    u0, v0 = m.x_start - 4, m.by0 - 2
    Ha = (m.by1 + 2 - v0) * ka
    F.text(20, 24, "A  PLAN AT MID-HEIGHT OF THE LAMP, LUG SIDE UP", "label")
    va = View(F, 24, 40 + Ha, ka, u0, v0)
    draw(va, z=m.zc - 0.5)
    a, b = va.xy(m.x_to, m.y_core_front), va.xy(m.x_to, m.by0 - 2)    # at this height they meet only here
    F.line(a[0], a[1], b[0], b[1], "parting")
    move_arrow(va, 40, m.by1 - 9, 0, 7, "off")
    move_arrow(va, 40, m.by0 + 9, 0, -7, "off")
    X = 24 + (m.bx1 + 2 - u0) * ka + 18
    callout(va, 20, 47, X, 52, ["Top piece", "the back, the lug, the top and", "bottom faces and the tip end"])
    callout(va, xl + cap.lug_len / 2, yc, X, 116, ["Slot pin", "on the middle mould's arm"])
    callout(va, 45, m.y_in(45) + 0.75 / ca, X, 164, ["Carbon part"])
    callout(va, 25, 8, X, 198, ["Middle mould", "the inside of the cap; the cap", "slides off it to the right"])
    callout(va, 25, m.by0 + 5, X, 262, ["Bottom piece", "the front, with the keeper tabs"])

    # B: section at a keeper tab, back of the lamp up, top of the lamp to the right
    kb = 3.6
    xb = cap.tab_x[0]
    ub0, vb0 = m.bz0 - 2, m.by0 - 2
    Hb = (m.by1 + 2 - vb0) * kb
    oyb = 380
    F.text(20, oyb - 16, f"B  SECTION AT A KEEPER TAB ({xb:.0f} mm FROM THE ROOT FACE), BACK OF THE LAMP UP", "label")
    vb = View(F, 24, oyb + Hb, kb, ub0, vb0)
    draw(vb, x=xb, swap=True)
    a, b = vb.xy(m.bz0 - 2, yp), vb.xy(m.bz1 + 2, yp)
    F.line(a[0], a[1], b[0], b[1], "parting")
    zt_mid = m.z_it + cap.t / 2
    Xb = 24 + (m.bz1 + 2 - ub0) * kb + 26
    callout(vb, m.zc, m.by1 - 8, Xb, oyb + 20, ["Top piece", "comes off upwards (to the back of the lamp)"])
    callout(vb, m.z_it + cap.t + 9, 14, Xb, oyb + 70, ["Top piece wraps over the cap's", "top and bottom faces too"])
    callout(vb, zt_mid, 18, Xb, oyb + 118, ["Carbon part, 1.5 mm"])
    callout(vb, m.zc, 12, Xb, oyb + 152, ["Middle mould", "the cap slides off it along the lamp", "(out of the page)"])
    callout(vb, m.z_it - 1.2, -3.0, Xb, oyb + 216, ["Keeper tab", "formed by the bottom piece,", "rounded corners included"])
    callout(vb, m.z_it + cap.t + 4.0, yp - 0.75, Xb, oyb + 280, ["Overflow groove", "excess resin runs out here"])
    callout(vb, m.zc, m.by0 + 5, Xb, oyb + 330, ["Bottom piece", "comes off downwards (to the front)"])
    F.text(20, 748, "Red dashed line: where the top and bottom pieces meet. Dowel pins align them; 4 bolts clamp them.", "small")
    F.write(path, "Plan and section of the mould")


if __name__ == "__main__":
    m, s = build_mould()
    print(f"block {s['block_mm']} mm, parting plane y = {s['parting_plane_y']}")
    for k, v in s["pieces"].items():
        print(f"  {k:7s} {v['size']} mm  {v['volume_cm3']} cm3")
    print(f"part {s['part_volume_mm3']} mm3 as moulded -> {s['forged_carbon_part_g']} g finished; charge {s['charge_g']}")
    for r in s["checks"]:
        print(f"  [{'ok' if r['ok'] else 'FAIL'}] {r['check']}: {r['value']}  (need {r['requirement']})")
    print("ALL CHECKS PASS" if s["all_checks_pass"] else "*** CHECK FAILURES ***")
    fig_sections(m, DOCS / "fig_mould_section.svg")
