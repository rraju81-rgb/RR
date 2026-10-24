#!/usr/bin/env python3
"""Print-ready STLs of the rib support (the 8 mm wave-rib core with its closed frame), one paddle at a time.

    python tools/export_rib_support.py

For each paddle it writes to output/rib_support/:
  <design>_rib_support_1piece.stl          one piece, 385 mm long: needs a bed of about 390 x 205 mm
  <design>_rib_support_2piece_A.stl        butt end to y = 242 (handle, throat, lower blade)
  <design>_rib_support_2piece_B.stl        y = 238 to the tip
The two-piece version has a 7 mm solid splice band across the blade at y = 240 with 63 deg flute
run-outs, cut by a dovetail joint (0.1 mm clearance per side) - each piece fits a 256 x 256 mm (or
250 x 210 mm) bed.  Every file lies flat (z = 0 .. 8) in the print orientation, centred on x = y = 0, mm.
Checks (closed mesh, one body, volume, size) go to output/rib_support/rib_support_report.json.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import trimesh  # noqa: E402
from build123d import Pos, export_stl  # noqa: E402

from paddle import cad  # noqa: E402
from paddle.geometry import CONSTRUCTION as C  # noqa: E402
from paddle.geometry import DESIGNS, build  # noqa: E402

OUT = ROOT / "output" / "rib_support"
DENSITY = {"PA-CF": 1.18, "PETG": 1.27, "PLA": 1.24}           # g/cm3 at 100 % infill
BEDS = {"256 x 256 (Bambu X1/P1/A1)": (256, 256), "250 x 210 (Prusa MK4)": (250, 210),
        "300 x 300": (300, 300), "350 x 350": (350, 350), "420 x 420 (large format)": (420, 420)}


def fits(size_x: float, size_y: float, bed: tuple[float, float], margin: float = 3.0) -> bool:
    bx, by = bed[0] - 2 * margin, bed[1] - 2 * margin
    return (size_x <= bx and size_y <= by) or (size_x <= by and size_y <= bx)


def write(shape, path: Path) -> dict:
    bb = shape.bounding_box()
    placed = Pos(-(bb.min.X + bb.max.X) / 2, -(bb.min.Y + bb.max.Y) / 2, -bb.min.Z) * shape
    export_stl(placed, str(path), tolerance=0.02, angular_tolerance=0.1)
    m = trimesh.load(path, force="mesh")
    size = m.bounds[1] - m.bounds[0]
    return dict(file=path.name, triangles=len(m.faces), watertight=bool(m.is_watertight),
                bodies=len(m.split(only_watertight=False)), volume_cm3=round(m.volume / 1000, 2),
                cad_volume_cm3=round(shape.volume / 1000, 2), size_mm=[round(float(v), 1) for v in size],
                mass_g={k: round(m.volume / 1000 * rho, 1) for k, rho in DENSITY.items()},
                fits_bed=[k for k, bed in BEDS.items() if fits(size[0], size[1], bed)])


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    report = dict(note=f"rib support = {C.core_t:g} mm wave-rib core, frame {C.frame_w:g} mm, wave pitch "
                       f"{C.rib_pitch:g} / wall {C.rib_t:g} / amplitude {C.rib_amp:g} mm, solid to y = {C.solid_to:g} "
                       f"with 45 deg run-outs, M3 insert bore in the butt; print flat, 100 % infill, no supports",
                  splice=dict(y=cad.SPLICE_Y, band_mm=cad.SPLICE_BAND, runout_mm=cad.SPLICE_RUNOUT,
                              joint="dovetail tabs on piece A, 20 mm pitch, 5 mm deep, 4 mm clear of the edge, "
                                    "0.1 mm clearance per side"),
                  designs={})
    for sp in DESIGNS:
        o = build(sp)
        one = cad.rib_core(o)
        spliced = cad.rib_core(o, splice=cad.SPLICE_Y)
        a, b = cad.split_core(spliced, cad.SPLICE_Y, o.half_width_at(cad.SPLICE_Y))
        r = {"1piece": write(one, OUT / f"{sp.key}_rib_support_1piece.stl"),
             "2piece_A": write(a, OUT / f"{sp.key}_rib_support_2piece_A.stl"),
             "2piece_B": write(b, OUT / f"{sp.key}_rib_support_2piece_B.stl")}
        report["designs"][sp.key] = r
        for k, v in r.items():
            print(f"{sp.name:9s} {k:9s} {v['size_mm']} mm  {v['mass_g']['PA-CF']} g PA-CF  closed={v['watertight']} "
                  f"bodies={v['bodies']}  fits: {', '.join(v['fits_bed']) or 'none listed'}")
    (OUT / "rib_support_report.json").write_text(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
