"""PB-MO-003 (REV H): the stack mould that forms both rib supports, shared by both paddles.

Plans of the main plate's top face (Elongated pocket and teeth) and bottom face (Hybrid pocket and
teeth) 1:3, section X-X through the closed stack and both parts 1:2, detail Y of the edge 2:1,
hardware list and the moulding steps.
"""
from __future__ import annotations

import math

from shapely.affinity import scale as sh_scale
from shapely.affinity import translate
from shapely.geometry import LineString, Polygon, box
from shapely.ops import unary_union

from . import wave
from .geometry import CONSTRUCTION as C
from .geometry import Outline
from .mould import BOTTOM, MOULD, TOP, layout, ring, union_ring, vent_span
from .sheets import GREY, cell, core_inner, fill, hatches, notes_block, polygon_path, title_block
from .sheets_construction import _segments, break_line, view_label
from .svgkit import Doc, View, fmt, frame_iso

MOULD_NO = "PB-MO-003"
M = MOULD
BOLT = dict(shank=6.0, head_af=10.0, head_h=4.0, nut_h=5.0, washer_d=12.0, washer_t=1.6)
BOLT["length"] = 5.0 * math.ceil((M.height + 2 * BOLT["washer_t"] + BOLT["nut_h"] + 1.5) / 5.0)   # 1.5 proud


def _x_extent(poly: Polygon, y: float) -> float:
    """Half width at height y of a shapely polygon symmetric about x = 0."""
    seg = LineString([(-1000, y), (1000, y)]).intersection(poly)
    return max(abs(x) for x, _ in seg.coords) if seg.geom_type == "LineString" else \
        max(abs(x) for g in seg.geoms for x, _ in g.coords)


def teeth(side: int, x_half: float) -> list[tuple[float, float]]:
    """x intervals of the mould teeth on one side (+1 clamp plate, -1 main plate): the gaps between lands."""
    lands = wave.land_intervals(x_half, side)
    edges = [-x_half] + [x for iv in lands for x in iv] + [x_half]
    return [(a, b) for a, b in zip(edges[0::2], edges[1::2]) if b - a > 1e-3]


def _flutes(o: Outline, y: float):
    """Paddle-coordinate (x, z) pieces at height y: half width, frame inner edge, top flutes, bottom flutes, part."""
    h = M.h
    aw = o.half_width_at(y)
    xi = aw - C.frame_w
    wall = Polygon(wave.wall_polygon(-xi, xi, 1600)).buffer(0)
    voids = box(-xi, -h, xi, h).difference(wall)
    pieces = list(getattr(voids, "geoms", [voids]))
    top = [p for p in pieces if p.bounds[3] > h - 1e-6 and p.bounds[1] > -h + 1e-6]
    bot = [p for p in pieces if p.bounds[1] < -h + 1e-6 and p.bounds[3] < h - 1e-6]
    part = unary_union([box(-aw, -h, -xi, h), box(xi, -h, aw, h), wall])
    return aw, xi, unary_union(top), unary_union(bot), part


def _placed(g, up: bool):
    """A paddle-coordinate (x, z) polygon moved to its cavity in the stack (as mould.place does in 3-D)."""
    return translate(g, 0, M.shift) if up else translate(sh_scale(g, 1, -1, origin=(0, 0)), 0, -M.shift)


