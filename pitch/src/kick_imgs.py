"""Pitch renders for the SlideRack Fold (fixed rack + kickstand) family."""
import os, sys, numpy as np, trimesh
sys.path.insert(0, '/home/user/RR/3d-models')
from rlib import render
src_imgs = open('pitch_imgs.py').read().split('# ---------------- wall mount')[0].replace("open('table_stands.py')", "open('/home/user/RR/3d-models/build_table_stands.py')"); g = {}; exec(src_imgs, g)
card, CARS = g['card'], g['CARS'] + g['CARS']
RACKC, LEGC = (0.30, 0.32, 0.40), (0.91, 0.52, 0.12)
GR = (0, (1.5, 1.5, 1.52), (-1500, 1500, -1500, 1500)); BG = (0.955, 0.955, 0.965)
OUT = '/home/user/RR/pitch/'; MD = '/home/user/RR/3d-models/'
CFG = {3: (121, 27.5), 5: (176, 25.0), 6: (176, 24.5)}
mv = lambda m, M: (lambda c: (c.apply_transform(M), c)[1])(m.copy())
def load(N):
    YH, A = CFG[N]
    os.environ.update(KS_N=str(N), KS_YH=str(YH), KS_ALPHA=str(A), KS_RACK=MD + 'reference_right_fixed_rack_PRINT.stl')
    sys.modules.pop('build_right_fixed_rack_kickstand', None); import build_right_fixed_rack_kickstand as E
    m = trimesh.load(MD + f'right_fixed_rack_{N}card_kickstand_PRINT.stl'); m.apply_transform(E.TO_RACK)
    P, L = sorted(m.split(), key=lambda b: -b.volume)
    return E, P, L
def scene(N, dx=0.0, shift=None, psi=None, cards=True):
    E, P, L = load(N); A = CFG[N][1]
    T = E.tilt(A, P); M = trimesh.transformations.translation_matrix([dx, 0, 0])
    psi = E.PSI if psi is None else psi
    items = [(mv(P, M @ T), RACKC, 1), (mv(L, M @ T @ E.rot(psi)), LEGC, 1)]
    if cards:
        for k in range(N):
            off = (shift or {}).get(k, 0)
            for m, c, al in card(28.5 + off, 55*k, 3.7 + 4.6*k + 0.3, carc=CARS[k]): items.append((mv(m, M @ T), c, al))
    return E, items
if __name__ == '__main__':
    ONLY = os.environ.get('ONLY', '')
    # hero: the three sizes side by side
    items = []
    if ONLY and ONLY != 'hero': items = None
    for N, dx in [(3, -340), (5, -170), (6, 0)]: items += scene(N, dx)[1]
    render(items, eye=(-420, -640, 360), target=(-110, 60, 150), fov=34, W=1600, H=1000, ground=GR, bg=BG, out=OUT + 'k_hero.png')
    # slide-in: 5-card, 3rd card halfway out of the open end
    E, items = scene(5, shift={2: 80})
    render(items, eye=(-330, -560, 420), target=(90, 40, 120), fov=34, W=900, H=1000, ground=GR, bg=BG, out=OUT + 'k_slide.png')
    # behind: stand open, hinge on the end wall
    E, items = scene(5, cards=False)
    render(items, eye=(420, 520, 300), target=(60, 50, 100), fov=34, W=900, H=1000, ground=GR, bg=BG, out=OUT + 'k_back.png')
    # folded flat, lying on its back on the table (the way it stores)
    E, P, L = load(5)
    Tf = np.array([[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]], float)
    lay = trimesh.transformations.rotation_matrix(np.pi/2, [1, 0, 0]) @ trimesh.transformations.rotation_matrix(np.pi, [0, 1, 0])
    a = mv(P, lay); b = mv(L, lay); zmin = min(a.bounds[0][2], b.bounds[0][2]); sh = trimesh.transformations.translation_matrix([0, 0, -zmin])
    a, b = mv(a, sh), mv(b, sh); cc = trimesh.util.concatenate([a, b]).bounds.mean(0)
    render([(a, RACKC, 1), (b, LEGC, 1)], eye=(cc[0] + 180, cc[1] - 330, 330), target=tuple(cc), fov=40, W=900, H=700, ground=GR, bg=BG, out=OUT + 'k_fold.png')
    # hinge close-up, open, from behind
    E, P, L = load(5); T = E.tilt(CFG[5][1], P); hy = (T @ np.array([14, E.YH, E.H['z'], 1]))[:3]
    render([(mv(P, T), RACKC, 1), (mv(L, T @ E.rot(E.PSI)), LEGC, 1)], eye=(hy[0] - 60, hy[1] + 115, hy[2] + 45), target=tuple(hy), fov=32, W=900, H=700, ground=GR, bg=BG, out=OUT + 'k_hinge.png')
    # as printed: one piece on its side
    m = trimesh.load(MD + 'right_fixed_rack_5card_kickstand_PRINT.stl')
    P2, L2 = sorted(m.split(), key=lambda b: -b.volume)
    render([(P2, RACKC, 1), (L2, LEGC, 1)], eye=(330, -260, 330), target=(20, 120, 60), fov=38, W=900, H=700, ground=GR, bg=BG, out=OUT + 'k_print.png')
    print('ok')
