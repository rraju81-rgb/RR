#!/usr/bin/env python3
"""Generate the ten pickleball grip STLs (fitment identical to PickleballGrip_1.3mf).

usage:  python3 generate_grips.py [--only 01 07 ...] [--res 0.25]
Outputs ../stl/<id>.stl and ../data/<id>_colors.npz (render-only colour map).
"""
import argparse
import sys
import time
import warnings
from pathlib import Path

import numpy as np
import trimesh
from scipy.ndimage import gaussian_filter

sys.path.insert(0, str(Path(__file__).resolve().parent))
from grip_core import Frame, build_mesh_reduced, cut_windows, write_stl  # noqa: E402
from designs import DESIGNS, Ctx  # noqa: E402

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parent.parent


SMOOTH_SIGMA = 0.25      # mm - Gaussian rounding of the texture height field (sub-nozzle, kills stair-steps)
SUPERSAMPLE = 3          # 3 x 3 sub-samples per mesh node (anti-aliased feature edges)


def evaluate(F, fn, res, ss=SUPERSAMPLE):
    """Evaluate a design on an ss x ss supersampled grid, box-filter down, then round the height
    field with a small Gaussian (sigma << nozzle) so steep edges become clean smooth ramps."""
    ctx = Ctx(F, res=res)
    S0, Z0, ds = ctx.S2.copy(), ctx.Z2.copy(), F.L / F.N
    offs = [((k + .5) / ss - .5) for k in range(ss)]
    t = rgb = 0
    for a in offs:
        for b in offs:
            ctx.S2, ctx.Z2 = S0 + a * ds, Z0 + b * res
            d = fn(ctx)
            t = t + d["t"] / ss ** 2
            rgb = rgb + np.asarray(d["rgb"], float) / ss ** 2
    ctx.S2, ctx.Z2 = S0, Z0
    d0 = fn(ctx)                                  # unshifted pass: discrete colour classes for the 3MF export
    sig = d0.get("sigma", SMOOTH_SIGMA)
    t = np.clip(gaussian_filter(t, (sig / res, sig / ds), mode=("nearest", "wrap")), 0, 1)
    return ctx, dict(d0, t=t, rgb=rgb, cls=d0["cls"])


def generate(F, name, label, fn, res):
    t0 = time.time()
    ctx, d = evaluate(F, fn, res)
    z, H, _ = F.skin(d["t"], res)
    V, Fc = build_mesh_reduced(F, z, H)
    if d.get("holes"):
        V, Fc = cut_windows(F, V, Fc, d["holes"])
    m = trimesh.Trimesh(V, Fc, process=False)
    (ROOT / "stl").mkdir(exist_ok=True)
    write_stl(ROOT / "stl" / f"{name}.stl", V, Fc)
    np.savez_compressed(ROOT / "data" / f"{name}_colors.npz", rgb=np.clip(d["rgb"], 0, 255).astype(np.uint8), z=ctx.Z,
                        cls=d["cls"].astype(np.uint8), palette=np.array(d["palette"], np.uint8), collar=d["collar"])
    print(f"{name:18s} tris={len(Fc):7d} watertight={m.is_watertight} vol={m.volume/1000:6.2f} cm3 "
          f"bbox={np.round(m.extents, 2).tolist()} {time.time() - t0:5.1f}s", flush=True)
    return m


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*", default=None)
    ap.add_argument("--res", type=float, default=0.25, help="surface sampling step in mm")
    a = ap.parse_args()
    F = Frame(ds=a.res)
    print(f"crest perimeter L={F.L:.2f} mm, {F.N} columns")
    for name, label, fn in DESIGNS:
        if a.only and not any(name.startswith(o) for o in a.only):
            continue
        generate(F, name, label, fn, a.res)