def section_geometry(outlines: dict, y: float) -> dict:
    """Shapely polygons (x, z) of the closed stack and both moulded rib supports cut at height y (blade)."""
    f, c, h = M.face, M.clamp, M.h
    pair = (outlines[TOP], outlines[BOTTOM])
    x_plate = _x_extent(Polygon(union_ring(pair, M.flange)), y)
    main = box(-x_plate, -f, x_plate, f)
    top = box(-x_plate, f, x_plate, f + c)
    bottom = box(-x_plate, -f - c, x_plate, -f)
    parts, info = {}, {}
    for key, up in ((TOP, True), (BOTTOM, False)):
        aw, xi, tf, bf, part = _flutes(outlines[key], y)
        g0, g1 = aw + M.land, aw + M.land + M.groove_w
        cut = unary_union([box(-aw, -h, aw, h + 1)] +
                          [box(lo, h - M.groove_d, hi, h + 1) for lo, hi in ((g0, g1), (-g1, -g0))])
        main = main.difference(_placed(cut, up)).union(_placed(bf, up))
        if up:
            top = top.union(_placed(tf, up))
        else:
            bottom = bottom.union(_placed(tf, up))
        parts[key] = _placed(part, up)
        info[key] = dict(aw=aw, xi=xi, g0=g0, g1=g1)
    bolts = [x for x, yb in layout(pair).bolts if abs(yb - y) < 0.5]
    for xb in bolts:
        hole = box(xb - M.bolt_d / 2, -f - c - 1, xb + M.bolt_d / 2, f + c + 1)
        main, top, bottom = main.difference(hole), top.difference(hole), bottom.difference(hole)
    b = BOLT
    hw, ww = b["head_af"] / 2, b["washer_d"] / 2
    steel = []
    for xb in bolts:
        z_top, z_bot = f + c + b["washer_t"], -f - c - b["washer_t"]
        steel += [box(xb - b["shank"] / 2, z_bot - b["nut_h"] - 1.5, xb + b["shank"] / 2, z_top),
                  box(xb - hw, z_top, xb + hw, z_top + b["head_h"]),
                  box(xb - ww, f + c, xb + ww, z_top), box(xb - ww, z_bot, xb + ww, -f - c),
                  box(xb - hw, z_bot - b["nut_h"], xb + hw, z_bot)]
    return dict(main=main, top=top, bottom=bottom, parts=parts, info=info, x_plate=x_plate, bolts=bolts,
                steel=unary_union(steel) if steel else None)


def mould_notes(outlines: dict, rep: dict | None) -> list[str]:
    nt, nb = outlines[TOP].spec.name, outlines[BOTTOM].spec.name
    mass = ""
    if rep:
        p = rep["plates"]
        mass = (f" PLA AT 100 %: MAIN {p['main_plate']['mass_g']['PLA'] / 1000:.1f}, TOP "
                f"{p['top_plate']['mass_g']['PLA'] / 1000:.1f}, BOTTOM {p['bottom_plate']['mass_g']['PLA'] / 1000:.1f} kg.")
    charge = (f" ≈ {rep['cavities'][TOP]['charge_g']:.0f} g ({nt}) AND {rep['cavities'][BOTTOM]['charge_g']:.0f} g ({nb}),"
              if rep else "")
    return [
        f"MAIN PLATE (1), TOP PLATE (2), BOTTOM PLATE (3): output/mould/mould_main_plate / _top_plate / _bottom_plate "
        f"(.stl / .step).\nTHE {fmt(M.main)} MAIN PLATE HOLDS BOTH CAVITIES: {nt} IN THE TOP FACE, {nb} IN THE BOTTOM "
        f"FACE, {fmt(M.web)} WEB BETWEEN.",
        f"EACH CAVITY IS THAT PADDLE'S RIB SUPPORT (SHEET 3): THE MAIN PLATE CARRIES THE BOTTOM-FLUTE TEETH, EACH "
        f"CLAMP PLATE ({fmt(M.clamp)} + {M.teeth:.1f} TEETH)\nTHE TOP-FLUTE TEETH. THE CLAMP PLATES SEAT FLAT ON THE "
        f"MAIN PLATE: CLOSED STACK {fmt(M.height)}, CORE HEIGHT {fmt(C.core_t)}, WALLS {fmt(C.rib_t)}, FRAME "
        f"{fmt(C.frame_w)}.",
        f"PRINT THE CLAMP PLATES BACK DOWN, TEETH UP, AND THE MAIN PLATE AS TWO {fmt(M.face)} HALVES SPLIT THROUGH THE "
        f"WEB\n(mould_main_upper_half / _lower_half.stl), EACH CAVITY UP; THE STACK BOLTS CLAMP THEM. ≥ 5 WALLS, ≥ 40 % "
        f"INFILL.{mass}",
        "PLA SOFTENS NEAR 55 °C: ROOM-TEMPERATURE-CURE EPOXY ONLY. FOR A WARM CURE PRINT IN PETG, ASA OR PA-CF. "
        "BED ≥ 440 mm, OR MACHINE THE STEP.",
        "DRY FIT FIRST WITH BOTH TRIAL RIB SUPPORT STLs PRINTED IN PLA: THE STACK MUST CLOSE FULLY. THEN SAND THE "
        "CAVITIES (P400 → P800),\nSEAL (EPOXY COAT), WAX ×3 + PVA.",
        f"FILL (FORGED CARBON){charge} HALF CHOPPED CARBON TOW (10–25 mm), HALF EPOXY BY MASS. MAIN PLATE {nb} "
        f"FACE UP:\nPACK THAT CAVITY, BOTTOM PLATE ON, 4 BOLTS; TURN THE PAIR OVER, PACK THE {nt} CAVITY, TOP PLATE ON.",
        "CLOSE: ALL BOLTS (4) FINGER-TIGHT, PRESS THE STACK BETWEEN 2 FLAT, STIFF PLATENS OR IN A PRESS UNTIL BOTH "
        "CLAMP PLATES SEAT;\nTIGHTEN THE BOLTS. EXCESS RESIN LEAVES BY THE OVERFLOW GROOVES AND THE VENTS.",
        "CURE 24 h AT ROOM TEMPERATURE, SPLIT AT THE PRY NOTCHES, EASE THE PARTS OUT FROM THE BUTT END WITH A "
        "PLASTIC WEDGE.\nTRIM THE FLASH, DRILL AND FIT THE M3 INSERTS (SHEET 3).",
    ]


