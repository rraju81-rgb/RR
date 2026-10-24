"""Construction drawings (REV D): the printed rib support (core) of each paddle and the shared printed grip.

  core_sheet(o)  - PB-xx-001 sheet 3: rib support plan view 1:2, section C-C across the wave 2:1,
                   section D-D along a land through the flute run-out 2:1, print notes.
  grip_sheet()   - PB-GR-002: handle in the printed grip 1:1, sections E-E / G-G across the grip and F-F through
                   the M3 screw and insert 2:1, fit-test coupon, bill of materials, notes.
"""
from __future__ import annotations

import math

import numpy as np
from shapely.geometry import LineString, Polygon, box

from . import wave
from .geometry import CONSTRUCTION as C
from .geometry import GRIP, Outline, PaddleSpec
from .sheets import (GREY, SHEETS, cell, core_inner, fill, grip_front, hatches, notes_block, polygon_path,
                     title_block)
from .svgkit import Doc, View, f, fmt, frame_iso


def _segments(geom):
    """Line segments (lists of points) of a shapely intersection result."""
    if geom.is_empty:
        return []
    if geom.geom_type == "LineString":
        return [list(geom.coords)]
    if geom.geom_type in ("MultiLineString", "GeometryCollection"):
        return [list(g.coords) for g in geom.geoms if g.geom_type == "LineString"]
    return []


def break_line(d: Doc, p: tuple, q: tuple, amp: float = 1.6) -> None:
    """Freehand-style break line (ISO 128 type 01.1 zig-zag) from p to q."""
    n = 4
    pts = []
    for i in range(2 * n + 1):
        t = i / (2 * n)
        x, y = p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t
        if 0 < i < 2 * n:
            dx, dy = q[0] - p[0], q[1] - p[1]
            L = math.hypot(dx, dy)
            s = amp if i % 2 else -amp
            x, y = x - dy / L * s, y + dx / L * s
        pts.append((x, y))
    d.poly(pts, "thin")


def phantom_rect(d: Doc, p: tuple, q: tuple) -> None:
    d.poly([p, (q[0], p[1]), q, (p[0], q[1])], "phan", closed=True)


def view_label(d: Doc, x: float, y: float, title: str, sub: str = "") -> None:
    d.text((x, y), title, 3.5, weight="bold")
    if sub:
        d.text((x, y + 4.3), sub, 2.6)


# --------------------------------------------------------------------------- sheet 3: rib core
def core_notes(o: Outline, mass: dict | None) -> list[str]:
    sp = o.spec
    m = f"MASS {mass['parts']['rib_core']['mass_g']:.0f} g. " if mass else ""
    return [
        "MATERIAL: PA-CF (CARBON-FIBRE-FILLED NYLON), E ≈ 4 GPa, ρ 1.18 g/cm³. DRY THE FILAMENT BEFORE PRINTING.",
        f"PRINT FLAT, 100 % SOLID: WALL {fmt(C.rib_t)} = 4 PERIMETERS (0.4 NOZZLE), 0.2 LAYERS. NO SUPPORTS (45° RUN-OUTS).",
        f"THICKNESS {fmt(C.core_t)} ±0.1. BOTH FACES ARE BOND SURFACES, FLAT WITHIN 0.1.",
        f"WAVE RIB λ{fmt(C.rib_pitch)}, WALL {fmt(C.rib_t)}, CENTRE-LINE AMPLITUDE {fmt(C.rib_amp)}; CRESTS CUT FLAT = "
        f"LANDS {wave.land_width():.2f} ON BOTH FACES.",
        f"FRAME {fmt(C.frame_w)}, CLOSED. SOLID TO y = {fmt(C.solid_to)}; EACH FLUTE STARTS WITH A 45° RUN-OUT, "
        f"{fmt(C.runout_len)} LONG (D–D).",
        f"M3 HEAT-SET INSERT BORE Ø{fmt(C.insert_d)} × {fmt(C.insert_depth)} + Ø{fmt(C.screw_relief_d)} × "
        f"{fmt(C.screw_relief_depth)} IN THE BUTT FACE (GRIP SCREW) – SEE PB-GR-002.",
        "BONDING: ABRADE (P120) AND DEGREASE BOTH FACES; THE SHEETS ARE LAMINATED ON IN THE MOULD (SHEET 4).",
        f"PRINT FILE output/rib_support/{sp.key}_rib_support.stl: ONE PIECE, FLAT, BED ≥ "
        f"{fmt(sp.length - sp.cap_length + 6)} × {fmt(sp.width + 6)}.\nIT DROPS INTO THE MOULD POCKET "
        f"(+0.2 CLEARANCE); PLUG THE INSERT BORE BEFORE MOULDING.",
        f"{m}y FROM THE GRIP BUTT FACE (y = 0); THE RIB SUPPORT STARTS AT y = {fmt(sp.cap_length)}.",
    ]


