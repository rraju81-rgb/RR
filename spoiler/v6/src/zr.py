"""numba z-buffer renderer with smooth shading, zebra stripes and edge lines (inspection + figures)."""
import numpy as np, trimesh
from numba import njit
from PIL import Image

@njit(cache=True)
def _raster(px, py, pz, F, W, H, zbuf, tid, b0, b1, toff):
    for t in range(F.shape[0]):
        i0, i1, i2 = F[t, 0], F[t, 1], F[t, 2]
        x0, y0, z0 = px[i0], py[i0], pz[i0]
        x1, y1, z1 = px[i1], py[i1], pz[i1]
        x2, y2, z2 = px[i2], py[i2], pz[i2]
        if z0 <= 0 or z1 <= 0 or z2 <= 0:
            continue
        xmin = max(int(np.floor(min(x0, x1, x2))), 0); xmax = min(int(np.ceil(max(x0, x1, x2))), W - 1)
        ymin = max(int(np.floor(min(y0, y1, y2))), 0); ymax = min(int(np.ceil(max(y0, y1, y2))), H - 1)
        if xmin > xmax or ymin > ymax:
            continue
        den = (y1 - y2) * (x0 - x2) + (x2 - x1) * (y0 - y2)
        if abs(den) < 1e-12:
            continue
        for yy in range(ymin, ymax + 1):
            for xx in range(xmin, xmax + 1):
                fx = xx + 0.5; fy = yy + 0.5
                w0 = ((y1 - y2) * (fx - x2) + (x2 - x1) * (fy - y2)) / den
                w1 = ((y2 - y0) * (fx - x2) + (x0 - x2) * (fy - y2)) / den
                w2 = 1.0 - w0 - w1
                if w0 < -1e-6 or w1 < -1e-6 or w2 < -1e-6:
                    continue
                # perspective-correct depth (pz holds view depth)
                iz = w0 / z0 + w1 / z1 + w2 / z2
                z = 1.0 / iz
                if z < zbuf[yy, xx]:
                    zbuf[yy, xx] = z
                    tid[yy, xx] = t + toff
                    b0[yy, xx] = w0 / z0 * z
                    b1[yy, xx] = w1 / z1 * z

def look_at(eye, target, up=(0, 1, 0)):
    eye = np.asarray(eye, float); target = np.asarray(target, float); up = np.asarray(up, float)
    f = target - eye; f /= np.linalg.norm(f)
    r = np.cross(f, up); r /= np.linalg.norm(r)
    u = np.cross(r, f)
    return eye, r, u, f

def prep(m, crease=35.0):
    """split at creases for smooth shading"""
    try:
        s = m.smooth_shaded if crease is None else trimesh.graph.smooth_shade(m, angle=np.radians(crease))
    except Exception:
        s = m
    return s