def _plan(d: Doc, o: Outline, plate: Polygon, cx: float, top_y: float, S: float, lay, y1: float) -> View:
    """Plan of one face of the main plate: plate, pocket of paddle o and its teeth, groove, vents, bolts, notches."""
    pv = View(d, (cx, top_y + y1 * S), S)
    P = pv.P

    def T(x: float, y: float):
        return P((x, y))
    d.path(polygon_path(plate, T), "vis")
    d.path(pv.outline_path(o), "vis")
    inner = core_inner(o)
    for a, b in teeth(-1, o.spec.width / 2 + C.rib_pitch):
        for xa in (a, b):
            for seg in _segments(LineString([(xa, C.solid_to), (xa, 1000)]).intersection(inner)):
                d.poly([P(q) for q in seg], "thin")
        for seg in _segments(LineString([(a, C.solid_to), (b, C.solid_to)]).intersection(inner)):
            d.poly([P(q) for q in seg], "thin")
        for seg in _segments(inner.exterior.intersection(box(a, C.solid_to, b, 1000))):
            d.poly([P(q) for q in seg], "thin")
    for off in (M.land, M.land + M.groove_w):
        d.path(polygon_path(Polygon(ring(o, off)), T), "thin")
    for v in lay.vents:
        (qx, qy), (rx, ry) = vent_span(o, v)
        ln = math.hypot(rx - qx, ry - qy)
        ox, oy = -(ry - qy) / ln * M.vent_w / 2, (rx - qx) / ln * M.vent_w / 2
        for s in (-1, 1):
            pv.line((qx + s * ox, qy + s * oy), (rx + s * ox, ry + s * oy), "thin")
    for x, y in lay.bolts:
        d.circle(P((x, y)), M.bolt_d / 2 * S, "vis")
    for x, y, nx, ny in lay.notches:
        tx, ty = -ny, nx
        w2, dd = M.notch_w / 2, M.notch_depth
        d.poly([P((x + tx * w2, y + ty * w2)), P((x + tx * w2 - nx * dd, y + ty * w2 - ny * dd)),
                P((x - tx * w2 - nx * dd, y - ty * w2 - ny * dd)), P((x - tx * w2, y - ty * w2))], "vis")
    pv.line((0, -25), (0, y1 + 5), "ctr")
    return pv


