"""Trace the OEM i20 N inner door handle and the strap face from photos (v3).

Inputs (ref/):
    oem_handle_front_LH.webp  OEM handle, cabin side. Red loop = visible face
                              as drawn on the OEM part (used to place the face)
    oem_handle_back_LH.webp   OEM handle, rear. Red loop = housing outline
    oem_handle_aespares.webp  OEM handle, clean frontal photo (shown upside
                              down: a vertical flip gives the LH cabin view)
    incar_front_closeup.webp  strap plate fitted in the car, seen from the
                              front of the door        } red loop = outline
    incar_rear_oblique.webp   the same, seen from the  } of the plate
                              rear, looking down       }

Output: cad/oem_trace.json and renders/oem_trace_overlay.png.  Native frame =
RH unit seen from the cabin: X right = REAR of the car, Z up, millimetres.

How the face outline is obtained (v3)
  1. The ribs on the plate are straight, parallel and horizontal.  A ridge
     filter + Hough transform finds them in both in-car photos and gives the
     horizontal vanishing point of each photo.
  2. With a phone-camera model (focal FOCAL_PX, principal point at the image
     centre) every red loop is projected onto the plate plane.  The plate tilt
     about the rib direction is solved so that both photos give the same shape.
  3. The two rectified loops are averaged and placed on the OEM handle with a
     similarity fit to the visible-face loop drawn on the OEM photo, keeping the
     lower edge at least RIM_MARGIN inside the OEM rim traced on photo 9.

SCALE: the photos carry no ruler.  The default 7.0 px/mm on the front OEM photo
comes from standard parts (clip heads ~7 mm, pivot pin ~3 mm, screw cap ~17 mm)
and is confirmed by the AE Spares photo, which registers onto it with a
similarity transform within ~2 mm.  Measure the real handle and re-run with
    --overall MM   overall length, lower-left "chin" to tip of the front clip
    --height  MM   tip of the top clip to tip of the bottom clip
FACE: --focal PX changes the camera model (default 1350 px, ~32 mm equivalent;
best agreement with the OEM face loop), --face-length MM forces the face length
once you have measured the opening in your door card.
usage: python oem_trace.py [--overall 185] [--height 91] [--focal 1350]
"""
import argparse
import json
import math
import os

import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from scipy.interpolate import splev, splprep
from scipy.optimize import minimize
from scipy.spatial import cKDTree
from skimage import draw, exposure, filters, measure, morphology, transform

HERE = os.path.dirname(os.path.abspath(__file__))
REF = os.path.join(HERE, "..", "ref")
FRONT = os.path.join(REF, "oem_handle_front_LH.webp")
BACK = os.path.join(REF, "oem_handle_back_LH.webp")
AES = os.path.join(REF, "oem_handle_aespares.webp")
CAR_F = os.path.join(REF, "incar_front_closeup.webp")
CAR_R = os.path.join(REF, "incar_rear_oblique.webp")
DEFAULT_PX_PER_MM = 7.0
FOCAL_PX = 1350.0          # in-car photos (823 x 1463 px)
RIM_MARGIN = 2.0           # face lower edge stays this far inside the OEM rim
GROOVE_EDGE = 9.0          # groove centre lines stay this far inside the face

# Hand-measured features in the FRONT OEM photo (pixels), see overlay image
CAP_CENTRE_PX = (628.0, 808.0)        # square screw cap -> door-card screw
CAP_SIZE_PX = (120.0, 135.0)
PIVOT_PIN_PX = (1057.0, 532.0)        # top end of the stainless pivot pin
PIVOT_BOSS_PX = (1048.0, 1003.0)      # lower pivot boss
# clip protrusion beyond the housing frame edge (front photo, pixels)
CLIP_LEN_PX = {"top": 57.0, "bottom": 56.0, "front": 62.0, "rear": 45.0}

# In-car photos: strap / N-lever regions hidden from the rib detector (px)
OCCLUDERS = {
    "front": [[(160, 770), (452, 775), (456, 872), (160, 866)],
              [(442, 752), (668, 742), (670, 872), (442, 885)]],
    "rear": [[(300, 712), (330, 712), (470, 800), (470, 890), (330, 890)],
             [(375, 620), (500, 630), (470, 720), (400, 730), (370, 700)]],
}
RIB_ANGLES = {"front": (-15.0, 15.0), "rear": (-40.0, -12.0)}   # deg


# =============================================================================
# image helpers
# =============================================================================

def load(path):
    return np.asarray(Image.open(path).convert("RGB")).astype(int)


def red_mask(im):
    r, g, b = im[..., 0], im[..., 1], im[..., 2]
    return (r > 160) & (r - g > 80) & (r - b > 80)


