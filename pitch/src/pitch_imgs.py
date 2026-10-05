import trimesh, numpy as np
from trimesh.creation import box
from rlib import render
src = open('table_stands.py').read().split('CONFIG = {')[0]; ns = {}; exec(src, ns)
OUT = '/home/user/RR/pitch/'
RACK, BASE, FEET = (0.36, 0.38, 0.45), (0.20, 0.56, 0.44), (0.20, 0.56, 0.44)
CARDC, CAR, BLIS, SLIDE = (1.45, 1.47, 1.52), (0.95, 0.20, 0.17), (0.85, 0.92, 1.0), (1.5, 1.2, 0.7)
FLOOR, WALL = (0.955, 0.955, 0.965), (1.52, 1.50, 1.46)

def card(x0, y0, zg, carc=CAR, cardc=CARDC):
    """carded car in rack frame: card in the groove, blister + car on its front lower half"""
    c = box(bounds=[[x0, y0 + 3.2, zg], [x0 + 108, y0 + 168, zg + 0.6]])
    bl = box(bounds=[[x0 + 17, y0 + 14, zg + 0.6], [x0 + 91, y0 + 50, zg + 16]])
    car = box(bounds=[[x0 + 24, y0 + 18, zg + 2], [x0 + 84, y0 + 38, zg + 13]])
    wheels = [trimesh.creation.cylinder(radius=6, height=10, sections=24) for _ in range(2)]
    for w, xc in zip(wheels, (x0 + 36, x0 + 72)):
        w.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2, [0, 0, 1]) @ trimesh.transformations.rotation_matrix(np.pi/2, [0, 1, 0]))
        w.apply_translation([xc, y0 + 19, zg + 8])
    return [(c, cardc, 1), (trimesh.util.concatenate([car] + wheels), carc, 1), (bl, BLIS, 0.35)]

def tf(items, M):
    out = []
    for m, c, a in items:
        mm = m.copy(); mm.apply_transform(M); out.append((mm, c, a))
    return out

WALLM = np.array([[1, 0, 0, 0], [0, 0, -1, 0], [0, 1, 0, 0], [0, 0, 0, 1]], float)   # rack (x,y,z) -> wall scene (X, -z, y)
CARS = [(0.85, 0.16, 0.14), (0.95, 0.70, 0.10), (0.15, 0.35, 0.80), (0.20, 0.60, 0.30), (0.55, 0.20, 0.65), (0.90, 0.45, 0.10)]

# ---------------- wall mount ----------------
W = trimesh.load('rack_6ledge_130_3mmholes.stl')
wall_plane = box(bounds=[[-900, 0.2, -900], [1200, 3, 1500]])
def wall_cards(n=6, slide=None):
    it = []
    for k in range(n):
        x0 = 22.0 + (slide[1] if slide and slide[0] == k else 0)
        it += card(x0, 55*k, 3.7 + 4.6*k + 0.3, carc=CARS[k], cardc=SLIDE if slide and slide[0] == k else CARDC)
    return tf(it, WALLM)
scene = [(W.copy().apply_transform(WALLM) or W, RACK, 1)]
Wm = W.copy(); Wm.apply_transform(WALLM)
render([(wall_plane, WALL, 1), (Wm, RACK, 1)] + wall_cards(), eye=(-420, -880, 420), target=(70, 0, 225), fov=30, W=1000, H=1300, bg=(0.94, 0.93, 0.91), out=OUT + 'w_hero.png')
render([(wall_plane, WALL, 1), (Wm, RACK, 1)], eye=(-200, -900, 330), target=(65, 0, 225), fov=30, W=1000, H=1300, bg=(0.94, 0.93, 0.91), out=OUT + 'w_bare.png')
for i, off in enumerate([125, 60, 0]):
    render([(wall_plane, WALL, 1), (Wm, RACK, 1)] + wall_cards(2, slide=(0, off))[:3*1] + wall_cards(2, slide=(0, off))[3:],
           eye=(420, -430, 190), target=(150, 0, 75), fov=34, W=900, H=700, bg=(0.94, 0.93, 0.91), out=OUT + f'w_slide_{i}.png')
