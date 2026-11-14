#!/usr/bin/env python3
"""
Build everything for the KTM indicator cap from params.py:

    out/cap_formed.step / .stl     formed part (STEP for the bend shop, STL to 3D-print a fit gauge)
    out/cap_blank.dxf / .step      flat laser blank: cut contours + bend lines
    out/assembly_reference.step    cap on the schematic lamp, for context
    out/summary.json               every derived number and every check result
    out/viewer_data.json           meshes for the 3D design-review page

Usage:  python3 build.py            (stainless 1.5 mm, default)
        python3 build.py --alu      (aluminium 2.0 mm variant -> out/alu/)
"""
from __future__ import annotations

import base64
import json
import math
import sys
from pathlib import Path

import numpy as np
import cadquery as cq
import ezdxf
from OCP.BRepAdaptor import BRepAdaptor_Curve
from OCP.BRepTools import BRepTools_WireExplorer
from OCP.GCPnts import GCPnts_QuasiUniformDeflection

from params import Design, aluminium_variant
from model import CapGeometry, make_lamp, make_hardware, make_liners

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "out"

# In the blank drawing the OUTSIDE (cosmetic) face is up, so the kernel's "up" (towards the inside
# of the cap) is a bend AWAY from the viewer.
SHOP_DIR = {"up": "DOWN", "down": "UP"}
BEND_ORDER = ["bend_TOP_TAB1", "bend_TOP_TAB2", "bend_BOTTOM_TAB1", "bend_BOTTOM_TAB2",
              "bend_TIP", "bend_EAR", "bend_TOP", "bend_BOTTOM"]


