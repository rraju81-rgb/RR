#!/usr/bin/env python3
"""Measure everything the specification sheets quote - straight from the STL files.

per grip -> specs/assets/<id>/data.json  and  relief.png
    overall   bbox extents, volume, surface area, weights, filament length, layer count
    profile   per-z (0.5 mm): material area, outer width/depth, outer perimeter, min/max offset from the bore
    sections  simplified outlines (mm) at three heights for the dimensioned section drawings
    zones     landmark heights
    peaks     peak texture height above bore, max outer width/depth inside the textured band, min wall
and relief.png - the unrolled surface (S along the crest perimeter x z) coloured by height above the bore.

usage: python3 spec_data.py [--only 01 07 ...]
"""
import argparse
import json
import sys
import warnings
from pathlib import Path

import numpy as np
import trimesh
from PIL import Image
from shapely.geometry import Polygon

sys.path.insert(0, str(Path(__file__).resolve().parent))
from designs import DESIGNS, Ctx  # noqa: E402
from grip_core import Frame, ZONE_LO, ZONE_HI  # noqa: E402
from generate_grips import evaluate  # noqa: E402
from verify_fitment import section_solid  # noqa: E402

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "specs" / "assets"
DENSITY = {"PLA": 1.24, "PETG": 1.27, "TPU": 1.21, "ABS": 1.04}
SECTION_Z = (10.0, 60.0, 128.0)
FILAMENT_D = 1.75


def poly_coords(g, tol=0.02):
    g = g.simplify(tol)
    polys = g.geoms if hasattr(g, "geoms") else [g]
    out = []
    for p in polys:
        if p.is_empty or p.geom_type != "Polygon":
            continue
        out.append([np.round(np.asarray(p.exterior.coords), 3).tolist()] + [np.round(np.asarray(h.coords), 3).tolist() for h in p.interiors])
    return out


def viridis_like(v):
    """Compact perceptual ramp (dark blue -> teal -> yellow) for the relief map, v in [0,1]."""
    stops = np.array([[0.0, 30, 34, 90], [0.25, 44, 92, 150], [0.5, 32, 150, 140], [0.75, 130, 200, 90], [1.0, 250, 232, 60]])
    return np.stack([np.interp(v, stops[:, 0], stops[:, k]) for k in (1, 2, 3)], -1)


def relief_map(F, name, fn, out):
    ctx, d = evaluate(F, fn, 0.25)
    z, H, nfoot = F.skin(d["t"], 0.25)
    pat = z[nfoot:nfoot + len(ctx.Z)]
    Hp = H[nfoot:nfoot + len(ctx.Z)]
    v = np.clip((Hp - F.wall) / (F.crest - F.wall), 0, 1)
    img = viridis_like(v[::-1])                                   # z up
    im = Image.fromarray(img.astype(np.uint8)).resize((img.shape[1] * 2, img.shape[0] * 2), Image.LANCZOS)
    im.save(out)
    return dict(z0=float(pat[0]), z1=float(pat[-1]), L=float(F.L), hmin=float(Hp.min()), hmax=float(Hp.max()))


