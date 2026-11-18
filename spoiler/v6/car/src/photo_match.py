"""Solve the camera of the owner's photo against the 3D car: a chamfer match of the car's outline against the sky and
background (extra weight round the rear pillars and roof, where the spoiler sits; the old wing left out) plus the wheel
rims, with the body's ride height on its wheels as a free parameter. Writes v6/car/data/photo_camera.json.
Usage (from spoiler/): python3 v6/car/src/photo_match.py [start params as JSON]"""
import sys, json, numpy as np
sys.path.insert(0, 'v6/car/src')
from scipy import ndimage as ndi
from scipy.optimize import minimize
from PIL import Image
from skimage.color import rgb2hsv
from photo_cam import Cam, load_parts, raster_labels, overlay, wheel_centre, poly_mask, PHOTO, CAM_JSON, WING_TOP, WING_BOTTOM

W, H = 510, 392
Y_CUT = 258                            # below this the car's shadow spoils the mask
REGION = (85, 60, 446, Y_CUT - 3)      # outline compared inside this box (x0, y0, x1, y1)
ROI = (100, 60, 360, 165)              # rear pillars and roof round the spoiler: weighted up
ROI_W = 4.0
RIM_FACE = 0.1005                      # rim lip outer face, outboard of the wheel centre (m)
R_LIP = 0.235
FEATS = {   # photo (u, v)  <->  model point (m); wheels do not move with the body's ride height
    'rr_rim_centre': ((359.0, 249.0), wheel_centre('rear', 1) + [RIM_FACE, 0, 0]),
    'fr_rim_centre': ((440.0, 246.5), wheel_centre('front', 1) + [RIM_FACE, 0, 0]),
    'rr_rim_top':    ((358.0, 207.0), wheel_centre('rear', 1) + [RIM_FACE, 0, R_LIP]),
    'rr_rim_bottom': ((358.0, 291.0), wheel_centre('rear', 1) + [RIM_FACE, 0, -R_LIP]),
    'fr_rim_top':    ((441.0, 214.0), wheel_centre('front', 1) + [RIM_FACE, 0, R_LIP]),
    'fr_rim_bottom': ((440.0, 279.0), wheel_centre('front', 1) + [RIM_FACE, 0, -R_LIP]),
}
# lines across the car's rear in the photo (lateral in 3D, so they must point at the lateral vanishing point):
# (end 1, end 2, weight). The lamp corners are the least sure (soft, curved edges)
LAT_LINES = [((135.0, 206.2), (255.0, 205.5), 1.0),     # tailgate/bumper crease
             ((175.0, 140.3), (295.0, 138.2), 1.0),     # bottom edge of the rear window
             ((113.6, 151.6), (287.3, 149.6), 0.5),     # tail lamps, inner top corners
             ((117.6, 183.6), (282.9, 186.5), 0.5),     # tail lamps, inner bottom corners
             ((160.5, 220.5), (211.0, 220.0), 0.3),     # number plate, top edge
             ((141.0, 84.3), (283.0, 75.5), 0.3)]       # old wing, end-plate tops
FEAT_W = {'rr_rim_centre': 1.0, 'fr_rim_centre': 1.0, 'rr_rim_top': 0.5, 'rr_rim_bottom': 0.5, 'fr_rim_top': 0.5, 'fr_rim_bottom': 0.5}

def column_fill(m):
    """solid below the first car pixel of each column (no holes from sky reflections in the glass)"""
    out = np.zeros_like(m); top = np.argmax(m, axis=0); has = m.any(axis=0)
    yy = np.arange(m.shape[0])[:, None]
    out[:] = has[None, :] & (yy >= top[None, :]); out[Y_CUT:] = False
    return out

def photo_mask():
    A = np.asarray(Image.open(PHOTO).convert('RGB')).astype(float) / 255
    h, s, v = np.moveaxis(rgb2hsv(A), -1, 0)
    m = ((s > 0.42) & (h > 0.55) & (h < 0.72)) | (v < 0.30)
    m[Y_CUT:] = False
    m = ndi.binary_closing(m, iterations=2); m = ndi.binary_fill_holes(m)
    lab, n = ndi.label(m); m = lab == (np.argmax(np.bincount(lab.ravel())[1:]) + 1)
    return column_fill(m)

def weights():
    w = np.zeros((H, W)); x0, y0, x1, y1 = REGION; w[y0:y1, x0:x1] = 1.0
    x0, y0, x1, y1 = ROI; w[y0:y1, x0:x1] *= ROI_W
    wing = ndi.binary_dilation(poly_mask(WING_TOP + WING_BOTTOM, W, H) > 0.02, iterations=2)
    w[wing] = 0.0
    return w

def edges(m):
    return m & ~ndi.binary_erosion(m)

PM = None; DT_P = None; WT = None; PARTS = None; EP = None
def setup():
    global PM, DT_P, WT, PARTS, EP
    PM = photo_mask(); WT = weights(); PARTS = load_parts()
    EP = edges(PM) & (WT > 0); DT_P = ndi.distance_transform_edt(~edges(PM))

def feats(r_lip):
    """wheel points with the rim lip radius free (the car may not run the modelled 18 in wheels)"""
    F = {}
    for k, (uv, X) in FEATS.items():
        X = np.array(X, float); c = X.copy()
        if 'top' in k: X = c - [0, 0, R_LIP] + [0, 0, r_lip]
        if 'bottom' in k: X = c + [0, 0, R_LIP] - [0, 0, r_lip]
        F[k] = (uv, X)
    return F