# ----------------------------------------------------------------------------- checks
def run_checks(d: Design, g: CapGeometry, cap, parts, frames, lamp):
    """Geometric self-checks. Returns (rows, ok) where rows = [(name, value, requirement, passed)]."""
    lampd, capd = d.lamp, d.cap
    rows = []

    def add(name, value, req, passed):
        rows.append(dict(check=name, value=value, requirement=req, ok=bool(passed)))

    body = lamp["HOUSING"].fuse(lamp["LENS"])
    named = dict(parts)

    inter = cap.intersect(body)
    vol = sum(s.Volume() for s in inter.Solids()) if inter.Solids() else 0.0
    add("Cap vs lamp head, overlap volume", f"{vol:.3f} mm3", "0", vol < 1e-6)

    def dist(a, b):
        return float(a.distance(b))

    dz_top = dist(named["TOP"], lamp["HOUSING"])
    dz_bot = dist(named["BOTTOM"], lamp["HOUSING"])
    add("Liner gap, top / bottom plate", f"{dz_top:.2f} / {dz_bot:.2f} mm", f"{capd.gap_z:.2f}",
        abs(dz_top - capd.gap_z) < 0.02 and abs(dz_bot - capd.gap_z) < 0.02)
    db = dist(named["BACK"], lamp["HOUSING"])
    add("Liner gap, back wall", f"{db:.2f} mm", f"{capd.gap_back:.2f}", abs(db - capd.gap_back) < 0.02)
    dt = dist(named["TIP"], lamp["HOUSING"])
    add("Liner gap, tip wall", f"{dt:.2f} mm", f"{capd.gap_tip:.2f}", abs(dt - capd.gap_tip) < 0.02)
    tabs = [min(dist(named[n], body), dist(named["bend_" + n], body))          # flat part and its bend arc
            for n, _ in parts if n.endswith(("TAB1", "TAB2")) and not n.startswith("bend")]
    add("Keeper tabs to lens chamfer (closest point)", " / ".join(f"{x:.2f}" for x in tabs) + " mm", f"{capd.gap_tab:.2f}",
        all(abs(x - capd.gap_tab) < 0.03 for x in tabs))

    # how far the tabs hook below the top face of the head (this is what keeps a loose head in)
    th = math.radians(capd.tab_angle)
    hook = capd.r * (1 - math.cos(th)) + capd.tab_flat * math.sin(th) - capd.gap_z
    add("Tab hook depth past the head's top edge", f"{hook:.2f} mm", ">= 1.5", hook >= 1.5)

    # slide-on: pull the cap outboard in steps, it must never touch the head
    worst = 1e9
    clash = 0.0
    for dx in (1, 2, 4, 8, 16, 32, 64, 90):
        moved = cap.moved(cq.Location(cq.Vector(dx, 0, 0)))
        it = moved.intersect(body)
        clash += sum(s.Volume() for s in it.Solids()) if it.Solids() else 0.0
        worst = min(worst, float(moved.distance(body)))
    add("Slides on from the tip without touching (8 stations)", f"min gap {worst:.2f} mm", "> 0", clash < 1e-6 and worst > 0)

    # symmetric top to bottom -> one part fits left and right
    mirrored = cap.mirror("XY", (0, 0, lampd.H / 2))
    diff = cap.cut(mirrored)
    dvol = sum(s.Volume() for s in diff.Solids()) if diff.Solids() else 0.0
    if abs(d.mount.screw_dz) < 1e-9:
        add("Top/bottom symmetric (same part for left and right)", f"{dvol:.3f} mm3 difference", "0", dvol < 1e-3)
    else:
        add("Screw is off mid-height: left and right are mirror-image parts", f"{dvol:.1f} mm3 difference",
            "make a handed pair (same blank, ear and all bends mirrored)", True)

    # nothing in front of the lens
    bb = cap.BoundingBox()
    lens_front = -(lampd.lens_run + lampd.lens_nose)
    add("Cap stays behind the lens front face", f"{bb.ymin - lens_front:.2f} mm behind", "> 0", bb.ymin > lens_front)
    window = cq.Workplane("XY").box(lampd.L, 200, lampd.H - 2 * (lampd.lens_drop + 1.0), centered=False).translate(
        (0, lens_front - 200, lampd.lens_drop + 1.0)).val()
    it = cap.intersect(window)
    wv = sum(s.Volume() for s in it.Solids()) if it.Solids() else 0.0
    add("Lens light window obstructed", f"{wv:.3f} mm3", "0", wv < 1e-6)

    # sheet-metal rules of thumb
    t = capd.t
    tab_flange = capd.ba(capd.tab_angle) + capd.tab_flat
    add("Shortest flange (keeper tab, from tangent)", f"{tab_flange:.2f} mm", f">= {3 * t:.2f} (3 t)", tab_flange >= 3 * t)
    add("Slot width vs thickness", f"{capd.slot_w:.2f} mm", f">= {t:.2f} (1 t)", capd.slot_w >= t)
    add("Slot keep-out from bend / edge", f"{capd.slot_margin:.2f} mm", f">= {2 * t + capd.r:.2f} (2 t + r)",
        capd.slot_margin >= 2 * t + capd.r)
    ear_edge = g.q_hole - capd.ear_slot_len / 2
    add("Ear slot to bend tangent", f"{ear_edge:.2f} mm", f">= {2 * t:.2f} (2 t)", ear_edge >= 2 * t)
    add("Exposed corner radius", f"{capd.r_corner:.1f} mm", ">= 2.5", capd.r_corner >= 2.5)
    return rows, all(r["ok"] for r in rows)


# ----------------------------------------------------------------------------- DXF
def _ordered(wire):
    exp = BRepTools_WireExplorer(wire.wrapped)
    edges = []
    while exp.More():
        edges.append(cq.Edge(exp.Current()))
        exp.Next()
    return edges


