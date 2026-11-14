#!/usr/bin/env python3
"""
Drawings for the indicator cap, written as SVG in true millimetres:

    out/drawing_formed.svg   A3  formed part, three views + isometric, key dimensions
    out/drawing_blank.svg    A3  flat blank, bend lines, bend table
    out/template_1to1.svg    A4  blank at 1:1 to print on card for a fit check

`node svg2pdf.js` turns them into PDFs (same folder).
"""
from __future__ import annotations

import datetime
import math
from pathlib import Path

import numpy as np

import hlr
from build import build, OUT, SHOP_DIR, BEND_ORDER, wire_to_bulge_points
from params import Design

DRG_NO = "IC-390A-01"
REV = "A"


# ----------------------------------------------------------------------------- tiny SVG writer
class Sheet:
    CSS = """
      .frame{fill:none;stroke:#111;stroke-width:.5}
      .part{fill:none;stroke:#111;stroke-width:.4;stroke-linejoin:round;stroke-linecap:round}
      .ref{fill:none;stroke:#8a8f98;stroke-width:.2;stroke-linejoin:round}
      .cut{fill:#eef1f4;stroke:#111;stroke-width:.4;stroke-linejoin:round}
      .hole{fill:#fff;stroke:#111;stroke-width:.4}
      .bendD{fill:none;stroke:#0a7d3c;stroke-width:.3;stroke-dasharray:4 1.2 .8 1.2}
      .bendU{fill:none;stroke:#c22727;stroke-width:.3;stroke-dasharray:4 1.2 .8 1.2}
      .dim{fill:none;stroke:#1f4e9c;stroke-width:.18}
      .arrow{fill:#1f4e9c;stroke:none}
      .dimtxt{font:2.6px 'DejaVu Sans',Arial,sans-serif;fill:#1f4e9c}
      .txt{font:2.8px 'DejaVu Sans',Arial,sans-serif;fill:#111}
      .small{font:2.2px 'DejaVu Sans',Arial,sans-serif;fill:#333}
      .label{font:bold 3.2px 'DejaVu Sans',Arial,sans-serif;fill:#111}
      .title{font:bold 5px 'DejaVu Sans',Arial,sans-serif;fill:#111}
      .warn{font:bold 2.8px 'DejaVu Sans',Arial,sans-serif;fill:#b3261e}
      .tb{fill:none;stroke:#111;stroke-width:.3}
      .datum{fill:none;stroke:#c2410c;stroke-width:.2;stroke-dasharray:3 1}
      .datumtxt{font:2.3px 'DejaVu Sans',Arial,sans-serif;fill:#c2410c}
    """

    U = 1.0   # size of one "drawing millimetre" in sheet units (figures for the web page use px and override this)

    def __init__(self, w, h):
        self.w, self.h = w, h
        self.items = []

    def add(self, s):
        self.items.append(s)

    def line(self, x1, y1, x2, y2, cls="part"):
        self.add(f'<line class="{cls}" x1="{x1:.3f}" y1="{y1:.3f}" x2="{x2:.3f}" y2="{y2:.3f}"/>')

    def polyline(self, pts, cls="part", close=False):
        d = " ".join(f"{x:.3f},{y:.3f}" for x, y in pts)
        tag = "polygon" if close else "polyline"
        self.add(f'<{tag} class="{cls}" points="{d}"/>')

    def path(self, d, cls):
        self.add(f'<path class="{cls}" d="{d}"/>')

    def rect(self, x, y, w, h, cls="tb"):
        self.add(f'<rect class="{cls}" x="{x:.3f}" y="{y:.3f}" width="{w:.3f}" height="{h:.3f}"/>')

    def text(self, x, y, s, cls="txt", anchor="start", rotate=0):
        s = str(s).replace("&", "&amp;").replace("<", "&lt;")
        tr = f' transform="rotate({rotate:.2f} {x:.3f} {y:.3f})"' if rotate else ""
        self.add(f'<text class="{cls}" x="{x:.3f}" y="{y:.3f}" text-anchor="{anchor}"{tr}>{s}</text>')

    def arrow(self, x, y, ang, size=1.8):
        size *= self.U
        a1, a2 = ang + math.radians(160), ang - math.radians(160)
        pts = [(x, y), (x + size * math.cos(a1), y + size * math.sin(a1)), (x + size * math.cos(a2), y + size * math.sin(a2))]
        self.polyline(pts, "arrow", close=True)

    def save(self, path: Path):
        body = "\n".join(self.items)
        path.write_text(
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}mm" height="{self.h}mm" '
            f'viewBox="0 0 {self.w} {self.h}"><style>{self.CSS}</style>'
            f'<rect width="{self.w}" height="{self.h}" fill="#fff"/>\n{body}\n</svg>\n'
        )


