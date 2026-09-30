#!/usr/bin/env python3
"""Build the specification sheets (one 4-page PDF per grip) and the combined spec book.

    python3 build_specs.py                 # everything
    python3 build_specs.py --only 01 07    # just those sheets (no book)
    python3 build_specs.py --no-book

needs specs/assets/<id>/ from render_spec_assets.py and spec_data.py, plus the verify reports.
"""
import argparse
import json
import math
import re
import sys
import zipfile
from datetime import date
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pdfkit import *  # noqa: E402,F401,F403
from pdfkit import MM, PAGE_W, PAGE_H  # noqa: E402
from spec_content import CONTENT  # noqa: E402
from designs import DESIGNS  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "specs" / "assets"
OUTDIR = ROOT / "specs"
TODAY = date.today().isoformat()
REV = "2"
LIMIT_G = 50.0

FIT = {r["name"]: r for r in json.loads((ROOT / "fitment_report.json").read_text())}
PRT = {r["name"]: r for r in json.loads((ROOT / "print_report.json").read_text())}
REF = json.loads((ROOT / "data" / "reference_profile.json").read_text())
LABEL = {n: l for n, l, _ in DESIGNS}
NAMES = [n for n, _, _ in DESIGNS]


def load(name):
    rec = json.loads((ASSETS / name / "data.json").read_text())
    rec["ortho"] = json.loads((ASSETS / name / "ortho.json").read_text())
    rec["fit"], rec["prt"], rec["content"] = FIT[name], PRT[name], CONTENT[name]
    rec["dir"] = ASSETS / name
    with zipfile.ZipFile(ROOT / "3mf" / f"{name}.3mf") as z:
        rec["palette"] = ["#" + h for h in re.findall(r'<m:color color="#([0-9A-F]{6})FF"/>', z.read("3D/3dmodel.model").decode())]
    rec["stl_mb"] = (ROOT / "stl" / f"{name}.stl").stat().st_size / 1e6
    rec["mf_mb"] = (ROOT / "3mf" / f"{name}.3mf").stat().st_size / 1e6
    rec["docno"] = f"PG-{rec['content']['id']}"
    return rec


def dash(s):
    return s.replace(" - ", " – ").replace(" x ", " × ")


def bar_col(acc):
    """Accent for weight bars: reds read as 'over the limit' next to the red 50 g line, so use slate instead."""
    r, g, b = (int(acc[i:i + 2], 16) for i in (1, 3, 5))
    return "#59636F" if (r > 150 and g < 90 and b < 90) else acc


def fmm(v, n=2):
    return f"{v:.{n}f}"


def interp_prof(rec, z):
    """Profile values linearly interpolated to an exact height z."""
    zs = np.array([p["z"] for p in rec["profile"]])
    out = {"z": z}
    for k in ("w", "d", "perim", "area", "off_max"):
        out[k] = float(np.interp(z, zs, [p[k] for p in rec["profile"]]))
    i = int(np.clip(np.searchsorted(zs, z), 1, len(zs) - 1))
    lo, hi = rec["profile"][i - 1]["off_min"], rec["profile"][i]["off_min"]
    out["off_min"] = None if (lo is None or hi is None) else float(np.interp(z, zs[i - 1:i + 1], [lo, hi]))
    return out


def img_aspect(path):
    from PIL import Image
    with Image.open(path) as im:
        return im.width / im.height


def rim_start_z():
    """Height where the reference taper thins to the 0.8 mm minimum rim."""
    tz, te = np.array(REF["taper_table"]).T
    return float(np.interp(0.8, te[::-1], tz[::-1]))


# ------------------------------------------------------------------------------------------------
# shared furniture
# ------------------------------------------------------------------------------------------------
class Ctx:
    def __init__(self, c, page_no=1, total=1, book=False, sheet_of=4):
        self.c, self.pg, self.page_no, self.total, self.book, self.sheet_of = c, Page(c), page_no, total, book, sheet_of


def furniture(cx, rec, section, sheet_no):
    pg, acc = cx.pg, rec["content"]["accent"]
    pg.text(12, 12.4, "PICKLEBALL GRIP SPECIFICATION", F_B, 6.6, INK)
    pg.text(198, 12.4, f"{rec['docno']}  ·  {rec['label']}  ·  {section.upper()}", F_R, 6.6, MUTED, anchor="r")
    pg.line(12, 14.6, 198, 14.6, HAIR, 0.2)
    pg.rect(12, 14.1, 26, 1.0, fill=acc)
    pg.line(12, 283.5, 198, 283.5, HAIR, 0.2)
    pg.text(12, 287.6, "Fitted to PickleballGrip_1.3mf  ·  dimensions in mm unless noted  ·  measured from the STL files", F_R, 6.2, SUBTLE)
    lab = f"Page {cx.page_no} of {cx.total}" if cx.book else f"Sheet {sheet_no} of {cx.sheet_of}"
    pg.text(198, 287.6, lab, F_R, 6.2, SUBTLE, anchor="r")


def heading(pg, x, y, text, acc, w=None):
    pg.rect(x, y - 3.2, 1.5, 3.9, fill=acc)
    pg.text(x + 3.2, y, text.upper(), F_B, 7.0, INK)
    if w:
        pg.line(x + 3.2 + sw(text.upper(), F_B, 7.0) / MM + 2.0, y - 1.1, x + w, y - 1.1, HAIR, 0.2)
    return y + 2.6


def check(pg, x, y, s=2.2, color=GREEN, w=0.55):
    pg.polyline([(x, y), (x + s * 0.38, y + s * 0.42), (x + s, y - s * 0.55)], color, w)


def pill(pg, x, y, text, color=GREEN, size=6.2, pad=2.4, tick=True):
    w = sw(text, F_B, size) / MM + pad * 2 + (3.4 if tick else 0)
    pg.rect(x, y, w, 5.4, fill=tint(color, 0.86), stroke=None, r=2.7)
    if tick:
        check(pg, x + pad, y + 2.9, 2.0, color, 0.5)
    pg.text(x + pad + (3.4 if tick else 0), y + 3.75, text, F_B, size, shade(color, 0.15))
    return w


