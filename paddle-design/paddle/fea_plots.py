"""Post-processing of the CalculiX results: plan-view contour plots and colour-mapped meshes."""
from __future__ import annotations

from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Circle, Rectangle  # noqa: E402
from matplotlib.tri import Triangulation  # noqa: E402

from .fea import FACES, GRIP_Y, LoadCase, Mesh, von_mises  # noqa: E402
from .geometry import CONSTRUCTION as C  # noqa: E402
from .geometry import Outline  # noqa: E402

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9})


def load_mesh(npz: Path) -> Mesh:
    z = np.load(npz)
    m = Mesh(z["nodes"], {k: z["el_" + k] for k in ("TOP", "CORE", "BOT")})
    m.eids = {k: z["id_" + k] for k in ("TOP", "CORE", "BOT")}
    return m


def plane_tris(m: Mesh, key: str, axis: int, value: float) -> tuple[np.ndarray, np.ndarray]:
    """Corner-node triangles (1-based ids) of the element faces of a set lying on a plane, and their element row."""
    conn = m.elems[key][:, :4]
    tris, rows = [], []
    for f in FACES:
        tri = conn[:, list(f)]
        on = np.all(np.abs(m.nodes[tri - 1, axis] - value) < 1e-6, axis=1)
        tris.append(tri[on])
        rows.append(np.nonzero(on)[0])
    return np.vstack(tris), np.concatenate(rows)


def boundary_tris(m: Mesh, key: str) -> np.ndarray:
    """Corner-node triangles of the faces bounding an element set (faces used by one element only)."""
    conn = m.elems[key][:, :4]
    faces = np.vstack([conn[:, list(f)] for f in FACES])
    srt = np.sort(faces, axis=1)
    _, inv, cnt = np.unique(srt, axis=0, return_inverse=True, return_counts=True)
    return faces[cnt[inv.ravel()] == 1]


def element_max(m: Mesh, key: str, rows: np.ndarray, vals: np.ndarray) -> np.ndarray:
    """Per-element maximum of integration-point values (array indexed like m.elems[key])."""
    idx = rows[:, 0].astype(np.int64) - int(m.eids[key][0])
    out = np.full(len(m.elems[key]), -np.inf)
    np.maximum.at(out, idx, vals)
    return out


def nodal_average(m: Mesh, key: str, elem_vals: np.ndarray) -> np.ndarray:
    """Average element values onto the corner nodes of one set (NaN for nodes outside the set)."""
    conn = m.elems[key][:, :4] - 1
    acc = np.zeros(len(m.nodes))
    cnt = np.zeros(len(m.nodes))
    for k in range(4):
        np.add.at(acc, conn[:, k], elem_vals)
        np.add.at(cnt, conn[:, k], 1)
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(cnt > 0, acc / cnt, np.nan)


def fibre_stress(s: np.ndarray) -> np.ndarray:
    return np.max(np.abs(s[:, 0:2]), axis=1)


def transverse_shear(s: np.ndarray) -> np.ndarray:
    return np.hypot(s[:, 4], s[:, 5])


# ---------------------------------------------------------------- plan-view panels
def plan_panel(ax, o: Outline, m: Mesh, tris: np.ndarray, nodal: np.ndarray, vmin: float, vmax: float,
               cmap: str, lc: LoadCase | None, title: str, peak: tuple[float, float, float] | None = None,
               unit: str = "MPa", fmt_peak: str = "{:.0f}") -> matplotlib.cm.ScalarMappable:
    P = m.nodes
    n = len(P)
    x = np.concatenate([P[:, 0], -P[:, 0]])
    y = np.concatenate([P[:, 1], P[:, 1]])
    v = np.concatenate([nodal, nodal])
    t0 = tris - 1
    t1 = t0[:, [0, 2, 1]] + n
    tri = Triangulation(x, y, np.vstack([t0, t1]))
    good = np.isfinite(v)
    v = np.where(good, v, vmin)
    pc = ax.tripcolor(tri, v, shading="gouraud", cmap=cmap, vmin=vmin, vmax=vmax, rasterized=True)
    ol = np.array(o.polyline(1.0) + [o.polyline(1.0)[0]])
    ax.plot(ol[:, 0], ol[:, 1], color="#111", lw=0.8)
    h = o.spec.handle_width / 2
    ax.add_patch(Rectangle((-h - 3, GRIP_Y[0]), 2 * h + 6, GRIP_Y[1] - GRIP_Y[0], fill=False, hatch="////",
                           ec="#555", lw=0.6))
    ax.text(h + 6, (GRIP_Y[0] + GRIP_Y[1]) / 2, "grip\n(clamped)", fontsize=7, color="#444", va="center")
    if lc is not None:
        ax.add_patch(Circle((lc.x, lc.y), lc.diameter / 2, fill=False, ec="white", lw=1.2, ls="--"))
        ax.add_patch(Circle((lc.x, lc.y), lc.diameter / 2, fill=False, ec="black", lw=0.5, ls="--"))
    if peak is not None:
        ax.plot([peak[0]], [peak[1]], marker="x", ms=7, mew=1.6, color="white")
        ax.plot([peak[0]], [peak[1]], marker="x", ms=6, mew=0.8, color="black")
        ax.annotate(f"max {fmt_peak.format(peak[2])} {unit}", (peak[0], peak[1]), xytext=(18, 22),
                    textcoords="offset points", fontsize=7.5, fontweight="bold",
                    arrowprops=dict(arrowstyle="-", lw=0.6, color="#222"),
                    bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="#888", lw=0.5))
    ax.set_aspect("equal")
    ax.set_xlim(-o.spec.width / 2 - 14, o.spec.width / 2 + 14)
    ax.set_ylim(-4, o.spec.length + 8)
    ax.set_title(title, fontsize=9, fontweight="bold")
    ax.axis("off")
    return pc