class View:
    """Maps model (u, v) in mm to sheet coordinates. (u0, v0) lands at (ox, oy); v is up."""

    def __init__(self, sheet: Sheet, ox, oy, scale, u0=0.0, v0=0.0):
        self.s, self.ox, self.oy, self.k, self.u0, self.v0 = sheet, ox, oy, scale, u0, v0

    def xy(self, u, v):
        return self.ox + (u - self.u0) * self.k, self.oy - (v - self.v0) * self.k

    def polylines(self, pls, cls):
        for pl in pls:
            self.s.polyline([self.xy(u, v) for u, v in pl], cls)

    def projection(self, proj, styles):
        for name, cls in styles.items():
            if name in proj:
                self.polylines(proj[name]["visible"], cls)

    # --- dimensions -------------------------------------------------------
    def dim_h(self, u1, u2, v_from, off, text=None, v_from2=None):
        """Horizontal dimension between u1 and u2. `off` = sheet mm from the feature (+ = below)."""
        x1, y1 = self.xy(u1, v_from)
        x2, y2 = self.xy(u2, v_from if v_from2 is None else v_from2)
        U = self.s.U
        off *= U
        yd = (max(y1, y2) + off) if off > 0 else (min(y1, y2) + off)
        e = (1.2 if off > 0 else -1.2) * U
        self.s.line(x1, y1 + e, x1, yd + e, "dim")
        self.s.line(x2, y2 + e, x2, yd + e, "dim")
        self.s.line(x1, yd, x2, yd, "dim")
        self.s.arrow(x1, yd, math.pi if x2 > x1 else 0)
        self.s.arrow(x2, yd, 0 if x2 > x1 else math.pi)
        self.s.text((x1 + x2) / 2, yd - 0.9 * U, text if text is not None else f"{abs(u2 - u1):.1f}", "dimtxt", "middle")

    def dim_v(self, v1, v2, u_from, off, text=None, u_from2=None):
        """Vertical dimension between v1 and v2. `off` = sheet mm from the feature (+ = right)."""
        x1, y1 = self.xy(u_from, v1)
        x2, y2 = self.xy(u_from if u_from2 is None else u_from2, v2)
        U = self.s.U
        off *= U
        xd = (max(x1, x2) + off) if off > 0 else (min(x1, x2) + off)
        e = (1.2 if off > 0 else -1.2) * U
        self.s.line(x1 + e, y1, xd + e, y1, "dim")
        self.s.line(x2 + e, y2, xd + e, y2, "dim")
        self.s.line(xd, y1, xd, y2, "dim")
        self.s.arrow(xd, y1, math.pi / 2 if y1 > y2 else -math.pi / 2)
        self.s.arrow(xd, y2, -math.pi / 2 if y1 > y2 else math.pi / 2)
        self.s.text(xd - 0.9 * U, (y1 + y2) / 2, text if text is not None else f"{abs(v2 - v1):.1f}", "dimtxt", "middle", rotate=-90)

    def leader(self, u, v, dx, dy, text, anchor="start"):
        U = self.s.U
        x, y = self.xy(u, v)
        xe, ye = x + dx * U, y + dy * U
        self.s.line(x, y, xe, ye, "dim")
        self.s.arrow(x, y, math.atan2(y - ye, x - xe), 1.5)
        self.s.text(xe + (0.8 if anchor == "start" else -0.8) * U, ye + 0.9 * U, text, "dimtxt", anchor)

    def datum(self, u1, v1, u2, v2, text, tx=0.0, ty=0.0, anchor="start"):
        U = self.s.U
        x1, y1 = self.xy(u1, v1)
        x2, y2 = self.xy(u2, v2)
        self.s.line(x1, y1, x2, y2, "datum")
        self.s.text(x2 + tx * U, y2 + ty * U, text, "datumtxt", anchor)