# ------------------------------------------------------------------------------------------------
# PAGE 1 - overview
# ------------------------------------------------------------------------------------------------
def page_overview(cx, rec):
    pg, ct, acc = cx.pg, rec["content"], rec["content"]["accent"]
    ov, br, pk, zn = rec["overall"], rec["bore"], rec["peaks"], rec["zones"]
    furniture(cx, rec, "Overview", 1)

    # ---- title band
    pg.text(12, 42.5, ct["id"], F_B, 50, acc)
    pg.text(41, 31.5, rec["label"], F_B, 26, INK)
    pg.para(41, 34.6, ct["tagline"], 100, F_R, 10.2, MUTED, leading=13.2, max_lines=3)
    # weight callout
    pg.rect(146, 20, 52, 27.5, fill=PANEL, r=2.5)
    w_pla = ov["weight_g"]["PLA"]
    pg.text(172, 35.2, f"{w_pla:.1f} g", F_B, 25, INK, anchor="c")
    pg.text(172, 40.2, "PLA · 100 % infill · solid", F_R, 6.6, MUTED, anchor="c")
    pill(pg, 150.2, 42.0, "UNDER 50 G IN ALL 4 MATERIALS", GREEN, 5.4, 2.0)

    # ---- hero
    hx, hy, hw = 12, 52.5, 88.0
    hh = hw * 2400 / 1400
    pg.image(rec["dir"] / "hero.png", hx, hy, hw, hh, quality=88, round_=3, max_px=1500)
    pg.text(hx + 3.5, hy + hh - 3.5, "3/4 view · rendered from the STL, colours are preview only", F_R, 5.6, SUBTLE)

    # ---- right column
    x0, wcol = 104.0, 94.0
    y = 56.0
    y = heading(pg, x0, y, "At a glance", acc, wcol)
    rows = [("Overall height", f"{ov['z']:.2f} mm"),
            ("Max footprint (foot)", f"{ov['x']:.2f} × {ov['y']:.2f} mm"),
            ("Bore", f"{br['x']:.2f} × {br['y']:.2f} mm, {br['depth']:.1f} deep"),
            ("Textured band", f"z {zn['tex_lo']:.1f} – {zn['tex_hi']:.1f} mm ({zn['tex_hi'] - zn['tex_lo']:.1f} tall)"),
            ("Outer size in band (max)", f"{pk['max_w']:.1f} × {pk['max_d']:.1f} mm"),
            ("Peak texture height", f"{pk['peak_offset']:.2f} mm above bore"),
            ("Base wall / min rim", f"{zn['base_wall']:.1f} mm / {zn['rim_wall']:.1f} mm"),
            ("Volume / surface area", f"{ov['volume_cm3']:.2f} cm³ / {ov['surface_area_cm2']:.0f} cm²")]
    y = table(pg, x0, y, [42, 52], rows, row_h=5.5, size=7.6, aligns=["l", "r"], fonts=[F_R, F_B], zebra=False) + 4.6

    y = heading(pg, x0, y, "Weight · 100 % infill", acc, wcol)
    bar0, barw = 145.0, 40.0
    track = 60.0
    for mat, dens in (("PLA", 1.24), ("PETG", 1.27), ("TPU", 1.21), ("ABS", 1.04)):
        wg = ov["weight_g"][mat]
        pg.text(x0 + 1, y + 4.0, mat, F_B, 7.4, INK)
        pg.text(x0 + 12, y + 4.0, f"{dens:.2f} g/cm³", F_R, 6.4, MUTED)
        pg.rect(bar0, y + 1.2, barw, 3.0, fill=PANEL2, r=0.8)
        pg.rect(bar0, y + 1.2, barw * wg / track, 3.0, fill=bar_col(acc), r=0.8)
        pg.text(x0 + wcol - 0.5, y + 4.0, f"{wg:.1f} g", F_B, 7.6, INK, anchor="r")
        y += 6.1
    lx = bar0 + barw * LIMIT_G / track
    pg.line(lx, y - 24.6, lx, y - 0.6, RED, 0.25, dash=[0.8, 0.6])
    pg.text(lx, y + 2.3, "50 g limit", F_R, 5.6, RED, anchor="c")
    y += 6.3

    y = heading(pg, x0, y, "Colourway", acc, wcol)
    xs = x0 + 0.5
    for hx_ in rec["palette"]:
        pg.rect(xs, y - 0.4, 8.2, 8.2, fill=hx_, stroke=HAIR, sw_=0.2, r=1.2)
        pg.text(xs + 4.1, y + 11.4, hx_.upper(), F_R, 4.9, MUTED, anchor="c")
        xs += 12.6
    pg.text(x0 + wcol, y + 6.0, "3MF print palette", F_R, 5.6, SUBTLE, anchor="r")
    y += 19.0

    y = heading(pg, x0, y, "Print profile", acc, wcol)
    rows = [("Infill / layer height", "100 % / 0.20 mm"),
            ("Layers", f"{ov['layers_0p2']}"),
            ("Orientation", "upright, butt end down"),
            ("Supports", "none required"),
            ("Filament, 1.75 mm", f"≈ {ov['filament_1p75_m']:.1f} m (100 % flow)")]
    table(pg, x0, y, [42, 52], rows, row_h=5.3, size=7.4, aligns=["l", "r"], fonts=[F_R, F_B], zebra=False)

    # ---- bottom: intent / features / files
    yb = 210.0
    heading(pg, 12, yb, "Design intent", acc, 88)
    yy = pg.para(12, yb + 3.6, dash(ct["intent"]), 88, F_R, 8.4, INK, leading=11.4)
    yy = pg.para(12, yy + 2.4, dash(ct["print_note"]), 88, F_I, 7.4, MUTED, leading=9.8)
    # verification summary (left, under the intent text)
    fit, prt = rec["fit"], rec["prt"]
    yv0 = yy + 4.2
    yv0 = heading(pg, 12, yv0, "Verified against the reference", acc, 88)
    win = rec["name"].startswith("07")
    rows = [("Bore vs reference", "identical" + ("; 54 windows open the wall" if win else "")),
            ("Outer envelope vs reference", f"{fit['max_over_reference_envelope_mm']:+.3f} mm at most"),
            ("Rim vs reference", f"{fit['rim_added_vs_reference_mm']:+.2f} mm (deliberate, ≥ 0.8 mm wall)"),
            ("Bodies / enclosed voids", f"{prt['bodies']} / none"),
            ("Material under 0.4 mm wide", f"{prt['thin_lt_0.4mm_pct_of_volume']:.3f} % of volume"),
            ("Longest bridge", "none" if prt["max_bridge_span_mm"] < 0.05 else f"{prt['max_bridge_span_mm']:.1f} mm")]
    rh_v = max(4.0, min(4.8, (271.0 - yv0) / len(rows)))
    table(pg, 12, yv0, [46, 42], rows, row_h=rh_v, size=6.9, aligns=["l", "r"], fonts=[F_R, F_B], zebra=False)
    heading(pg, 104, yb, "Key features", acc, wcol)
    yy = yb + 4.6
    for f in ct["features"]:
        pg.rect(104.2, yy + 0.8, 1.7, 1.7, fill=acc)
        yy = pg.para(108, yy, dash(f), 90, F_R, 8.2, INK, leading=10.6) + 1.7
    yy += 3.4
    heading(pg, 104, yy + 1.2, "Files", acc, wcol)
    yy += 5.6
    rows = [(f"stl/{rec['name']}.stl", f"{rec['stl_mb']:.1f} MB · {ov['triangles']:,} triangles"),
            (f"3mf/{rec['name']}.3mf", f"{rec['mf_mb']:.1f} MB · colour")]
    table(pg, 104, yy, [56, 38], rows, row_h=5.2, size=6.9, aligns=["l", "r"], fonts=[F_R, F_R], zebra=False)

    # ---- verification pills
    yv = 274.0
    x = 12
    for txt in ("FITMENT VERIFIED", "SOLID · ONE CLOSED BODY", "PRINT-READY · 0.20 MM LAYERS", "3MF VALIDATED"):
        x += pill(pg, x, yv, txt, GREEN, 5.6, 2.2) + 2.4


# ------------------------------------------------------------------------------------------------
# PAGE 2 - technical drawing (1:1, third-angle projection)
# ------------------------------------------------------------------------------------------------
def third_angle_symbol(pg, x, y, s=1.0):
    """ISO third-angle projection symbol: frustum side view (left) + two concentric circles (right)."""
    w1, w2, hgt = 6.0 * s, 3.4 * s, 5.2 * s
    tri = [(x, y - w1 / 2 * 0 - hgt / 2 + 1.0 * s), (x + 7.2 * s, y - hgt / 2 + 0.2 * s), (x + 7.2 * s, y + hgt / 2 - 0.2 * s), (x, y + hgt / 2 - 1.0 * s)]
    pg.polygon(tri, stroke=INK, sw_=0.25)
    pg.line(x + 3.4 * s, y - hgt / 2 + 0.6 * s, x + 3.4 * s, y + hgt / 2 - 0.6 * s, INK, 0.2)
    cx = x + 13.2 * s
    pg.circle(cx, y, 2.6 * s, stroke=INK, sw_=0.25)
    pg.circle(cx, y, 1.3 * s, stroke=INK, sw_=0.25)
    pg.line(cx - 3.8 * s, y, cx + 3.8 * s, y, INK, 0.13, dash=[1.2, 0.5, 0.2, 0.5])
    pg.line(x - 1.2 * s, y, x + 8.2 * s, y, INK, 0.13, dash=[1.2, 0.5, 0.2, 0.5])


