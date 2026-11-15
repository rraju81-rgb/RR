#!/usr/bin/env python3
"""
3D-printable version of the cap: printed flat, with a V-groove on every bend line, folded after printing.

    out/print/cap_print_flat.stl     print this; it already lies outside face down
    out/print/cap_print_flat.step
    out/print/cap_print_folded.stl   what it becomes once folded (reference, not for printing)
    out/print/summary.json           grooves, checks, mesh checks
    docs/fig_groove.svg              how a groove folds

How the grooves work
--------------------
Each bend line gets a V cut almost through the plate, leaving a thin web on the far side. The web is the
hinge. The panels pivot on the groove's apex, so the groove's opening closes exactly when the fold
reaches the bend angle: the fold stops by itself at the right angle. The flat layout is computed so that
the inside of the folded part is the same as the press-brake version.

Usage:  python3 printed.py
"""
from __future__ import annotations

import json
import math
import struct
from pathlib import Path

import numpy as np
import cadquery as cq

from build import OUT, BEND_ORDER, run_checks
from model import CapGeometry, make_lamp
from params import printed_variant
from sheetmetal import rot90, unit

PRINT_OUT = OUT / "print"
DOCS = OUT.parent / "docs"
BED = 180.0     # mm, a small printer bed


def groove_solid(line, cap, ext=0.3, eps=0.05):
    """V-groove along one bend line of the flat part (part coordinates: z = 0 inside face, z = t outer face)."""
    a, b = np.asarray(line["a"], float), np.asarray(line["b"], float)
    e = unit(b - a)
    n = rot90(e)
    depth = cap.t - cap.web
    half = math.radians(line["angle"] + cap.groove_extra_deg) / 2
    h = (depth + eps) * math.tan(half)           # half width where the V leaves the face (just outside it)
    a0 = a - ext * e
    if line["direction"] == "up":                # bend closes towards the inside face: groove opens there
        z_open, z_apex = -eps, depth
    else:                                        # bend closes towards the outer face (the ear)
        z_open, z_apex = cap.t + eps, cap.t - depth
    pts = [(*(a0 + h * n), z_open), (*(a0 - h * n), z_open), (*a0, z_apex)]
    wire = cq.Wire.makePolygon([cq.Vector(*p) for p in pts], close=True)
    L = float(np.linalg.norm(b - a)) + 2 * ext
    return cq.Solid.extrudeLinear(cq.Face.makeFromWires(wire), cq.Vector(*(e * L), 0))


def print_flat(blank_solid, lines, cap):
    """Flat part with grooves, turned over so the outer face is on the bed and centred on the origin."""
    s = blank_solid
    for ln in lines:
        s = s.cut(groove_solid(ln, cap))
    s = s.clean()
    s = s.rotate((0, 0, 0), (1, 0, 0), 180).translate((0, 0, cap.t))   # turn over (a rotation, not a mirror)
    bb = s.BoundingBox()
    return s.translate((-(bb.xmin + bb.xmax) / 2, -(bb.ymin + bb.ymax) / 2, -bb.zmin))


def stl_check(path: Path):
    """Read a binary STL and check it is a closed, manifold, consistently wound mesh."""
    data = path.read_bytes()
    n = struct.unpack("<I", data[80:84])[0]
    assert len(data) == 84 + 50 * n, f"{path.name}: not a well-formed binary STL"
    rec = np.frombuffer(data[84:], dtype=np.dtype([("n", "<3f4"), ("v", "<9f4"), ("a", "<u2")]), count=n)
    V = rec["v"].reshape(-1, 3, 3).astype(np.float64)
    _, idx = np.unique(np.round(V.reshape(-1, 3) / 1e-4).astype(np.int64), axis=0, return_inverse=True)
    F = idx.reshape(-1, 3)
    directed = np.concatenate([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]])
    _, uc = np.unique(np.sort(directed, axis=1), axis=0, return_counts=True)
    _, dc = np.unique(directed, axis=0, return_counts=True)
    vol = float(np.einsum("ij,ij->i", V[:, 0], np.cross(V[:, 1], V[:, 2])).sum() / 6.0)
    lo, hi = V.reshape(-1, 3).min(0), V.reshape(-1, 3).max(0)
    return dict(triangles=int(n), closed_manifold=bool((uc == 2).all()), consistent_winding=bool((dc == 1).all()),
                volume_mm3=round(vol, 1), size=[round(float(x), 2) for x in hi - lo], kb=round(len(data) / 1024))