def frame(sheet: Sheet, title, sub, scale_txt, summary, sheet_no):
    w, h = sheet.w, sheet.h
    sheet.rect(8, 8, w - 16, h - 16, "frame")
    bw, bh = 150, 34
    x0, y0 = w - 8 - bw, h - 8 - bh
    sheet.rect(x0, y0, bw, bh)
    sheet.line(x0, y0 + 12, x0 + bw, y0 + 12, "tb")
    sheet.line(x0, y0 + 23, x0 + bw, y0 + 23, "tb")
    sheet.line(x0 + 96, y0 + 12, x0 + 96, y0 + bh, "tb")
    sheet.text(x0 + 3, y0 + 5.2, title, "title")
    sheet.text(x0 + 3, y0 + 10, sub, "small")
    sheet.text(x0 + 3, y0 + 16.5, f"Material: {summary['material']}", "small")
    sheet.text(x0 + 3, y0 + 20.5, f"Inside bend radius {summary['inside_radius']:.1f}   K {summary['k_factor']:.2f}   mass {summary['mass_g']} g", "small")
    sheet.text(x0 + 3, y0 + 27.5, "Finish: deburr all edges, bead blast, black textured powder coat", "small")
    sheet.text(x0 + 3, y0 + 31.5, "Tolerances: cut ±0.15   formed ±0.5   bends ±1°", "small")
    sheet.text(x0 + 99, y0 + 16.5, f"Drg {DRG_NO}   Rev {REV}", "small")
    sheet.text(x0 + 99, y0 + 20.5, f"Sheet {sheet_no}   Scale {scale_txt}", "small")
    sheet.text(x0 + 99, y0 + 27.5, f"Date {datetime.date.today().isoformat()}", "small")
    sheet.text(x0 + 99, y0 + 31.5, "Units mm   3rd-angle views", "small")
    sheet.text(12, h - 11, "REV A: lamp and mount dimensions are scaled from photographs, not measured. "
                           "Confirm M1-M10 on a real lamp before cutting metal.", "warn")