def page_drawing(cx, rec):
    pg, ct, acc = cx.pg, rec["content"], rec["content"]["accent"]
    ov, br, pk, zn, orth = rec["overall"], rec["bore"], rec["peaks"], rec["zones"], rec["ortho"]["views"]
    # sheet frame
    pg.rect(8, 8, 194, 281, stroke=INK, sw_=0.5)
    pg.rect(8, 8, 194, 4.4, fill=PANEL)
    pg.text(10.5, 11.2, f"{rec['docno']}-DWG  ·  {rec['label']}  ·  TECHNICAL DRAWING", F_B, 6.2, INK)
    pg.text(199.5, 11.2, "TRUE SIZE - PRINT AT 100 % (ACTUAL SIZE)", F_B, 6.2, acc, anchor="r")
    pg.line(8, 12.4, 202, 12.4, INK, 0.3)

    Xc, Zbase = 66.0, 208.0                  # front-view centre x, page y of z = 0
    Xs = 140.0                               # side-view centre x
    Ycp = 44.5                               # plan-view centre y
    z_top = ov["z"]
    xmid = (ov["x_min"] + ov["x_max"]) / 2
    ymid = (ov["y_min"] + ov["y_max"]) / 2

    def front_pt(x_mm, z_mm):
        return Xc + (x_mm - xmid), Zbase - z_mm

    def side_pt(y_mm, z_mm):
        return Xs + (y_mm - ymid), Zbase - z_mm

    def plan_pt(x_mm, y_mm):
        return Xc + (x_mm - xmid), Ycp - (y_mm - ymid)

    # ---- images (exact 1:1: 12 px per mm)
    for view, (Xv, ymap) in (("front", (Xc, None)), ("side", (Xs, None)), ("top", (Xc, None))):
        v = orth[view]
        wmm, hmm = v["w"] / v["scale"], v["h"] / v["scale"]
        if view == "front":
            x, y = Xc - wmm / 2, Zbase - (v["cz"]) - hmm / 2
        elif view == "side":
            x, y = Xs - wmm / 2, Zbase - (v["cz"]) - hmm / 2
        else:
            x, y = Xc - wmm / 2, Ycp - hmm / 2
        pg.image(rec["dir"] / f"{view}.png", x, y, wmm, hmm, quality=92)

    # ---- hidden bore lines (dashed) in front and side
    bx0, bx1, by0, by1 = br["x_min"], br["x_max"], br["y_min"], br["y_max"]
    for (xa, xb, mapper) in ((bx0, bx1, front_pt), (by0, by1, side_pt)):
        for xx in (xa, xb):
            p1, p2 = mapper(xx, br["floor_z"]), mapper(xx, z_top)
            pg.line(p1[0], p1[1], p2[0], p2[1], "#2B303B", 0.15, dash=[1.3, 0.9], alpha=0.75)
        p1, p2 = mapper(xa, br["floor_z"]), mapper(xb, br["floor_z"])
        pg.line(p1[0], p1[1], p2[0], p2[1], "#2B303B", 0.15, dash=[1.3, 0.9], alpha=0.75)

    # ---- datum levels between front and side
    rz = rim_start_z()
    levels = [(br["floor_z"], "z 5.0", "bore floor"), (20.0, "z 20.0", "foot top"), (zn["tex_hi"], f"z {zn['tex_hi']:.1f}", "texture ends"),
              (rz, f"z {rz:.1f}", "rim 0.8"), (z_top, f"z {z_top:.2f}", "top")]
    xr = Xc + ov["x"] / 2 + 1.6
    xl = Xs - ov["y"] / 2 - 1.6
    for z, a, b in levels:
        yy = Zbase - z
        pg.line(xr, yy, xl, yy, "#7A8494", 0.16, dash=[3.0, 0.7, 0.4, 0.7])
        pg.text((xr + xl) / 2, yy - 0.9, f"{a}  {b}", F_R, 6.0, MUTED, anchor="c")

    # ---- FRONT: vertical chain + overall height (left) ----
    xe = Xc - ov["x"] / 2 - 0.6
    xch, xov = xe - 9.0, xe - 17.5
    chain = [(0.0, 20.0), (20.0, zn["tex_hi"]), (zn["tex_hi"], z_top)]
    for z0, z1 in chain:
        pg.dim_v(Zbase - z1, Zbase - z0, xch, f"{z1 - z0:.2f}", ext1=xe, ext2=xe, left=True)
    pg.dim_v(Zbase - z_top, Zbase, xov, f"{z_top:.2f}", ext1=xe - 0.0, ext2=xe - 0.0, left=True)
    # ---- FRONT: widths below ----
    yb = Zbase + 6.5
    fx0, fx1 = front_pt(ov["x_min"], 0)[0], front_pt(ov["x_max"], 0)[0]
    pg.dim_h(fx0, fx1, yb, f"{ov['x']:.2f}", ext1=Zbase, ext2=Zbase)
    # band (max outer width in the textured zone)
    bw = pk["max_w"]
    pg.dim_h(Xc - bw / 2, Xc + bw / 2, yb + 7.0, f"{bw:.2f}  (max in textured band)", ext1=None, ext2=None, size=6.2, out_arrows=False)
    pg.text(Xc, Zbase + 24.6, "FRONT VIEW  (from −Y)", F_B, 7, INK, anchor="c")
    # ---- SIDE: depth below ----
    sx0, sx1 = side_pt(ov["y_min"], 0)[0], side_pt(ov["y_max"], 0)[0]
    pg.dim_h(sx0, sx1, yb, f"{ov['y']:.2f}", ext1=Zbase, ext2=Zbase)
    bd = pk["max_d"]
    pg.dim_h(Xs - bd / 2, Xs + bd / 2, yb + 7.0, f"{bd:.2f}  (max in band)", size=6.2, out_arrows=False)
    pg.text(Xs, Zbase + 24.6, "RIGHT VIEW  (from +X)", F_B, 7, INK, anchor="c")
    # cutting planes on the right view (sections on sheet 3)
    xa = Xs - ov["y"] / 2 - 2.5
    xb = Xs + ov["y"] / 2 + 2.5
    for z, letter in ((10.0, "A"), (60.0, "B"), (128.0, "C")):
        yy = Zbase - z
        pg.line(xa, yy, xb, yy, INK, 0.45, dash=[4.0, 0.9, 1.0, 0.9])
        for xe_, s_ in ((xb, 1), (xa, -1)):
            pg.line(xe_, yy, xe_, yy + 4.2, INK, 0.45)
            pg.arrow(xe_, yy + 4.6, 0, 1, INK, L=2.0, Wd=0.75)
            pg.text(xe_ + s_ * 1.9, yy - 0.7, letter, F_B, 8.0, INK, anchor="c")
    pg.text(xb + 6.0, Zbase - 60.0 + 0.6, "A, B, C: see sheet 3", F_I, 5.8, MUTED)

    # ---- PLAN: overall W above, overall D right, bore inside ----
    px0, px1 = plan_pt(ov["x_min"], 0)[0], plan_pt(ov["x_max"], 0)[0]
    ytop_edge = plan_pt(0, ov["y_max"])[1]
    ybot_edge = plan_pt(0, ov["y_min"])[1]
    pg.dim_h(px0, px1, ytop_edge - 5.0, f"{ov['x']:.2f}", ext1=ytop_edge, ext2=ytop_edge)
    pxr = px1 + 5.0
    pg.dim_v(ytop_edge, ybot_edge, pxr, f"{ov['y']:.2f}", ext1=px1, ext2=px1, left=False)
    # bore inside plan
    b0, b1 = plan_pt(br["x_min"], 0)[0], plan_pt(br["x_max"], 0)[0]
    yb_in = plan_pt(0, br["y_min"])[1] - 3.0
    pg.dim_h(b0, b1, yb_in, f"bore {br['x']:.2f}", size=6.2)
    d0, d1 = plan_pt(0, br["y_max"])[1], plan_pt(0, br["y_min"])[1]
    pg.dim_v(d0, d1, plan_pt(br["x_min"], 0)[0] + 4.0, f"bore {br['y']:.2f}", size=6.2, left=False, halo=True)
    pg.text(Xc, ybot_edge + 8.6, "TOP VIEW  (from +Z)", F_B, 7, INK, anchor="c")

    foot20 = min(rec["profile"], key=lambda p: abs(p["z"] - 20.0))
    # ---- key dimensions table (top right)
    x0 = 108.0
    yk = heading(pg, x0, 19.0, "Key dimensions", acc, 90)
    rows = [("Overall height", f"{ov['z']:.2f}"),
            ("Overall width × depth (foot)", f"{ov['x']:.2f} × {ov['y']:.2f}"),
            ("Bore width × depth", f"{br['x']:.2f} × {br['y']:.2f}"),
            ("Bore depth (floor at z 5.0)", f"{br['depth']:.2f}"),
            ("Outer W × D, textured band (max)", f"{pk['max_w']:.2f} × {pk['max_d']:.2f}"),
            ("Foot top (z 20)", f"{foot20['w']:.2f} × {foot20['d']:.2f}"),
            ("Butt face (z 0)", f"{pk['butt_w']:.2f} × {pk['butt_d']:.2f}"),
            ("Peak texture height above bore", f"{pk['peak_offset']:.2f}"),
            ("Base wall / minimum rim wall", f"{zn['base_wall']:.2f} / {zn['rim_wall']:.2f}")]
    table(pg, x0, yk, [58, 32], rows, row_h=5.2, size=7.2, aligns=["l", "r"], fonts=[F_R, F_B], zebra=False)
    pg.para(122.0, yk + 9 * 5.2 + 0.6, "All values in mm. Dashed lines: bore (hidden edges). Renders are the actual STL surface.", 76, F_I, 6.0, MUTED, leading=7.6)

    # ---- scale bar
    sx = 14.0
    ys = 243.0
    pg.line(sx, ys, sx + 50, ys, INK, 0.35)
    for i in range(0, 51, 10):
        pg.line(sx + i, ys - 1.0, sx + i, ys + 1.0, INK, 0.25)
        pg.text(sx + i, ys + 4.2, str(i), F_R, 5.6, MUTED, anchor="c")
    pg.text(sx + 53.5, ys + 1.0, "mm", F_R, 6.0, MUTED)
    pg.text(sx, ys - 3.0, "SCALE 1 : 1", F_B, 6.6, INK)

    # ---- title block
    ty, th = 249.0, 40.0
    pg.line(8, ty, 202, ty, INK, 0.5)
    pg.line(110, ty, 110, ty + th, INK, 0.3)
    pg.rect(8, ty, 102, th, fill=None)
    pg.text(11, ty + 4.4, "PART", F_R, 5.2, MUTED)
    pg.text(11, ty + 12.2, rec["label"], F_B, 16, INK)
    pg.text(11, ty + 17.6, "Pickleball paddle grip sleeve, closed butt, open throat", F_R, 7.2, MUTED)
    pg.line(8, ty + 20, 110, ty + 20, INK, 0.3)
    pg.text(11, ty + 24.0, "GENERAL NOTES", F_R, 5.2, MUTED)
    notes = ["1. Views are true size: print this sheet at 100 %, do not fit to page.",
             "2. Dimensions are measured from the STL, not nominal.",
             "3. Bore, floor and outer envelope match the reference PickleballGrip_1.3mf.",
             f"4. Rim is held at a minimum of {zn['rim_wall']:.1f} mm (reference tapers to 0.36 mm)."]
    for i, t in enumerate(notes):
        pg.text(11, ty + 28.4 + i * 3.1, t, F_R, 6.0, INK)
    # right grid 3 x 4
    cw, chh = 92 / 3, 10.0
    cells = [("SCALE", "1 : 1"), ("UNITS", "millimetres"), ("PROJECTION", None),
             ("MATERIAL", "PLA / PETG / TPU"), ("INFILL", "100 %"), ("LAYER HEIGHT", "0.20 mm"),
             ("MASS (PLA)", f"{ov['weight_g']['PLA']:.1f} g"), ("VOLUME", f"{ov['volume_cm3']:.2f} cm³"), ("SURFACE AREA", f"{ov['surface_area_cm2']:.0f} cm²"),
             ("REVISION", REV), ("DATE", TODAY), ("SHEET", f"2 of {cx.sheet_of}")]
    for i, (lab, val) in enumerate(cells):
        r_, c_ = divmod(i, 3)
        x, y = 110 + c_ * cw, ty + r_ * chh
        pg.line(x, y, x, y + chh, INK, 0.2) if c_ else None
        pg.line(110, y, 202, y, INK, 0.2) if r_ else None
        pg.text(x + 1.8, y + 3.6, lab, F_R, 5.0, MUTED)
        if val is None:
            third_angle_symbol(pg, x + 5.2, y + 6.9, 0.78)
        else:
            pg.text(x + 1.8, y + 8.0, val, F_B, 8.2, INK)


# ------------------------------------------------------------------------------------------------
# PAGE 3 - sections, profiles, dimension data
# ------------------------------------------------------------------------------------------------
def page_title(pg, y, title, sub):
    pg.text(12, y + 5.6, title, F_B, 16, INK)
    pg.text(12, y + 10.6, sub, F_R, 8.0, MUTED)


