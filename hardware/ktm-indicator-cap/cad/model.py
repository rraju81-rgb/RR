"""
Geometry of the indicator cap and of the (schematic) lamp it fits over.

Panels of the cap, all folded from the back wall:

        TAB  TAB                 keeper tabs  (35 deg, down over the lens chamfer)
     +------------+
     | TOP plate  |              90 deg
     +------------+
 TIP |  BACK wall | EAR          tip wall 90-taper deg, ear 90-taper deg the other way
     +------------+
     | BOTTOM     |              90 deg
     +------------+
        TAB  TAB

The part is symmetric top-to-bottom, so the same piece fits a left or a right
lamp (turn it over) and, for the same lamp, front or rear.
"""
from __future__ import annotations

import math

import numpy as np
import cadquery as cq

from params import Design
from sheetmetal import Panel, fold, unfold, fuse_all, obround, rot90, unit


class CapGeometry:
    """Derived dimensions + the panel tree."""

    def __init__(self, d: Design):
        self.d = d
        lamp, cap, mount = d.lamp, d.cap, d.mount
        t, r = cap.t, cap.r
        al = lamp.taper
        self.al = al
        sa, ca = math.sin(al), math.cos(al)
        self.u2 = np.array([ca, -sa])   # along the back face, root -> tip (plan view)
        self.n2 = np.array([sa, ca])    # outward normal of the back face  (plan view)

        self.Hc = lamp.H + 2 * cap.gap_z            # clear height between the plates
        self.hb = self.Hc - 2 * r                   # flat height of the back wall
        self.ht = self.hb - 2 * cap.tip_h_relief    # height of the tip wall
        self.he = self.hb - 2 * cap.relief          # height of the ear / its strap

        # stations along the back wall, measured along u from the head's back-root corner
        self.s_tip = (lamp.L + cap.gap_tip - r - (cap.gap_back - r) * sa) / ca
        self.s_root = (-mount.G_ear + (t + r) * (1 - sa) - cap.gap_back * sa) / ca
        self.Lbw = self.s_tip - self.s_root
        self.s_b = (cap.plate_root_x - (cap.gap_back - r) * sa) / ca
        self.pT_a = cap.plate_bend_start
        self.pT_b = self.s_tip - self.s_b
        self.W = self.pT_b - self.pT_a              # length of the plate bends
        assert self.Lbw - self.pT_b >= 1.5, "ear strap too short: raise mount.G_ear or plate_root_x"

        self.tip_angle = 90.0 - math.degrees(al)
        self.ear_angle = cap.ear_angle if cap.ear_angle is not None else 90.0 - math.degrees(al)

        self.x_tip_plate = lamp.L + cap.gap_tip + t   # plates end flush with the outside of the tip wall
        self.y_tab = self._solve_tab_line()           # bend tangent line of the keeper tabs
        self.y_edge = self.y_tab + cap.edge_setback   # plate front edge between the tabs

        # tip wall reaches from its bend to the lens joint line
        cy = lamp.D_root + (cap.gap_back - r) * ca - self.s_tip * sa
        self.tip_len = cy - cap.tip_front_y
        # ear slot centre, measured from the ear's bend tangent line (ear square to the lamp axis)
        self.q_hole = mount.screw_behind_back - (cap.gap_back + t + r) * ca + self.s_root * sa
        assert self.q_hole - cap.ear_slot_len / 2 >= 2 * t, (
            "ear slot too close to the bend: the screw is too near the lamp for a folded ear "
            f"(need screw_behind_back >= {2 * t + cap.ear_slot_len / 2 + (cap.gap_back + t + r) * ca - self.s_root * sa:.1f})")
        self.p_hole = self.he / 2 - mount.screw_dz    # ear local p runs downwards

        self.root = self._build()

    # ------------------------------------------------------------------ helpers
    def y_tangent(self, x):
        """y of the plate bend tangent line at lamp station x (plan view)."""
        lamp, cap = self.d.lamp, self.d.cap
        sa, ca = math.sin(self.al), math.cos(self.al)
        s = (x - (cap.gap_back - cap.r) * sa) / ca
        return lamp.D_root + (cap.gap_back - cap.r) * ca - s * sa

    def plan_to_top(self, x, y):
        """Lamp plan coordinates -> local (p, q) of the TOP plate."""
        cap, lamp = self.d.cap, self.d.lamp
        v = np.array([x, y - lamp.D_root])
        q = (cap.gap_back - cap.r) - float(v @ self.n2)
        p = self.s_tip - self.pT_a - float(v @ self.u2)
        return np.array([p, q])

    def _dir_to_top(self, dx, dy):
        v = np.array([dx, dy])
        return np.array([-float(v @ self.u2), -float(v @ self.n2)])

    def tab_profile(self, y_tab=None, n=24):
        """Inner surface of a keeper tab in the (y, z) section: bend arc + flat."""
        lamp, cap = self.d.lamp, self.d.cap
        y_tab = self.y_tab if y_tab is None else y_tab
        th = math.radians(cap.tab_angle)
        z0 = lamp.H + cap.gap_z
        pts = [(y_tab + 3.0, z0), (y_tab, z0)]
        for i in range(1, n + 1):
            a = th * i / n
            pts.append((y_tab - cap.r * math.sin(a), z0 - cap.r * (1 - math.cos(a))))
        ye, ze = pts[-1]
        pts.append((ye - cap.tab_flat * math.cos(th), ze - cap.tab_flat * math.sin(th)))
        return pts

    def lens_top_profile(self):
        """Top of the lamp in the (y, z) section: flat housing top, chamfer, lens face."""
        lamp = self.d.lamp
        return [
            (lamp.D_tip, lamp.H),
            (0.0, lamp.H),
            (-lamp.lens_run, lamp.H - lamp.lens_drop),
            (-lamp.lens_run - lamp.lens_nose, lamp.H - lamp.lens_drop - 1.0),
            (-lamp.lens_run - lamp.lens_nose, lamp.H / 2),
        ]

    def tab_gap(self, y_tab=None):
        from shapely.geometry import LineString
        return LineString(self.tab_profile(y_tab)).distance(LineString(self.lens_top_profile()))

    def _solve_tab_line(self):
        """Place the tab bend so the tab clears the lens chamfer by exactly gap_tab."""
        cap = self.d.cap
        lo, hi = -8.0, 6.0     # the gap shrinks as the bend line moves back (+y); 0 once the tab hits the housing
        assert self.tab_gap(lo) > cap.gap_tab > self.tab_gap(hi)
        for _ in range(60):
            mid = (lo + hi) / 2
            if self.tab_gap(mid) > cap.gap_tab:
                lo = mid
            else:
                hi = mid
        return (lo + hi) / 2

    # ------------------------------------------------------------------ panels
    def _plate(self, mirror: bool, name: str):
        lamp, cap = self.d.lamp, self.d.cap
        xt, xr = self.x_tip_plate, cap.plate_root_x
        ye, yt = self.y_edge, self.y_tab
        hw = cap.tab_w / 2

        plan, radii = [], []

        def add(x, y, rad=0.0):
            plan.append((x, y))
            radii.append(rad)

        add(xt, self.y_tangent(xt), 1.0)            # tip edge meets the bend tangent line
        add(xt, ye, cap.r_corner)                   # exposed tip/front corner
        tabs = []
        for xc in sorted(cap.tab_x, reverse=True):  # walk the front edge from tip to root
            add(xc + hw, ye, 1.0)
            add(xc + hw, yt)
            add(xc - hw, yt)
            add(xc - hw, ye, 1.0)
            tabs.append(((xc + hw, yt), (xc - hw, yt)))
        add(xr, ye, cap.r_corner)                   # exposed root/front corner
        add(xr, self.y_tangent(xr))                 # = bend end B
        pts = [self.plan_to_top(x, y) for x, y in plan]
        pts.append(np.array([0.0, 0.0]))            # bend end A (collinear vertex)
        radii.append(0.0)

        cuts = []
        for xc in cap.slot_x:
            y_lo, y_hi = ye + cap.slot_margin, self.y_tangent(xc) - cap.slot_margin
            span = y_hi - y_lo
            if span < cap.slot_w + 0.5:
                continue
            a = math.radians(cap.slot_angle)
            length = (span - cap.slot_w) / math.sin(a) + cap.slot_w
            c = self.plan_to_top(xc, (y_lo + y_hi) / 2)
            dl = self._dir_to_top(math.cos(a), math.sin(a))
            cuts.append((c, length, math.degrees(math.atan2(dl[1], dl[0]))))

        tab_edges = [(self.plan_to_top(*a), self.plan_to_top(*b)) for a, b in tabs]

        if mirror:
            W = self.W
            pts = [np.array([W - p[0], p[1]]) for p in pts][::-1]
            radii = radii[::-1]
            cuts = [(np.array([W - c[0], c[1]]), ln, 180.0 - ang) for c, ln, ang in cuts]
            tab_edges = [(np.array([W - b[0], b[1]]), np.array([W - a[0], a[1]])) for a, b in tab_edges]

        panel = Panel(name, [tuple(p) for p in pts], radii, [obround(c, ln, cap.slot_w, ang) for c, ln, ang in cuts])
        for i, (a, b) in enumerate(tab_edges):
            tab = Panel(f"{name}_TAB{i + 1}", [(0, 0), (cap.tab_w, 0), (cap.tab_w, cap.tab_flat), (0, cap.tab_flat)],
                        [0, 0, 1.5, 1.5])
            panel.attach(a, b, cap.tab_angle, "up", tab, f"bend_{name}_TAB{i + 1}")
        return panel

    def _ear_outline(self):
        """Ear flange. Straight out of its bend, round-ended; widens into a flag when the screw is off mid-height."""
        from shapely.geometry import Polygon
        from sheetmetal import filleted_outline, segs_points
        cap = self.d.cap
        t, r, he = cap.t, cap.r, self.he
        qh, ph, R = self.q_hole, self.p_hole, self.he / 2
        qn = t + r                                  # run straight out of the bend before widening (no bend relief needed)
        pA, pB = max(he, ph + R), min(0.0, ph - R)
        pts, radii = [(0.0, 0.0), (he, 0.0)], [0.0, 0.0]
        if pA > he + 1e-9:
            pts += [(he, qn), (pA, qn + (pA - he))]    # 45 degree shoulder
            radii += [2.0, 2.0]
        pts += [(pA, qh + R), (pB, qh + R)]
        radii += [R, R]
        if pB < -1e-9:
            pts += [(pB, qn - pB), (0.0, qn)]
            radii += [2.0, 2.0]
        hint = (f"ear cannot reach a screw {self.d.mount.screw_dz:+.1f} mm off mid-height at "
                f"{self.d.mount.screw_behind_back:.1f} mm behind the lamp: the screw needs to be further out "
                "(mount.screw_behind_back) or the ear needs a dog-leg")
        try:
            outline = Polygon(segs_points(filleted_outline(pts, radii), 16))
        except ValueError as e:
            raise ValueError(hint) from e
        slot = Polygon(segs_points(obround((ph, qh), cap.ear_slot_len, cap.ear_slot_w, 90), 16))
        if not (outline.is_valid and outline.buffer(-2 * t + 1e-6).contains(slot)):
            raise ValueError(hint)
        return pts, radii

    def _build(self):
        cap = self.d.cap
        hb, ht, he, Lbw = self.hb, self.ht, self.he, self.Lbw
        a, b = self.pT_a, self.pT_b

        back = Panel(
            "BACK",
            [(0, -ht / 2), (0, ht / 2), (a, hb / 2), (b, hb / 2), (b, he / 2), (Lbw, he / 2),
             (Lbw, -he / 2), (b, -he / 2), (b, -hb / 2), (a, -hb / 2)],
        )
        back.attach((a, hb / 2), (b, hb / 2), 90, "up", self._plate(False, "TOP"), "bend_TOP")
        back.attach((b, -hb / 2), (a, -hb / 2), 90, "up", self._plate(True, "BOTTOM"), "bend_BOTTOM")

        tip = Panel("TIP", [(0, 0), (ht, 0), (ht, self.tip_len), (0, self.tip_len)], [0, 0, 2.5, 2.5])
        back.attach((0, -ht / 2), (0, ht / 2), self.tip_angle, "up", tip, "bend_TIP")

        ear = Panel("EAR", *self._ear_outline(), [obround((self.p_hole, self.q_hole), cap.ear_slot_len, cap.ear_slot_w, 90)])
        back.attach((Lbw, he / 2), (Lbw, -he / 2), self.ear_angle, "down", ear, "bend_EAR")
        return back

    # ------------------------------------------------------------------ evaluation
    def back_frame(self):
        """3D frame of the back wall: reference face = inside face."""
        lamp, cap = self.d.lamp, self.d.cap
        u3 = np.array([self.u2[0], self.u2[1], 0.0])
        n3 = np.array([self.n2[0], self.n2[1], 0.0])
        O = np.array([0.0, lamp.D_root, 0.0]) + cap.gap_back * n3 + self.s_tip * u3 + np.array([0, 0, lamp.H / 2])
        return O, -u3, np.array([0.0, 0.0, 1.0]), n3

    def folded(self):
        cap = self.d.cap
        parts, frames = fold(self.root, self.back_frame(), cap.t, cap.r)
        return fuse_all([s for _, s in parts]), parts, frames

    def flat(self):
        """Laser blank. Returns (blank_face, blank_solid, faces, bend_lines, placed)."""
        cap = self.d.cap
        faces, lines, placed = unfold(self.root, cap.ba)
        # fuse as thin solids (robust), then take the single planar face on top as the 2D blank
        solid = fuse_all([cq.Solid.extrudeLinear(f, cq.Vector(0, 0, cap.t)) for _, f in faces])
        tops = [f for f in solid.Faces() if f.geomType() == "PLANE" and abs(f.Center().z - cap.t) < 1e-6]
        assert len(tops) == 1, f"blank did not fuse into one piece ({len(tops)} faces)"
        blank = tops[0].moved(cq.Location(cq.Vector(0, 0, -cap.t)))
        return blank, solid, faces, lines, placed

    def ear_hole_centre(self, frames):
        """Screw axis position in lamp coordinates (centre of the ear slot, on the seat face)."""
        O, eP, eQ, eN = frames["EAR"]
        return O + self.p_hole * eP + self.q_hole * eQ