def line_resid(cam):
    """px: how far each lateral line's far end is off the direction the camera gives lateral lines there"""
    out = []
    rt, up, f = cam.axes(); s_ = cam.lens / 36.0 * cam.W
    for (p1, p2, w) in LAT_LINES:
        m = (np.array(p1) + np.array(p2)) / 2
        x = (m[0] - cam.W / 2 + cam.shift_x * cam.W) / s_; y = -(m[1] - cam.H / 2 - cam.shift_y * cam.W) / s_
        P = cam.loc + 5.0 * (f + x * rt + y * up)
        q, _ = cam.project(np.array([P, P + [0.2, 0, 0]])); d = q[1] - q[0]; d /= np.linalg.norm(d)
        e = np.array(p2) - np.array(p1); L = np.linalg.norm(e); e /= L
        out.append((w, L * (d[0] * e[1] - d[1] * e[0])))
    return out

def cam_of(p):
    x, y, z, yaw, pitch, roll, lens, sx, sy = p[:9]
    return Cam((x, y, z), yaw, pitch, roll, lens, sx, sy, W, H)

def loss(p, verbose=False):
    cam = cam_of(p); dz = p[9]
    lab, _ = raster_labels(cam, PARTS, ['body', 'mirrors', 'tyres', 'handles', 'spoiler'], dz_body=dz)
    mm = column_fill((lab > 0) & (lab != 5))
    em = edges(mm) & (WT > 0)
    if em.sum() < 50: return 1e6
    hub = lambda d: np.where(d < 5, 0.5 * d * d, 5 * (d - 2.5))
    w1 = WT[em]; d1 = hub(DT_P[em])
    dt_m = ndi.distance_transform_edt(~edges(mm)); w2 = WT[EP]; d2 = hub(dt_m[EP])
    sil = (w1 * d1).sum() / w1.sum() + (w2 * d2).sum() / w2.sum()
    fe = 0.0
    for k, (uv, X) in feats(p[10]).items():
        q, z = cam.project(X); fe += FEAT_W[k] * np.sum((q[0] - uv) ** 2)
    fe /= sum(FEAT_W.values())
    lr = line_resid(cam); li = sum(w * r * r for w, r in lr) / sum(w for w, r in lr)
    prior = (p[5] / 2.0) ** 2 + (dz / 0.03) ** 2 + ((p[10] - 0.245) / 0.02) ** 2
    L = sil + 0.25 * fe + 0.5 * li + prior
    if verbose: print('sil %.3f feat_rms %.2f px lines_rms %.2f px roll %.2f dz %.1f mm rim %.3f -> %.3f' % (
        sil, np.sqrt(fe), np.sqrt(li), p[5], dz * 1000, p[10], L), ' lines:', ' '.join('%.1f' % r for w, r in lr))
    return L

def roi_report(p):
    """mean outline distance (px) inside the ROI, both ways"""
    cam = cam_of(p); lab, _ = raster_labels(cam, PARTS, ['body', 'mirrors', 'tyres', 'handles', 'spoiler'], dz_body=p[9])
    mm = column_fill((lab > 0) & (lab != 5)); x0, y0, x1, y1 = ROI
    r = np.zeros((H, W), bool); r[y0:y1, x0:x1] = True; r &= WT > 0
    em = edges(mm) & r; ep = edges(PM) & r
    return DT_P[em].mean(), ndi.distance_transform_edt(~edges(mm))[ep].mean()

if __name__ == '__main__':
    setup()
    d = json.load(open(CAM_JSON))
    p0 = np.array([*d['loc'], d['yaw'], d['pitch'], d['roll'], d['lens'], d['shift_x'], d['shift_y'], d.get('dz_body', 0.0), d.get('rim_lip', 0.245)])
    if len(sys.argv) > 1: p0 = np.array(json.loads(sys.argv[1]))
    loss(p0, True); print('ROI outline distance (model->photo, photo->model) px: %.2f %.2f' % roi_report(p0))
    best = p0
    for it, scale in enumerate([1.0, 0.35, 0.12]):
        st = np.array([0.4, 0.6, 0.1, 3.0, 1.5, 0.8, 10.0, 0.06, 0.03, 0.02, 0.015]) * scale
        sim = np.array([best] + [best + np.eye(11)[i] * st[i] for i in range(11)])
        r = minimize(loss, best, method='Nelder-Mead', options=dict(initial_simplex=sim, maxfev=1500, xatol=1e-4, fatol=1e-5))
        best = r.x; print('round', it, r.nfev, 'evals'); loss(best, True)
        print(json.dumps(np.round(best, 5).tolist()))
    print('ROI outline distance (model->photo, photo->model) px: %.2f %.2f' % roi_report(best))
    cam = cam_of(best)
    cam.to_json(CAM_JSON, dz_body=float(best[9]), rim_lip=float(best[10]), fit=dict(loss=float(loss(best)), roi_px=list(roi_report(best)),
                lines_px=[round(float(r), 2) for w, r in line_resid(cam)],
                feats={k: [list(v[0]), cam.project(v[1])[0][0].round(1).tolist()] for k, v in feats(best[10]).items()}))
    pts = {k: (uv, cam.project(X)[0][0]) for k, (uv, X) in feats(best[10]).items()}
    overlay(cam, PARTS, 'v6/car/out/photo_comp/photo_match_overlay.png', pts=pts, dz_body=float(best[9]))
    print('saved', CAM_JSON)
