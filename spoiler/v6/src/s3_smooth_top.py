"""Step 3: remove the full-width step (v5 'top lift' edge) on the top surface of the rear part.
For every chordwise column (1 mm apart) a cubic Hermite bridge replaces the top surface over [zs-a, zs+b]
(matching height and slope at both ends, so the natural curvature is kept); each top-surface vertex is then
moved vertically onto the bridge evaluated exactly at its own (x, z)."""
import numpy as np, trimesh
from scipy.ndimage import uniform_filter1d
from trimesh.ray.ray_pyembree import RayMeshIntersector
E = trimesh.load('v6/out/E0.stl')
R = RayMeshIntersector(E)
hx, hz = 1.0, 0.25
xs = np.arange(-560, 560 + 1e-9, hx); zs = np.arange(90, 262 + 1e-9, hz)
X, Z = np.meshgrid(xs, zs, indexing='ij')
O = np.column_stack([X.ravel(), np.full(X.size, 200.0), Z.ravel()]); D = np.tile([0, -1.0, 0], (len(O), 1))
loc, ir, it = R.intersects_location(O, D, multiple_hits=False)
Y = np.full(X.size, np.nan); Y[ir] = loc[:, 1]; Y = Y.reshape(X.shape)
d1 = np.full_like(Y, np.nan); d1[:, 1:-1] = (Y[:, 2:] - Y[:, :-2]) / (2 * hz)
d2 = np.full_like(Y, np.nan); d2[:, 1:-1] = (Y[:, 2:] - 2 * Y[:, 1:-1] + Y[:, :-2]) / hz ** 2
ze = np.array([zs[np.isfinite(Y[i])].max() if np.isfinite(Y[i]).any() else np.nan for i in range(len(xs))])
xa = np.abs(xs)
# --- step / kink line: strongest convex corner (most negative d2) in 150..195, not in the rear-edge rounding
zl = np.full(len(xs), np.nan)
for i in range(len(xs)):
    m = (zs > 150) & (zs < 195) & np.isfinite(d2[i]) & (zs < ze[i] - 3)
    # exclude cliffs (rear-lip end) : slope < -0.4
    m &= ~(d1[i] < -0.4)
    if m.sum() < 20: continue
    v = np.where(m, d2[i], np.inf); k = int(np.argmin(v))
    # also accept concave V-kinks (positive spike) near the ends
    vpos = np.where(m, d2[i], -np.inf); kp = int(np.argmax(vpos))
    if v[k] < -0.15: zl[i] = zs[k]
    elif xa[i] > 460 and vpos[kp] > 0.15: zl[i] = zs[kp]
zsym = np.full(len(xs), np.nan)
for i in range(len(xs)):
    j = np.argmin(np.abs(xs + xs[i]))
    vals = [v for v in (zl[i], zl[j]) if np.isfinite(v)]
    if vals and xa[i] <= 545: zsym[i] = np.mean(vals)
good = np.isfinite(zsym)
zline = uniform_filter1d(np.interp(xs, xs[good], zsym[good]), 15, mode='nearest')
# --- rear limit: first cliff/rounding after the step (slope < -0.4), minus 1 mm; never beyond edge-4
zlim = np.full(len(xs), np.nan)
for i in range(len(xs)):
    if not np.isfinite(ze[i]): continue
    m = (zs > zline[i] + 4.5) & np.isfinite(d1[i]) & (d1[i] < -0.4)
    zc = zs[m].min() - 1.5 if m.any() else ze[i] - 4.0
    zlim[i] = min(zc, ze[i] - 4.0)
a = np.where(xa < 470, 30.0, np.interp(xa, [470, 545], [30.0, 15.0]))
b = np.minimum(30.0, zlim - zline)
act = (xa <= 545) & np.isfinite(b) & (b >= 4.0)
ic = np.argmin(np.abs(xs))
lo = ic
while lo - 1 >= 0 and act[lo - 1]: lo -= 1
hi = ic
while hi + 1 < len(xs) and act[hi + 1]: hi += 1
act[:] = False; act[lo:hi + 1] = True
cols = dict(x=[], za=[], zb=[], ya=[], yb=[], sa=[], sb=[])
for i in np.nonzero(act)[0]:
    y = Y[i]; za = zline[i] - a[i]; zb = zline[i] + b[i]
    k0 = int(np.argmin(np.abs(zs - za))); k1 = int(np.argmin(np.abs(zs - zb)))
    za, zb = zs[k0], zs[k1]
    fm = (zs >= za - 12) & (zs <= za + 1e-6) & np.isfinite(y)
    rm = (zs >= zb - 1e-6) & (zs <= min(zb + 12, zlim[i] + 1e-6)) & np.isfinite(y)
    if fm.sum() < 6 or not np.isfinite(y[k0]) or not np.isfinite(y[k1]): continue
    pf = np.polyfit(zs[fm], y[fm], 2)
    sa = np.polyval(np.polyder(pf), za)
    if rm.sum() >= 9:
        pr = np.polyfit(zs[rm], y[rm], 2); sb = np.polyval(np.polyder(pr), zb)
    else:
        k2 = max(k1 - 6, 0); sb = (y[k1] - y[k2]) / (zs[k1] - zs[k2])   # one-sided slope over the last 1.5 mm
    for kname, val in zip(['x', 'za', 'zb', 'ya', 'yb', 'sa', 'sb'], [xs[i], za, zb, y[k0], y[k1], sa, sb]):
        cols[kname].append(val)
C = {k: np.array(v) for k, v in cols.items()}
# symmetrise the column data (part is mirror symmetric)
def sym(arr):
    out = arr.copy()
    for n, x in enumerate(C['x']):
        j = np.argmin(np.abs(C['x'] + x))
        if abs(C['x'][j] + x) < 1e-6: out[n] = 0.5 * (arr[n] + (arr[j] if arr is not C['sa'] and arr is not C['sb'] else arr[j]))
    return out
for k in ['za', 'zb', 'ya', 'yb', 'sa', 'sb']:
    C[k] = sym(C[k])
print('bridged columns', len(C['x']), ' x range', C['x'].min(), C['x'].max())
def hermite(z, za, zb, ya, yb, sa, sb):
    L = zb - za; t = np.clip((z - za) / L, 0, 1)
    return (2*t**3 - 3*t**2 + 1) * ya + (t**3 - 2*t**2 + t) * L * sa + (-2*t**3 + 3*t**2) * yb + (t**3 - t**2) * L * sb
xend = min(-C['x'].min(), C['x'].max())
print('bridge columns |x| <= %.1f ; taper over the last 12 mm' % xend)
np.savez('v6/out/_smooth_top.npz', **C, zline=zline, xs=xs, xend=xend)
