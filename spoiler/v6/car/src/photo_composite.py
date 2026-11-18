"""Put the spoiler into the owner's photo: remove the old wing (sky refitted above, glass continued below), add the
spoiler's shadow on the car (ratio of the 'with' and 'without' passes), and composite the rendered spoiler, matched to
the photo's exposure, softness and grain.   Run from spoiler/ after render_photo_comp.sh:
    python3 v6/car/src/photo_composite.py [--dbg]  ->  v6/brochure/photo/owner_car_with_spoiler.png"""
import sys, json, numpy as np
sys.path.insert(0, 'v6/car/src')
from PIL import Image
from scipy import ndimage as ndi
from skimage.restoration import inpaint_biharmonic
from photo_cam import Cam, load_parts, raster_labels, PHOTO, CAM_JSON, WING_TOP, WING_BOTTOM, PILLAR_L, poly_mask
PASS = 'v6/car/out/photo_comp/'
OUT = 'v6/brochure/photo/owner_car_with_spoiler.png'
RNG = np.random.default_rng(7)
# The real car's roof and rear window sit higher than the generic model's (by ~5 px here, ~30-40 mm): measured on the
# visible roof edge right of the old wing (5-6 px), the bottom of the rear window (~7 px) and the left D-pillar (~2 px).
# The rendered spoiler, its shade and the model outline used beside it are moved by this much (photo px, x right, y down)
SHIFT_PX = (-2.0, -5.5)

def srgb2lin(x): return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)
def lin2srgb(x): x = np.clip(x, 0, None); return np.where(x <= 0.0031308, 12.92 * x, 1.055 * x ** (1 / 2.4) - 0.055)

def load_pass(name, k, shift=True):
    R = np.load(PASS + name + '.npy'); H, W = R.shape[0] // k, R.shape[1] // k
    if shift and SHIFT_PX != (0.0, 0.0):
        R = np.stack([ndi.shift(R[..., c], (SHIFT_PX[1] * k, SHIFT_PX[0] * k), order=1, mode='constant',
                                cval=0.0 if c == 3 or name == 'spoiler' else np.nan) for c in range(4)], -1)
        if name != 'spoiler': R = np.nan_to_num(R, nan=0.0)
    return R[:H * k, :W * k].reshape(H, k, W, k, 4).mean((1, 3))

def model_outline(W, H, dz, ss=4):
    """the model car's outline (no spoiler) at the photo's size, moved with the spoiler by SHIFT_PX"""
    cam = Cam.from_json(CAM_JSON, W=W, H=H)
    lab, _ = raster_labels(cam, load_parts(), ['body', 'mirrors', 'tyres', 'handles'], dz_body=dz, ss=ss)
    m = ndi.shift((lab > 0).astype(float), (SHIFT_PX[1] * ss, SHIFT_PX[0] * ss), order=0, mode='nearest')
    return m.reshape(H, ss, W, ss).mean((1, 3)) > 0.5

def left_of_pillar(W, H):
    (x0, y0), (x1, y1) = PILLAR_L; yy, xx = np.mgrid[0:H, 0:W] + 0.5
    return (xx - x0) * (y1 - y0) - (yy - y0) * (x1 - x0) > 0          # sky side of the extended pillar line

# the photo's look: blacks are lifted and turn blue (its colour grading). Channel / luminance ratios read off the photo's
# dark parts (diffuser, old wing, tyre, sky):  luminance -> (R/L, G/L, B/L)
TINT_L = np.array([0.0127, 0.039, 0.150, 0.957])
TINT_RGB = np.array([[0.31, 0.87, 4.33], [0.41, 1.00, 2.82], [0.80, 1.01, 1.42], [1.00, 1.00, 1.01]])
BLACK = 0.012                      # the photo's black level (old wing, 1st percentile)
FRIT_L = 0.036                     # shaded black of the old wing's underside (its darker half): the window's top band
GAMMA_DARK = 0.8                   # lifts the render's blacks to the photo's (old wing median 0.06, darker half 0.039)
KNEE, HI_MAX = 0.06, 0.17          # highlight roll-off (linear, after exposure): sky glints on the black stay grey (<= ~0.45),
                                   # as on the photo's own black parts, instead of white sparkles along the lip edge

