"""Trace the OEM i20 N inner door handle from the two reference photos.

Inputs (ref/):
    oem_handle_front_LH.webp  cabin-side view, red loop = visible face outline
    oem_handle_back_LH.webp   rear view, red loop = housing body outline

Output: cad/oem_trace.json with smoothed outlines and mounting features in mm,
in the model's native frame (RH unit, viewed from the cabin:
X right = REAR of car, Z up) and an overlay image for checking the trace.

SCALE: photos carry no ruler.  The default 7.0 px/mm (front photo) comes from
four standard parts that agree at that scale: clip heads ~7 mm, stainless
pivot pin ~3 mm, screw cap ~17 mm, torsion spring ~9-10 mm OD.  Measure the
real handle and re-run with ONE of:
    --overall MM   overall length, lower-left "chin" to tip of the front clip
    --height  MM   tip of top clip to tip of bottom clip
usage: python oem_trace.py [--overall 185] [--height 91]
"""
import argparse
import json
import math
import os

import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from scipy.interpolate import splev, splprep
from skimage import draw, measure, morphology

HERE = os.path.dirname(os.path.abspath(__file__))
REF = os.path.join(HERE, "..", "ref")
FRONT = os.path.join(REF, "oem_handle_front_LH.webp")
BACK = os.path.join(REF, "oem_handle_back_LH.webp")
DEFAULT_PX_PER_MM = 7.0

# Hand-measured features in the FRONT photo (pixels), see overlay image
CAP_CENTRE_PX = (628.0, 808.0)        # square screw cap -> door-card screw
CAP_SIZE_PX = (120.0, 135.0)
PIVOT_PIN_PX = (1057.0, 532.0)        # top end of the stainless pivot pin
PIVOT_BOSS_PX = (1048.0, 1003.0)      # lower pivot boss
# clip protrusion beyond the housing frame edge (front photo, pixels)
CLIP_LEN_PX = {"top": 57.0, "bottom": 56.0, "front": 62.0, "rear": 45.0}


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


def smooth_loop(xy, n=260, s_per_pt=6.0):
    xy = xy[::2]
    tck, _ = splprep([xy[:, 0], xy[:, 1]], s=len(xy) * s_per_pt, per=1)
    u = np.linspace(0, 1, n, endpoint=False)
    x, y = splev(u, tck)
    return np.column_stack([x, y])


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


def front_left_pin(sil):
    """The small pin on the left flank (not the lower-left chin)."""
    sel = sil[(sil[:, 1] > 695) & (sil[:, 1] < 760) & (sil[:, 0] < 205)]
    return sel[:, 0].min(), sel[:, 1].mean(), np.ptp(sel[:, 1])