# ---------------------------------------------------------------------------- lamp (schematic)
def make_lamp(d: Design, hole_centre=None):
    """Schematic OEM lamp + the bit of the bike it plugs into.

    Returns dict name -> cq.Shape. Only HOUSING and LENS are used for fit checks;
    the rest is context for pictures.
    """
    lamp, mount = d.lamp, d.mount
    L, H = lamp.L, lamp.H
    out = {}

    housing = (
        cq.Workplane("XY")
        .polyline([(0, 0), (L, 0), (L, lamp.D_tip), (0, lamp.D_root)])
        .close()
        .extrude(H)
    )
    out["HOUSING"] = housing.val()

    # lens: chamfered bar in front of the joint line (section in the y-z plane, extruded along x)
    yn = -lamp.lens_run - lamp.lens_nose
    sec = [
        (0, 0), (0, H),
        (-lamp.lens_run, H - lamp.lens_drop),
        (yn, H - lamp.lens_drop - 1.0),
        (yn, lamp.lens_drop + 1.0),
        (-lamp.lens_run, lamp.lens_drop),
    ]
    lens = cq.Workplane(cq.Plane(origin=(0, 0, 0), xDir=(0, 1, 0), normal=(1, 0, 0))).polyline(sec).close().extrude(L)
    out["LENS"] = lens.val()

    zc = H / 2
    neck = cq.Workplane("XY").box(lamp.neck_len, lamp.neck_dy, lamp.neck_dz, centered=False).translate(
        (-lamp.neck_len, lamp.neck_y0, zc - lamp.neck_dz / 2)
    )
    out["NECK"] = neck.val()

    sock_dx = 12.0
    socket = cq.Workplane("XY").box(sock_dx, lamp.neck_dy + 8, lamp.neck_dz + 8, centered=False).translate(
        (-lamp.neck_len - sock_dx, lamp.neck_y0 - 4, zc - lamp.neck_dz / 2 - 4)
    )
    out["SOCKET"] = socket.val()

    if hole_centre is not None:
        hx, hy, hz = hole_centre
        boss_len = 14.0
        boss = cq.Workplane(cq.Plane(origin=(hx - boss_len, hy, hz), xDir=(0, 1, 0), normal=(1, 0, 0))).circle(8.0).extrude(boss_len)
        out["BOSS"] = boss.val()
        body = cq.Workplane("XY").box(10.0, hy + 14 - (lamp.neck_y0 - 8), lamp.neck_dz + 16, centered=False).translate(
            (-lamp.neck_len - sock_dx - 2, lamp.neck_y0 - 8, zc - lamp.neck_dz / 2 - 8)
        )
        out["BODY"] = body.val()
    return out