def red_loop(im):
    """Centre-line of the hand-drawn red loop as an ordered (x, y) array."""
    m = morphology.remove_small_objects(red_mask(im), max_size=200)
    sk = morphology.skeletonize(morphology.closing(m, morphology.disk(3)))
    nb = ndi.convolve(sk.astype(int), np.ones((3, 3), int), mode="constant")
    ends = np.argwhere(sk & (nb == 2))
    if len(ends) >= 2:                       # close the pen gap
        (r0, c0), (r1, c1) = ends[0], ends[-1]
        rr, cc = draw.line(r0, c0, r1, c1)
        sk[rr, cc] = True
    filled = ndi.binary_fill_holes(morphology.dilation(sk, morphology.disk(1)))
    cs = sorted(measure.find_contours(filled.astype(float), 0.5), key=len)
    c = cs[-1]
    return np.column_stack([c[:, 1], c[:, 0]])          # x, y


def silhouette(im):
    nonwhite = (im.min(axis=2) < 200) | red_mask(im)
    nonwhite = morphology.closing(nonwhite, morphology.disk(4))
    nonwhite = ndi.binary_fill_holes(nonwhite)
    lab = measure.label(nonwhite)
    big = lab == max(measure.regionprops(lab), key=lambda p: p.area).label
    big = morphology.opening(big, morphology.disk(2))
    c = max(measure.find_contours(big.astype(float), 0.5), key=len)
    return np.column_stack([c[:, 1], c[:, 0]])


def silhouette_watermarked(im):
    """Part silhouette on a white background with a light watermark + logo."""
    blue = im[..., 2] > im[..., 0] + 40
    part = (im.min(axis=2) < 170) & ~blue
    part = ndi.binary_fill_holes(morphology.closing(part, morphology.disk(5)))
    lab = measure.label(part)
    big = lab == max(measure.regionprops(lab), key=lambda p: p.area).label
    big = morphology.opening(big, morphology.disk(3))
    c = max(measure.find_contours(big.astype(float), 0.5), key=len)
    return np.column_stack([c[:, 1], c[:, 0]])


def smooth_loop(xy, n=260, s_per_pt=6.0):
    xy = xy[::2]
    tck, _ = splprep([xy[:, 0], xy[:, 1]], s=len(xy) * s_per_pt, per=1)
    u = np.linspace(0, 1, n, endpoint=False)
    x, y = splev(u, tck)
    return np.column_stack([x, y])


def resample(xy, n):
    xy = np.vstack([xy, xy[:1]])
    d = np.r_[0, np.cumsum(np.linalg.norm(np.diff(xy, axis=0), axis=1))]
    t = np.linspace(0, d[-1], n, endpoint=False)
    return np.column_stack([np.interp(t, d, xy[:, 0]), np.interp(t, d, xy[:, 1])])


def poly_mask(shape, pts):
    rr, cc = draw.polygon([p[1] for p in pts], [p[0] for p in pts], shape)
    m = np.zeros(shape, bool)
    m[rr, cc] = True
    return m


def extremes(sil, band=28):
    x, y = sil[:, 0], sil[:, 1]
    top = sil[y < y.min() + band]
    bot = sil[y > y.max() - band]
    left = sil[x < x.min() + band]
    right = sil[x > x.max() - band]
    return dict(top=(top[:, 0].mean(), y.min(), np.ptp(top[:, 0])),
                bottom=(bot[:, 0].mean(), y.max(), np.ptp(bot[:, 0])),
                left=(x.min(), left[:, 1].mean(), np.ptp(left[:, 1])),
                right=(x.max(), right[:, 1].mean(), np.ptp(right[:, 1])))


def tip(sil, xr, yr, mode, band=12):
    """Clip tip (x, y, width) inside a search window of a silhouette."""
    s = sil[(sil[:, 0] >= xr[0]) & (sil[:, 0] <= xr[1]) &
            (sil[:, 1] >= yr[0]) & (sil[:, 1] <= yr[1])]
    if mode in ("top", "bottom"):
        j = np.argmin(s[:, 1]) if mode == "top" else np.argmax(s[:, 1])
        sel = s[np.abs(s[:, 1] - s[j, 1]) < band]
        return sel[:, 0].mean(), s[j, 1], np.ptp(sel[:, 0])
    j = np.argmin(s[:, 0]) if mode == "left" else np.argmax(s[:, 0])
    sel = s[np.abs(s[:, 0] - s[j, 0]) < band]
    return s[j, 0], sel[:, 1].mean(), np.ptp(sel[:, 1])


def front_left_pin(sil):
    """The small pin on the left flank (not the lower-left chin)."""
    sel = sil[(sil[:, 1] > 695) & (sil[:, 1] < 760) & (sil[:, 0] < 205)]
    return sel[:, 0].min(), sel[:, 1].mean(), np.ptp(sel[:, 1])


def back_right_clip(sil):
    """Arrow clip on the right flank of the back view (not the cup's end)."""
    sel = sil[(sil[:, 1] < 450) & (sil[:, 0] > 1445)]
    return sel[:, 0].max(), sel[:, 1].mean(), np.ptp(sel[:, 1])


