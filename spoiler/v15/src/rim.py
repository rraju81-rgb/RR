"""v14 smooth tip: the line the back edge follows, and the height of the rounded tip along it.
The line (as v10): for each x, where the gap between the spoiler's underside and the car first grows past RIM_G (the
rear edge of the contact band at the back), then a lower envelope over RIM_WIN and Gaussian smoothing over RIM_SIG, so
it is one smooth line (no steps from the car model's faceted crest). The tip runs TIP_T forward of it; its lowest point
follows the spoiler's own underside there (smoothed), so the tip just touches where the underside sat on the car.
The tip's cross-section (the front face, see tip_profile) is used by p1_core.py as a smooth field, not as a solid."""
import numpy as np
from scipy import ndimage as ndi
from scipy.interpolate import RegularGridInterpolator as RGI
from skimage.measure import find_contours
from trimesh.ray.ray_pyembree import RayMeshIntersector
from layout import RIM_G, RIM_WIN, RIM_SIG, RIM_X, TIP_T, TIP_R, TIP_EPS, M_FRONT

def gap_map(E, car, x0=-600.0, x1=600.0, dx=1.0, z0=90.0, z1=235.0, dz=0.5):
    xs = np.arange(x0, x1 + 1e-9, dx); zs = np.arange(z0, z1 + 1e-9, dz)
    X, Z = np.meshgrid(xs, zs, indexing='ij')
    def first(R, y0, dy):
        O = np.column_stack([X.ravel(), np.full(X.size, y0), Z.ravel()])
        loc, ir, it = R.intersects_location(O, np.tile([0, dy, 0], (len(O), 1)), multiple_hits=False)
        out = np.full(X.size, np.nan); out[ir] = loc[:, 1]; return out.reshape(X.shape)
    return xs, zs, first(RayMeshIntersector(E), -400.0, 1.0), first(RayMeshIntersector(car), 400.0, -1.0)

def rim_curve(E, car, step=1.0):
    """stations along the rim: (x, z) in plan, forward unit normal N (x, z), and the tip's lowest point y_tip"""
    xs, zs, ybot, ycar = gap_map(E, car)
    g = np.where(np.isfinite(ybot - ycar), ybot - ycar, 50.0)
    xb = np.arange(-RIM_X, RIM_X + 1e-9, 0.5)
    zz = []
    for G0 in RIM_G:
        c = max(find_contours(g, G0), key=len)
        P = np.column_stack([np.interp(c[:, 0], np.arange(len(xs)), xs), np.interp(c[:, 1], np.arange(len(zs)), zs)])
        zb = np.full(len(xb), np.nan)
        for i, x in enumerate(xb):
            k = np.abs(P[:, 0] - x) < 0.75
            if k.any(): zb[i] = P[k, 1].max()
        ok = np.isfinite(zb); zz.append(np.interp(xb, xb[ok], zb[ok]))
    base = np.mean(zz, axis=0)
    zr = ndi.gaussian_filter1d(ndi.minimum_filter1d(base, int(RIM_WIN / 0.5), mode='nearest'), RIM_SIG / 0.5, mode='nearest')
    # resample by arc length in plan
    s = np.r_[0, np.cumsum(np.hypot(np.diff(xb), np.diff(zr)))]
    t = np.arange(0, s[-1] + 1e-9, step)
    x = np.interp(t, s, xb); z = np.interp(t, s, zr)
    T = np.column_stack([np.gradient(x), np.gradient(z)]); T /= np.linalg.norm(T, axis=1, keepdims=True)
    N = np.column_stack([T[:, 1], -T[:, 0]])                                  # forward (into the contact band)
    Yb = RGI((xs, zs), np.where(np.isfinite(ybot), ybot, 1e3), bounds_error=False, fill_value=1e3)
    Yc = RGI((xs, zs), np.where(np.isfinite(ycar), ycar, -1e3), bounds_error=False, fill_value=-1e3)
    at = lambda F, b: F(np.column_stack([x + b * N[:, 0], z + b * N[:, 1]]))
    # the tip's lowest point: the underside just at and in front of the tip line (lowest over 1 mm), smoothed along the line
    y_u = np.min([at(Yb, TIP_T + b) for b in np.arange(0.0, 1.01, 0.25)], axis=0)
    y_tip = ndi.gaussian_filter1d(y_u, 4.0, mode='nearest') - TIP_EPS
    gap_tip = y_tip - at(Yc, TIP_T)
    # depth of the back edge at the tip: from the top surface down to the tip
    Rt = RayMeshIntersector(E)
    O = np.column_stack([x + TIP_T * N[:, 0], np.full(len(x), 400.0), z + TIP_T * N[:, 1]])
    loc, ir, _ = Rt.intersects_location(O, np.tile([0, -1.0, 0], (len(O), 1)), multiple_hits=False)
    ytop = np.full(len(x), np.nan); ytop[ir] = loc[:, 1]
    return dict(x=x, z=z, N=N, y_tip=y_tip, gap_tip=gap_tip, depth_tip=ytop - y_tip)

def tip_profile(u, m=M_FRONT):
    """height of the tip's surface above its lowest point, at u mm forward of the tip (u <= 0: behind the tip, where the
    spoiler's own underside carries on, so the profile is flat): a circular arc of radius TIP_R at the bottom, running
    into a straight face of slope m (M_FRONT; v14: m may vary per column, flattening to 0 towards the spoiler's ends)"""
    u = np.asarray(u, dtype=np.float32); m = np.asarray(m, dtype=np.float32)
    th = np.arctan(m); us = TIP_R * np.sin(th)
    a = np.clip(u, 0.0, None)
    arc = TIP_R - np.sqrt(np.maximum(TIP_R ** 2 - np.minimum(a, us) ** 2, 0.0))
    return np.where(a <= us, arc, TIP_R * (1 - np.cos(th)) + m * (a - us)).astype(np.float32)

def wall_line(u, m=M_FRONT):
    """the tip's straight front face continued through and behind the tip (height above the lowest point at u)"""
    m = np.asarray(m, dtype=np.float32); th = np.arctan(m); us = TIP_R * np.sin(th)
    return (TIP_R * (1 - np.cos(th)) + m * (np.asarray(u, dtype=np.float32) - us)).astype(np.float32)
