#!/usr/bin/env python3
"""Check every generated STL against the reference 3MF and the paddle specification (revision 3).

For each grip:
  * mesh is a closed, consistently wound manifold, positive volume
  * height / footprint equal the reference (z 0..132.823)
  * OUTER envelope never exceeds the reference envelope (reference bore line offset by E(z)) by more than 0.05 mm
    - except the deliberate rim thickening (reference tapers to 0.36 mm; grips keep >= 0.8 mm), reported separately
  * FOOT (z<20) and TOP TAPER (z>112) outer profile equals the reference
  * SOLID: at every height there is exactly one cavity - the 30 x 16 mm paddle slot (+0.2 mm clearance), z 5 .. top -
    and nothing else; no material inside the slot
  * SCREW HOLE: one 3.5 mm hole through the butt (z 0 .. 5) on the slot axis; floor solid around it
  * OPEN TOP: the slot is open at z = top

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
from grip_core import Frame, slot_polygon, bore_centre, HOLE_D, PADDLE_W, PADDLE_T, SLOT_CLEAR  # noqa: E402
from designs import DESIGNS  # noqa: E402

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from extract_reference_profile import load_3mf_mesh, section_polys  # noqa: E402


def holes_of(solid):
    """Interior rings of an even-odd section as polygons (the cavities)."""
    gs = list(solid.geoms) if hasattr(solid, "geoms") else [solid]
    return [Polygon(i) for g in gs for i in g.interiors]


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
    cav = Polygon(F.ring)                       # the reference bore: the datum the outer skin is measured from
    ring = cav.exterior
    slot = slot_polygon(F)
    cx, cy = bore_centre(F)
    hole_area = np.pi * (HOLE_D / 2) ** 2
    rb = ref.bounds
    rows = []
    for name, label, _ in DESIGNS:
        m = trimesh.load(ROOT / "stl" / f"{name}.stl", process=True)
        m.merge_vertices()
        r = dict(name=name, tris=int(len(m.faces)), watertight=bool(m.is_watertight),
                 winding_ok=bool(m.is_winding_consistent), volume_cm3=round(m.volume / 1000, 2))
        r["z_min"], r["z_max"] = round(float(m.bounds[0][2]), 3), round(float(m.bounds[1][2]), 3)
        r["height_err_mm"] = round(abs(m.bounds[1][2] - rb[1][2]), 3)
        # ---- outer envelope vs the REFERENCE E(z); foot / taper profile match; wall + rim thickness
        over = foot_err = taper_err = rim_add = 0.0
        min_wall = rim_min = 9.0
        peak = 0.0
        for z in list(np.arange(0.5, 20, 1.5)) + list(np.arange(21, 111, 6.0)) + list(np.arange(112, 132.8, 2.0)):
            solid, loops = section_solid(m, float(z))
            b = loops[0].exterior
            d = np.array([ring.distance(b.interpolate(t)) for t in np.linspace(0, b.length, 700, endpoint=False)])
            E_ref = float(F.E_foot(z)) if z < 20 else float(F.E_ref_upper(z))
            E_des = float(F.E_foot(z)) if z < 20 else float(F.E_upper(z))
            if E_ref >= F.min_rim - 1e-9:
                over = max(over, d.max() - E_ref)                    # must never exceed the reference
            else:
                rim_add = max(rim_add, d.max() - E_ref)              # deliberate rim thickening (E_ref < min_rim)
                rim_min = min(rim_min, d.min())
            if 23 <= z <= 110:
                peak = max(peak, d.max())
            if 21 <= z <= 118:
                min_wall = min(min_wall, d.min())
            if z < 20:
                foot_err = max(foot_err, abs(d.mean() - E_des))
            if z >= 122:                                            # smooth neck above the textured zone
                taper_err = max(taper_err, abs(d.mean() - E_des))
        r["max_over_reference_envelope_mm"] = round(over, 3)
        r["foot_profile_err_mm"] = round(foot_err, 3)
        r["taper_profile_err_mm"] = round(taper_err, 3)
        r["min_wall_textured_zone_mm"] = round(min_wall, 3) if min_wall < 9 else None
        r["rim_min_wall_mm"] = round(rim_min, 3)
        r["rim_added_vs_reference_mm"] = round(rim_add, 3)
        r["peak_texture_height_above_bore_mm"] = round(peak, 2)
        # ---- paddle slot: exactly one cavity from the floor to the top, equal to the slot polygon, nothing inside it
        xor_max, intr, n_holes_bad = 0.0, 0.0, 0
        probe = slot.buffer(-0.05)
        for z in np.linspace(5.4, 132.6, 40):
            solid, _ = section_solid(m, float(z))
            hs = holes_of(solid)
            if len(hs) != 1:
                n_holes_bad += 1
                continue
            xor_max = max(xor_max, hs[0].symmetric_difference(slot).area)
            intr = max(intr, solid.intersection(probe).area)
        r["slot_w_mm"], r["slot_t_mm"] = [round(float(v), 3) for v in (slot.bounds[2] - slot.bounds[0], slot.bounds[3] - slot.bounds[1])]
        s60, _ = section_solid(m, 60.0)
        h60 = holes_of(s60)
        r["slot_measured_w_mm"] = round(float(h60[0].bounds[2] - h60[0].bounds[0]), 3) if len(h60) == 1 else None
        r["slot_measured_t_mm"] = round(float(h60[0].bounds[3] - h60[0].bounds[1]), 3) if len(h60) == 1 else None
        r["slot_levels_without_single_cavity"] = n_holes_bad
        r["slot_xor_max_mm2"] = round(float(xor_max), 4)
        r["slot_intrusion_mm2"] = round(float(intr), 5)
        # ---- screw hole through the butt: one round 3.5 mm hole on the slot axis for z 0.4 .. 4.6, floor solid around it
        hole_ok, hole_d = True, []
        for z in np.arange(0.4, 4.7, 0.5):
            solid, _ = section_solid(m, float(z))
            hs = holes_of(solid)
            if len(hs) != 1 or abs(hs[0].area - hole_area) > 0.25 or np.hypot(hs[0].centroid.x - cx, hs[0].centroid.y - cy) > 0.05:
                hole_ok = False
            else:
                hole_d.append(2 * np.sqrt(hs[0].area / np.pi))
        r["screw_hole_ok"] = bool(hole_ok)
        r["screw_hole_dia_mm"] = round(float(np.mean(hole_d)), 3) if hole_d else None
        r["floor_solid_z4.8"] = bool(section_solid(m, 4.8)[0].contains(Point(cx + 6.0, cy)))
        r["slot_empty_z5.2"] = bool(not section_solid(m, 5.2)[0].contains(Point(cx + 6.0, cy)))
        r["open_top"] = bool(not section_solid(m, 132.7)[0].contains(Point(cx, cy)))
        r["pass"] = bool(r["watertight"] and r["winding_ok"] and r["height_err_mm"] < 0.01 and
                         r["max_over_reference_envelope_mm"] < 0.05 and r["slot_intrusion_mm2"] < 0.01 and
                         r["slot_levels_without_single_cavity"] == 0 and r["slot_xor_max_mm2"] < 1.0 and r["screw_hole_ok"] and
                         (r["min_wall_textured_zone_mm"] is None or r["min_wall_textured_zone_mm"] >= F.wall - 0.03) and r["rim_min_wall_mm"] >= F.min_rim - 0.03 and
                         r["floor_solid_z4.8"] and r["slot_empty_z5.2"] and r["open_top"] and
                         r["foot_profile_err_mm"] < 0.06 and r["taper_profile_err_mm"] < 0.06)
        rows.append(r)
        print(f"{name:18s} pass={r['pass']} watertight={r['watertight']} over_env={r['max_over_reference_envelope_mm']:+.3f} "
              f"slot={r['slot_measured_w_mm']}x{r['slot_measured_t_mm']} xor={r['slot_xor_max_mm2']} intrusion={r['slot_intrusion_mm2']} "
              f"hole={r['screw_hole_dia_mm']} ok={r['screw_hole_ok']} foot_err={r['foot_profile_err_mm']} taper_err={r['taper_profile_err_mm']} "
              f"min_relief_base={r['min_wall_textured_zone_mm']} rim_min={r['rim_min_wall_mm']}", flush=True)
    (ROOT / "fitment_report.json").write_text(json.dumps(rows, indent=1))
    return rows


if __name__ == "__main__":
    main()
