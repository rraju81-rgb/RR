"""2-sheet A3 blueprint of the hinged card rack, drawn from the real CAD geometry (build_board.py).
python3 blueprint/build_blueprint.py -> blueprint/blueprint.pdf (+ blueprint_sheet1.png, blueprint_sheet2.png)"""
import os, sys, datetime
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT); sys.path.insert(0, HERE); os.chdir(ROOT)
import numpy as np, trimesh
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import Rectangle, FancyArrowPatch, Circle
import build_board as B
from build_board import box, union, place
from draw import *

NAME = "SWINGRACK"
PW, PH = 420.0, 297.0
strip = B.build_strip(); ledge = B.build_ledge(); clips = [B.build_clip(j) for j in range(4)]
N = 4
def card(j, ang=0.0, lift=0.0, dy=0.0):
    zc = -B.gw / 2
    c = union([box(B.end_stop + 0.1, B.end_stop + 0.1 + B.card_w, 0.01, B.card_h, zc, zc + B.card_t),
               box(B.end_stop + B.blister_dx, B.end_stop + B.card_w - B.blister_dx, B.blister_y0, B.blister_y0 + B.blister_h, zc + B.card_t, zc + B.card_t + 18)])
    c.apply_transform(trimesh.transformations.rotation_matrix(np.radians(-ang), [0, 1, 0])); c.apply_translation([B.pin_x, B.clip_y(j) + B.gb + lift + dy, B.hz_j(j)]); return c
def mv(m, d): m = m.copy(); m.apply_translation(d); return m

def page():
    fig = plt.figure(figsize=(PW / 25.4, PH / 25.4)); fig.patch.set_facecolor(BG)
    bg = fig.add_axes([0, 0, 1, 1]); bg.set_xlim(0, PW); bg.set_ylim(PH, 0); bg.axis("off"); bg.set_facecolor(BG)
    # grid + border
    for x in np.arange(0, PW, 10): bg.plot([x, x], [0, PH], color="#164a90", lw=0.25, zorder=0)
    for y in np.arange(0, PH, 10): bg.plot([0, PW], [y, y], color="#164a90", lw=0.25, zorder=0)
    bg.add_patch(Rectangle((7, 7), PW - 14, PH - 14, fill=False, ec=INK, lw=1.2)); bg.add_patch(Rectangle((9, 9), PW - 18, PH - 18, fill=False, ec=INK, lw=0.4))
    return fig, bg
def axmm(fig, x, y, w, h):
    ax = fig.add_axes([x / PW, 1 - (y + h) / PH, w / PW, h / PH]); ax.set_facecolor("none"); ax.axis("off"); return ax
def frame(ax, pr, scale=None, center=None, w=None, h=None):
    ax.set_aspect("equal")
    if scale is None:
        e = pr.extent(); ax.set_xlim(e[0], e[1]); ax.set_ylim(e[2], e[3]); return
    pos = ax.get_position(); wmm, hmm = pos.width * PW, pos.height * PH
    e = pr.extent(); c = center if center is not None else ((e[0] + e[1]) / 2, (e[2] + e[3]) / 2)
    ax.set_xlim(c[0] - wmm * scale / 2, c[0] + wmm * scale / 2); ax.set_ylim(c[1] - hmm * scale / 2, c[1] + hmm * scale / 2)
def label(bg, x, y, title, sub=None, fs=8.5):
    bg.text(x, y, title, color=INK, fontsize=fs, fontweight="bold", ha="left", va="bottom", family="DejaVu Sans")
    if sub: bg.text(x, y + 3.4, sub, color=HID, fontsize=6.2, ha="left", va="bottom")
def header(bg, title, sheet):
    bg.text(14, 21, f"{NAME}", color=INK, fontsize=22, fontweight="bold", ha="left", va="bottom")
    bg.text(84, 21, title, color=INK, fontsize=12, ha="left", va="bottom")
    bg.text(PW - 14, 21, f"SHEET {sheet} / 2", color=INK, fontsize=10, ha="right", va="bottom")
    bg.plot([12, PW - 12], [24, 24], color=INK, lw=0.6)
