"""2-sheet A3 blueprint of the current PITLANE racks (SWING lift-off rack, SLIDE fixed rack, right + left twins),
drawn from the real CAD geometry (build_liftoff.py, build_fixed.py).
python3 blueprint/build_blueprint.py -> blueprint/blueprint.pdf (+ blueprint_sheet1.png, blueprint_sheet2.png)"""
import os, sys, datetime
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT); sys.path.insert(0, HERE); os.chdir(ROOT)
import numpy as np, trimesh
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import Rectangle, FancyArrowPatch, Circle
import build_liftoff as B, build_fixed as F
from build_liftoff import box, union, inter, mirror, LEFT_DY
from draw import *

NAME = "PITLANE"
PW, PH = 420.0, 297.0
w, ls = B.build(); fx = F.rack()
BLUE = (0.25, 0.55, 0.95)
def mv(m, d): m = m.copy(); m.apply_translation(d); return m
def rot(m, j, deg):
    m = m.copy(); m.apply_transform(trimesh.transformations.rotation_matrix(np.radians(-deg), [0, 1, 0], [B.ax_x, 0, B.zc(j)])); return m
def card(y0, zf, slide=0.0):
    return union([box(23 + slide, 128 + slide, y0 + 3.02, y0 + 168, zf + 0.05, zf + 1.25), box(35 + slide, 116 + slide, y0 + 11, y0 + 53, zf + 1.25, zf + 19.25)])
def scard(j, ang=0, dy=0): return mv(rot(card(B.yb(j), B.front_ref(j) + B.DZ), j, ang), [0, dy, 0])
def fcard(j, slide=0): return card(F.pitch * j, F.front_ref(j), slide)
L = lambda m: mirror(m, LEFT_DY)

# ------------------------------------------------------------------ page furniture
def page():
    fig = plt.figure(figsize=(PW / 25.4, PH / 25.4)); fig.patch.set_facecolor(BG)
    bg = fig.add_axes([0, 0, 1, 1]); bg.set_xlim(0, PW); bg.set_ylim(PH, 0); bg.axis("off"); bg.set_facecolor(BG)
    for x in np.arange(0, PW, 10): bg.plot([x, x], [0, PH], color="#164a90", lw=0.25, zorder=0)
    for y in np.arange(0, PH, 10): bg.plot([0, PW], [y, y], color="#164a90", lw=0.25, zorder=0)
    bg.add_patch(Rectangle((7, 7), PW - 14, PH - 14, fill=False, ec=INK, lw=1.2)); bg.add_patch(Rectangle((9, 9), PW - 18, PH - 18, fill=False, ec=INK, lw=0.4))
    return fig, bg
def axmm(fig, x, y, w_, h):
    ax = fig.add_axes([x / PW, 1 - (y + h) / PH, w_ / PW, h / PH]); ax.set_facecolor("none"); ax.axis("off"); return ax
def frame(ax, pr, scale=None, center=None):
    ax.set_aspect("equal")
    if scale is None:
        e = pr.extent(); ax.set_xlim(e[0], e[1]); ax.set_ylim(e[2], e[3]); return
    pos = ax.get_position(); wmm, hmm = pos.width * PW, pos.height * PH
    e = pr.extent(); c = center if center is not None else ((e[0] + e[1]) / 2, (e[2] + e[3]) / 2)
    ax.set_xlim(c[0] - wmm * scale / 2, c[0] + wmm * scale / 2); ax.set_ylim(c[1] - hmm * scale / 2, c[1] + hmm * scale / 2)
def window(ax, x0, x1, y0, y1):
    """fit a model window into the axes keeping 1:1 aspect"""
    ax.set_aspect("equal"); pos = ax.get_position(); r = (pos.height * PH) / (pos.width * PW)
    cx, cy, wd, ht = (x0 + x1) / 2, (y0 + y1) / 2, x1 - x0, y1 - y0
    if ht / wd > r: wd = ht / r
    else: ht = wd * r
    ax.set_xlim(cx - wd / 2, cx + wd / 2); ax.set_ylim(cy - ht / 2, cy + ht / 2)