def dark_square(im, box):
    """Centre and size of the dark rounded-square screw cap inside box."""
    x0, y0, x1, y1 = box
    g = im[y0:y1, x0:x1].mean(axis=2)
    dark = morphology.remove_small_objects(g < np.percentile(g, 6), max_size=40)
    p = max(measure.regionprops(measure.label(dark)), key=lambda q: q.area)
    r0, c0, r1, c1 = p.bbox
    return (x0 + 0.5 * (c0 + c1), y0 + 0.5 * (r0 + r1)), (c1 - c0, r1 - r0)


def similarity(src, dst):
    """Least-squares similarity src -> dst; returns (M 2x2, t, residuals)."""
    A, b = [], []
    for (x, y), (u, v) in zip(src, dst):
        A += [[x, -y, 1, 0], [y, x, 0, 1]]
        b += [u, v]
    (a, c, tx, ty), *_ = np.linalg.lstsq(np.array(A, float), np.array(b, float),
                                         rcond=None)
    M, t = np.array([[a, -c], [c, a]]), np.array([tx, ty])
    res = [np.asarray(d) - (M @ np.asarray(s) + t) for s, d in zip(src, dst)]
    return M, t, res


# =============================================================================
# in-car photos: ribs, vanishing point, rectification
# =============================================================================

def rib_lines(im, loop, occluders, ang):
    """Rib-crest line segments (y = a x + b) on the plate inside the loop."""
    H, W = im.shape[:2]
    m = morphology.erosion(poly_mask((H, W), [tuple(p) for p in loop]),
                           morphology.disk(3))
    m &= ~morphology.dilation(red_mask(im), morphology.disk(5))
    for P in occluders:
        m &= ~poly_mask((H, W), P)
    eq = exposure.equalize_adapthist(np.clip(im.mean(axis=2) / 255.0, 0, 1),
                                     clip_limit=0.025, kernel_size=40)
    rid = filters.sato(eq, sigmas=[1.5, 2.5], black_ridges=False)
    bw = morphology.remove_small_objects((rid > np.percentile(rid[m], 80)) & m,
                                         max_size=25)
    sk = morphology.skeletonize(bw)
    th = np.deg2rad(np.linspace(ang[0], ang[1], int((ang[1] - ang[0]) * 8) + 1))
    hs, t, d = transform.hough_line(sk, theta=th + np.pi / 2)
    ys, xs = np.nonzero(sk)
    lines = []
    for _, a, dist in zip(*transform.hough_line_peaks(
            hs, t, d, num_peaks=30, min_distance=5, min_angle=2,
            threshold=0.3 * hs.max())):
        sel = np.abs(xs * np.cos(a) + ys * np.sin(a) - dist) < 1.5
        if sel.sum() < 15:
            continue
        (k, b), *_ = np.linalg.lstsq(np.column_stack([xs[sel], np.ones(sel.sum())]),
                                     ys[sel], rcond=None)
        lines.append((float(k), float(b), float(xs[sel].min()),
                      float(xs[sel].max())))
    return lines


def vanishing_point(lines, thr_deg=1.0, iters=5):
    L = np.array([[k, -1.0, b] for k, b, _, _ in lines])
    w = np.array([x1 - x0 for _, _, x0, x1 in lines])
    keep = np.ones(len(L), bool)
    for _ in range(iters):
        Ln = L / np.linalg.norm(L[:, :2], axis=1)[:, None]
        sw = np.sqrt(w[keep])[:, None]
        v, *_ = np.linalg.lstsq(Ln[keep, :2] * sw, -Ln[keep, 2] * sw[:, 0],
                                rcond=None)
        err = []
        for k, b, x0, x1 in lines:
            xm = 0.5 * (x0 + x1)
            ym = k * xm + b
            e = math.degrees(math.atan(k) - math.atan2(v[1] - ym, v[0] - xm))
            err.append((e + 90) % 180 - 90)
        keep = np.abs(np.array(err)) < thr_deg
    return v, np.array(err), keep


class PlateCam:
    """Pinhole camera looking at the (planar) strap plate."""

    def __init__(self, f, vp, size, psi=0.0):
        self.f, self.vp, (self.W, self.H) = f, np.asarray(vp, float), size
        self.set_psi(psi)

    def set_psi(self, psi):
        f, cx, cy = self.f, self.W / 2, self.H / 2
        self.K = np.array([[f, 0, cx], [0, f, cy], [0, 0, 1.0]])
        self.Ki = np.linalg.inv(self.K)
        d = self.Ki @ np.r_[self.vp, 1]
        d /= np.linalg.norm(d)
        if self.vp[0] < cx:
            d = -d                        # +u = image right = front of the car
        y = np.r_[0, 1.0, 0]
        e2 = y - (y @ d) * d
        e2 /= np.linalg.norm(e2)
        n0 = np.cross(d, e2)
        self.eu = d
        self.ev = math.cos(psi) * e2 + math.sin(psi) * n0     # plate "down"
        self.n = np.cross(self.eu, self.ev)
        self.psi = psi

    def to_plate(self, xy):
        r = (self.Ki @ np.column_stack([xy, np.ones(len(xy))]).T).T
        s = r @ self.n
        if np.mean(s) < 0:
            self.n, s = -self.n, -s
        X = r / s[:, None]
        return np.column_stack([X @ self.eu, -(X @ self.ev)])   # z up

    def to_image(self, uz):
        X = (uz[:, :1] * self.eu + (-uz[:, 1:2]) * self.ev + self.n)
        p = (self.K @ X.T).T
        return p[:, :2] / p[:, 2:3]