def core_sheet(o: Outline, mass: dict | None = None) -> Doc:
    sp = o.spec
    d = Doc(420, 297, f"{sp.drawing_no} {sp.name} paddle - rib core")
    H = hatches(d)
    frame_iso(d)
    a, L, hc = sp.width / 2, sp.length, C.core_t / 2
    y_open = C.solid_to + C.runout_len           # the flutes open at the face sheets from here
    inner = core_inner(o)

    # ---- plan view (top face of the core), 1:2
    S = 0.5
    cx, tip_y = 117.0, 40.0
    butt_y = tip_y + L * S
    pv = View(d, (cx, butt_y), S)
    P = pv.P
    d.path(pv.outline_path(o), "vis")
    clip = box(-400, y_open, 400, 1000)
    for seg in _segments(inner.exterior.intersection(clip)):
        d.poly([P(q) for q in seg], "vis")
    lands = wave.land_intervals(a + C.rib_pitch, +1)
    edges = sorted(x for iv in lands for x in iv)
    for x in edges:                               # land edges, visible from y_open to the frame
        for seg in _segments(LineString([(x, y_open), (x, 1000)]).intersection(inner)):
            d.poly([P(q) for q in seg], "vis")
    gaps = [(-400, lands[0][0])] + [(lands[i][1], lands[i + 1][0]) for i in range(len(lands) - 1)] + \
           [(lands[-1][1], 400)]
    for x0, x1 in gaps:                           # top edge of each flute run-out
        for seg in _segments(LineString([(x0, y_open), (x1, y_open)]).intersection(inner)):
            d.poly([P(q) for q in seg], "vis")
    hc_ = C.core_t / 2                            # lower edge of each top-flute run-out (meets the flute floor)
    for ua, ub in wave.channel_bounds(a + C.rib_pitch, +1):
        pts = []
        for i in range(61):
            xs_, zs_ = wave.surface_point(ua + (ub - ua) * i / 60, +1)
            pts.append((xs_, C.solid_to + C.runout_len * (zs_ + hc_) / (2 * hc_)))
        for seg in _segments(LineString(pts).intersection(inner)):
            d.poly([P(q) for q in seg], "vis")
    y0 = sp.cap_length                            # insert bore + clearance (hidden)
    r1, r2 = C.insert_d / 2, C.screw_relief_d / 2
    d.poly([P((-r1, y0)), P((-r1, y0 + C.insert_depth)), P((-r2, y0 + C.insert_depth)),
            P((-r2, y0 + C.screw_relief_depth)), P((r2, y0 + C.screw_relief_depth)), P((r2, y0 + C.insert_depth)),
            P((r1, y0 + C.insert_depth)), P((r1, y0))], "hid")
    pv.line((0, -6), (0, L + 9), "ctr")
    # dimensions
    yside = o.pts["side_hi"][1]
    d.dim_linear(P((-a, yside)), P((a, yside)), "x", tip_y - 11, fmt(sp.width))
    xl = cx - a * S - 12
    xl2 = cx - a * S - 23
    hb = sp.handle_width / 2
    d.dim_linear(P((-hb, y0)), P((-o.half_width_at(C.solid_to), C.solid_to)), "y", xl, fmt(C.solid_to - y0))
    d.dim_linear(P((-hb, y0)), P((0, L)), "y", xl2, fmt(L - y0))
    d.leader_note(P((a - C.frame_w / 2, 300)), (P((a, 0))[0] + 10, P((0, 312))[1]), f"FRAME {fmt(C.frame_w)}", 3.0)
    xr_land = sum(next(iv for iv in lands if iv[0] > C.rib_pitch / 2)) / 2
    d.leader_note(P((xr_land, 262)), (P((a, 0))[0] + 10, P((0, 256))[1]),
                  f"LANDS {wave.land_width():.2f} @ {fmt(C.rib_pitch)}", 3.0, dot=True, arrow=False)
    d.leader_note(P((0.0, y0 + 8)), (P((0, 0))[0] + 22, P((0, y0 + 26))[1]), "M3 INSERT BORE", 3.0)
    # cutting planes: C-C across the blade, D-D along the centre land
    pv.section_line(280.0, -a - 12, a + 12, "C")
    ya_d, yb_d = 128.0, 196.0
    pa, pb = P((0, yb_d)), P((0, ya_d))
    for p, s in ((pa, 1), (pb, -1)):
        d.line(p, (p[0], p[1] + s * 6), "cut")
        d.line((p[0], p[1] + s * 3), (p[0] - 6, p[1] + s * 3), "thin")
        d.arrow((p[0] - 7.5, p[1] + s * 3), (-1, 0), 3.0, 1.4)
        d.text((p[0] + 1.2, p[1] - (1.5 if s > 0 else -4.5)), "D", 5.0, anchor="start", weight="bold")
    view_label(d, cx, 259, "PLAN VIEW (TOP FACE)", "SCALE 1:2 · BOTTOM LANDS OFFSET ½ PITCH")

    # ---- section C-C (partial, at y = 280, right-hand edge), 2:1
    S2 = 2.0
    aw = o.half_width_at(280.0)
    span = 42.0
    while sum(1 for c in range(0, 20) if aw - span + 3 < c * C.rib_pitch < aw - C.frame_w - 3) < 2:
        span += 3.0
    xc, zc = 397.0 - aw * S2, 60.0

    def Cc(x: float, z: float):
        return (xc + x * S2, zc - z * S2)

    xs = aw - span
    xi = aw - C.frame_w
    for z0 in (hc, -hc - C.face_t):
        phantom_rect(d, Cc(xs, z0 + C.face_t), Cc(aw, z0))
    p, q = Cc(xi, hc), Cc(aw, -hc)
    d.rect(p[0], p[1], q[0] - p[0], q[1] - p[1], "vis", extra=fill(H["core"]))
    d.poly([Cc(x, z) for x, z in wave.wall_polygon(xs, xi)], "vis", closed=True, extra=fill(H["core"]))
    break_line(d, Cc(xs, hc + C.face_t + 1), Cc(xs, -hc - C.face_t - 1))
    k = 2 * math.pi / C.rib_pitch
    d.poly([Cc(x, C.rib_amp * math.cos(k * x)) for x in [xs + i * (xi - xs) / 200 for i in range(201)]], "ctr")
    crests = [c * C.rib_pitch for c in range(int(xs // C.rib_pitch) - 1, int(xi // C.rib_pitch) + 2)
              if xs + 3 < c * C.rib_pitch < xi - 3]
    c1, c2 = crests[-2:] if len(crests) > 1 else (crests[0] - C.rib_pitch, crests[0])
    ztop = hc + C.face_t
    d.dim_linear(Cc(c1, ztop), Cc(c2, ztop), "x", zc - ztop * S2 - 6, fmt(C.rib_pitch))
    lw = wave.land_width()
    d.dim_linear(Cc(c1 - lw / 2, hc), Cc(c1 + lw / 2, hc), "x", zc - ztop * S2 - 13, f"{lw:.2f}", outside=True)
    d.dim_linear(Cc(xi, ztop), Cc(aw, ztop), "x", zc - ztop * S2 - 6, fmt(C.frame_w))
    d.dim_linear(Cc(aw, hc), Cc(aw, -hc), "y", xc + aw * S2 + 6, fmt(C.core_t))
    # wall thickness and amplitude callouts
    xm = c2 - C.rib_pitch / 4                         # wall crossing the mid-plane
    zb = zc + (hc + C.face_t) * S2                    # bottom of the phantom face sheet
    xk = Cc(xs, 0)[0] + 4
    d.leader_note(Cc(xm, 0.0), (xk, zb + 6), f"WALL {fmt(C.rib_t)} (NORMAL TO THE CENTRE LINE)", 2.6)
    d.leader_note(Cc(c1, hc - wave.under_land_wall() / 2), (xk, zb + 12),
                  f"{wave.under_land_wall():.1f} UNDER EACH LAND", 2.6)
    xa_ = c2 - C.rib_pitch / 2 + 2.0
    d.leader_note(Cc(xa_, C.rib_amp * math.cos(k * xa_)), (xk, zb + 18),
                  f"CENTRE LINE z = {fmt(C.rib_amp)}·cos(2πx/{fmt(C.rib_pitch)})", 2.6, arrow=False, dot=True)
    view_label(d, xc + (xs + aw) / 2 * S2, zb + 25, "SECTION C–C (PART)", "SCALE 2:1 · FACE SHEETS SHOWN PHANTOM")

    # ---- section D-D (along the centre land x = 0, through the flute run-out), 2:1
    yd0, yd1 = 134.0, 184.0
    xd, zd = 252.0 - yd0 * S2, 140.0

    def D(y: float, z: float):
        return (xd + y * S2, zd - z * S2)

    for z0 in (hc, -hc - C.face_t):
        phantom_rect(d, D(yd0, z0 + C.face_t), D(yd1, z0))
    z_top = C.rib_amp - C.rib_t / 2                   # lower surface of the wall under the land (x = 0)
    y_foot = C.solid_to + C.runout_len                # run-out meets the bottom face here
    y_head = C.solid_to + (hc - z_top) * C.runout_len / C.core_t
    solid = [D(yd0, -hc), D(y_foot, -hc), D(y_head, z_top), D(yd1, z_top), D(yd1, hc), D(yd0, hc)]
    d.poly(solid, "vis", closed=True, extra=fill(H["core"]))
    d.line(D(y_head, z_top), D(C.solid_to, hc), "hid")
    for yy in (yd0, yd1):
        break_line(d, D(yy, hc + C.face_t + 1), D(yy, -hc - C.face_t - 1))
    d.dim_linear(D(C.solid_to, hc), D(y_foot, -hc), "x", zd + (hc + C.face_t) * S2 + 7, fmt(C.runout_len))
    d.line(D(C.solid_to, hc), D(C.solid_to, -hc - C.face_t - 1), "thin")
    v = View(d, D(y_foot, -hc), S2)
    d.path(f"M{f(D(y_foot, -hc)[0] - 9)},{f(D(y_foot, -hc)[1])} "
           f"A9,9 0 0 1 {f(D(y_foot, -hc)[0] - 9 * math.cos(math.pi / 4))},{f(D(y_foot, -hc)[1] - 9 * math.sin(math.pi / 4))}",
           "thin")
    del v
    d.text((D(y_foot, -hc)[0] - 13.5, D(y_foot, -hc)[1] - 2.0), "45°", 3.0)
    d.dim_linear(D(yd1, z_top), D(yd1, hc), "y", D(yd1, 0)[0] + 7, f"{wave.under_land_wall():.1f}", outside=True)
    d.text(D(170, -1.5), "BOTTOM FLUTE", 2.6, fill=GREY)
    d.text((D(yd0, 0)[0] + 18, D(yd0, 0)[1] + 1), "SOLID CORE", 2.6, fill=GREY)
    view_label(d, (D(yd0, 0)[0] + D(yd1, 0)[0]) / 2, zd + (hc + C.face_t) * S2 + 15, "SECTION D–D (PART)",
               f"SCALE 2:1 · ON THE CENTRE LAND (x = 0), RUN-OUT FROM y = {fmt(C.solid_to)}; TOP FLUTES MIRROR IT")

    # ---- notes + title block
    notes_block(d, 228.0, 192.0, core_notes(o, mass), size=2.3, lead=3.4)
    title_block(d, 225.0, 236.0, sp, f"RIB SUPPORT (CORE)  ·  3D-PRINTED PA-CF  ·  {fmt(L - sp.cap_length)} × "
                f"{fmt(sp.width)} × {fmt(C.core_t)} mm", "1:2, 2:1", f"3 / {SHEETS}", "A3",
                title=f"RIB SUPPORT – {sp.name}", material="PA-CF (NOTE 1)")
    return d


# --------------------------------------------------------------------------- PB-GR-002: printed grip interface
GRIP_NO = "PB-GR-002"


def grip_notes(sp: PaddleSpec, g: dict, masses: dict | None) -> list[str]:
    tot = " / ".join(f"{masses[k]['mass_g']:.0f}" for k in ("elongated", "hybrid")) if masses else "–"
    return [
        f"GRIP (3): ANY OF THE TEN REV-8 PRINTED GRIPS (pickleball_grips) - SAME INTERFACE, DIFFERENT SURFACE; DRAWN: "
        f"{g['name']}.\nPLA 60–65 g ({g['mass_g']:.1f} g DRAWN). PRINT UPRIGHT, BUTT DOWN, 100 % INFILL, NO SUPPORTS.",
        f"REV-8 SLOT {fmt(GRIP.slot_w)} × {fmt(GRIP.slot_t)} × {fmt(GRIP.slot_depth)} DEEP, {fmt(GRIP.lead_in)} LEAD-IN; "
        f"HANDLE {fmt(sp.handle_width)} × {fmt(sp.thickness)} ({fmt(C.face_t)} / {fmt(C.core_t)} / {fmt(C.face_t)}, "
        f"MOULDED) = {fmt(GRIP.slot_t - sp.thickness)} LOOSE.\nREGENERATE THE GRIPS WITH SLOT_T = {fmt(sp.thickness)} "
        f"(pickleball_grips/scripts/grip_core.py) AND THE COUPON AT {fmt(sp.thickness - 0.4)} / {fmt(sp.thickness)} / "
        f"{fmt(sp.thickness + 0.4)}.",
        f"END WALLS SLIT OVER THE TOP {fmt(GRIP.slit_depth)} (y {fmt(GRIP.length - GRIP.slit_depth)}–{fmt(GRIP.length)}) "
        f"SO THE THROAT FLARE (FROM y = {fmt(sp.handle_length)}) PASSES;\nTHE GRIP SEATS ON THE BODY BUTT AT "
        f"y = {fmt(sp.cap_length)} (= GRIP BASE {fmt(GRIP.base)}).",
        f"INSERT (5): HEAT-SET M3 × {fmt(C.insert_len)} INTO THE Ø{fmt(C.insert_d)} BORE, FLUSH WITH THE CORE BUTT, "
        "BEFORE MOULDING; KEEP A SCREW IN IT SO NO RESIN GETS IN.",
        f"SCREW (4): DIN 7984 M3 × {fmt(GRIP.screw_len)} LOW-HEAD (M3 × 16 ALSO FITS), LOW-STRENGTH THREADLOCKER, "
        f"HAND-TIGHT (≈0.5 N·m)\nSO THE PLA BASE DOES NOT CRACK; {fmt(GRIP.base - GRIP.cbore_depth)} OF FLOOR UNDER "
        "THE HEAD.",
        f"OVERALL LENGTH {fmt(sp.length)} INCL. THE {fmt(GRIP.base)} GRIP BASE; HANDLE {fmt(sp.handle_length)} FROM THE "
        f"BUTT TO THE THROAT. MASS WITH GRIP {tot} g (EL / HY).",
        "SAME GRIP ON PB-EL-001 AND PB-HY-001. ALL DIMENSIONS IN mm.",
    ]


def grip_sheet(sp: PaddleSpec, masses: dict | None = None) -> Doc:
    """PB-GR-002: the printed grip on the paddle handle (shared by both paddles).

    masses: the mass_properties.json content (optional, for the BOM mass column)."""
    from shapely.geometry import box as sbox

    from .geometry import build
    from .grip import drawing_data, fit_test_section
    g = drawing_data()
    d = Doc(420, 297, f"{GRIP_NO} printed grip - paddle interface")
    H = hatches(d)
    frame_iso(d)
    h, T, hc, y0 = sp.handle_width / 2, sp.thickness / 2, C.core_t / 2, sp.cap_length
    o = build(sp)
    gw = float(g["face"][:, 0].max())
    gy = float(g["face"][int(np.argmax(g["face"][:, 0])), 1])

    # ---- face view of the handle in the grip, 1:1
    cx, butt_y = 80.0, 250.0
    fv = View(d, (cx, butt_y), 1.0)
    P = fv.P
    y_cut = 152.0
    for seg in _segments(Polygon(o.polyline(0.3)).exterior.intersection(sbox(-200, GRIP.length - 0.01, 200, y_cut))):
        d.poly([P(q) for q in seg], "vis")
    half_cut = o.half_width_at(y_cut)
    break_line(d, P((-half_cut - 4, y_cut)), P((half_cut + 4, y_cut)), 1.2)
    grip_front(d, fv, o)
    fv.line((0, -6), (0, y_cut + 4), "ctr")
    fv.line((-gw - 12, sp.handle_length), (gw + 4, sp.handle_length), "phan")
    d.text((P((-gw - 6.5, 0))[0], P((0, sp.handle_length))[1] - 1.0), "THROAT", 2.2, fill=GREY)
    xl, xl2 = cx - gw - 14, cx - gw - 23
    d.dim_linear(P((-gw, 0)), P((-gw, GRIP.base)), "y", xl, fmt(GRIP.base), outside=True)
    d.dim_linear(P((-gw, GRIP.base)), P((-gw, GRIP.length)), "y", xl, fmt(GRIP.slot_depth))
    d.dim_linear(P((-gw, 0)), P((-gw, GRIP.length)), "y", xl2, fmt(GRIP.length))
    d.dim_linear(P((gw, GRIP.length - GRIP.slit_depth)), P((gw, GRIP.length)), "y", cx + gw + 14, fmt(GRIP.slit_depth))
    d.text((cx + gw + 17.5, P((0, GRIP.length - GRIP.slit_depth / 2))[1]), "SLITS", 2.4, rot=-90, fill=GREY)
    d.dim_linear(P((-gw, gy)), P((gw, gy)), "x", butt_y + 13, f"{2 * gw:.1f}")
    fv.section_line(70.0, -gw - 4, gw + 4, "E")
    fv.section_line(120.0, -gw - 4, gw + 4, "G", up=True)        # looking up keeps the arrows clear of the 20 dim
    for p, s in ((P((0, 46)), 1), (P((0, -6.5)), -1)):  # plane x = 0, looking towards -x
        d.line(p, (p[0], p[1] + s * 4), "cut")
        tail = (p[0], p[1] + s * 2)
        d.line(tail, (tail[0] - 6, tail[1]), "thin")
        d.arrow((tail[0] - 7.5, tail[1]), (-1, 0), 3.0, 1.4)
        d.text((tail[0] - 9.5, tail[1] + 1.8), "F", 5.0, anchor="end", weight="bold")
    _balloon(d, P((gw - 1.5, 92)), (P((gw, 92))[0] + 14, P((0, 98))[1]), 3)
    _balloon(d, P((h - 4, y_cut - 6)), (P((gw, 0))[0] + 10.7, P((0, 141.5))[1]), 1)
    view_label(d, cx, 270, "HANDLE IN THE GRIP (FACE VIEW)", f"SCALE 1:1 · DRAWN: {g['name']}")

    S2 = 2.0
    # ---- section E-E across the grip at y = 70, 2:1 (sealed hollow core of the grip shown white)
    xe, ze = 163.0, 64.0

    def E(x: float, z: float):
        return (xe + x * S2, ze - z * S2)

    d.path(polygon_path(g["sec_e"], E), "vis", extra=f'style="fill:{H["grip"]}" fill-rule="evenodd"')
    for zb, zt, key in ((hc, T, "cf"), (-hc, hc, "core"), (-T, -hc, "cf")):
        p, q = E(-h, zt), E(h, zb)
        d.rect(p[0], p[1], q[0] - p[0], q[1] - p[1], "vis", extra=fill(H[key]))
    ex0, ez0, ex1, ez1 = g["sec_e"].bounds
    d.dim_linear(E(-h, T), E(h, T), "x", ze - ez1 * S2 - 5, fmt(sp.handle_width))
    d.dim_linear(E(ex0, ez1), E(ex1, ez1), "x", ze - ez1 * S2 - 11, f"{ex1 - ex0:.1f} MAX")
    d.dim_linear(E(h, T), E(h, -T), "y", xe + ex1 * S2 + 5, fmt(sp.thickness))
    d.dim_linear(E(ex1, ez1), E(ex1, ez0), "y", xe + ex1 * S2 + 11, f"{ez1 - ez0:.1f} MAX")
    d.leader_note(E(-h - 0.05, -4.0), (E(ex0, 0)[0] - 5, ze + 14),
                  f"SLOT {fmt(GRIP.slot_w)} × {fmt(GRIP.slot_t)}", 2.6)
    cav = max((Polygon(r) for r in g["sec_e"].interiors), key=lambda q: q.centroid.y)     # topmost cavity
    d.leader_note(E(cav.centroid.x - 4.0, cav.centroid.y), (E(ex0, 0)[0] - 5, ze - 12), "SEALED HOLLOW CORE", 2.4,
                  dot=True, arrow=False)
    d.line((xe + ex0 * S2 - 3, ze), (xe + ex1 * S2 + 2, ze), "ctr")
    view_label(d, xe, ze + ez1 * S2 + 15, "SECTION E–E", "SCALE 2:1")

    # ---- section G-G through the head at y = 125: end walls slit away, two plates remain, 2:1
    xg, zg = 163.0, 156.0

    def Gp(x: float, z: float):
        return (xg + x * S2, zg - z * S2)

    d.path(polygon_path(g["sec_g"], Gp), "vis", extra=f'style="fill:{H["grip"]}" fill-rule="evenodd"')
    for zb, zt, key in ((hc, T, "cf"), (-hc, hc, "core"), (-T, -hc, "cf")):
        p, q = Gp(-h, zt), Gp(h, zb)
        d.rect(p[0], p[1], q[0] - p[0], q[1] - p[1], "vis", extra=fill(H[key]))
    gx0, gz0, gx1, gz1 = g["sec_g"].bounds
    ts = GRIP.slot_t / 2                              # slot face (the handle may be thinner: see note 2)
    plate = min(gz1 - ts, -ts - gz0)
    d.dim_linear(Gp(gx0, gz1), Gp(gx1, gz1), "x", zg - gz1 * S2 - 5, f"{gx1 - gx0:.1f}")
    d.dim_linear(Gp(gx1, gz1), Gp(gx1, ts), "y", xg + gx1 * S2 + 5, f"{plate:.1f}", outside=True)
    d.leader_note(Gp(gx1 - 0.6, 0.0), (Gp(gx1, 0)[0] + 9, zg + gz1 * S2 + 6), "OPEN SLIT", 2.4)
    d.line((xg + gx0 * S2 - 3, zg), (xg + gx1 * S2 + 2, zg), "ctr")
    view_label(d, xg, zg + gz1 * S2 + 16, "SECTION G–G", "SCALE 2:1 · HEAD, IN THE SLIT ZONE (y = 120)")

    # ---- fit-test coupon, plan section, 1:1
    cpn = fit_test_section()
    xc, yc = 163.0, 228.0

    def K(x: float, y: float):
        return (xc + y, yc + x)                       # coupon turned 90 deg: its long axis across the sheet

    d.path(polygon_path(cpn, K), "vis", extra=f'style="fill:{H["grip"]}" fill-rule="evenodd"')
    for hole, label in zip(sorted(cpn.interiors, key=lambda r: Polygon(r).bounds[1]), ("15.6", "16.0", "16.4")):
        b0, b1, b2, b3 = Polygon(hole).bounds
        d.text((xc + (b1 + b3) / 2, yc + 1.0), label, 2.6, weight="bold")
    cb = cpn.bounds
    view_label(d, xc, yc + cb[2] + 10, "FIT-TEST COUPON (fit_test_slot.stl)",
               "SCALE 1:1 · 8 THK · REV-8 SLOTS 15.6 / 16.0 / 16.4 × 30.2")

    # ---- section F-F through the screw, butt end (y = 0 .. 40), 2:1
    yf1 = 40.0
    xf, zf = 268.0, 60.0

    def F(y: float, z: float):
        return (xf + y * S2, zf - z * S2)

    def box_(y_a, y_b, z_a, z_b, style, cls="vis"):
        p, q = F(y_a, max(z_a, z_b)), F(y_b, min(z_a, z_b))
        d.rect(p[0], p[1], q[0] - p[0], q[1] - p[1], cls, extra=style)

    longf = g["long"].intersection(sbox(-1, -40, yf1, 40))
    d.path(polygon_path(longf, F), "vis", extra=f'style="fill:{H["grip"]}" fill-rule="evenodd"')
    for zb, zt in ((hc, T), (-T, -hc)):
        box_(y0, yf1, zb, zt, fill(H["cf"]))
    r1, r2 = C.insert_d / 2, C.screw_relief_d / 2
    yi, yr = y0 + C.insert_depth, y0 + C.screw_relief_depth
    core = [F(y0, r1), F(yi, r1), F(yi, r2), F(yr, r2), F(yr, -r2), F(yi, -r2), F(yi, -r1), F(y0, -r1),
            F(y0, -hc), F(yf1, -hc), F(yf1, hc), F(y0, hc)]
    d.poly(core, "vis", closed=True, extra=fill(H["core"]))
    ins_i = 1.25
    for s in (1, -1):
        box_(y0, y0 + C.insert_len, s * ins_i, s * r1, fill(H["metal"]))
    yb = GRIP.cbore_depth
    hr = GRIP.screw_head_d / 2
    head = [F(yb - GRIP.screw_head_h, hr - 0.4), F(yb - GRIP.screw_head_h, -hr + 0.4), F(yb - GRIP.screw_head_h + 0.4, -hr),
            F(yb, -hr), F(yb, hr), F(yb - GRIP.screw_head_h + 0.4, hr)]
    d.poly(head, "vis", closed=True, extra='style="fill:#fff"')
    box_(yb, yb + GRIP.screw_len, -1.5, 1.5, 'style="fill:#fff"')
    for s in (1, -1):                                 # thread root lines over the engaged length
        d.line(F(y0 + 0.3, s * 1.23), F(yb + GRIP.screw_len - 0.4, s * 1.23), "thin")
    break_line(d, F(yf1, 19.5), F(yf1, -19.5))
    d.line(F(-3, 0), F(yf1 + 3, 0), "ctr")
    lz0, lz1 = longf.bounds[1], longf.bounds[3]
    d.dim_linear(F(0, lz1), F(GRIP.base, lz1), "x", zf - lz1 * S2 - 6, fmt(GRIP.base), outside=True)
    d.dim_linear(F(0, lz0), F(0, lz1), "y", xf - 9, f"{lz1 - lz0:.1f}")
    d.leader_note(F(GRIP.cbore_depth / 2, -GRIP.cbore_d / 2), (F(0, 0)[0] - 4, zf + 19.5 * S2 + 8),
                  f"⌴Ø{fmt(GRIP.cbore_d)} ↧{fmt(GRIP.cbore_depth)}, Ø{fmt(GRIP.hole_d)} THRU", 2.6)
    d.leader_note(F(y0 + 3.5, -r1), (F(y0, 0)[0] + 16, zf + 19.5 * S2 + 8),
                  f"BORE Ø{fmt(C.insert_d)} × {fmt(C.insert_depth)}, Ø{fmt(C.screw_relief_d)} × "
                  f"{fmt(C.screw_relief_depth)}", 2.6)
    d.leader_note(F(y0 + 3.0, ins_i + 0.35), (F(16, 0)[0] + 16, zf - lz1 * S2 - 4), f"INSERT M3 × {fmt(C.insert_len)} (5)", 2.6)
    d.leader_note(F(yb + 9, 0.4), (F(yf1, 0)[0] + 8, zf - 3), f"DIN 7984 M3 × {fmt(GRIP.screw_len)} (4)", 2.6,
                  dot=True, arrow=False)
    view_label(d, F(yf1 / 2, 0)[0], zf + 19.5 * S2 + 17, "SECTION F–F (BUTT END)", "SCALE 2:1")

    # ---- bill of materials
    bx, by = 228.0, 124.0
    cols = (("ITEM", 11), ("PART", 34), ("MATERIAL / SPECIFICATION", 86), ("QTY", 10), ("MASS g EL / HY", 31))
    rh = 5.4
    xx = bx
    for cap, w in cols:
        cell(d, xx, by, w, rh + 0.6, "", cap, 2.4, weight="bold")
        xx += w

    def mass(part: str) -> str:
        if not masses:
            return "–"
        v = [masses[k]["parts"][part]["mass_g"] for k in ("elongated", "hybrid")]
        if abs(v[0] - v[1]) < 0.05:
            return f"{v[0]:.1f}" if v[0] < 10 else f"{v[0]:.0f}"
        return " / ".join(f"{x:.0f}" for x in v)
    rows = [("1", "Face sheet", f"Woven carbon/epoxy {fmt(C.face_t)} thk, cut to the profile DXF", "2",
             mass("face_sheet_top")),
            ("2", "Rib support", "PA-CF printed in one piece – sheet 3 of PB-EL-001 / PB-HY-001", "1",
             mass("rib_core")),
            ("3", "Grip", f"PLA printed, rev 8 (drawn {g['name']}), slot: note 2", "1", mass("grip")),
            ("4", "Screw", f"DIN 7984 M3 × {fmt(GRIP.screw_len)} low-head cap screw, A2 stainless", "1",
             mass("screw_M3x12_DIN7984")),
            ("5", "Threaded insert", f"M3 heat-set, brass, {fmt(C.insert_len)} long, in a Ø{fmt(C.insert_d)} bore",
             "1", mass("insert_M3_heatset")),
            ("6", "Adhesive", "Laminating epoxy, sheets onto the rib support in the mould", "a/r", "–")]
    for i, r in enumerate(rows):
        yy = by + rh + 0.6 + i * rh
        xx = bx
        for k, (cap, w) in enumerate(cols):
            cell(d, xx, yy, w, rh, "", r[k], 2.35, anchor="start" if k in (1, 2) else "middle")
            xx += w
    if masses:
        yy = by + rh + 0.6 + len(rows) * rh
        tot = " / ".join(f"{masses[k]['mass_g']:.0f}" for k in ("elongated", "hybrid"))
        cell(d, bx, yy, sum(w for _, w in cols[:4]), rh, "", "COMPLETE PADDLE WITH GRIP (3D MODEL)", 2.35,
             weight="bold", anchor="start")
        cell(d, bx + sum(w for _, w in cols[:4]), yy, cols[4][1], rh, "", tot, 2.35, weight="bold")

    # ---- notes + title block
    notes_block(d, 228.0, 172.0, grip_notes(sp, g, masses), size=2.25, lead=3.3)
    title_block(d, 225.0, 236.0, None, f"PRINTED GRIP {fmt(GRIP.length)} LONG, SLOT {fmt(GRIP.slot_w)} × "
                f"{fmt(GRIP.slot_t)}  ·  M3 LOW-HEAD SCREW + HEAT-SET INSERT  ·  BOTH PADDLES",
                "1:1, 2:1", "1 / 1", "A3", title="PRINTED GRIP – PADDLE INTERFACE", drawing_no=GRIP_NO,
                material="SEE BOM")
    return d


def _balloon(d: Doc, tip: tuple, centre: tuple, n: int, r: float = 3.2) -> None:
    """Item balloon (ISO 6433) with a leader ending in a dot on the part."""
    dx, dy = tip[0] - centre[0], tip[1] - centre[1]
    L = math.hypot(dx, dy) or 1.0
    d.line(tip, (centre[0] + dx / L * r, centre[1] + dy / L * r))
    d.circle(tip, 0.55, "arrow")
    d.circle(centre, r, "thin", extra='style="fill:#fff"')
    d.text((centre[0], centre[1] + 1.1), str(n), 3.0)
