"""Renders of the current models (lift-off SWING rack, fixed SLIDE rack, right + left pairs) for the sales kit.
Cards are drawn as simple coloured blanks. python3 marketing/make_renders_v2.py -> marketing/img/v2_*.png"""
import sys, os; ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, ROOT); os.chdir(ROOT)
import numpy as np, trimesh
import build_liftoff as B, build_fixed as F
from build_liftoff import box, union, mirror, LEFT_DY
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
src = open("render_clip.py").read(); exec(src[src.index("def raster("):src.index("def panel(")])
OUT = "marketing/img"
DARK, ORANGE, GREY = (0.22, 0.23, 0.27), (0.98, 0.45, 0.08), (0.82, 0.83, 0.86)
COLS = [(0.12, 0.35, 0.85), (0.85, 0.12, 0.15), (0.1, 0.65, 0.35), (0.55, 0.2, 0.75), (0.95, 0.75, 0.1), (0.1, 0.7, 0.85)]
def mv(m, d): m = m.copy(); m.apply_translation(d); return m
def rot(m, j, deg):                       # deg > 0 opens the ledge
    m = m.copy(); m.apply_transform(trimesh.transformations.rotation_matrix(np.radians(-deg), [0, 1, 0], [B.ax_x, 0, B.zc(j)])); return m
def card(y0, zf, slide=0.0):              # 105 x 165 card in the slot, blister 42 x 81 x 14
    return union([box(23 + slide, 128 + slide, y0 + 3.02, y0 + 168, zf + 0.05, zf + 1.25), box(35 + slide, 116 + slide, y0 + 11, y0 + 53, zf + 1.25, zf + 15.25)])
def scard(j, slide=0.0): return card(B.yb(j), B.front_ref(j) + B.DZ, slide)
def fcard(j, slide=0.0): return card(F.pitch * j, F.front_ref(j), slide)
def save(img, name):
    m = (img < 0.99).any(axis=2); ys, xs = np.where(m); img = img[max(ys.min() - 20, 0):ys.max() + 20, max(xs.min() - 20, 0):xs.max() + 20]
    plt.imsave(f"{OUT}/{name}.png", np.clip(img, 0, 1))
w, ls = B.build(); fx = F.rack()

def swing(angs, cards=True, left=False, lift=None):
    m, c = [w], [DARK]
    for j in range(B.n):
        a = angs[j]; d = [0, (lift or {}).get(j, 0), 0]
        m.append(mv(rot(ls[j], j, a), d)); c.append(ORANGE)
        if cards: m.append(mv(rot(scard(j), j, a), d)); c.append(COLS[(j + (3 if left else 0)) % 6])
    if left: m = [mirror(x, LEFT_DY) for x in m]
    return m, c
# 1 hero: SWING pair loaded, closed
mr, cr = swing([0] * 6); ml, cl = swing([0] * 6, left=True)
save(raster(mr + ml, cr + cl, 14, 24, (1300, 1700), [[-160, -40, -5], [140, 480, 140]]), "v2_swing_pair")
# 2 one door open on each side
mr, cr = swing([0, 0, 0, 65, 0, 0]); ml, cl = swing([0, 0, 45, 0, 0, 0], left=True)
save(raster(mr + ml, cr + cl, 18, 30, (1300, 1700), [[-160, -40, -5], [150, 480, 170]]), "v2_swing_open")
# 3 single SWING rack, one open (for close ads)
mr, cr = swing([0, 0, 0, 0, 70, 0])
save(raster(mr, cr, 16, 38, (1100, 1600), [[-10, 0, -5], [150, 470, 160]]), "v2_swing_one")
# 4 lift-off close-up: ledge lifted off its pin
y = B.yb(2); sub = B.inter([w, box(-10, 30, y - 18, y + 40, -5, 50)])
save(raster([sub, mv(ls[2], [0, B.lift + 2, 10])], [DARK, ORANGE], 22, 35, (1000, 900), [[-10, y - 18, -5], [140, y + 45, 60]]), "v2_liftoff")
save(raster([sub, ls[2]], [DARK, ORANGE], 22, 35, (1000, 900), [[-10, y - 18, -5], [140, y + 45, 60]]), "v2_hinge")
# 5 SLIDE pair loaded, one card sliding in on each side
def slide(left=False, sl=None):
    m, c = [fx], [ORANGE if not left else (0.95, 0.95, 0.96)]
    for j in range(F.n):
        m.append(fcard(j, (sl or {}).get(j, 0))); c.append(COLS[(j + (3 if left else 0)) % 6])
    if left: m = [mirror(x, LEFT_DY) for x in m]
    return m, c
mr, cr = slide(sl={3: 70}); ml, cl = slide(left=True, sl={2: 70})
save(raster(mr + ml, cr + cl, 14, 24, (1300, 1700), [[-230, -40, -5], [210, 480, 120]]), "v2_slide_pair")
mr, cr = slide(sl={4: 60})
save(raster(mr, cr, 16, 32, (1100, 1600), [[-10, 0, -5], [200, 470, 120]]), "v2_slide_one")
# 6 parts: SWING wall body + 6 ledges as printed
parts = [B.to_print_wall(w)] + [mv(B.to_print_ledge(l), [50, 15 * k, 0]) for k, l in enumerate(ls)]
save(raster(parts, [DARK] + [ORANGE] * 6, 40, 20, (1100, 1300)), "v2_parts")
print("ok")