def titleblock(bg, x, y, w, h, sheet, scale_note):
    bg.add_patch(Rectangle((x, y), w, h, fill=False, ec=INK, lw=0.8))
    rows = [("PRODUCT", f"{NAME} hinged wall rack for carded 1:64 die-cast"), ("DRAWING", "General arrangement & operation" if sheet == 1 else "Part details"),
            ("SOURCE", "build_board.py (v3)  |  units: mm"), ("SCALE", scale_note), ("MATERIAL", "PLA / PETG, 0.2 mm layers, no supports"),
            ("DATE", datetime.date.today().isoformat()), ("SHEET", f"{sheet} of 2")]
    rh = h / len(rows)
    for i, (k, v) in enumerate(rows):
        yy = y + i * rh
        if i: bg.plot([x, x + w], [yy, yy], color=INK, lw=0.3)
        bg.text(x + 2, yy + rh / 2, k, color=HID, fontsize=5.6, va="center"); bg.text(x + 22, yy + rh / 2, v, color=INK, fontsize=6.2, va="center")
    bg.plot([x + 20, x + 20], [y, y + h], color=INK, lw=0.3)
def balloon(ax, p, q, n):
    ax.annotate("", xy=p, xytext=q, arrowprops=dict(arrowstyle="-|>", color=DIM, lw=0.5, mutation_scale=5), zorder=6)
    ax.add_patch(Circle(q, radius=ax_r(ax), fc=BG, ec=DIM, lw=0.7, zorder=7)); ax.text(q[0], q[1], str(n), color=DIM, fontsize=7, ha="center", va="center", zorder=8, fontweight="bold")
def ax_r(ax):
    x0, x1 = ax.get_xlim(); pos = ax.get_position(); return 3.2 * (x1 - x0) / (pos.width * PW)
def arrow3(ax, pr, a, b, col=DIM, lw=1.2):
    A, Bp = pr.p2(a)[0], pr.p2(b)[0]
    ax.add_patch(FancyArrowPatch(A, Bp, arrowstyle="-|>", mutation_scale=9, color=col, lw=lw, zorder=8))

