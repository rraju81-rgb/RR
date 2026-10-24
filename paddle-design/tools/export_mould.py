#!/usr/bin/env python3
"""Print-ready compression mould for each paddle: one STL (print it twice) plus STEP for CNC.

    python tools/export_mould.py

For each paddle it writes to output/mould/:
  <design>_mould_half.stl    one mould half in the print orientation: back face on the bed (z = 0),
                             pocket opening upwards.  Both halves are this part: turn the second one
                             over onto the first, so the two pockets face each other.
  <design>_mould_half.step   the same solid for machining (aluminium, HDPE, MDF ...).
and output/mould/mould_report.json (cavity, sizes, volume, hardware, bed fit, closed-mesh checks).
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from build123d import Pos, export_step  # noqa: E402

from paddle import mould  # noqa: E402
from paddle.geometry import CONSTRUCTION as C  # noqa: E402
from paddle.geometry import DESIGNS, build  # noqa: E402

sys.path.insert(0, str(ROOT / "tools"))
from export_rib_support import write  # noqa: E402

OUT = ROOT / "output" / "mould"
DENSITY = {"PLA": 1.24, "PETG": 1.27, "PA-CF": 1.18}           # g/cm3 at 100 % infill
M = mould.MOULD


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    report = dict(note=f"two identical halves split on the paddle mid-plane; pocket {M.depth:g} deep each, so the "
                       f"closed cavity is {C.thickness:g} mm = skin {C.face_t:g} + rib support {C.core_t:g} + skin "
                       f"{C.face_t:g}; pocket = body outline + {M.clearance:g} mm, {M.draft:g} deg draft",
                  cavity_mm=C.thickness, pocket_depth_mm=M.depth, plate_mm=M.height, designs={})
    for sp in DESIGNS:
        o = build(sp)
        half = mould.mould_half(o)
        lay = mould.layout(o)
        printed = Pos(0, 0, M.height) * half                     # back face on the bed, pocket up
        export_step(printed, str(OUT / f"{sp.key}_mould_half.step"))
        r = write(half, OUT / f"{sp.key}_mould_half.stl", DENSITY)
        r.update(print_count=2, bolts_M6=len(lay.bolts), dowel_pins_6x20=len(lay.dowels), pry_notches=len(lay.notches),
                 vents=len(lay.vents))
        report["designs"][sp.key] = r
        print(f"{sp.name:9s} {r['size_mm']} mm  {r['volume_cm3']} cm3 ({r['mass_g']['PLA']} g PLA solid)  "
              f"closed={r['watertight']} bodies={r['bodies']}  {len(lay.bolts)} x M6, {len(lay.dowels)} dowels  "
              f"fits: {', '.join(r['fits_bed']) or 'none listed: needs a 440 mm bed or CNC'}")
    (OUT / "mould_report.json").write_text(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