def build_print(out: Path = PRINT_OUT):
    out.mkdir(parents=True, exist_ok=True)
    d = printed_variant()
    cap = d.cap
    g = CapGeometry(d)
    folded, parts, frames = g.folded()
    assert folded.isValid() and len(folded.Solids()) == 1, "folded part did not fuse into one solid"
    _blank, blank_solid, _faces, lines, _placed = g.flat()
    lamp = make_lamp(d, g.ear_hole_centre(frames))
    rows, ok = run_checks(d, g, folded, parts, frames, lamp)

    flat = print_flat(blank_solid, lines, cap)
    assert flat.isValid() and len(flat.Solids()) == 1, "flat part is not one valid solid"
    bb = flat.BoundingBox()
    groove_vol = blank_solid.Volume() - flat.Volume()

    def add(name, value, req, passed):
        rows.append(dict(check=name, value=value, requirement=req, ok=bool(passed)))

    add("Flat part fits a small printer bed", f"{bb.xlen:.1f} x {bb.ylen:.1f} mm", f"<= {BED:.0f} x {BED:.0f}",
        bb.xlen <= BED and bb.ylen <= BED)
    add("Flat part lies flat on the bed", f"height {bb.zlen:.2f} mm", f"= {cap.t:.2f} (wall thickness)",
        abs(bb.zlen - cap.t) < 1e-6)
    ok = all(r["ok"] for r in rows)

    # exports
    cq.exporters.export(flat, str(out / "cap_print_flat.stl"), tolerance=0.01, angularTolerance=0.1)
    cq.exporters.export(flat, str(out / "cap_print_flat.step"))
    cq.exporters.export(folded, str(out / "cap_print_folded.stl"), tolerance=0.01, angularTolerance=0.1)
    mesh_flat = stl_check(out / "cap_print_flat.stl")
    mesh_folded = stl_check(out / "cap_print_folded.stl")

    idx = {lab: i + 1 for i, lab in enumerate(BEND_ORDER)}
    depth = cap.t - cap.web
    grooves = sorted(
        (dict(id=f"B{idx[ln['label']]}", feature=ln["label"].replace("bend_", "").replace("_", " ").title(),
              fold_angle=round(ln["angle"], 2),
              groove_angle=round(ln["angle"] + cap.groove_extra_deg, 2),
              opening=round(2 * depth * math.tan(math.radians(ln["angle"] + cap.groove_extra_deg) / 2), 2),
              depth=round(depth, 2), web=cap.web,
              face="top" if ln["direction"] == "up" else "underside",
              fold="up, towards you" if ln["direction"] == "up" else "down, away from you",
              length=round(float(np.linalg.norm(np.asarray(ln["b"]) - np.asarray(ln["a"]))), 1))
         for ln in lines),
        key=lambda x: int(x["id"][1:]),
    )
    fe = folded.BoundingBox()
    summary = dict(
        variant="Printed flat, folded on V-grooves",
        material=cap.material,
        wall=cap.t, web=cap.web, layer=cap.layer, groove_extra_deg=cap.groove_extra_deg,
        flat=dict(size=[round(bb.xlen, 1), round(bb.ylen, 1), round(bb.zlen, 2)],
                  volume_mm3=round(flat.Volume(), 1), grooves_removed_mm3=round(groove_vol, 1)),
        folded_size=[round(fe.xlen, 1), round(fe.ylen, 1), round(fe.zlen, 1)],
        mass_g=round(flat.Volume() * cap.density, 1),
        grooves=grooves,
        checks=rows,
        all_checks_pass=ok,
        mesh=dict(flat=mesh_flat, folded=mesh_folded),
    )
    (out / "summary.json").write_text(json.dumps(summary, indent=2))
    return dict(d=d, g=g, flat=flat, folded=folded, lines=lines, summary=summary)