# ----------------------------------------------------------------------------- sheet 1: formed part
def draw_formed(res, path: Path):
    d, g, cap, lamp, hw, sm = res["d"], res["g"], res["cap"], res["lamp"], res["hw"], res["summary"]
    L, H = d.lamp.L, d.lamp.H
    capd = d.cap
    hole = res["hole"]
    env = sm["formed_envelope"]
    S = Sheet(420, 297)
    frame(S, "KTM indicator slip-on cap", "390 Adventure (2025+) LED lamp   one part fits left/right, front/rear", "2:1", sm, "1 of 2")
    k = 2.0
    shapes = {"CAP": cap, "HOUSING": lamp["HOUSING"], "LENS": lamp["LENS"], "NECK": lamp["NECK"]}
    styles = {"HOUSING": "ref", "LENS": "ref", "NECK": "ref", "CAP": "part"}

    # --- plan view (looking down): u = x, v = y
    top = View(S, 52, 124, k)
    top.projection(hlr.project(shapes, *hlr.VIEWS["top"], deflection=0.03), styles)
    S.text(96, 20, "PLAN  (top plate)", "label")
    sa, ca = math.sin(g.al), math.cos(g.al)
    y_bw_out_ear = d.lamp.D_root + (capd.gap_back + capd.t) * ca - g.s_root * sa   # outside of back wall at the ear bend
    y_bw_out_root = g.y_tangent(capd.plate_root_x) + capd.r + capd.t              # ... at the root end of the plates
    y_bw_out_tip = g.y_tangent(g.x_tip_plate) + capd.r + capd.t
    y_low = env["y"][0] - 1.0                                                      # just in front of the lens
    top.datum(0, y_low - 1, 0, 46, "x = 0  root face of lamp head", 1.0, 1.5)
    top.datum(-11, 0, 87, 0, "y = 0  housing / lens joint", 1.0, -1.0)
    for i, xc in enumerate(capd.tab_x):
        top.dim_h(0, xc, y_low, 6 + 5 * i, f"{xc:.0f}")
    top.dim_h(capd.plate_root_x, g.x_tip_plate, y_low, 17, f"{g.x_tip_plate - capd.plate_root_x:.1f} plates")
    top.dim_h(env["x"][0], env["x"][1], y_low, 23, f"{env['x'][1] - env['x'][0]:.1f} overall")
    top.leader(capd.tab_x[1] + capd.tab_w / 2 - 1, g.y_tab - 2.5, 18, 2, f"4 x keeper tab, {capd.tab_w:.0f} wide")
    top.dim_v(g.y_edge, y_bw_out_tip, g.x_tip_plate, 9, f"{y_bw_out_tip - g.y_edge:.1f}")
    top.dim_v(g.y_edge, y_bw_out_root, capd.plate_root_x, -22, f"{y_bw_out_root - g.y_edge:.1f}")
    top.dim_v(d.lamp.D_root, float(hole[1]), 0, -8, f"{float(hole[1]) - d.lamp.D_root:.1f} (M8)", u_from2=env["x"][0])
    top.dim_h(env["x"][0], 0, env["y"][1] + 1, -5, f"{-env['x'][0]:.1f} (M7)")
    top.leader(capd.slot_x[2], (g.y_edge + g.y_tangent(capd.slot_x[2])) / 2 + 2, 30, -44,
               f"3 x slot {capd.slot_w:.0f} wide at {capd.slot_angle:.0f}°,  x = " + " / ".join(f"{x:.0f}" for x in capd.slot_x))
    top.leader(30, g.y_tangent(30) + capd.r + capd.t, 14, -16, f"back wall follows the lamp taper, {math.degrees(g.al):.1f}°")

    # --- lens-side elevation: u = x, v = z
    front = View(S, 52, 234, k)
    front.projection(hlr.project(shapes, *hlr.VIEWS["lens"], deflection=0.03), styles)
    S.text(52, 178, "VIEW ON LENS", "label")
    front.dim_v(env["z"][0], env["z"][1], env["x"][1], 9, f"{env['z'][1] - env['z'][0]:.1f}")
    front.dim_v(-capd.gap_z, H + capd.gap_z, env["x"][0], -8, f"{g.Hc:.1f} inside")
    front.dim_h(0, L, env["z"][0], 8, f"lamp head {L:.0f} (M1)")

    # --- end view from the tip: u = y, v = z
    tipv = View(S, 264, 234, k)
    shapes_tip = dict(shapes)
    shapes_tip.update(hw)
    tipv.projection(hlr.project(shapes_tip, *hlr.VIEWS["tip"], deflection=0.03),
                    {**styles, "WASHER": "ref", "SCREW": "ref"})
    S.text(252, 162, "VIEW ON TIP", "label")
    tipv.dim_h(env["y"][0], env["y"][1], env["z"][0], 8, f"{env['y'][1] - env['y'][0]:.1f}")
    zc = H / 2
    tipv.dim_v(zc - g.he / 2, zc + g.he / 2, env["y"][1], 7, f"{g.he:.1f} ear")
    tipv.leader(float(hole[1]), zc, 4, -30, f"slot {capd.ear_slot_w:.1f} x {capd.ear_slot_len:.1f} for M{d.mount.screw_d:.0f}", "end")
    tipv.leader(g.y_tab - 3.0, H - 0.4, -1.5, -12, f"tab {capd.tab_angle:.0f}°", "end")
    tipv.leader(y_bw_out_tip - capd.t / 2, zc + 4, 6, -34, f"t {capd.t:.1f}, inside R{capd.r:.1f}", "end")

    # --- isometric, not to scale
    eye, xd = hlr.iso_view((0.95, -1.25, 0.8))
    iso_shapes = dict(shapes)
    iso_shapes.update(hw)
    iso_shapes["SOCKET"] = lamp["SOCKET"]
    iso_shapes["BOSS"] = lamp["BOSS"]
    pr = hlr.project(iso_shapes, eye, xd, deflection=0.03)
    x0, y0, x1, y1 = hlr.bounds(pr)
    ki = 1.55
    iso = View(S, 262, 28 + (y1 - y0) * ki, ki, x0, y0)
    iso.projection(pr, {**styles, "SOCKET": "ref", "BOSS": "ref", "WASHER": "ref", "SCREW": "ref"})
    S.text(252, 20, "ISOMETRIC  (not to scale, lamp and mount shown thin)", "label")

    notes = [
        "1. One part, symmetric top to bottom: turn it over for the other side of the bike.",
        "2. Line inside faces with self-adhesive EPDM foam: plates 1 mm, back wall 2 mm, tip wall 3 mm, tabs 1 mm.",
        "3. Slide on from the lamp tip, seat the ear on the boss, fit screw with Ø12-15 washer. Do not overtighten in plastic.",
        "4. Nothing may sit in front of the lens face. Tabs only lap the chamfer above and below the light window.",
        "5. Break all edges; outside corners R3 as drawn.",
    ]
    for i, s in enumerate(notes):
        S.text(12, 258 + i * 4.2, s, "small")
    S.save(path)


