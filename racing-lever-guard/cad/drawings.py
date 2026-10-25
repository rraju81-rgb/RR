"""Dimensioned A3 drawings (third-angle projection) generated from the CAD model.

    python drawings.py ../docs/drawings/lever_guard_drawings.pdf

Writes the multi-page PDF plus one PNG preview per sheet next to it. Edges come from
OCC's hidden-line removal, so every view is a true projection of the solids in
lever_guard.py; dimensions are taken from the same Params.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.backends.backend_pdf import PdfPages  # noqa: E402
from matplotlib.patches import Circle, PathPatch, Polygon, Rectangle  # noqa: E402
from matplotlib.path import Path as MPath  # noqa: E402

import cadquery as cq  # noqa: E402
from OCP.BRepAdaptor import BRepAdaptor_CompCurve, BRepAdaptor_Curve  # noqa: E402
from OCP.BRepLib import BRepLib  # noqa: E402
from OCP.GCPnts import GCPnts_QuasiUniformDeflection  # noqa: E402
from OCP.gp import gp_Ax2, gp_Dir, gp_Pnt  # noqa: E402
from OCP.HLRAlgo import HLRAlgo_Projector  # noqa: E402
from OCP.HLRBRep import HLRBRep_Algo, HLRBRep_HLRToShape  # noqa: E402
from OCP.TopAbs import TopAbs_EDGE  # noqa: E402
from OCP.TopExp import TopExp_Explorer  # noqa: E402
from OCP.TopoDS import TopoDS  # noqa: E402

import lever_guard as lg  # noqa: E402

W, H = 420.0, 297.0
INK, REF, DIMC, CL = "#111111", "#a3a3a3", "#173a6b", "#6b6b6b"
SHELL = "#9c3b36"  # wind guard shell drawn as a phantom over the assembly
DATE = "2026-10-23"
_SUMMARY = Path(__file__).resolve().parent.parent / "exports" / "summary.json"
MASS = json.loads(_SUMMARY.read_text()) if _SUMMARY.exists() else {}
plt.rcParams.update({"font.family": "DejaVu Sans", "hatch.linewidth": 0.35, "hatch.color": INK})


def fmt(v: float) -> str:
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return "0" if s == "-0" else s


# ------------------------------------------------------------------------------------------------
# projection
# ------------------------------------------------------------------------------------------------
def _edges_2d(compound) -> list[np.ndarray]:
    out: list[np.ndarray] = []
    if compound is None or compound.IsNull():
        return out
    BRepLib.BuildCurves3d_s(compound, 1e-6)
    exp = TopExp_Explorer(compound, TopAbs_EDGE)
    while exp.More():
        curve = BRepAdaptor_Curve(TopoDS.Edge_s(exp.Current()))
        try:
            disc = GCPnts_QuasiUniformDeflection(curve, 0.005)
            pts = [curve.Value(disc.Parameter(i)) for i in range(1, disc.NbPoints() + 1)]
        except Exception:
            pts = [curve.Value(curve.FirstParameter()), curve.Value(curve.LastParameter())]
        out.append(np.array([(q.X(), q.Y()) for q in pts]))
        exp.Next()
    return out


def hlr(shape: cq.Shape, n, xdir):
    algo = HLRBRep_Algo()
    algo.Add(shape.wrapped)
    algo.Projector(HLRAlgo_Projector(gp_Ax2(gp_Pnt(0, 0, 0), gp_Dir(*n), gp_Dir(*xdir))))
    algo.Update()
    algo.Hide()
    h = HLRBRep_HLRToShape(algo)
    visible = _edges_2d(h.VCompound()) + _edges_2d(h.OutLineVCompound())
    smooth = _edges_2d(h.Rg1LineVCompound())
    hidden = _edges_2d(h.HCompound()) + _edges_2d(h.OutLineHCompound())
    return visible, smooth, hidden


def _wire_points(wire: cq.Wire) -> np.ndarray:
    curve = BRepAdaptor_CompCurve(wire.wrapped)
    disc = GCPnts_QuasiUniformDeflection(curve, 0.005)
    pts = [curve.Value(disc.Parameter(i)) for i in range(1, disc.NbPoints() + 1)]
    return np.array([(q.X(), q.Y(), q.Z()) for q in pts])


def _signed_area(p: np.ndarray) -> float:
    return 0.5 * float(np.sum(p[:-1, 0] * p[1:, 1] - p[1:, 0] * p[:-1, 1]))


# ------------------------------------------------------------------------------------------------
# sheet + view
# ------------------------------------------------------------------------------------------------
class Sheet:
    def __init__(self, title: str, part_no: str, material: str, finish: str, scale: str, qty: str,
                 sheet_no: int, n_sheets: int):
        self.fig = plt.figure(figsize=(W / 25.4, H / 25.4))
        ax = self.fig.add_axes([0, 0, 1, 1])
        ax.set_xlim(0, W)
        ax.set_ylim(0, H)
        ax.set_aspect("equal")
        ax.axis("off")
        self.ax = ax
        ax.add_patch(Rectangle((10, 10), W - 20, H - 20, fill=False, lw=0.9, ec=INK))
        self._title_block(title, part_no, material, finish, scale, qty, sheet_no, n_sheets)

    def _title_block(self, title, part_no, material, finish, scale, qty, sheet_no, n_sheets):
        ax, x0, y0, w = self.ax, 230.0, 10.0, 180.0
        rows = [12.0, 7.0, 7.0, 7.0]
        y = y0 + sum(rows)
        ax.add_patch(Rectangle((x0, y0), w, sum(rows), fill=False, lw=0.8, ec=INK))
        ax.text(x0 + 3, y - 4.2, "RACING LEVER GUARD  /  UNIVERSAL BAR-END FIT", fontsize=6.5, color=INK)
        ax.text(x0 + 3, y - 10.0, title, fontsize=11.5, weight="bold", color=INK)
        ax.text(x0 + w - 3, y - 10.0, part_no, fontsize=11.5, weight="bold", color=INK, ha="right")
        y -= rows[0]

        def cells(yy, items):
            xs = x0
            for label, value, cw in items:
                ax.add_patch(Rectangle((xs, yy - 7.0), cw, 7.0, fill=False, lw=0.5, ec=INK))
                ax.text(xs + 1.5, yy - 2.4, label, fontsize=4.6, color=CL)
                ax.text(xs + 1.5, yy - 5.9, value, fontsize=6.6, color=INK)
                xs += cw

        cells(y, [("MATERIAL", material, 95.0), ("FINISH", finish, 85.0)])
        y -= 7.0
        cells(y, [("SCALE", scale, 25.0), ("UNITS", "mm", 20.0), ("QTY / SIDE", qty, 25.0),
                  ("GENERAL TOLERANCES", "ISO 2768-mK", 45.0), ("PROJECTION", "", 25.0),
                  ("SHEET", f"{sheet_no} / {n_sheets}", 40.0)])
        self._third_angle(x0 + 25 + 20 + 25 + 45 + 4, y - 6.2)
        y -= 7.0
        cells(y, [("SOURCE", "cad/lever_guard.py (CadQuery), drawings.py", 95.0), ("DATE", DATE, 45.0),
                  ("BREAK SHARP EDGES", "0.2 - 0.5", 40.0)])

    def _third_angle(self, x, y):
        ax = self.ax
        ax.add_patch(Polygon([(x, y - 0.2), (x, y + 4.2), (x + 6, y + 3.4), (x + 6, y + 0.6)],
                             closed=True, fill=False, lw=0.45, ec=INK))
        ax.add_patch(Circle((x + 11.5, y + 2.0), 2.2, fill=False, lw=0.45, ec=INK))
        ax.add_patch(Circle((x + 11.5, y + 2.0), 1.4, fill=False, lw=0.45, ec=INK))

    def text(self, x, y, s, size=7.5, **kw):
        kw.setdefault("color", INK)
        self.ax.text(x, y, s, fontsize=size, **kw)

    def notes(self, x, y, lines, size=6.8, step=4.2, title="NOTES"):
        self.text(x, y, title, size=size + 0.6, weight="bold")
        for i, line in enumerate(lines):
            self.text(x, y - (i + 1) * step, line, size=size)


class View:
    def __init__(self, sheet: Sheet, n, xdir, origin, scale: float, label: str | None = None):
        self.s, self.ax = sheet, sheet.ax
        self.n = np.array(n, float)
        self.xd = np.array(xdir, float)
        self.yd = np.cross(self.n, self.xd)
        self.o = np.array(origin, float)
        self.k = scale
        self.label = label

    # coordinates ---------------------------------------------------------------------------
    def uv(self, P3) -> np.ndarray:
        P = np.asarray(P3, float)
        return np.array([P @ self.xd, P @ self.yd])

    def sh(self, uv) -> np.ndarray:
        return self.o + self.k * np.asarray(uv, float)

    # geometry ------------------------------------------------------------------------------
    def draw(self, shape: cq.Shape, color=INK, lw=0.7, hidden=True, smooth=True, dashed=False):
        vis, smo, hid = hlr(shape, self.n, self.xd)
        if dashed:  # whole part hidden (e.g. inside the handlebar): draw it in the hidden-line style
            hid, vis, smo = hid + vis + smo, [], []
        for e in vis:
            q = self.sh(e)
            self.ax.plot(q[:, 0], q[:, 1], color=color, lw=lw, solid_capstyle="round", zorder=3)
        if smooth:
            for e in smo:
                q = self.sh(e)
                self.ax.plot(q[:, 0], q[:, 1], color=color, lw=lw * 0.35, zorder=3)
        if hidden:
            for e in hid:
                q = self.sh(e)
                self.ax.plot(q[:, 0], q[:, 1], color=color, lw=lw * 0.45, ls=(0, (2.2, 1.4)), zorder=2)

    def hatch(self, shape: cq.Shape, hatch="////"):
        """Hatch the cut face of a half section: plane z = 0, half y >= 0."""
        face = cq.Face.makeFromWires(cq.Wire.makePolygon(
            [cq.Vector(-300, 0, 0), cq.Vector(300, 0, 0), cq.Vector(300, 300, 0), cq.Vector(-300, 300, 0)],
            close=True))
        sec = shape.intersect(face)
        for f in sec.Faces():
            verts, codes = [], []
            rings = [(f.outerWire(), True)] + [(w, False) for w in f.innerWires()]
            for wire, outer in rings:
                ring = np.array([self.sh(self.uv(p)) for p in _wire_points(wire)])
                if (_signed_area(ring) > 0) != outer:
                    ring = ring[::-1]
                verts += list(ring) + [ring[0]]
                codes += [MPath.MOVETO] + [MPath.LINETO] * (len(ring) - 1) + [MPath.CLOSEPOLY]
            self.ax.add_patch(PathPatch(MPath(verts, codes), fill=False, hatch=hatch, lw=0, zorder=1))

    def hatch_plane(self, shape: cq.Shape, point, normal, hatch="////"):
        """Hatch the faces of `shape` that lie on the plane (point, normal)."""
        n = cq.Vector(*normal).normalized()
        u = cq.Vector(0, 0, 1) if abs(n.z) < 0.9 else cq.Vector(1, 0, 0)
        u = (u - n * u.dot(n)).normalized()
        w = n.cross(u)
        o = cq.Vector(*point)
        corners = [o + (u * a + w * b) * 400 for a, b in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
        face = cq.Face.makeFromWires(cq.Wire.makePolygon(corners, close=True))
        for f in shape.intersect(face).Faces():
            verts, codes = [], []
            rings = [(f.outerWire(), True)] + [(wi, False) for wi in f.innerWires()]
            for wire, outer in rings:
                ring = np.array([self.sh(self.uv(q)) for q in _wire_points(wire)])
                if (_signed_area(ring) > 0) != outer:
                    ring = ring[::-1]
                verts += list(ring) + [ring[0]]
                codes += [MPath.MOVETO] + [MPath.LINETO] * (len(ring) - 1) + [MPath.CLOSEPOLY]
            self.ax.add_patch(PathPatch(MPath(verts, codes), fill=False, hatch=hatch, lw=0, zorder=1))

    def tag(self, uv, text, size=7.4, color=DIMC):
        q = self.sh(uv)
        self.ax.text(q[0], q[1], text, fontsize=size, color=color, ha="center", va="center", zorder=5,
                     bbox=dict(boxstyle="square,pad=0.15", fc="white", ec="none"))

    def centerline(self, a, b):
        p, q = self.sh(a), self.sh(b)
        self.ax.plot([p[0], q[0]], [p[1], q[1]], color=CL, lw=0.3, ls=(0, (9, 2, 1.5, 2)), zorder=1)

    def center_mark(self, c, r=4.0):
        self.centerline((c[0] - r / self.k, c[1]), (c[0] + r / self.k, c[1]))
        self.centerline((c[0], c[1] - r / self.k), (c[0], c[1] + r / self.k))

    def caption(self, uv, text, size=8.0):
        p = self.sh(uv)
        self.s.text(p[0], p[1], text, size=size, weight="bold", ha="center", va="top")

    # dimensions ----------------------------------------------------------------------------
    def _arrow(self, p, q, style="<|-|>"):
        self.ax.annotate("", xy=q, xytext=p, zorder=4, arrowprops=dict(
            arrowstyle=style, color=DIMC, lw=0.4, mutation_scale=6.5, shrinkA=0, shrinkB=0))

    def _ext(self, p, q):
        d = q - p
        L = np.linalg.norm(d)
        if L < 1.5:
            return
        u = d / L
        a, b = p + u * 1.0, q + u * 2.0
        self.ax.plot([a[0], b[0]], [a[1], b[1]], color=DIMC, lw=0.3, zorder=4)

    def _label(self, p, text, rot=0.0, offset=(0, 0), ha="center", va="bottom"):
        self.ax.text(p[0] + offset[0], p[1] + offset[1], text, fontsize=7.4, color=DIMC, rotation=rot,
                     ha=ha, va=va, rotation_mode="anchor", zorder=5,
                     bbox=dict(boxstyle="square,pad=0.08", fc="white", ec="none"))

    def hdim(self, a, b, at, text=None, tpos=None):
        """Horizontal dimension between view points a, b; dimension line at view v = at."""
        A, B = self.sh(a), self.sh(b)
        y = self.sh((0, at))[1]
        pa, pb = np.array([A[0], y]), np.array([B[0], y])
        self._ext(A, pa)
        self._ext(B, pb)
        self._arrow(pa, pb)
        val = text if text is not None else fmt(abs(b[0] - a[0]))
        mid = (pa + pb) / 2 if tpos is None else np.array([self.sh((tpos, 0))[0], y])
        self._label(mid, val, offset=(0, 0.9))

    def vdim(self, a, b, at, text=None):
        """Vertical dimension between view points a, b; dimension line at view u = at."""
        A, B = self.sh(a), self.sh(b)
        x = self.sh((at, 0))[0]
        pa, pb = np.array([x, A[1]]), np.array([x, B[1]])
        self._ext(A, pa)
        self._ext(B, pb)
        self._arrow(pa, pb)
        val = text if text is not None else fmt(abs(b[1] - a[1]))
        self._label((pa + pb) / 2, val, rot=90, offset=(-0.9, 0))

    def adim(self, a, b, off, text=None):
        """Aligned dimension, offset (sheet mm) to the left of a -> b."""
        A, B = self.sh(a), self.sh(b)
        d = (B - A) / np.linalg.norm(B - A)
        nrm = np.array([-d[1], d[0]])
        pa, pb = A + nrm * off, B + nrm * off
        self._ext(A, pa)
        self._ext(B, pb)
        self._arrow(pa, pb)
        val = text if text is not None else fmt(np.linalg.norm(np.asarray(b) - np.asarray(a)))
        rot = math.degrees(math.atan2(d[1], d[0]))
        if rot > 90 or rot < -90:
            rot += 180
        self._label((pa + pb) / 2, val, rot=rot, offset=tuple(nrm * 0.9 * np.sign(off)))

    def leader(self, at, text_at, text, ha=None):
        """Leader with an arrowhead on view point `at`; text_at is in view coords too."""
        P, T = self.sh(at), self.sh(text_at)
        self._arrow(T, P, style="-|>")
        ha = ha or ("left" if T[0] >= P[0] else "right")
        self._label(T, text, ha=ha, va="center", offset=(1.0 if ha == "left" else -1.0, 0))

    def radius(self, c, r, ang, text, outside=6.0):
        a = math.radians(ang)
        on = (c[0] + r * math.cos(a), c[1] + r * math.sin(a))
        txt = (c[0] + (r + outside) * math.cos(a), c[1] + (r + outside) * math.sin(a))
        self.leader(on, txt, text)

    def diameter(self, c, r, ang, text, outside=8.0):
        a = math.radians(ang)
        p1 = self.sh((c[0] - r * math.cos(a), c[1] - r * math.sin(a)))
        p2 = self.sh((c[0] + r * math.cos(a), c[1] + r * math.sin(a)))
        self._arrow(p1, p2)
        t = self.sh((c[0] + (r + outside) * math.cos(a), c[1] + (r + outside) * math.sin(a)))
        self.ax.plot([p2[0], t[0]], [p2[1], t[1]], color=DIMC, lw=0.4, zorder=4)
        self._label(t, text, ha="left" if math.cos(a) >= 0 else "right", va="center",
                    offset=(1.0 if math.cos(a) >= 0 else -1.0, 0))


# ------------------------------------------------------------------------------------------------
# sheets
# ------------------------------------------------------------------------------------------------
def quadrant_cut(wp: cq.Workplane) -> cq.Shape:
    """Remove the y > 0, z > 0 quadrant (half-section of a part turned about X)."""
    box = cq.Solid.makeBox(400, 200, 200, cq.Vector(-200, 0, 0))
    return wp.val().cut(box)


def sheet_ga(p: lg.Params, n_sheets: int) -> Sheet:
    s = Sheet("GENERAL ARRANGEMENT", "LG-00", "see part sheets", "see part sheets", "1 : 1", "1 set",
              1, n_sheets)
    outside = cq.Solid.makeBox(300, 300, 300, cq.Vector(0, -150, -150))
    parts = {n: wp.val() for n, wp, _ in lg.guard_parts(p)}
    shell = parts.pop("diffuser_shell")
    guard = cq.Compound.makeCompound(
        [sh.intersect(outside) if n in ("adapter", "m6_bolt") else sh
         for n, sh in parts.items() if not n.startswith("expander")])
    inside = cq.Compound.makeCompound(
        [parts["adapter"].cut(outside), parts["m6_bolt"].cut(outside), parts["expander_sleeve"], parts["expander_cone"]])
    refs = {n: wp.val() for n, wp, _ in lg.reference_parts(p)}
    ref = cq.Compound.makeCompound([refs["ref_grip"], refs["ref_lever"],
                                    lg.ref_handlebar(p).val().intersect(cq.Solid.makeBox(110, 60, 60, cq.Vector(-235, -30, -30)))])

    # plan view: drawing plane = lever plane
    v = View(s, (0, 0, 1), (1, 0, 0), (270, 125), 1.0)
    v.draw(ref, color=REF, lw=0.45, hidden=False, smooth=False)
    v.draw(guard, lw=0.7, hidden=False)
    v.draw(shell, color=SHELL, lw=0.4, hidden=False)
    v.draw(inside, lw=0.7, dashed=True)
    v.centerline((-240, 0), (60, 0))
    v.caption((-60, -27), "PLAN  (looking square onto the lever plane)")
    tip = p.run_point(p.front_len)
    tip_min_x = tip[0] - p.blade_t / 2 * math.sin(math.radians(p.front_toe_deg))
    head_x = p.blade_seat_x + p.blade_t + 1.0 + 2.75
    top_y = p.run_point(p.front_len, -p.blade_t / 2)[1]
    shell_pts = np.array([(q.x, q.y) for q in shell.tessellate(0.05, 0.1)[0]])
    shell_end = shell_pts[np.argmin(shell_pts[:, 0])]
    shell_top = shell_pts[:, 1].max()
    lvl1, lvl2 = shell_top + 9, shell_top + 18
    v.hdim(tuple(shell_end), (head_x, p.screw_v[1] + 4.75), lvl2, fmt(head_x - shell_end[0]))
    v.hdim((tip_min_x, top_y), (0, p.body_d / 2), lvl1, fmt(-tip_min_x))
    v.hdim((0, p.body_d / 2), (head_x, p.screw_v[1] + 4.75), lvl1, fmt(head_x))
    v.tag((-150, shell_top - 12), "LG-06 WIND GUARD SHELL (phantom, RH shown)", color=SHELL)
    clamp_mid = p.run_point(p.clamp_pos + p.clamp_len / 2, -p.blade_t / 2)
    v.leader((clamp_mid[0], clamp_mid[1] + p.clamp_wall), (-50, shell_top - 26),
             f"slotted mount: slides {fmt(p.clamp_range[1] - p.clamp_range[0])} along the run, 2x M4 grub", ha="right")
    rs = p.run_point(0, p.blade_t / 2)
    v.vdim((rs[0], rs[1]), (40, 0), 48, f"{fmt(rs[1])} to blade face")
    # gap to the reference lever at its closest point (toward the blade tip)
    gx = -86.0
    lever_y = 50 + (gx + 60) / (-60) * 3
    s_run = (rs[0] - gx) / math.cos(math.radians(p.front_toe_deg))
    blade_y = rs[1] + s_run * math.sin(math.radians(p.front_toe_deg))
    v.vdim((gx, lever_y), (gx, blade_y), gx + 6, f"{fmt(blade_y - lever_y)} gap")
    bc = p.bend_center
    v.center_mark(bc, 2.5)
    v.radius(bc, p.bend_r, 30, f"R{fmt(p.bend_r)} CL, gusset inside", outside=26)
    v.leader((p.blade_seat_x + p.blade_t, 15), (34, -9), f"slot: blade ±{fmt(p.adjust)}")
    v.leader((-112, -15.6), (-135, -25), "reference grip, bar and lever (phantom)", ha="right")

    # bar-end view (from outboard), aligned with the plan
    e = View(s, (1, 0, 0), (0, 0, -1), (390, 125), 1.0)
    e.draw(guard, lw=0.7, hidden=False)
    e.centerline((-22, 0), (22, 0))
    e.centerline((0, -22), (0, 60))
    e.caption((0, -24), "BAR-END VIEW")
    e.hdim((-p.blade_h / 2, 62), (p.blade_h / 2, 62), lvl1)
    e.diameter((0, 0), p.body_d / 2, -135, f"Ø{fmt(p.body_d)}", outside=8)

    # front view (looking back at the lever), aligned with the plan
    f = View(s, (0, 1, 0), (1, 0, 0), (270, 72), 1.0)
    f.draw(guard, lw=0.7, hidden=False)
    f.centerline((-240, 0), (60, 0))
    f.caption((-90, -16), "FRONT VIEW (wind guard shell not shown)")
    f.vdim((tip_min_x + 4, p.blade_h / 2), (tip_min_x + 4, -p.blade_h / 2), tip_min_x - 8)

    s.notes(18, 44, [
        "1. Drawing plane = lever plane. Turn the arm on its 36-tooth serration (10° steps) to put the blade on the lever line.",
        "2. Clearances shown for the reference sport-bike lever; keep ≥ 10 mm all round, re-check at full lever travel.",
        f"3. Mass per side ≈ {fmt(round(MASS.get('mass_per_side_grams_carbon_blade', 0)))} g, "
        f"{fmt(round(MASS.get('mass_per_side_grams_with_diffuser', 0)))} g with the wind guard.",
        "4. Left side: same parts, arm turned over (they are symmetric about the lever plane), except the wind guard",
        "    shell: LG-06 is made as a mirror-image pair.",
        "5. Wind guard shell drawn as a phantom in the plan; its profile and fixing are on sheet 6.",
    ], size=6.4, step=4.0)
    return s


def sheet_adapter(p: lg.Params, n_sheets: int) -> Sheet:
    s = Sheet("BAR-END ADAPTER", "LG-01", "EN AW-6061-T6", "Hard anodise, colour to order", "3 : 1", "1",
              2, n_sheets)
    k = 3.0
    part = lg.adapter(p)
    sec = quadrant_cut(part)
    v = View(s, (0, 0, 1), (1, 0, 0), (130, 160), k)
    v.draw(sec, lw=0.7, hidden=False)
    v.hatch(sec)
    v.centerline((-10, 0), (16, 0))
    v.centerline((p.pitch_x, -20), (p.pitch_x, 20))
    v.caption((3, -34), "HALF SECTION A-A")
    rb, top = p.body_d / 2, p.pitch_x + p.serr_r_out * p.tan_g
    v.vdim((10, rb), (10, -rb), top + 6, f"Ø{fmt(p.body_d)}")
    v.vdim((-5.5, p.spigot_d / 2), (-5.5, -p.spigot_d / 2), -11, f"Ø{fmt(p.spigot_d)}")
    v.leader((-4, p.bolt_clear_d / 2), (-16, 9), f"Ø{fmt(p.bolt_clear_d)} THRU (M6 clearance)")
    v.hdim((-p.spigot_len, -p.spigot_d / 2), (0, -rb + 0.8), -22)
    v.hdim((0, -rb + 0.8), (p.pitch_x, -rb), -26, f"{fmt(p.pitch_x)} (pitch plane)")
    v.hdim((-p.spigot_len, -p.spigot_d / 2), (top, -rb + 0.5), -30, fmt(top + p.spigot_len))
    for gx in p.groove_x:
        v.hdim((0, rb - 0.8), (gx, rb), 20 + (gx - 4) * 0.8)
    v.leader((p.groove_x[1], rb - p.groove_depth), (16, 25),
             f"2x V-groove 90°, {fmt(p.groove_w)} wide x {fmt(p.groove_depth)} deep")
    v.leader((0.3, rb - 0.3), (-12, 23), "0.8 x 45°")
    v.leader((-p.spigot_len + 0.2, p.spigot_d / 2 - 0.2), (-14, 12), "0.5 x 45° (both ends)")

    e = View(s, (1, 0, 0), (0, 0, -1), (300, 160), k)
    e.draw(part.val(), lw=0.6, hidden=False, smooth=False)
    e.centerline((-19, 0), (19, 0))
    e.centerline((0, -19), (0, 19))
    e.caption((0, -24), "VIEW ON SERRATION (from outboard)")
    e.diameter((0, 0), p.serr_r_in, 135, f"Ø{fmt(2 * p.serr_r_in)} relief, 0.6 deep", outside=14)
    e.diameter((0, 0), rb, -35, f"Ø{fmt(p.body_d)}", outside=6)

    s.notes(232, 80, [
        f"1. Hirth face serration: {p.teeth} teeth, 90° included, crests and roots radial through the axis,",
        f"    pitch plane at {fmt(p.pitch_x)} from the bar-end face, toothed from Ø{fmt(2 * p.serr_r_in)} to Ø{fmt(p.body_d)}:",
        f"    tooth height {fmt(2 * p.serr_r_out * p.tan_g)} at Ø{fmt(p.body_d)}. Mates with LG-02 (offset half a tooth).",
        "2. Variant LG-01b: same part without the spigot, for bars with a threaded OEM bar-end insert.",
        f"3. Spigot Ø{fmt(p.spigot_d)} centres in any bar with ID ≥ 12.5; the expander (LG-04/05) sits behind it.",
        "4. Hard anodise after machining; mask nothing. Serration may be cut with a 90° V-cutter.",
    ])
    return s


def sheet_arm(p: lg.Params, n_sheets: int) -> Sheet:
    s = Sheet("GUARD ARM", "LG-02", "EN AW-6061-T6", "Hard anodise, colour to order", "2 : 1", "1",
              3, n_sheets)
    k = 2.0
    part = lg.arm(p).val()
    rb, w = p.body_d / 2, p.neck_h / 2
    o = View(s, (1, 0, 0), (0, 1, 0), (110, 200), k)
    o.draw(part, lw=0.7, hidden=False)
    o.centerline((-22, 0), (50, 0))
    o.centerline((0, -21), (0, 21))
    for yv in p.screw_v:
        o.center_mark((yv, 0), 3.5)
    o.caption((14, -30), "OUTBOARD FACE")
    o.diameter((0, 0), rb, 135, f"Ø{fmt(p.body_d)}", outside=8)
    o.vdim((p.neck_end - w, w), (p.neck_end - w, -w), p.neck_end + 6, fmt(p.neck_h))
    o.hdim((0, 0), (p.neck_end, 0), -22)
    o.hdim((0, 0), (p.screw_v[0], 0), -27)
    o.hdim((p.screw_v[0], 0), (p.screw_v[1], 0), -27)
    o.leader((p.screw_v[1] + 1.5, -1.5), (56, -8), f"2x M5 x 0.8 THRU (drill Ø{fmt(p.tap_d)})")
    o.leader((-p.cbore_d / 2 * 0.7, p.cbore_d / 2 * 0.7), (-20, 24),
             f"Ø{fmt(p.bolt_clear_d)} THRU, C'BORE Ø{fmt(p.cbore_d)} x {fmt(p.cbore_depth)} DEEP")
    o.radius((p.neck_end - w, 0), w, 60, f"R{fmt(w)} full round", outside=8)
    o.leader((13.3, w + 0.9), (20, 22), f"R{fmt(p.neck_fillet_r)}")

    t = View(s, (0, 0, 1), (0, 1, 0), (110, 125), k)
    t.draw(part, lw=0.7, hidden=True)
    t.centerline((-22, -p.pitch_x), (50, -p.pitch_x))
    t.caption((14, -34), "PLAN (lever plane), serration toward the bar")
    t.vdim((-rb, -p.hub_outer_x), (-rb, -p.pitch_x), -rb - 6, f"{fmt(p.hub_outer_x - p.pitch_x)} (pitch pl.)")
    t.vdim((p.neck_end - 2, -p.hub_outer_x), (p.neck_end - 2, -p.neck_inner_x), p.neck_end + 6)

    s.notes(240, 270, [
        f"1. Hirth serration as LG-01: {p.teeth} teeth, 90°, pitch plane",
        "    on the hub's inner face. Sits half a tooth out of phase",
        "    with LG-01 so crests meet roots: 10° indexing.",
        "2. Neck edges R1. Outboard face is the blade seat:",
        "    flat within 0.05.",
        "3. M6 screw: ISO 4762 M6 x 45 (expander) or to suit the",
        "    OEM thread; 8 N·m, medium threadlocker.",
        "4. M5 screws: ISO 7380 M5 x 14 (x 16 with LG-03b)",
        "    + ISO 7089 washers, 4 N·m.",
    ], size=6.6)
    return s


def sheet_blade(p: lg.Params, pp: lg.Params, n_sheets: int) -> Sheet:
    s = Sheet("GUARD BLADE WITH BEND GUSSET", "LG-03", "3K 2x2 twill carbon / epoxy, forged-carbon gusset",
              "Gloss clear coat, edges R0.6", "3 : 2", "1", 4, n_sheets)
    k = 1.5
    part = lg.blade(p).val()
    t, h = p.blade_t, p.blade_h
    v = View(s, (0, 0, 1), (1, 0, 0), (232, 120), k)
    v.draw(part, lw=0.7, hidden=True)
    v.caption((-30, -2), "PLAN (lever plane)")
    v.vdim((p.blade_seat_x + t, p.blade_rear), (p.blade_seat_x + t, p.bend_start), p.blade_seat_x + t + 9,
           fmt(p.bend_start - p.blade_rear))
    v.hdim((p.blade_seat_x, p.blade_rear + 2), (p.blade_seat_x + t, p.blade_rear + 2), p.blade_rear - 6,
           f"{fmt(t)}  (LG-03b: {fmt(pp.blade_t)})")
    bc = p.bend_center
    v.center_mark(bc, 2.5)
    ox, oy, rho = lg.haunch_circle(p)
    b_pt = lg.haunch_ends(p)[1]
    s_pt, t_pt, f_pt = lg.haunch_blend(p)
    v.leader(lg.arc_mid((ox, oy), rho, t_pt, b_pt), (-8, 38),
             f"gusset edge R{fmt(round(rho, 1))}, tangent to the run")
    v.adim(p.run_point(0, t / 2), p.run_point(p.haunch_len, t / 2), 7.0, fmt(p.haunch_len))
    v.leader(lg.arc_mid(f_pt, p.haunch_blend_r, s_pt, t_pt), (44, s_pt[1] - 4),
             f"R{fmt(p.haunch_blend_r)} blend into the seat face")
    v.leader((bc[0] + (p.bend_r + t / 2) * math.cos(math.radians(50)), bc[1] + (p.bend_r + t / 2) * math.sin(math.radians(50))),
             (40, 88), f"bend {fmt(p.bend_angle_deg)}° on R{fmt(p.bend_r)} centre line")
    a = p.run_point(0, -t / 2)
    b = p.run_point(p.front_len, -t / 2)
    v.adim(b, a, 10.0, f"{fmt(p.front_len)} straight run (toe-out {fmt(p.front_toe_deg)}°)")

    o = View(s, (1, 0, 0), (0, 0, -1), (352, 120), k)
    o.draw(part, lw=0.7, hidden=False)
    o.centerline((0, p.blade_rear - 4), (0, p.bend_start + 4))
    o.caption((0, 2), "REAR PLATE (outboard)")
    o.hdim((-h / 2, p.blade_rear + 8), (h / 2, p.blade_rear + 8), p.blade_rear - 5)
    s0 = p.slot_center - p.slot_len / 2
    o.vdim((p.slot_w / 2, s0), (p.slot_w / 2, s0 + p.slot_len), h / 2 + 5, f"slot {fmt(p.slot_len)}")
    o.vdim((-h / 2, p.blade_rear), (-p.slot_w / 2, s0), -h / 2 - 5)
    o.leader((p.slot_w / 2, p.slot_center), (h / 2 + 2, p.bend_start + 12), f"{fmt(p.slot_w)} wide")
    o.leader((-h / 2 + 1.8, p.blade_rear + 1.8), (-h / 2 - 3, p.blade_rear - 9), f"2x R{fmt(p.blade_rear_r)}")

    f = View(s, (0, 1, 0), (1, 0, 0), (232, 74), k)
    f.draw(part, lw=0.7, hidden=False)
    f.caption((-30, -14), "FRONT VIEW (outer face)")
    tip_x = p.tip_x
    f.vdim((tip_x + 20, h / 2), (tip_x + 20, -h / 2), tip_x - 6)
    f.leader((tip_x + 2.4, h / 2 - 2.4), (tip_x - 8, h / 2 + 8), f"2x R{fmt(p.tip_r)}")

    s.notes(18, 270, [
        f"1. Centre-line length {fmt(round(p.blade_path_len, 1))} mm: {fmt(p.bend_start - p.blade_rear)} straight + "
        f"{fmt(p.bend_angle_deg)}° bend on R{fmt(p.bend_r)} + {fmt(p.front_len)} straight.",
        f"2. Gusset inside the bend: section {fmt(round(lg.bend_section(p, False), 1))} -> {fmt(round(lg.bend_section(p), 1))} mm across the bend, "
        f"about {fmt(round((lg.bend_section(p) / lg.bend_section(p, False)) ** 2, 1))}x the bending strength where a fall loads the blade.",
        "    Its edge is tangent all along (blend into the seat face, arc, run-out on the run): no corner to start a crack.",
        f"3. LG-03 carbon: skin {fmt(t)} ± 0.2 moulded over a male tool, gusset filled with forged (chopped) carbon in the same cure;",
        "    CNC-trim the outline and slot. Lay plies continuous round the bend; no cut fibres at the gusset edge.",
        "4. LG-03 aluminium option: machine from 6061-T6 25 mm plate (the gusset rules out bending strip), carbon hydro-dip.",
        f"5. LG-03b 3D print: same outline, {fmt(pp.blade_t)} thick,",
        "    PA12-CF / PETG-CF, lying flat (lever plane on the bed),",
        "    6 walls, 50 % gyroid; hydro-dip or wrap for the carbon finish.",
        f"6. Slot lets the blade slide ±{fmt(p.adjust)} mm toward / away from the lever.",
    ], size=6.6)
    return s


def sheet_expander(p: lg.Params, n_sheets: int) -> Sheet:
    s = Sheet("EXPANDER SET", "LG-04 / LG-05", "LG-04 TPU 95A or NBR 70A; LG-05 6061-T6",
              "LG-05 clear anodise or zinc", "4 : 1", "1 sleeve + 1 cone", 5, n_sheets)
    k = 4.0
    sleeve = lg.expander_sleeve(p, "M")
    cone = lg.expander_cone(p, "M")
    x0 = -p.spigot_len - p.sleeve_len
    v = View(s, (0, 0, 1), (1, 0, 0), (110 - 4 * (x0 + p.sleeve_len / 2) - 40, 190), k)
    sec = quadrant_cut(sleeve.rotate((0, 0, 0), (1, 0, 0), 45))  # cut plane between the slits
    v.draw(sec, lw=0.7, hidden=False)
    v.hatch(sec, hatch="\\\\\\\\")
    v.centerline((x0 - 3, 0), (-p.spigot_len + 3, 0))
    v.caption((x0 + p.sleeve_len / 2, -12), "LG-04 SLEEVE (size M shown)")
    od = lg.SLEEVES["M"][0]
    v.vdim((x0 + 3, od / 2), (x0 + 3, -od / 2), x0 - 3, f"Ø{fmt(od)}")
    v.hdim((x0, -od / 2), (-p.spigot_len, -od / 2), -od / 2 - 4)
    v.hdim((x0, od / 2 - 1), (x0 + p.sleeve_recess_depth, (lg.cone_small_d(p, "M") + 0.4) / 2), od / 2 + 3,
           fmt(p.sleeve_recess_depth))
    v.leader((x0 + 3, od / 2 - 0.3), (x0 + 12, od / 2 + 7.5), f"4x slit {fmt(p.sleeve_slit_w)} wide x {fmt(p.sleeve_slit_len)}")

    c = View(s, (0, 0, 1), (1, 0, 0), (330 + 4 * 24, 190), k)
    csec = quadrant_cut(cone)
    c.draw(csec, lw=0.7, hidden=False)
    c.hatch(csec)
    xs = x0 + p.sleeve_recess_depth
    xl = x0 - p.cone_land
    c.centerline((xl - 3, 0), (xs + 3, 0))
    c.caption(((xl + xs) / 2, -10), "LG-05 CONE NUT (size M shown)")
    c.hdim((xl, -6), (xs, -lg.cone_small_d(p, "M") / 2), -9)
    c.hdim((xl, -6), (x0, -6.5), -12, fmt(p.cone_land))
    c.leader((xs - 0.5, p.cone_tap_d / 2), (xs + 4, 7), "M6 x 1 THRU")

    rows = [("Size", "Bar ID", "Sleeve OD", "Recess Ø face / bottom", "Cone Ø big / small", "Taper (half)")]
    for size, (sod, (lo, hi)) in lg.SLEEVES.items():
        big = sod - 1.2
        small = lg.cone_small_d(p, size)
        half = math.degrees(math.atan2((big - small) / 2, p.sleeve_recess_depth))
        rows.append((size, f"{fmt(lo)} - {fmt(hi)}", fmt(sod), f"{fmt(big + 0.2)} / {fmt(small + 0.4)}",
                     f"{fmt(big)} / {fmt(round(small, 2))}", f"{half:.0f}°"))
    x, y = 30.0, 118.0
    widths = [16, 26, 24, 46, 40, 26]
    for r, row in enumerate(rows):
        xx = x
        for cw, cell in zip(widths, row):
            s.ax.add_patch(Rectangle((xx, y - 7 * (r + 1)), cw, 7, fill=False, lw=0.5, ec=INK))
            s.text(xx + 1.5, y - 7 * (r + 1) + 2.3, cell, size=6.8, weight="bold" if r == 0 else "normal")
            xx += cw
    s.text(x, y + 3, "SIZES (all lengths as drawn: sleeve 20, recess 7, cone land 3)", size=7.4, weight="bold")

    s.notes(240, 118, [
        "1. Bolt chain: M6 x 45 (ISO 4762) through LG-02 and LG-01",
        "    into the cone nut: 8.5 mm thread engagement at fit-up.",
        "2. Tightening pulls the cone into the slit sleeve, which",
        "    grips the bar bore. 8 N·m. Hold the arm square on",
        "    its serration while tightening.",
        "3. Pick the size from the bar's measured inside diameter.",
        "4. Sleeve can be printed in TPU 95A (100 % infill) or cut",
        "    from NBR tube; cone may be steel for higher load.",
    ], size=6.6)
    return s


def sheet_wind_guard(p: lg.Params, n_sheets: int) -> Sheet:
    s = Sheet("WIND GUARD SHELL WITH SLOTTED MOUNT", "LG-06",
              "HDPE or PP, moulded; ASA / PA12 printed", "colour to order, edges R1", "1:1 / 2:1",
              "1 pair (RH + LH)", 6, n_sheets)
    c, L, t, w = p.clamp_clear, p.clamp_len, p.shell_t, p.clamp_wall
    shell = lg.wind_guard_local(p).val()
    blade_bar = cq.Workplane("XY").box(L + 30, p.blade_t, p.blade_h).translate((L / 2, p.blade_t / 2, 0)).val()
    holes = lg._clamp_screw_xy(p)
    h, sy0, sy1 = lg._slot(p)
    yb, zb = sy1 + p.clamp_back, lg._boss_face(p)
    a = math.radians(p.lever_deg)

    # LG-06 seen from the front of the bike, 1:1
    v = View(s, (0, -math.cos(a), math.sin(a)), (1, 0, 0), (44, 172), 1.0)
    v.draw(shell, lw=0.7, hidden=False)
    v.draw(blade_bar, color=REF, lw=0.4, hidden=False, smooth=False)
    uv = np.array([v.uv((q.x, q.y, q.z)) for q in shell.tessellate(0.05, 0.1)[0]])
    lo, hi = uv.min(axis=0), uv.max(axis=0)
    crest = uv[np.argmax(uv[:, 1])]
    v.caption((lo[0] + (hi[0] - lo[0]) / 2, lo[1] - 16), "LG-06 SHELL (RH), SEEN FROM THE FRONT OF THE BIKE  -  blade phantom")
    v.hdim((lo[0], lo[1]), (hi[0], lo[1]), lo[1] - 7)
    v.vdim((lo[0], lo[1]), (lo[0], hi[1]), lo[0] - 8)
    v.hdim((lo[0], hi[1]), tuple(crest), hi[1] + 6)
    xc = 100.0  # crease height there, as in lg.wind_guard_local
    uc = p.shell_crease[0] + (p.shell_crease[1] - p.shell_crease[0]) * (xc + p.shell_out) / (226.0 * p.shell_len / 230.0)
    v.leader((xc, uc), (xc + 40, uc + 34), "crease R4, outboard top to tip")
    v.leader((hi[0] - 2, lo[1] + 3), (hi[0] + 6, lo[1] + 16), "tip ≈ R5")

    # flange and mount seen from below, 1:1 (view up = forward, away from the blade)
    x0, y0, yf = -p.shell_out, -p.shell_gap, -p.shell_flange
    base = shell.intersect(cq.Solid.makeBox(L + 20 - x0, yb - yf + 2, t / 2 - zb + 1, cq.Vector(x0, yf - 1, zb - 1)))
    b = View(s, (0, 0, -1), (1, 0, 0), (44, 106), 1.0)
    b.draw(base, lw=0.7, hidden=False)
    b.caption((25, -yb - 30), "FLANGE AND SLOTTED MOUNT FROM BELOW")
    (hx0, hy), (hx1, _) = holes
    b.hdim((x0, -y0), (0, -sy0 + w), -yf + 5)
    b.hdim((0, -yb), (L, -yb), -yb - 6)
    b.hdim((0, -hy), (hx0, -hy), -yb - 13)
    b.hdim((hx0, -hy), (hx1, -hy), -yb - 13)
    b.vdim((L + 20, -y0), (L + 20, -yf), L + 26, f"flange {fmt(y0 - yf)}")
    b.leader((hx1 + p.clamp_boss_d / 2 * 0.7, -hy + p.clamp_boss_d / 2 * 0.7), (hx1 + 6, -yb - 40),
             f"2x boss Ø{fmt(p.clamp_boss_d)}, Ø{fmt(p.insert_d)} x {fmt(p.insert_len)} for M4 heat-set insert, Ø4.2 thru")

    # mount seen along the run, 2:1
    m = View(s, (1, 0, 0), (0, 1, 0), (192, 62), 2.0)
    m.draw(lg.mount_local(p).val(), lw=0.7, hidden=True)
    m.draw(blade_bar, color=REF, lw=0.4, hidden=False, smooth=False)
    m.caption(((sy0 + yb) / 2, h + w + 19), "SLOTTED MOUNT, END VIEW (2:1)")
    m.hdim((sy0, h), (sy1, h), h + w + 5, f"slot {fmt(round(sy1 - sy0, 2))}")
    m.hdim((sy0 - w, h + w), (yb, h + w), h + w + 11)
    m.vdim((yb, -h), (yb, h), yb + 6, f"slot {fmt(round(2 * h, 2))}")
    m.vdim((sy0 - w, zb), (sy0 - w, h + w), sy0 - w - 6)
    m.tag((p.blade_t / 2, 0), "blade", size=6.0, color=CL)

    # section through a grub screw, looking along the run, 1:1
    xs = holes[0][0]
    keep = cq.Solid.makeBox(200, 200, 200, cq.Vector(xs - 200, -100, -100))
    x_sec = View(s, (1, 0, 0), (0, 1, 0), (318, 150), 1.0)
    cut = shell.intersect(keep)
    x_sec.draw(cut, lw=0.6, hidden=False, smooth=False)
    x_sec.hatch_plane(cut, (xs, 0, 0), (1, 0, 0), "\\\\\\")
    x_sec.draw(blade_bar.intersect(keep), color=REF, lw=0.5, hidden=False, smooth=False)
    x_sec.draw(lg.m4_grub_insert_local(p, *holes[0]).val().intersect(keep), lw=0.4, hidden=False, smooth=False)
    x_sec.caption((10, -30), "SECTION THROUGH A GRUB SCREW (1:1)")
    sec = np.array([x_sec.uv((q.x, q.y, q.z)) for q in cut.tessellate(0.05, 0.1)[0]])
    x_sec.vdim((sec[:, 0].min(), -t / 2), (sec[:, 0].min(), sec[:, 1].max()), sec[:, 0].min() - 6)
    x_sec.leader((-p.shell_flange - 6, 3), (-44, 14), f"bend R{fmt(p.shell_bend_r)}")
    x_sec.leader((-(p.shell_gap + p.shell_flange) / 2 - 3, -t / 2), (-40, -12), f"flange {fmt(t)}")
    band = shell.intersect(cq.Solid.makeBox(1, 200, 4, cq.Vector(xs - 1, -100, 38))).BoundingBox()
    x_sec.leader((band.ymax, 40), (band.ymax + 22, 32), f"wall {fmt(t)}")
    x_sec.leader((p.blade_t / 2 + 2, zb + 2), (30, zb - 6), "M4 x 8 grub screw, ISO 4029")

    s.notes(286, 112, [
        "1. LG-06 surface as the STEP files 06 (RH) / 06b (LH, mirror image).",
        "    One piece: shell, flange and slotted mount. Injection-moulded HDPE",
        "    or PP, or printed ASA / PA12 with tree supports. Edges R1.",
        "2. Press an M4 x 5.7 brass heat-set insert into each boss (soldering",
        "    iron at about 230 °C), flush with the boss face.",
        "3. Slide the mount onto the blade run from the blade tip, shell in",
        "    front of the lever. The slot closes round the blade on all sides.",
        "4. Lock with 2x M4 x 8 grub screws (ISO 4029, cup point, nylon-tipped",
        "    if available) from below onto the blade's lower edge, 1 N·m.",
        f"5. Loosen to slide: {fmt(p.clamp_range[0])}-{fmt(p.clamp_range[1])} mm from the bend. No holes in the blade.",
        "6. Keep the blade slot at -4 or more with the shell fitted (>= 10 mm",
        "    to the reference lever). Check steering lock, mirrors, reservoir.",
    ], size=6.4, step=4.0)
    return s


def main() -> None:
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "drawings.pdf")
    out.parent.mkdir(parents=True, exist_ok=True)
    p, pp = lg.Params(), lg.PRINT_PARAMS
    n = 6
    makers = [lambda: sheet_ga(p, n), lambda: sheet_adapter(p, n), lambda: sheet_arm(p, n),
              lambda: sheet_blade(p, pp, n), lambda: sheet_expander(p, n), lambda: sheet_wind_guard(p, n)]
    with PdfPages(out) as pdf:
        for i, make in enumerate(makers, 1):
            sheet = make()
            pdf.savefig(sheet.fig)
            sheet.fig.savefig(out.with_name(f"sheet_{i}.png"), dpi=110)
            plt.close(sheet.fig)
            print(f"  sheet {i} done")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
