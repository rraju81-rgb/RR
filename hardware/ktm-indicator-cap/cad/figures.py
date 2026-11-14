#!/usr/bin/env python3
"""
Explanatory figures (SVG, px units, theme-able through CSS variables):

    docs/fig_section.svg    section through a keeper tab: how the lamp head is held
    docs/fig_measure.svg    what to measure on the bike (M1..M10)
    docs/fig_blank.svg      flat blank with bend lines
    docs/fig_iso.svg        line isometric of the cap on the lamp

Every colour is a CSS variable with a light-theme fallback, so the same file
works on its own (README) and inside the design-review page (which sets the
variables for light and dark).
"""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import cadquery as cq
from OCP.BRepTools import BRepTools_WireExplorer

import hlr
from build import build, OUT
from drawing import Sheet, View, draw_blank_geometry
from params import Design

DOCS = OUT.parent / "docs"

FIG_CSS = """
  .fig text{font-family:Barlow,'DejaVu Sans',Arial,sans-serif}
  .fig .part{fill:none;stroke:var(--fig-ink,#14181f);stroke-width:1.5;stroke-linejoin:round;stroke-linecap:round}
  .fig .ref{fill:none;stroke:var(--fig-ref,#8a909b);stroke-width:1;stroke-linejoin:round;stroke-linecap:round}
  .fig .steel{fill:var(--fig-steel,#c5cad2);stroke:var(--fig-ink,#14181f);stroke-width:1.3;stroke-linejoin:round}
  .fig .foam{fill:var(--fig-foam,#5b6472);stroke:none}
  .fig .housing{fill:var(--fig-housing,#23262d);stroke:var(--fig-ink,#14181f);stroke-width:1}
  .fig .lens{fill:var(--fig-lens,#f6a300);fill-opacity:.5;stroke:var(--fig-lens-edge,#b87400);stroke-width:1}
  .fig .cut{fill:var(--fig-steel,#c5cad2);fill-opacity:.55;stroke:var(--fig-ink,#14181f);stroke-width:1.4;stroke-linejoin:round}
  .fig .hole{fill:var(--fig-bg,#ffffff);stroke:var(--fig-ink,#14181f);stroke-width:1.4}
  .fig .bendD{fill:none;stroke:var(--fig-down,#0a7d3c);stroke-width:1.3;stroke-dasharray:14 4 3 4}
  .fig .bendU{fill:none;stroke:var(--fig-up,#c22727);stroke-width:1.3;stroke-dasharray:14 4 3 4}
  .fig .dim{fill:none;stroke:var(--fig-dim,#1f4e9c);stroke-width:.9}
  .fig .arrow{fill:var(--fig-dim,#1f4e9c);stroke:none}
  .fig .dimtxt{font-size:13px;font-weight:600;fill:var(--fig-dim,#1f4e9c)}
  .fig .txt{font-size:13px;fill:var(--fig-ink,#14181f)}
  .fig .small{font-size:11.5px;fill:var(--fig-ink,#14181f)}
  .fig .inv{font-size:12px;fill:var(--fig-inv,#e9ecf1)}
  .fig .label{font-size:13px;font-weight:700;letter-spacing:.06em;fill:var(--fig-ink,#14181f)}
  .fig .ray{fill:none;stroke:var(--fig-lens-edge,#b87400);stroke-width:1.3;stroke-dasharray:3 4}
  .fig .rayarrow{fill:var(--fig-lens-edge,#b87400);stroke:none}
  .fig .datum{fill:none;stroke:var(--fig-ref,#8a909b);stroke-width:.9;stroke-dasharray:8 3 2 3}
  .fig .datumtxt{font-size:11.5px;fill:var(--fig-ref,#8a909b)}"""


class Fig(Sheet):
    U = 4.6  # px per "drawing mm" for arrow heads, extension overshoot and text offsets

    def svg(self, title: str) -> str:
        body = "\n".join(self.items)
        return (
            f'<svg class="fig" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.w} {self.h}" role="img" '
            f'aria-label="{title}"><title>{title}</title><style>{FIG_CSS}</style>'
            f'<rect width="{self.w}" height="{self.h}" fill="var(--fig-bg,#ffffff)"/>\n{body}\n</svg>'
        )

    def write(self, path: Path, title: str):
        path.write_text(self.svg(title) + "\n")


