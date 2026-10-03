"""Product renders for the marketing material (cards drawn as simple coloured blanks)."""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from build_board import *
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
src = open("render_clip.py").read(); exec(src[src.index("def raster("):src.index("def panel(")])
OUT = "marketing/img"
strip = build_strip(); clips = [build_clip(j) for j in range(6)]
GREY, DARK, ORANGE = (0.82, 0.83, 0.86), (0.22, 0.23, 0.27), (0.98, 0.45, 0.08)
CARD_COLS = [(0.12, 0.35, 0.85), (0.85, 0.12, 0.15), (0.1, 0.65, 0.35), (0.55, 0.2, 0.75)]
def card(j, ang=0.0, lift=0.0, slide=0.0):
    y = clip_y(j) + gb + lift; zc = -gw / 2
    c = union([box(end_stop + 0.1 + slide, end_stop + 0.1 + slide + card_w, 0.01, card_h, zc, zc + card_t),
               box(end_stop + blister_dx + slide, end_stop + card_w - blister_dx + slide, blister_y0, blister_y0 + blister_h, zc + card_t, zc + card_t + 14)])
    c.apply_transform(trimesh.transformations.rotation_matrix(np.radians(-ang), [0, 1, 0])); c.apply_translation([pin_x, y, hz_j(j)]); return c
def save(img, name, crop=True):
    if crop:
        m = (img < 0.99).any(axis=2); ys, xs = np.where(m); img = img[max(ys.min() - 20, 0):ys.max() + 20, max(xs.min() - 20, 0):xs.max() + 20]
    plt.imsave(f"{OUT}/{name}.png", np.clip(img, 0, 1))
def scene(N, angs, cards=True, slide=None):
    m, c = [strip], [GREY]
    for j in range(N):
        a = angs[j]; lf = 1.0 if a else 0.0
        m += [place(clips[j], 0, clip_y(j)), place(ledge_at(j, a, lf), 0, clip_y(j))]; c += [DARK, ORANGE]
        if cards: m.append(card(j, a, lf, (slide or [0] * N)[j])); c.append(CARD_COLS[j % 4])
    return m, c
# hero: 4 cars closed
m, c = scene(4, [0, 0, 0, 0]); save(raster(m, c, 15, 30, (1100, 1500), [[-40, 0, -5], [140, 420, 80]]), "hero_closed")
# one door open
m, c = scene(4, [0, 0, 30, 90]); save(raster(m, c, 20, 40, (1100, 1500), [[-40, 0, -5], [160, 420, 140]]), "one_open")
# all open (fan)
m, c = scene(4, [20, 45, 70, 90], cards=False); save(raster(m, c, 25, 45, (1100, 1500), [[-40, 0, -5], [160, 420, 160]]), "all_open")
# no cards, closed (structure)
m, c = scene(4, [0, 0, 0, 0], cards=False); save(raster(m, c, 20, 35, (900, 1300), [[-40, 0, -5], [140, 260, 60]]), "frame_only")
# hang the clip: 3 steps (close-up)
y = clip_y(1); sub = inter([strip, box(-20, 20, y - 30, y + 45, -10, 20)])
for i, (dy, dz) in enumerate([(lift + 0.5, 25), (lift + 0.5, 0), (0, 0)]):
    cm = trimesh.Trimesh(clips[1].vertices + [0, y + dy, dz], clips[1].faces)
    save(raster([sub, cm], [GREY, DARK], 0, -70, (700, 700), [[-30, y - 30, -10], [40, y + 45, 60]]), f"hang_step{i+1}")
# close-up hinge with ledge
m = [sub, place(clips[1], 0, y), place(ledge_at(1, 35, 1.0), 0, y)]
save(raster(m, [GREY, DARK, ORANGE], 30, 35, (1000, 1000), [[-40, y - 35, -10], [120, y + 60, 110]]), "hinge_closeup")
# parts flat
parts = [strip, place(clips[0], 45, 60), place(ledge_at(0, 0), 60, 20)]
lp = build_ledge(); lp.apply_translation([40, 95, 20])
save(raster([inter([strip, box(-20, 20, 0, 130, -10, 20)]), place(clips[0], 60, 30), lp], [GREY, DARK, ORANGE], 25, 30, (1000, 1300), [[-30, 0, -10], [190, 140, 50]]), "parts")
print("ok")