def contour_figure(panels: list[dict], cbar_label: str, outfile: Path, cmap: str = "turbo",
                   vmin: float = 0.0, vmax: float | None = None, suptitle: str = "", unit: str = "MPa",
                   fmt_peak: str = "{:.0f}") -> None:
    """panels: dicts with o, m, tris, nodal, lc, title, peak."""
    if vmax is None:
        vmax = max(float(np.nanmax(p["nodal"][np.unique(p["tris"]) - 1])) for p in panels)
    fig, axes = plt.subplots(1, len(panels), figsize=(2.55 * len(panels) + 0.9, 5.4))
    axes = np.atleast_1d(axes)
    pc = None
    for ax, p in zip(axes, panels):
        pc = plan_panel(ax, p["o"], p["m"], p["tris"], p["nodal"], vmin, vmax, cmap, p.get("lc"), p["title"],
                        p.get("peak"), unit, fmt_peak)
    cb = fig.colorbar(pc, ax=list(axes), fraction=0.025, pad=0.02)
    cb.set_label(cbar_label)
    if suptitle:
        fig.suptitle(suptitle, fontsize=11, fontweight="bold", x=0.02, ha="left")
    fig.savefig(outfile, dpi=200, bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------- colour-mapped mesh (Blender)
def colour_map(vals: np.ndarray, vmax: float, cmap: str = "turbo", vmin: float = 0.0) -> np.ndarray:
    cm = matplotlib.colormaps[cmap]
    t = np.clip((vals - vmin) / (vmax - vmin), 0, 1)
    return (np.asarray(cm(t))[:, :3] * 255).astype(np.uint8)


def write_ply(path: Path, verts: np.ndarray, tris: np.ndarray, colours: np.ndarray) -> None:
    with open(path, "wb") as fh:
        fh.write((f"ply\nformat binary_little_endian 1.0\nelement vertex {len(verts)}\n"
                  "property float x\nproperty float y\nproperty float z\n"
                  "property uchar red\nproperty uchar green\nproperty uchar blue\n"
                  f"element face {len(tris)}\nproperty list uchar int vertex_indices\nend_header\n").encode())
        vt = np.zeros(len(verts), dtype=[("x", "<f4"), ("y", "<f4"), ("z", "<f4"),
                                         ("r", "u1"), ("g", "u1"), ("b", "u1")])
        vt["x"], vt["y"], vt["z"] = verts[:, 0], verts[:, 1], verts[:, 2]
        vt["r"], vt["g"], vt["b"] = colours[:, 0], colours[:, 1], colours[:, 2]
        fh.write(vt.tobytes())
        ft = np.zeros(len(tris), dtype=[("n", "u1"), ("i", "<i4", (3,))])
        ft["n"] = 3
        ft["i"] = tris
        fh.write(ft.tobytes())


def mirrored_surface_ply(m: Mesh, key: str, nodal: np.ndarray, vmax: float, path: Path,
                         cmap: str = "turbo", drop_symmetry_plane: bool = True) -> None:
    """Boundary surface of an element set, mirrored about x = 0, coloured by a nodal field."""
    tris = boundary_tris(m, key)
    if drop_symmetry_plane:
        tris = tris[~np.all(np.abs(m.nodes[tris - 1, 0]) < 1e-6, axis=1)]
    used = np.unique(tris)
    remap = np.zeros(len(m.nodes) + 1, dtype=np.int64)
    remap[used] = np.arange(len(used))
    v = m.nodes[used - 1]
    val = np.nan_to_num(nodal[used - 1], nan=0.0)
    col = colour_map(val, vmax, cmap)
    t = remap[tris]
    vm = v.copy()
    vm[:, 0] *= -1
    verts = np.vstack([v, vm])
    faces = np.vstack([t, t[:, [0, 2, 1]] + len(v)])
    write_ply(path, verts, faces, np.vstack([col, col]))


def colourbar_png(path: Path, vmax: float, label: str, cmap: str = "turbo", vmin: float = 0.0) -> None:
    fig, ax = plt.subplots(figsize=(4.2, 0.62))
    cb = matplotlib.colorbar.ColorbarBase(ax, cmap=matplotlib.colormaps[cmap],
                                          norm=matplotlib.colors.Normalize(vmin, vmax), orientation="horizontal")
    cb.set_label(label)
    fig.savefig(path, dpi=220, bbox_inches="tight", transparent=True)
    plt.close(fig)


__all__ = ["load_mesh", "plane_tris", "boundary_tris", "element_max", "nodal_average", "fibre_stress",
           "transverse_shear", "contour_figure", "mirrored_surface_ply", "colourbar_png", "von_mises", "C"]
