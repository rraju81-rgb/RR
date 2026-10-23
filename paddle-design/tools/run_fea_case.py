#!/usr/bin/env python3
"""Mesh, solve and evaluate one CalculiX case of the half paddle (needs gmsh and ccx).

    python tools/run_fea_case.py elongated WORK/static_elongated            # LC1 + LC2, 1.6 / 3.5 mm mesh
    python tools/run_fea_case.py elongated WORK/modal_elongated --modes 6 --mesh 3.0 5.0
    python tools/run_fea_case.py elongated WORK/baseline_elongated --set rib_amp=3.6 runout_len=0

A static case on the default mesh has about 0.9 M degrees of freedom: about 11 GB of RAM and
10 minutes on 4 cores.  Post-process all cases with tools/fea_report.py --work WORK.
"""
import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402

from paddle import fea  # noqa: E402
from paddle.geometry import CONSTRUCTION, DESIGNS, build  # noqa: E402

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("design", choices=[sp.key for sp in DESIGNS])
ap.add_argument("workdir", type=Path)
ap.add_argument("--mesh", type=float, nargs=2, default=(1.6, 3.5), metavar=("CORE", "SHEETS"),
                help="element size in the core and in the face sheets [mm]")
ap.add_argument("--modes", type=int, default=0, help="natural frequencies instead of the static load cases")
ap.add_argument("--set", nargs="*", default=[], metavar="NAME=VALUE",
                help="override construction parameters, e.g. rib_amp=3.6 runout_len=0")
a = ap.parse_args()

for item in a.set:                     # design-study override of the (frozen) shared construction
    k, v = item.split("=")
    object.__setattr__(CONSTRUCTION, k, float(v))
a.workdir.mkdir(parents=True, exist_ok=True)
o = build(next(sp for sp in DESIGNS if sp.key == a.design))

t0 = time.time()
fea.half_model_step(o, a.workdir / "half.step")
m = fea.mesh_half_model(a.workdir / "half.step", *a.mesh)
np.savez_compressed(a.workdir / "mesh.npz", nodes=m.nodes, **{f"el_{k}": v for k, v in m.elems.items()},
                    **{f"id_{k}": v for k, v in m.eids.items()})
print(f"mesh {time.time() - t0:.0f} s: {len(m.nodes)} nodes, " +
      ", ".join(f"{k} {len(v)}" for k, v in m.elems.items()), flush=True)
loads = [] if a.modes else fea.LOADS
info = fea.write_inp(m, o, a.workdir / "paddle.inp", loads=loads, modes=a.modes)
print("input", json.dumps(info), flush=True)
t, mb = fea.run_ccx(a.workdir / "paddle.inp")
print(f"ccx {t:.0f} s, peak {mb:.0f} MB", flush=True)
if a.modes:
    print("frequencies [Hz]", fea.read_frequencies(a.workdir / "paddle.dat"))
else:
    stresses = fea.read_dat_stresses(a.workdir / "paddle.dat")[:len(loads)]
    res = {lc.key: fea.evaluate(m, o, s) for lc, s in zip(loads, stresses)}
    for lc, u in zip(loads, fea.read_frd_displacements(a.workdir / "paddle.frd")):
        res[lc.key]["max_deflection"] = round(float(np.abs(u[:, 2]).max()), 3)
    fea.save_json(res, a.workdir / "results.json")
    print(json.dumps({k: v["rf"] for k, v in res.items()}, indent=1))
