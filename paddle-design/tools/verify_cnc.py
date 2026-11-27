#!/usr/bin/env python3
"""Verify the CNC programs of the stack mould by stock-removal simulation against the mould STLs.

    python tools/verify_cnc.py               # ISO (VMC) programs
    python tools/verify_cnc.py --generic     # also the generic (router) files

Each plate is simulated program by program (OP 10 drilling, then its face programs) on a 0.25 mm
height map; the main plate is turned over for face B with the OP 10 holes carried across.  The result is
compared with the plate's STL cast from the machined side.  Writes output/cnc/verify_report.json and
output/cnc/verify_<face>.png (simulated surface | deviation map).
"""
import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import shapely  # noqa: E402
import trimesh  # noqa: E402

from paddle.cam_mould import (BLANK, FIXTURE, FIXTURE_T, STOCK_T, TOOLS, layout_cache, notch_rect, obstacles,  # noqa: E402
                               plate_outline, pt_m, to_m)
from paddle.cam_sim import Grid, Sim, cast, compare  # noqa: E402
from paddle.mould import BOTTOM, TOP  # noqa: E402
from paddle.mould import MOULD as SPEC  # noqa: E402

OUT = ROOT / "output" / "cnc"
MOULD = ROOT / "output" / "mould"
TOL = 0.03


def files_for(post: str, key: str) -> list[tuple[Path, int | None]]:
    if post == "iso":
        return [(next((OUT / "iso").glob(f"O*_{key}.nc")), None)]
    d = next((OUT / "generic").glob(f"*_{key}"))
    return [(f, int(f.name.split("_")[1][1:])) for f in sorted(d.glob("*.nc"))]


def simulate(grid, H0, keys, post, t):
    """Run the programs in order; each with the obstacles of its set-up (OP 10: toe clamps on the blank;
    main plate faces: 18 bolt heads + clamps; clamp plates: clamps)."""
    sim = Sim(grid, H0, TOOLS, [], z_bottom=-t)
    for key in keys:
        sim.obstacles = ([] if key.startswith("OP00") else
                         obstacles("bolted" if key.startswith(("OP20_main", "OP30_main")) else "clamped"))
        for f, tn in files_for(post, key):
            sim.run(f.read_text(), tn)
    return sim


def expected_zones(XX, YY, plate, main: bool, lay):
    """Where the CAD cannot be met by design: (leftover mask, gouge mask, labels).
    Leftover: R3 at the two cavity corners at the butt and at the notch corners inside the plate (tool radius).
    Gouge: the 0.4 x 45 deg spot chamfers of the bolt holes on a parting face that is not machined (main plate)."""
    left = np.zeros(XX.shape, bool)
    gouge = np.zeros(XX.shape, bool)
    import shapely
    corners = []
    if main:
        corners += [(5.0, 15.0), (5.0, -15.0)]                    # cavity butt corners (paddle (+-15, 5))
    for n in lay.notches:
        for c in list(to_m(notch_rect(n)).exterior.coords)[:-1]:
            if plate.buffer(-0.5).contains(shapely.Point(c)):
                corners.append(c)
    for cx, cy in corners:
        left |= np.hypot(XX - cx, YY - cy) < 4.0
    if main:
        for (x, y), dia in [(b, SPEC.bolt_d) for b in lay.bolts] + [(q, SPEC.dowel_d) for q in lay.dowels]:
            bx, by = pt_m(x, y)
            gouge |= np.hypot(XX - bx, YY - by) < dia / 2 + 0.4 + 0.4
    return left, gouge