def label(bg, x, y, title, sub=None, fs=8.5):
    bg.text(x, y, title, color=INK, fontsize=fs, fontweight="bold", ha="left", va="bottom", family="DejaVu Sans")
    if sub: bg.text(x, y + 3.4, sub, color=HID, fontsize=6.2, ha="left", va="bottom")
def header(bg, title, sheet):
    bg.text(14, 21, NAME, color=INK, fontsize=22, fontweight="bold", ha="left", va="bottom")
    bg.text(84, 21, title, color=INK, fontsize=12, ha="left", va="bottom")
    bg.text(PW - 14, 21, f"SHEET {sheet} / 2", color=INK, fontsize=10, ha="right", va="bottom")
    bg.plot([12, PW - 12], [24, 24], color=INK, lw=0.6)
def titleblock(bg, x, y, w_, h, sheet, scale_note):
    bg.add_patch(Rectangle((x, y), w_, h, fill=False, ec=INK, lw=0.8))
    rows = [("PRODUCT", f"{NAME} SWING & SLIDE wall racks, carded 1:64 die-cast"), ("DRAWING", "General arrangement & operation" if sheet == 1 else "Part details"),
            ("SOURCE", "build_liftoff.py, build_fixed.py  |  units: mm"), ("SCALE", scale_note), ("MATERIAL", "PLA+ / PETG, 0.2 mm layers, no supports"),
            ("DATE", datetime.date.today().isoformat()), ("SHEET", f"{sheet} of 2")]
    rh = h / len(rows)
    for i, (k, v) in enumerate(rows):
        yy = y + i * rh
        if i: bg.plot([x, x + w_], [yy, yy], color=INK, lw=0.3)
        bg.text(x + 2, yy + rh / 2, k, color=HID, fontsize=5.6, va="center"); bg.text(x + 22, yy + rh / 2, v, color=INK, fontsize=6.2, va="center")
    bg.plot([x + 20, x + 20], [y, y + h], color=INK, lw=0.3)
def arrow3(ax, pr, a, b, col=DIM, lw=1.2):
    A, Bp = pr.p2(a)[0], pr.p2(b)[0]
    ax.add_patch(FancyArrowPatch(A, Bp, arrowstyle="-|>", mutation_scale=9, color=col, lw=lw, zorder=8))
def table(bg, x0, y0, rows, cw, rh=5.6):
    for i, r in enumerate(rows):
        yy = y0 + i * rh; xx = x0
        for c_, t in zip(cw, r):
            bg.add_patch(Rectangle((xx, yy), c_, rh, fill=(i == 0), fc="#174d93", ec=INK, lw=0.4))
            bg.text(xx + 1.5, yy + rh / 2, t, color=INK, fontsize=5.6 if i else 5.9, va="center", fontweight="bold" if i == 0 else "normal"); xx += c_

