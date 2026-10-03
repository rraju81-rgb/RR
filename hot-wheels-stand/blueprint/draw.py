"""Line-drawing engine for the blueprint: orthographic projection, z-buffer hidden-line removal, sections, dimensions."""
import numpy as np, trimesh
BG, INK, HID, DIM, FILL = "#0f3b7a", "#f2f7ff", "#7fa6dd", "#ffd166", "#1d5199"

def iso_M(elev=25, azim=35):
    ca, sa, ce, se = np.cos(np.radians(azim)), np.sin(np.radians(azim)), np.cos(np.radians(elev)), np.sin(np.radians(elev))
    Ry = np.array([[ca, 0, sa], [0, 1, 0], [-sa, 0, ca]]); Rt = np.array([[1, 0, 0], [0, ce, -se], [0, se, ce]])
    return Rt @ Ry
FRONT = np.eye(3)                                         # look at the wall: screen (x, y), depth z
SIDE = np.array([[0, 0, 1], [0, 1, 0], [-1, 0, 0]])       # from the left (-x): screen (z, y), wall on the left
TOP = np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0]])        # from above: screen (x, -z), wall at the top

class Proj:
    def __init__(self, meshes, M, res=6.0, pad=2.0):
        self.M, self.res = np.asarray(M, float), res
        V = np.vstack([m.vertices for m in meshes]) @ self.M.T
        self.lo = V.min(0)[:2] - pad; hi = V.max(0)[:2] + pad
        self.W, self.H = int((hi[0] - self.lo[0]) * res) + 1, int((hi[1] - self.lo[1]) * res) + 1
        self.zb = np.full((self.H, self.W), -1e9); self.shade = np.full((self.H, self.W), np.nan); self.tag = np.full((self.H, self.W), -1)
        L = np.array([0.35, 0.55, 0.75]); L /= np.linalg.norm(L)
        for k, m in enumerate(meshes):
            v = m.vertices @ self.M.T; n = m.face_normals @ self.M.T
            px = (v[:, 0] - self.lo[0]) * res; py = (v[:, 1] - self.lo[1]) * res
            for f, nn in zip(m.faces, n):
                if nn[2] <= 1e-9: continue
                xs, ys, zs = px[f], py[f], v[f, 2]
                x0, x1 = int(max(0, np.floor(xs.min()))), int(min(self.W - 1, np.ceil(xs.max())))
                y0, y1 = int(max(0, np.floor(ys.min()))), int(min(self.H - 1, np.ceil(ys.max())))
                if x1 < x0 or y1 < y0: continue
                X, Y = np.meshgrid(np.arange(x0, x1 + 1) + .5, np.arange(y0, y1 + 1) + .5)
                d = (ys[1] - ys[2]) * (xs[0] - xs[2]) + (xs[2] - xs[1]) * (ys[0] - ys[2])
                if abs(d) < 1e-12: continue
                a = ((ys[1] - ys[2]) * (X - xs[2]) + (xs[2] - xs[1]) * (Y - ys[2])) / d
                b = ((ys[2] - ys[0]) * (X - xs[2]) + (xs[0] - xs[2]) * (Y - ys[2])) / d
                c = 1 - a - b; inside = (a >= -1e-6) & (b >= -1e-6) & (c >= -1e-6)
                z = a * zs[0] + b * zs[1] + c * zs[2]
                sub = self.zb[y0:y1 + 1, x0:x1 + 1]; upd = inside & (z > sub)
                sub[upd] = z[upd]; self.shade[y0:y1 + 1, x0:x1 + 1][upd] = 0.4 + 0.6 * max(0.0, nn @ L)
                self.tag[y0:y1 + 1, x0:x1 + 1][upd] = k
        self.meshes = meshes
    def p2(self, P): return (np.atleast_2d(P) @ self.M.T)[:, :2]
    def extent(self): return [self.lo[0], self.lo[0] + self.W / self.res, self.lo[1], self.lo[1] + self.H / self.res]
    def edges(self, sharp_deg=25.0, tol=0.35, step=0.25):
        vis, hid = [], []
        for m in self.meshes:
            n = m.face_normals @ self.M.T; fr = n[:, 2] > 1e-6
            adj = m.face_adjacency; ang = m.face_adjacency_angles
            keep = ((ang > np.radians(sharp_deg)) & (fr[adj[:, 0]] | fr[adj[:, 1]])) | (fr[adj[:, 0]] != fr[adj[:, 1]])
            for e in m.face_adjacency_edges[keep]:
                A, B = m.vertices[e[0]] @ self.M.T, m.vertices[e[1]] @ self.M.T
                L = np.linalg.norm(B[:2] - A[:2]); ns = max(2, int(L / step) + 1)
                t = np.linspace(0, 1, ns); P = A[None] + t[:, None] * (B - A)[None]
                ix = np.clip(((P[:, 0] - self.lo[0]) * self.res).astype(int), 0, self.W - 1)
                iy = np.clip(((P[:, 1] - self.lo[1]) * self.res).astype(int), 0, self.H - 1)
                zb = np.max(np.stack([self.zb[np.clip(iy + dy, 0, self.H - 1), np.clip(ix + dx, 0, self.W - 1)] for dx in (-1, 0, 1) for dy in (-1, 0, 1)]), 0)
                ok = P[:, 2] >= np.minimum(zb, self.zb[iy, ix]) - tol
                ok2 = P[:, 2] >= self.zb[iy, ix] - tol
                ok = ok2
                i = 0
                while i < ns - 1:
                    j = i
                    while j < ns - 1 and ok[j + 1] == ok[i]: j += 1
                    seg = P[i:j + 1, :2] if j > i else P[i:i + 2, :2]
                    (vis if ok[i] else hid).append(seg); i = max(j, i + 1)
        return vis, hid