def wire_to_bulge_points(wire):
    """Closed wire -> [(x, y, bulge)] for an LWPOLYLINE (true arcs, no faceting)."""
    edges = _ordered(wire)
    segs = []
    for e in edges:
        a, b, m = e.startPoint(), e.endPoint(), e.positionAt(0.5)
        segs.append([np.array([a.x, a.y]), np.array([b.x, b.y]), np.array([m.x, m.y]), e.geomType()])
    # orient each edge so that it chains with its neighbours
    n = len(segs)
    if n > 1:
        s0, s1 = segs[0], segs[1]
        if min(np.linalg.norm(s0[1] - s1[0]), np.linalg.norm(s0[1] - s1[1])) > 1e-6:
            s0[0], s0[1] = s0[1], s0[0]
        for i in range(1, n):
            prev_end = segs[i - 1][1]
            if np.linalg.norm(segs[i][0] - prev_end) > 1e-6:
                segs[i][0], segs[i][1] = segs[i][1], segs[i][0]
            assert np.linalg.norm(segs[i][0] - prev_end) < 1e-5, "wire does not chain"
    pts = []
    for a, b, m, kind in segs:
        bulge = 0.0
        if kind != "LINE":
            chord = b - a
            c = np.linalg.norm(chord)
            right = np.array([chord[1], -chord[0]]) / c
            sag = float((m - (a + b) / 2) @ right)
            bulge = 2 * sag / c
        pts.append((float(a[0]), float(a[1]), float(bulge)))
    return pts


def export_dxf(g: CapGeometry, blank, lines, path: Path, title: str):
    doc = ezdxf.new("R2010", setup=True)
    doc.units = ezdxf.units.MM
    doc.header["$MEASUREMENT"] = 1
    for name, color, ltype in (("CUT", 7, "CONTINUOUS"), ("BEND_DOWN", 3, "CENTER"), ("BEND_UP", 1, "CENTER"),
                               ("ANNOTATION", 4, "CONTINUOUS")):
        doc.layers.add(name, color=color, linetype=ltype)
    msp = doc.modelspace()
    for wire in [blank.outerWire()] + list(blank.innerWires()):
        pts = wire_to_bulge_points(wire)
        msp.add_lwpolyline(pts, format="xyb", close=True, dxfattribs={"layer": "CUT"})
    idx = {lab: i + 1 for i, lab in enumerate(BEND_ORDER)}
    for ln in lines:
        shop = SHOP_DIR[ln["direction"]]
        msp.add_line(tuple(ln["a"]), tuple(ln["b"]), dxfattribs={"layer": f"BEND_{shop}"})
        mid = (ln["a"] + ln["b"]) / 2
        msp.add_text(f"B{idx[ln['label']]} {shop} {ln['angle']:.1f}", height=1.6,
                     dxfattribs={"layer": "ANNOTATION"}).set_placement((mid[0] + 1.0, mid[1] + 1.0))
    bb = blank.BoundingBox()
    cap = g.d.cap
    notes = [
        title,
        f"MATERIAL: {cap.material}",
        f"INSIDE BEND RADIUS {cap.r:.1f}   K-FACTOR {cap.k:.2f}   ALL DIMENSIONS mm",
        "VIEW: OUTSIDE (COSMETIC) FACE UP.  BEND_DOWN = away from viewer, BEND_UP = towards viewer.",
        "Bend lines are bend centre lines. Do not cut layers BEND_* or ANNOTATION.",
        "UNVERIFIED LAMP DIMENSIONS - make a card / printed fit check before cutting metal.",
    ]
    for i, s in enumerate(notes):
        msp.add_text(s, height=2.2, dxfattribs={"layer": "ANNOTATION"}).set_placement((bb.xmin, bb.ymin - 6 - 3.6 * i))
    doc.saveas(path)


# ----------------------------------------------------------------------------- meshes for the viewer
def _b64(arr, dtype):
    return base64.b64encode(np.ascontiguousarray(arr, dtype=dtype).tobytes()).decode()


