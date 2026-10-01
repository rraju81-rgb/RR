"""Side-view kinematics of the fold-down 'stand-up' rack.
Panel (a window frame) is hinged at the bottom. Cards sit on its INNER side, between
the panel and the wall. Each card is carried so that it keeps its absolute orientation
(upright) while the panel swings down 90 degrees; the card bases ride with the panel.
closed: cards overlap in a column (like photo 1).  open: cards stand one behind another (photo 2).
Usage: python3 foldout_kinematics.py [N]  -> foldout_poses.png, foldout_open.gif
"""
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Polygon
from PIL import Image
import io

N        = int(sys.argv[1]) if len(sys.argv) > 1 else 6
pitch    = 45.0       # visible strip per card (measured from photo 1: ~45 mm at 105 mm card width)
card_h   = 165.0
card_t   = 1.2
blister  = 14.0       # blister depth in front of the card
step     = 4.6        # depth step between cards
c0       = 3.0        # nearest card sits this far behind the panel
v0       = 12.0       # height of the lowest card base on the panel
panel_t  = 4.0
L        = v0 + (N - 1) * pitch + card_h + 10    # panel length
wall_d   = c0 + (N - 1) * step + blister + 8     # wall distance behind the panel

H0 = [-c0 - (N - 1 - j) * step for j in range(N)]    # j = N-1 (top card) is nearest the panel/viewer
V0 = [v0 + j * pitch for j in range(N)]

def pose(phi_deg):
    f = np.radians(phi_deg)
    out = []
    for h, v in zip(H0, V0):
        out.append((h * np.cos(f) + v * np.sin(f), -h * np.sin(f) + v * np.cos(f)))   # card base in world
    return out

def check():
    worst_gap, worst_wall, worst_panel = 1e9, 1e9, 1e9
    for phi in range(0, 91):
        P = pose(phi); f = np.radians(phi)
        for a in range(N):
            for b in range(a + 1, N):
                worst_gap = min(worst_gap, abs(P[a][0] - P[b][0]) - card_t)
            worst_wall = min(worst_wall, P[a][0] + wall_d)                 # card body vs wall plane
            # card (vertical) vs panel plane: distance of base to the panel plane on the inner side
            worst_panel = min(worst_panel, -H0[a])                         # constant, always > 0
    return worst_gap, worst_wall, worst_panel

def draw(ax, phi):
    f = np.radians(phi)
    ax.add_patch(Rectangle((-wall_d - 3, -5), 3, L + 30, color="#bbbbbb"))           # wall
    # panel as rotated rectangle
    corners = [(0, 0), (panel_t, 0), (panel_t, L), (0, L)]
    pts = [(x * np.cos(f) + y * np.sin(f), -x * np.sin(f) + y * np.cos(f)) for x, y in corners]
    ax.add_patch(Polygon(pts, closed=True, color="#40444c"))
    cols = ["#d9381e", "#2670d9", "#f09a1a", "#33a65a", "#9a40b3", "#e6d933", "#1aa6b3", "#d94c80"]
    for j, (bx, by) in enumerate(pose(phi)):
        ax.add_patch(Rectangle((bx, by), card_t, card_h, color=cols[j % len(cols)], alpha=0.9))
        ax.add_patch(Rectangle((bx + card_t, by + 4), blister, 36, color="#9fc3e6"))     # blister window
        ax.plot(bx + card_t / 2, by, "ko", ms=3)                                          # base pivot
    ax.plot(0, 0, "k^", ms=8)
    ax.set_xlim(-wall_d - 10, L + 20); ax.set_ylim(-10, L + 40)
    ax.set_aspect("equal"); ax.axis("off")
    ax.set_title(f"panel {phi}° open", fontsize=10)

if __name__ == "__main__":
    gap, wall, panel = check()
    print(f"N={N}: min gap between neighbouring cards over 0-90 deg: {gap:.2f} mm | "
          f"min card-to-wall distance: {wall:.1f} mm | cards always {panel:.1f} mm inside the panel")
    fig, axes = plt.subplots(1, 4, figsize=(18, 5.2))
    for ax, phi in zip(axes, (0, 30, 60, 90)):
        draw(ax, phi)
    fig.suptitle(f"Fold-down stand-up rack, {N} cards (side view). Wall on the left, viewer on the right. Cards stay upright.", fontsize=12)
    fig.savefig("foldout_poses.png", dpi=100, bbox_inches="tight", facecolor="white")
    frames = []
    for phi in list(range(0, 91, 5)) + [90] * 6 + list(range(90, -1, -5)):
        fig, ax = plt.subplots(figsize=(7, 4.6))
        draw(ax, phi)
        buf = io.BytesIO(); fig.savefig(buf, format="png", dpi=80, facecolor="white", bbox_inches="tight"); plt.close(fig)
        frames.append(Image.open(buf).convert("P"))
    w = max(f.width for f in frames); h = max(f.height for f in frames)
    fixed = []
    for f in frames:
        c = Image.new("P", (w, h), 255); c.putpalette(f.getpalette()); c.paste(f, (0, 0)); fixed.append(c)
    fixed[0].save("foldout_open.gif", save_all=True, append_images=fixed[1:], duration=90, loop=0)