def _rot(a):
    return np.array([[math.cos(a), -math.sin(a)], [math.sin(a), math.cos(a)]])


def fit_similarity_curves(A, B, iters=60, rotate=True):
    """Similarity (s, R, t) moving curve B onto curve A (closest points)."""
    s_tot, R_tot, t_tot = 1.0, np.eye(2), np.zeros(2)
    Bc = B.copy()
    ta = cKDTree(A)
    for _ in range(iters):
        i = cKDTree(Bc).query(A)[1]
        j = ta.query(Bc)[1]
        P = np.vstack([A, A[j]])
        Q = np.vstack([Bc[i], Bc])
        Pm, Qm = P.mean(0), Q.mean(0)
        Pc, Qc = P - Pm, Q - Qm
        if rotate:
            U, S, Vt = np.linalg.svd(Qc.T @ Pc)
            D = np.diag([1.0, np.sign(np.linalg.det(Vt.T @ U.T))])
            R = Vt.T @ D @ U.T                         # proper rotation only
            s = (S * np.diag(D)).sum() / (Qc ** 2).sum()
        else:
            R, s = np.eye(2), (Qc * Pc).sum() / (Qc ** 2).sum()
        t = Pm - s * R @ Qm
        Bc = (Bc @ R.T) * s + t
        s_tot, R_tot, t_tot = s * s_tot, R @ R_tot, s * R @ t_tot + t
    return s_tot, R_tot, t_tot


def curve_rms(A, B):
    d1 = cKDTree(A).query(B)[0]
    d2 = cKDTree(B).query(A)[0]
    return float(np.sqrt(np.mean(np.r_[d1, d2] ** 2)))


def shape_mismatch(A, B):
    """Shape difference after normalising position/scale (no rotation)."""
    def nrm(S):
        S = S - S.mean(0)
        return S / np.sqrt((S ** 2).sum(1).mean())
    A, B = nrm(A), nrm(B)
    s, R, t = fit_similarity_curves(A, B, iters=12, rotate=False)
    return curve_rms(A, B * s + t)


def rectify_pair(loops, vps, sizes, f):
    """Solve the plate tilt in both photos so that they agree; return cams."""
    cams = {k: PlateCam(f, vps[k], sizes[k]) for k in loops}

    def cost(q):
        cams["rear"].set_psi(q[0])
        cams["front"].set_psi(q[1])
        return shape_mismatch(cams["front"].to_plate(loops["front"]),
                              cams["rear"].to_plate(loops["rear"]))
    best = min(((cost((a, b)), a, b) for a in np.radians(np.arange(-40, 41, 10))
                for b in np.radians(np.arange(-30, 31, 10))))
    r = minimize(cost, best[1:], method="Nelder-Mead",
                 options=dict(xatol=1e-4, fatol=1e-7))
    cams["rear"].set_psi(r.x[0])
    cams["front"].set_psi(r.x[1])
    return cams, float(r.fun)


def mean_loop(A, B, n=400):
    """Average of two similar closed curves (B already aligned onto A)."""
    A = resample(A, n)
    Bm = B[cKDTree(B).query(A)[1]]
    k = 170.0 / np.ptp(A[:, 0])            # smooth at ~mm scale
    return smooth_loop(0.5 * (A + Bm) * k, n=n, s_per_pt=0.02) / k


def place_face(shape, target, rim, margin, x_range, length=None):
    """Place the rectified plate outline on the OEM handle.

    * ribs stay horizontal (along the handle): no rotation
    * length = length of the visible-face loop drawn on the OEM photo
      (or `length` if given), centred on that loop
    * lower edge sits `margin` inside the OEM rim z = rim[0] + rim[1] * x
    """
    L = length or float(np.ptp(target[:, 0]))
    S = shape * (L / np.ptp(shape[:, 0]))
    S = S + [0.5 * (target[:, 0].max() + target[:, 0].min())
             - 0.5 * (S[:, 0].max() + S[:, 0].min()), 0.0]
    sel = (S[:, 0] > x_range[0]) & (S[:, 0] < x_range[1])
    gap = S[sel, 1] - (rim[0] + rim[1] * S[sel, 0])
    F = S + [0.0, margin - gap.min()]
    scale = L / np.ptp(shape[:, 0])
    t = F[0] - shape[0] * scale
    return F, dict(scale=float(scale), length_mm=round(L, 2),
                   rms_to_oem_loop=round(curve_rms(target, F), 2),
                   lower_edge_above_rim_mm=margin), (scale, t)