def mesh_payload(shape, tol=0.03, ang=0.25, edge_defl=0.05):
    """Triangles with per-face smooth normals + feature edges, base64 packed."""
    verts, tris = shape.tessellate(tol, ang)
    V = np.array([[v.x, v.y, v.z] for v in verts], float)
    T = np.array(tris, np.int64)
    N = np.zeros_like(V)
    fn = np.cross(V[T[:, 1]] - V[T[:, 0]], V[T[:, 2]] - V[T[:, 0]])   # area-weighted face normals
    for k in range(3):
        np.add.at(N, T[:, k], fn)
    ln = np.linalg.norm(N, axis=1)
    N[ln > 0] /= ln[ln > 0][:, None]
    segs = []
    for e in shape.Edges():
        curve = BRepAdaptor_Curve(e.wrapped)
        disc = GCPnts_QuasiUniformDeflection(curve, edge_defl)
        if not disc.IsDone() or disc.NbPoints() < 2:
            continue
        p = [(disc.Value(i).X(), disc.Value(i).Y(), disc.Value(i).Z()) for i in range(1, disc.NbPoints() + 1)]
        for a, b in zip(p[:-1], p[1:]):
            segs.append(a + b)
    return dict(
        pos=_b64(V, np.float32), nrm=_b64(N, np.float32), idx=_b64(T, np.uint32),
        edges=_b64(np.array(segs, float).reshape(-1), np.float32),
        nv=int(len(V)), nt=int(len(T)),
    )