# ----------------------------------------------------------------------------- blank geometry helpers
def wire_path(pts, view: View):
    """LWPOLYLINE-style (x, y, bulge) list -> SVG path in sheet coordinates."""
    n = len(pts)
    x0, y0 = view.xy(pts[0][0], pts[0][1])
    d = [f"M{x0:.3f},{y0:.3f}"]
    for i in range(n):
        x1, y1, b = pts[i]
        x2, y2, _ = pts[(i + 1) % n]
        X2, Y2 = view.xy(x2, y2)
        if abs(b) < 1e-12:
            d.append(f"L{X2:.3f},{Y2:.3f}")
        else:
            c = math.hypot(x2 - x1, y2 - y1)
            th = 4 * math.atan(abs(b))
            r = c / (2 * math.sin(th / 2)) * view.k
            large = 1 if th > math.pi else 0
            sweep = 0 if b > 0 else 1      # y axis is flipped on the sheet
            d.append(f"A{r:.3f},{r:.3f} 0 {large} {sweep} {X2:.3f},{Y2:.3f}")
    d.append("Z")
    return " ".join(d)


def draw_blank_geometry(S: Sheet, view: View, res, label_bends=True, fill=True):
    blank, lines = res["blank"], res["lines"]
    outer = wire_to_bulge_points(blank.outerWire())
    S.path(wire_path(outer, view), "cut" if fill else "part")
    for w in blank.innerWires():
        S.path(wire_path(wire_to_bulge_points(w), view), "hole" if fill else "part")
    idx = {lab: i + 1 for i, lab in enumerate(BEND_ORDER)}
    for ln in lines:
        shop = SHOP_DIR[ln["direction"]]
        a, b = view.xy(*ln["a"]), view.xy(*ln["b"])
        S.line(a[0], a[1], b[0], b[1], "bendD" if shop == "DOWN" else "bendU")
        if label_bends:
            mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
            ang = math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))
            if ang > 90 or ang < -90:
                ang += 180
            S.text(mx, my - 1.0 * S.U, f"B{idx[ln['label']]}", "small", "middle", rotate=ang)