def render(items, eye, target, up=(0, 1, 0), fov=30.0, W=1400, H=1000, bg=(30, 30, 34), ortho=None,
           light=None, zebra=0.0, zebra_axis=None, spec=0.35, ambient=0.22, edges=False, ssaa=2, crease=35.0,
           fill_light=0.25):
    """items: list of (trimesh, rgb[0-255]) or (trimesh, rgb, dict(alpha..)). zebra: stripe frequency (0=off)"""
    S = ssaa; Wr, Hr = W * S, H * S
    eye, r, u, f = look_at(eye, target, up)
    if light is None:
        light = -f + 0.7 * u - 0.35 * r
    light = np.asarray(light, float); light /= np.linalg.norm(light)
    fpx = 0.5 * Hr / np.tan(np.radians(fov) / 2)
    zbuf = np.full((Hr, Wr), np.inf); tid = np.full((Hr, Wr), -1, np.int64)
    b0 = np.zeros((Hr, Wr)); b1 = np.zeros((Hr, Wr))
    allV = []; allF = []; allN = []; allC = []; off = 0; voff = 0
    for it in items:
        m, rgb = it[0], it[1]
        s = prep(m, crease)
        V = np.asarray(s.vertices, float); Fc = np.asarray(s.faces, np.int64)
        N = np.asarray(s.vertex_normals, float)
        d = V - eye; x = d @ r; y = d @ u; z = d @ f
        if ortho:
            sc = Hr / ortho; px = Wr / 2 + x * sc; py = Hr / 2 - y * sc; pz = z - z.min() + 1.0 if False else z
            pz = np.where(z > 0, z, 1e-3)
            # orthographic: depth affine -> use z directly with no perspective correction (approx fine)
        else:
            px = Wr / 2 + fpx * x / z; py = Hr / 2 - fpx * y / z; pz = z
        _raster(px, py, pz, Fc, Wr, Hr, zbuf, tid, b0, b1, off)
        allV.append(V); allF.append(Fc + voff); allN.append(N)
        allC.append(np.tile(np.asarray(rgb, float), (len(Fc), 1)))
        off += len(Fc); voff += len(V)
    V = np.concatenate(allV); F = np.concatenate(allF); N = np.concatenate(allN); C = np.concatenate(allC)
    img = np.empty((Hr, Wr, 3)); img[:] = np.asarray(bg, float)
    mask = tid >= 0
    t = tid[mask]; w0 = b0[mask]; w1 = b1[mask]; w2 = 1 - w0 - w1
    tri = F[t]
    n = N[tri[:, 0]] * w0[:, None] + N[tri[:, 1]] * w1[:, None] + N[tri[:, 2]] * w2[:, None]
    n /= np.linalg.norm(n, axis=1)[:, None] + 1e-12
    P = V[tri[:, 0]] * w0[:, None] + V[tri[:, 1]] * w1[:, None] + V[tri[:, 2]] * w2[:, None]
    vdir = P - eye; vdir /= np.linalg.norm(vdir, axis=1)[:, None]
    back = np.einsum('ij,ij->i', n, vdir) > 0
    n[back] *= -1
    lam = np.clip(n @ light, 0, 1)
    l2 = -f - 0.3 * u + 0.6 * r; l2 /= np.linalg.norm(l2)
    lam2 = np.clip(n @ l2, 0, 1)
    h = light - vdir; h /= np.linalg.norm(h, axis=1)[:, None]
    sp = np.clip(np.einsum('ij,ij->i', n, h), 0, 1) ** 60
    base = C[t]
    col = base * (ambient + 0.75 * lam + fill_light * lam2)[:, None] + 255 * spec * sp[:, None]
    if zebra > 0:
        # reflection-line stripes: reflect view dir, stripe on chosen world axis
        rv = vdir - 2 * np.einsum('ij,ij->i', vdir, n)[:, None] * n
        ax = np.asarray(zebra_axis if zebra_axis is not None else u, float); ax /= np.linalg.norm(ax)
        s_ = np.sin(np.arcsin(np.clip(rv @ ax, -1, 1)) * zebra)
        stripe = (s_ > 0).astype(float)
        col = col * (0.35 + 0.65 * stripe[:, None])
    col[back] *= 0.6
    img[mask] = np.clip(col, 0, 255)
    if edges:
        # depth-discontinuity + triangle-normal-crease edges
        zb = np.where(mask, zbuf, 1e9)
        dz = np.zeros_like(zb)
        dz[1:-1, 1:-1] = np.maximum.reduce([abs(zb[1:-1, 1:-1] - zb[:-2, 1:-1]), abs(zb[1:-1, 1:-1] - zb[2:, 1:-1]),
                                            abs(zb[1:-1, 1:-1] - zb[1:-1, :-2]), abs(zb[1:-1, 1:-1] - zb[1:-1, 2:])])
        rel = dz / np.where(np.isfinite(zb) & (zb < 1e8), zb, 1e9)
        e = rel > 0.02
        img[e] = img[e] * 0.25
    im = Image.fromarray(img.astype(np.uint8))
    if S > 1:
        im = im.resize((W, H), Image.LANCZOS)
    return im

def grid(imgs, cols=2, bg=(30, 30, 34)):
    w, h = imgs[0].size; rows = (len(imgs) + cols - 1) // cols
    g = Image.new('RGB', (w * cols, h * rows), bg)
    for k, im in enumerate(imgs):
        g.paste(im, ((k % cols) * w, (k // cols) * h))
    return g

def label(im, text, xy=(12, 10), fill=(255, 255, 255), size=22):
    from PIL import ImageDraw, ImageFont
    try:
        font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', size)
    except Exception:
        font = None
    ImageDraw.Draw(im).text(xy, text, fill=fill, font=font)
    return im

def fit_view(meshes, direction, up=(0, 1, 0), W=1400, H=1000, dist=3000.0, margin=0.06, iters=3):
    """camera on `direction` (from target to eye), auto fov + target so all vertices fit with a margin"""
    V = np.vstack([np.asarray(m.vertices) for m in meshes])
    d = np.asarray(direction, float); d /= np.linalg.norm(d)
    tgt = V.mean(0)
    for _ in range(iters):
        eye = tgt + d * dist
        e, r, u, f = look_at(eye, tgt, up)
        q = V - e; z = q @ f; x = (q @ r) / z; y = (q @ u) / z
        cx, cy = (x.max() + x.min()) / 2, (y.max() + y.min()) / 2
        # shift target so the projected bbox is centred
        tgt = tgt + (r * cx + u * cy) * (tgt - e) @ f
    eye = tgt + d * dist
    e, r, u, f = look_at(eye, tgt, up)
    q = V - e; z = q @ f; x = (q @ r) / z; y = (q @ u) / z
    hx = max(abs(x.max()), abs(x.min())) * (1 + margin); hy = max(abs(y.max()), abs(y.min())) * (1 + margin)
    t = max(hy, hx * H / W)
    fov = 2 * np.degrees(np.arctan(t))
    return eye, tgt, fov