def make_hardware(d: Design, hole_centre):
    """Screw + washer through the ear, for pictures."""
    cap, mount = d.cap, d.mount
    hx, hy, hz = hole_centre
    pl = cq.Plane(origin=(hx + cap.t, hy, hz), xDir=(0, 1, 0), normal=(1, 0, 0))
    washer = cq.Workplane(pl).circle(7.0).circle(mount.screw_d / 2 + 0.15).extrude(1.2)
    head = cq.Workplane(pl).workplane(offset=1.2).circle(4.75).extrude(3.2).faces(">X").edges().fillet(1.2)
    shank = cq.Workplane(cq.Plane(origin=(hx - 12.0, hy, hz), xDir=(0, 1, 0), normal=(1, 0, 0))).circle(
        mount.screw_d / 2
    ).extrude(12.0 + cap.t + 1.2)
    return {"WASHER": washer.val(), "SCREW": head.union(shank).val()}


def make_liners(g: CapGeometry, frames):
    """EPDM foam liner pads at their compressed (installed) thickness. Returns name -> (solid, free_thickness)."""
    d = g.d
    lamp, cap = d.lamp, d.cap
    out = {}
    L, H = lamp.L, lamp.H
    inset = 1.5
    # top / bottom pads follow the housing top (a tapered quadrilateral)
    quad = [(inset, inset + g.y_edge), (L - inset, inset + g.y_edge), (L - inset, lamp.D_tip - inset), (inset, lamp.D_root - inset)]
    top = cq.Workplane("XY").workplane(offset=H).polyline(quad).close().extrude(cap.gap_z)
    bot = cq.Workplane("XY").workplane(offset=-cap.gap_z).polyline(quad).close().extrude(cap.gap_z)
    out["LINER_TOP"] = (top.val(), 1.0)
    out["LINER_BOTTOM"] = (bot.val(), 1.0)
    # back pad on the back face of the housing
    u3 = np.array([g.u2[0], g.u2[1], 0.0])
    n3 = np.array([g.n2[0], g.n2[1], 0.0])
    Lb = L / math.cos(g.al)
    pl = cq.Plane(origin=(0, lamp.D_root, 0), xDir=tuple(u3), normal=tuple(n3))
    back = cq.Workplane(pl).polyline([(inset, -inset), (Lb - inset, -inset), (Lb - inset, -H + inset), (inset, -H + inset)]).close().extrude(cap.gap_back)
    out["LINER_BACK"] = (back.val(), 2.0)
    # tip pad
    tipp = cq.Workplane(cq.Plane(origin=(L, 0, 0), xDir=(0, 1, 0), normal=(1, 0, 0))).polyline(
        [(1.0, inset), (lamp.D_tip - 1.0, inset), (lamp.D_tip - 1.0, H - inset), (1.0, H - inset)]
    ).close().extrude(cap.gap_tip)
    out["LINER_TIP"] = (tipp.val(), 3.0)
    return out
