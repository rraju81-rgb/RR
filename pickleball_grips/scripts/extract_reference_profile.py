#!/usr/bin/env python3
"""Extract the fitment-critical profile from the reference pickleball grip 3MF.

The reference (PickleballGrip_1.3mf) is a closed-bottom sleeve.  Everything that
matters for fit is a function of height z:

  * the CAVITY   - a constant octagonal extrusion (floor at z=5, open at the top)
  * the ENVELOPE - outer offset E(z) measured *from the cavity wall*:
        z in [0, 20]      flared foot (measured table; ~2 mm bottom fillet, slope ~ -0.098)
        z in [20, ~110]   honeycomb zone, crest offset 3.5 (base wall 1.5)
        z in [~110, top]  smooth taper down to a 0.35 mm rim

Output: ../data/reference_profile.json
"""
import json
import re
import sys
import warnings
import zipfile
from pathlib import Path

import numpy as np
import trimesh
from shapely.geometry import Polygon

warnings.filterwarnings("ignore")
HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data"


def load_3mf_mesh(path):
    with zipfile.ZipFile(path) as z:
        xml = z.read("3D/3dmodel.model").decode()
    v = np.array(re.findall(r'<vertex x="([-\d.e]+)" y="([-\d.e]+)" z="([-\d.e]+)"', xml), float)
    t = np.array(re.findall(r'<triangle v1="(\d+)" v2="(\d+)" v3="(\d+)"', xml), int)
    m = trimesh.Trimesh(v, t, process=False)
    m.merge_vertices()
    return m


def section_polys(mesh, z):
    s = mesh.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
    if s is None:
        return []
    polys = [Polygon(np.asarray(d)[:, :2]).buffer(0) for d in s.discrete if len(d) > 3]
    return sorted(polys, key=lambda p: -p.area)


def max_offset(outer, cav_ring):
    b = outer.exterior
    d = [cav_ring.distance(b.interpolate(t)) for t in np.linspace(0, b.length, 1600, endpoint=False)]
    return float(np.max(d)), float(np.min(d))


def main(src):
    mesh = load_3mf_mesh(src)
    z_top = float(mesh.bounds[1][2])
    cav = section_polys(mesh, 60.0)[1]           # inner loop at mid-height
    ring = cav.exterior

    # floor height: first z where the section acquires an inner loop
    z_floor = next(round(z, 2) for z in np.arange(4.0, 6.0, 0.02) if len(section_polys(mesh, z)) > 1)

    # constancy check of the cavity
    dev = max(cav.symmetric_difference(section_polys(mesh, z)[1]).area for z in (6, 30, 90, 125, 132))

    # measured envelope offsets  (E = distance from the cavity wall to the outer skin)
    z_meas = [0.005, 0.02] + list(np.arange(0.05, 2.5, 0.05)) + list(np.arange(2.5, 20.01, 0.5)) + \
        list(np.arange(21, 109, 4.0)) + list(np.arange(108, z_top, 0.5)) + [z_top - 0.05]
    meas = []
    for z in z_meas:
        ps = section_polys(mesh, float(z))
        mx, mn = max_offset(ps[0], ring)
        meas.append((float(z), mx, mn))

    foot = [(0.0, 3.30)] + [(round(z, 3), round((mx + mn) / 2, 4)) for z, mx, mn in meas if z <= 19.5]
    foot.append((20.0, 3.54))                  # z=20 sample sits on the pattern edge -> extrapolate (slope ~ -0.098)
    err_mid = max(abs(3.5 - mx) for z, mx, mn in meas if 22 <= z <= 108)
    taper = [(round(z, 3), round(mx, 4)) for z, mx, mn in meas if z >= 108.0]

    out = dict(
        source=Path(src).name,
        units="mm",
        z_top=round(z_top, 3),
        z_floor=z_floor,
        z_foot_top=20.0,
        crest_offset=3.5, wall_offset=1.5,
        foot_table=foot,                            # [z, outer offset from cavity]
        taper_table=taper,                          # [z, outer offset from cavity]
        cavity_ring=[[round(x, 4), round(y, 4)] for x, y in ring.coords],
        cavity_bounds=[round(b, 3) for b in cav.bounds],
        cavity_area=round(cav.area, 3),
        checks=dict(cavity_constancy_area_err=dev, crest_fit_err_mm=round(err_mid, 3)),
    )
    DATA.mkdir(exist_ok=True)
    (DATA / "reference_profile.json").write_text(json.dumps(out, indent=1))
    print(json.dumps({k: v for k, v in out.items() if k not in ("cavity_ring", "taper_table", "foot_table")}, indent=1))
    print("taper:", taper[::4])


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else HERE.parent / "reference" / "PickleballGrip_1.3mf")
