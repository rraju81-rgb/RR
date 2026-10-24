"""Sheet 4 of each paddle drawing (REV D): the two-half compression mould.

Plan of the parting face 1:2, section X-X through the closed mould and a bolt 1:2, detail Y of the
edge 3:1 (clearance, draft, land, overflow groove, bolt line), hardware list and the moulding steps.
"""
from __future__ import annotations

import math

from shapely.affinity import scale as sh_scale
from shapely.geometry import LineString, Polygon, box
from shapely.ops import unary_union

from . import wave
from .geometry import CONSTRUCTION as C
from .geometry import Outline
from .mould import MOULD, layout, ring
from .sheets import GREY, SHEETS, cell, fill, hatches, notes_block, polygon_path, title_block
from .sheets_construction import break_line, view_label
from .svgkit import Doc, View, fmt, frame_iso

M = MOULD
BOLT = dict(shank=6.0, head_af=10.0, head_h=4.0, nut_h=5.0, washer_d=12.0, washer_t=1.6, length=45.0)


def _x_extent(o: Outline, off: float, y: float) -> float:
    """Half width at height y of the body outline offset by `off`."""
    seg = LineString([(-500, y), (500, y)]).intersection(Polygon(ring(o, off)))
    return max(abs(x) for x, _ in seg.coords) if seg.geom_type == "LineString" else \
        max(abs(x) for g in seg.geoms for x, _ in g.coords)


def section_geometry(o: Outline, y: float) -> dict:
    """Shapely polygons (x, z) of the closed mould and the sandwich cut at height y."""
    D, H, T = M.depth, M.height, C.thickness / 2
    aw = o.half_width_at(y)
    x_plate = _x_extent(o, M.clearance + M.flange, y)
    x_floor = _x_extent(o, M.clearance, y)
    x_face = x_floor + D * math.tan(math.radians(M.draft))
    g0, g1 = _x_extent(o, M.clearance + M.land, y), _x_extent(o, M.clearance + M.land + M.groove_w, y)
    bolts = [x for x, yb in layout(o).bolts if abs(yb - y) < 0.5]
    half = box(-x_plate, -H, x_plate, 0.0)
    half = half.difference(Polygon([(-x_floor, -D), (x_floor, -D), (x_face, 0.01), (-x_face, 0.01)]))
    for s in (-1, 1):
        lo, hi = sorted((s * g0, s * g1))
        half = half.difference(box(lo, -M.groove_d, hi, 0.01))
    for xb in bolts:
        half = half.difference(box(xb - M.bolt_d / 2, -H - 1, xb + M.bolt_d / 2, 1))
    top = sh_scale(half, 1.0, -1.0, origin=(0, 0))
    skins = unary_union([box(-aw, C.core_t / 2, aw, T), box(-aw, -T, aw, -C.core_t / 2)])
    xi = aw - C.frame_w
    if y > C.solid_to + C.runout_len:
        core = unary_union([box(-aw, -C.core_t / 2, -xi, C.core_t / 2), box(xi, -C.core_t / 2, aw, C.core_t / 2),
                            Polygon(wave.wall_polygon(-xi, xi)).buffer(0)])
    else:
        core = box(-aw, -C.core_t / 2, aw, C.core_t / 2)
    b = BOLT
    hw, ww = b["head_af"] / 2, b["washer_d"] / 2
    steel = []
    for xb in bolts:
        z_head = H + b["washer_t"]
        steel += [box(xb - b["shank"] / 2, -H - b["washer_t"] - b["nut_h"] - 1.5, xb + b["shank"] / 2, z_head),
                  box(xb - hw, z_head, xb + hw, z_head + b["head_h"]),
                  box(xb - ww, H, xb + ww, H + b["washer_t"]), box(xb - ww, -H - b["washer_t"], xb + ww, -H),
                  box(xb - hw, -H - b["washer_t"] - b["nut_h"], xb + hw, -H - b["washer_t"])]
    return dict(bottom=half, top=top, skins=skins, core=core, steel=unary_union(steel) if steel else None,
                aw=aw, x_plate=x_plate, x_floor=x_floor, x_face=x_face, g0=g0, g1=g1, bolts=bolts)