def mould_sheet(outlines: dict, report: dict | None = None) -> Doc:
    """PB-MO-003: outlines = {design key: Outline} for both paddles."""
    o_t, o_b = outlines[TOP], outlines[BOTTOM]
    pair = (o_t, o_b)
    d = Doc(420, 297, f"{MOULD_NO} rib support stack mould")
    H_ = hatches(d)
    frame_iso(d)
    f, c = M.face, M.clamp
    lay = layout(pair)
    plate = Polygon(union_ring(pair, M.flange))
    x0, y0, x1, y1 = plate.bounds

    # ---- plans of the main plate, 1:3: top face (top paddle) and bottom face (bottom paddle)
    S = 1 / 3
    top_y = 32.0
    tv = _plan(d, o_t, plate, 72.0, top_y, S, lay, y1)
    bv = _plan(d, o_b, plate, 172.0, top_y, S, lay, y1)
    d.dim_linear(tv.P((x0, y1 - 30)), tv.P((x1, y1 - 30)), "x", top_y - 7, fmt(x1 - x0, 1))
    d.dim_linear(bv.P((x1 - 20, y0)), bv.P((x1 - 20, y1)), "y", bv.P((x1, 0))[0] + 7, fmt(y1 - y0, 1))
    ys = max(lay.bolts, key=lambda p: (p[0], -abs(p[1] - 300)))[1]          # section through a side bolt
    tv.section_line(ys, x0 - 4, x1 + 4, "X")
    d.leader_note(tv.P((teeth(-1, o_t.spec.width / 2)[3][0] + 2, 300)), (tv.P((x1, 0))[0] + 4, tv.P((0, 340))[1]),
                  "TEETH", 2.4, dot=True, arrow=False)
    view_label(d, 72.0, tv.P((0, y0))[1] + 9, "MAIN PLATE – TOP FACE",
               f"SCALE 1:3 · {o_t.spec.name} CAVITY, {fmt(C.core_t)} DEEP")
    view_label(d, 172.0, bv.P((0, y0))[1] + 9, "MAIN PLATE – BOTTOM FACE",
               f"SCALE 1:3 · {o_b.spec.name} CAVITY, {fmt(C.core_t)} DEEP")

    # ---- section X-X through the closed stack, 1:2
    g = section_geometry(outlines, ys)
    S2 = 0.5
    xs_c, zs_c = 318.0, 46.0

    def X(x: float, z: float):
        return (xs_c + x * S2, zs_c - z * S2)
    for key in ("top", "main", "bottom"):
        d.path(polygon_path(g[key], X), "vis", extra=fill(H_["cap"]) + ' fill-rule="evenodd"')
    for part in g["parts"].values():
        d.path(polygon_path(part, X), "thin", extra='style="fill:#000"')
    if g["steel"] is not None:
        d.path(polygon_path(g["steel"], X), "vis", extra=fill(H_["metal"]))
    xp = g["x_plate"]
    d.line((xs_c - xp * S2 - 4, zs_c), (xs_c + xp * S2 + 4, zs_c), "ctr")
    d.dim_linear(X(xp, -f - c), X(xp, f + c), "y", xs_c + xp * S2 + 16, fmt(M.height))
    for z0, z1, txt in ((f, f + c, M.clamp), (-f, f, M.main), (-f - c, -f, M.clamp)):
        d.dim_linear(X(xp, z0), X(xp, z1), "y", xs_c + xp * S2 + 8, fmt(txt))
    view_label(d, xs_c, zs_c + (f + c) * S2 + 13, "SECTION X–X",
               f"SCALE 1:2 · CLOSED STACK, PARTS BLACK: {o_t.spec.name} (TOP), {o_b.spec.name} (BOTTOM), M6 BOLT")

    # ---- detail Y: right-hand edge of the closed stack, 2:1
    S3 = 2.0
    it = g["info"][TOP]
    wx0, wx1 = it["xi"] - 14.0, xp + 0.5               # 14 mm of wave: at least one wall crossing
    wz0, wz1 = -f - 2.0, f + 2.0                         # clamp plates broken off (full heights in X-X)
    win = box(wx0, wz0, wx1, wz1)
    xd0, zd0 = 262.0 - wx0 * S3, 126.0

    def Y(x: float, z: float):
        return (xd0 + x * S3, zd0 - z * S3)
    for key, style in (("top", fill(H_["cap"])), ("main", fill(H_["cap"])), ("bottom", fill(H_["cap"]))):
        geom = g[key].intersection(win)
        if not geom.is_empty:
            d.path(polygon_path(geom, Y), "vis", extra=style + ' fill-rule="evenodd"')
    for part in g["parts"].values():
        geom = part.intersection(win)
        if not geom.is_empty:
            d.path(polygon_path(geom, Y), "vis", extra=fill(H_["cf"]) + ' fill-rule="evenodd"')
    break_line(d, Y(wx0, wz0), Y(wx0, wz1), 1.0)
    for zz in (wz0, wz1):
        break_line(d, Y(wx0, zz), Y(xp, zz), 1.0)
    xb_ = [x for x in g["bolts"] if x > 0]
    for xb in xb_:
        d.line(Y(xb, wz0 - 1.0), Y(xb, wz1 + 1.0), "ctr")
    xr = xp
    for z0, z1, txt in ((f - C.core_t, f, C.core_t), (-f + C.core_t, f - C.core_t, M.web), (-f, -f + C.core_t, C.core_t)):
        d.dim_linear(Y(xr, z0), Y(xr, z1), "y", Y(xr, 0)[0] + 5, fmt(txt))
    d.dim_linear(Y(it["aw"], 0), Y(xb_[0] if xb_ else it["aw"] + M.bolt_off, 0), "x", Y(0, wz0)[1] + 6,
                 fmt(M.bolt_off))
    d.dim_linear(Y(it["aw"], 0), Y(xr, 0), "x", Y(0, wz0)[1] + 12, fmt(M.flange))
    d.dim_linear(Y(it["xi"], f), Y(it["aw"], f), "x", Y(0, wz1)[1] - 6, fmt(C.frame_w))   # top cavity's frame
    d.leader_note(Y((it["g0"] + it["g1"]) / 2, f - M.groove_d / 2), (Y(it["g1"], 0)[0] + 6, Y(0, wz1)[1] - 4),
                  f"LAND {fmt(M.land)}, GROOVE {fmt(M.groove_w)} × {fmt(M.groove_d)}", 2.3)
    xw = min(wave.crossings(wx0 + 1.5, it["xi"] - 1), key=lambda x: abs(x - (wx0 + 6)))  # a wall at the mid-plane
    d.leader_note(Y(xw, M.shift), (Y(wx0, 0)[0] - 3, Y(0, wz0)[1] + 9),
                  f"{'WEB' if wave.is_square() else 'WALL'} {fmt(C.rib_t)} (CARBON)", 2.3)
    xl = (it["aw"] + xb_[0]) / 2 if xb_ else it["aw"] + 6
    d.text(Y(xl, 0.0), "MAIN PLATE", 2.2, fill=GREY)
    d.text((Y(wx0, 0)[0], Y(0, wz1)[1] - 2.0), "TOP PLATE (BROKEN)", 2.2, anchor="start", fill=GREY)
    d.text((Y(wx0, 0)[0] + 4, Y(0, wz0)[1] + 4.2), "BOTTOM PLATE (BROKEN)", 2.2, anchor="start", fill=GREY)
    view_label(d, (Y(wx0, 0)[0] + Y(xr, 0)[0]) / 2, Y(0, wz0)[1] + 21, "DETAIL Y",
               f"SCALE 2:1 · {o_t.spec.name} ABOVE THE WEB, {o_b.spec.name} BELOW · THE GAPS ARE THE WALLS AND FRAMES")

    # ---- hardware list
    tx, ty = 228.0, 201.0
    widths = (9.0, 74.0, 10.0)
    rows = [("ITEM", "PART", "QTY"),
            ("1", "Main plate, mould_main_plate (or the 2 halves)", "1"),
            ("2", "Top plate, mould_top_plate.stl", "1"),
            ("3", "Bottom plate, mould_bottom_plate.stl", "1"),
            ("4", f"Hex bolt M6 × {BOLT['length']:.0f}, 2 washers, nut", str(len(lay.bolts))),
            ("5", "Release wax + PVA; flat platens + clamps or a press", "a/r")]
    yy = ty
    for i, row in enumerate(rows):
        xx = tx
        for w, val in zip(widths, row):
            cell(d, xx, yy, w, 5.5, "", val, size=2.2, weight="bold" if i == 0 else "normal",
                 anchor="middle" if w < 12 else "start")
            xx += w
        yy += 5.5
    d.text((tx, ty - 2.5), "MOULD HARDWARE", 3.0, anchor="start", weight="bold")

    # ---- notes + title block
    notes_block(d, 28.0, 198.0, mould_notes(outlines, report), size=2.15, lead=3.05)
    title_block(d, 225.0, 236.0, o_t.spec, f"BOTH PADDLES · MAIN {fmt(M.main)} + 2 CLAMP PLATES {fmt(M.clamp)} (+ TEETH) · "
                f"CLOSED {fmt(M.height)} · {fmt(x1 - x0, 1)} × {fmt(y1 - y0, 1)} mm", "1:3, 1:2, 2:1", "1 / 1", "A3",
                title="RIB SUPPORT STACK MOULD", drawing_no=MOULD_NO, material="PLA / PETG (NOTE 3)")
    return d