def clusters(v, tol=1.6):
    v = sorted(v)
    out = [[v[0]]]
    for x in v[1:]:
        if x - out[-1][-1] < tol:
            out[-1].append(x)
        else:
            out.append([x])
    return [float(np.mean(c)) for c in out]


def rib_lattice(z, p_range=(8.5, 13.0)):
    """Uniform pitch + phase that best explains the rib-crest heights."""
    z = np.asarray(z, float)
    best = None
    for p in np.arange(p_range[0], p_range[1], 0.02):
        for ph in np.arange(0.0, p, 0.05):
            d = (z - ph + p / 2) % p - p / 2
            c = np.minimum(d * d, 4.0).sum()
            if best is None or c < best[0]:
                best = (c, p, ph, d)
    return float(best[1]), float(best[2]), best[3]


# =============================================================================
# main
# =============================================================================

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--overall", type=float, help="measured overall length mm")
    ap.add_argument("--height", type=float, help="measured clip-to-clip height mm")
    ap.add_argument("--focal", type=float, default=FOCAL_PX,
                    help="in-car photo focal length, px (sets face aspect)")
    ap.add_argument("--face-length", type=float,
                    help="force the face length (mm), e.g. measured door-card opening")
    a = ap.parse_args()

    # ---- 1. OEM front + back photos (v2 frame) -----------------------------
    f_im, b_im = load(FRONT), load(BACK)
    face_px = smooth_loop(red_loop(f_im))
    body_px_b = smooth_loop(red_loop(b_im))
    sil_f, sil_b = silhouette(f_im), silhouette(b_im)
    ef, eb = extremes(sil_f), extremes(sil_b)
    lp = front_left_pin(sil_f)
    eb["right"] = back_right_clip(sil_b)

    # mirror registration back -> front: x_f = A - s*x_b, y_f = B + s*y_b
    rows, rhs = [], []

    def eq_x(xf, xb):
        rows.append([1, 0, -xb])
        rhs.append(xf)

    def eq_y(yf, yb):
        rows.append([0, 1, yb])
        rhs.append(yf)
    eq_x(ef["top"][0], eb["top"][0]); eq_y(ef["top"][1], eb["top"][1])
    eq_x(ef["bottom"][0], eb["bottom"][0]); eq_y(ef["bottom"][1], eb["bottom"][1])
    eq_x(ef["right"][0], eb["left"][0]); eq_y(ef["right"][1], eb["left"][1])
    eq_x(lp[0], eb["right"][0]); eq_y(lp[1], eb["right"][1])
    (A, B, s), *_ = np.linalg.lstsq(np.array(rows, float),
                                    np.array(rhs, float), rcond=None)
    resid = np.array(rows, float) @ np.array([A, B, s]) - np.array(rhs)
    body_px = np.column_stack([A - s * body_px_b[:, 0], B + s * body_px_b[:, 1]])

    overall_px = ef["right"][0] - sil_f[:, 0].min()
    height_px = ef["bottom"][1] - ef["top"][1]
    k = DEFAULT_PX_PER_MM
    if a.overall:
        k = overall_px / a.overall
    elif a.height:
        k = height_px / a.height
    x0 = 0.5 * (face_px[:, 0].min() + face_px[:, 0].max())
    z0 = 0.5 * (face_px[:, 1].min() + face_px[:, 1].max())

    def to_lh(xy):          # LH cabin view, mm: x right = FRONT of car, z up
        xy = np.atleast_2d(np.asarray(xy, float))
        return np.column_stack([(xy[:, 0] - x0) / k, (z0 - xy[:, 1]) / k])

    def lh_to_px(P):
        return np.column_stack([x0 + k * P[:, 0], z0 - k * P[:, 1]])

    # ---- 2. AE Spares photo: same handle, registered onto the front photo --
    a_im = load(AES)
    Ha = a_im.shape[0]
    sil_a = silhouette_watermarked(a_im)
    flip = lambda p: (p[0], Ha - 1 - p[1])          # noqa: E731
    ta = tip(sil_a, (560, 720), (950, 1100), "bottom")   # -> top clip (LH)
    ba = tip(sil_a, (560, 720), (150, 300), "top")       # -> bottom clip (LH)
    ra = tip(sil_a, (1400, 1600), (450, 750), "right")   # -> front clip
    pa = tip(sil_a, (40, 140), (620, 690), "left")       # -> rear pin
    cap_a, cap_a_size = dark_square(a_im, (480, 380, 820, 700))
    src = [flip(ta), flip(ba), flip(ra), flip(cap_a), flip(pa)]
    dst = [ef["top"][:2], ef["bottom"][:2], ef["right"][:2], CAP_CENTRE_PX, lp[:2]]
    Ma, tA, res_a = similarity(src, dst)
    a_to_f = lambda P: np.column_stack(                      # noqa: E731
        [P[:, 0], Ha - 1 - P[:, 1]]) @ Ma.T + tA
    f_to_a = lambda P: (lambda q: np.column_stack(           # noqa: E731
        [q[:, 0], Ha - 1 - q[:, 1]]))((P - tA) @ np.linalg.inv(Ma).T)
    scale_a = float(np.hypot(*Ma[:, 0]))
    # OEM rim (outer edge of the straight flange, top edge of photo 9) ->
    # the lower edge of the visible face in the LH view
    rim = []
    for xx in range(150, 1000, 10):
        if 560 <= xx <= 720:
            continue                                   # clip
        col = sil_a[np.abs(sil_a[:, 0] - xx) < 1.0]
        col = col[col[:, 1] < 400]
        if len(col):
            rim.append((xx, col[:, 1].min()))
    rim_lh = to_lh(a_to_f(np.array(rim, float)))
    rim_fit = np.polyfit(rim_lh[:, 0], rim_lh[:, 1], 1)[::-1]   # z = c0 + c1 x

    # ---- 3. in-car photos: rectify the plate outline -----------------------
    ims = {"front": load(CAR_F), "rear": load(CAR_R)}
    loops, ribs, vps, sizes, vp_info = {}, {}, {}, {}, {}
    for key, im in ims.items():
        raw = red_loop(im)
        loops[key] = resample(smooth_loop(raw, n=400, s_per_pt=2.0), 400)
        ribs[key] = rib_lines(im, raw, OCCLUDERS[key], RIB_ANGLES[key])
        v, err, keep = vanishing_point(ribs[key])
        vps[key], sizes[key] = v, (im.shape[1], im.shape[0])
        vp_info[key] = dict(vp_px=[round(float(q), 1) for q in v],
                            lines_used=int(keep.sum()), lines=len(keep),
                            rms_deg=round(float(np.sqrt(np.mean(err[keep] ** 2))), 2))
    cams, mismatch = rectify_pair(loops, vps, sizes, a.focal)
    P_f = cams["front"].to_plate(loops["front"])
    P_r = cams["rear"].to_plate(loops["rear"])
    s_r, R_r, t_r = fit_similarity_curves(P_f, P_r)
    P_r_on_f = (P_r @ R_r.T) * s_r + t_r
    mean_shape = mean_loop(P_f, P_r_on_f)

    face_v2_lh = to_lh(face_px)
    face_lh, fit, (sc, tr) = place_face(
        mean_shape, face_v2_lh, rim_fit, RIM_MARGIN,
        (rim_lh[:, 0].min(), rim_lh[:, 0].max()), a.face_length)
    plate_to_lh = lambda U: U * sc + tr                       # noqa: E731
    lh_to_plate = lambda P: (P - tr) / sc                     # noqa: E731
    front_lh = plate_to_lh(P_f)
    rear_lh = plate_to_lh(P_r_on_f)
    # rib-crest heights on the plate (mm, LH frame)
    rib_z = {}
    for key in ims:
        zs = []
        for kk, b, xa, xb in ribs[key]:
            xm = np.linspace(xa, xb, 5)
            U = cams[key].to_plate(np.column_stack([xm, kk * xm + b]))
            if key == "rear":
                U = (U @ R_r.T) * s_r + t_r
            zs.append(float(np.median(plate_to_lh(U)[:, 1])))
        rib_z[key] = sorted(round(z, 1) for z in zs)
    # highlight + shadow edge of one rib are ~3 mm apart: merge them
    crest_f = clusters(rib_z["front"], tol=3.2)
    crest_r = clusters(rib_z["rear"], tol=3.2)      # complete set, top to bottom
    crests = crest_f + crest_r
    pitch, phase, dev = rib_lattice(crests)
    centre = 0.5 * (min(crest_r) + max(crest_r))
    n_g = int(round((max(crest_r) - min(crest_r)) / pitch))   # gaps = grooves
    zf0, zf1 = face_lh[:, 1].min(), face_lh[:, 1].max()
    grooves = [round(centre + (j - (n_g - 1) / 2) * pitch, 2) for j in range(n_g)]
    grooves = [g for g in grooves if zf0 + GROOVE_EDGE <= g <= zf1 - GROOVE_EDGE]

    # ---- 4. features: average of both OEM photos ---------------------------
    def pt_rh(p):
        q = to_lh(p)[0]
        return [round(float(-q[0]), 3), round(float(q[1]), 3)]

    def avg_rh(p_front, p_aes):
        q = 0.5 * (to_lh(p_front)[0] + to_lh(a_to_f(np.array([p_aes])))[0])
        return [round(float(-q[0]), 3), round(float(q[1]), 3)]

    clips = []
    for name, ff, aa, direction in (("top", ef["top"], ta, (0, 1)),
                                    ("bottom", ef["bottom"], ba, (0, -1))):
        clips.append(dict(name=name, tip=avg_rh(ff[:2], aa[:2]),
                          dir=list(direction),
                          width=round(0.5 * (ff[2] + aa[2] * scale_a) / k, 2),
                          length=round(CLIP_LEN_PX[name] / k, 2)))
    clips.append(dict(name="front", tip=avg_rh(ef["right"][:2], ra[:2]),
                      dir=[-1, 0],
                      width=round(0.5 * (ef["right"][2] + ra[2] * scale_a) / k, 2),
                      length=round(CLIP_LEN_PX["front"] / k, 2)))
    clips.append(dict(name="rear", tip=avg_rh(lp[:2], pa[:2]), dir=[1, 0],
                      width=round(lp[2] / k, 2),
                      length=round(CLIP_LEN_PX["rear"] / k, 2)))

    def rh_list(P_lh):
        return [[round(float(-x), 3), round(float(z), 3)] for x, z in P_lh]

    out = dict(
        note="native frame = RH unit seen from the cabin; X right = rear of "
             "car, Z up, mm. LH unit = mirror in X.",
        version=3,
        px_per_mm=k, overall_px=float(overall_px), height_px=float(height_px),
        overall_mm=float(overall_px / k), clip_height_mm=float(height_px / k),
        registration=dict(A=float(A), B=float(B), s=float(s),
                          residual_px=[round(float(r), 1) for r in resid]),
        aespares=dict(px_per_mm=round(k / scale_a, 3),
                      residual_mm=[[round(float(v) / k, 2) for v in r] for r in res_a],
                      cap_size_mm=[round(float(v) * scale_a / k, 1) for v in cap_a_size],
                      rim_z_mm=[round(float(v), 3) for v in rim_fit]),
        face_source=dict(focal_px=a.focal, vanishing=vp_info,
                         tilt_deg=dict(front=round(math.degrees(cams["front"].psi), 1),
                                       rear=round(math.degrees(cams["rear"].psi), 1)),
                         view_mismatch=round(mismatch, 4),
                         views_rms_mm=round(curve_rms(front_lh, rear_lh), 2),
                         placement=fit, rib_crest_z_mm=rib_z),
        grooves=dict(z=grooves, pitch=round(pitch, 2),
                     crests_mm=[round(c, 1) for c in crests],
                     crest_fit_rms_mm=round(float(np.sqrt(np.mean(
                         np.minimum(dev ** 2, 4.0)))), 2),
                     note="grooves sit between the rib crests measured on the "
                          "rectified in-car photos"),
        face=rh_list(face_lh),
        face_oem_loop=rh_list(face_v2_lh),
        body=rh_list(to_lh(body_px)),
        silhouette=rh_list(to_lh(a_to_f(sil_a[::4]))),
        clips=clips,
        screw=dict(centre=avg_rh(CAP_CENTRE_PX, cap_a),
                   cap=[round(CAP_SIZE_PX[0] / k, 2), round(CAP_SIZE_PX[1] / k, 2)]),
        pivot=dict(top=pt_rh(PIVOT_PIN_PX), boss=pt_rh(PIVOT_BOSS_PX)),
    )
    with open(os.path.join(HERE, "oem_trace.json"), "w") as fh:
        json.dump(out, fh, indent=1)

    # ---- 5. overlay for checking ------------------------------------------
    overlay(out, ims, loops, ribs, cams, plate_to_lh, lh_to_plate, s_r, R_r, t_r,
            P_f, P_r_on_f, face_lh, face_v2_lh, front_lh, rear_lh, rim_lh,
            rim_fit, f_im, a_im, sil_f, to_lh, lh_to_px, f_to_a)
    print(json.dumps({k2: out[k2] for k2 in ("px_per_mm", "overall_mm",
                                            "clip_height_mm", "aespares",
                                            "grooves", "clips", "screw",
                                            "pivot")}, indent=1))
    F = np.array(out["face"])
    print("face %.1f x %.1f mm" % (np.ptp(F[:, 0]), np.ptp(F[:, 1])))


