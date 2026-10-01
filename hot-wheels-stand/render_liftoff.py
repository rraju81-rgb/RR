"""Preview of the lift-off tray: hung in the wall frame, and lifted off, lying flat.
Usage: python3 render_liftoff.py [N]   -> preview_liftoff_<N>slot.png
Small orthographic z-buffer rasteriser (numpy + PIL), so depth ordering is exact."""
import sys
import numpy as np
from PIL import Image, ImageDraw
import build_liftoff as L
import build_stl as b

N = int(sys.argv[1]) if len(sys.argv) > 1 else 4
tray, frame = L.tray(N), L.frame(N)[0]
cols = [(0.85,0.2,0.15),(0.15,0.45,0.85),(0.95,0.6,0.1),(0.2,0.65,0.35),(0.6,0.25,0.7),(0.9,0.85,0.2)]

def cards():
    out = []
    for j in range(N):
        cy = j * b.pitch + b.ledge_h - b.gutter_d
        z = b.zc(j) + b.back_t
        out.append((b.box(b.spine_w, b.spine_w + b.card_w, cy, cy + b.card_h, z, z + b.card_t), cols[j]))
        out.append((b.box(b.spine_w + 12, b.spine_w + b.card_w - 12, cy + 4, cy + b.blister_h,
                          z + b.card_t, z + b.card_t + 14), (0.75, 0.85, 0.95)))
    return out

def rotation(elev, azim):
    e, a = np.radians(elev), np.radians(azim)
    rz = np.array([[np.cos(a), -np.sin(a), 0], [np.sin(a), np.cos(a), 0], [0, 0, 1]])
    rx = np.array([[1, 0, 0], [0, np.cos(e), -np.sin(e)], [0, np.sin(e), np.cos(e)]])
    return rx @ rz

def render(items, to_world, elev, azim, size, scale):
    """to_world: maps model (x, y, z) -> world with +Z up. Camera looks along +Y after rotation."""
    R = rotation(elev, azim)
    W, Hh = size
    img = np.full((Hh, W, 3), 255, np.uint8)
    zbuf = np.full((Hh, W), -1e9)
    light = np.array([0.35, -0.6, 0.7]); light /= np.linalg.norm(light)
    allv = np.vstack([to_world(m.vertices) @ R.T for m, _ in items])
    cx, cy = (allv[:, 0].min() + allv[:, 0].max()) / 2, (allv[:, 2].min() + allv[:, 2].max()) / 2
    for mesh, col in items:
        wv = to_world(mesh.vertices)
        v = wv @ R.T
        u = (v[:, 0] - cx) * scale + W / 2
        w = Hh / 2 - (v[:, 2] - cy) * scale
        depth = -v[:, 1]                       # larger = closer to the camera
        nrm = (mesh.face_normals @ (to_world(np.eye(3)) - to_world(np.zeros((1, 3)))).T) @ R.T
        for f, n in zip(mesh.faces, nrm):
            if n[1] > 0:                        # back-facing (camera looks along +Y)
                continue
            shade = 0.5 + 0.5 * max(0.0, float(np.dot(n, light)))
            p = np.array([[u[k], w[k], depth[k]] for k in f])
            x0, x1 = int(max(0, np.floor(p[:, 0].min()))), int(min(W - 1, np.ceil(p[:, 0].max())))
            y0, y1 = int(max(0, np.floor(p[:, 1].min()))), int(min(Hh - 1, np.ceil(p[:, 1].max())))
            if x1 < x0 or y1 < y0:
                continue
            xs, ys = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
            d = (p[1, 1] - p[2, 1]) * (p[0, 0] - p[2, 0]) + (p[2, 0] - p[1, 0]) * (p[0, 1] - p[2, 1])
            if abs(d) < 1e-9:
                continue
            l1 = ((p[1, 1] - p[2, 1]) * (xs - p[2, 0]) + (p[2, 0] - p[1, 0]) * (ys - p[2, 1])) / d
            l2 = ((p[2, 1] - p[0, 1]) * (xs - p[2, 0]) + (p[0, 0] - p[2, 0]) * (ys - p[2, 1])) / d
            l3 = 1 - l1 - l2
            inside = (l1 >= -1e-3) & (l2 >= -1e-3) & (l3 >= -1e-3)
            z = l1 * p[0, 2] + l2 * p[1, 2] + l3 * p[2, 2]
            sub = zbuf[y0:y1 + 1, x0:x1 + 1]
            upd = inside & (z > sub)
            sub[upd] = z[upd]
            img[y0:y1 + 1, x0:x1 + 1][upd] = (np.array(col) * shade * 255).astype(np.uint8)
    return Image.fromarray(img)

def label(im, text):
    d = ImageDraw.Draw(im); d.text((12, 10), text, fill=(20, 20, 20)); return im

frame_col, tray_col = (0.6, 0.62, 0.66), (0.2, 0.2, 0.23)
hung = [(frame, frame_col), (tray, tray_col)] + cards()
flat = [(tray, tray_col)] + cards()
# hung: wall plane is x-z... model (x right, y up, z out) -> world (x, -z, y): camera sits on the +z side
im1 = render(hung, lambda p: np.column_stack([p[:, 0], -p[:, 2], p[:, 1]]), 6, -35, (560, 1100), 1.9)
# flat: model (x, y, z) -> world (x, y, z): z (card faces) up
im2 = render(flat, lambda p: np.column_stack([p[:, 0], p[:, 1], p[:, 2]]), 42, -58, (1000, 1100), 2.3)
from PIL import ImageChops

def crop(im, pad=20):
    bg = Image.new("RGB", im.size, "white")
    box = ImageChops.difference(im, bg).getbbox()
    box = (max(0, box[0] - pad), max(0, box[1] - pad), min(im.width, box[2] + pad), min(im.height, box[3] + pad))
    return im.crop(box)

im1, im2 = crop(im1), crop(im2)
bar = 46
H = max(im1.height, im2.height) + bar
out = Image.new("RGB", (im1.width + im2.width + 30, H), "white")
out.paste(im1, (0, bar)); out.paste(im2, (im1.width + 30, bar))
d = ImageDraw.Draw(out)
d.text((10, 14), f"HUNG IN THE WALL FRAME ({N} cards)", fill=(20, 20, 20))
d.text((im1.width + 40, 14), "LIFTED OFF AND LAID FLAT: cards face up, any card slides out sideways", fill=(20, 20, 20))
out.save(f"preview_liftoff_{N}slot.png")
