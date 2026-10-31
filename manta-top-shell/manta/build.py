"""Mesh generation for the MANTA top shell and its optional appendages."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import triangle as tr

from .curves import (catmull_rom, distance_to_polyline, gaussian_smooth_1d, polygon_area,
                     resample)
from .design import (ENDPLATE_HALF_T, ENDPLATE_TOP, ENDPLATE_X, ENDPLATE_Y, GURNEY_H,
                     HORN_CUT_X, MIRROR_C, MIRROR_HALF, WING_SPAN_HALF, MantaDesign, Variant)
from .mesh import Part, merge_parts, mirror_y

# Material names (shared with the viewer / exporters)
PAINT = "paint"
GLASS = "glass"
DARK = "carbon"
HEADLIGHT = "headlight"
TAILLIGHT = "taillight"
EDGE = "edge"
RUBBER = "tyre"
RIM = "rim"
FLOOR = "floor"
MARKING = "marking"
SPLITTER_Z = 70.0  # lowest lower-edge height: top of the (separate) splitter / floor


@dataclass
class ShellBuild:
    variant: Variant
    design: MantaDesign
    shell: Part  # crown + skirt (+ fin merged) - the top shell
    crown_half_outline: np.ndarray
    louvre_polys: list
    parts: dict  # name -> Part (shell components and appendages)


# ---------------------------------------------------------------------------
# crown: constrained Delaunay triangulation of the plan, lifted onto H(x, y)
# ---------------------------------------------------------------------------

def _interior_point(poly):
    """A point safely inside a simple polygon (centroid if inside, else nudged)."""
    from .curves import points_in_polygon
    c = poly.mean(axis=0)
    if points_in_polygon(c[None], poly)[0]:
        return c
    for t in np.linspace(0.1, 0.9, 41):
        p = poly[0] * (1 - t) + poly[len(poly) // 2] * t
        if points_in_polygon(p[None], poly)[0]:
            return p
    raise ValueError("no interior point found")


def _inner_rings(outline, V, S, offsets, min_gap):
    """Points offset inward from the outline, kept clear of every constraint."""
    from scipy.spatial import cKDTree

    from .curves import points_in_polygon

    tan = np.gradient(outline, axis=0)
    tan /= np.linalg.norm(tan, axis=1, keepdims=True)
    nrm = np.column_stack([-tan[:, 1], tan[:, 0]])
    closed = np.vstack([outline, outline[::-1][1:-1] * [1, 0]])  # outline + centre line
    inside_dir = np.where(points_in_polygon(outline + 2.0 * nrm, closed)[:, None], 1.0, -1.0)
    nrm = nrm * inside_dir
    cand = np.vstack([outline[3:-3] + d * nrm[3:-3] for d in offsets])
    keep = points_in_polygon(cand, closed) & (cand[:, 1] > min_gap)
    cand = cand[keep]
    # stay clear of all constraint segments (outline, glazing, livery, slots)
    a, bb = V[S[:, 0]], V[S[:, 1]]
    ab = bb - a
    ab2 = np.maximum((ab ** 2).sum(1), 1e-12)
    tree = cKDTree(0.5 * (a + bb))
    seg_len = np.sqrt(ab2).max()
    ok = np.ones(len(cand), bool)
    for i, p in enumerate(cand):
        idx = tree.query_ball_point(p, min_gap + seg_len)
        if not idx:
            continue
        aa, abv, ab2v = a[idx], ab[idx], ab2[idx]
        t = np.clip(((p - aa) * abv).sum(1) / ab2v, 0, 1)
        dmin = np.sqrt((((aa + t[:, None] * abv) - p) ** 2).sum(1)).min()
        ok[i] = dmin >= min_gap
    cand = cand[ok]
    # thin out points that crowd each other (concave corners)
    tree = cKDTree(cand)
    taken = np.zeros(len(cand), bool)
    out = []
    for i in range(len(cand)):
        if taken[i]:
            continue
        out.append(cand[i])
        for j in tree.query_ball_point(cand[i], min_gap):
            taken[j] = True
    return np.array(out)


def _loop_segments(start, n, closed=True):
    idx = np.arange(start, start + n)
    if closed:
        return np.column_stack([idx, np.roll(idx, -1)])
    return np.column_stack([idx[:-1], idx[1:]])


def _target_area(design: MantaDesign, cx, cy, h3):
    """Max 2-D triangle area so the lifted 3-D triangles stay near size h3."""
    gx, gy = design.grad_H(cx, cy)
    g2 = gx * gx + gy * gy
    e = 4.0
    hxx = (design.H(cx + e, cy) - 2 * design.H(cx, cy) + design.H(cx - e, cy)) / e ** 2
    hyy = (design.H(cx, cy + e) - 2 * design.H(cx, cy) + design.H(cx, cy - e)) / e ** 2
    kappa = (np.abs(hxx) + np.abs(hyy)) / (1.0 + g2) ** 1.5
    h_local = np.clip(np.minimum(h3, 0.30 / np.maximum(kappa, 1e-9)), 0.25 * h3, h3)
    h2 = h_local / np.sqrt(1.0 + g2)
    return 0.433 * h2 * h2


def build_crown(design: MantaDesign, h3=14.0, boundary_ds=7.0):
    v = design.v
    # ---- outline (right half) ---------------------------------------------
    dense, dparams = design.outline_half()
    pts, s_new = resample(dense, boundary_ds)
    s_dense = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(dense, axis=0), axis=1))])
    params = np.column_stack([np.interp(s_new, s_dense, dparams[:, k])
                              for k in range(dparams.shape[1])])
    sig = 30.0 / boundary_ds
    for k in range(params.shape[1]):
        params[:, k] = gaussian_smooth_1d(params[:, k], sig)
    pts[0, 1] = 0.0
    pts[-1, 1] = 0.0
    n_out = len(pts)

    # ---- centre line back from tail to mouth, honouring windscreen ends ----
    ws = design.windscreen_half()
    ws_pts, _ = resample(ws, 6.0)
    ws_pts[0] = ws[0]
    ws_pts[-1] = ws[-1]
    x_tail, x_lip = pts[-1, 0], pts[0, 0]
    special = sorted([ws_pts[0, 0], ws_pts[-1, 0]], reverse=True)
    n_cl = int(np.ceil((x_tail - x_lip) / boundary_ds))
    xs = list(np.linspace(x_tail, x_lip, n_cl + 1)[1:-1])
    for sx in special:
        xs = [x for x in xs if abs(x - sx) > 0.45 * boundary_ds]
    xs = np.array(sorted(xs + special, reverse=True))
    cl = np.column_stack([xs, np.zeros_like(xs)])

    verts = [pts, cl]
    segs = [_loop_segments(0, n_out + len(cl))]
    base = n_out + len(cl)
    # map windscreen ends onto the centre-line vertices
    cl_index = {round(x, 6): n_out + i for i, x in enumerate(xs)}

    # windscreen internal segments
    inner = ws_pts[1:-1]
    i0 = cl_index[round(ws_pts[0, 0], 6)]
    i1 = cl_index[round(ws_pts[-1, 0], 6)]
    idx = list(range(base, base + len(inner)))
    verts.append(inner)
    chain = [i0] + idx + [i1]
    segs.append(np.column_stack([chain[:-1], chain[1:]]))
    base += len(inner)

    # side window (closed internal loop)
    sw, _ = resample(design.side_window(), 6.0, closed=True)
    verts.append(sw)
    segs.append(_loop_segments(base, len(sw)))
    base += len(sw)

    # livery: shoulder chevron (closed internal loop)
    ch, _ = resample(design.chevron(), 8.0, closed=True)
    verts.append(ch)
    segs.append(_loop_segments(base, len(ch)))
    base += len(ch)

    # livery: cut line across the horn root (between two outline vertices)
    xc = v.mx(HORN_CUT_X)
    near_front = pts[:, 0] < v.mx(-820.0)
    cand_in = np.nonzero(near_front & (pts[:, 1] > 350) & (pts[:, 1] < 476))[0]
    cand_out = np.nonzero(near_front & (pts[:, 1] > 480) & (pts[:, 1] < 600))[0]
    i_in = cand_in[np.argmin(np.abs(pts[cand_in, 0] - xc))]
    i_out = cand_out[np.argmin(np.abs(pts[cand_out, 0] - xc))]
    segs.append(np.array([[i_in, i_out]]))

    # gill louvre holes
    holes = []
    louvres = []
    for poly in design.gill_slots():
        lp, _ = resample(poly, 3.0, closed=True)
        if polygon_area(lp) < 0:
            lp = lp[::-1]
        verts.append(lp)
        segs.append(_loop_segments(base, len(lp)))
        base += len(lp)
        holes.append(lp.mean(axis=0))
        louvres.append(lp)

    # Two regular rows of vertices just inside the outline: the crown then
    # meets the skirt through an orderly strip of triangles (no sawtooth
    # shading where the surface curves hardest, e.g. the horn tops).
    V2 = np.vstack(verts)
    S = np.vstack(segs)
    rings = _inner_rings(pts, V2, S, offsets=(0.55 * boundary_ds, 1.3 * boundary_ds),
                         min_gap=0.42 * boundary_ds)
    if len(rings):
        V2 = np.vstack([V2, rings])
    ws_seed = np.array([0.5 * (ws[0, 0] + ws[-1, 0]), 60.0])
    sw_seed = sw.mean(axis=0)
    body_seed = np.array([v.mx(2600.0), 700.0])
    ch_seed = _interior_point(ch)
    horn_seed = np.array([v.mx(-975.0), 478.0])
    regions = np.array([[body_seed[0], body_seed[1], 0, 0],
                        [ws_seed[0], ws_seed[1], 1, 0],
                        [sw_seed[0], sw_seed[1], 1, 0],
                        [ch_seed[0], ch_seed[1], 2, 0],
                        [horn_seed[0], horn_seed[1], 2, 0]], float)
    area0 = 0.433 * h3 * h3
    inp = dict(vertices=V2, segments=S, holes=np.array(holes), regions=regions)
    t = tr.triangulate(inp, f"pq30YAa{area0:.3f}")

    # adaptive refinement for steep / curved areas
    for _ in range(3):
        tv, tt = t["vertices"], t["triangles"]
        c = tv[tt].mean(axis=1)
        e1, e2 = tv[tt[:, 1]] - tv[tt[:, 0]], tv[tt[:, 2]] - tv[tt[:, 0]]
        a2 = np.abs(0.5 * (e1[:, 0] * e2[:, 1] - e1[:, 1] * e2[:, 0]))
        target = _target_area(design, c[:, 0], c[:, 1], h3)
        if np.all(a2 <= 1.15 * target):
            break
        t = tr.triangulate(dict(vertices=tv, triangles=tt, segments=t["segments"],
                                holes=np.array(holes), triangle_max_area=np.minimum(target, a2),
                                triangle_attributes=t["triangle_attributes"]), "rpq30YA")

    tv, tt = t["vertices"], t["triangles"]
    attr = t["triangle_attributes"][:, 0].astype(int)
    assert np.allclose(tv[:n_out], pts), "outline vertices were moved by the triangulator"
    z = design.H(tv[:, 0], tv[:, 1])
    V3 = np.column_stack([tv, z])
    # orient faces upward (+z normals)
    fn = np.cross(V3[tt[:, 1]] - V3[tt[:, 0]], V3[tt[:, 2]] - V3[tt[:, 0]])
    flip = fn[:, 2] < 0
    tt = tt.copy()
    tt[flip] = tt[flip][:, ::-1]
    mats = [PAINT, GLASS, MARKING]
    gx, gy = design.grad_H(tv[:, 0], tv[:, 1], eps=0.75)
    nrm = np.column_stack([-gx, -gy, np.ones_like(gx)])
    nrm /= np.linalg.norm(nrm, axis=1, keepdims=True)
    crown = Part("crown", V3, tt, attr, mats, normals=nrm)
    return crown, pts, params, louvres, (int(i_in), int(i_out))


# ---------------------------------------------------------------------------
# skirt: shoulder roll-over + wall down to the parting line, along the outline
# ---------------------------------------------------------------------------

def _outward_normals(pts):
    tan = np.gradient(pts, axis=0)
    tan /= np.linalg.norm(tan, axis=1, keepdims=True)
    # outline runs lip -> right side -> tail with the crown on the -y side of
    # the side portion, so the outward normal is the right-hand normal (t_y, -t_x)
    # rotated: for travel along +x on the right side the outward normal is +y.
    n = np.column_stack([-tan[:, 1], tan[:, 0]])
    # make sure it points away from the centre plane on the long sides
    probe = pts + 5.0 * n
    if np.mean(np.abs(probe[:, 1]) - np.abs(pts[:, 1])) < 0:
        n = -n
    n[0] = [-1.0, 0.0]
    n[-1] = [1.0, 0.0]
    return n


def skirt_profiles(design: MantaDesign, pts, params, rows=14, min_lip=8.0):
    """3-D skirt rows for every outline point -> array (N, rows, 3)."""
    n2 = _outward_normals(pts)
    out = np.empty((len(pts), rows, 3))
    z0s = design.H(pts[:, 0], pts[:, 1])
    zb_eff_all = np.empty(len(pts))
    for i, (p, n, prm) in enumerate(zip(pts, n2, params)):
        r_s, undercut, w, a_abs, d_rel = prm
        z0 = z0s[i]
        eps = 3.0
        g = (z0 - design.H(p[0] - n[0] * eps, p[1] - n[1] * eps)) / eps
        a0 = np.arctan(g)
        thw = -np.pi / 2 - np.radians(undercut)
        turn = max(a0 - thw, 0.0)
        # shoulder arc in (n, z)
        phi0 = a0 + np.pi / 2
        c = np.array([r_s * np.sin(a0), -r_s * np.cos(a0)])
        phis = np.linspace(phi0, phi0 - turn, 25)
        arc = c + r_s * np.column_stack([np.cos(phis), np.sin(phis)])
        zb = (1.0 - w) * a_abs + w * (z0 - d_rel)
        # wheel arches on the outer side walls; the arch never cuts into the
        # shoulder roll, so the fender always reaches its full plan width
        if abs(n[1]) > 0.55 and p[1] > 880.0:
            arch = max(design.front_arch_z(p[0]), design.rear_arch_z(p[0]))
            zb = max(zb, min(arch, z0 + arc[-1, 1] - 8.0))
        zb = max(zb, SPLITTER_Z)
        zb = min(zb, z0 - min_lip)
        zb_eff_all[i] = zb
        dir_w = np.array([np.cos(a0 - turn), np.sin(a0 - turn)])
        wall_len = max((arc[-1, 1] - (zb - z0 - 60.0)) / max(-dir_w[1], 0.2), 1.0)
        wall = arc[-1] + np.linspace(0, wall_len, 60)[1:, None] * dir_w
        prof = np.vstack([arc, wall])
        prof[:, 1] += z0
        # cut at the lower edge
        below = np.nonzero(prof[:, 1] <= zb)[0]
        k = below[0]
        f = (prof[k - 1, 1] - zb) / max(prof[k - 1, 1] - prof[k, 1], 1e-9)
        end = prof[k - 1] + f * (prof[k] - prof[k - 1])
        prof = np.vstack([prof[:k], end])
        # weighted resample: shoulder gets denser rows
        seg = np.linalg.norm(np.diff(prof, axis=0), axis=1)
        w = np.where(np.arange(len(seg)) < 24, 2.2, 1.0)
        s = np.concatenate([[0.0], np.cumsum(seg * w)])
        su = np.linspace(0.0, s[-1], rows)
        dn = np.interp(su, s, prof[:, 0])
        zz = np.interp(su, s, prof[:, 1])
        out[i, :, 0] = p[0] + n[0] * dn
        out[i, :, 1] = p[1] + n[1] * dn
        out[i, :, 2] = zz
        out[i, 0] = [p[0], p[1], z0]
    return out, n2, zb_eff_all


def build_shell_half(design: MantaDesign, h3=14.0, rows=14):
    crown, pts, params, louvres, (i_in, i_out) = build_crown(design, h3=h3)
    prof, n2, zb = skirt_profiles(design, pts, params, rows=rows)
    n_out = len(pts)
    nv = len(crown.vertices)
    # new vertices for rows 1.. ; row 0 is the crown boundary (indices 0..n_out-1)
    sk = prof[:, 1:, :].reshape(-1, 3)
    V = np.vstack([crown.vertices, sk])

    def vid(i, r):
        if r == 0:
            return i
        return nv + i * (rows - 1) + (r - 1)

    faces = []
    mats = []
    # material zones on the skirt: headlights on the leading edge below the
    # shoulder, tail-light strip on the trailing-edge lip
    v = design.v
    for i in range(n_out - 1):
        xm = 0.5 * (pts[i, 0] + pts[i + 1, 0])
        ym = 0.5 * (pts[i, 1] + pts[i + 1, 1])
        for r in range(rows - 1):
            a, b = vid(i, r), vid(i + 1, r)
            c, d = vid(i + 1, r + 1), vid(i, r + 1)
            faces.append([a, b, c])
            faces.append([a, c, d])
            m = 0
            frac = (r + 0.5) / (rows - 1)
            if i_in <= i < i_out:
                m = 5  # cephalic horn blades in the marking colour
            elif v.mx(-835.0) < xm < v.mx(-610.0) and 560 < ym < 860 and 0.25 < frac < 0.8:
                m = 2  # light blade along the pectoral leading edge
            elif xm > v.mx(3930.0) and 560 < ym < 905 and frac > 0.3:
                m = 3  # tail-light strip along the crescent trailing edge
            elif r == rows - 2:
                m = 4  # lower edge band (rendered darker)
            mats += [m, m]
    F = np.array(faces)
    M = np.array(mats)
    # orient skirt outward: compare with the 2-D outward normal at the shoulder
    fn = np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]])
    i_ref = n_out // 2
    ref_face = 2 * (i_ref * (rows - 1)) + 2 * (rows // 2)
    if np.dot(fn[ref_face, :2], n2[i_ref]) < 0:
        F = F[:, ::-1]
    allF = np.vstack([crown.faces, F])
    crown_m = np.array([0, 1, 5])[crown.face_mat]
    allM = np.concatenate([crown_m, M])
    mats_all = [PAINT, GLASS, HEADLIGHT, TAILLIGHT, EDGE, MARKING]
    half = Part("top_shell_skin", V, allF, allM, mats_all)
    nrm = half.vertex_normals()
    nrm[:nv] = crown.normals
    half.normals = nrm
    return half, pts, louvres, prof


def build_louvre_liners(design: MantaDesign, louvres, depth=28.0):
    """Dark slot walls below each gill slit (visual only; not in the CAD surface)."""
    V, F = [], []
    off = 0
    for lp in louvres:
        n = len(lp)
        z = design.H(lp[:, 0], lp[:, 1])
        top = np.column_stack([lp, z + 0.5])
        bot = np.column_stack([lp, z - depth])
        V += [top, bot]
        for i in range(n):
            j = (i + 1) % n
            F += [[off + i, off + j, off + n + j], [off + i, off + n + j, off + n + i]]
        off += 2 * n
    part = Part("louvre_liners", np.vstack(V), np.array(F), np.zeros(len(F), int), [EDGE])
    return mirror_y(part)


# ---------------------------------------------------------------------------
# thin "lens" blades: fin, endplates, mirror stalks
# ---------------------------------------------------------------------------

def lens_blade(profile, to3d, half_thickness, edge_round=7.0, max_area=60.0, name="blade",
               material=DARK, boundary_ds=5.0):
    """Closed thin body from a 2-D outline: faces at +/- thickness, sharp-free rim.

    ``to3d(u, v, w)`` maps profile coordinates + offset to design space.
    ``half_thickness(u, v)`` gives the half thickness away from the rim.
    """
    P, _ = resample(profile, boundary_ds, closed=True)
    if polygon_area(P) < 0:
        P = P[::-1]
    n = len(P)
    t = tr.triangulate(dict(vertices=P, segments=_loop_segments(0, n)), f"pq30Ya{max_area}")
    tv, tt = t["vertices"], t["triangles"]
    d = distance_to_polyline(tv, P, closed=True)
    d[:n] = 0.0
    w = half_thickness(tv[:, 0], tv[:, 1]) * np.sqrt(np.clip(d / edge_round, 0.0, 1.0))
    rim = np.arange(len(tv)) < n
    front = to3d(tv[:, 0], tv[:, 1], w)
    back_idx = np.arange(len(tv)) + len(tv)
    back_idx[rim] = np.nonzero(rim)[0]
    back = to3d(tv[:, 0], tv[:, 1], -w)
    V = np.vstack([front, back])
    F = np.vstack([tt, back_idx[tt][:, ::-1]])
    used = np.zeros(len(V), bool)
    used[F.ravel()] = True
    remap = np.cumsum(used) - 1
    V = V[used]
    F = remap[F]
    part = Part(name, V, F, np.zeros(len(F), int), [material])
    # make normals point outward (away from the mid plane)
    fn = part.face_normals()
    cen = V[F].mean(axis=1)
    mid = to3d(np.array([P[:, 0].mean()]), np.array([P[:, 1].mean()]), np.array([0.0]))[0]
    if np.mean(np.einsum("ij,ij->i", fn, cen - mid)) < 0:
        part.faces = part.faces[:, ::-1]
    return part


def build_fin(design: MantaDesign):
    prof = design.fin_profile()
    x_hi = prof[:, 0].max()

    def half_t(u, v):
        # 7 mm at the root tapering to 4 mm at the top / tail
        z_root = design.H(u, 0 * u)
        h = np.clip((v - z_root) / 260.0, 0.0, 1.0)
        tail = np.clip((u - (x_hi - 300.0)) / 300.0, 0.0, 1.0)
        return 7.0 - 3.0 * h - 2.0 * tail

    def to3d(u, v, w):
        return np.column_stack([u, w, v])

    return lens_blade(prof, to3d, half_t, edge_round=6.0, max_area=80.0, name="dorsal_fin",
                      material=DARK)


def build_endplate(design: MantaDesign, side=1):
    v = design.v
    xs = np.linspace(v.mx(ENDPLATE_X[0]), v.mx(ENDPLATE_X[1]), 80)
    zb = design.H(xs, np.full_like(xs, 958.0)) - 34.0
    top = np.array(ENDPLATE_TOP, float)
    tx, tz = v.mx(top[:, 0]), v.mz(top[:, 1])
    tp, _ = catmull_rom(np.column_stack([tx, tz]), 16)
    prof = np.vstack([np.column_stack([xs, zb])[::-1], tp[1:]])
    # bottom runs rear->front, then top front->rear (closed by the trailing edge)
    prof = np.vstack([np.column_stack([xs, zb]), tp[::-1][1:-1]])

    def to3d(u, vv, w):
        return np.column_stack([u, side * (ENDPLATE_Y + w * 0) + w, vv])

    return lens_blade(prof, to3d, lambda u, vv: np.full_like(u, ENDPLATE_HALF_T), edge_round=5.0,
                      max_area=60.0, name=f"endplate_{'r' if side > 0 else 'l'}", material=DARK)


def build_wing(design: MantaDesign, n_span=90, n_af=60):
    """Crescent rear wing main plane with Gurney, closed at the tips."""
    ys = WING_SPAN_HALF * np.sin(np.linspace(-np.pi / 2, np.pi / 2, n_span))
    secs = []
    meta = []
    for y in ys:
        X, Z, chord, x_le, z_le = design.wing_section(abs(y), n_af)
        secs.append(np.column_stack([X, np.full_like(X, y), Z]))
        meta.append((chord, x_le, z_le))
    S = np.array(secs)  # (n_span, n_loop, 3)
    ns, nl = S.shape[:2]
    V = S.reshape(-1, 3)
    F = []
    for i in range(ns - 1):
        for j in range(nl - 1):
            a = i * nl + j
            b = a + 1
            c = a + nl + 1
            d = a + nl
            F += [[a, b, c], [a, c, d]]
    # tip caps (fan to centroid)
    caps_v = []
    for i in (0, ns - 1):
        cen = S[i].mean(axis=0)
        ci = len(V) + len(caps_v)
        caps_v.append(cen)
        for j in range(nl - 1):
            a = i * nl + j
            F.append([ci, a + 1, a] if i == 0 else [ci, a, a + 1])
    V = np.vstack([V, np.array(caps_v)])
    F = np.array(F)
    part = Part("rear_wing", V, F, np.zeros(len(F), int), [DARK])
    cen = V.mean(axis=0)
    # orient outward (main plane is thin; use per-section centroid)
    fn = part.face_normals()
    fc = V[F].mean(axis=1)
    sec_c = S.mean(axis=1)
    near = sec_c[np.clip(np.searchsorted(ys, fc[:, 1]), 0, ns - 1)]
    if np.mean(np.einsum("ij,ij->i", fn[: len(F) - 2 * (nl - 1)], (fc - near)[: len(F) - 2 * (nl - 1)])) < 0:
        part.faces = part.faces[:, ::-1]
    # Gurney flap strip on the pressure (upper) side at the trailing edge
    gv, gf = [], []
    for k, y in enumerate(ys):
        X, Z, chord, x_le, z_le = design.wing_section(abs(y), n_af)
        te = np.array([X[0], y, Z[0]])
        a = np.radians(9.5)
        up = np.array([-np.sin(a), 0.0, np.cos(a)])
        back = np.array([np.cos(a), 0.0, np.sin(a)])
        gv += [te - 1.0 * back, te - 1.0 * back + GURNEY_H * up, te + 1.0 * back + GURNEY_H * up,
               te + 1.0 * back]
        if k:
            o = 4 * (k - 1)
            for q in range(3):
                a0, a1 = o + q, o + q + 1
                gf += [[a0, a1, a1 + 4], [a0, a1 + 4, a0 + 4]]
    gurney = Part("gurney", np.array(gv), np.array(gf), np.zeros(len(gf), int), [DARK])
    return merge_parts("rear_wing", [part, gurney])


def superellipsoid(center, half, n_u=48, n_v=24, e=0.55, taper=0.35):
    """Teardrop-ish pod: superellipsoid stretched in x with a tapering tail."""
    u = np.linspace(-np.pi, np.pi, n_u, endpoint=False)
    vv = np.linspace(-np.pi / 2, np.pi / 2, n_v)
    U, Vv = np.meshgrid(u, vv)

    def sp(w, m):
        return np.sign(w) * np.abs(w) ** m

    x = sp(np.cos(Vv), e) * sp(np.cos(U), e)
    y = sp(np.cos(Vv), e) * sp(np.sin(U), e)
    z = sp(np.sin(Vv), e)
    shrink = 1.0 - taper * np.clip(x, 0, 1)
    X = center[0] + half[0] * x
    Y = center[1] + half[1] * y * shrink
    Z = center[2] + half[2] * z * shrink
    P = np.column_stack([X.ravel(), Y.ravel(), Z.ravel()])
    F = []
    for i in range(n_v - 1):
        for j in range(n_u):
            a = i * n_u + j
            b = i * n_u + (j + 1) % n_u
            c = (i + 1) * n_u + (j + 1) % n_u
            d = (i + 1) * n_u + j
            F += [[a, b, c], [a, c, d]]
    return P, np.array(F)


def build_mirrors(design: MantaDesign):
    v = design.v
    parts = []
    for side in (1, -1):
        c = np.array([v.mx(MIRROR_C[0]), side * MIRROR_C[1], float(v.mz(MIRROR_C[2]))])
        P, F = superellipsoid(c, MIRROR_HALF)
        pod = Part("mirror_pod", P, F, np.zeros(len(F), int), [DARK])
        if side < 0:
            pod.faces = pod.faces[:, ::-1]
        fn = pod.face_normals()
        if np.mean(np.einsum("ij,ij->i", fn, P[F].mean(1) - c)) < 0:
            pod.faces = pod.faces[:, ::-1]
        # stalk: blade from the fender surface up into the pod
        x0, x1 = c[0] - 40.0, c[0] + 30.0
        yy = abs(c[1]) + 8.0
        zs0 = design.H(np.array([x0, x1]), np.array([yy, yy])) - 10.0
        prof = np.array([[x0, zs0[0]], [x1, zs0[1]], [x1 + 10, c[2] - 10], [x0 + 20, c[2] - 10]])

        def to3d(u, w2, w, s=side, yy=yy):
            return np.column_stack([u, s * yy + w, w2])

        stalk = lens_blade(prof, to3d, lambda u, w2: np.full_like(u, 5.0), edge_round=4.0,
                           max_area=30.0, name="mirror_stalk", material=DARK, boundary_ds=4.0)
        parts += [pod, stalk]
    return merge_parts("mirrors", parts)


# ---------------------------------------------------------------------------
# reference context (NOT part of the design): tyres, rims, floor
# ---------------------------------------------------------------------------

def build_context(design: MantaDesign):
    v = design.v
    rules = v.rules
    parts = []
    for (xw, zw, tyre, track) in ((0.0, v.wheel_z_front, rules.front_tyre, v.front_track),
                                  (v.x_rear_axle, v.wheel_z_rear, rules.rear_tyre, v.rear_track)):
        for side in (1, -1):
            yc = side * track / 2
            parts.append(_tyre(xw, yc, zw, tyre.radius, tyre.width))
            parts.append(_rim(xw, yc, zw, 229.0, tyre.width - 40.0, side))
    parts.append(_floor(design))
    ctx = merge_parts("context", parts, is_shell=False)
    return ctx


def _lathe(profile_rz, xc, yc, zc, n=96):
    """Revolve (r, w) profile about the lateral (y) axis through (xc, yc, zc)."""
    th = np.linspace(0, 2 * np.pi, n, endpoint=False)
    r = profile_rz[:, 0]
    w = profile_rz[:, 1]
    P = np.array([[xc + ri * np.cos(t), yc + wi, zc + ri * np.sin(t)] for t in th for ri, wi in zip(r, w)])
    m = len(r)
    F = []
    for i in range(n):
        for j in range(m - 1):
            a = i * m + j
            b = ((i + 1) % n) * m + j
            F += [[a, b, b + 1], [a, b + 1, a + 1]]
    return P, np.array(F)


def _tyre(xc, yc, zc, R, W):
    """Tyre with rounded shoulders (section: sidewall -> shoulder -> tread)."""
    rr = 45.0
    sec = [(R - 125.0, -W / 2 + 4.0)]
    for a in np.linspace(0.0, np.pi / 2, 10):  # inner shoulder
        sec.append((R - rr + rr * np.sin(a), -(W / 2 - rr) - rr * np.cos(a)))
    for a in np.linspace(0.0, np.pi / 2, 10):  # outer shoulder
        sec.append((R - rr + rr * np.cos(a), (W / 2 - rr) + rr * np.sin(a)))
    sec.append((R - 125.0, W / 2 - 4.0))
    P, F = _lathe(np.array(sec), xc, yc, zc)
    return Part("tyre", P, F, np.zeros(len(F), int), [RUBBER], is_shell=False)


def _rim(xc, yc, zc, R, W, side):
    w_out = side * (W / 2)
    sec = np.array([(R, -side * W / 2), (R, w_out), (R * 0.25, w_out - side * 25), (1.0, w_out - side * 30)])
    P, F = _lathe(sec, xc, yc, zc)
    return Part("rim", P, F, np.zeros(len(F), int), [RIM], is_shell=False)


def _floor(design: MantaDesign):
    v = design.v
    x0, x1 = v.x_front + 15, v.x_rear - 210
    plan = np.array([[x0, -560], [x0 + 40, -980], [x1 - 380, -985], [x1, -900], [x1, 900],
                     [x1 - 380, 985], [x0 + 40, 980], [x0, 560]])
    t = tr.triangulate(dict(vertices=plan, segments=_loop_segments(0, len(plan))), "pq30a20000")
    tv, tt = t["vertices"], t["triangles"]
    # flat floor with a diffuser ramp behind the rear axle
    def zf(x):
        return np.where(x > v.x_rear_axle - 300, 0.0 + 0.32 * np.clip(x - (v.x_rear_axle - 300), 0, None), 0.0)

    top = np.column_stack([tv, zf(tv[:, 0]) + 30.0])
    bot = np.column_stack([tv, zf(tv[:, 0])])
    n = len(tv)
    F = [tt, tt[:, ::-1] + n]
    # rim walls
    m = len(plan)
    rim = []
    for i in range(m):
        a, b = i, (i + 1) % m
        rim += [[a, b, b + n], [a, b + n, a + n]]
    F.append(np.array(rim))
    P = np.vstack([top, bot])
    return Part("floor", P, np.vstack(F), np.zeros(sum(len(f) for f in F), int), [FLOOR], is_shell=False)


# ---------------------------------------------------------------------------
# full build
# ---------------------------------------------------------------------------

def build_variant(variant: Variant, h3=14.0, rows=14) -> ShellBuild:
    design = MantaDesign(variant)
    half, pts, louvres, prof = build_shell_half(design, h3=h3, rows=rows)
    skin = mirror_y(half)
    fin = build_fin(design)
    shell = merge_parts("top_shell", [skin, fin])
    parts = {
        "top_shell_skin": skin,
        "dorsal_fin": fin,
        "louvre_liners": build_louvre_liners(design, louvres),
        "rear_wing": build_wing(design),
        "endplates": merge_parts("endplates", [build_endplate(design, 1), build_endplate(design, -1)]),
        "mirrors": build_mirrors(design),
        "context": build_context(design),
    }
    louvres_full = louvres + [np.column_stack([p[:, 0], -p[:, 1]]) for p in louvres]
    return ShellBuild(variant, design, shell, pts, louvres_full, parts)