def section_cell(cx, rec, key, letter, name, x0, y0, wcell):
    pg, acc = cx.pg, rec["content"]["accent"]
    ov, br = rec["overall"], rec["bore"]
    s = rec["sections"][key]
    z = s["z"]
    xmid, ymid = (ov["x_min"] + ov["x_max"]) / 2, (ov["y_min"] + ov["y_max"]) / 2
    ccx, ccy = x0 + wcell / 2 + 1.0, y0 + 32.0          # centre of the drawing

    def P(x, y):
        return ccx + (x - xmid), ccy - (y - ymid)

    pg.rect(x0, y0, wcell - 2.0, 6.0, fill=PANEL, r=1.2)
    pg.text(x0 + 2.2, y0 + 4.1, f"SECTION {letter}–{letter}", F_B, 7.2, INK)
    pg.text(x0 + wcell - 4.2, y0 + 4.1, f"z = {z:.0f} mm  ·  {name}", F_R, 6.6, MUTED, anchor="r")
    rings = []
    for poly in s["poly"]:
        for ring in poly:
            rings.append([P(px, py) for px, py in ring])
    pg.multipath(rings, fill=tint(acc, 0.66), stroke=INK, sw_=0.22)
    if interp_prof(rec, z)["off_min"] is None and len(s["poly"]) > 1:        # ring broken by windows: show the envelope
        from shapely.geometry import MultiPoint
        hull = MultiPoint([pt for ring in rings for pt in ring]).convex_hull
        pg.polyline(list(hull.exterior.coords), MUTED, 0.16, dash=[1.0, 0.7])
    # dimensions: outer W (top) / D (right); bore W (inside, below centre) / D (inside, left)
    top_y = P(0, s["ymax"])[1]
    pg.dim_h(P(s["xmin"], 0)[0], P(s["xmax"], 0)[0], top_y - 4.6, f"{s['w']:.2f}", ext1=top_y, ext2=top_y, size=6.4)
    rx = P(s["xmax"], 0)[0]
    pg.dim_v(P(0, s["ymax"])[1], P(0, s["ymin"])[1], rx + 4.6, f"{s['d']:.2f}", ext1=rx, ext2=rx, size=6.4, left=False)
    b0, b1 = P(br["x_min"], 0)[0], P(br["x_max"], 0)[0]
    pg.dim_h(b0, b1, P(0, br["y_min"])[1] - 3.2, f"bore {br['x']:.2f}", size=5.8)
    d0, d1 = P(0, br["y_max"])[1], P(0, br["y_min"])[1]
    pg.dim_v(d0, d1, b0 + 3.6, f"bore {br['y']:.2f}", size=5.8, left=False)
    # data caption
    prof = interp_prof(rec, z)
    yt = y0 + 32 + 21.5
    if prof["off_min"] is None:
        cap = f"Wall: cut through by windows   ·   peak offset {prof['off_max']:.2f} mm"
    else:
        cap = f"Wall (offset from bore)   min {prof['off_min']:.2f}   max {prof['off_max']:.2f} mm"
    pg.text(x0 + 2.0, yt, cap, F_R, 6.5, INK)
    pg.text(x0 + 2.0, yt + 3.6, f"Area {s['area']:,.0f} mm²   ·   outer perimeter {s['perim']:.1f} mm", F_R, 6.5, MUTED)


def chart_frame(pg, x, y, w, h, xr, yr, xt, yt, xlabel, ylabel, fmt_y="{:.0f}"):
    """Axes box with grid; returns mapping functions (data -> page mm)."""
    pg.rect(x, y, w, h, fill=WHITE, stroke=HAIR, sw_=0.2)
    mx = lambda v: x + (v - xr[0]) / (xr[1] - xr[0]) * w
    my = lambda v: y + h - (v - yr[0]) / (yr[1] - yr[0]) * h
    for v in yt:
        pg.line(x, my(v), x + w, my(v), HAIR, 0.12)
        pg.text(x - 1.2, my(v) + 0.8, fmt_y.format(v), F_R, 5.6, MUTED, anchor="r")
    for v in xt:
        pg.line(mx(v), y, mx(v), y + h, HAIR, 0.1)
        pg.text(mx(v), y + h + 3.0, f"{v:g}", F_R, 5.6, MUTED, anchor="c")
    pg.text(x + w / 2, y + h + 6.3, xlabel, F_R, 5.9, MUTED, anchor="c")
    pg.text(x - 7.2, y + h / 2, ylabel, F_R, 5.9, MUTED, anchor="c", rot=90)
    return mx, my


def page_sections(cx, rec):
    pg, acc = cx.pg, rec["content"]["accent"]
    ov, br, pk, zn = rec["overall"], rec["bore"], rec["peaks"], rec["zones"]
    furniture(cx, rec, "Sections & profiles", 3)
    page_title(pg, 17.0, "Sections & profiles", "True-size cross-sections, how the outer surface and material change with height, and the dimension tables.")

    # ---- three sections
    for i, (key, letter, nm) in enumerate((("10.0", "A", "foot"), ("60.0", "B", "textured band"), ("128.0", "C", "rim"))):
        section_cell(cx, rec, key, letter, nm, 12 + i * 62.5, 34.0, 62.5)

    # ---- charts
    yc = 98.5
    prof = rec["profile"]
    zs = np.array([p["z"] for p in prof])
    off_max = np.array([p["off_max"] for p in prof])
    off_min = [p["off_min"] for p in prof]
    area = np.array([p["area"] for p in prof])
    tz, te = np.array(REF["taper_table"]).T
    fz, fe = np.array(REF["foot_table"]).T
    zref = np.linspace(0, ov["z"], 400)
    eref = np.where(zref <= 20, np.interp(zref, fz, fe), np.where(zref < tz[0], 3.5, np.interp(zref, tz, te)))

    cw, chh = 76.0, 33.0
    for k, (title, xx) in enumerate((("Outer offset from the bore vs height", 21.0), ("Material cross-section area vs height", 115.0))):
        heading(pg, xx - 9.0, yc, title, acc, cw + 14)
    # chart 1
    x1, y1 = 21.0, yc + 5.0
    mx, my = chart_frame(pg, x1, y1, cw, chh, (0, ov["z"]), (0, 6.0), (0, 20, 40, 60, 80, 100, 120), (0, 1, 2, 3, 4, 5, 6),
                         "height z, mm", "offset, mm", "{:g}")
    # zone bands
    for za, zb, lab in ((0, 20, "foot"), (zn["tex_lo"], zn["tex_hi"], "textured band"), (rim_start_z(), ov["z"], "rim")):
        pg.rect(mx(za), y1, mx(zb) - mx(za), chh, fill=tint(acc, 0.93))
        pg.text((mx(za) + mx(zb)) / 2, y1 + 3.0, lab, F_I, 5.4, SUBTLE, anchor="c")
    pg.polyline([(mx(z), my(e)) for z, e in zip(zref, eref)], "#7A8494", 0.22, dash=[1.4, 0.8])
    pg.polyline([(mx(z), my(o)) for z, o in zip(zs, off_max)], acc, 0.5)
    seg = []
    for z, o in list(zip(zs, off_min)) + [(0, None)]:
        if o is None:
            if len(seg) > 1:
                pg.polyline(seg, shade(acc, 0.35), 0.3)
            seg = []
        else:
            seg.append((mx(z), my(o)))
    pg.polyline([(mx(z), my(1.2)) for z in (0, ov["z"])], RED, 0.15, dash=[0.6, 0.6]) if False else None
    ly = y1 + chh + 10.6
    for i, (lab, col, dash) in enumerate((("reference envelope", "#7A8494", True), ("grip: outer peak", acc, False), ("grip: wall, closed rings" if any(o is None for o in off_min) else "grip: wall (min offset)", shade(acc, 0.35), False))):
        lx = x1 + i * 27.0 - 1.5 + (2 if i == 0 else 0)
        pg.line(lx, ly - 0.9, lx + 5.0, ly - 0.9, col, 0.5 if i == 1 else 0.3, dash=[1.4, 0.8] if dash else None)
        pg.text(lx + 6.2, ly, lab, F_R, 5.6, MUTED)
    for z, letter in ((10, "A"), (60, "B"), (128, "C")):
        pg.line(mx(z), y1, mx(z), y1 + chh, INK, 0.16, dash=[0.8, 0.6])
        pg.text(mx(z), y1 - 0.9, letter, F_B, 6.4, INK, anchor="c")
    # chart 2
    x2 = 115.0
    amax = max(1400.0, math.ceil(area.max() / 200.0) * 200.0)
    mx2, my2 = chart_frame(pg, x2, y1, cw, chh, (0, ov["z"]), (0, amax), (0, 20, 40, 60, 80, 100, 120), tuple(range(0, int(amax) + 1, 400 if amax > 1200 else 200)),
                           "height z, mm", "area, mm²", "{:,.0f}")
    for za, zb, lab in ((0, 20, "foot"), (zn["tex_lo"], zn["tex_hi"], "textured band"), (rim_start_z(), ov["z"], "rim")):
        pg.rect(mx2(za), y1, mx2(zb) - mx2(za), chh, fill=tint(acc, 0.93))
        pg.text((mx2(za) + mx2(zb)) / 2, y1 + 3.0, lab, F_I, 5.4, SUBTLE, anchor="c")
    poly = [(mx2(zs[0]), my2(0))] + [(mx2(z), my2(a)) for z, a in zip(zs, area)] + [(mx2(zs[-1]), my2(0))]
    pg.polygon(poly, fill=tint(acc, 0.55), stroke=None)
    pg.polyline([(mx2(z), my2(a)) for z, a in zip(zs, area)], acc, 0.45)
    for z, letter in ((10, "A"), (60, "B"), (128, "C")):
        pg.line(mx2(z), y1, mx2(z), y1 + chh, INK, 0.16, dash=[0.8, 0.6])
        pg.text(mx2(z), y1 - 0.9, letter, F_B, 6.4, INK, anchor="c")
    band = [p["area"] for p in rec["profile"] if zn["tex_lo"] <= p["z"] <= zn["tex_hi"]]
    pg.text(x2 + cw - 13.5, y1 + 9.2, f"textured band: mean {np.mean(band):,.0f} mm²  (min {min(band):,.0f}, max {max(band):,.0f})", F_R, 5.4, MUTED, anchor="r")

    # ---- tables
    yt = 154.0
    heading(pg, 12, yt, "Overall & bore", acc, 88)
    rows = [("Overall length (Z)", f"{ov['z']:.2f} mm"), ("Overall width (X)", f"{ov['x']:.2f} mm"), ("Overall depth (Y)", f"{ov['y']:.2f} mm"),
            ("Bore width × depth", f"{br['x']:.2f} × {br['y']:.2f} mm"), ("Bore area / perimeter", f"{br['area']:.1f} mm² / {br['perimeter']:.1f} mm"),
            ("Bore depth (floor at z 5.0)", f"{br['depth']:.2f} mm"),
            ("Butt face (z 0)", f"{pk['butt_w']:.2f} × {pk['butt_d']:.2f} mm"),
            ("Outer W × D in band (max)", f"{pk['max_w']:.2f} × {pk['max_d']:.2f} mm"),
            ("Circumference in band", f"{pk['perim_min']:.1f} – {pk['perim_max']:.1f} mm"),
            ("Volume / surface area", f"{ov['volume_cm3']:.2f} cm³ / {ov['surface_area_cm2']:.1f} cm²")]
    table(pg, 12, yt + 3.0, [44, 44], rows, row_h=4.9, size=7.0, aligns=["l", "r"], fonts=[F_R, F_B], zebra=False)

    heading(pg, 104, yt, "Zones by height", acc, 94)
    rz = rim_start_z()
    rows = [("Solid floor (butt)", "0.0", f"{br['floor_z']:.1f}", f"{br['floor_z']:.1f}"),
            ("Flared foot", "0.0", "20.0", "20.0"),
            ("Smooth collar", "20.0", f"{zn['tex_lo']:.1f}", f"{zn['tex_lo'] - 20:.1f}"),
            ("Textured band", f"{zn['tex_lo']:.1f}", f"{zn['tex_hi']:.1f}", f"{zn['tex_hi'] - zn['tex_lo']:.1f}"),
            ("Smooth neck (taper)", f"{zn['tex_hi']:.1f}", f"{rz:.1f}", f"{rz - zn['tex_hi']:.1f}"),
            ("Rim (0.8 mm wall)", f"{rz:.1f}", f"{ov['z']:.2f}", f"{ov['z'] - rz:.1f}")]
    yy = table(pg, 104, yt + 3.0, [42, 17, 17, 18], rows, header=["Zone", "z from", "z to", "height"], row_h=4.9, size=7.0,
               aligns=["l", "r", "r", "r"], fonts=[F_R, F_R, F_R, F_B], zebra=False, hsize=5.8)
    wl = pk["min_wall"]
    rows = [("Base wall (design / measured min)", f"{zn['base_wall']:.2f} / " + ("windows" if wl is None else f"{wl:.2f} mm")),
            ("Rim wall (design / measured min)", f"{zn['rim_wall']:.2f} / {rec['fit']['rim_min_wall_mm']:.2f} mm"),
            ("Peak texture height above bore", f"{pk['peak_offset']:.2f} mm")]
    table(pg, 104, yy + 3.0, [64, 30], rows, row_h=4.9, size=7.0, aligns=["l", "r"], fonts=[F_R, F_B], zebra=False)

    # ---- by-height table
    yh = 211.0
    heading(pg, 12, yh, "Outer dimensions by height", acc, 186)
    picks = [5, 10, 20, 30, 45, 60, 75, 90, 105, 116, 125, 132]
    rows = []
    for zt in picks:
        p_ = interp_prof(rec, float(zt))
        rows.append([f"{p_['z']:.1f}", f"{p_['w']:.2f}", f"{p_['d']:.2f}", f"{p_['perim']:.1f}", f"{p_['area']:,.0f}", ("open" if p_["off_min"] is None else f"{p_['off_min']:.2f}"), f"{p_['off_max']:.2f}"])
    table(pg, 12, yh + 3.0, [26, 26, 26, 28, 26, 26, 28], rows,
          header=["z (mm)", "outer W", "outer D", "perimeter", "area mm²", "wall min", "peak offset"], row_h=4.55, size=6.9,
          aligns=["r"] * 7, fonts=[F_B] + [F_R] * 6, zebra=True, hsize=5.6, pad=3.0)