def back_right_clip(sil):
    """Arrow clip on the right flank of the back view (not the cup's end)."""
    sel = sil[(sil[:, 1] < 450) & (sil[:, 0] > 1445)]
    return sel[:, 0].max(), sel[:, 1].mean(), np.ptp(sel[:, 1])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--overall", type=float, help="measured overall length mm")
    ap.add_argument("--height", type=float, help="measured clip-to-clip height mm")
    a = ap.parse_args()

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
        rows.append([1, 0, -xb]); rhs.append(xf)
    def eq_y(yf, yb):
        rows.append([0, 1, yb]); rhs.append(yf)
    eq_x(ef["top"][0], eb["top"][0]); eq_y(ef["top"][1], eb["top"][1])
    eq_x(ef["bottom"][0], eb["bottom"][0]); eq_y(ef["bottom"][1], eb["bottom"][1])
    eq_x(ef["right"][0], eb["left"][0]); eq_y(ef["right"][1], eb["left"][1])
    eq_x(lp[0], eb["right"][0]); eq_y(lp[1], eb["right"][1])
    (A, B, s), res, *_ = np.linalg.lstsq(np.array(rows, float),
                                        np.array(rhs, float), rcond=None)
    resid = np.array(rows, float) @ np.array([A, B, s]) - np.array(rhs)
    body_px = np.column_stack([A - s * body_px_b[:, 0], B + s * body_px_b[:, 1]])

    # scale
    overall_px = ef["right"][0] - sil_f[:, 0].min()
    height_px = ef["bottom"][1] - ef["top"][1]
    k = DEFAULT_PX_PER_MM
    if a.overall:
        k = overall_px / a.overall
    elif a.height:
        k = height_px / a.height
    x0 = 0.5 * (face_px[:, 0].min() + face_px[:, 0].max())
    z0 = 0.5 * (face_px[:, 1].min() + face_px[:, 1].max())

    def to_rh(xy):      # native frame: mirror of the LH photo
        xy = np.atleast_2d(np.asarray(xy, float))
        return np.column_stack([-(xy[:, 0] - x0) / k, (z0 - xy[:, 1]) / k])

    def pt(p):
        return [round(float(v), 3) for v in to_rh(p)[0]]

    clips = []
    for name, (xc, yc, w), direction in (
            ("top", ef["top"], (0, 1)), ("bottom", ef["bottom"], (0, -1))):
        tip = pt((xc, yc))
        clips.append(dict(name=name, tip=tip, dir=list(direction),
                          width=round(w / k, 2),
                          length=round(CLIP_LEN_PX[name] / k, 2)))
    # front-view right pin = front-of-car clip; left pin = rear clip
    clips.append(dict(name="front", tip=pt((ef["right"][0], ef["right"][1])),
                      dir=[-1, 0], width=round(ef["right"][2] / k, 2),
                      length=round(CLIP_LEN_PX["front"] / k, 2)))
    clips.append(dict(name="rear", tip=pt((lp[0], lp[1])), dir=[1, 0],
                      width=round(lp[2] / k, 2),
                      length=round(CLIP_LEN_PX["rear"] / k, 2)))
    out = dict(
        note="native frame = RH unit seen from the cabin; X right = rear of "
             "car, Z up, mm. LH unit = mirror in X.",
        px_per_mm=k, overall_px=float(overall_px), height_px=float(height_px),
        overall_mm=float(overall_px / k), clip_height_mm=float(height_px / k),
        registration=dict(A=float(A), B=float(B), s=float(s),
                          residual_px=[round(float(r), 1) for r in resid]),
        face=[[round(float(x), 3), round(float(z), 3)] for x, z in to_rh(face_px)],
        body=[[round(float(x), 3), round(float(z), 3)] for x, z in to_rh(body_px)],
        silhouette=[[round(float(x), 3), round(float(z), 3)]
                    for x, z in to_rh(sil_f[::4])],
        clips=clips,
        screw=dict(centre=pt(CAP_CENTRE_PX),
                   cap=[round(CAP_SIZE_PX[0] / k, 2), round(CAP_SIZE_PX[1] / k, 2)]),
        pivot=dict(top=pt(PIVOT_PIN_PX), boss=pt(PIVOT_BOSS_PX)),
    )
    with open(os.path.join(HERE, "oem_trace.json"), "w") as f:
        json.dump(out, f, indent=1)

    # ---- overlay for checking -------------------------------------------
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axs = plt.subplots(1, 2, figsize=(16, 6.2), dpi=110)
    ax = axs[0]
    ax.imshow(f_im.astype("uint8"))
    ax.plot(*np.vstack([face_px, face_px[:1]]).T, color="#ff2d55", lw=1.6,
            label="face (your red loop, smoothed)")
    ax.plot(*np.vstack([body_px, body_px[:1]]).T, color="#00c8ff", lw=1.4,
            label="housing (back loop, mirrored onto front)")
    ax.plot(sil_f[:, 0], sil_f[:, 1], color="#ffd400", lw=0.8,
            label="silhouette incl. clips")
    for c in (ef["top"], ef["bottom"]):
        ax.plot(c[0], c[1], "o", color="#00ff88", ms=6)
    ax.plot(ef["right"][0], ef["right"][1], "o", color="#00ff88", ms=6)
    ax.plot(lp[0], lp[1], "o", color="#00ff88", ms=6, label="clip tips")
    ax.plot(*CAP_CENTRE_PX, "s", color="#ff9500", ms=9, mfc="none", mew=2,
            label="door-card screw (cap)")
    ax.plot(*PIVOT_PIN_PX, "^", color="#bf5af2", ms=8, label="OEM pivot pin")
    ax.set_title(f"Front (cabin side) - scale {k:.2f} px/mm: overall "
                 f"{overall_px / k:.0f} mm, clip-to-clip {height_px / k:.0f} mm",
                 fontsize=9)
    ax.legend(fontsize=7, loc="upper left")
    ax.set_xlim(60, 1480)
    ax.set_ylim(1140, 400)
    ax.axis("off")
    ax = axs[1]
    ax.imshow(b_im.astype("uint8"))
    ax.plot(*np.vstack([body_px_b, body_px_b[:1]]).T, color="#00c8ff", lw=1.6)
    ax.set_title("Back - housing outline traced from your red loop", fontsize=9)
    ax.axis("off")
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "..", "renders", "oem_trace_overlay.png"))
    plt.close(fig)
    print(json.dumps({k2: out[k2] for k2 in ("px_per_mm", "overall_mm",
                                            "clip_height_mm", "registration",
                                            "clips", "screw", "pivot")},
                     indent=1))


if __name__ == "__main__":
    main()