# ----------------------------------------------------------------------------- sheet 2: blank
def draw_blank(res, path: Path):
    d, g, sm, blank, lines, placed = res["d"], res["g"], res["summary"], res["blank"], res["lines"], res["placed"]
    capd = d.cap
    S = Sheet(420, 297)
    frame(S, "KTM indicator slip-on cap - flat blank", "Laser profile and bend lines. The DXF is the master for cutting.", "2:1", sm, "2 of 2")
    bb = blank.BoundingBox()
    k = 2.0
    view = View(S, 38, 232, k, bb.xmin, bb.ymin)
    draw_blank_geometry(S, view, res)
    S.text(38, 22, "FLAT BLANK   outside (cosmetic) face up", "label")

    view.dim_h(bb.xmin, bb.xmax, bb.ymin, 9, f"{bb.xlen:.1f}")
    view.dim_v(bb.ymin, bb.ymax, bb.xmax, 18, f"{bb.ylen:.1f}")
    hb, ht, he, Lbw = g.hb, g.ht, g.he, g.Lbw
    ba_tip, ba90 = capd.ba(g.tip_angle), capd.ba90
    view.dim_h(0, Lbw, -hb / 2, 62, f"{Lbw:.2f} back wall, tangent to tangent", v_from2=-hb / 2)
    view.dim_v(-hb / 2, hb / 2, 40, -8, f"{hb:.2f}")
    view.dim_v(-ht / 2, ht / 2, -ba_tip - g.tip_len, -7, f"{ht:.2f}")
    view.dim_h(-ba_tip - g.tip_len, -ba_tip, ht / 2, -5, f"{g.tip_len:.2f}")
    view.dim_h(-ba_tip, 0, ht / 2, -11, f"BA {ba_tip:.2f}")
    xe0 = Lbw + capd.ba(g.ear_angle)
    view.dim_h(xe0, xe0 + g.q_hole, 0, 20, f"{g.q_hole:.2f}", v_from2=0)
    view.dim_v(-he / 2, he / 2, xe0 + g.q_hole + he / 2, 7, f"{he:.2f}")
    view.dim_v(hb / 2, hb / 2 + ba90, g.pT_b, 9, f"BA {ba90:.2f}")
    view.leader(xe0 + g.q_hole, 0, 9, -24, f"slot {capd.ear_slot_w:.1f} x {capd.ear_slot_len:.1f}")

    # bend table
    tx, ty = 292, 22
    S.text(tx, ty, "BEND TABLE  (in bend order)", "label")
    heads = ["ID", "Feature", "Dir", "Angle", "Length", "Allow."]
    cols = [0, 12, 44, 60, 78, 97]
    ty += 6
    for c, h in zip(cols, heads):
        S.text(tx + c, ty, h, "small")
    S.line(tx, ty + 1.5, tx + 114, ty + 1.5, "tb")
    for i, b in enumerate(sm["bends"]):
        y = ty + 6 + i * 5
        vals = [b["id"], b["feature"].replace("_", " "), b["direction"], f"{b['angle']:.1f}°", f"{b['length']:.1f}", f"{b['allowance']:.2f}"]
        for c, v in zip(cols, vals):
            S.text(tx + c, y, v, "small")
    y = ty + 6 + len(sm["bends"]) * 5 + 3
    key = [
        ("bendD", "DOWN = flange folds away from viewer"),
        ("bendU", "UP = flange folds towards viewer"),
    ]
    for i, (cls, s) in enumerate(key):
        S.line(tx, y + i * 5 - 1, tx + 16, y + i * 5 - 1, cls)
        S.text(tx + 19, y + i * 5, s, "small")
    y += 14
    notes = [
        f"Blank {bb.xlen:.1f} x {bb.ylen:.1f}, area {sm['blank']['area']:.0f} mm², "
        f"cut length {sm['blank']['cut_length']:.0f} mm, {sm['blank']['pierces']} pierces.",
        "Bend lines are bend centre lines.",
        f"Bend allowance = angle x (R + K t), R {capd.r:.1f}, K {capd.k:.2f}.",
        "Adjust K to your tooling and re-run build.py;",
        "the inside dimensions are held, the blank changes.",
        "Form tabs B1-B4 first, then B5, B6, then the two",
        f"long bends B7, B8 over a {g.Hc:.1f} mm form block or with",
        "a gooseneck punch (channel is deeper than it is wide).",
        "Tabs may be trimmed to the lamp by hand with",
        "pliers after the liner is fitted.",
        "Grain along the long bends if the sheet allows.",
    ]
    for i, s in enumerate(notes):
        S.text(tx, y + i * 4.4, s, "small")
    S.save(path)


