#!/usr/bin/env python3
"""Print-ready compression mould that forms the rib support in carbon fibre: tray + lid per paddle.

    python tools/export_mould.py

For each paddle it writes to output/mould/:
  <design>_mould_bottom.stl / .step   the tray: pocket of the paddle outline with the bottom teeth
  <design>_mould_top.stl / .step      the lid: plate with the top teeth
Both are in the print orientation, back face on the bed (z = 0), teeth pointing up.  The STEP files
are for machining instead (aluminium, HDPE).  output/mould/mould_report.json holds the cavity,
sizes, volumes, hardware, bed fit and the closed-mesh checks.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from build123d import export_step  # noqa: E402

from paddle import cad, mould  # noqa: E402
from paddle.geometry import CONSTRUCTION as C  # noqa: E402
from paddle.geometry import DESIGNS, build  # noqa: E402

sys.path.insert(0, str(ROOT / "tools"))
from export_rib_support import write  # noqa: E402

OUT = ROOT / "output" / "mould"
DENSITY = {"PLA": 1.24, "PETG": 1.27, "PA-CF": 1.18}           # g/cm3 at 100 % infill
CARBON = 1.50                                                 # g/cm3, moulded chopped carbon/epoxy
M = mould.MOULD


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("*"):                      # the REV D skin-press halves must not linger
        old.unlink()
    report = dict(note=f"tray + lid; the cavity between them is the rib support ({C.core_t:g} mm high, wave walls "
                       f"{C.rib_t:g} mm, frame {C.frame_w:g} mm, solid to y = {C.solid_to:g}); the lid seats on the "
                       f"tray rim, which sets the height. Fill: chopped carbon fibre + epoxy.",
                  core_height_mm=C.core_t, tray_mm=M.tray_height, lid_mm=M.lid, designs={})
    for sp in DESIGNS:
        o = build(sp)
        tray, lid = mould.mould_halves(o)
        lay = mould.layout(o)
        part = cad.rib_core(o, with_hole=False)
        r = {}
        for name, half, top in (("bottom", tray, False), ("top", lid, True)):
            printed = mould.print_pose(half, top)
            export_step(printed, str(OUT / f"{sp.key}_mould_{name}.step"))
            r[name] = write(printed, OUT / f"{sp.key}_mould_{name}.stl", DENSITY)
        r.update(part_volume_cm3=round(part.volume / 1000, 1), part_mass_g=round(part.volume / 1000 * CARBON, 1),
                 bolts_M6=len(lay.bolts), dowel_pins_6x16=len(lay.dowels), pry_notches=len(lay.notches),
                 vents=len(lay.vents), ejectors=len(lay.ejectors),
                 clash_mm3=dict(tray_part=round((tray & part).volume, 3), lid_part=round((lid & part).volume, 3),
                                tray_lid=round((tray & lid).volume, 3)))
        report["designs"][sp.key] = r
        for name in ("bottom", "top"):
            v = r[name]
            print(f"{sp.name:9s} {name:6s} {v['size_mm']} mm  {v['volume_cm3']} cm3 ({v['mass_g']['PLA']} g PLA solid)  "
                  f"closed={v['watertight']} bodies={v['bodies']}  fits: {', '.join(v['fits_bed']) or 'none listed'}")
        print(f"{sp.name:9s} part {r['part_volume_cm3']} cm3 = {r['part_mass_g']} g carbon; clashes {r['clash_mm3']}")
    (OUT / "mould_report.json").write_text(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