def tint(Lo):
    lg = np.log(np.clip(Lo, TINT_L[0], TINT_L[-1]))
    r = np.stack([np.interp(lg, np.log(TINT_L), TINT_RGB[:, c]) for c in range(3)], -1)
    rgb = Lo[..., None] * r
    return rgb * (Lo / np.maximum(rgb @ [0.2126, 0.7152, 0.0722], 1e-6))[..., None]   # keep the luminance exact

def smooth_fill(A, valid, fill, sigmas=(3, 6, 12, 24, 48)):
    """normalized convolution: each fill pixel gets the local mean of valid pixels, at the smallest scale that has any"""
    out = A.copy(); todo = fill.copy(); w = valid.astype(float)
    for sg in sigmas:
        den = ndi.gaussian_filter(w, sg)
        ok = todo & (den > 0.08)
        if ok.any():
            for c in range(3): out[..., c][ok] = (ndi.gaussian_filter(A[..., c] * w, sg)[ok] / den[ok])
        todo &= ~ok
        if not todo.any(): break
    return out

def remove_wing(A, a_sp, body):
    """A: photo (sRGB 0-1). a_sp: our spoiler's coverage. body: the model car's outline without any spoiler."""
    H, W = A.shape[:2]
    wing = ndi.binary_dilation(poly_mask(WING_TOP + WING_BOTTOM, W, H) > 0.02, iterations=1)
    halo = ndi.binary_dilation(wing, iterations=4) & ~wing            # the photo's sharpening halo round the wing
    # the car side grown 2 px: under the spoiler's lower edge the background must be glass, not sky (the model outline
    # can sit a pixel below the rendered underside)
    car_side = ndi.binary_dilation(body, iterations=2) & ~left_of_pillar(W, H)
    L = A @ [0.2126, 0.7152, 0.0722]
    # 1) sky: local mean of the clear sky round it (the photo's sky is almost noiseless)
    fill_sky = (wing | halo) & ~car_side
    sky_ok = ~ndi.binary_dilation(wing | car_side, iterations=4) & (L > 0.6)
    B = smooth_fill(A, sky_ok, fill_sky)
    B[fill_sky] += RNG.normal(0, 0.0012, (fill_sky.sum(), 1))
    # 2) car (glass, pillars) where the wing was and our spoiler does not cover: carried on from the glass below and the
    #    dark wing underside that stays hidden under our spoiler (reads as the shade under the new lip)
    # 2) car where the wing was and our spoiler does not cover: the top of a rear window is its black ceramic band, in
    #    the shade of the lip, so it is filled with the photo's shaded black, blended into the glass and pillars it meets
    fill_car = wing & car_side & ~(a_sp > 0.995)
    if fill_car.any():
        B2 = inpaint_biharmonic(B, fill_car, channel_axis=-1)
        known = car_side & ~wing                                      # glass and pillars outside the old wing
        dist = ndi.distance_transform_edt(~known)
        w = np.clip((dist - 1.0) / 6.0, 0, 1); w = (w * w * (3 - 2 * w))[..., None]   # glass fades into the band over ~7 px
        dark = tint(np.full((H, W), FRIT_L)) + RNG.normal(0, 0.004, (H, W, 1))
        B[fill_car] = ((1 - w) * B2 + w * dark)[fill_car]
    return np.clip(B, 0, 1), dict(wing=wing, fill_sky=fill_sky, fill_car=fill_car)

