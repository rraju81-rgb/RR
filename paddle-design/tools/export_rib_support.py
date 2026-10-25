#!/usr/bin/env python3
"""Print-ready STL of the rib support (the wave-rib core with its closed frame), one piece per paddle.

    python tools/export_rib_support.py

For each paddle it writes output/rib_support/<design>_rib_support.stl: the whole rib support in one
piece, lying flat (z = 0 .. core thickness) in the print orientation, centred on x = y = 0, mm.  It is
385 mm long, so it needs a large-format bed.  The real part is moulded in carbon fibre in the
two-half wave mould (tools/export_mould.py); this print is the trial piece that checks the mould
closes, or a printed alternative.  Checks (closed mesh, one body, volume, size, bed fit) go to
output/rib_support/rib_support_report.json.
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
BEDS = {"256 x 256 (Bambu X1/P1/A1)": (256, 256), "300 x 300": (300, 300), "360 x 360 (Prusa XL)": (360, 360),
        "400 x 400": (400, 400), "500 x 500": (500, 500)}


def fits(size_x: float, size_y: float, bed: tuple[float, float], margin: float = 3.0) -> bool:
    bx, by = bed[0] - 2 * margin, bed[1] - 2 * margin
    return (size_x <= bx and size_y <= by) or (size_x <= by and size_y <= bx)


def write(shape, path: Path, density: dict = DENSITY) -> dict:
    """Place `shape` flat on z = 0, centred on x = y = 0, export it as STL and check the mesh."""
    bb = shape.bounding_box()
    placed = Pos(-(bb.min.X + bb.max.X) / 2, -(bb.min.Y + bb.max.Y) / 2, -bb.min.Z) * shape
    export_stl(placed, str(path), tolerance=0.02, angular_tolerance=0.1)
    m = trimesh.load(path, force="mesh")
    size = m.bounds[1] - m.bounds[0]
    return dict(file=path.name, triangles=len(m.faces), watertight=bool(m.is_watertight),
                bodies=len(m.split(only_watertight=False)), volume_cm3=round(m.volume / 1000, 2),
                cad_volume_cm3=round(shape.volume / 1000, 2), size_mm=[round(float(v), 1) for v in size],
                mass_g={k: round(m.volume / 1000 * rho, 1) for k, rho in density.items()},
                fits_bed=[k for k, bed in BEDS.items() if fits(size[0], size[1], bed)])


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("*.stl"):                  # the REV C two-piece files must not linger
        old.unlink()
    report = dict(note=f"rib support = {C.core_t:g} mm wave-rib core, frame {C.frame_w:g} mm, wave pitch "
                       f"{C.rib_pitch:g} / wall {C.rib_t:g} / amplitude {C.rib_amp:g} mm, solid to y = {C.solid_to:g} "
                       f"with 45 deg run-outs, M3 insert bore in the butt; one piece, print flat, 100 % infill, "
                       f"no supports", designs={})
    for sp in DESIGNS:
        r = write(cad.rib_core(build(sp)), OUT / f"{sp.key}_rib_support.stl")
        report["designs"][sp.key] = r
        print(f"{sp.name:9s} {r['size_mm']} mm  {r['mass_g']['PA-CF']} g PA-CF  closed={r['watertight']} "
              f"bodies={r['bodies']}  fits: {', '.join(r['fits_bed']) or 'none listed'}")
    (OUT / "rib_support_report.json").write_text(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
