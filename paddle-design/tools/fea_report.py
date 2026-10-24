#!/usr/bin/env python3
"""Post-process the CalculiX runs into result JSON, contour figures and the PDF stress report.

    python tools/fea_report.py --work WORKDIR

WORKDIR holds the runs written by tools/run_fea_case.py:
    static_elongated/  static_hybrid/   final design, load cases LC1 + LC2   (modes = 0)
    baseline_elongated/                 first core version (rib_amp 3.6, runout_len 0), optional
    modal_elongated/   modal_hybrid/    natural frequencies (modes = 6), optional
"""
import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from paddle import fea  # noqa: E402
from paddle import fea_report as fr  # noqa: E402
from paddle.export import Chromium  # noqa: E402
from paddle.geometry import CONSTRUCTION as C  # noqa: E402
from paddle.geometry import DESIGNS, build  # noqa: E402

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("--work", type=Path, required=True)
ap.add_argument("--out", type=Path, default=ROOT / "output" / "fea")
ap.add_argument("--json", type=Path, default=ROOT / "analysis" / "fea")
ap.add_argument("--render-core", action="store_true",
                help="render the core coloured by von Mises stress with Blender (Fig. 5 of the report)")
a = ap.parse_args()
a.out.mkdir(parents=True, exist_ok=True)
a.json.mkdir(parents=True, exist_ok=True)
lcs = [lc.key for lc in fea.LOADS]

outlines = {sp.key: build(sp) for sp in DESIGNS}
cases = [fr.load_case(outlines[k], a.work / f"static_{k}") for k in outlines]
stats = {c.name: {lc: fr.case_stats(c, i) for i, lc in enumerate(lcs)} for c in cases}
for c, k in zip(cases, outlines):
    fea.save_json(stats[c.name], a.json / f"static_{k}.json")
    print(c.name, {lc: stats[c.name][lc]["rf"] for lc in lcs})

baseline = None
if (a.work / "baseline_elongated").exists():
    b = fr.load_case(outlines["elongated"], a.work / "baseline_elongated")
    baseline = {lc: fr.case_stats(b, i) for i, lc in enumerate(lcs)}
    fea.save_json(dict(note="first core version: rib_amp 3.6 mm (2.7 mm lands), square flute ends (runout_len 0)",
                       **baseline), a.json / "baseline_elongated_static.json")

modal = {}
for c, k in zip(cases, outlines):
    dat = a.work / f"modal_{k}" / "paddle.dat"
    modal[c.name] = fea.read_frequencies(dat) if dat.exists() else []
fea.save_json(dict(note=f"bending modes of the half model (symmetric), grip clamped y={fea.GRIP_Y[0]:g}..{fea.GRIP_Y[1]:g}",
                   frequencies_hz=modal), a.json / "modal.json")

mass_json = ROOT / "analysis" / "mass_properties.json"
if not mass_json.exists():
    sys.exit(f"{mass_json} is missing: run tools/export_cad.py first (it weighs the assembly with the printed grip)")
mass = json.loads(mass_json.read_text())

mesh = {}
for c in cases:
    _, area = fea.patch_faces(c.m, fea.LOADS[0], C.thickness / 2)
    mesh[c.name] = dict(n_nodes=len(c.m.nodes), n_elems=int(sum(len(v) for v in c.m.elems.values())), patch_area=area)

fr.fig_deflection(cases, a.out / "fea_deflection.png")
fr.fig_face_stress(cases, a.out / "fea_face_sheet_stress.png")
fr.fig_bond_shear(cases, a.out / "fea_bond_shear.png")
profiles = {c.name: fr.bond_profile(c, 1) for c in cases}
fea.save_json(profiles, a.json / "bond_shear_profile_LC2.json")
fr.fig_bond_profile(profiles, a.out / "fea_bond_profile.png", fea.ALLOW["bond_shear"])

vmax = fr._ceil(max(stats[c.name]["LC2"]["core_vm"]["value"] for c in cases), 2.0)
for c, k in zip(cases, outlines):
    fr.core_vm_ply(c, 1, a.work / f"core_vm_{k}.ply", vmax)
fr.fp.colourbar_png(a.out / "fea_core_von_mises_scale.png", vmax, "core von Mises stress [MPa], tip impact")
fea.save_json(dict(vmax=vmax), a.work / "core_vm_scale.json")
if a.render_core:
    from paddle.render3d import render_stress_cores
    render_stress_cores({k: a.work / f"core_vm_{k}.ply" for k in outlines}, a.out / "fea_core_von_mises_scale.png",
                        a.out / "fea_core_von_mises.png", a.work)


def rel(p: Path):
    return os.path.relpath(p, a.out) if p.exists() else None


figs = dict(deflection="fea_deflection.png", face="fea_face_sheet_stress.png", bond="fea_bond_shear.png",
            profile="fea_bond_profile.png",
            core="fea_core_von_mises.png" if (a.out / "fea_core_von_mises.png").exists() else None,
            cutaway=rel(ROOT / "output" / "render" / "paddles_3d_cutaway.png"))
html = a.out / "paddle_stress_report.html"
fr.write_report(dict(stats=stats, baseline=baseline, mesh=mesh, modal=modal,
                     mass={k: mass[k] for k in ("grip", *outlines) if k in mass}, figs=figs, date=date.today().isoformat()), html)
with Chromium() as ch:
    ch.html_pdf(html, html.with_suffix(".pdf"))
print("report ->", html.with_suffix(".pdf"))