render([(wall_plane, WALL, 1), (Wm, RACK, 1)] + wall_cards(1, slide=(0, 40)), eye=(260, -150, 140), target=(118, -6, 10), fov=34, W=900, H=700, bg=(0.94, 0.93, 0.91), out=OUT + 'w_detail.png')
# on table feet
fl = trimesh.load('foot_left_plain.stl'); fr = trimesh.load('foot_right_plain.stl')
ybot = W.bounds[0, 1]
for f in (fl, fr): f.apply_translation([0, ybot - 4.0, 0])
TM = np.array([[1, 0, 0, 0], [0, 0, -1, 0], [0, 1, 0, 4 - ybot], [0, 0, 0, 1]], float)  # table scene: y up -> Z, z out -> -Y
items = [(W.copy(), RACK, 1), (fl, FEET, 1), (fr, FEET, 1)]
items = tf(items, TM)
cards_t = tf([it for k in range(6) for it in card(22, 55*k, 3.7 + 4.6*k + 0.3, carc=CARS[k])], TM)
render(items + cards_t, eye=(-520, -700, 380), target=(70, 0, 215), fov=30, W=1000, H=1300, ground=(0, (1.5, 1.5, 1.52), (-600, 800, -600, 800)), bg=FLOOR, out=OUT + 'w_table.png')
render(items, eye=(-140, -260, 120), target=(60, 0, 20), fov=34, W=1000, H=650, ground=(0, (1.5, 1.5, 1.52), (-600, 800, -600, 800)), bg=FLOOR, out=OUT + 'w_feet.png')

# ---------------- tabletop ----------------
B = trimesh.load('_ub_base.stl')
def table_items(N, dx=0.0, lift_rack=0.0, cards=True, slide=None):
    R = trimesh.load(f'_ub_rack_{N}.stl'); lift, LP = np.load(f'_ub_{N}.npy')
    T = ns['TILT'].copy(); T[2, 3] += lift
    it = [(R.copy(), RACK, 1)]
    if lift_rack: it[0][0].apply_translation([0, 0, lift_rack])
    if cards:
        cs = []
        for k in range(N):
            x0 = 1.5 - 8 + 8 + (slide[1] if slide and slide[0] == k else 0)      # body x already shifted by -X0 in rack build? (rack frame kept)
            cs += card(1.5 + (slide[1] if slide and slide[0] == k else 0), 55*k, 3.7 + 4.6*k + 0.3, carc=CARS[k],
                       cardc=SLIDE if slide and slide[0] == k else CARDC)
        it += tf(cs, T)
    b = B.copy()
    it.append((b, BASE, 1))
    return [(m.copy().apply_translation([dx, 0, 0]) or m, c, a) for m, c, a in it]
def shift(items, d):
    out = []
    for m, c, a in items:
        mm = m.copy(); mm.apply_translation(d); out.append((mm, c, a))
    return out
G = (0, (1.5, 1.5, 1.52), (-800, 1000, -800, 1000))
render(shift(table_items(3), [0, 0, 0]) + shift(table_items(5), [170, 40, 0]), eye=(-330, -560, 330), target=(150, 30, 120), fov=32, W=1400, H=1100, ground=G, bg=FLOOR, out=OUT + 't_hero.png')
render(table_items(3, slide=(1, 120)), eye=(320, -420, 260), target=(80, 20, 90), fov=32, W=1000, H=900, ground=G, bg=FLOOR, out=OUT + 't_slide.png')
ex = table_items(3, cards=False); ex[0][0].apply_translation([0, -12, 70])
render(ex, eye=(-300, -420, 260), target=(60, 30, 110), fov=34, W=900, H=1000, ground=G, bg=FLOOR, out=OUT + 't_explode.png')
render(table_items(5, cards=False), eye=(320, 420, 260), target=(60, 40, 110), fov=34, W=900, H=1000, ground=G, bg=FLOOR, out=OUT + 't_back.png')
render([(B.copy(), BASE, 1)], eye=(-260, -300, 210), target=(60, 50, 50), fov=32, W=900, H=700, ground=G, bg=FLOOR, out=OUT + 't_base.png')
render([(B.copy(), BASE, 1)], eye=(-420, 60, 60), target=(60, 60, 60), fov=30, W=900, H=600, ground=G, bg=FLOOR, out=OUT + 't_base_side.png')
print('done')