# ------------------------------------------------------------------------------------------------
# PAGE 4 - views and surface
# ------------------------------------------------------------------------------------------------
def page_surface(cx, rec):
    pg, ct, acc = cx.pg, rec["content"], rec["content"]["accent"]
    ov, pk = rec["overall"], rec["peaks"]
    furniture(cx, rec, "Views & surface", 4)
    page_title(pg, 17.0, "Views & surface", "Four-way turntable, close-ups of the surface, and the unrolled height map with the design parameters.")
    # lineup (cropped to the content)
    lcrop = (0.0, 0.035, 1.0, 1.0)
    lw_ = 186.0
    lh_ = lw_ / img_aspect(rec["dir"] / "lineup.png") * (lcrop[3] - lcrop[1]) / (lcrop[2] - lcrop[0])
    pg.image(rec["dir"] / "lineup.png", 12, 33.5, lw_, lh_, quality=88, round_=2.5, crop=lcrop, max_px=2800)
    pg.text(12.5, 33.5 + lh_ + 3.4, "Four views, 90° apart · rendered from the STL, colours are preview only", F_R, 5.8, SUBTLE)
    # close-ups
    y2 = 33.5 + lh_ + 6.0
    dw = 91.0
    dcrop = (0.0, 0.14, 1.0, 0.86)
    dh = dw * 1200 / 1700 * (dcrop[3] - dcrop[1])
    for i, (fn, cap) in enumerate((("detail1.png", "Surface close-up · mid body (z 62 mm)"), ("detail2.png", "Neck, rim and bore · from above (z 119 mm)"))):
        xx = 12 + i * (dw + 4.0)
        pg.image(rec["dir"] / fn, xx, y2, dw, dh, quality=88, round_=2.5, max_px=1700, crop=dcrop)
        pg.rect(xx + 2.2, y2 + 2.2, sw(cap, F_B, 6.2) / MM + 4.0, 5.0, fill=WHITE, r=1.2)
        pg.text(xx + 4.2, y2 + 5.6, cap, F_B, 6.2, INK)
    # relief map
    y3 = y2 + dh + 5.0
    rm_w = 80.0
    rel = rec["relief"]
    rm_h = rm_w * (rel["z1"] - rel["z0"]) / rel["L"]
    heading(pg, 12, y3, "Unrolled surface · height above bore", acc, rm_w + 6)
    ry = y3 + 3.6
    pg.image(rec["dir"] / "relief.png", 12 + 6.5, ry, rm_w - 6.5, rm_h, jpeg=False)
    mw = rm_w - 6.5
    for zt in (20, 40, 60, 80, 100):
        yy = ry + rm_h - (zt - rel["z0"]) / (rel["z1"] - rel["z0"]) * rm_h
        pg.line(12 + 6.5, yy, 12 + 5.4, yy, MUTED, 0.15)
        pg.text(12 + 4.6, yy + 0.8, f"{zt}", F_R, 5.2, MUTED, anchor="r")
    for st in (0, 30, 60, 90, 120):
        xx = 12 + 6.5 + st / rel["L"] * mw
        pg.line(xx, ry + rm_h, xx, ry + rm_h + 1.1, MUTED, 0.15)
        pg.text(xx, ry + rm_h + 3.6, f"{st}", F_R, 5.2, MUTED, anchor="c")
    pg.text(12 + 6.5 + mw / 2, ry + rm_h + 6.9, f"distance around the grip S, mm  (crest perimeter {rel['L']:.1f} mm)", F_R, 5.6, MUTED, anchor="c")
    pg.text(12 + 1.0, ry + rm_h / 2, "z, mm", F_R, 5.6, MUTED, anchor="c", rot=90)
    # colour bar
    cb_y = ry + rm_h + 9.2
    nseg = 60
    for i in range(nseg):
        v = i / (nseg - 1)
        stops = [(0.0, (30, 34, 90)), (0.25, (44, 92, 150)), (0.5, (32, 150, 140)), (0.75, (130, 200, 90)), (1.0, (250, 232, 60))]
        col = [np.interp(v, [s[0] for s in stops], [s[1][k] for s in stops]) for k in range(3)]
        pg.rect(12 + 6.5 + i * mw / nseg, cb_y, mw / nseg + 0.05, 2.6, fill="#%02X%02X%02X" % tuple(int(q) for q in col))
    pg.text(12 + 6.5, cb_y + 5.6, f"{rec['zones']['base_wall']:.1f} mm (base wall)", F_R, 5.4, MUTED)
    pg.text(12 + 6.5 + mw, cb_y + 5.6, "3.5 mm (crest)", F_R, 5.4, MUTED, anchor="r")

    # parameters + verification (right)
    xr = 104.0
    yp = heading(pg, xr, y3, "Design parameters", acc, 94)
    yp = table(pg, xr, yp + 0.4, [40, 54], [[dash(q) for q in p_] for p_ in ct["params"]], row_h=5.0, size=6.9, aligns=["l", "r"], fonts=[F_R, F_B], zebra=False)
    yv = heading(pg, xr, yp + 5.0, "Print & verification", acc, 94)
    fit, prt = rec["fit"], rec["prt"]
    win = rec["name"].startswith("07")
    rows = [("Result: fitment / print-ready", "PASS / PASS"),
            ("Bodies · genus", f"{prt['bodies']} · {prt['genus']}" + ("  (54 windows)" if win else "")),
            ("Bore vs reference", "identical" if not win else "identical (windows open wall)"),
            ("Envelope over reference", f"{fit['max_over_reference_envelope_mm']:+.3f} mm"),
            ("Material under 0.4 mm wide", f"{prt['thin_lt_0.4mm_pct_of_volume']:.3f} %"),
            ("Longest bridge", "none" if prt["max_bridge_span_mm"] < 0.05 else f"{prt['max_bridge_span_mm']:.1f} mm")]
    table(pg, xr, yv + 0.4, [48, 46], rows, row_h=5.0, size=6.9, aligns=["l", "r"], fonts=[F_R, F_B], zebra=False,
          colors=[[None, GREEN]] + [None] * 5)


# ------------------------------------------------------------------------------------------------
# BOOK FRONT / BACK MATTER
# ------------------------------------------------------------------------------------------------
ACCENTS = [CONTENT[n]["accent"] for n in NAMES]
FIRST_SHEET_PAGE = 5
BACK_PAGE = FIRST_SHEET_PAGE + 4 * len(NAMES)
BOOK_TOTAL = BACK_PAGE
DENS = (("PLA", 1.24), ("PETG", 1.27), ("TPU", 1.21), ("ABS", 1.04))