def grade_spoiler(c_lin, e):
    """rendered spoiler colour (linear, un-premultiplied) -> the photo's display look"""
    x = e * (c_lin @ [0.2126, 0.7152, 0.0722])
    x = np.where(x < KNEE, x, KNEE + (x - KNEE) / (1 + (x - KNEE) / (HI_MAX - KNEE)))
    Ls = lin2srgb(x)
    Lo = BLACK + (1 - BLACK) * np.clip(Ls, 0, 1) ** GAMMA_DARK
    return tint(Lo)

def main(out=OUT, dbg=None):
    A = np.asarray(Image.open(PHOTO).convert('RGB')).astype(float) / 255
    H, W = A.shape[:2]
    cd = json.load(open(CAM_JSON)); dz = float(cd.get('dz_body', 0.0))
    body = model_outline(W, H, dz)
    sp = load_pass('spoiler', 3); a = np.clip(sp[..., 3], 0, 1)
    B, info = remove_wing(A, a, body)
    Bl = srgb2lin(B)
    # the spoiler's shade on the car: ratio of the car rendered with and without it
    w_, wo = load_pass('with', 2), load_pass('without', 2)
    ok = (w_[..., 3] > 0.99) & (wo[..., 3] > 0.99)
    lw, lwo = w_[..., :3] @ [0.2126, 0.7152, 0.0722], wo[..., :3] @ [0.2126, 0.7152, 0.0722]
    ratio = np.where(ok & (lwo > 1e-4), lw / np.maximum(lwo, 1e-4), 1.0)
    ratio = np.clip(ndi.gaussian_filter(ratio, 0.7), 0.35, 1.1)
    near = ndi.binary_dilation(a > 0.02, iterations=14) & body & (a < 0.98)
    Bl[near] *= ratio[near][:, None]
    # exposure: the environment as rendered vs the photo's sky above the car
    sky = load_pass('sky', 1, shift=False)[..., :3] @ [0.2126, 0.7152, 0.0722]
    yy, xx = np.mgrid[0:H, 0:W]; reg = (xx > 100) & (xx < 360) & (yy > 35) & (yy < 70)
    e = np.median(srgb2lin(A)[reg] @ [0.2126, 0.7152, 0.0722]) / np.median(sky[reg])
    # the spoiler: un-premultiply, grade, slight softening to the photo's sharpness, then over the plate
    soft = lambda x, sg=0.35: ndi.gaussian_filter(x, sg)
    ap = soft(a); cpre = np.stack([soft(sp[..., c], 0.6) for c in range(3)], -1)
    c = np.where(ap[..., None] > 1e-4, cpre / np.maximum(soft(a, 0.6), 1e-4)[..., None], 0)
    S = srgb2lin(grade_spoiler(c, e))
    O = Bl * (1 - ap[..., None]) + S * ap[..., None]
    Os = lin2srgb(O)
    # the photo's own sharpening halo, round the new edges only
    zone = ndi.binary_dilation((ap > 0.02) & (ap < 0.98), iterations=3) | (ndi.binary_dilation(ap > 0.5, iterations=2) & ~(ap > 0.5))
    us = Os + 0.45 * (Os - np.stack([ndi.gaussian_filter(Os[..., k], 1.0) for k in range(3)], -1))
    Os[zone] = us[zone]
    Os = np.clip(Os, 0, 1)
    Image.fromarray((Os * 255 + 0.5).astype(np.uint8)).save(out)
    vis = a > 0.5
    print('exposure %.3f  spoiler L median %.3f  (old wing 0.060)  shade min %.2f' % (
        e, np.median(Os[vis] @ [0.2126, 0.7152, 0.0722]), ratio[near].min() if near.any() else 1), 'fill px sky', info['fill_sky'].sum(), 'car', info['fill_car'].sum())
    if dbg:
        Image.fromarray((Os * 255 + 0.5).astype(np.uint8)).crop((105, 50, 355, 175)).resize((1000, 500), Image.LANCZOS).save(dbg)
    return Os

if __name__ == '__main__':
    main(dbg='v6/car/out/photo_comp/composite_zoom.png' if '--dbg' in sys.argv else None)