def mould_notes(o: Outline, rep: dict | None) -> list[str]:
    sp = o.spec
    mass = f" ABOUT {rep['mass_g']['PLA'] / 1000:.1f} kg OF PLA AT 100 % INFILL." if rep else ""
    return [
        f"MOULD HALF (1): PRINT TWICE – BOTH HALVES ARE THE SAME PART (output/mould/{sp.key}_mould_half.stl / .step); "
        f"TURN ONE\nOVER ONTO THE OTHER. POCKET {fmt(M.depth)} DEEP IN EACH HALF = CAVITY {fmt(C.thickness)} = SKIN "
        f"{fmt(C.face_t)} + RIB SUPPORT {fmt(C.core_t)} + SKIN {fmt(C.face_t)} WHEN THE FLANGES MEET.",
        f"PRINT POCKET UP, BACK ON THE BED: ≥ 5 WALLS, ≥ 40 % INFILL, 6 TOP LAYERS + IRONING ON THE POCKET FLOOR. "
        f"NEEDS A ≥ 440 mm BED;\nOR MACHINE THE STEP FROM ALUMINIUM / HDPE.{mass}",
        "PLA SOFTENS NEAR 55 °C: ROOM-TEMPERATURE-CURE EPOXY ONLY. FOR A WARM POST-CURE PRINT IN PETG, ASA OR PA-CF.",
        "PREPARE: SAND THE POCKET FLOORS (P400 → P800), SEAL (EPOXY COAT OR PRIMER), WAX + PVA RELEASE, OR LINE "
        "WITH\nRELEASE FILM. PRESS THE 4 DOWEL PINS (3) INTO ONE HALF.",
        f"LAY UP IN THE BOTTOM HALF: SKIN (CUT TO THE PROFILE, 0.5 UNDERSIZE), WET OUT → RIB SUPPORT (FACES "
        f"ABRADED, M3 INSERT\nFITTED, SCREW IN IT) → TOP SKIN, WET OUT → TOP HALF OVER THE DOWELS. THE POCKET "
        f"LOCATES THE RIB SUPPORT (+{fmt(M.clearance)}).",
        "CLOSE: BOLTS (2) FINGER-TIGHT, THEN PRESS THE MOULD BETWEEN 2 FLAT, STIFF PLATENS (≥ 18 mm PLY OR "
        "ALUMINIUM, CLAMPS\nEVERY ~100 mm), IN A PRESS OR IN A VACUUM BAG UNTIL THE FLANGES MEET; THEN TIGHTEN "
        "THE BOLTS. BOLTS ALONE BOW\nA PRINTED MOULD AND CANNOT PRESS THE MIDDLE OF THE BLADE.",
        f"EXCESS RESIN FILLS THE OVERFLOW GROOVE ({fmt(M.groove_w)} × {fmt(M.groove_d)} IN EACH HALF) AND LEAVES BY "
        f"THE {len(layout(o).vents)} VENTS. CURE, SPLIT AT THE\nPRY NOTCHES, TRIM THE FLASH AT THE EDGE.",
        f"MEASURE THE RIB SUPPORT ({fmt(C.core_t)} ±0.1) BEFORE MOULDING; SAND THE LANDS IF THICK. SHIM THE "
        "FLANGE (TAPE / FOIL) TO OPEN THE\nCAVITY, E.G. FOR PRE-CURED SKINS AND GLUE LINES.",
    ]