# ----------------------------------------------------------------------------- section helpers
def wire_points(wire, n_arc=14):
    """Ordered points round a closed wire (arcs sampled)."""
    exp = BRepTools_WireExplorer(wire.wrapped)
    chains = []
    while exp.More():
        e = cq.Edge(exp.Current())
        n = 2 if e.geomType() == "LINE" else n_arc
        pts = [e.positionAt(t) for t in np.linspace(0, 1, n)]
        chains.append([np.array([p.x, p.y, p.z]) for p in pts])
        exp.Next()
    out = []
    for i, ch in enumerate(chains):
        if out and np.linalg.norm(ch[0] - out[-1]) > 1e-6:
            ch = ch[::-1]
        elif not out and len(chains) > 1:
            nxt = chains[1]
            if min(np.linalg.norm(ch[-1] - nxt[0]), np.linalg.norm(ch[-1] - nxt[-1])) > 1e-6:
                ch = ch[::-1]
        out.extend(ch if not out else ch[1:])
    return out


def section_loops(shape, x):
    """Cross-section of `shape` in the plane x = const -> list of closed loops [(y, z), ...]."""
    big = cq.Face.makeFromWires(
        cq.Wire.makePolygon([cq.Vector(x, -300, -300), cq.Vector(x, 300, -300), cq.Vector(x, 300, 300), cq.Vector(x, -300, 300)], close=True)
    )
    sec = big.intersect(shape)
    loops = []
    for f in sec.Faces():
        loops.append([(p[1], p[2]) for p in wire_points(f.outerWire())])
    return loops


# ----------------------------------------------------------------------------- figure A: section
def fig_section(res) -> Fig:
    d, g, cap, lamp, hw, liners, parts = res["d"], res["g"], res["cap"], res["lamp"], res["hw"], res["liners"], dict(res["parts"])
    L, H = d.lamp.L, d.lamp.H
    capd = d.cap
    hole = res["hole"]
    xs = capd.tab_x[0]
    F = Fig(780, 364)
    k = 6.4
    v = View(F, 196, 262, k, -13.0, -6.0)

    # things beyond the section plane: ear, washer, screw, boss - thin lines
    beyond = {"EAR": parts["EAR"], "BEAR": parts["bend_EAR"], "BOSS": lamp["BOSS"], **hw}
    pr = hlr.project(beyond, *hlr.VIEWS["tip"], deflection=0.05)
    for name in beyond:
        v.polylines(pr[name]["visible"], "ref")

    def fill(shape, cls):
        for loop in section_loops(shape, xs):
            F.polyline([v.xy(y, z) for y, z in loop], cls, close=True)

    fill(lamp["HOUSING"], "housing")
    fill(lamp["LENS"], "lens")
    for name in ("LINER_TOP", "LINER_BOTTOM", "LINER_BACK"):
        fill(liners[name][0], "foam")
    fill(cap, "steel")

    # light: straight ahead plus the +/-15 degree vertical limits of the light window
    y_face = -(d.lamp.lens_run + d.lamp.lens_nose)
    z_lo, z_hi = d.lamp.lens_drop + 1.0, H - d.lamp.lens_drop - 1.0
    for z in (z_lo + 2, H / 2, z_hi - 2):
        a, b = v.xy(y_face - 0.6, z), v.xy(y_face - 6.0, z)
        F.line(a[0], a[1], b[0], b[1], "ray")
        F.polyline([(b[0] - 7, b[1]), (b[0], b[1] - 3), (b[0], b[1] + 3)], "rayarrow", close=True)
    for z, sgn in ((z_hi, 1), (z_lo, -1)):
        a = v.xy(y_face - 0.4, z)
        b = v.xy(y_face - 0.4 - 7.5 * math.cos(math.radians(15)), z + sgn * 7.5 * math.sin(math.radians(15)))
        F.line(a[0], a[1], b[0], b[1], "ray")

    zc = H / 2
    y_back_in = g.y_tangent(xs) + capd.r                      # inside face of the back wall at this station
    F.text(*v.xy(11.5, zc - 0.8), "lamp housing", "inv", "middle")
    F.text(*v.xy(-2.6, zc - 0.8), "lens", "txt", "middle")

    def callout(y, z, X, Y, lines, anchor="start", elbow=None):
        """Leader from model point (y, z) to sheet point (X, Y), text lines start there."""
        x0, y0 = v.xy(y, z)
        ex, ey = elbow if elbow else (X - (6 if anchor == "start" else -6), Y - 4)
        F.line(x0, y0, ex, ey, "dim")
        F.arrow(x0, y0, math.atan2(y0 - ey, x0 - ex), 1.5)
        for i, t in enumerate(lines):
            F.text(X, Y + i * 16, t, "dimtxt", anchor)

    callout(-2.7, H + 0.55, 14, 46, ["Keeper tab hooks 2 mm", "over the sloped lens edge"], elbow=(120, 72))
    for i, t in enumerate(["Light window stays", "clear, incl. 15° up", "and 15° down"]):
        F.text(14, 150 + i * 16, t, "dimtxt")
    callout(-2.7, -0.55, 14, 292, ["Same tab underneath"], elbow=(150, 280))
    callout(20.0, H + capd.gap_z / 2, 420, 30, ["1 mm EPDM foam liner"], elbow=(414, 34))
    callout(g.y_tangent(xs) + capd.r + capd.t * 0.5, H + capd.gap_z + capd.t * 0.3, 536, 62,
            [f"{capd.t:.1f} mm stainless channel"], elbow=(530, 60))
    callout(y_back_in - capd.gap_back / 2, 6.0, 236, 296, ["2 mm EPDM foam liner"], elbow=(380, 282))
    callout(float(hole[1]) + 3.0, zc - 6.0, 452, 296, ["Ear and M5 screw into the boss", "beside the socket (behind this section)"],
            elbow=(560, 280))
    F.text(14, 352, f"Section through the cap and lamp at a keeper tab, {xs:.0f} mm from the root face. The lens faces left.", "small")
    return F


