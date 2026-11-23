#!/usr/bin/env python3
"""Print-ready stack mould that forms both rib supports in carbon fibre: three plates, one press.

    python tools/export_mould.py

It writes to output/mould/:
  mould_main_plate.stl / .step     the main plate: Elongated cavity in the top face, Hybrid cavity in the
                                   bottom face, solid web between (one piece, Elongated face up)
  mould_main_upper_half.stl        the main plate split through the middle of the web, for printing:
  mould_main_lower_half.stl          each half with its cavity up; the stack bolts clamp them together
  mould_top_plate.stl / .step      top clamp plate with the Elongated top-flute teeth
  mould_bottom_plate.stl / .step   bottom clamp plate with the Hybrid top-flute teeth
All are in the print orientation, back face on the bed (z = 0), teeth pointing up.  The STEP files
are for machining instead (aluminium, HDPE).  output/mould/mould_report.json holds the sizes,
volumes, the charges, hardware, bed fit, the closed-mesh checks and the cavity checks.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from build123d import export_step, extrude  # noqa: E402

from paddle import cad, mould  # noqa: E402
from paddle.geometry import CONSTRUCTION as C  # noqa: E402
from paddle.geometry import DESIGNS, build  # noqa: E402

sys.path.insert(0, str(ROOT / "tools"))
from export_rib_support import write  # noqa: E402

OUT = ROOT / "output" / "mould"
DENSITY = {"PLA": 1.24, "PETG": 1.27, "PA-CF": 1.18}           # g/cm3 at 100 % infill
CARBON = 1.50                                                 # g/cm3, moulded chopped carbon/epoxy
OVERFILL = 1.10                                               # charge = part + 10 % that leaves as flash
M = mould.MOULD


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("*"):                      # the REV G per-paddle trays and lids must not linger
        if old.suffix in (".stl", ".step", ".json"):  # (the PB-MO-003 drawing written by build.py stays)
            old.unlink()
    outlines = {sp.key: build(sp) for sp in DESIGNS}
    o_top, o_bot = outlines[mould.TOP], outlines[mould.BOTTOM]
    top, main_plate, bottom = mould.mould_stack(o_top, o_bot)
    upper, lower = mould.main_halves(main_plate)
    lay = mould.layout((o_top, o_bot))
    report = dict(note=f"stack mould for both paddles: main plate {M.main:g} mm ({mould.TOP} cavity in the top face, "
                       f"{M.web:g} mm web, {mould.BOTTOM} cavity in the bottom face) between two {M.clamp:g} mm clamp "
                       f"plates that carry the top-flute teeth. Each cavity is the {C.core_t:g} mm rib support (wave "
                       f"walls {C.rib_t:g} mm, frame {C.frame_w:g} mm, solid to y = {C.solid_to:g}); the clamp plates "
                       f"seat flat on the main plate. Fill: chopped carbon fibre + epoxy.",
                  top_cavity=mould.TOP, bottom_cavity=mould.BOTTOM, main_mm=M.main, web_mm=M.web, clamp_mm=M.clamp,
                  stack_mm=M.height, core_height_mm=C.core_t, bolts_M6=len(lay.bolts), pry_notches=len(lay.notches),
                  vents_per_face=len(lay.vents), plates={}, cavities={})
    for name, shape, pose, step in (("main_plate", main_plate, "main", True), ("main_upper_half", upper, "upper", False),
                                    ("main_lower_half", lower, "lower", False), ("top_plate", top, "top", True),
                                    ("bottom_plate", bottom, "bottom", True)):
        printed = mould.print_pose(shape, pose)
        if step:
            export_step(printed, str(OUT / f"mould_{name}.step"))
        report["plates"][name] = write(printed, OUT / f"mould_{name}.stl", DENSITY)
    for key, up, clamp in ((mould.TOP, True, top), (mould.BOTTOM, False, bottom)):
        o = outlines[key]
        part = mould.place(cad.rib_core(o, with_hole=False), up)
        slab = mould.place(extrude(cad.outline_face(o, -M.h), amount=2 * M.h), up)
        cavity = slab - main_plate - clamp
        open_cm3 = (slab - main_plate).volume / 1000                     # room for the loose charge, clamp off
        v = part.volume / 1000
        report["cavities"][key] = dict(
            face="top" if up else "bottom", part_volume_cm3=round(v, 1), part_mass_g=round(v * CARBON, 1),
            charge_g=round(v * CARBON * OVERFILL), open_volume_cm3=round(open_cm3, 1),
            open_over_part=round(open_cm3 / v, 2),
            cavity_vs_part_mm3=round((cavity - part).volume + (part - cavity).volume, 3),
            clash_mm3=dict(main=round((part & main_plate).volume, 3), clamp=round((part & clamp).volume, 3)))
    report["clash_mm3"] = dict(top_main=round((top & main_plate).volume, 3),
                               bottom_main=round((bottom & main_plate).volume, 3))
    for name, v in report["plates"].items():
        print(f"{name:16s} {v['size_mm']} mm  {v['volume_cm3']} cm3 ({v['mass_g']['PLA']} g PLA solid)  "
              f"closed={v['watertight']} bodies={v['bodies']}  fits: {', '.join(v['fits_bed']) or 'none listed'}")
    for key, r in report["cavities"].items():
        print(f"{key:9s} ({r['face']} face): part {r['part_volume_cm3']} cm3 = {r['part_mass_g']} g carbon, charge "
              f"{r['charge_g']} g; open cavity {r['open_over_part']}x the part; cavity vs part {r['cavity_vs_part_mm3']} mm3; "
              f"clashes {r['clash_mm3']}")
    print("plates clash", report["clash_mm3"])
    (OUT / "mould_report.json").write_text(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