# ----------------------------------------------------------------------------- main
def build(d: Design, out: Path, tag: str):
    out.mkdir(parents=True, exist_ok=True)
    g = CapGeometry(d)
    lampd, capd, mount = d.lamp, d.cap, d.mount

    cap, parts, frames = g.folded()
    assert cap.isValid() and len(cap.Solids()) == 1
    blank, blank_solid, flat_faces, lines, placed = g.flat()
    hole = g.ear_hole_centre(frames)
    lamp = make_lamp(d, hole)
    hw = make_hardware(d, hole)
    liners = make_liners(g, frames)

    rows, ok = run_checks(d, g, cap, parts, frames, lamp)

    # ---- numbers
    vol = cap.Volume()
    bbf = blank.BoundingBox()
    bb = cap.BoundingBox()
    panel_area = sum(p.area() for p in g.root.walk())
    strip_area = sum(b.length * capd.ba(b.angle) for b in g.root.bends())
    idx = {lab: i + 1 for i, lab in enumerate(BEND_ORDER)}
    bends = sorted(
        (dict(id=f"B{idx[ln['label']]}", feature=ln["label"].replace("bend_", ""), direction=SHOP_DIR[ln["direction"]],
              angle=round(ln["angle"], 2), length=round(float(np.linalg.norm(ln["b"] - ln["a"])), 2),
              allowance=round(ln["allowance"], 3)) for ln in lines),
        key=lambda b: int(b["id"][1:]),
    )
    summary = dict(
        variant=tag,
        material=capd.material,
        thickness=capd.t, inside_radius=capd.r, k_factor=capd.k,
        mass_g=round(vol * capd.density, 1),
        volume_mm3=round(vol, 1),
        formed_envelope=dict(x=[round(bb.xmin, 2), round(bb.xmax, 2)], y=[round(bb.ymin, 2), round(bb.ymax, 2)],
                             z=[round(bb.zmin, 2), round(bb.zmax, 2)],
                             size=[round(bb.xlen, 2), round(bb.ylen, 2), round(bb.zlen, 2)]),
        blank=dict(width=round(bbf.xlen, 2), height=round(bbf.ylen, 2), area=round(blank.Area(), 1),
                   area_check=round(panel_area + strip_area, 1),
                   cut_length=round(sum(w.Length() for w in [blank.outerWire()] + list(blank.innerWires())), 1),
                   pierces=1 + len(blank.innerWires())),
        derived=dict(
            taper_deg=round(math.degrees(g.al), 2), cavity_height=round(g.Hc, 2), outer_height=round(g.Hc + 2 * capd.t, 2),
            back_wall_flat_height=round(g.hb, 2), back_wall_length=round(g.Lbw, 2), plate_bend_length=round(g.W, 2),
            tip_wall=[round(g.ht, 2), round(g.tip_len, 2)], ear_height=round(g.he, 2),
            ear_angle=round(g.ear_angle, 2), tip_angle=round(g.tip_angle, 2),
            tab_bend_line_y=round(g.y_tab, 3), plate_edge_y=round(g.y_edge, 3),
            screw_axis=[round(float(v), 2) for v in hole],
            ear_slot_centre_from_bend_tangent=round(g.q_hole, 2),
        ),
        bends=bends,
        checks=rows,
        all_checks_pass=ok,
        params=d.as_dict(),
    )
    (out / "summary.json").write_text(json.dumps(summary, indent=2))

    # ---- CAD exports
    cq.exporters.export(cap, str(out / "cap_formed.step"))
    cq.exporters.export(cap, str(out / "cap_formed.stl"), tolerance=0.02, angularTolerance=0.2)
    cq.exporters.export(blank_solid, str(out / "cap_blank.step"))
    export_dxf(g, blank, lines, out / "cap_blank.dxf", f"KTM INDICATOR CAP  -  FLAT BLANK  -  {tag}")

    asm = cq.Assembly(name="indicator_cap_on_lamp")
    asm.add(cap, name="cap", color=cq.Color(0.72, 0.74, 0.76))
    colors = {"HOUSING": (0.08, 0.08, 0.09), "LENS": (1.0, 0.62, 0.1), "NECK": (0.15, 0.15, 0.16),
              "SOCKET": (0.2, 0.2, 0.22), "BOSS": (0.2, 0.2, 0.22), "BODY": (0.2, 0.2, 0.22)}
    for k, s in lamp.items():
        asm.add(s, name=f"ref_{k.lower()}", color=cq.Color(*colors.get(k, (0.5, 0.5, 0.5))))
    for k, s in hw.items():
        asm.add(s, name=k.lower(), color=cq.Color(0.8, 0.8, 0.82))
    asm.save(str(out / "assembly_reference.step"))

    # ---- viewer payload
    payload = dict(
        meta=dict(L=lampd.L, H=lampd.H, D_root=lampd.D_root, D_tip=lampd.D_tip, t=capd.t,
                  hole=[float(v) for v in hole], G_ear=mount.G_ear),
        parts={"CAP": mesh_payload(cap)},
    )
    for k, s in lamp.items():
        payload["parts"][k] = mesh_payload(s, tol=0.05)
    for k, s in hw.items():
        payload["parts"][k] = mesh_payload(s, tol=0.03)
    for k, (s, _free) in liners.items():
        payload["parts"][k] = mesh_payload(s, tol=0.05)
    (out / "viewer_data.json").write_text(json.dumps(payload))

    return dict(d=d, g=g, cap=cap, parts=parts, frames=frames, blank=blank, blank_solid=blank_solid, lines=lines,
                placed=placed, lamp=lamp, hw=hw, liners=liners, summary=summary, hole=hole)


def report(summary):
    s = summary
    print(f"\n=== {s['variant']} ===")
    print(f"{s['material']}   mass {s['mass_g']} g   formed {s['formed_envelope']['size']} mm   "
          f"blank {s['blank']['width']} x {s['blank']['height']} mm, cut length {s['blank']['cut_length']} mm")
    for b in s["bends"]:
        print(f"  {b['id']}  {b['feature']:12s} {b['direction']:4s} {b['angle']:6.2f} deg  L={b['length']:6.2f}  BA={b['allowance']:.3f}")
    for r in s["checks"]:
        print(f"  [{'ok' if r['ok'] else 'FAIL'}] {r['check']}: {r['value']}  (need {r['requirement']})")
    print("ALL CHECKS PASS" if s["all_checks_pass"] else "*** CHECK FAILURES ***")


if __name__ == "__main__":
    if "--alu" in sys.argv:
        res = build(aluminium_variant(), OUT / "alu", "AL5052 2.0 mm")
    else:
        res = build(Design(), OUT, "SS304 1.5 mm")
    report(res["summary"])
    sys.exit(0 if res["summary"]["all_checks_pass"] else 1)