# =============================================================== SHEET 1
def sheet1():
    fig, bg = page(); header(bg, "GENERAL ARRANGEMENT  ·  4-CAR KIT  ·  OPERATION", 1)
    asm = [strip] + [place(clips[j], 0, B.clip_y(j)) for j in range(N)] + [place(B.ledge_at(j, 0), 0, B.clip_y(j)) for j in range(N)]
    top = B.clip_y(N - 1) + B.gb + B.rear_h
    # --- front elevation 1:2
    ax = axmm(fig, 14, 34, 92, 158); pr = Proj(asm, FRONT, res=3.0); draw(ax, pr, fill=True, alpha=0.35); frame(ax, pr, 2.0)
    label(bg, 14, 31, "FRONT ELEVATION", "scale 1:2  ·  cards omitted")
    xr = B.pin_x + B.ledge_len
    dim(ax, (-15, 0), (-15, 240), 14, "240 strip pitch")
    dim(ax, (B.pin_x - 7, B.clip_y(0)), (B.pin_x - 7, B.clip_y(1)), -9, "60 rack pitch")
    dim(ax, (-15, -1), (15, -1), -6, "30")
    dim(ax, (B.pin_x, B.clip_y(N - 1) + B.ly0 + B.bar_h + 6), (xr, B.clip_y(N - 1) + B.ly0 + B.bar_h + 6), 4, f"{B.ledge_len:.0f} ledge")
    for y_ in B.hole_ys: leader(ax, (0, y_), (32, y_ + 6), "Ø5 csk Ø9")
    # --- side elevation 1:2 (from the left)
    ax = axmm(fig, 108, 34, 46, 158); prs = Proj(asm, SIDE, res=3.0); draw(ax, prs, fill=True, alpha=0.35); frame(ax, prs, 2.0)
    label(bg, 108, 31, "SIDE ELEVATION", "scale 1:2  ·  from the left")
    dim(ax, (-B.strip_t, -2), (B.hz_j(N - 1) + B.fext, -2), -6, f"{B.hz_j(N-1) + B.fext + B.strip_t:.0f}")
    for j in range(N - 1): pass
    dim(ax, (B.hz_j(2), B.clip_y(2) + 30), (B.hz_j(3), B.clip_y(2) + 30), 0, "7", fs=5.5)
    leader(ax, (B.hz_j(3), B.clip_y(3) + B.gb + 8), (B.hz_j(3) - 30, B.clip_y(3) + 48), "each rack 7 mm further\nout (shingled)", fs=5.4)
    # --- iso assembled with cards
    asm_c = asm + [card(j) for j in range(N)]
    ax = axmm(fig, 158, 34, 120, 158); pri = Proj(asm_c, iso_M(18, 38), res=2.2); tint = {k: (0.25, 0.55, 0.95) for k in range(1 + 2 * N, 1 + 3 * N)}
    draw(ax, pri, fill=True, alpha=0.75, lw=0.45, tint=tint); frame(ax, pri)
    label(bg, 158, 31, "ASSEMBLED  ·  4 CARDED CARS", "isometric · not to scale · every card name stays visible")
    # --- exploded
    exp = [mv(inter_strip := B.inter([strip, box(-20, 20, 0, 80, -10, 10)]), [0, 0, 0]), mv(place(clips[0], 0, B.clip_y(0)), [0, 6, 30]), mv(place(B.ledge_at(0, 0), 0, B.clip_y(0)), [0, 32, 70])]
    ax = axmm(fig, 282, 34, 124, 100); pre = Proj(exp, iso_M(22, 35), res=4.0); draw(ax, pre, fill=True, alpha=0.6, lw=0.5); frame(ax, pre)
    label(bg, 282, 31, "EXPLODED VIEW", "isometric · one rack")
    for n_, P in ((1, (14, 70, 0)), (2, (16, 48, 37)), (3, (60, 47, 75))):
        p = pre.p2(P)[0]; balloon(ax, p, p + np.array([14, 6]), n_)
    arrow3(ax, pre, (B.pin_x, B.clip_y(0) + 40, 60), (B.pin_x, B.clip_y(0) + 26, 60))
    arrow3(ax, pre, (0, 52, 30), (0, 44, 8))
    # parts list
    x0, y0 = 282, 140; rows = [("ITEM", "PART", "QTY (4-car)", "PRINT"), ("1", "Wall strip 30 x 6 x 252 (hook lips every 20)", "1", "on long edge"),
                                ("2", "Hinge clip, depth j = 0..3 (one each)", "4", "standing"), ("3", "Ledge 128.6 long, 1.8 mm card slot", "4", "standing"),
                                ("-", "Screw 4-5 mm countersunk + wall plug", "3", "-")]
    cw = [12, 72, 20, 20]
    for i, r in enumerate(rows):
        yy = y0 + i * 6.2; xx = x0
        for c_, t in zip(cw, r):
            bg.add_patch(Rectangle((xx, yy), c_, 6.2, fill=(i == 0), fc="#174d93", ec=INK, lw=0.4))
            bg.text(xx + 1.5, yy + 3.1, t, color=INK, fontsize=5.8 if i else 6, va="center", fontweight="bold" if i == 0 else "normal"); xx += c_
    bg.text(x0, y0 + 36, "Kits: 2, 3, 4 cars on 1 strip (119 / 179 / 239 mm tall), 5-6 cars on 2 strips.", color=HID, fontsize=6)
    bg.text(x0, y0 + 40, "Strips join with the C-hook joint; clips need no tools.", color=HID, fontsize=6)
    # --- operation sequence
    label(bg, 14, 203, "OPERATION SEQUENCE", "how the product works")
    y = B.clip_y(1); sub = B.inter([strip, box(-20, 20, y - 30, y + 50, -10, 10)])
    steps = []
    # 1 mount
    s1 = [sub]; steps.append(("1  SCREW THE STRIP", "3 countersunk screws; hook lips face up", s1, None))
    s2 = [sub, mv(place(clips[1], 0, y), [0, B.lift + 0.5, 22])]; steps.append(("2  HANG THE CLIP", "hold 6 mm high, push in, let go: gravity lock", s2, [((B.pin_x, y + 20, 26), (B.pin_x, y + 20, 8)), ((0, y + 34, 6), (0, y + 27, 6))]))
    s3 = [sub, place(clips[1], 0, y), mv(place(B.ledge_at(1, 0), 0, y), [0, 26, 0])]; steps.append(("3  DROP THE LEDGE ON THE PIN", "it clicks shut on the detent bump", s3, [((B.pin_x - 10, y + 48, B.hz_j(1)), (B.pin_x - 10, y + 32, B.hz_j(1)))]))
    s4 = [sub, place(clips[1], 0, y), place(B.ledge_at(1, 30, 1), 0, y), card(1, 30, 1, 40)]; steps.append(("4  LIFT 1 mm, SWING 10-35°, SLIDE CARD IN", "close it: the stop nub holds it at 0°", s4, [((60, y + 140, 50), (60, y + 105, 50))]))
    for i, (t, sbt, ms, arrows) in enumerate(steps):
        x = 14 + i * 67; ax = axmm(fig, x, 212, 64, 72)
        pr_ = Proj(ms, iso_M(20, 38), res=3.0); draw(ax, pr_, fill=True, alpha=0.6, lw=0.45, tint={3: (0.25, 0.55, 0.95)} if i == 3 else None); frame(ax, pr_)
        for a, b in (arrows or []): arrow3(ax, pr_, a, b)
        bg.add_patch(Rectangle((x, 207), 64, 79, fill=False, ec=INK, lw=0.4)); bg.text(x + 2, 210.5, t, color=INK, fontsize=6.2, fontweight="bold", va="center")
        bg.text(x + 2, 283.5, sbt, color=HID, fontsize=5.6, va="center")
    titleblock(bg, 286, 232, 120, 54, 1, "as noted (1:2 orthographic, iso NTS)")
    return fig

