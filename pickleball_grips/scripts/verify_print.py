#!/usr/bin/env python3
"""Print-readiness check for a solid part: 100 % infill, 0.20 mm layers, 0.4 mm nozzle.

For every STL:
  * MESH      closed, consistently wound, ONE body (no floating shells / enclosed voids), no degenerate
              triangles; genus reported (VORONOI-CORE's 54 windows are 54 handles by design)
  * WEIGHT    volume x density for PLA / PETG / TPU / ABS  (100 % infill => mass = volume x density)
  * LAYERS    the part is sliced at the mid-plane of every 0.20 mm layer (664 layers); each layer's
              cross-section is opened with a 0.4 mm and a 0.8 mm disc.  Material that vanishes under
              the opening is thinner than one nozzle line / two perimeters, i.e. the slicer would drop
              it or print it as a lone thin line
  * SUPPORT   layer-to-layer: material more than 0.35 mm (a 60 degree overhang at 0.2 mm layers) beyond
              the layer below is unsupported; the longest such run is the bridge span (must be <= 5 mm,
              the reliable bridging length for PLA/PETG).  Also reports the share of downward-facing
              surface steeper than 45 / 60 degrees from vertical (first mm, bed flare, excluded)

Writes ../print_report.json
"""
import json
import sys
import warnings
from pathlib import Path

import numpy as np
import trimesh
from shapely.geometry import MultiPolygon, Polygon
from shapely.ops import unary_union

sys.path.insert(0, str(Path(__file__).resolve().parent))
from designs import DESIGNS  # noqa: E402

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parent.parent
LAYER = 0.20
DENSITY = {"PLA": 1.24, "PETG": 1.27, "TPU": 1.21, "ABS": 1.04}      # g/cm3
LIMIT_G = 50.0


def layer_solids(mesh, heights):
    secs = mesh.section_multiplane(plane_origin=[0, 0, 0], plane_normal=[0, 0, 1], heights=heights)
    for s in secs:
        if s is None:
            yield Polygon()
            continue
        polys = s.polygons_full
        yield unary_union(polys) if len(polys) else Polygon()


def bridge_span(cur, below, tol=0.35):
    """Longest unsupported run in this layer: material farther than `tol` mm from the layer below."""
    if cur.is_empty:
        return 0.0
    uns = cur.difference(below.buffer(tol)) if not below.is_empty else cur
    if uns.is_empty:
        return 0.0
    best = 0.0
    for g in (uns.geoms if hasattr(uns, "geoms") else [uns]):
        if g.area < 0.3:
            continue
        r = g.minimum_rotated_rectangle
        xs, ys = r.exterior.coords.xy
        e = [np.hypot(xs[i + 1] - xs[i], ys[i + 1] - ys[i]) for i in range(2)]
        best = max(best, max(e))
    return best


def thin_stats(solid, r, min_piece=0.02):
    """Area of material narrower than 2r: what a morphological opening with a disc of radius r removes.
    Fragments under `min_piece` mm2 are the rounded tips of sharp convex corners, not thin walls."""
    if solid.is_empty:
        return 0.0
    opened = solid.buffer(-r, join_style=1).buffer(r, join_style=1)
    lost = solid.difference(opened)
    parts = lost.geoms if hasattr(lost, "geoms") else [lost]
    return float(sum(g.area for g in parts if g.area >= min_piece))


def main():
    rows = []
    heights = np.arange(LAYER / 2, 132.82, LAYER)
    for name, label, _ in DESIGNS:
        m = trimesh.load(ROOT / "stl" / f"{name}.stl", process=True)
        m.merge_vertices()
        r = dict(name=name, label=label)
        # ---- mesh
        bodies = m.split(only_watertight=False)
        r["bodies"] = len(bodies)
        r["watertight"] = bool(m.is_watertight)
        r["winding_ok"] = bool(m.is_winding_consistent)
        r["genus"] = int(round((2 - m.euler_number) / 2)) if len(bodies) == 1 else None
        r["degenerate_tris"] = int((m.area_faces < 1e-9).sum())
        r["volume_cm3"] = round(m.volume / 1000, 2)
        r["weight_g"] = {k: round(m.volume / 1000 * d, 1) for k, d in DENSITY.items()}
        # ---- overhang
        nz = m.face_normals[:, 2]
        zc = m.triangles_center[:, 2]
        for deg in (45, 60):
            bad = (nz < -np.sin(np.radians(deg))) & (zc > 1.0)
            r[f"downfacing_gt{deg}deg_pct_of_surface"] = round(float(m.area_faces[bad].sum() / m.area * 100), 2)
        # ---- layer analysis
        vol_total = vol_t04 = vol_t08 = 0.0
        worst04 = worst08 = 0.0
        layers04 = layers08 = 0
        z_thin08 = []
        span_max, span_z, prev = 0.0, 0.0, Polygon()
        for z, sol in zip(heights, layer_solids(m, heights)):
            if z > 1.0:
                sp = bridge_span(sol, prev)
                if sp > span_max:
                    span_max, span_z = sp, float(z)
            prev = sol
            a = sol.area
            t04 = thin_stats(sol, 0.20)                # < 0.4 mm : one nozzle line
            t08 = thin_stats(sol, 0.38)                # < 0.76 mm: cannot hold two perimeters
            vol_total += a * LAYER
            vol_t04 += t04 * LAYER
            vol_t08 += t08 * LAYER
            if t04 > 0.5:
                layers04 += 1
            if t08 > 2.0:
                layers08 += 1
                z_thin08.append(round(float(z), 1))
            worst04, worst08 = max(worst04, t04), max(worst08, t08)
        r["max_bridge_span_mm"] = round(span_max, 1)
        r["max_bridge_span_at_z"] = round(span_z, 1)
        r["layers"] = len(heights)
        r["sliced_volume_cm3"] = round(vol_total / 1000, 2)
        r["thin_lt_0.4mm_pct_of_volume"] = round(vol_t04 / vol_total * 100, 3)
        r["thin_lt_0.76mm_pct_of_volume"] = round(vol_t08 / vol_total * 100, 3)
        r["layers_with_thin_lt_0.4mm"] = layers04
        r["layers_with_thin_lt_0.76mm"] = layers08
        r["thin_lt_0.76mm_z_range"] = [min(z_thin08), max(z_thin08)] if z_thin08 else None
        r["under_50g_all_materials"] = bool(max(r["weight_g"].values()) <= LIMIT_G)
        r["pass"] = bool(r["bodies"] == 1 and r["watertight"] and r["winding_ok"] and r["under_50g_all_materials"] and
                         r["thin_lt_0.4mm_pct_of_volume"] < 0.05 and r["max_bridge_span_mm"] <= 5.0)
        rows.append(r)
        print(f"{name:18s} pass={r['pass']} bodies={r['bodies']} genus={r['genus']} vol={r['volume_cm3']:5.2f} "
              f"PLA={r['weight_g']['PLA']:5.1f}g PETG={r['weight_g']['PETG']:5.1f}g TPU={r['weight_g']['TPU']:5.1f}g "
              f"thin<0.4={r['thin_lt_0.4mm_pct_of_volume']:.3f}% thin<0.76={r['thin_lt_0.76mm_pct_of_volume']:.3f}% "
              f"bridge={r['max_bridge_span_mm']:.1f}mm@z{r['max_bridge_span_at_z']:.0f} down>45={r['downfacing_gt45deg_pct_of_surface']:.2f}%", flush=True)
    (ROOT / "print_report.json").write_text(json.dumps(rows, indent=1))


if __name__ == "__main__":
    main()
