"""Tiny orthographic z-buffer rasteriser (numpy + PIL) for previews of trimesh meshes."""
import numpy as np
from PIL import Image, ImageChops


def rotation(elev, azim):
    e, a = np.radians(elev), np.radians(azim)
    rz = np.array([[np.cos(a), -np.sin(a), 0], [np.sin(a), np.cos(a), 0], [0, 0, 1]])
    rx = np.array([[1, 0, 0], [0, np.cos(e), -np.sin(e)], [0, np.sin(e), np.cos(e)]])
    return rx @ rz


def render(items, to_world, elev, azim, size, scale, center=None):
    """items: [(mesh, (r,g,b) 0..1)]. to_world maps model xyz -> world with +Z up; camera looks along +Y."""
    R = rotation(elev, azim)
    W, Hh = size
    img = np.full((Hh, W, 3), 255, np.uint8)
    zbuf = np.full((Hh, W), -1e9)
    light = np.array([0.35, -0.6, 0.7]); light /= np.linalg.norm(light)
    allv = np.vstack([to_world(m.vertices) @ R.T for m, _ in items])
    if center is None:
        center = ((allv[:, 0].min() + allv[:, 0].max()) / 2, (allv[:, 2].min() + allv[:, 2].max()) / 2)
    cx, cy = center
    L = to_world(np.eye(3)) - to_world(np.zeros((1, 3)))
    for mesh, col in items:
        v = to_world(mesh.vertices) @ R.T
        u = (v[:, 0] - cx) * scale + W / 2
        w = Hh / 2 - (v[:, 2] - cy) * scale
        depth = -v[:, 1]
        nrm = (mesh.face_normals @ L.T) @ R.T
        for f, n in zip(mesh.faces, nrm):
            if n[1] > 0:
                continue
            shade = 0.5 + 0.5 * max(0.0, float(np.dot(n, light)))
            p = np.column_stack([u[f], w[f], depth[f]])
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
    return Image.fromarray(img), center


def crop(im, pad=16):
    box = ImageChops.difference(im, Image.new("RGB", im.size, "white")).getbbox()
    box = (max(0, box[0] - pad), max(0, box[1] - pad), min(im.width, box[2] + pad), min(im.height, box[3] + pad))
    return im.crop(box)