def mould_sheet(o: Outline, report: dict | None = None) -> Doc:
    sp = o.spec
    d = Doc(420, 297, f"{sp.drawing_no} {sp.name} paddle - compression mould")
    H_ = hatches(d)
    frame_iso(d)
    D, Hm = M.depth, M.height
    lay = layout(o)

    # ---- plan view of the parting face, 1:2
    S = 0.5
    plate = Polygon(ring(o, M.clearance + M.flange))
    x0, y0, x1, y1 = plate.bounds
    cx, top_y = 100.0, 30.0
    oy = top_y + y1 * S
    pv = View(d, (cx, oy), S)
    P = pv.P

    def T(x: float, y: float):
        return P((x, y))
    d.path(polygon_path(plate, T), "vis")
    d.path(polygon_path(Polygon(ring(o, M.clearance + D * math.tan(math.radians(M.draft)))), T), "vis")
    for off in (M.clearance + M.land, M.clearance + M.land + M.groove_w):
        d.path(polygon_path(Polygon(ring(o, off)), T), "thin")
    for x, y in lay.bolts:
        d.circle(P((x, y)), M.bolt_d / 2 * S, "vis")
    for x, y in lay.dowels:
        d.circle(P((x, y)), M.dowel_d / 2 * S, "vis")
        d.circle(P((x, y)), M.dowel_d / 2 * S * 0.45, "thin", extra='style="fill:#000"')
    e_in = M.bolt_off - M.land - M.groove_w / 2
    for x, y, nx, ny in lay.vents:                 # two lines, groove centre to the plate edge
        for s in (-1, 1):
            ox, oy_ = -ny * s * M.vent_w / 2, nx * s * M.vent_w / 2
            pv.line((x - nx * e_in + ox, y - ny * e_in + oy_),
                    (x + nx * (M.flange - M.bolt_off) + ox, y + ny * (M.flange - M.bolt_off) + oy_), "thin")
    for x, y, nx, ny in lay.notches:               # (x, y) on the plate edge
        tx, ty = -ny, nx
        w2, dd = M.notch_w / 2, M.notch_depth
        d.poly([P((x + tx * w2, y + ty * w2)), P((x + tx * w2 - nx * dd, y + ty * w2 - ny * dd)),
                P((x - tx * w2 - nx * dd, y - ty * w2 - ny * dd)), P((x - tx * w2, y - ty * w2))], "vis")
    pv.line((0, y0 - 6), (0, y1 + 6), "ctr")
    # dimensions and callouts
    d.dim_linear(P((x0, y1 - 40)), P((x1, y1 - 40)), "x", top_y - 8, fmt(x1 - x0, 1))
    d.dim_linear(P((x0 + 30, y0)), P((x0 + 30, y1)), "y", P((x0, 0))[0] - 8, fmt(y1 - y0, 1))
    bx, by = max(lay.bolts, key=lambda p: (p[0], -abs(p[1] - 300)))
    yb_tip = max(lay.bolts, key=lambda p: p[1])
    d.leader_note(P((yb_tip[0] + 2.0, yb_tip[1] + 2.0)), (P((0, 0))[0] + 26, top_y - 3),
                  f"{len(lay.bolts)} × Ø{fmt(M.bolt_d)} THRU (M6)", 2.6)
    dx_, dy_ = lay.dowels[0]
    d.leader_note(P((dx_ + 2.2, dy_ + 2.2)), (P((x1, 0))[0] + 4, P((0, dy_ + 30))[1]),
                  f"{len(lay.dowels)} × Ø{fmt(M.dowel_d)} ↧{fmt(M.dowel_depth)} (DOWEL)", 2.6)
    nx_, ny_, *_ = lay.notches[0]
    d.leader_note(P((nx_ - 2.0, ny_)), (P((x1, 0))[0] + 4, P((0, ny_ - 22))[1]),
                  f"{len(lay.notches)} × PRY NOTCH {fmt(M.notch_w)} × {fmt(M.notch_depth)} × {fmt(M.notch_h)}", 2.6)
    vx, vy, vnx, vny = lay.vents[2]
    d.leader_note(P((vx + vnx * 4, vy + vny * 4)), (P((x1, 0))[0] + 4, P((0, vy + 30))[1]),
                  f"{len(lay.vents)} × VENT {fmt(M.vent_w)} × {fmt(M.vent_d)}", 2.6)
    yg = 230.0
    xg = _x_extent(o, M.clearance + M.land + M.groove_w / 2, yg)
    d.leader_note(P((xg, yg)), (P((x1, 0))[0] + 4, P((0, yg - 20))[1]),
                  f"OVERFLOW GROOVE {fmt(M.groove_w)} × {fmt(M.groove_d)}", 2.6)
    yp = 330.0
    d.leader_note(P((o.half_width_at(yp) - 20, yp)), (P((x1, 0))[0] + 4, P((0, yp + 40))[1]),
                  f"POCKET ↧{fmt(M.depth)}, {fmt(M.draft)}° DRAFT", 2.6, dot=True, arrow=False)
    ys = by                                         # section through the bolt on the side
    pv.section_line(ys, x0 - 6, x1 + 6, "X")
    view_label(d, cx, P((0, y0))[1] + 12, "MOULD HALF – PARTING FACE",
               "SCALE 1:2 · BOTH HALVES ARE THIS PART")

    # ---- section X-X (closed mould with the sandwich), 1:2
    g = section_geometry(o, ys)
    xs_c, zs_c = 300.0, 42.0

    def X(x: float, z: float):
        return (xs_c + x * S, zs_c - z * S)
    d.path(polygon_path(g["bottom"], X), "vis", extra=fill(H_["cap"]) + ' fill-rule="evenodd"')
    d.path(polygon_path(g["top"], X), "vis", extra=fill(H_["cap"]) + ' fill-rule="evenodd"')
    d.path(polygon_path(g["core"], X), "thin", extra='style="fill:#000"')
    d.path(polygon_path(g["skins"], X), "thin", extra='style="fill:#000"')
    if g["steel"] is not None:
        d.path(polygon_path(g["steel"], X), "vis", extra=fill(H_["metal"]))
    d.line((xs_c - g["x_plate"] * S - 5, zs_c), (xs_c + g["x_plate"] * S + 5, zs_c), "ctr")
    d.dim_linear(X(g["x_plate"], -Hm), X(g["x_plate"], Hm), "y", xs_c + g["x_plate"] * S + 9, fmt(2 * Hm))
    view_label(d, xs_c, zs_c + Hm * S + 12, "SECTION X–X",
               f"SCALE 1:2 · CLOSED MOULD, SANDWICH {fmt(C.face_t)} / {fmt(C.core_t)} / {fmt(C.face_t)}, M6 BOLT")

    # ---- detail Y: right-hand edge of the closed mould, 3:1
    S3 = 3.0
    aw = g["aw"]
    wx0, wx1, wz = aw - 5.0, g["x_plate"] + 0.5, 8.0
    win = box(wx0, -wz, wx1, wz)
    xd0, zd0 = 228.0 - wx0 * S3, 100.0

    def Y(x: float, z: float):
        return (xd0 + x * S3, zd0 - z * S3)
    for key, cls, style in (("bottom", "vis", fill(H_["cap"])), ("top", "vis", fill(H_["cap"])),
                            ("core", "vis", fill(H_["core"])), ("skins", "thin", 'style="fill:#000"')):
        geom = g[key].intersection(win)
        if not geom.is_empty:
            d.path(polygon_path(geom, Y), cls, extra=style + ' fill-rule="evenodd"')
    for zz in (-wz, wz):
        break_line(d, Y(wx0, zz), Y(g["x_plate"], zz), 1.0)
    break_line(d, Y(wx0, -wz), Y(wx0, wz), 1.0)
    xb_ = [x for x in g["bolts"] if x > 0]
    for xb in xb_:
        d.line(Y(xb, -wz - 1.5), Y(xb, wz + 1.5), "ctr")
    xf = g["x_floor"]
    d.dim_linear(Y(xf, -D), Y(xf, D), "y", Y(wx0, 0)[0] - 5, fmt(C.thickness))
    d.dim_linear(Y(xf, 0), Y(xf, -D), "y", Y(wx0, 0)[0] - 11, fmt(D))
    d.dim_linear(Y(xf, 0), Y(xb_[0] if xb_ else xf + M.bolt_off, 0), "x", Y(0, -wz)[1] + 5, fmt(M.bolt_off))
    d.dim_linear(Y(xf, 0), Y(g["x_plate"], 0), "x", Y(0, -wz)[1] + 11, fmt(M.flange))
    d.leader_note(Y((g["g0"] + g["g1"]) / 2, -M.groove_d / 2), (Y(g["g1"], 0)[0] + 9, Y(0, wz)[1] - 3),
                  f"LAND {fmt(M.land)}, GROOVE {fmt(M.groove_w)} × {fmt(M.groove_d)} EACH HALF", 2.4)
    d.leader_note(Y(aw + M.clearance / 2, -3.0), (Y(wx0, 0)[0] - 14, Y(0, -wz)[1] + 15),
                  f"{fmt(M.clearance)} CLEARANCE, {fmt(M.draft)}° DRAFT", 2.4)
    d.leader_note(Y(aw - 2.0, C.core_t / 2 + C.face_t / 2), (Y(wx0, 0)[0] + 3, Y(0, wz)[1] - 3),
                  f"SKIN {fmt(C.face_t)}", 2.4, dot=True, arrow=False)
    d.text(Y(aw - C.frame_w / 2 + 0.5, -0.8), "RIB", 2.2, fill=GREY)
    xm = (g["g1"] + (xb_[0] if xb_ else g["x_plate"])) / 2
    d.text(Y(xm, wz / 2), "TOP HALF", 2.2, fill=GREY)
    d.text(Y(xm, -wz / 2 - 0.8), "BOTTOM HALF", 2.2, fill=GREY)
    view_label(d, (Y(wx0, 0)[0] + Y(g["x_plate"], 0)[0]) / 2, Y(0, -wz)[1] + 22, "DETAIL Y",
               "SCALE 3:1 · EDGE OF THE CLOSED MOULD AT X–X")

    # ---- hardware list
    tx, ty = 320.0, 82.0
    widths = (9.0, 64.0, 10.0)
    rows = [("ITEM", "PART", "QTY"),
            ("1", f"Mould half, {sp.key}_mould_half.stl (print 2)", "2"),
            ("2", f"Hex bolt M6 × {BOLT['length']:.0f}, 2 washers, nut", str(len(lay.bolts))),
            ("3", "Dowel pin Ø6 × 20, steel (ISO 2338)", str(len(lay.dowels))),
            ("4", "Release wax + PVA, or release film", "a/r"),
            ("5", "Flat platens ≥ 18 mm + clamps, or press", "2")]
    yy = ty
    for i, row in enumerate(rows):
        xx = tx
        for w, val in zip(widths, row):
            cell(d, xx, yy, w, 6.0, "", val, size=2.3, weight="bold" if i == 0 else "normal",
                 anchor="middle" if w < 12 else "start")
            xx += w
        yy += 6.0
    d.text((tx, ty - 2.5), "MOULD HARDWARE", 3.0, anchor="start", weight="bold")

    # ---- notes + title block
    notes_block(d, 228.0, 162.0, mould_notes(o, report), size=2.2, lead=3.1)
    title_block(d, 225.0, 236.0, sp, f"TWO-HALF COMPRESSION MOULD  ·  CAVITY {fmt(C.thickness)} mm  ·  "
                f"{fmt(x1 - x0, 1)} × {fmt(y1 - y0, 1)} × {fmt(Hm)} mm PER HALF", "1:2, 3:1", f"4 / {SHEETS}", "A3",
                title=f"COMPRESSION MOULD – {sp.name}", material="PLA / PETG (NOTE 2)")
    return d
