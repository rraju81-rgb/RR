"""Close-up of the built-in snap latch: section through the catch (latched) + 3D view of the clip bottom."""
import os, sys; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np, build_board as B
from build_board import box, inter, place
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
src = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "render_clip.py")).read(); exec(src[src.index("def raster("):src.index("def panel(")])
strip = B.build_strip(); clip = B.build_clip(1); y = B.clip_y(1)
fig, axs = plt.subplots(1, 3, figsize=(15, 5.5), dpi=110)
for ax, (B.catch_z, title) in zip(axs[:2], ((4.0, "LATCHED (section through the catch)\ncatch sits 0.3 mm under the lower lip: clip can't lift"),
                                           (B.zb0 + 0.05, "INSTALL / REMOVE: pull the side tab\nthe arm flexes 2.3 mm toward you, the clip lifts free"))):
    c = place(B.build_clip(1), 0, y)
    for m, col in ((strip, "#c9ccd3"), (c, "#3a3f4b")):
        s = m.section(plane_origin=(-7, 0, 0), plane_normal=(1, 0, 0))
        for poly in s.discrete: ax.add_patch(Polygon(np.asarray(poly)[:, [2, 1]], closed=True, fc=col, ec="k", lw=0.5))
    ax.set_xlim(-8, 24); ax.set_ylim(y + B.clip_y0 - 4, y + B.clip_y1 + 3); ax.set_aspect("equal"); ax.set_title(title, fontsize=9); ax.set_xlabel("z: distance from wall (mm)")
B.catch_z = 4.0
axs[0].annotate("catch", xy=(5.0, y + B.catch_top - 1.2), xytext=(13, y + B.catch_top - 6), arrowprops=dict(arrowstyle="->"), fontsize=8)
axs[0].annotate("lower (bearing) lip", xy=(3, y + B.bear_y + 2), xytext=(9, y + B.bear_y + 9), arrowprops=dict(arrowstyle="->"), fontsize=8)
axs[0].annotate("finger behind hook lip", xy=(1.7, y + B.b_loc + 6), xytext=(9, y + B.b_loc + 8), arrowprops=dict(arrowstyle="->"), fontsize=8)
cl = B.build_clip(1)
axs[2].imshow(raster([cl], [(0.3, 0.32, 0.38)], -25, 200, (520, 520), [[-26, B.clip_y0 - 2, -4], [20, 12, 30]])); axs[2].axis("off")
axs[2].set_title("clip from below/behind: spring arm, catch,\nand the pull tab on the left", fontsize=9)
fig.tight_layout(); fig.savefig(os.path.join(os.path.dirname(os.path.abspath(__file__)), "latch_detail.png"))
