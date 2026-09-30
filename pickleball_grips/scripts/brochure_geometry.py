#!/usr/bin/env python3
"""Extra geometry and artwork for the per-design brochures.

    cutaway   quadrant cut through the grip (manifold3d boolean, cut faces coloured) -> render buffer
    paddle    an illustrative generic paddle whose handle is the reference bore      -> render buffer
    swatch    the unrolled surface as a lit relief picture (numpy shading, no renderer)
"""
import sys
from pathlib import Path

import numpy as np
import trimesh
from PIL import Image, ImageDraw
from scipy.ndimage import gaussian_filter
from shapely.geometry import Polygon, box
from shapely.ops import unary_union

sys.path.insert(0, str(Path(__file__).resolve().parent))
import render_grips as R  # noqa: E402
from grip_core import Frame  # noqa: E402

ROOT = R.ROOT
Z_TOP = 132.823


def bore_centre(F):
    r = F.ring
    return (r[:, 0].min() + r[:, 0].max()) / 2, (r[:, 1].min() + r[:, 1].max()) / 2


def _pack(out, parts):
    """parts = [(V, Fc, rgb)] with rgb a (3,) uint8 colour or (nv,3) array -> render buffer."""
    P, N, C = [], [], []
    for V, Fc, rgb in parts:
        V = np.asarray(V, float)
        nrm = R.corner_normals(V, Fc)
        col = np.broadcast_to(np.asarray(rgb, np.uint8), (len(Fc) * 3, 3)) if np.ndim(rgb) == 1 else np.asarray(rgb, np.uint8)[Fc.ravel()]
        P.append(V[Fc].reshape(-1, 3))
        N.append(nrm)
        C.append(col)
    R._write_bin(out, np.concatenate(P), np.concatenate(N), np.concatenate(C))


# ---------------------------------------------------------------------------------------------- cutaway
def make_cutaway(name, out, z0=-1.0, cap_grey=255, body_grey=205):
    """Half section: remove everything at x > centre above z0 and colour the new cut faces lighter than the skin, so the
    solid wall, floor and relief profile read as a section when seen from +x."""
    import manifold3d as m3d
    F = Frame()
    xm, ym = bore_centre(F)
    m = trimesh.load(ROOT / "stl" / f"{name}.stl", process=True)
    m.merge_vertices()
    base = m3d.Manifold(m3d.Mesh(np.asarray(m.vertices, np.float32), np.asarray(m.faces, np.uint32)))
    cutter = m3d.Manifold.cube((120, 240, 200)).translate((xm, ym - 120, z0))
    res = (base - cutter).to_mesh()
    V = np.asarray(res.vert_properties)[:, :3].astype(float)
    Fc = np.asarray(res.tri_verts).astype(np.int64)
    tri = V[Fc]
    n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
    tol = 2e-3
    cap = (np.abs(tri[:, :, 0] - xm) < tol).all(1) & (np.abs(n[:, 0]) > 0.99)
    # per-corner colours: cap triangles get their own (unshared) vertices so the colour does not bleed into the skin
    grey = np.where(cap, cap_grey, body_grey).astype(np.uint8)
    col = np.repeat(grey[:, None], 3, axis=1)
    col = np.repeat(col[:, None, :], 3, axis=1).reshape(-1, 3)
    Vf, Nf = V[Fc].reshape(-1, 3), np.repeat(n, 3, axis=0).astype(np.float32)
    smooth = R.corner_normals(V, Fc)
    Nf = np.where(np.repeat(cap, 3)[:, None], Nf, smooth)
    R._write_bin(out, Vf, Nf, col)
    return int(cap.sum())


# ---------------------------------------------------------------------------------------------- paddle
def _extrude_xz(poly, y0, y1, xm, ym):
    """Extrude a polygon drawn in the (x, z) plane to y in [ym+y0, ym+y1]."""
    m = trimesh.creation.extrude_polygon(poly, y1 - y0)            # polygon (u, v) -> (u, v, w), w in [0, h]
    V = np.asarray(m.vertices)
    V = np.column_stack([V[:, 0], V[:, 2] + ym + y0, V[:, 1]])       # (x, y, z) = (u, w, v)
    Fc = np.asarray(m.faces)[:, ::-1]                                # axis permutation flipped the handedness
    return V, Fc