# =============================================================== SHEET 1
def sheet1():
    fig, bg = page(); header(bg, "GENERAL ARRANGEMENT  ·  SWING & SLIDE  ·  RIGHT + LEFT TWIN  ·  OPERATION", 1)
    sw_r = [w] + ls; sw_l = [L(m) for m in sw_r]
    # --- front elevation of the SWING twin, 1:4
    ax = axmm(fig, 14, 34, 98, 160); pr = Proj(sw_r + sw_l, FRONT, res=1.6); draw(ax, pr, fill=True, alpha=0.35, lw=0.45); frame(ax, pr, 4.0)
    label(bg, 14, 31, "FRONT ELEVATION  ·  SWING TWIN", "scale 1:4  ·  cards omitted  ·  left rack 27.5 lower")
    dim(ax, (B.W + 4, 0), (B.W + 4, B.H), -10, "350")
    dim(ax, (B.SPX, B.H + 3), (14, B.H + 3), 6, "20", fs=5.5)
    dim(ax, (B.SPX, -3), (B.W, -3), -8, "136")
    dim(ax, (B.W + 2, B.yb(4)), (B.W + 2, B.yb(5)), 5, "55", fs=5.5)
    dim(ax, (2 * B.SPX - B.W - 3, B.yb(5)), (2 * B.SPX - B.W - 3, B.yb(5) + LEFT_DY), -5, "27.5", fs=5.2)
    for x_, y_ in B.holes: leader(ax, (x_, y_), (x_ + 40, y_ + 10), "Ø3 screw", fs=5.2)
    # --- side elevation right SWING 1:4
    ax = axmm(fig, 114, 34, 30, 160); prs = Proj(sw_r, SIDE, res=2.0); draw(ax, prs, fill=True, alpha=0.35, lw=0.45); frame(ax, prs, 4.0)
    label(bg, 114, 31, "SIDE", "1:4, from the left")
    dim(ax, (0, -3), (B.zc(5) + 5.1 + 0.1, -3), -6, f"{w.bounds[1][2]:.1f}", fs=5.2)
    leader(ax, (B.front_ref(5) + B.DZ, B.yb(5) + 10), (B.front_ref(5) - 25, B.yb(5) + 45), "rows step\n4.6 mm", fs=5.2)
    # --- iso SWING twin with cards
    asm = sw_r + [scard(j, 0) for j in range(B.n)] + sw_l + [L(scard(j, 0)) for j in range(B.n)]
    ax = axmm(fig, 146, 34, 132, 160); pri = Proj(asm, iso_M(16, 28), res=1.6)
    tint = {k: BLUE for k in list(range(7, 13)) + list(range(20, 26))}
    draw(ax, pri, fill=True, alpha=0.75, lw=0.35, tint=tint); frame(ax, pri)
    label(bg, 146, 31, "SWING TWIN  ·  12 CARDED CARS", "isometric · NTS · every card name stays visible")
    # --- iso SLIDE twin
    asm = [fx] + [fcard(j, 70 if j == 3 else 0) for j in range(F.n)] + [L(fx)] + [L(fcard(j, 70 if j == 2 else 0)) for j in range(F.n)]
    ax = axmm(fig, 282, 34, 124, 96); pri = Proj(asm, iso_M(16, 28), res=1.4)
    draw(ax, pri, fill=True, alpha=0.75, lw=0.35, tint={k: BLUE for k in list(range(1, 7)) + list(range(8, 14))}); frame(ax, pri)
    label(bg, 282, 31, "SLIDE TWIN  ·  FIXED RACKS", "isometric · NTS · cards slide in from the open ends")
    # --- parts list
    rows = [("ITEM", "PART", "QTY", "PRINT"),
            ("1", "SWING wall mount 350 x 20, 6 pins Ø5 (R or L)", "1", "on back edge"),
            ("2", "SWING ledge, socket ring Ø10.2 / hole Ø5.5", "6", "standing"),
            ("3", "SLIDE rack 350 x 136, one piece (R or L)", "1", "on back edge"),
            ("-", "Screw Ø3-3.5 + wall plug", "3", "-")]
    table(bg, 282, 140, rows, [11, 75, 11, 27])
    bg.text(282, 172, "TWIN: right rack + mirrored left rack, spines back to back,", color=HID, fontsize=6)
    bg.text(282, 176, "left rack 27.5 mm lower so the ledges alternate.", color=HID, fontsize=6)
    bg.text(282, 180, "SLIDE: card slides into the 1.8 mm slot from the open end,", color=HID, fontsize=6)
    bg.text(282, 184, "the solid block next to the spine is the end stop.", color=HID, fontsize=6)
    # --- operation sequence (SWING)
    label(bg, 14, 203, "OPERATION SEQUENCE  ·  SWING", "how the hinge works (the SLIDE rack only needs step 1, then cards slide in)")
    y = B.yb(2); sub = inter([w, box(-10, 30, y - 22, y + 60, -5, 60)])
    steps = [("1  SCREW THE WALL MOUNT", "3 screws, pins point up", [sub], None),
             ("2  DROP THE LEDGE ON ITS PIN", "the ring sits on the knuckle", [sub, mv(ls[2], [0, 24, 0])], [((70, y + 40, 20), (70, y + 26, 20))]),
             ("3  SWING OUT, SLIDE THE CARD IN", "0° stop at closed, opens to 135°", [sub, rot(ls[2], 2, 60), scard(2, 60)], [((40, y + 120, 70), (40, y + 85, 70))]),
             ("4  TO REMOVE: LIFT 15.5, PULL OUT", "pin and ring are 15 mm long", [sub, mv(ls[2], [0, B.lift + 1, 12])], [((70, y + 3, 14), (70, y + 16, 14))])]
    for i, (t, sbt, ms, arrows) in enumerate(steps):
        x = 14 + i * 67; ax = axmm(fig, x, 212, 64, 70)
        pr_ = Proj(ms, iso_M(20, 35), res=3.0); draw(ax, pr_, fill=True, alpha=0.6, lw=0.45, tint={2: BLUE} if i == 2 else None); frame(ax, pr_)
        for a, b in (arrows or []): arrow3(ax, pr_, a, b)
        bg.add_patch(Rectangle((x, 207), 64, 79, fill=False, ec=INK, lw=0.4)); bg.text(x + 2, 210.5, t, color=INK, fontsize=6.0, fontweight="bold", va="center")
        bg.text(x + 2, 283.5, sbt, color=HID, fontsize=5.6, va="center")
    titleblock(bg, 286, 232, 120, 54, 1, "as noted (1:4 orthographic, iso NTS)")
    return fig

