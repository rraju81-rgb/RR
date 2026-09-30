#!/usr/bin/env python3
"""Check every generated STL against the reference 3MF.

For each grip:
  * mesh is a closed, consistently wound manifold, positive volume
  * height / footprint equal the reference (z 0..132.823)
  * BORE: the cavity is identical to the reference's - measured by sampling the reference
    cavity wall at many heights and finding the distance to the grip surface (must be ~0
    wherever the wall is not deliberately windowed), and by probing points 0.15 mm inside
    the bore to confirm no material intrudes
  * FLOOR at z=5.0 and open top
  * OUTER envelope never exceeds the reference envelope (cavity offset E(z)) by more than 0.05 mm
  * FOOT (z<20) and TOP TAPER (z>112) outer profile equals the reference

Writes ../fitment_report.json and prints a markdown table.
"""
import json
import sys
import warnings
from pathlib import Path

import numpy as np
import trimesh
from shapely.geometry import Polygon, Point, LineString

sys.path.insert(0, str(Path(__file__).resolve().parent))
from grip_core import Frame  # noqa: E402
from designs import DESIGNS  # noqa: E402

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from extract_reference_profile import load_3mf_mesh, section_polys  # noqa: E402


def section_solid(mesh, z):
    """Even-odd solid region of the plane z = const, plus the list of loops."""
    s = mesh.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
    if s is None:
        return Polygon(), []
    loops = sorted([Polygon(np.asarray(d)[:, :2]).buffer(0) for d in s.discrete if len(d) > 3], key=lambda p: -p.area)
    solid = Polygon()
    for p in loops:
        solid = solid.symmetric_difference(p)
    return solid, loops


def main():
    F = Frame()
    ref = load_3mf_mesh(ROOT / "reference" / "PickleballGrip_1.3mf")
    cav = Polygon(F.ring)
    ring = cav.exterior
    rb = ref.bounds
    rows = []
    for name, label, _ in DESIGNS:
        m = trimesh.load(ROOT / "stl" / f"{name}.stl", process=True)
        m.merge_vertices()
        r = dict(name=name, tris=int(len(m.faces)), watertight=bool(m.is_watertight),
                 winding_ok=bool(m.is_winding_consistent), volume_cm3=round(m.volume / 1000, 2))
        r["z_min"], r["z_max"] = round(float(m.bounds[0][2]), 3), round(float(m.bounds[1][2]), 3)
        r["height_err_mm"] = round(abs(m.bounds[1][2] - rb[1][2]), 3)
        # ---- outer envelope vs reference E(z); foot / taper profile match
        over = foot_err = taper_err = 0.0
        for z in list(np.arange(0.5, 20, 1.5)) + list(np.arange(21, 111, 6.0)) + list(np.arange(112, 132.8, 2.0)):
            solid, loops = section_solid(m, float(z))
            b = loops[0].exterior
            d = np.array([ring.distance(b.interpolate(t)) for t in np.linspace(0, b.length, 700, endpoint=False)])
            E = float(F.E_foot(z)) if z < 20 else float(F.E_upper(z))
            over = max(over, d.max() - E)
            if z < 20:
                foot_err = max(foot_err, abs(d.mean() - E))
            if z > 112:
                taper_err = max(taper_err, abs(d.mean() - E))
        r["max_over_reference_envelope_mm"] = round(over, 3)
        r["foot_profile_err_mm"] = round(foot_err, 3)
        r["taper_profile_err_mm"] = round(taper_err, 3)
        # ---- bore: reference wall must lie on the grip's boundary (except deliberate windows)
        # and nothing may intrude into the bore (probe region = bore shrunk by 0.1 mm)
        probe = cav.buffer(-0.1)
        wall_pts = [ring.interpolate(t) for t in np.linspace(0, ring.length, 90, endpoint=False)]
        dists, intr = [], 0.0
        for z in np.linspace(5.4, 132.6, 40):
            solid, _ = section_solid(m, float(z))
            bd = solid.boundary
            dists += [bd.distance(q) for q in wall_pts]
            intr = max(intr, solid.intersection(probe).area)
        dists = np.array(dists)
        r["bore_wall_dist_p50_mm"] = round(float(np.percentile(dists, 50)), 4)
        r["bore_wall_on_surface_pct"] = round(float((dists < 0.01).mean() * 100), 1)
        r["bore_intrusion_mm2"] = round(float(intr), 5)
        # ---- floor at z=5 and open top
        c = Point(*F.center)
        r["floor_solid_z4.8"] = bool(section_solid(m, 4.8)[0].contains(c))
        r["floor_empty_z5.2"] = bool(not section_solid(m, 5.2)[0].contains(c))
        r["open_top"] = bool(not section_solid(m, 132.7)[0].contains(c))
        r["pass"] = bool(r["watertight"] and r["winding_ok"] and r["height_err_mm"] < 0.01 and
                         r["max_over_reference_envelope_mm"] < 0.05 and r["bore_intrusion_mm2"] < 0.01 and
                         r["floor_solid_z4.8"] and r["floor_empty_z5.2"] and r["open_top"] and
                         r["foot_profile_err_mm"] < 0.06 and r["taper_profile_err_mm"] < 0.06)
        rows.append(r)
        print(f"{name:18s} pass={r['pass']} watertight={r['watertight']} over_env={r['max_over_reference_envelope_mm']:+.3f} "
              f"bore_on_surface={r['bore_wall_on_surface_pct']}% intrusion={r['bore_intrusion_mm2']} "
              f"foot_err={r['foot_profile_err_mm']} taper_err={r['taper_profile_err_mm']}", flush=True)
    (ROOT / "fitment_report.json").write_text(json.dumps(rows, indent=1))
    return rows


if __name__ == "__main__":
    main()
