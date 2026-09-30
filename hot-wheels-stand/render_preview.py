"""Renders preview.png of the rack using the same parameters as side_slide_rack.scad."""
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

card_w, card_h, card_t, blister_h = 105, 165, 1.2, 42
N, pitch, step = 8, 55, 4.6
back_t, spine_w, ledge_h, gutter_d, slop = 3, 14, 10, 6, 0.3
rear_wall, front_wall, thumb_out = 2.4, 2.4, 8
gw = card_t + 2 * slop
ledge_w = spine_w + card_w - thumb_out
H = (N - 1) * pitch + ledge_h - gutter_d + card_h + 5
zc = lambda j: 1 + j * step

polys, cols = [], []

def box(x0, x1, y0, y1, z0, z1, color):
    # plot coords: X=x, Y=-z (so the camera sits on the front side), Z=y (up)
    v = lambda x, y, z: (x, -z, y)
    c = [v(x0,y0,z0), v(x1,y0,z0), v(x1,y1,z0), v(x0,y1,z0),
         v(x0,y0,z1), v(x1,y0,z1), v(x1,y1,z1), v(x0,y1,z1)]
    faces = [(0,1,2,3),(4,5,6,7),(0,1,5,4),(2,3,7,6),(1,2,6,5),(0,3,7,4)]
    shade = [0.75, 1.0, 0.7, 0.95, 0.85, 0.8]
    for f, s in zip(faces, shade):
        polys.append([c[i] for i in f])
        cols.append(tuple(np.clip(np.array(color) * s, 0, 1)))

rack, wall = (0.13, 0.13, 0.15), (0.2, 0.2, 0.22)
box(0, spine_w, 0, H, -back_t, 0, wall)
cards = [(0.85,0.2,0.15),(0.15,0.45,0.85),(0.95,0.6,0.1),(0.2,0.65,0.35),
         (0.6,0.25,0.7),(0.9,0.85,0.2),(0.1,0.65,0.7),(0.85,0.3,0.5)]
for j in range(N):
    y0 = j * pitch
    z0 = zc(j) - slop - rear_wall
    z1 = zc(j) + card_t + slop + front_wall
    zg0, zg1 = zc(j) - slop, zc(j) + card_t + slop
    box(0, spine_w, y0, y0 + ledge_h, 0, z1, rack)                         # spine block
    box(spine_w, ledge_w, y0, y0 + ledge_h - gutter_d, z0, z1, rack)       # ledge floor
    box(spine_w, ledge_w, y0, y0 + ledge_h, z0, zg0, rack)                 # rear wall
    box(spine_w, ledge_w, y0, y0 + ledge_h, zg1, z1, rack)                 # front wall
    # card + blister
    cy = y0 + ledge_h - gutter_d
    col = cards[j]
    box(spine_w, spine_w + card_w, cy, cy + card_h, zc(j), zc(j) + card_t, col)
    box(spine_w + 12, spine_w + card_w - 12, cy + 4, cy + blister_h,
        zc(j) + card_t, zc(j) + card_t + 14, (0.75, 0.85, 0.95))

def render(fname, size, elev, azim, xl, yl, zl, aspect, title):
    fig = plt.figure(figsize=size, dpi=110)
    ax = fig.add_axes([-0.05, -0.02, 1.1, 0.98], projection="3d")
    ax.add_collection3d(Poly3DCollection(polys, facecolors=cols,
                        edgecolors=(0, 0, 0, 0.3), linewidths=0.3))
    ax.set_xlim(*xl); ax.set_ylim(-yl[1], -yl[0]); ax.set_zlim(*zl)
    ax.set_box_aspect(aspect)
    ax.view_init(elev=elev, azim=azim)
    ax.set_axis_off()
    fig.suptitle(title, fontsize=11, y=0.985)
    fig.savefig(fname, facecolor="white", bbox_inches="tight", pad_inches=0.15)

render("preview.png", (5, 13), 6, -62, (-10, 130), (-10, 60), (0, H),
       (140, 70, H), "Side-Slide Shingle Rack: 8 cards, top card frontmost\nEach card slides out to the right")
render("preview_closeup.png", (9, 9), 18, -50, (-10, 130), (-10, 60), (0, 190),
       (140, 70, 190), "Close-up: ledges, gutters and shingled cards (bottom 3)")