def main(only=None):
    F = Frame()
    ring = Polygon(F.ring).exterior
    cav = Polygon(F.ring)
    for name, label, fn in DESIGNS:
        if only and not any(name.startswith(o) for o in only):
            continue
        d = OUT / name
        d.mkdir(parents=True, exist_ok=True)
        m = trimesh.load(ROOT / "stl" / f"{name}.stl", process=True)
        m.merge_vertices()
        lo, hi = m.bounds
        vol = m.volume / 1000
        rec = dict(name=name, label=label)
        rec["overall"] = dict(x=float(hi[0] - lo[0]), y=float(hi[1] - lo[1]), z=float(hi[2] - lo[2]),
                              x_min=float(lo[0]), x_max=float(hi[0]), y_min=float(lo[1]), y_max=float(hi[1]),
                              volume_cm3=vol, surface_area_cm2=float(m.area / 100), triangles=int(len(m.faces)),
                              weight_g={k: vol * v for k, v in DENSITY.items()},
                              filament_1p75_m=float(m.volume / (np.pi * (FILAMENT_D / 2) ** 2) / 1000),
                              layers_0p2=int(np.ceil((hi[2] - lo[2]) / 0.2)))
        rec["bore"] = dict(x=float(F.ring[:, 0].max() - F.ring[:, 0].min()), y=float(F.ring[:, 1].max() - F.ring[:, 1].min()),
                           area=float(cav.area), perimeter=float(ring.length), floor_z=float(F.z_floor),
                           depth=float(F.z_top - F.z_floor), x_min=float(F.ring[:, 0].min()), x_max=float(F.ring[:, 0].max()),
                           y_min=float(F.ring[:, 1].min()), y_max=float(F.ring[:, 1].max()))
        # ---- per-z profile
        zs = np.round(np.arange(0.25, hi[2], 0.5), 3)
        prof = []
        for z in zs:
            solid, loops = section_solid(m, float(z))
            if solid.is_empty or not loops:
                prof.append(None)
                continue
            polys = list(solid.geoms) if hasattr(solid, "geoms") else [solid]
            npts = 600 if len(polys) == 1 else 90              # fragmented section (through-windows): fewer samples each
            dd = []
            for pl in polys:
                bd = pl.exterior
                dd += [ring.distance(bd.interpolate(t)) for t in np.linspace(0, bd.length, npts, endpoint=False)]
            dd = np.array(dd)
            xmin, ymin, xmax, ymax = solid.bounds
            hull = solid.convex_hull
            is_open = len(polys) > 1 or dd.min() < 0.05      # ring broken by windows -> wall thickness undefined
            prof.append(dict(z=float(z), area=float(solid.area), w=float(xmax - xmin), d=float(ymax - ymin),
                             perim=float(hull.exterior.length), off_max=float(dd.max()),
                             off_min=(None if is_open else float(dd.min())), open=bool(is_open)))
        rec["profile"] = [p for p in prof if p]
        # ---- section outlines
        secs = {}
        for z in SECTION_Z:
            solid, loops = section_solid(m, z)
            xmin, ymin, xmax, ymax = solid.bounds
            secs[str(z)] = dict(z=z, poly=poly_coords(solid), w=float(xmax - xmin), d=float(ymax - ymin), xmin=float(xmin),
                                xmax=float(xmax), ymin=float(ymin), ymax=float(ymax), area=float(solid.area),
                                perim=float(solid.convex_hull.exterior.length))
        rec["sections"] = secs
        # ---- landmarks / peaks
        zone = [p for p in rec["profile"] if 23 <= p["z"] <= 110]
        rec["zones"] = dict(floor_top=float(F.z_floor), foot_top=20.0, tex_lo=ZONE_LO, tex_hi=ZONE_HI, top=float(hi[2]),
                            rim_wall=float(F.min_rim), base_wall=float(F.wall))
        rec["peaks"] = dict(peak_offset=max(p["off_max"] for p in zone), max_w=max(p["w"] for p in zone),
                            max_d=max(p["d"] for p in zone), perim_min=min(p["perim"] for p in zone),
                            perim_max=max(p["perim"] for p in zone), perim_mean=float(np.mean([p["perim"] for p in zone])),
                            min_wall=(None if any(p["off_min"] is None for p in zone) else min(p["off_min"] for p in zone)),
                            foot_w=max(p["w"] for p in rec["profile"] if p["z"] < 20),
                            foot_d=max(p["d"] for p in rec["profile"] if p["z"] < 20),
                            butt_w=rec["profile"][0]["w"], butt_d=rec["profile"][0]["d"])
        rec["relief"] = relief_map(F, name, fn, d / "relief.png")
        (d / "data.json").write_text(json.dumps(rec))
        print("data", name, "peak %.2f  maxW %.2f maxD %.2f  perim %.1f..%.1f" % (rec["peaks"]["peak_offset"], rec["peaks"]["max_w"],
              rec["peaks"]["max_d"], rec["peaks"]["perim_min"], rec["peaks"]["perim_max"]), flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*")
    main(ap.parse_args().only)