# =============================================================== SHEET 2
def sheet2():
    fig, bg = page(); header(bg, "PART DETAILS  ·  1 SWING WALL MOUNT  ·  2 SWING LEDGE  ·  3 SLIDE RACK", 2)
    j = 2; y = B.yb(j); zc = B.zc(j); M_side = np.array([[0, 0, 1], [0, 1, 0]]); M_top = np.array([[1, 0, 0], [0, 0, -1]])
    # ---------- PART 1 wall mount
    label(bg, 14, 31, "1  SWING WALL MOUNT (right)", "front & side 1:5 · details 2:1")
    ax = axmm(fig, 14, 37, 34, 150); pr = Proj([w], FRONT, res=2.0); draw(ax, pr, alpha=0.35, lw=0.45); frame(ax, pr, 5.0)
    dim(ax, (B.SPX, 0), (B.SPX, B.H), 8, "350", fs=5.5); dim(ax, (B.SPX, -2), (14, -2), -6, "20", fs=5.2)
    dim(ax, (20, B.yb(0)), (20, B.yb(1)), -5, "55", fs=5)
    ax = axmm(fig, 50, 37, 20, 150); prs = Proj([w], SIDE, res=2.0); draw(ax, prs, alpha=0.35, lw=0.45); frame(ax, prs, 5.0)
    dim(ax, (0, -2), (w.bounds[1][2], -2), -6, f"{w.bounds[1][2]:.1f}", fs=5)
    # detail A: section through the pin axis (closed ledge), 2:1
    ax = axmm(fig, 74, 37, 56, 74)
    section(ax, inter([w, box(-10, 30, y - 20, y + 25, -5, 60)]), (B.ax_x, 0, 0), (1, 0, 0), M_side, hatch="....")
    section(ax, ls[j], (B.ax_x, 0, 0), (1, 0, 0), M_side, hatch="\\\\\\\\")
    window(ax, zc - 13, zc + 13, y - 18, y + 22)
    dim(ax, (zc - 2.5, y + 15.6), (zc + 2.5, y + 15.6), 1.5, "Ø5 pin", fs=4.8)
    dim(ax, (zc + 5.6, y - 15), (zc + 5.6, y), -1.5, "15", fs=4.8); dim(ax, (zc + 5.6, y), (zc + 5.6, y + 15), -1.5, "15", fs=4.8)
    dim(ax, (zc - 5, y - 16), (zc + 5, y - 16), -1.5, "Ø10", fs=4.8)
    leader(ax, (zc + 3.2, y + 0.6), (zc + 8, y + 19), "1 x 45° root chamfer", fs=4.8)
    leader(ax, (zc + 4.0, y + 9), (zc + 8, y + 6), "ledge ring\nØ10.2 / Ø5.5", fs=4.8)
    bg.text(74, 114, "DETAIL A  section on the pin axis (2:1)", color=INK, fontsize=6.3, fontweight="bold")
    bg.text(74, 118, "knuckle + pin from LiftOffHinge.stl; ledge ring sits on the knuckle", color=HID, fontsize=5.4)
    # detail B: top section through the hinge (closed), 2:1
    ax = axmm(fig, 74, 124, 56, 60)
    section(ax, ls[j], (0, y + 7, 0), (0, 1, 0), M_top, hatch="\\\\\\\\")
    section(ax, w, (0, y + 7, 0), (0, 1, 0), M_top, hatch="....")
    window(ax, -8, 26, -(zc + 9), -(B.rear_ref(j) + B.DZ - 12))
    leader(ax, (B.ax_x, -zc), (16, -(zc + 7.5)), "pin in ring", fs=4.8)
    leader(ax, (12, -(B.rear_ref(j) + B.DZ - 1)), (17, -(B.rear_ref(j) + B.DZ - 9)), "stand-off = 0° stop", fs=4.8)
    bg.text(74, 187, "DETAIL B  plan section through the hinge (2:1)", color=INK, fontsize=6.3, fontweight="bold")
    # ---------- PART 2 ledge
    l = ls[j]; l0 = mv(l, [0, -y, -(B.rear_ref(j) + B.DZ)])
    label(bg, 136, 31, "2  SWING LEDGE (row 3 shown)", "top & front 1:1 · section D-D 4:1 · iso NTS")
    ax = axmm(fig, 136, 37, 146, 24); pr = Proj([l0], TOP, res=5.0); draw(ax, pr, hidden=True, alpha=0.35, lw=0.45); frame(ax, pr, 1.0)
    dim(ax, (l0.bounds[0][0], -l0.bounds[1][2] - 1), (B.W, -l0.bounds[1][2] - 1), -3, f"{B.W - l0.bounds[0][0]:.1f}", fs=5.2)
    ax.plot([60, 60], [-12, 2], color=DIM, lw=0.5, ls="-."); ax.text(60, 2.6, "D", color=DIM, fontsize=6, ha="center")
    ax = axmm(fig, 136, 64, 146, 30); prf = Proj([l0], FRONT, res=5.0); draw(ax, prf, hidden=True, alpha=0.35, lw=0.45); frame(ax, prf, 1.0)
    dim(ax, (B.W + 1, 0), (B.W + 1, 22), -3, "22", fs=5.2)
    dim(ax, (30.5, 11), (121, 11), 4, "posts 90.5 apart, 6 x 45° chamfers", fs=5)
    # section D-D
    ax = axmm(fig, 136, 100, 52, 76)
    section(ax, l0, (60, 0, 0), (1, 0, 0), M_side)
    zf = B.front_ref(j) - B.rear_ref(j); window(ax, -2, zf + 8, -2, 24)
    ax.add_patch(Rectangle((zf + 0.05, 3.02), 1.2, 18, fc="none", ec=HID, lw=0.6, ls="--")); ax.text(zf + 0.6, 22.5, "card", color=HID, fontsize=5, ha="center")
    dim(ax, (zf, 4.5), (zf + 1.8, 4.5), 0, "1.8", fs=4.6)
    dim(ax, (-0.6, 0), (-0.6, 22), 1.2, "22", fs=4.8); dim(ax, (zf + 5.6, 0), (zf + 5.6, 3), -1, "3", fs=4.6)
    bg.text(136, 180, "SECTION D-D (4:1)", color=INK, fontsize=6.3, fontweight="bold")
    bg.text(136, 184, "card slot 1.8 (1.3 at the corner posts)", color=HID, fontsize=5.4)
    ax = axmm(fig, 192, 100, 90, 76); pri = Proj([l0], iso_M(28, 30), res=4.0); draw(ax, pri, alpha=0.6, lw=0.45); frame(ax, pri)
    p = pri.p2((B.ax_x, 7, zc - B.rear_ref(j) - B.DZ))[0]; leader(ax, p, p + np.array([10, 18]), "socket ring", fs=5.2)
    p = pri.p2((27, 9, zf + 3))[0]; leader(ax, p, p + np.array([14, 22]), "chamfered corner post", fs=5.2)
    # ---------- PART 3 SLIDE rack
    label(bg, 288, 31, "3  SLIDE RACK (right)", "front & side 1:5 · iso NTS")
    ax = axmm(fig, 288, 37, 34, 150); pr = Proj([fx], FRONT, res=2.0); draw(ax, pr, alpha=0.35, lw=0.45); frame(ax, pr, 5.0)
    dim(ax, (F.SPX, 0), (F.SPX, F.H), 8, "350", fs=5.5); dim(ax, (F.SPX, -2), (F.W, -2), -6, "136", fs=5.2)
    ax = axmm(fig, 324, 37, 18, 150); prs = Proj([fx], SIDE, res=2.0); draw(ax, prs, alpha=0.35, lw=0.45); frame(ax, prs, 5.0)
    dim(ax, (0, -2), (fx.bounds[1][2], -2), -6, f"{fx.bounds[1][2]:.0f}", fs=5)
    yy = F.pitch * 2; ax = axmm(fig, 344, 37, 64, 70); pri = Proj([inter([fx, box(-10, 140, yy - 3, yy + 26, -1, 60)]), fcard(2, 55)], iso_M(28, 32), res=3.0)
    draw(ax, pri, alpha=0.6, lw=0.45, tint={1: BLUE}); frame(ax, pri)
    p = pri.p2((5, yy + 20, 10))[0]; leader(ax, p, p + np.array([-2, 20]), "solid end stop", fs=5.2)
    arrow3(ax, pri, (175, yy + 40, F.front_ref(2) + 20), (150, yy + 40, F.front_ref(2) + 20))
    bg.text(344, 110, "card slides in from the open end", color=HID, fontsize=5.4)
    # ---------- hinge function (plan sections at 0 / 90 / 135 deg)
    label(bg, 14, 196, "HINGE FUNCTION", "plan section through the hinge, 1:1  ·  closed (stop) / open 90° / open 135°")
    for i, ang in enumerate((0, 90, 135)):
        ax = axmm(fig, 14 + i * 66, 202, 64, 84)
        section(ax, rot(ls[j], j, ang), (0, y + 7, 0), (0, 1, 0), M_top, hatch="\\\\\\\\")
        section(ax, inter([w, box(-10, 40, y - 1, y + 23, -5, 60)]), (0, y + 7, 0), (0, 1, 0), M_top, hatch="....")
        window(ax, -12, 60, -(zc + 70), -(B.rear_ref(j) + B.DZ - 14))
        ax.text(-10, -(zc + 66), f"{ang}°", color=DIM, fontsize=8, fontweight="bold")
    bg.text(214, 200, "NOTES", color=INK, fontsize=8, fontweight="bold")
    notes = ["1. Card ~105 x 165 x 1.2 mm, blister up to 42 mm. Slot 1.8 mm.",
             "2. SWING: ring Ø5.5 on pin Ø5 (0.25 radial clearance), stops ~3° past",
             "    closed on the stand-off, opens to 135°. Lift 15.5 mm to remove.",
             "3. Twin: left rack mirrored, hung 27.5 mm lower, spines touching.",
             "    One side opened at a time never touches the other; both together",
             "    are clear to 75° (leave 20 mm between spines for 90°).",
             "4. SLIDE: one piece, card slides in 105 mm from the open end.",
             "5. No supports: wall mount / SLIDE rack on the flat back edge,",
             "    ledges standing on their bottom face (ring vertical).",
             "6. Fit verified on the CAD model by boolean collision checks.",
             "    Print tolerances may need tuning on your printer."]
    for i, t in enumerate(notes): bg.text(214, 206 + i * 3.7, t, color=INK, fontsize=5.6)
    titleblock(bg, 286, 246, 120, 40, 2, "as noted on each view")
    return fig

if __name__ == "__main__":
    out = os.path.join(HERE, "blueprint.pdf")
    with PdfPages(out) as pdf:
        for k, f in enumerate((sheet1, sheet2), 1):
            fig = f(); pdf.savefig(fig, facecolor=BG); fig.savefig(os.path.join(HERE, f"blueprint_sheet{k}.png"), dpi=170, facecolor=BG); plt.close(fig); print("sheet", k)
