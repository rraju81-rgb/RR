"""v8 step 0 (documentation): back-project the blue lines the user drew on two v7 figures onto the v7 end pieces.
The result, v8/data/user_marks_3d.npz, is only used to draw v8/docs/v8_cut_vs_marks.png; the cut itself is CUT_Z in
layout.py. Needs the v7 files (sh v7/src/run_all.sh).
Run from spoiler/:  python3 v8/src/p0_marks.py"""
import sys; sys.path.insert(0, 'v7/src'); sys.path.insert(0, 'v6/src')
import numpy as np, trimesh
from PIL import Image
from skimage.morphology import skeletonize
from trimesh.ray.ray_pyembree import RayMeshIntersector
from zr import look_at, fit_view
from layout import ASM, PRN, OUT, IDS, STEM

f_asm, f_bed, f_out = 'v8/data/marks/marked_v7_assembled.png', 'v8/data/marks/marked_v7_bed_layouts.webp', 'v8/data/user_marks_3d.npz'
P = {k: trimesh.load(f'{ASM}/{k}.stl') for k in IDS}

def stroke_mask(path, scale=1.0):
    a = np.asarray(Image.open(path).convert('RGB')).astype(int)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    return (b > 150) & (r < 80) & (g > 80) & (g < 160) & (b - r > 110)

def rays(eye, tgt, up, fov, W, H, px, py):
    e, r, u, f = look_at(eye, tgt, up)
    F = 0.5 * H / np.tan(np.radians(fov) / 2)
    xz = (px - W / 2) / F; yz = -(py - H / 2) / F
    D = f[None] + xz[:, None] * r[None] + yz[:, None] * u[None]
    return np.tile(e, (len(px), 1)), D / np.linalg.norm(D, axis=1, keepdims=True)

def hit(meshes, O, D):
    """first hit over several meshes: returns points, mesh index (-1 = miss)"""
    best_t = np.full(len(O), np.inf); best_p = np.full((len(O), 3), np.nan); best_k = np.full(len(O), -1)
    for k, m in enumerate(meshes):
        loc, ir, it = RayMeshIntersector(m).intersects_location(O, D, multiple_hits=False)
        t = np.einsum('ij,ij->i', loc - O[ir], D[ir])
        better = t < best_t[ir]
        best_t[ir[better]] = t[better]; best_p[ir[better]] = loc[better]; best_k[ir[better]] = k
    return best_p, best_k

out = {}
# ---- image 2: v7_assembled.png = two 1300 x 800 panels stacked (rear three-quarter on top, front below)
m2 = stroke_mask(f_asm)
for panel, (dr, y0) in enumerate([((-0.55, 0.42, 0.72), 0), ((0.62, 0.40, -0.67), 800)]):
    sub = skeletonize(m2[y0:y0 + 800])
    jy, ix = np.nonzero(sub)
    if len(ix) == 0: continue
    eye, tgt, fov = fit_view(list(P.values()), dr, W=1300, H=800, dist=2600)
    O, D = rays(eye, tgt, (0, 1, 0), fov, 1300, 800, ix + 0.5, jy + 0.5)
    pts, k = hit([P[i] for i in IDS], O, D)
    for pid in ('P1', 'P4'):
        sel = k == IDS.index(pid)
        if sel.sum():
            out[f'asm{panel}_{pid}'] = pts[sel]
            print(f'assembled panel {panel}: {sel.sum()} stroke pixels hit {pid}; {np.sum(k < 0)} missed; x {pts[sel, 0].min():.0f}..{pts[sel, 0].max():.0f}')

# ---- image 1: v7_bed_layouts.png (5 panels of 620 x 820), shown to the user scaled to 2000 px wide
m1 = stroke_mask(f_bed)
s = 3100.0 / m1.shape[1]
sk = skeletonize(m1)
jy, ix = np.nonzero(sk)
X = (ix + 0.5) * s; Y = (jy + 0.5) * s
for panel, pid in [(0, 'P1'), (3, 'P4')]:
    sel = (X >= 620 * panel) & (X < 620 * (panel + 1))
    if not sel.any(): continue
    pr = trimesh.load(f'{PRN}/{STEM[pid]}.stl')
    O, D = rays((210 + 650, 210 - 750, 520), (210, 210, 160), (0, 0, 1), 42, 620, 820, X[sel] - 620 * panel, Y[sel])
    pts, k = hit([pr], O, D)
    ok = k == 0
    # print frame -> assembled frame: V_print = V_asm @ Rt.T + t
    Rt = np.load(f'{OUT}/_place_{pid}.npy'); A = P[pid]
    t = pr.vertices.mean(0) - (A.vertices @ Rt.T).mean(0)
    back = (pts[ok] - t) @ Rt                          # inverse rotation
    out[f'bed_{pid}'] = back
    print(f'bed panel {panel}: {ok.sum()} stroke pixels hit {pid} (of {sel.sum()}); x {back[:, 0].min():.0f}..{back[:, 0].max():.0f}')
np.savez(f_out, **out)
print('saved', f_out, list(out))