def overlay(out, ims, loops, ribs, cams, plate_to_lh, lh_to_plate, s_r, R_r,
            t_r, P_f, P_r_on_f, face_lh, face_v2_lh, front_lh, rear_lh, rim_lh,
            rim_fit, f_im, a_im, sil_f, to_lh, lh_to_px, f_to_a):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    GREEN, RED, CYAN, ORANGE = "#2bd96b", "#ff2d55", "#00c8ff", "#ff9500"
    cl = lambda P: np.vstack([P, P[:1]])                     # noqa: E731
    fig = plt.figure(figsize=(17, 10.4), dpi=110)
    gs = fig.add_gridspec(2, 6, height_ratios=[1, 0.92])
    # (a), (b): in-car photos, red loop + ribs + v3 face re-projected
    for i, (key, title, box) in enumerate(
            (("front", "In car, from the front (your red loop)", (200, 610, 790, 1000)),
             ("rear", "In car, from the rear (your red loop)", (110, 520, 580, 900)))):
        ax = fig.add_subplot(gs[0, 3 * i:3 * i + 3])
        ax.imshow(ims[key].astype("uint8"))
        for kk, b, xa, xb in ribs[key]:
            xx = np.array([xa, xb])
            ax.plot(xx, kk * xx + b, "-", color=CYAN, lw=0.7, alpha=0.8)
        U = lh_to_plate(face_lh)
        if key == "rear":
            U = ((U - t_r) @ R_r) / s_r
        img = cams[key].to_image(U)
        ax.plot(*cl(img).T, "-", color=GREEN, lw=1.6,
                label="v3 face projected back into the photo")
        ax.plot([], [], "-", color=CYAN, lw=1, label="ribs found (-> vanishing point)")
        ax.set_xlim(box[0], box[2])
        ax.set_ylim(box[3], box[1])
        ax.set_title(title, fontsize=9)
        ax.legend(fontsize=7, loc="upper left")
        ax.axis("off")
    # (c): rectified outlines in mm
    ax = fig.add_subplot(gs[1, 0:2])
    body = np.array(out["body"]) * [-1, 1]
    ax.plot(*cl(body).T, "-", color="0.55", lw=1, label="housing (back photo)")
    ax.plot(*cl(face_v2_lh).T, "--", color=RED, lw=1, label="face loop on OEM photo")
    ax.plot(*cl(front_lh).T, "-", color=CYAN, lw=0.9, label="front photo, rectified")
    ax.plot(*cl(rear_lh).T, "-", color=ORANGE, lw=0.9, label="rear photo, rectified")
    ax.plot(*cl(face_lh).T, "-", color=GREEN, lw=2, label="v3 face = mean")
    for zg in out["grooves"]["z"]:
        ax.axhline(zg, color="0.7", lw=0.5, ls=(0, (2, 3)), zorder=0)
    xr = np.array([rim_lh[:, 0].min(), rim_lh[:, 0].max()])
    ax.plot(xr, rim_fit[0] + rim_fit[1] * xr, ":", color="k", lw=1, label="OEM rim edge")
    for c in out["clips"]:
        ax.plot(-c["tip"][0], c["tip"][1], "o", color="k", ms=3)
    ax.plot(-out["screw"]["centre"][0], out["screw"]["centre"][1], "s", mfc="none",
            mec=ORANGE, ms=8)
    ax.set_aspect("equal")
    ax.grid(alpha=0.25)
    ax.legend(fontsize=6, loc="lower center", ncol=2)
    F = face_lh
    ax.set_title("Rectified, LH view (x = front of car), mm: face %.0f x %.0f"
                 % (np.ptp(F[:, 0]), np.ptp(F[:, 1])), fontsize=9)
    ax.set_ylim(-62, 58)
    # (d): AE Spares photo with the result
    ax = fig.add_subplot(gs[1, 2:4])
    ax.imshow(a_im.astype("uint8"))
    to_a = lambda P: f_to_a(lh_to_px(P))                     # noqa: E731
    ax.plot(*cl(to_a(face_lh)).T, "-", color=GREEN, lw=1.6)
    ax.plot(*cl(to_a(body)).T, "-", color=CYAN, lw=1.0)
    for c in out["clips"]:
        ax.plot(*to_a(np.array([[-c["tip"][0], c["tip"][1]]]))[0], "o",
                color="#00ff88", ms=5)
    ax.plot(*to_a(np.array([[-out["screw"]["centre"][0],
                             out["screw"]["centre"][1]]]))[0], "s", mfc="none",
            mec=ORANGE, ms=9, mew=2)
    ax.set_title("AE Spares photo (upside down = RH view of LH part), "
                 "%.2f px/mm" % out["aespares"]["px_per_mm"], fontsize=9)
    ax.set_xlim(0, a_im.shape[1])
    ax.set_ylim(1080, 160)
    ax.axis("off")
    # (e): OEM front photo with the result
    ax = fig.add_subplot(gs[1, 4:6])
    ax.imshow(f_im.astype("uint8"))
    ax.plot(*cl(lh_to_px(face_lh)).T, "-", color=GREEN, lw=1.6, label="v3 face")
    ax.plot(*cl(lh_to_px(body)).T, "-", color=CYAN, lw=1.0, label="housing")
    ax.plot(*cl(lh_to_px(face_v2_lh)).T, "--", color=RED, lw=1, label="OEM-photo loop")
    for c in out["clips"]:
        ax.plot(*lh_to_px(np.array([[-c["tip"][0], c["tip"][1]]]))[0], "o",
                color="#00ff88", ms=5)
    ax.plot(*CAP_CENTRE_PX, "s", color=ORANGE, ms=9, mfc="none", mew=2)
    ax.plot(*PIVOT_PIN_PX, "^", color="#bf5af2", ms=8)
    ax.legend(fontsize=7, loc="upper left")
    ax.set_title("OEM front photo, %.2f px/mm: overall %.0f mm, clip-to-clip %.0f mm"
                 % (out["px_per_mm"], out["overall_mm"], out["clip_height_mm"]),
                 fontsize=9)
    ax.set_xlim(60, 1480)
    ax.set_ylim(1140, 400)
    ax.axis("off")
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "..", "renders", "oem_trace_overlay.png"))
    plt.close(fig)


if __name__ == "__main__":
    main()
