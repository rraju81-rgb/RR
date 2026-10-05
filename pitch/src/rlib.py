"""Tiny z-buffer renderer: perspective camera, two lights, outlines, translucent overlays, ground shadow. numpy only."""
import numpy as np, trimesh
from PIL import Image, ImageFilter

def look_at(eye, target, up=(0, 0, 1)):
    eye, target, up = map(lambda v: np.array(v, float), (eye, target, up))
    f = target - eye; f /= np.linalg.norm(f); r = np.cross(f, up); r /= np.linalg.norm(r); u = np.cross(r, f)
    return eye, r, u, f

def _raster(tris, cols, cam, W, H, fov, zbuf, cbuf, idbuf=None, ids=None, alpha=None):
    eye, r, u, f = cam; fl = 0.5*H/np.tan(np.radians(fov)/2)
    rel = tris - eye
    X, Y, Z = rel @ r, rel @ u, rel @ f
    ok = (Z > 1).all(axis=1)
    sx = W/2 + fl*X/Z; sy = H/2 - fl*Y/Z
    for i in np.nonzero(ok)[0]:
        x, y, z = sx[i], sy[i], Z[i]
        x0, x1 = max(int(np.floor(x.min())), 0), min(int(np.ceil(x.max())), W - 1)
        y0, y1 = max(int(np.floor(y.min())), 0), min(int(np.ceil(y.max())), H - 1)
        if x1 < x0 or y1 < y0: continue
        d = (y[1]-y[2])*(x[0]-x[2]) + (x[2]-x[1])*(y[0]-y[2])
        if abs(d) < 1e-9: continue
        px, py = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
        a = ((y[1]-y[2])*(px-x[2]) + (x[2]-x[1])*(py-y[2]))/d
        b = ((y[2]-y[0])*(px-x[2]) + (x[0]-x[2])*(py-y[2]))/d
        c = 1 - a - b
        m = (a >= -1e-6) & (b >= -1e-6) & (c >= -1e-6)
        if not m.any(): continue
        zz = 1.0/(a/z[0] + b/z[1] + c/z[2])
        sub = zbuf[y0:y1+1, x0:x1+1]
        w = m & (zz < sub)
        if not w.any(): continue
        sub[w] = zz[w]
        cbuf[y0:y1+1, x0:x1+1][w] = cols[i]
        if idbuf is not None: idbuf[y0:y1+1, x0:x1+1][w] = ids[i]

def render(items, eye, target, W=1600, H=1100, fov=30, ss=2, bg=(1, 1, 1), ground=None, out=None, outline=True):
    """items: list of (mesh, rgb, alpha). alpha<1 meshes are drawn as a translucent layer over the opaque scene."""
    W2, H2 = W*ss, H*ss; cam = look_at(eye, target)
    L1 = np.array([0.45, -0.6, 0.75]); L1 /= np.linalg.norm(L1); L2 = np.array([-0.6, 0.3, 0.4]); L2 /= np.linalg.norm(L2)
    def shade(m, rgb):
        n = m.face_normals; vdir = -(m.triangles_center - cam[0]); vdir /= np.linalg.norm(vdir, axis=1)[:, None]
        n = np.where((np.sum(n*vdir, axis=1) < 0)[:, None], -n, n)
        k = 0.38 + 0.52*np.clip(n @ L1, 0, 1) + 0.18*np.clip(n @ L2, 0, 1)
        return np.clip(np.array(rgb)[None, :]*k[:, None], 0, 1)
    zb = np.full((H2, W2), np.inf); cb = np.ones((H2, W2, 3))*np.array(bg); ib = np.full((H2, W2), -1, int)
    gid = 0
    if ground is not None:      # (z, rgb, extent) ground plane with a soft contact shadow
        gz, grgb, (gx0, gx1, gy0, gy1) = ground
        g = trimesh.Trimesh([[gx0, gy0, gz], [gx1, gy0, gz], [gx1, gy1, gz], [gx0, gy1, gz]], [[0, 1, 2], [0, 2, 3]])
        _raster(g.triangles, np.clip(np.array([grgb, grgb])*0.64, 0, 1), cam, W2, H2, fov, zb, cb, ib, np.array([-2, -2]))
    for m, rgb, a in items:
        if a >= 1:
            _raster(m.triangles, shade(m, rgb), cam, W2, H2, fov, zb, cb, ib, np.full(len(m.faces), gid)); gid += 1
    if outline:                 # dark lines at object / depth / normal discontinuities
        zf = np.where(np.isinf(zb), 1e9, zb)
        e = np.zeros((H2, W2), bool)
        for dy, dx in [(0, 1), (1, 0)]:
            idd = ib != np.roll(np.roll(ib, dy, 0), dx, 1)
            dz = np.abs(zf - np.roll(np.roll(zf, dy, 0), dx, 1)) > 0.02*np.minimum(zf, np.roll(np.roll(zf, dy, 0), dx, 1))
            dc = np.abs(cb - np.roll(np.roll(cb, dy, 0), dx, 1)).sum(axis=2) > 0.22
            both_bg = (ib < 0) & (np.roll(np.roll(ib, dy, 0), dx, 1) < 0)
            e |= (idd | dz | (dc & (ib >= 0))) & ~both_bg
        e &= ~((ib == -2) & np.roll(ib == -2, 1, 0) & np.roll(ib == -2, 1, 1))
        cb[e] = cb[e]*0.35
    for m, rgb, a in items:     # translucent layer
        if a < 1:
            zt = np.full((H2, W2), np.inf); ct = np.zeros((H2, W2, 3))
            _raster(m.triangles, shade(m, rgb), cam, W2, H2, fov, zt, ct)
            w = zt < zb
            cb[w] = cb[w]*(1 - a) + ct[w]*a
    img = Image.fromarray((np.clip(cb, 0, 1)*255).astype(np.uint8)).resize((W, H), Image.LANCZOS)
    if out: img.save(out)
    return img

def project(pts, eye, target, W, H, fov):
    eye_, r, u, f = look_at(eye, target); fl = 0.5*H/np.tan(np.radians(fov)/2)
    rel = np.atleast_2d(pts) - eye_
    return np.c_[W/2 + fl*(rel @ r)/(rel @ f), H/2 - fl*(rel @ u)/(rel @ f)]
