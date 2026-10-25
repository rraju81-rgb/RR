"""Sheet 4 of each paddle drawing (REV E): the two-half wave mould that forms the rib support.

Plans of the tray (bottom half, teeth up) and of the lid's underside 1:3, section X-X through the
closed mould and the part 1:2, detail Y of the edge 2:1, hardware list and the moulding steps.
"""
from __future__ import annotations

from shapely.geometry import LineString, Polygon, box
from shapely.ops import unary_union

from . import wave
from .geometry import CONSTRUCTION as C
from .geometry import Outline
from .mould import MOULD, layout, ring
from .sheets import GREY, SHEETS, cell, core_inner, fill, hatches, notes_block, polygon_path, title_block
from .sheets_construction import _segments, break_line, view_label
from .svgkit import Doc, View, fmt, frame_iso

M = MOULD
BOLT = dict(shank=6.0, head_af=10.0, head_h=4.0, nut_h=5.0, washer_d=12.0, washer_t=1.6, length=50.0)


def _x_extent(o: Outline, off: float, y: float) -> float:
    """Half width at height y of the body outline offset by `off`."""
    seg = LineString([(-500, y), (500, y)]).intersection(Polygon(ring(o, off)))
    return max(abs(x) for x, _ in seg.coords) if seg.geom_type == "LineString" else \
        max(abs(x) for g in seg.geoms for x, _ in g.coords)


def teeth(side: int, x_half: float) -> list[tuple[float, float]]:
    """x intervals of the mould teeth on one side (+1 lid, -1 tray): the gaps between that side's lands."""
    lands = wave.land_intervals(x_half, side)
    edges = [-x_half] + [x for iv in lands for x in iv] + [x_half]
    return [(a, b) for a, b in zip(edges[0::2], edges[1::2]) if b - a > 1e-3]


def section_geometry(o: Outline, y: float) -> dict:
    """Shapely polygons (x, z) of the closed mould and the moulded rib support cut at height y (blade)."""
    h, fl, lt = M.h, M.floor, M.lid
    aw = o.half_width_at(y)
    xi = aw - C.frame_w
    x_plate = _x_extent(o, M.flange, y)
    wall = Polygon(wave.wall_polygon(-xi, xi, 1600)).buffer(0)
    voids = box(-xi, -h, xi, h).difference(wall)
    pieces = list(getattr(voids, "geoms", [voids]))
    top = [p for p in pieces if p.bounds[3] > h - 1e-6 and p.bounds[1] > -h + 1e-6]
    bot = [p for p in pieces if p.bounds[1] < -h + 1e-6 and p.bounds[3] < h - 1e-6]
    bolts = [x for x, yb in layout(o).bolts if abs(yb - y) < 0.5]
    g0, g1 = aw + M.land, aw + M.land + M.groove_w
    tray = box(-x_plate, -h - fl, x_plate, h).difference(box(-aw, -h, aw, h + 1)).union(unary_union(bot))
    for s in (-1, 1):
        lo, hi = sorted((s * g0, s * g1))
        tray = tray.difference(box(lo, h - M.groove_d, hi, h + 1))
    lid = box(-x_plate, h, x_plate, h + lt).union(unary_union(top))
    for xb in bolts:
        hole = box(xb - M.bolt_d / 2, -h - fl - 1, xb + M.bolt_d / 2, h + lt + 1)
        tray, lid = tray.difference(hole), lid.difference(hole)
    part = unary_union([box(-aw, -h, -xi, h), box(xi, -h, aw, h), wall])
    b = BOLT
    hw, ww = b["head_af"] / 2, b["washer_d"] / 2
    steel = []
    for xb in bolts:
        z_top, z_bot = h + lt + b["washer_t"], -h - fl - b["washer_t"]
        steel += [box(xb - b["shank"] / 2, z_bot - b["nut_h"] - 1.5, xb + b["shank"] / 2, z_top),
                  box(xb - hw, z_top, xb + hw, z_top + b["head_h"]),
                  box(xb - ww, h + lt, xb + ww, z_top), box(xb - ww, z_bot, xb + ww, -h - fl),
                  box(xb - hw, z_bot - b["nut_h"], xb + hw, z_bot)]
    return dict(tray=tray, lid=lid, part=part, steel=unary_union(steel) if steel else None, aw=aw, xi=xi,
                x_plate=x_plate, g0=g0, g1=g1, bolts=bolts)