def make_paddle(out, width=190.0, top=402.0):
    """Generic paddle: handle = the bore polygon, loft into a neck, rounded face with an edge guard."""
    F = Frame()
    xm, ym = bore_centre(F)
    bore = Polygon(F.ring).buffer(-0.12)
    ring = np.asarray(bore.exterior.coords)[:-1]
    parts = []
    # handle prism (starts inside the grip, pokes 6 mm out of the open throat)
    hv = trimesh.creation.extrude_polygon(bore, Z_TOP + 6.0 - 5.2)
    V = np.asarray(hv.vertices).copy()
    V[:, 2] += 5.2
    parts.append((V, np.asarray(hv.faces), np.array([92, 101, 114], np.uint8)))
    # throat: convex loft from the handle outline to a flat neck section
    z_a, z_b, neck_w, neck_t = Z_TOP + 1.0, 170.0, 40.0, 11.0
    pts = [(x, y, z_a) for x, y in ring]
    pts += [(xm + sx * neck_w / 2, ym + sy * neck_t / 2, z_b) for sx in (-1, 1) for sy in (-1, 1)]
    hull = trimesh.convex.convex_hull(np.array(pts))
    parts.append((np.asarray(hull.vertices), np.asarray(hull.faces), np.array([92, 101, 114], np.uint8)))
    # face outline (x, z): neck + rounded rectangle, concave joins rounded off
    face = box(xm - width / 2, 176.0, xm + width / 2, top)
    face = face.buffer(-46).buffer(46)                                    # round all corners
    neck = box(xm - neck_w / 2, 150.0, xm + neck_w / 2, 200.0)
    outline = unary_union([face, neck]).buffer(24).buffer(-24)
    rim = outline.difference(outline.buffer(-9.0))
    plate = outline.buffer(-9.0)
    for poly, t, rgb in ((rim, 15.4, (126, 136, 150)), (plate, 12.8, (46, 54, 66))):
        for g in (poly.geoms if hasattr(poly, "geoms") else [poly]):
            if g.is_empty or g.geom_type != "Polygon":
                continue
            V, Fc = _extrude_xz(g, -t / 2, t / 2, xm, ym)
            parts.append((V, Fc, np.array(rgb, np.uint8)))
    _pack(out, parts)
    return outline.bounds


# ---------------------------------------------------------------------------------------------- swatch
def relief_grid(name):
    """Height above the bore (mm) on the textured band: returns (H[z, S], z0, z1, L, holes)."""
    from designs import DESIGNS
    from generate_grips import evaluate
    F = Frame()
    fn = dict((n, f) for n, _, f in DESIGNS)[name]
    ctx, d = evaluate(F, fn, 0.25)
    z, H, nfoot = F.skin(d["t"], 0.25)
    pat = z[nfoot:nfoot + len(ctx.Z)]
    Hp = H[nfoot:nfoot + len(ctx.Z)]
    return Hp, float(pat[0]), float(pat[-1]), float(F.L), d.get("holes") or []


def make_swatch(name, tint_hex, out, px_per_mm=10.0, size_mm=86.0, s_start=10.0, z_top=112.0, exag=1.0):
    """Unrolled surface (S around, z up) as a lit relief picture: Lambert + cavity shading in the PLA tint, specular
    glints, and through-windows painted dark.  Returns the image size."""
    Hp, z0, z1, L, holes = relief_grid(name)
    nz, nS = Hp.shape
    ds, dz = L / nS, (z1 - z0) / (nz - 1)
    gz, gS = np.gradient(Hp, dz, ds)                                      # dH/dz (up), dH/dS (mm per mm)
    gz, gS = gz * exag, gS * exag                                         # exag > 1 exaggerates gentle relief
    Hf, gz, gS = Hp[::-1], gz[::-1], gS[::-1]                              # image rows run downward, z upward
    l = np.array([-0.55, 0.75, 0.9])
    n_dot_l = (-gS * l[0] - gz * l[1] + l[2]) / (np.sqrt(gS ** 2 + gz ** 2 + 1.0) * np.linalg.norm(l))
    lam = np.clip(n_dot_l, 0, 1)
    cav = (Hf - gaussian_filter(Hf, 6.0)) * exag                                   # crests lighter, valleys darker
    shade = 0.30 + 0.78 * lam + 0.55 * np.clip(cav, -0.6, 0.6)
    spec = np.clip((n_dot_l - 0.93) / 0.07, 0, 1) ** 2 * 0.35
    tint = np.array([int(tint_hex[i:i + 2], 16) for i in (0, 2, 4)], float)
    img = np.clip(tint[None, None, :] * shade[..., None] + 255 * spec[..., None], 0, 255)
    im = Image.fromarray(img.astype(np.uint8)).resize((int(round(nS * ds * px_per_mm)), int(round(nz * dz * px_per_mm))), Image.LANCZOS)
    x0, y0 = int(s_start * px_per_mm), int((z1 - z_top) * px_per_mm)
    w = h = int(size_mm * px_per_mm)
    crop = im.crop((x0, y0, x0 + w, y0 + h))
    if holes:
        dr = ImageDraw.Draw(crop)
        for hp in holes:
            for shift in (-L, 0.0, L):
                pts = [((x + shift - s_start) * px_per_mm, (z_top - y) * px_per_mm) for x, y in hp.exterior.coords]
                dr.polygon(pts, fill=(14, 17, 22))
    crop.save(out)
    return crop.size