# ----------------------------------------------------------------------------- figure: how a groove folds
def fig_groove(d, path: Path):
    from drawing import View
    from figures import Fig

    cap = d.cap
    t, w = cap.t, cap.web
    dep = t - w
    th = math.radians(90.0)
    h = dep * math.tan(th / 2)
    F = Fig(780, 372)
    k = 24.0

    def callout(view, u, v, X, Y, text):
        """Text starting at (X, Y); the leader leaves from under (or over) the middle of the text."""
        x0, y0 = view.xy(u, v)
        ex = X + 0.5 * 7.0 * len(text)
        ey = Y + 5 if y0 > Y else Y - 15
        F.line(x0, y0, ex, ey, "dim")
        F.arrow(x0, y0, math.atan2(y0 - ey, x0 - ex), 1.5)
        F.text(X, Y, text, "dimtxt")

    # left: flat, as printed (outside face on the bed, groove opening upwards)
    F.text(20, 26, "AS PRINTED", "label")
    v = View(F, 200, 236, k, 0.0, 0.0)
    L = 4.2
    left = [(-L, 0), (0, 0), (0, w), (-h, t), (-L, t)]
    right = [(0, 0), (L, 0), (L, t), (h, t), (0, w)]
    F.polyline([v.xy(*p) for p in left], "steel", close=True)
    F.polyline([v.xy(*p) for p in right], "steel", close=True)
    b0, b1 = v.xy(-L - 0.8, 0), v.xy(L + 0.8, 0)
    F.line(b0[0], b0[1] + 3, b1[0], b1[1] + 3, "ref")
    F.text(v.xy(0, 0)[0], v.xy(0, 0)[1] + 22, "printer bed (outside face)", "small", "middle")
    v.dim_v(0, t, -L, -6, f"{t:.1f} wall")
    v.dim_v(0, w, L, 7, f"{w:.1f} web")
    callout(v, -h * 0.45, t * 0.72, 20, 84, f"V-groove: opening angle = fold angle + {cap.groove_extra_deg:.0f}°")
    callout(v, 0.12, w * 0.45, 20, 322, "the web is the hinge")

    # right: folded 90 degrees about the apex; the groove has closed
    F.text(440, 26, "FOLDED", "label")
    v2 = View(F, 610, 252, k, 0.0, 0.0)
    horiz = [(-L, 0), (0, 0), (0, w), (-dep, t), (-L, t)]

    def rot(p):  # rotate +90 degrees about the apex (0, w)
        x, z = p[0], p[1] - w
        return (-z, x + w)

    vert = [rot(p) for p in right]
    F.polyline([v2.xy(*p) for p in horiz], "steel", close=True)
    F.polyline([v2.xy(*p) for p in vert], "steel", close=True)
    a, b = v2.xy(-dep, t), v2.xy(0, w)
    F.line(a[0], a[1], b[0], b[1], "dim")
    callout(v2, -dep - 0.05, t + 0.05, 440, 84, "fold stops here, at the bend angle")
    callout(v2, -dep * 0.5, (t + w) * 0.5, 440, 338, "closed groove: glue this seam")
    callout(v2, w * 0.75, w * 0.2, 560, 300, "web stretches round the corner")
    F.text(20, 362, "Fold every groove until it closes. Grooves on the top face fold up; the ear's groove is underneath and folds down.", "small")
    F.write(path, "How a V-groove folds")


if __name__ == "__main__":
    res = build_print()
    s = res["summary"]
    print(f"=== {s['variant']} ===")
    print(f"{s['material']}   wall {s['wall']} mm, web {s['web']} mm   flat {s['flat']['size']} mm   folded {s['folded_size']} mm   {s['mass_g']} g")
    for gr in s["grooves"]:
        print(f"  {gr['id']}  {gr['feature']:12s} fold {gr['fold_angle']:6.2f}  V {gr['groove_angle']:6.2f} deg  "
              f"opening {gr['opening']:.2f}  depth {gr['depth']:.2f}  on {gr['face']:9s} fold {gr['fold']}")
    for r in s["checks"]:
        print(f"  [{'ok' if r['ok'] else 'FAIL'}] {r['check']}: {r['value']}  (need {r['requirement']})")
    for name, m in s["mesh"].items():
        print(f"  mesh {name}: {m}")
    print("ALL CHECKS PASS" if s["all_checks_pass"] else "*** CHECK FAILURES ***")
    fig_groove(res["d"], DOCS / "fig_groove.svg")