def mould_notes(o: Outline, rep: dict | None) -> list[str]:
    sp = o.spec
    mass = ""
    if rep:
        mass = (f" ABOUT {rep['bottom']['mass_g']['PLA'] / 1000:.1f} + {rep['top']['mass_g']['PLA'] / 1000:.1f} kg OF "
                f"PLA AT 100 %.")
    part = f" THE PART WEIGHS ≈ {rep['part_mass_g']:.0f} g." if rep else ""
    return [
        f"TRAY (1) + LID (2): output/mould/{sp.key}_mould_bottom / _top (.stl / .step). THE CAVITY BETWEEN THEM IS THE "
        f"RIB\nSUPPORT (SHEET 3); THE TEETH ARE ITS FLUTES. THE LID SEATS ON THE TRAY RIM: CORE HEIGHT {fmt(C.core_t)}, "
        f"WALLS {fmt(C.rib_t)}.",
        f"PRINT BOTH BACK DOWN, TEETH UP: ≥ 5 WALLS, ≥ 40 % INFILL, 0.12–0.16 LAYERS FOR THE TEETH, IRONING ON FLAT "
        f"TOPS.\nNEEDS A ≥ 440 mm BED, OR MACHINE THE STEP FROM ALUMINIUM.{mass}",
        "PLA SOFTENS NEAR 55 °C: ROOM-TEMPERATURE-CURE EPOXY ONLY. FOR A WARM CURE PRINT IN PETG, ASA OR PA-CF.",
        "PREPARE: SAND THE CAVITY FACES (P400 → P800), SEAL (EPOXY COAT), WAX ×3 + PVA. PRESS THE 4 DOWEL PINS (4) "
        "INTO\nTHE TRAY. PLUG THE EJECTOR HOLES FROM BELOW WITH TAPE.",
        "FILL (FORGED CARBON): CHOP CARBON TOW TO 10–25 mm, WET IT WITH EPOXY (≈ 40 % FIBRE BY VOLUME). PACK THE "
        "WALL\nGAPS AND THE FRAME FIRST, THEN THE SOLID HANDLE ZONE; OVERFILL BY ≈ 10 %.",
        "CLOSE: LID OVER THE DOWELS, BOLTS (3) FINGER-TIGHT, THEN PRESS BETWEEN 2 FLAT, STIFF PLATENS OR IN A PRESS "
        "UNTIL\nTHE LID SEATS ON THE RIM; TIGHTEN THE BOLTS. EXCESS RESIN LEAVES BY THE OVERFLOW GROOVE AND THE VENTS.",
        "CURE (24 h AT ROOM TEMPERATURE), SPLIT AT THE PRY NOTCHES, LIFT THE LID STRAIGHT UP, PUSH THE PART OUT WITH "
        f"THE 4\nEJECTOR PINS. TRIM THE FLASH, DRILL AND FIT THE M3 INSERT (SHEET 3).{part}",
        "TRIAL FIRST: PRINT THE RIB SUPPORT STL IN PLA AND CLOSE THE EMPTY MOULD ON IT – IT MUST SEAT FULLY.",
    ]


def _plan(d: Doc, o: Outline, cx: float, top_y: float, S: float, side: int, lay, x1: float, y1: float) -> View:
    """Plan of one half: plate, pocket / lid footprint, teeth, flange features.  side -1 tray, +1 lid."""
    pv = View(d, (cx, top_y + y1 * S), S)
    P = pv.P

    def T(x: float, y: float):
        return P((x, y))
    d.path(polygon_path(Polygon(ring(o, M.flange)), T), "vis")
    d.path(pv.outline_path(o), "vis" if side < 0 else "thin")
    inner = core_inner(o)
    for a, b in teeth(side, o.spec.width / 2 + C.rib_pitch):
        for xa in (a, b):
            for seg in _segments(LineString([(xa, C.solid_to), (xa, 1000)]).intersection(inner)):
                d.poly([P(q) for q in seg], "thin")
        for seg in _segments(LineString([(a, C.solid_to), (b, C.solid_to)]).intersection(inner)):
            d.poly([P(q) for q in seg], "thin")
        for seg in _segments(inner.exterior.intersection(box(a, C.solid_to, b, 1000))):
            d.poly([P(q) for q in seg], "thin")
    if side < 0:
        for off in (M.land, M.land + M.groove_w):
            d.path(polygon_path(Polygon(ring(o, off)), T), "thin")
        e_in = M.bolt_off - M.land - M.groove_w / 2
        for x, y, nx, ny in lay.vents:
            for s in (-1, 1):
                ox, oy = -ny * s * M.vent_w / 2, nx * s * M.vent_w / 2
                pv.line((x - nx * e_in + ox, y - ny * e_in + oy),
                        (x + nx * (M.flange - M.bolt_off) + ox, y + ny * (M.flange - M.bolt_off) + oy), "thin")
        for x, y in lay.ejectors:
            d.circle(P((x, y)), M.ejector_d / 2 * S, "hid")
    for x, y in lay.bolts:
        d.circle(P((x, y)), M.bolt_d / 2 * S, "vis")
    for x, y in lay.dowels:
        d.circle(P((x, y)), M.dowel_d / 2 * S, "vis", extra='style="fill:#000"')
    for x, y, nx, ny in lay.notches:
        tx, ty = -ny, nx
        w2, dd = M.notch_w / 2, M.notch_depth
        d.poly([P((x + tx * w2, y + ty * w2)), P((x + tx * w2 - nx * dd, y + ty * w2 - ny * dd)),
                P((x - tx * w2 - nx * dd, y - ty * w2 - ny * dd)), P((x - tx * w2, y - ty * w2))], "vis")
    pv.line((0, -25), (0, y1 + 5), "ctr")
    return pv