# =============================================================== SHEET 2
def sheet2():
    fig, bg = page(); header(bg, "PART DETAILS  ·  1 WALL STRIP  ·  2 HINGE CLIP  ·  3 LEDGE", 2)
    # ---------- PART 1 strip
    label(bg, 14, 31, "1  WALL STRIP", "front 1:2 · section A-A 1:1 · details 3:1")
    ax = axmm(fig, 14, 36, 34, 140); pr = Proj([strip], FRONT, res=3.0); draw(ax, pr, alpha=0.35); frame(ax, pr, 2.0)
    dim(ax, (-15, 0), (-15, 252), 8, "252"); dim(ax, (-15, 0), (15, 0), -5, "30")
    dim(ax, (16, B.lip_ys[1]), (16, B.lip_ys[2]), -5, "20", fs=5.5)
    ax = axmm(fig, 50, 36, 22, 140); prs = Proj([strip], SIDE, res=3.0); draw(ax, prs, alpha=0.35); frame(ax, prs, 2.0)
    dim(ax, (-6, -1), (6, -1), -5, "12", fs=5.5)
    # lip profile detail 3:1
    ax = axmm(fig, 76, 36, 48, 60); ax.set_aspect("equal")
    section(ax, B.inter([strip, box(-1, 1, 40, 75, -10, 10)]), (0, 0, 0), (1, 0, 0), np.array([[0, 0, 1], [0, 1, 0]]))
    ax.set_xlim(-9, 13); ax.set_ylim(41, 69)
    b = B.lip_ys[1]
    dim(ax, (B.lip_d, b), (B.lip_d, b + B.shelf_h), 2.2, "4", fs=5.5); dim(ax, (B.lip_d, b + B.shelf_h), (B.lip_d, b + B.shelf_h + B.lip_up), 2.2, "5", fs=5.5)
    dim(ax, (0, b - 1.5), (B.groove, b - 1.5), -1.6, "3.5", fs=5.5); dim(ax, (B.groove, b - 1.5), (B.lip_d, b - 1.5), -1.6, "2.5", fs=5.5)
    dim(ax, (-6, b + 15), (0, b + 15), 1.5, "6", fs=5.5)
    bg.text(76, 98, "DETAIL B  hook lip (3:1)", color=INK, fontsize=6.5, fontweight="bold")
    # C-joint detail 3:1
    ax = axmm(fig, 76, 104, 48, 72); ax.set_aspect("equal")
    two = [B.inter([strip, box(-1, 1, 226, 260, -10, 10)]), place(B.inter([strip, box(-1, 1, 0, 26, -10, 10)]), 0, 240)]
    section(ax, two[0], (0, 0, 0), (1, 0, 0), np.array([[0, 0, 1], [0, 1, 0]])); section(ax, two[1], (0, 0, 0), (1, 0, 0), np.array([[0, 0, 1], [0, 1, 0]]), hatch="\\\\\\\\")
    ax.set_xlim(-10, 8); ax.set_ylim(234, 258)
    dim(ax, (-6.5, 240), (-6.5, 252), -1.5, "12 lap", fs=5.5); dim(ax, (-3, 249), (-1.5, 249), 3.5, "1.5", fs=5)
    leader(ax, (-2.4, 250.5), (1.5, 255.5), "hook", fs=5.5); leader(ax, (-3.7, 241.5), (1.5, 237), "hook", fs=5.5)
    bg.text(76, 178, "DETAIL C  C-hook strip joint (3:1)", color=INK, fontsize=6.5, fontweight="bold")
    bg.text(76, 182, "press the upper strip on from the front; hooks lock it vertically", color=HID, fontsize=5.6)
    # ---------- PART 2 clip (j0)
    c0 = clips[0]
    label(bg, 132, 31, "2  HINGE CLIP  (depth j = 0 shown)", "front / side / top 1:1 · iso NTS")
    ax = axmm(fig, 132, 38, 52, 50); pr = Proj([c0], FRONT, res=8.0); draw(ax, pr, hidden=True, alpha=0.35); frame(ax, pr, 1.0)
    dim(ax, (B.x_min, B.clip_y0 - 1), (-B.x_min, B.clip_y0 - 1), -4, f"{-2 * B.x_min:.1f}")
    dim(ax, (-B.x_min + 1, B.clip_y0), (-B.x_min + 1, B.clip_y1), -4, f"{B.clip_y1 - B.clip_y0:.1f}")
    leader(ax, (B.pin_x + 4, 12), (B.pin_x + 12, 26), "pin Ø8", fs=5.5)
    ax = axmm(fig, 186, 38, 48, 50); prs = Proj([c0], SIDE, res=8.0); draw(ax, prs, hidden=True, alpha=0.35); frame(ax, prs, 1.0)
    dim(ax, (B.cheek_z0, B.clip_y0 - 1), (B.hz + B.fext, B.clip_y0 - 1), -4, f"{B.hz + B.fext - B.cheek_z0:.1f}")
    leader(ax, (1.5, B.b_loc + 8), (-6, B.b_loc + 24), "finger drops\nbehind lip", fs=5.2)
    leader(ax, (B.hz + 4, B.ly0 - 1), (B.hz + 2, B.ly0 + 22), "sag pad\n+ stop nub", fs=5.2)
    ax = axmm(fig, 132, 92, 52, 40); prt = Proj([c0], TOP, res=8.0); draw(ax, prt, hidden=True, alpha=0.35); frame(ax, prt, 1.0)
    dim(ax, (B.pin_x, -B.hz), (B.pin_x, 0), -4, f"{B.hz:.1f}", fs=5.5)
    ax = axmm(fig, 186, 92, 48, 40); pri = Proj([c0], iso_M(25, 35), res=6.0); draw(ax, pri, alpha=0.6); frame(ax, pri)
    rows = [("j", "pin from strip", "block depth")] + [(str(j), f"{B.hz_j(j):.1f}", f"{B.zf_j(j) - B.zb0:.1f}") for j in range(6)]
    for i, r in enumerate(rows):
        for k, t in enumerate(r): bg.text(132 + [0, 8, 30][k], 138 + i * 4, t, color=INK if i else DIM, fontsize=5.6, fontweight="bold" if i == 0 else "normal")
    bg.text(186, 138, "Clip j sits 7 mm deeper per rack.", color=HID, fontsize=5.6)
    bg.text(186, 142, "Hang: lift 5.3 mm over the lip.", color=HID, fontsize=5.6)
    bg.text(186, 146, "Cheeks: 0.3 mm each side of strip.", color=HID, fontsize=5.6)
    bg.text(186, 150, "Pin-to-barrel clearance 0.3 mm.", color=HID, fontsize=5.6)
    bg.text(186, 154, "Nothing right of pin + 6.6 mm in", color=HID, fontsize=5.6); bg.text(186, 158, "the card lane (cards start at 15).", color=HID, fontsize=5.6)
    # ---------- PART 3 ledge
    label(bg, 240, 31, "3  LEDGE", "top 1:1 · front 1:1 · section D-D 3:1 · iso NTS")
    ax = axmm(fig, 240, 38, 168, 22); pr = Proj([ledge], TOP, res=6.0); draw(ax, pr, hidden=True, alpha=0.35); frame(ax, pr, 1.0)
    dim(ax, (0, -B.rext - 1), (B.ledge_len, -B.rext - 1), -3, f"{B.ledge_len:.1f}")
    dim(ax, (B.end_stop, B.fext + 0.5), (B.end_stop + B.card_w, B.fext + 0.5), 3, "105 card", fs=5.5)
    ax.plot([60, 60], [-8, 8], color=DIM, lw=0.5, ls="-."); ax.text(60, 8.6, "D", color=DIM, fontsize=6, ha="center")
    ax = axmm(fig, 240, 62, 168, 32); prf = Proj([ledge], FRONT, res=6.0); draw(ax, prf, hidden=True, alpha=0.35); frame(ax, prf, 1.0)
    dim(ax, (B.ledge_len + 1, B.ly0), (B.ledge_len + 1, B.gb + B.rear_h), -3, f"{B.gb + B.rear_h - B.ly0:.0f}", fs=5.5)
    dim(ax, (-B.bar_r, B.ly0 - 1), (B.bar_r, B.ly0 - 1), -3, f"Ø{2 * B.bar_r:.1f}", fs=5.5)
    dim(ax, (0, B.gb + B.rear_h + 1), (B.end_stop, B.gb + B.rear_h + 1), 3, "15", fs=5.5)
    # section D-D 3:1
    ax = axmm(fig, 240, 98, 56, 62); ax.set_aspect("equal")
    section(ax, ledge, (60, 0, 0), (1, 0, 0), np.array([[0, 0, 1], [0, 1, 0]]))
    ax.set_xlim(-7, 7); ax.set_ylim(B.ly0 - 2, B.gb + B.rear_h + 2)
    ax.add_patch(Rectangle((-B.gw / 2 + 0.05, B.gb + 0.02), B.card_t, 14, fc="none", ec=HID, lw=0.6, ls="--")); ax.text(0.2, B.gb + 15, "card", color=HID, fontsize=5, ha="center")
    dim(ax, (-B.gw / 2, B.gb + 2.5), (B.gw / 2, B.gb + 2.5), 0, "1.8", fs=4.6)
    dim(ax, (B.fext + 0.3, B.gb), (B.fext + 0.3, B.gb + B.front_h), -1.2, "1", fs=4.6)
    dim(ax, (-B.rext - 0.3, B.gb), (-B.rext - 0.3, B.gb + B.rear_h), 1.2, "19", fs=5)
    dim(ax, (-B.rext - 0.3, B.ly0), (-B.rext - 0.3, B.gb), 1.2, "3", fs=4.6)
    dim(ax, (-B.rext, B.ly0 - 0.8), (-B.gw / 2, B.ly0 - 0.8), -0.8, "4", fs=4.6)
    bg.text(240, 166, "SECTION D-D (3:1)", color=INK, fontsize=6.5, fontweight="bold")
    bg.text(240, 170, "tall back wall 19, front lip 1, corner pads 4", color=HID, fontsize=5.6)
    ax = axmm(fig, 300, 98, 108, 64); pri = Proj([ledge], iso_M(28, 30), res=5.0); draw(ax, pri, alpha=0.6); frame(ax, pri)
    p = pri.p2((B.end_stop / 2, B.gb + 10, 0))[0]; leader(ax, p, p + np.array([18, 10]), "solid hinge block\n(full height)", fs=5.5)
    p = pri.p2((B.nub_x + 1, B.ly0, -B.rext + 1))[0]; leader(ax, p, p + np.array([22, -10]), "stop notch (underside)", fs=5.5)
    # ---------- hinge function detail (bottom)
    label(bg, 14, 192, "HINGE FUNCTION", "section through the pin axis, 2:1  ·  ledge closed / lifted & opening")
    y = 0.0
    for i, (ang, lf) in enumerate(((0, 0), (30, 1.0))):
        ax = axmm(fig, 14 + i * 104, 198, 100, 86); ax.set_aspect("equal")
        cl = clips[1]; L = B.ledge_at(1, ang, lf); st = B.inter([strip, box(-20, 20, -40, 60, -10, 10)])
        M2 = np.array([[0, 0, 1], [0, 1, 0]])
        section(ax, mv(st, [0, -B.clip_y(1) + B.clip_y(1), 0]), (0, 0, 0), (1, 0, 0), M2, hatch="....")
        section(ax, place(cl, 0, 0), (B.pin_x, 0, 0), (1, 0, 0), M2)
        section(ax, L, (B.pin_x + (6 if ang == 0 else 0.01), 0, 0), (1, 0, 0), M2, hatch="\\\\\\\\")
        ax.set_xlim(-8, 42); ax.set_ylim(-12, 30)
        if i == 0:
            leader(ax, (B.hz_j(1), B.ly0 + B.bar_h - 3), (B.hz_j(1) + 6, 27), "pin Ø8 in 18 mm barrel", fs=5.2)
            leader(ax, (B.hz_j(1) + 1, B.ly0 - 0.5), (B.hz_j(1) + 8, -6), "detent bump / dimple", fs=5.2)
            leader(ax, (1.5, B.b_loc + 7), (6, 27), "finger behind lip", fs=5.2)
            leader(ax, (B.zf_j(1) - 1, -4), (B.zf_j(1) - 4, -10), "solid block face", fs=5.2)
        else:
            ax.annotate("", xy=(B.hz_j(1) + 2, B.ly0 + 4), xytext=(B.hz_j(1) + 2, B.ly0 + 1), arrowprops=dict(arrowstyle="-|>", color=DIM, lw=0.8))
            ax.text(B.hz_j(1) + 3, B.ly0 + 3, "lift 1 mm\nthen swing", color=DIM, fontsize=5.4)
    bg.text(222, 200, "NOTES", color=INK, fontsize=8, fontweight="bold")
    notes = ["1. Card: ~105 x 165 mm, 1.2 mm thick, blister up to 42 mm. Slot 1.8 mm.",
             "2. Clip hangs by gravity: finger behind a full-width hook lip; cheeks stop twisting.",
             "3. Ledge rests on the sag pad; nub + notch stop it at 0°, bump holds it closed.",
             "4. To load: open the ledges above, lift 1 mm, swing 10-35°, slide card down.",
             "5. Every part prints without supports (strip on edge, clip & ledge standing).",
             "6. Fit verified on the CAD model by boolean collision checks (hang, lift-off,",
             "    swing, stop, card loading, strip joint). Print tolerances may need tuning."]
    for i, t in enumerate(notes): bg.text(222, 206 + i * 4.3, t, color=INK, fontsize=5.8)
    titleblock(bg, 286, 238, 120, 48, 2, "as noted on each view")
    return fig

if __name__ == "__main__":
    out = os.path.join(HERE, "blueprint.pdf")
    with PdfPages(out) as pdf:
        for k, f in enumerate((sheet1, sheet2), 1):
            fig = f(); pdf.savefig(fig, facecolor=BG); fig.savefig(os.path.join(HERE, f"blueprint_sheet{k}.png"), dpi=170, facecolor=BG); plt.close(fig); print("sheet", k)
