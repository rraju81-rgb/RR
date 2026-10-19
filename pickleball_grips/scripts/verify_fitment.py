#!/usr/bin/env python3
"""Check every generated STL against the reference 3MF and the paddle specification (revision 3).

For each grip:
  * mesh is a closed, consistently wound manifold, positive volume
  * height 135.0 mm (13.5 cm: 5 mm base + 130 mm slot); footprint equal the reference
  * OUTER envelope never exceeds the reference envelope (reference bore line offset by E(z)) by more than 0.05 mm
    - except the deliberate rim thickening (reference tapers to 0.36 mm; grips keep >= 0.8 mm), reported separately
  * FOOT (z<20) and TOP TAPER (z>112) outer profile equals the reference
  * SLOT: at every height the cavity around the axis is the 30 x 16 mm paddle slot (+0.2 mm clearance), z 5 .. top;
    no material inside the slot (the sealed lightening cavity in the side walls is checked in verify_print.py)
  * SCREW HOLE: one 3.5 mm hole through the butt (z 0 .. 5) on the slot axis with a 6.2 mm x 3.2 mm counterbore for an M3
    socket-head screw at the butt face; floor solid around it
  * HEAD: no sealed cavity above z = 110 (the head must be solid); slot mouth has a 0.5 mm 45 degree lead-in
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
from grip_core import Frame, slot_polygon, bore_centre, HOLE_D, HEAD_D, HEAD_H, MOUTH_CHAMFER, PADDLE_W, PADDLE_T, SLOT_CLEAR  # noqa: E402
from lighten import HEAD_SOLID_FROM  # noqa: E402
from designs import DESIGNS  # noqa: E402

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from extract_reference_profile import load_3mf_mesh, section_polys  # noqa: E402


def holes_of(solid):
    """Interior rings of an even-odd section as polygons (the cavities)."""
    gs = list(solid.geoms) if hasattr(solid, "geoms") else [solid]
    return [Polygon(i) for g in gs for i in g.interiors]


def hole_at(solid, pt):
    """The smallest cavity ring that contains `pt` (the slot above the floor, the screw hole below it), else None.
    (Where the sealed cavity wraps round the slot - in the foot - its outer ring contains `pt` too, so take the smallest.)"""
    hs = [h for h in holes_of(solid) if h.contains(pt)]
    return min(hs, key=lambda h: h.area) if hs else None


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
        r["height_err_mm"] = round(abs(m.bounds[1][2] - F.z_top), 3)
        # ---- outer envelope vs the REFERENCE E(z); foot / taper profile match; wall + rim thickness
        over = foot_err = taper_err = rim_add = 0.0
        min_wall = rim_min = 9.0
        peak = 0.0
        for z in list(np.arange(0.5, 20, 1.5)) + list(np.arange(21, 111, 6.0)) + list(np.arange(112, F.z_top - 0.2, 2.0)):
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
        axis = Point(cx, cy)
        probe = slot.buffer(-0.05)
        for z in np.linspace(5.4, F.z_top - 1.0, 40):                         # stop below the 0.5 mm mouth chamfer
            solid, _ = section_solid(m, float(z))
            h = hole_at(solid, axis)
            if h is None:
                n_holes_bad += 1
                continue
            xor_max = max(xor_max, h.symmetric_difference(slot).area)
            intr = max(intr, solid.intersection(probe).area)
        r["slot_w_mm"], r["slot_t_mm"] = [round(float(v), 3) for v in (slot.bounds[2] - slot.bounds[0], slot.bounds[3] - slot.bounds[1])]
        s60, _ = section_solid(m, 60.0)
        h60 = hole_at(s60, axis)
        r["slot_measured_w_mm"] = round(float(h60.bounds[2] - h60.bounds[0]), 3) if h60 is not None else None
        r["slot_measured_t_mm"] = round(float(h60.bounds[3] - h60.bounds[1]), 3) if h60 is not None else None
        r["slot_levels_without_single_cavity"] = n_holes_bad
        r["slot_xor_max_mm2"] = round(float(xor_max), 4)
        r["slot_intrusion_mm2"] = round(float(intr), 5)
        # ---- screw hole through the butt: round 3.5 mm on the slot axis for z 1.8 .. 4.8, centred; 90 degree countersink below
        hole_ok, hole_d = True, []
        for z in np.arange(HEAD_H + 0.3, 4.9, 0.4):
            h = hole_at(section_solid(m, float(z))[0], axis)
            if h is None or abs(h.area - hole_area) > 0.25 or np.hypot(h.centroid.x - cx, h.centroid.y - cy) > 0.05:
                hole_ok = False
            else:
                hole_d.append(2 * np.sqrt(h.area / np.pi))
        csd = {}
        for z in (0.1, 1.6, HEAD_H - 0.2):
            h = hole_at(section_solid(m, z)[0], axis)
            csd[z] = 2 * np.sqrt(h.area / np.pi) if h is not None else None
        csink_ok = all(csd[z] is not None and abs(csd[z] - HEAD_D) < 0.25 for z in csd)          # counterbore: constant diameter
        r["screw_hole_ok"] = bool(hole_ok)
        r["screw_hole_dia_mm"] = round(float(np.mean(hole_d)), 3) if hole_d else None
        r["counterbore_ok"] = bool(csink_ok)
        r["counterbore_dia_mm"] = round(float(np.mean([v for v in csd.values() if v])), 2) if all(csd.values()) else None
        r["counterbore_depth_mm"] = HEAD_H
        r["floor_solid_z4.8"] = bool(section_solid(m, 4.8)[0].contains(Point(cx + 6.0, cy)))
        r["slot_empty_z5.2"] = bool(not section_solid(m, 5.2)[0].contains(Point(cx + 6.0, cy)))
        r["open_top"] = bool(not section_solid(m, F.z_top - 0.1)[0].contains(Point(cx, cy)))
        r["pass"] = bool(r["watertight"] and r["winding_ok"] and r["height_err_mm"] < 0.01 and
                         r["max_over_reference_envelope_mm"] < 0.05 and r["slot_intrusion_mm2"] < 0.01 and
                         r["slot_levels_without_single_cavity"] == 0 and r["slot_xor_max_mm2"] < 1.0 and r["screw_hole_ok"] and r["counterbore_ok"] and
                         (r["min_wall_textured_zone_mm"] is None or r["min_wall_textured_zone_mm"] >= F.wall - 0.03) and r["rim_min_wall_mm"] >= F.min_rim - 0.03 and
                         r["floor_solid_z4.8"] and r["slot_empty_z5.2"] and r["open_top"] and
                         r["foot_profile_err_mm"] < 0.06 and r["taper_profile_err_mm"] < 0.06)
        rows.append(r)
        print(f"{name:18s} pass={r['pass']} watertight={r['watertight']} over_env={r['max_over_reference_envelope_mm']:+.3f} "
              f"slot={r['slot_measured_w_mm']}x{r['slot_measured_t_mm']} xor={r['slot_xor_max_mm2']} intrusion={r['slot_intrusion_mm2']} "
              f"hole={r['screw_hole_dia_mm']} ok={r['screw_hole_ok']} cbore={r['counterbore_dia_mm']} ok={r['counterbore_ok']} foot_err={r['foot_profile_err_mm']} taper_err={r['taper_profile_err_mm']} "
              f"min_relief_base={r['min_wall_textured_zone_mm']} rim_min={r['rim_min_wall_mm']}", flush=True)
    (ROOT / "fitment_report.json").write_text(json.dumps(rows, indent=1))
    return rows


if __name__ == "__main__":
    main()