def spaced(pg, x, y, s, font, size, color, tracking=0.6, anchor="l"):
    """Letter-spaced text (canvas has no tracking)."""
    total = sum(sw(ch, font, size) / MM + tracking for ch in s) - tracking
    xx = x - (total if anchor == "r" else total / 2 if anchor == "c" else 0)
    for ch in s:
        pg.text(xx, y, ch, font, size, color)
        xx += sw(ch, font, size) / MM + tracking


def page_cover(cx, recs):
    pg, c = cx.pg, cx.c
    pg.rect(0, 0, PAGE_W, PAGE_H, fill="#12161D")
    for i, a in enumerate(ACCENTS):                      # colour strip along the top edge
        pg.rect(i * PAGE_W / 10, 0, PAGE_W / 10 + 0.1, 3.2, fill=a)
    spaced(pg, 14, 22, "SPECIFICATION BOOK", F_B, 8.2, "#9AA5B4", 1.4)
    spaced(pg, 196, 22, f"REVISION {REV}  ·  {TODAY}", F_R, 7.4, "#9AA5B4", 0.9, anchor="r")
    pg.text(14, 50, "Pickleball", F_B, 46, WHITE)
    pg.text(14, 68, "Paddle Grips", F_B, 46, WHITE)
    pg.text(14, 80, "Ten designs. One fitment.", F_R, 16, "#C5CCD6")
    pg.text(14, 88, "Full specifications, true-size drawings and dimension data for every grip.", F_R, 9.4, "#8F9AAB")
    # hero grid on a warm panel
    py, ph = 100.0, 137.0
    pg.rect(12, py, 186, ph, fill="#E9E6E1", r=3.5)
    cw, hh = 186 / 5, 51.0
    hw = hh * 1400 / 2400
    for i, rec in enumerate(recs):
        r_, c_ = divmod(i, 5)
        x = 12 + c_ * cw + (cw - hw) / 2
        y = py + 4.0 + r_ * (hh + 15.5)
        pg.image(rec["dir"] / "hero.png", x, y, hw, hh, quality=86, max_px=700)
        pg.rect(12 + c_ * cw + cw / 2 - 5.2, y + hh + 1.8, 10.4, 0.9, fill=rec["content"]["accent"], r=0.45)
        pg.text(12 + c_ * cw + cw / 2, y + hh + 6.6, rec["label"], F_B, 6.6, INK, anchor="c")
        pg.text(12 + c_ * cw + cw / 2, y + hh + 10.4, f"{rec['content']['id']}  ·  {rec['overall']['weight_g']['PLA']:.1f} g PLA", F_R, 5.8, MUTED, anchor="c")
    # fact strip
    facts = [("132.82 mm", "overall height"), ("32.06 × 26.04 mm", "bore, identical on all ten"), ("40 – 49 g", "solid, 100 % infill, any material"), ("0.20 mm", "layer height, no supports")]
    fx = 14.0
    for big, small in facts:
        pg.text(fx, 256.0, big, F_B, 13.5, WHITE)
        pg.text(fx, 262.0, small, F_R, 7.0, "#8F9AAB")
        fx += 47.5
    pg.line(14, 270.5, 196, 270.5, "#2A313C", 0.25)
    pg.text(14, 277.2, "Fitted to PickleballGrip_1.3mf  ·  measured from the STL files  ·  colours are preview only", F_R, 7.0, "#8F9AAB")
    pg.text(196, 277.2, "10 specification sheets · 40 pages", F_R, 7.0, "#8F9AAB", anchor="r")


def book_furniture(cx, title):
    pg = cx.pg
    pg.text(12, 12.4, "PICKLEBALL PADDLE GRIPS  ·  SPECIFICATION BOOK", F_B, 6.6, INK)
    pg.text(198, 12.4, title.upper(), F_R, 6.6, MUTED, anchor="r")
    pg.line(12, 14.6, 198, 14.6, HAIR, 0.2)
    pg.rect(12, 14.1, 26, 1.0, fill=INK)
    pg.line(12, 283.5, 198, 283.5, HAIR, 0.2)
    pg.text(12, 287.6, f"Revision {REV}  ·  {TODAY}  ·  dimensions in mm unless noted", F_R, 6.2, SUBTLE)
    pg.text(198, 287.6, f"Page {cx.page_no} of {BOOK_TOTAL}", F_R, 6.2, SUBTLE, anchor="r")


def page_contents(cx, recs):
    pg, c = cx.pg, cx.c
    book_furniture(cx, "Contents")
    page_title(pg, 17.0, "Contents", "Click any entry to jump to the page.")
    y = 40.0

    def entry(y, title, page, sub=None, accent=INK, key=None, chip=None):
        if chip:
            pg.rect(12, y - 4.6, 9.0, 6.6, fill=accent, r=1.2)
            pg.text(16.5, y, chip, F_B, 8.4, WHITE, anchor="c")
        x0 = 24.0 if chip else 12.0
        pg.text(x0, y, title, F_B, 9.6, INK)
        tw = sw(title, F_B, 9.6) / MM
        pg.text(198, y, str(page), F_B, 9.6, INK, anchor="r")
        pg.line(x0 + tw + 2.0, y - 0.6, 195.0, y - 0.6, HAIR, 0.25, dash=[0.3, 1.1], cap=1)
        c.linkRect("", key or f"p{page}", (pg.X(12), pg.Y(y + 2.4), pg.X(198), pg.Y(y - 4.4)), relative=0, thickness=0)
        if sub:
            pg.text(x0, y + 4.4, sub, F_R, 7.2, MUTED)

    pg.text(12, y - 4.5, "FRONT MATTER", F_B, 6.8, SUBTLE)
    y += 3.0
    entry(y, "All ten at a glance", 3, "Weight, size and print-readiness compared", key="p3"); y += 13.0
    entry(y, "The reference fitment", 4, "What is identical on every grip, and the two deliberate deviations", key="p4"); y += 16.0
    pg.text(12, y - 4.5, "SPECIFICATION SHEETS  ·  4 PAGES EACH", F_B, 6.8, SUBTLE)
    y += 3.5
    for i, rec in enumerate(recs):
        p0 = FIRST_SHEET_PAGE + 4 * i
        entry(y, rec["label"].title(), f"{p0}–{p0 + 3}", f"Overview {p0}  ·  Drawing {p0 + 1}  ·  Sections {p0 + 2}  ·  Surface {p0 + 3}",
              accent=rec["content"]["accent"], key=f"p{p0}", chip=rec["content"]["id"])
        y += 13.4
    y += 1.5
    pg.text(12, y - 4.5, "BACK MATTER", F_B, 6.8, SUBTLE)
    y += 3.0
    entry(y, "Notes, method and file manifest", BACK_PAGE, key=f"p{BACK_PAGE}")
    # legend box
    ly = 258.0
    pg.rect(12, ly, 186, 18.0, fill=PANEL, r=2.5)
    pg.text(16, ly + 5.6, "HOW TO READ THESE SHEETS", F_B, 6.4, INK)
    pg.para(16, ly + 7.6, "Every dimension is measured from the STL, not copied from the design intent.  Drawings on the second page of each sheet are true size when "
            "printed at 100 %.  Renders and colours are a preview; the STLs are single-material.  Weight = volume × density at 100 % infill.", 178, F_R, 7.2, MUTED, leading=9.4)