def mould_sheet(o: Outline, report: dict | None = None) -> Doc:
    sp = o.spec
    d = Doc(420, 297, f"{sp.drawing_no} {sp.name} paddle - rib support mould")
    H_ = hatches(d)
    frame_iso(d)
    h, fl, lt = M.h, M.floor, M.lid
    lay = layout(o)
    plate = Polygon(ring(o, M.flange))
    x0, y0, x1, y1 = plate.bounds

    # ---- plans, 1:3: tray (teeth up) and lid underside (teeth towards the viewer)
    S = 1 / 3
    top_y = 32.0
    tv = _plan(d, o, 72.0, top_y, S, -1, lay, x1, y1)
    lv = _plan(d, o, 172.0, top_y, S, +1, lay, x1, y1)
    d.dim_linear(tv.P((x0, y1 - 30)), tv.P((x1, y1 - 30)), "x", top_y - 7, fmt(x1 - x0, 1))
    d.dim_linear(lv.P((x1 - 20, y0)), lv.P((x1 - 20, y1)), "y", lv.P((x1, 0))[0] + 7, fmt(y1 - y0, 1))
    ys = max(lay.bolts, key=lambda p: (p[0], -abs(p[1] - 300)))[1]          # section through a side bolt
    tv.section_line(ys, x0 - 4, x1 + 4, "X")
    d.leader_note(tv.P((teeth(-1, sp.width / 2)[3][0] + 2, 300)), (tv.P((x1, 0))[0] + 4, tv.P((0, 340))[1]),
                  "TEETH", 2.4, dot=True, arrow=False)
    ex, ey = lay.ejectors[1]
    d.leader_note(tv.P((ex + 1.5, ey + 1.5)), (tv.P((x1, 0))[0] + 4, tv.P((0, ey + 25))[1]),
                  f"{len(lay.ejectors)} × Ø{fmt(M.ejector_d)} EJECTOR", 2.4)
    view_label(d, 72.0, tv.P((0, y0))[1] + 9, "TRAY (BOTTOM HALF)", "SCALE 1:3 · TEETH = BOTTOM FLUTES")
    view_label(d, 172.0, lv.P((0, y0))[1] + 9, "LID, UNDERSIDE", "SCALE 1:3 · TEETH = TOP FLUTES")

    # ---- section X-X through the closed mould, 1:2
    g = section_geometry(o, ys)
    S2 = 0.5
    xs_c, zs_c = 318.0, 44.0

    def X(x: float, z: float):
        return (xs_c + x * S2, zs_c - z * S2)
    for key in ("tray", "lid"):
        d.path(polygon_path(g[key], X), "vis", extra=fill(H_["cap"]) + ' fill-rule="evenodd"')
    d.path(polygon_path(g["part"], X), "thin", extra='style="fill:#000"')
    if g["steel"] is not None:
        d.path(polygon_path(g["steel"], X), "vis", extra=fill(H_["metal"]))
    d.line((xs_c - g["x_plate"] * S2 - 4, zs_c), (xs_c + g["x_plate"] * S2 + 4, zs_c), "ctr")
    d.dim_linear(X(g["x_plate"], -h - fl), X(g["x_plate"], h + lt), "y", xs_c + g["x_plate"] * S2 + 9,
                 fmt(fl + 2 * h + lt))
    view_label(d, xs_c, zs_c + (h + fl) * S2 + 13, "SECTION X–X",
               "SCALE 1:2 · CLOSED MOULD, MOULDED RIB SUPPORT BLACK, M6 BOLT")

    # ---- detail Y: right-hand edge of the closed mould, 2:1
    S3 = 2.0
    aw, xi = g["aw"], g["xi"]
    wx0, wx1 = aw - 25.0, g["x_plate"] + 0.5
    wz0, wz1 = -h - 4.0, h + 4.0                         # floor and lid broken off (full heights in X-X)
    win = box(wx0, wz0, wx1, wz1)
    xd0, zd0 = 262.0 - wx0 * S3, 101.0

    def Y(x: float, z: float):
        return (xd0 + x * S3, zd0 - z * S3)
    for key, style in (("tray", fill(H_["cap"])), ("lid", fill(H_["cap"])), ("part", fill(H_["cf"]))):
        geom = g[key].intersection(win)
        if not geom.is_empty:
            d.path(polygon_path(geom, Y), "vis", extra=style + ' fill-rule="evenodd"')
    break_line(d, Y(wx0, wz0), Y(wx0, wz1), 1.0)
    for zz in (wz0, wz1):
        break_line(d, Y(wx0, zz), Y(g["x_plate"], zz), 1.0)
    xb_ = [x for x in g["bolts"] if x > 0]
    for xb in xb_:
        d.line(Y(xb, wz0 - 1.0), Y(xb, wz1 + 1.0), "ctr")
    xr = g["x_plate"]
    d.dim_linear(Y(xr, -h), Y(xr, h), "y", Y(xr, 0)[0] + 5, fmt(C.core_t))
    d.dim_linear(Y(aw, 0), Y(xb_[0] if xb_ else aw + M.bolt_off, 0), "x", Y(0, wz0)[1] + 11, fmt(M.bolt_off))
    d.dim_linear(Y(aw, 0), Y(xr, 0), "x", Y(0, wz0)[1] + 17, fmt(M.flange))
    d.dim_linear(Y(xi, -h), Y(aw, -h), "x", Y(0, wz0)[1] + 5, fmt(C.frame_w), outside=True)
    d.leader_note(Y((g["g0"] + g["g1"]) / 2, h - M.groove_d / 2), (Y(g["g1"], 0)[0] + 6, Y(0, wz1)[1] - 5),
                  f"LAND {fmt(M.land)}, GROOVE {fmt(M.groove_w)} × {fmt(M.groove_d)}", 2.3)
    xw = xi - C.rib_pitch / 4 - 0.3                       # a wall crossing the mid-plane, inside the window
    while xw - C.rib_pitch / 2 > wx0 + 4:
        xw -= C.rib_pitch / 2
    d.leader_note(Y(xw, 0.0), (Y(wx0, 0)[0] - 3, Y(0, wz0)[1] + 9), f"WALL {fmt(C.rib_t)} (CARBON)", 2.3)
    d.text(Y((aw + xb_[0]) / 2 if xb_ else aw + 6, h + 2.0), "LID", 2.2, fill=GREY)
    d.text(Y((aw + xb_[0]) / 2 if xb_ else aw + 6, -h - 2.8), "TRAY", 2.2, fill=GREY)
    view_label(d, (Y(wx0, 0)[0] + Y(xr, 0)[0]) / 2, Y(0, wz0)[1] + 27, "DETAIL Y",
               "SCALE 2:1 · TEETH INTERLOCK; THE GAPS ARE THE WALLS AND THE FRAME")

    # ---- hardware list
    tx, ty = 28.0, 214.0
    widths = (9.0, 74.0, 10.0)
    rows = [("ITEM", "PART", "QTY"),
            ("1", f"Tray, {sp.key}_mould_bottom.stl", "1"),
            ("2", f"Lid, {sp.key}_mould_top.stl", "1"),
            ("3", f"Hex bolt M6 × {BOLT['length']:.0f}, 2 washers, nut", str(len(lay.bolts))),
            ("4", "Dowel pin Ø6 × 16, steel (ISO 2338)", str(len(lay.dowels))),
            ("5", "Ejector pin Ø4 × 40 (or a drill shank)", str(len(lay.ejectors))),
            ("6", "Release wax + PVA; flat platens + clamps or a press", "a/r")]
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
    notes_block(d, 228.0, 158.0, mould_notes(o, report), size=2.15, lead=3.05)
    title_block(d, 225.0, 236.0, sp, f"RIB SUPPORT MOULD  ·  TRAY + LID, TEETH INTERLOCK  ·  {fmt(x1 - x0, 1)} × "
                f"{fmt(y1 - y0, 1)} mm", "1:3, 1:2, 2:1", f"4 / {SHEETS}", "A3",
                title=f"RIB SUPPORT MOULD – {sp.name}", material="PLA / PETG (NOTE 2)")
    return d