def shade_png(path: Path, S, inside, crop) -> None:
    """Shaded relief of the simulated surface, transparent outside the plate (for PB-MO-005)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import LightSource
    i0, i1, j0, j1 = crop
    Z = np.where(inside, np.clip(S, -12.0, 0.0), np.nan)[i0:i1, j0:j1]      # holes read as deep, not -30
    ls = LightSource(azdeg=315, altdeg=40)
    rgb = ls.shade(np.nan_to_num(Z, nan=0.0), cmap=plt.cm.Greys_r, vert_exag=2, blend_mode="overlay",
                   vmin=-14.0, vmax=1.0)
    rgb[..., 3] = np.where(np.isnan(Z), 0.0, 1.0)
    plt.imsave(path, rgb[::-1])


def image(path: Path, S, dev, title: str) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import LightSource, TwoSlopeNorm
    fig, ax = plt.subplots(1, 2, figsize=(16, 5.6), dpi=110)
    ls = LightSource(azdeg=315, altdeg=40)
    ax[0].imshow(ls.shade(np.nan_to_num(S, nan=S[np.isfinite(S)].min()), cmap=plt.cm.Greys_r, vert_exag=3, blend_mode="soft"),
                 origin="lower", aspect="equal")
    ax[0].set_title(f"{title}: simulated surface")
    m = max(0.3, float(np.nanmax(np.abs(dev))))
    im = ax[1].imshow(dev, origin="lower", cmap="RdBu_r", norm=TwoSlopeNorm(0, -min(m, 1.0), min(m, 1.0)), aspect="equal")
    ax[1].set_title("deviation from CAD, mm (red = material left, blue = cut too deep)")
    fig.colorbar(im, ax=ax[1], shrink=0.8)
    for a in ax:
        a.set_xticks([]), a.set_yticks([])
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--generic", action="store_true", help="also verify the generic (router) files")
    ap.add_argument("--cell", type=float, default=0.25)
    args = ap.parse_args()
    outlines, lay = layout_cache()
    pair = (outlines[TOP], outlines[BOTTOM])
    plate_p = plate_outline(pair)
    y_mid = (plate_p.bounds[1] + plate_p.bounds[3]) / 2           # the STLs are centred on the plate
    plate = to_m(plate_p)
    grid = Grid.over(BLANK[0] - 6, BLANK[1] - 6, BLANK[2] + 6, BLANK[3] + 6, args.cell)
    xs, ys = grid.centres()
    XX, YY = np.meshgrid(xs, ys)
    blank = (XX >= BLANK[0]) & (XX <= BLANK[2]) & (YY >= BLANK[1]) & (YY <= BLANK[3])
    region = shapely.contains_xy(plate.buffer(-1.0), XX, YY)
    inside = shapely.contains_xy(plate.buffer(0.5), XX, YY)
    meshes = {k: trimesh.load(MOULD / f"mould_{k}.stl", force="mesh") for k in ("main_plate", "top_plate", "bottom_plate")}
    old = OUT / "verify_report.json"
    report = json.loads(old.read_text()) if old.exists() else {}
    report.update(cell_mm=args.cell, tol_mm=TOL)
    report.setdefault("posts", {})
    posts = ["iso"] + (["generic"] if args.generic else [])
    for post in posts:
        rep = {}
        t0 = time.time()
        # fixture: safety checks only
        gf = Grid.over(FIXTURE[0] - 6, FIXTURE[1] - 6, FIXTURE[2] + 6, FIXTURE[3] + 6, 0.5)
        fx, fy = np.meshgrid(*gf.centres())
        H0 = np.where((fx >= FIXTURE[0]) & (fx <= FIXTURE[2]) & (fy >= FIXTURE[1]) & (fy <= FIXTURE[3]), 0.0, -1e3)
        sim = simulate(gf, H0, ["OP00_fixture_plate"], post, FIXTURE_T)
        rep["fixture"] = dict(events=[vars(e) for e in sim.events], removed_cm3={f"T{k}": round(v, 1)
                                                                                for k, v in sim.removed.items()})
        cases = [("main_A", "main_plate", ["OP10_main_plate_drill", "OP20_main_plate_face_A_elongated"], STOCK_T["main"],
                  False, "bolted"),
                 ("main_B", "main_plate", ["OP30_main_plate_face_B_hybrid"], STOCK_T["main"], True, "bolted"),
                 ("top_clamp", "top_plate", ["OP10_clamp_plates_drill", "OP20_top_clamp_plate"], STOCK_T["clamp"], False,
                  "clamped"),
                 ("bottom_clamp", "bottom_plate", ["OP10_clamp_plates_drill", "OP20_bottom_clamp_plate"], STOCK_T["clamp"],
                  False, "clamped")]
        holes = None
        for name, mesh_key, keys, t, flip, kind in cases:
            H0 = np.where(blank, 0.0, -1e3)
            if name == "main_B":
                H0 = np.where(holes[::-1, :], -t - 1.0, H0)               # OP 10 holes, plate turned over about X
            sim = simulate(grid, H0, keys, post, t)
            S = np.maximum(sim.H, -t)                                # nothing exists below the plate
            if name == "main_A":
                hs = Sim(grid, np.where(blank, 0.0, -1e3), TOOLS, [], -t)
                for f, tn in files_for(post, "OP10_main_plate_drill"):
                    hs.run(f.read_text(), tn)
                holes = hs.H < -t + 1e-3
            m = meshes[mesh_key]
            top = m.bounds[1][2]
            if flip:      # face B up: paddle x = Y, heights cast from below, Z = -z
                T = cast(m, grid, lambda X, Y: (Y, X - y_mid), True, inside)
                T = -T
            else:         # paddle x = -Y; Z = z - stock top
                T = cast(m, grid, lambda X, Y: (-Y, X - y_mid), False, inside)
                T = T - (t if mesh_key != "main_plate" else top)
            T = np.where(np.isnan(T), -t, np.maximum(T, -t))
            gouge, left, st = compare(S, T, region, TOL)
            exp_l, exp_g = expected_zones(XX, YY, plate, mesh_key == "main_plate", lay)
            st["max_leftover_other"] = float(np.where(exp_l, 0.0, left).max())
            st["max_gouge_other"] = float(np.where(exp_g, 0.0, gouge).max())
            st["max_leftover_expected"] = float(np.where(exp_l, left, 0.0).max())
            st["max_gouge_expected"] = float(np.where(exp_g, gouge, 0.0).max())
            dev = np.where(region, np.where(left > TOL, left, np.where(gouge > TOL, -gouge, 0.0)), np.nan)
            st.update(events=[vars(e) for e in sim.events], removed_cm3={f"T{k}": round(v, 1) for k, v in sim.removed.items()},
                      moves=sim.n)
            # where are the deviations?  report the largest clusters
            from scipy.ndimage import label
            for kind_, arr in (("leftover", left), ("gouge", gouge)):
                lab, nlab = label(arr > TOL)
                clusters = []
                for k in range(1, nlab + 1):
                    sel = lab == k
                    v = float(arr[sel].max())
                    jj, ii = np.nonzero(sel.T)
                    clusters.append(dict(max=round(v, 3), cells=int(sel.sum()), X=round(float(xs[jj].mean()), 1),
                                         Y=round(float(ys[ii].mean()), 1)))
                clusters.sort(key=lambda c: (-c["cells"] * c["max"]))
                st[f"{kind_}_clusters"] = clusters[:30]
                st[f"{kind_}_cluster_count"] = nlab
            rep[name] = st
            if post == "iso":
                image(OUT / f"verify_{name}.png", np.where(inside, S, np.nan), dev, name.replace("_", " ").upper())
                ii, jj = np.nonzero(inside)
                shade_png(OUT / f"sim_{name}.png", S, inside, (ii.min(), ii.max() + 1, jj.min(), jj.max() + 1))
            print(f"{post:7s} {name:12s} moves {sim.n:6d}  events {len(sim.events):3d}  gouge {st['max_gouge_other']:.3f} "
                  f"(expected {st['max_gouge_expected']:.3f})  leftover {st['max_leftover_other']:.3f} (expected "
                  f"{st['max_leftover_expected']:.3f})  out of tol: {st['gouge_cells']} / {st['leftover_cells']} of "
                  f"{st['cells']} cells")
        print(f"{post}: {time.time() - t0:.0f} s")
        report["posts"][post] = rep
    (OUT / "verify_report.json").write_text(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