def page_compare(cx, recs):
    pg = cx.pg
    book_furniture(cx, "All ten at a glance")
    page_title(pg, 17.0, "All ten at a glance", "Same bore, same foot, same envelope; ten different surfaces, all under 50 g.")
    x0, y0 = 12.0, 34.0
    cols = [("", 13), ("DESIGN", 33), ("VOLUME", 16), ("PLA g", 15), ("PETG g", 15), ("TPU g", 15), ("ABS g", 15), ("PEAK", 16), ("BAND W×D", 24), ("BRIDGE", 12), ("COLOURS", 12)]
    xs = [x0]
    for _, w in cols:
        xs.append(xs[-1] + w)
    pg.line(x0, y0 + 6.2, xs[-1], y0 + 6.2, INK, 0.3)
    for (h_, w), xa in zip(cols, xs):
        if h_:
            al = "l" if h_ == "DESIGN" else "r"
            pg.text(xa + (1.5 if al == "l" else w - 1.5), y0 + 4.2, h_, F_B, 5.8, MUTED, anchor=al)
    rh = 14.8
    for i, rec in enumerate(recs):
        y = y0 + 6.2 + i * rh
        if i % 2:
            pg.rect(x0, y, xs[-1] - x0, rh, fill=PANEL)
        ov, pk = rec["overall"], rec["peaks"]
        pg.image(rec["dir"] / "hero.png", x0 + 2.4, y + 0.7, 7.9, 13.4, quality=84, max_px=420)
        pg.text(xs[1] + 1.5, y + 6.0, rec["label"], F_B, 8.0, INK)
        pg.text(xs[1] + 1.5, y + 10.8, f"{rec['content']['id']}  ·  {CONTENT[rec['name']]['tagline'][:34].rstrip()}…", F_R, 5.4, SUBTLE) if False else pg.text(xs[1] + 1.5, y + 10.2, f"PG-{rec['content']['id']}", F_R, 6.0, SUBTLE)
        vals = [f"{ov['volume_cm3']:.1f} cm³"] + [f"{ov['weight_g'][m]:.1f}" for m, _ in DENS] + [f"{pk['peak_offset']:.2f}", f"{pk['max_w']:.1f} × {pk['max_d']:.1f}",
                 "none" if rec["prt"]["max_bridge_span_mm"] < 0.05 else f"{rec['prt']['max_bridge_span_mm']:.1f}"]
        for j, v in enumerate(vals):
            wcol = cols[2 + j][1]
            f_ = F_B if j == 1 else F_R
            pg.text(xs[2 + j] + wcol - 1.5, y + 8.6, v, f_, 7.6, INK, anchor="r")
        px = xs[10] + 1.8
        for hx_ in rec["palette"][:5]:
            pg.rect(px, y + 4.6, 2.0, 5.6, fill=hx_, stroke=HAIR, sw_=0.1)
            px += 2.05
        pg.line(x0, y + rh, xs[-1], y + rh, HAIR, 0.15)
    yb = y0 + 6.2 + 10 * rh + 4.0
    pg.text(x0, yb, "Volume and weights: 100 % infill, volume × density (g/cm³: PLA 1.24, PETG 1.27, TPU 1.21, ABS 1.04).  Peak = tallest texture above the bore, mm.  Bridge = longest unsupported run, mm.", F_I, 5.8, MUTED)

    # weight chart
    cy0 = yb + 9.0
    heading(pg, 12, cy0, "Weight against the 50 g limit", INK, 186)
    cx0, cwid, chh = 52.0, 130.0, 58.0
    top = cy0 + 6.0
    gmax = 60.0
    for g in range(0, 61, 10):
        xg = cx0 + g / gmax * cwid
        pg.line(xg, top, xg, top + chh, HAIR, 0.12)
        pg.text(xg, top + chh + 3.4, str(g), F_R, 5.6, MUTED, anchor="c")
    pg.text(cx0 + cwid / 2, top + chh + 7.0, "grams", F_R, 5.8, MUTED, anchor="c")
    rowh = chh / 10
    for i, rec in enumerate(recs):
        yy = top + i * rowh
        pg.text(cx0 - 2.0, yy + rowh * 0.62, rec["label"], F_B, 6.4, INK, anchor="r")
        for k, (mat, _) in enumerate(DENS[:2]):
            wg = rec["overall"]["weight_g"][mat]
            bw = cwid * wg / gmax
            pg.rect(cx0, yy + 0.6 + k * 2.55, bw, 2.35, fill=(bar_col(rec["content"]["accent"]) if k == 0 else tint(bar_col(rec["content"]["accent"]), 0.5)))
            pg.text(cx0 + bw - 1.0, yy + 2.3 + k * 2.55, f"{wg:.1f}", F_B if k == 0 else F_R, 4.8, WHITE if k == 0 else INK, anchor="r")
    xl = cx0 + LIMIT_G / gmax * cwid
    pg.line(xl, top - 1.5, xl, top + chh, RED, 0.3, dash=[1.0, 0.7])
    pg.text(xl, top - 2.6, "50 g limit", F_B, 6.0, RED, anchor="c")
    lgx = 12 + 186 - 41.0
    pg.rect(lgx, cy0 - 2.4, 2.6, 1.6, fill=INK)
    pg.text(lgx + 3.6, cy0 - 1.0, "PLA", F_R, 5.6, MUTED)
    pg.rect(lgx + 13.0, cy0 - 2.4, 2.6, 1.6, fill=tint(INK, 0.55))
    pg.text(lgx + 16.6, cy0 - 1.0, "PETG", F_R, 5.6, MUTED)


def page_reference(cx, recs):
    pg = cx.pg
    book_furniture(cx, "The reference fitment")
    page_title(pg, 17.0, "The reference fitment", "Measured from PickleballGrip_1.3mf.  Everything below is identical on all ten grips except where marked.")
    ring = np.array(REF["cavity_ring"])
    bx0, bx1, by0, by1 = ring[:, 0].min(), ring[:, 0].max(), ring[:, 1].min(), ring[:, 1].max()
    tz, te = np.array(REF["taper_table"]).T
    fz, fe = np.array(REF["foot_table"]).T
    ztop = REF["z_top"]
    zz = np.linspace(0, ztop, 500)
    E = np.where(zz <= 20, np.interp(zz, fz, fe), np.where(zz < tz[0], 3.5, np.interp(zz, tz, te)))
    E08 = np.maximum(E, 0.8)
    # ---- elevation (1:1, left)
    ex, ez0 = 51.0, 190.0
    xm = (bx0 + bx1) / 2
    left = [(ex + (bx0 - xm) - e, ez0 - z) for z, e in zip(zz, E)]
    right = [(ex + (bx1 - xm) + e, ez0 - z) for z, e in zip(zz, E)]
    poly = left + right[::-1]
    pg.polygon(poly, fill="#EEF0F3", stroke=INK, sw_=0.35)
    # bore
    pg.rect(ex + (bx0 - xm), ez0 - ztop, bx1 - bx0, ztop - 5.0, fill=WHITE, stroke=INK, sw_=0.2, dash=[1.3, 0.9])
    # rim deviation (thickened to 0.8) highlighted
    zr = np.array([z for z, e in zip(zz, E) if e < 0.8])
    if len(zr):
        pg.polygon([(ex + (bx0 - xm) - 0.8, ez0 - z) for z in zr] + [(ex + (bx0 - xm) - e, ez0 - z) for z, e in list(zip(zz, E))[::-1] if e < 0.8], fill=tint(RED, 0.4), stroke=None)
        pg.polygon([(ex + (bx1 - xm) + 0.8, ez0 - z) for z in zr] + [(ex + (bx1 - xm) + e, ez0 - z) for z, e in list(zip(zz, E))[::-1] if e < 0.8], fill=tint(RED, 0.4), stroke=None)
    # dims
    xe = ex + (bx0 - xm) - 5.0
    for z0, z1 in ((0, 5.0), (5.0, 20.0), (20.0, tz[0]), (tz[0], ztop)):
        pg.dim_v(ez0 - z1, ez0 - z0, xe - 7.0, f"{z1 - z0:.2f}" if z1 - z0 > 0 else "", ext1=xe + 1.0, ext2=xe + 1.0, size=6.0)
    pg.dim_v(ez0 - ztop, ez0, xe - 15.0, f"{ztop:.2f}", ext1=xe + 1.0, ext2=xe + 1.0, size=6.4)
    pg.dim_h(ex + (bx0 - xm), ex + (bx1 - xm), ez0 + 7.0, f"{bx1 - bx0:.2f}  bore", size=6.4)
    pg.dim_h(ex + (bx0 - xm) - fe.max(), ex + (bx1 - xm) + fe.max(), ez0 + 14.0, f"{bx1 - bx0 + 2 * fe.max():.2f}  foot", size=6.4)
    pg.text(ex, ez0 + 22.0, "FRONT ELEVATION OF THE ENVELOPE (1 : 1)", F_B, 6.4, INK, anchor="c")
    pg.leader(ex + (bx1 - xm) + 0.5, ez0 - ztop + 2.6, ex + (bx1 - xm) + 9.0, ez0 - ztop + 2.6, "rim 0.8 mm min", color=RED, size=5.8)
    pg.leader(ex + (bx1 - xm) - 0.2, ez0 - 5.0, ex + (bx1 - xm) + 9.0, ez0 - 5.0 - 6.0, "bore floor, z 5.0", color=MUTED, size=5.8)

    # ---- plan (right, top): bore + crest envelope + foot
    from shapely.geometry import Polygon as SP
    bore = SP(ring)
    crest, foot = bore.buffer(3.5, 24), bore.buffer(float(fe.max()), 24)
    px, py = 122.0, 60.0
    ym = (by0 + by1) / 2

    def P(x, y):
        return px + (x - xm), py - (y - ym)
    for shp, fillc, st, dsh in ((foot, "#F3F4F6", INK, [1.4, 0.9]), (crest, "#E4E8ED", INK, None), (bore, WHITE, INK, None)):
        pg.multipath([[P(*q) for q in shp.exterior.coords]], fill=fillc, stroke=st, sw_=0.3 if dsh is None else 0.2, dash=dsh)
    pg.dim_h(P(bx0, 0)[0], P(bx1, 0)[0], py + 1.5, f"{bx1 - bx0:.2f}", size=6.2)
    pg.dim_v(P(0, by1)[1], P(0, by0)[1], P(bx0, 0)[0] + 4.5, f"{by1 - by0:.2f}", size=6.2, left=False)
    fx0, fx1 = P(foot.bounds[0], 0)[0], P(foot.bounds[2], 0)[0]
    pg.dim_h(fx0, fx1, P(0, foot.bounds[3])[1] - 4.5, f"{foot.bounds[2] - foot.bounds[0]:.2f}  foot max", ext1=P(0, foot.bounds[3])[1], ext2=P(0, foot.bounds[3])[1], size=6.2)
    cx0_, cx1_ = P(crest.bounds[0], 0)[0], P(crest.bounds[2], 0)[0]
    pg.dim_h(cx0_, cx1_, P(0, foot.bounds[1])[1] + 5.0, f"{crest.bounds[2] - crest.bounds[0]:.2f}  crest envelope", ext1=P(0, crest.bounds[1])[1], ext2=P(0, crest.bounds[1])[1], size=6.2)
    pg.text(px, py + 33.5, "PLAN: BORE, CREST ENVELOPE, FOOT (1 : 1)", F_B, 6.4, INK, anchor="c")

    # ---- what is identical
    yt = 104.0
    heading(pg, 92, yt, "Identical on all ten", INK, 106)
    rows = [("Bore", f"{bx1 - bx0:.2f} × {by1 - by0:.2f} mm, octagonal"), ("Bore polygon", f"{len(ring) - 1} vertices, verbatim"),
            ("Bore depth / floor", f"{ztop - REF['z_floor']:.2f} mm / z {REF['z_floor']:.1f}"), ("Overall height", f"{ztop:.3f} mm"),
            ("Foot flare", "z 0 – 20, max 42.63 × 36.61"), ("Bottom fillet", "about 2 mm, flat closed butt"),
            ("Crest envelope", "3.5 mm from the bore"), ("Outer skin", "never exceeds the reference")]
    yy = table(pg, 92, yt + 3.0, [38, 68], rows, row_h=5.1, size=7.0, aligns=["l", "r"], fonts=[F_R, F_B], zebra=False)
    yy = heading(pg, 92, yy + 5.0, "Deliberate deviations", RED, 106)
    dev = [("Rim wall", "≥ 0.8 mm (reference tapers to 0.36 mm)", "Under one nozzle line, would print as a lone thin line or be dropped."),
           ("Base wall", "1.2 mm (reference 1.5 mm)", "Three 0.4 mm perimeters; saves about 1.4 cm³ (1.7 g)."),
           ("Texture heights", "2.7 – 3.1 mm on six designs", "Lowered plateaus keep every grip at or under 50 g.")]
    for a_, b_, c_ in dev:
        pg.rect(92, yy + 0.4, 1.3, 9.6, fill=RED)
        pg.text(95, yy + 3.4, a_, F_B, 7.4, INK)
        pg.text(95 + 24, yy + 3.4, b_, F_B, 7.0, INK)
        pg.para(95, yy + 4.6, c_, 100, F_R, 6.6, MUTED, leading=8.2)
        yy += 12.2

    # ---- envelope chart (bottom)
    cyy = 232.0
    heading(pg, 12, cyy, "Envelope vs height: reference and grips", INK, 186)
    x1, y1, cw, chh = 22.0, cyy + 5.5, 100.0, 34.0
    mx, my = chart_frame(pg, x1, y1, cw, chh, (0, ztop), (0, 6.0), (0, 20, 40, 60, 80, 100, 120), (0, 1, 2, 3, 4, 5, 6), "height z, mm", "offset from bore, mm", "{:g}")
    pg.polygon([(mx(z), my(e)) for z, e in zip(zz, E08)] + [(mx(z), my(e)) for z, e in list(zip(zz, E))[::-1]], fill=tint(RED, 0.5), stroke=None)
    pg.polyline([(mx(z), my(e)) for z, e in zip(zz, E)], INK, 0.4)
    pg.polyline([(mx(z), my(e)) for z, e in zip(zz, E08)], RED, 0.3, dash=[1.2, 0.7])
    pg.text(x1 + 24.0, y1 + 21.0, "reference envelope (solid line)", F_R, 5.8, INK)
    pg.text(x1 + 24.0, y1 + 25.0, "grips: rim held at 0.8 mm (dashed red)", F_R, 5.8, RED)
    pg.text(x1 + 24.0, y1 + 29.0, "elsewhere the grip surface never exceeds the solid line", F_R, 5.8, MUTED)
    # method box
    heading(pg, 132, cyy, "How it was verified", INK, 66)
    steps = ["Every STL is cross-sectioned at 40+ heights and compared with this profile.",
             "Bore: reference wall points must lie on the grip surface; nothing may enter the bore (0.000 mm²).",
             "Envelope: outer skin measured against the reference, worst case +0.001 mm.",
             "Print check: every 0.20 mm layer sliced; one closed body, no void, no material under 0.4 mm wide."]
    yy = cyy + 4.0
    for s_ in steps:
        pg.rect(132.2, yy + 1.5, 1.4, 1.4, fill=INK)
        yy = pg.para(135.4, yy, s_, 62, F_R, 6.9, INK, leading=8.6) + 1.3