# ----------------------------------------------------------------------------- 1:1 card template
def draw_template(res, path: Path):
    d, g, sm, blank = res["d"], res["g"], res["summary"], res["blank"]
    S = Sheet(210, 297)
    bb = blank.BoundingBox()
    view = View(S, (210 - bb.xlen) / 2, 62 + bb.ylen, 1.0, bb.xmin, bb.ymin)
    S.text(14, 18, "KTM indicator cap - 1:1 card fit-check template", "title")
    S.text(14, 25, "Print at 100 % (\"actual size\", no fit-to-page). Check the bar below with a ruler before cutting.", "txt")
    # 100 mm check bar
    bx, by = 14, 36
    S.line(bx, by, bx + 100, by, "part")
    for i in range(0, 101, 10):
        S.line(bx + i, by - (2.5 if i % 50 == 0 else 1.5), bx + i, by, "part")
        if i % 50 == 0:
            S.text(bx + i, by - 3.5, f"{i}", "small", "middle")
    S.text(bx + 104, by + 1, "this bar must measure 100 mm", "small")
    draw_blank_geometry(S, view, res, label_bends=True, fill=False)
    y = 62 + bb.ylen + 14
    steps = [
        "1. Glue this sheet to 1 mm card (cereal-box card works) and cut round the solid outline. Cut out the slots if you like.",
        "2. Score the dash-dot lines. Green lines fold AWAY from you, the one red line (B6, the ear) folds TOWARDS you.",
        f"3. Fold B7 and B8 to 90° to make the channel, B5 to close the tip, the four small tabs about {d.cap.tab_angle:.0f}° inwards,",
        "   and B6 so the ear stands square to the lamp.",
        "4. Slide it over the lamp from the tip. It should stop about 2 mm short of the tip, with about 1 mm play top and bottom",
        "   and 1.5 mm at the back (that space is for the foam liner). The tabs should sit on the sloped edge of the lens,",
        "   not on the lit face. The ear should land flat on the screw boss with the slot over the screw hole.",
        "5. Wherever it does not, measure the difference and change the matching value in cad/params.py (M1-M10),",
        "   then run build.py and drawing.py again. Only cut metal once the card version fits.",
        "",
        f"Card folds sharp, steel bends on a {d.cap.r:.1f} mm radius, so the card model runs about 0.4 mm larger inside. That is expected.",
    ]
    for i, s in enumerate(steps):
        S.text(14, y + i * 4.6, s, "small")
    S.text(14, 285, f"Drg {DRG_NO} Rev {REV}   lamp dimensions from photographs, unverified   {sm['material']}", "small")
    S.save(path)


if __name__ == "__main__":
    res = build(Design(), OUT, "SS304 1.5 mm")
    draw_formed(res, OUT / "drawing_formed.svg")
    draw_blank(res, OUT / "drawing_blank.svg")
    draw_template(res, OUT / "template_1to1.svg")
    print("drawings written to", OUT)
