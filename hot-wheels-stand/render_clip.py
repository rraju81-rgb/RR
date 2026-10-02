"""python3 render_clip.py -> clip/preview_*.png"""
import numpy as np, trimesh, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from build_clip import *

def raster(meshes, colors, elev, azim, size=(520, 640), lim=None):
    """small z-buffer rasteriser (matplotlib's painter sort breaks on big meshes)"""
    W, H = size
    ca, sa, ce, se = np.cos(np.radians(azim)), np.sin(np.radians(azim)), np.cos(np.radians(elev)), np.sin(np.radians(elev))
    Rz = np.array([[ca, -sa, 0], [sa, ca, 0], [0, 0, 1]]); Rx = np.array([[1, 0, 0], [0, ce, -se], [0, se, ce]])
    # model x right, y up, z toward viewer (+z out of wall); rotate about up axis then tilt
    Ry = np.array([[ca, 0, sa], [0, 1, 0], [-sa, 0, ca]]); Rt = np.array([[1, 0, 0], [0, ce, -se], [0, se, ce]])
    M = Rt @ Ry
    allv = np.vstack([m.vertices for m in meshes]) @ M.T
    if lim is not None: allv = np.array(lim) @ M.T
    lo, hi = allv.min(0), allv.max(0); sc = min((W - 20) / (hi[0] - lo[0]), (H - 20) / (hi[1] - lo[1]))
    img = np.ones((H, W, 3)); zb = np.full((H, W), -1e9)
    L = np.array([0.3, 0.5, 0.8]); L /= np.linalg.norm(L)
    for m, c in zip(meshes, colors):
        v = m.vertices @ M.T; n = m.face_normals @ M.T
        px = (v[:, 0] - lo[0]) * sc + 10; py = H - ((v[:, 1] - lo[1]) * sc + 10)
        for f, nn in zip(m.faces, n):
            if nn[2] <= 0: continue
            sh = 0.45 + 0.55 * max(0, nn @ L)
            xs, ys, zs = px[f], py[f], v[f, 2]
            x0, x1 = int(max(0, np.floor(xs.min()))), int(min(W - 1, np.ceil(xs.max())))
            y0, y1 = int(max(0, np.floor(ys.min()))), int(min(H - 1, np.ceil(ys.max())))
            if x1 < x0 or y1 < y0: continue
            X, Y = np.meshgrid(np.arange(x0, x1 + 1) + .5, np.arange(y0, y1 + 1) + .5)
            d = (ys[1] - ys[2]) * (xs[0] - xs[2]) + (xs[2] - xs[1]) * (ys[0] - ys[2])
            if abs(d) < 1e-9: continue
            a = ((ys[1] - ys[2]) * (X - xs[2]) + (xs[2] - xs[1]) * (Y - ys[2])) / d
            b = ((ys[2] - ys[0]) * (X - xs[2]) + (xs[0] - xs[2]) * (Y - ys[2])) / d
            cc = 1 - a - b; inside = (a >= -1e-6) & (b >= -1e-6) & (cc >= -1e-6)
            z = a * zs[0] + b * zs[1] + cc * zs[2]
            sub = zb[y0:y1 + 1, x0:x1 + 1]; upd = inside & (z > sub)
            sub[upd] = z[upd]; img[y0:y1 + 1, x0:x1 + 1][upd] = np.array(c) * sh
    return img


def panel(ax, ms, cs, el, az, lim=None, title="", size=(520, 640)):
    ax.imshow(raster(ms, cs, el, az, size, lim)); ax.set_axis_off(); ax.set_title(title, fontsize=10)

def box8(lo, hi): return [[x, y, z] for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])]
import build_clip as bc
grey, orange, dk = (0.75, 0.75, 0.78), (0.95, 0.6, 0.1), (0.3, 0.3, 0.35)
bc.strip_m = build_strip(); clips = {k: build_clip(k) for k in (1, 2, 3)}
fig, axs = plt.subplots(1, 5, figsize=(20, 9), dpi=100)
for ax, N in zip(axs, (2, 3, 4, 5, 6)):
    strips = 1 if N <= 4 else 2
    parts = stack_assembly(N, strips, clips)
    cols = [grey] * strips + [dk if i % 1 == 0 else dk for i in range(0)]
    ms, cs, idx = parts[:strips], [grey] * strips, strips
    for k in STACKS[N]:
        ms.append(parts[idx]); cs.append(dk); ms += parts[idx + 1: idx + 1 + k]; cs += [orange] * k; idx += 1 + k
    panel(ax, ms, cs, 14, 28, ([-60, 0, -5], [130, 240 * strips, 60]), f"{N} cars: " + " + ".join(f"clip x{k}" for k in STACKS[N]) + (f", {strips} strips" if strips > 1 else ""), (360, 640))
fig.savefig("clip/preview_stacks.png", bbox_inches="tight"); plt.close(fig)

fig, axs = plt.subplots(1, 3, figsize=(16, 5), dpi=100)
A = bc.strip_m; B = place(A, 0, 236)
panel(axs[0], [to_print(A, "strip")], [grey], 30, 20, ([0, 200, 0], [25, 250, 4]), "strip top end: two press-fit tabs", (480, 380))
panel(axs[1], [A, place(A, 0, 240)], [grey, (0.6, 0.7, 0.9)], 25, 25, ([-15, 200, -5], [30, 290, 6]), "two strips stacked", (480, 380))
panel(axs[2], [to_print(clips[3], "clip")], [dk], 20, 35, title="clip x3 (print standing, 150 mm)", size=(480, 380))
fig.savefig("clip/preview_strip_stack.png", bbox_inches="tight"); plt.close(fig)
