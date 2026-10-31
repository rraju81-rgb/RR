#!/usr/bin/env python3
"""Build the MANTA top shell for LMDh and/or LMH and write all exports.

    python scripts/generate.py                 # both classes, default resolution
    python scripts/generate.py --variants lmh  # one class
    python scripts/generate.py --h3 8          # finer mesh (edge length ~8 mm)
    python scripts/generate.py --print-scale 5 --print-wall 2.5   # 1:5 printable solid

Outputs go to exports/<class>/ (see README for the file list).
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from manta.build import build_variant  # noqa: E402
from manta.checks import run_checks  # noqa: E402
from manta.design import VARIANTS  # noqa: E402
from manta.export import write_glb, write_obj, write_stl  # noqa: E402
from manta.solid import thicken  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--variants", nargs="*", default=["lmdh", "lmh"], choices=sorted(VARIANTS))
    ap.add_argument("--out", default=str(ROOT / "exports"))
    ap.add_argument("--h3", type=float, default=14.0, help="target crown edge length [mm]")
    ap.add_argument("--skin", type=float, default=3.0,
                    help="full-scale skin thickness for the solid STL [mm] (default 3)")
    ap.add_argument("--print-scale", type=float, default=5.0,
                    help="scale divisor for the printable display model (5 -> 1:5)")
    ap.add_argument("--print-wall", type=float, default=2.5,
                    help="wall thickness of the printable model, at print scale [mm]")
    ap.add_argument("--no-obj", action="store_true", help="skip the (large) OBJ export")
    args = ap.parse_args(argv)

    for key in args.variants:
        t0 = time.time()
        v = VARIANTS[key]
        b = build_variant(v, h3=args.h3)
        out = Path(args.out) / key
        out.mkdir(parents=True, exist_ok=True)
        p = b.parts
        shell_parts = [p["top_shell_skin"], p["dorsal_fin"]]
        appendages = [p["rear_wing"], p["endplates"], p["mirrors"]]

        # viewer / presentation (metres, Y-up)
        report = run_checks(b)
        write_glb(out / f"manta_{key}.glb",
                  shell_parts + [p["louvre_liners"]] + appendages + [p["context"]],
                  extras=dict(class_name=v.rules.name))
        # CAD / CFD: zero-thickness outer surfaces, millimetres
        write_stl(out / f"manta_{key}_top_shell_surface.stl", shell_parts)
        write_stl(out / f"manta_{key}_aero_appendages.stl", appendages)
        if not args.no_obj:
            write_obj(out / f"manta_{key}_top_shell.obj", shell_parts + appendages,
                      mtl_name=f"manta_{key}.mtl")
        # manufacturing / display: closed solids
        solid = thicken(p["top_shell_skin"], args.skin)
        write_stl(out / f"manta_{key}_top_shell_solid_{args.skin:g}mm.stl", [solid, p["dorsal_fin"]])
        wall_full = args.print_wall * args.print_scale
        display = thicken(p["top_shell_skin"], wall_full)
        fin_print = p["dorsal_fin"]
        write_stl(out / f"manta_{key}_display_1to{args.print_scale:g}.stl", [display, fin_print],
                  scale=1.0 / args.print_scale)

        report["exports"] = sorted(f.name for f in out.iterdir() if f.is_file() and f.name != "report.json")
        (out / "report.json").write_text(json.dumps(report, indent=2))
        n_fail = sum(not c["pass"] for c in report["checks"])
        print(f"[{key}] {len(b.shell.faces):,} shell triangles, "
              f"{n_fail} failed checks, {time.time() - t0:.1f}s -> {out}")
        for c in report["checks"]:
            flag = "PASS" if c["pass"] else "FAIL"
            print(f"   {flag}  {c['name']:<44} {c['value']}")


if __name__ == "__main__":
    main()