def draw(ax, pr, fill=True, hidden=False, lw=0.6, fillcol=None, alpha=0.55, tint=None):
    from matplotlib.collections import LineCollection
    if fill:
        sh = pr.shade.copy(); img = np.zeros(sh.shape + (4,))
        base = np.array(trimesh.visual.color.hex_to_rgba(FILL)[:3]) / 255.0 if fillcol is None else np.array(fillcol)
        m = ~np.isnan(sh)
        img[m, :3] = base[None] * (0.75 + 0.45 * sh[m, None]); img[m, 3] = alpha
        if tint is not None:
            for k, col in tint.items():
                mk = m & (pr.tag == k); img[mk, :3] = np.array(col)[None] * (0.7 + 0.45 * sh[mk, None])
        ax.imshow(np.clip(img, 0, 1), extent=pr.extent(), origin="lower", interpolation="bilinear", zorder=1)
    vis, hid = pr.edges()
    if hidden and hid: ax.add_collection(LineCollection(hid, colors=HID, linewidths=lw * 0.6, linestyles=(0, (2.5, 1.5)), zorder=2))
    ax.add_collection(LineCollection(vis, colors=INK, linewidths=lw, zorder=3))

def section(ax, mesh, origin, normal, M2, color=INK, hatch="////", lw=0.8):
    """cut mesh with a plane; draw the cut faces hatched. M2: 2x3 matrix mapping 3D -> 2D screen."""
    from matplotlib.patches import Polygon
    s = mesh.section(plane_origin=origin, plane_normal=normal)
    if s is None: return
    for poly in s.discrete:
        P = np.asarray(poly) @ np.asarray(M2).T
        ax.add_patch(Polygon(P, closed=True, facecolor=FILL, edgecolor=color, hatch=hatch, linewidth=lw, zorder=3))

def dim(ax, a, b, off, text=None, fs=6.5, ext=True, color=DIM, unit=""):
    """linear dimension between 2D points a, b, offset perpendicular by off (drawing units = model mm)."""
    a, b = np.asarray(a, float), np.asarray(b, float); d = b - a; L = np.linalg.norm(d)
    if L < 1e-9: return
    u = d / L; nrm = np.array([-u[1], u[0]]); a2, b2 = a + nrm * off, b + nrm * off
    if ext:
        for p, q in ((a, a2), (b, b2)): ax.plot([p[0], q[0] + nrm[0] * np.sign(off) * 1.0], [p[1], q[1] + nrm[1] * np.sign(off) * 1.0], color=color, lw=0.35, zorder=4)
    ax.annotate("", xy=b2, xytext=a2, arrowprops=dict(arrowstyle="<|-|>", color=color, lw=0.5, shrinkA=0, shrinkB=0, mutation_scale=5), zorder=4)
    ang = np.degrees(np.arctan2(u[1], u[0]))
    if ang > 90.1 or ang < -89.9: ang += 180
    mid = (a2 + b2) / 2 + nrm * (0.9 if off >= 0 else -0.9) * 1.0
    ax.text(mid[0], mid[1], text if text is not None else f"{L:.1f}".rstrip("0").rstrip(".") + unit, color=color, fontsize=fs, ha="center", va="center", rotation=ang, zorder=5,
            bbox=dict(boxstyle="square,pad=0.08", fc=BG, ec="none"))

def leader(ax, p, q, text, fs=6.5, color=DIM):
    ax.annotate(text, xy=p, xytext=q, color=color, fontsize=fs, ha="left", va="center", zorder=6,
                arrowprops=dict(arrowstyle="-|>", color=color, lw=0.45, mutation_scale=5, shrinkA=0, shrinkB=0))