# ----------------------------------------------------------------------------- figure B: what to measure
def fig_measure(res) -> Fig:
    d, g, lamp = res["d"], res["g"], res["lamp"]
    lampd, mount = d.lamp, d.mount
    L, H = lampd.L, lampd.H
    hole = res["hole"]
    hy = float(hole[1])
    F = Fig(780, 624)
    k = 5.2

    # ---- plan
    F.text(330, 24, "PLAN  (looking down on the lamp)", "label")
    plan = View(F, 190, 300, k, 0.0, 0.0)
    shapes = {key: lamp[key] for key in ("HOUSING", "LENS", "NECK", "SOCKET", "BOSS")}
    pr = hlr.project(shapes, *hlr.VIEWS["top"], deflection=0.05)
    plan.projection(pr, {"NECK": "ref", "SOCKET": "ref", "BOSS": "ref", "HOUSING": "part", "LENS": "part"})
    y_face = -(lampd.lens_run + lampd.lens_nose)
    F.text(*plan.xy(L / 2, y_face / 2 - 0.9), "lens", "small", "middle")
    F.text(*plan.xy(L * 0.42, lampd.D_root * 0.45), "black housing, top face", "small", "middle")
    F.text(*plan.xy(-lampd.neck_len - 6, lampd.neck_y0 + lampd.neck_dy / 2 - 1), "socket", "small", "middle")
    F.text(*plan.xy(-mount.G_ear - 7, hy - 1), "screw boss", "small", "middle")
    plan.datum(-mount.G_ear - 16, hy, 8, hy, "screw axis", 1.0, 1.0)

    plan.dim_h(0, L, y_face, 9, f"M1   {L:.0f}")
    plan.dim_v(0, lampd.D_tip, L, 9, f"M4   {lampd.D_tip:.0f}")
    # M3 drawn just inside the root face
    a, b = plan.xy(1.6, 0), plan.xy(1.6, lampd.D_root)
    F.line(a[0], a[1], b[0], b[1], "dim")
    F.arrow(a[0], a[1], math.pi / 2)
    F.arrow(b[0], b[1], -math.pi / 2)
    F.text(a[0] + 7, (a[1] + b[1]) / 2 + 26, f"M3   {lampd.D_root:.0f}", "dimtxt")
    plan.dim_h(-lampd.neck_len, 0, lampd.neck_y0 - 4, 14, f"M6   {lampd.neck_len:.0f}", v_from2=0)
    plan.dim_h(-mount.G_ear, 0, hy + 8, -7, f"M7   {mount.G_ear:.0f}", v_from2=lampd.D_root)
    plan.dim_v(lampd.D_root, hy, 0, -9, f"M8   {mount.screw_behind_back:.0f}", u_from2=-mount.G_ear - 14)
    plan.leader(L * 0.8, 0.0, 6, 13.5, "housing / lens joint line  (y = 0)")
    plan.leader(0.0, lampd.D_root * 0.5, 9, -19, "root face of the head  (x = 0)")

    # ---- end view
    F.text(20, 398, "END VIEW  (from the tip)", "label")
    end = View(F, 150, 566, k, y_face, 0.0)
    pr2 = hlr.project({key: lamp[key] for key in ("HOUSING", "LENS", "BOSS")}, *hlr.VIEWS["tip"], deflection=0.05)
    end.projection(pr2, {"BOSS": "ref", "HOUSING": "part", "LENS": "part"})
    end.dim_v(0, H, y_face, -9, f"M2   {H:.0f}")
    end.leader(-lampd.lens_run / 2, H - lampd.lens_drop / 2, 7, -8,
               f"M5   lens chamfer: {lampd.lens_run:.1f} across (a), {lampd.lens_drop:.1f} down (b)")
    end.datum(-2, H / 2, hy + 12, H / 2, "mid-height of the head", 1.0, 1.0)
    end.leader(hy, H / 2 + mount.screw_dz, 5, -9, "M9   screw above (+) / below (-) mid-height:  0")
    F.text(470, 556, "M10  thread and length of the screw", "dimtxt")
    F.text(470, 572, "already in this boss (M5 assumed)", "dimtxt")
    F.text(20, 604, "Values shown are the photo estimates the model is built on. Measure and replace every one before cutting metal.", "small")
    return F


