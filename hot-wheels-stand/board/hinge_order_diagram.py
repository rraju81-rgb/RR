"""Side-view diagram: why the clip depths can't go 0..6..0, and how the second strip works (0..6 | gap | 0..6)."""
import os, sys; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import build_board as B
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
def rects(y, d):
    h = B.hz_j(d); yb = y + B.gb
    return {"ledge": (h - B.rext, y + B.ly0, B.rext + B.fext, B.gb + B.rear_h - B.ly0), "card": (h - B.gw / 2, yb, B.card_t, B.card_h),
            "blister": (h - B.gw / 2 + B.card_t, yb + B.blister_y0, 20, B.blister_h), "clip": (B.zb0, y + B.clip_y0, B.zf_j(d) - B.zb0, B.clip_y1 - B.clip_y0)}
def overlap(a, b): return a[0] < b[0] + b[2] and b[0] < a[0] + a[2] and a[1] < b[1] + b[3] and b[1] < a[1] + a[3]
def panel(ax, depths, ys, strips, title):
    R = [rects(y, d) for y, d in zip(ys, depths)]
    for s0 in strips: ax.add_patch(Rectangle((-B.strip_t, s0), B.strip_t + B.lip_d, B.strip_h, fc="#c9ccd3", ec="#555", lw=0.5))
    bad = set()
    for i, r in enumerate(R):
        for m, r2 in enumerate(R):
            if m == i: continue
            for k in ("card", "blister"):
                for k2 in ("ledge", "card", "blister", "clip"):
                    if overlap(r[k], r2[k2]): bad.add((i, k)); bad.add((m, k2))
    for i, (r, d) in enumerate(zip(R, depths)):
        for k, col in (("clip", "#2f3340"), ("ledge", "#f07a12"), ("card", "#2a63d4"), ("blister", "#9fc3ff")):
            ax.add_patch(Rectangle(r[k][:2], r[k][2], r[k][3], fc="#e3262d" if (i, k) in bad else col, ec="k", lw=0.3, alpha=0.95 if k != "blister" else 0.6))
        ax.text(-12, ys[i] + 10, str(d), fontsize=7, ha="right", va="center", fontweight="bold")
    ax.set_xlim(-25, 110); ax.set_ylim(-10, max(ys) + 200); ax.set_aspect("equal"); ax.set_title(title, fontsize=9)
    ax.set_xlabel("distance from wall (mm)"); ax.text(-24, max(ys) + 190, "clip depth j", fontsize=7)
fig, axs = plt.subplots(1, 2, figsize=(11, 12), dpi=110)
P = B.pitch
panel(axs[0], [0, 1, 2, 3, 4, 5, 6, 5, 4, 3, 2, 1, 0], [B.clip_y(0) + P * i for i in range(13)], [0, B.strip_h],
      "ASKED: 0-1-2-3-4-5-6-5-4-3-2-1-0\nred = collision: blisters hit the card below,\nand the cars above 6 are hidden behind it")
ys = [B.clip_y(j) for j in range(7)] + [B.upper_offset + B.clip_y(j) for j in range(7)]
panel(axs[1], list(range(7)) * 2, ys, [0, B.upper_offset],
      f"BUILT: 0..6 on each strip, upper strip {B.upper_offset:.0f} mm higher\n(no collisions, every car visible; {B.upper_offset - B.strip_h:.0f} mm bare wall between strips)")
fig.tight_layout(); fig.savefig(os.path.join(os.path.dirname(os.path.abspath(__file__)), "hinge_order_explained.png"))