def page_notes(cx, recs):
    pg = cx.pg
    book_furniture(cx, "Notes, method and file manifest")
    page_title(pg, 17.0, "Notes, method and file manifest", "What the numbers mean, what was assumed, and what is in the package.")
    y = 36.0
    y = heading(pg, 12, y, "About these sheets", INK, 88)
    notes = ["All dimensions and volumes are measured directly from the STL files; design-intent values are only used for descriptions.",
             "Weight = volume × density at 100 % infill.  Slicers land within a few percent, so budget ±3 %.",
             "Assumed: 0.4 mm nozzle, 1.75 mm filament, printed upright with the butt on the bed.  Not sliced or printed yet.",
             "Renders and colours are a preview.  The STLs are single-material; the 3MFs carry a small print palette per triangle.",
             "Sheet numbering: PG-01 to PG-10.  Drawings are third-angle, true size at 100 % print scale."]
    for n in notes:
        pg.rect(12.2, y + 1.6, 1.4, 1.4, fill=INK)
        y = pg.para(15.5, y, n, 82, F_R, 7.4, INK, leading=9.4) + 1.6
    y += 3.0
    y = heading(pg, 12, y, "Revision history", INK, 88)
    rows = [("1", "Initial ten designs, STL + colour 3MF"), ("2", "Smooth finish, solid 1.2 mm walls, ≤ 50 g each, specification sheets")]
    table(pg, 12, y, [10, 78], rows, header=["Rev", "Change"], row_h=5.3, size=7.0, aligns=["l", "l"], fonts=[F_B, F_R], zebra=False, hsize=5.8)
    x2 = 104.0
    y = heading(pg, x2, 36.0, "Densities used (g/cm³)", INK, 94)
    y = table(pg, x2, y, [24, 70], [(m, f"{d:.2f}") for m, d in DENS], row_h=5.2, size=7.2, aligns=["l", "r"], fonts=[F_B, F_R], zebra=False)
    y = heading(pg, x2, y + 6.0, "Files", INK, 94)
    rows = [("stl/", "ten single-material STLs"), ("3mf/", "ten colour 3MFs (materials extension)"), ("specs/", "ten sheets + this book"),
            ("renders/", "catalog and fitment overlay"), ("scripts/", "generator, verifiers, PDF builder")]
    table(pg, x2, y, [24, 70], rows, row_h=5.2, size=7.2, aligns=["l", "l"], fonts=[F_B, F_R], zebra=False)
    # manifest
    ym = 128.0
    heading(pg, 12, ym, "File manifest", INK, 186)
    rows = []
    for rec in recs:
        n = rec["name"]
        rows.append([f"PG-{rec['content']['id']}", rec["label"].title(), f"{n}.stl", f"{rec['stl_mb']:.1f} MB", f"{rec['overall']['triangles']:,}", f"{n}.3mf", f"{rec['mf_mb']:.1f} MB"])
    table(pg, 12, ym + 3.0, [14, 32, 42, 18, 24, 42, 14], rows, header=["No.", "Design", "STL", "Size", "Triangles", "3MF", "Size"], row_h=5.6, size=6.8,
          aligns=["l", "l", "l", "r", "r", "l", "r"], fonts=[F_B] + [F_R] * 6, zebra=True, hsize=5.6)
    yb = ym + 3.0 + 5.6 * 11 + 8.0
    pg.rect(12, yb, 186, 24.0, fill=PANEL, r=2.5)
    pg.text(16, yb + 5.6, "LIMITS OF THIS DOCUMENT", F_B, 6.4, INK)
    pg.para(16, yb + 7.6, "These sheets describe the geometry and its measured properties.  They are not a print guarantee: material, printer, cooling and slicer settings all "
            "affect the result.  Do a preview slice before committing filament.  The reference sleeve remains the authority for fit on your paddle.", 178, F_R, 7.2, MUTED, leading=9.4)


# ------------------------------------------------------------------------------------------------
# document assembly
# ------------------------------------------------------------------------------------------------
SHEET_PAGES = [("Overview", page_overview), ("Technical drawing", page_drawing), ("Sections & profiles", page_sections), ("Views & surface", page_surface)]


def build_sheet(name, path=None, cx=None):
    """One grip: 4 pages.  Standalone PDF when path is given, else appended to the book canvas in cx."""
    rec = load(name)
    standalone = cx is None
    if standalone:
        c = new_canvas(path, f"{rec['label']} - Specification Sheet ({rec['docno']}, Rev {REV})",
                       subject="Pickleball paddle grip specification sheet", keywords="pickleball, grip, 3D print, STL, 3MF, specification")
        cx = Ctx(c, 1, 4)
    for i, (title, fn) in enumerate(SHEET_PAGES):
        key = f"p{cx.page_no}"
        cx.c.bookmarkPage(key)
        cx.c.addOutlineEntry(f"{rec['label'].title()}: {title}" if standalone else title, key, level=(0 if standalone else 1))
        fn(cx, rec)
        cx.c.showPage()
        cx.page_no += 1
    if standalone:
        cx.c.showOutline()
        cx.c.save()
    return rec


def build_book(path):
    recs = [load(n) for n in NAMES]
    c = new_canvas(path, f"Pickleball Paddle Grips - Specification Book (Rev {REV})", subject="Ten pickleball grip designs, one fitment",
                   keywords="pickleball, grip, 3D print, STL, 3MF, specification")
    cx = Ctx(c, 1, BOOK_TOTAL, book=True)

    def front(title, fn):
        key = f"p{cx.page_no}"
        c.bookmarkPage(key)
        c.addOutlineEntry(title, key, level=0)
        fn(cx, recs)
        c.showPage()
        cx.page_no += 1

    front("Cover", page_cover)
    front("Contents", page_contents)
    front("All ten at a glance", page_compare)
    front("The reference fitment", page_reference)
    for rec in recs:
        key = f"p{cx.page_no}"
        c.bookmarkPage(key)
        c.addOutlineEntry(f"{rec['content']['id']}  {rec['label'].title()}", key, level=0)
        for i, (title, fn) in enumerate(SHEET_PAGES):
            k2 = f"p{cx.page_no}"
            c.bookmarkPage(k2)
            if i:
                c.addOutlineEntry(title, k2, level=1)
            fn(cx, rec)
            c.showPage()
            cx.page_no += 1
    front("Notes, method and file manifest", page_notes)
    assert cx.page_no - 1 == BOOK_TOTAL, (cx.page_no - 1, BOOK_TOTAL)
    c.showOutline()
    c.save()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--no-book", action="store_true")
    ap.add_argument("--no-sheets", action="store_true")
    a = ap.parse_args()
    OUTDIR.mkdir(exist_ok=True)
    if not a.no_sheets:
        for n in NAMES:
            if a.only and not any(n.startswith(o) for o in a.only):
                continue
            build_sheet(n, OUTDIR / f"{n}_spec.pdf")
            print("built", n, flush=True)
    if not a.no_book and not a.only:
        build_book(OUTDIR / "PickleballGrips_SpecBook.pdf")
        print("built book", flush=True)