# ----------------------------------------------------------------------------- figure C: blank
def fig_blank(res) -> Fig:
    blank, sm = res["blank"], res["summary"]
    bb = blank.BoundingBox()
    k = 5.0
    F = Fig(780, 524)
    v = View(F, 70, 30 + bb.ylen * k, k, bb.xmin, bb.ymin)
    draw_blank_geometry(F, v, res)
    v.dim_h(bb.xmin, bb.xmax, bb.ymin, 7, f"{bb.xlen:.1f}")
    v.dim_v(bb.ymin, bb.ymax, bb.xmax, 8, f"{bb.ylen:.1f}")
    F.line(70, 512, 118, 512, "bendD")
    F.text(126, 516, "folds away from you (B1-B5, B7, B8)", "small")
    F.line(400, 512, 448, 512, "bendU")
    F.text(456, 516, "folds towards you (B6, the ear)", "small")
    return F


# ----------------------------------------------------------------------------- figure D: line isometric
def fig_iso(res) -> Fig:
    cap, lamp, hw = res["cap"], res["lamp"], res["hw"]
    shapes = {"CAP": cap, **{key: lamp[key] for key in ("HOUSING", "LENS", "NECK", "SOCKET", "BOSS")}, **hw}
    eye, xd = hlr.iso_view((0.95, -1.3, 0.78))
    pr = hlr.project(shapes, eye, xd, deflection=0.04)
    x0, y0, x1, y1 = hlr.bounds(pr)
    k = 7.2
    m = 14
    F = Fig(round((x1 - x0) * k + 2 * m), round((y1 - y0) * k + 2 * m))
    v = View(F, m, m + (y1 - y0) * k, k, x0, y0)
    v.projection(pr, {"NECK": "ref", "SOCKET": "ref", "BOSS": "ref", "WASHER": "ref", "SCREW": "ref",
                      "HOUSING": "ref", "LENS": "ref", "CAP": "part"})
    return F


def make_all(res, docs: Path = DOCS):
    docs.mkdir(parents=True, exist_ok=True)
    figs = {
        "fig_section": (fig_section(res), "Section through the cap at a keeper tab"),
        "fig_measure": (fig_measure(res), "Dimensions to measure on the lamp and its mount"),
        "fig_blank": (fig_blank(res), "Flat blank with bend lines"),
        "fig_iso": (fig_iso(res), "Cap on the lamp, isometric"),
    }
    out = {}
    for name, (fig, title) in figs.items():
        fig.write(docs / f"{name}.svg", title)
        out[name] = fig.svg(title)
    return out


if __name__ == "__main__":
    res = build(Design(), OUT, "SS304 1.5 mm")
    make_all(res)
    print("figures written to", DOCS)
