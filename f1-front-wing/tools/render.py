"""Tiny dependency-light mesh renderer (numpy + PIL, painter's algorithm, flat shading)."""
import numpy as np
from PIL import Image, ImageDraw, ImageFont

def look_rotation(azim_deg, elev_deg):
    """Rotation matrix mapping world -> camera (camera looks along -z_cam). Z-up world."""
    a, e = np.radians(azim_deg), np.radians(elev_deg)
    # camera direction (from target to camera)
    d = np.array([np.cos(e) * np.cos(a), np.cos(e) * np.sin(a), np.sin(e)])
    up = np.array([0, 0, 1.0])
    if abs(np.dot(d, up)) > 0.999:
        up = np.array([0, 1.0, 0])
    right = np.cross(up, d); right /= np.linalg.norm(right)
    true_up = np.cross(d, right)
    return np.stack([right, true_up, d])  # rows

def render(meshes, colors=None, azim=-60, elev=25, size=(900, 700), margin=20,
           bg=(250, 250, 250), labels=None, scale=None, center=None, edge=False):
    """meshes: list of trimesh.Trimesh; colors: list of RGB tuples. Returns PIL image (and scale used)."""
    R = look_rotation(azim, elev)
    light = np.array([0.35, 0.55, 0.75]); light /= np.linalg.norm(light)
    all_tris, all_cols, all_depth = [], [], []
    pts_all = []
    for i, m in enumerate(meshes):
        v = m.vertices @ R.T
        pts_all.append(v)
    allv = np.vstack(pts_all)
    lo, hi = allv.min(0), allv.max(0)
    W, H = size
    if scale is None:
        scale = min((W - 2 * margin) / max(hi[0] - lo[0], 1e-6), (H - 2 * margin) / max(hi[1] - lo[1], 1e-6))
    if center is None:
        center = (lo + hi) / 2
    img = Image.new('RGB', size, bg)
    dr = ImageDraw.Draw(img)
    for i, (m, v) in enumerate(zip(meshes, pts_all)):
        col = np.array(colors[i] if colors else (180, 180, 190), float)
        tri = v[m.faces]                      # (F,3,3) in camera space
        n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
        nn = np.linalg.norm(n, axis=1); nn[nn == 0] = 1
        n = n / nn[:, None]
        facing = n[:, 2] > 0                  # facing camera (camera at +z)
        shade = np.clip(np.abs(n @ (R @ light if False else light)), 0, 1)
        lam = 0.35 + 0.65 * np.clip(n @ light, 0, 1)
        tri, lam = tri[facing], lam[facing]          # back-face culling (closed meshes)
        all_tris.append(tri); all_cols.append(np.clip(col[None] * lam[:, None], 0, 255)); all_depth.append(tri[:, :, 2].max(1))
    tris = np.concatenate(all_tris); cols = np.concatenate(all_cols); depth = np.concatenate(all_depth)
    order = np.argsort(depth)                 # far (small z) first
    xy = np.empty((len(tris), 3, 2))
    xy[..., 0] = (tris[..., 0] - center[0]) * scale + W / 2
    xy[..., 1] = H / 2 - (tris[..., 1] - center[1]) * scale
    for k in order:
        c = tuple(int(x) for x in cols[k])
        p = [tuple(q) for q in xy[k]]
        dr.polygon(p, fill=c, outline=(c if not edge else (40, 40, 40)))
    if labels:
        for (txt, pos, colr) in labels:
            dr.text(pos, txt, fill=colr)
    return img, scale, center

def project(points, azim, elev, scale, center, size):
    R = look_rotation(azim, elev)
    v = np.atleast_2d(points) @ R.T
    W, H = size
    return np.stack([(v[:, 0] - center[0]) * scale + W / 2, H / 2 - (v[:, 1] - center[1]) * scale], 1)
