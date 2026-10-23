"""Construction drawings (REV B): the printed rib core of each paddle and the shared grip assembly.

  core_sheet(o)  - PB-xx-001 sheet 3: core plan view 1:2, section C-C across the wave 2:1,
                   section D-D along a land through the flute run-out 2:1, print / bond notes.
  grip_sheet()   - PB-GR-001: handle face view 1:1, section E-E across the grip 2:1,
                   section F-F through the butt-cap screw 2:1, bill of materials, grip notes.
"""
from __future__ import annotations

import math

from shapely.geometry import LineString, box

from . import wave
from .geometry import CONSTRUCTION as C
from .geometry import Outline, PaddleSpec, grip_dims
from .sheets import (GREY, SHEETS, cell, core_inner, fill, grip_front, hatches, notes_block, rrect_path,
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
        f"M4 INSERT BORE Ø{fmt(C.insert_d)} × {fmt(C.insert_depth)} + Ø{fmt(C.screw_relief_d)} × "
        f"{fmt(C.screw_relief_depth)} IN THE BUTT FACE – SEE PB-GR-001.",
        "BONDING: ABRADE (P120), DEGREASE, STRUCTURAL EPOXY, FILLET EVERY LAND EDGE.",
        f"{m}3D MODEL: output/cad/{sp.key}_rib_core.step / .stl. y FROM THE BUTT-CAP BASE (CORE STARTS AT "
        f"y = {fmt(sp.cap_length)}).",
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
    d.leader_note(P((xr_land, 245)), (P((a, 0))[0] + 10, P((0, 236))[1]),
                  f"LANDS {wave.land_width():.2f} @ {fmt(C.rib_pitch)}", 3.0, dot=True, arrow=False)
    d.leader_note(P((0.0, y0 + 8)), (P((0, 0))[0] + 22, P((0, y0 + 26))[1]), "M4 INSERT BORE", 3.0)
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
    title_block(d, 225.0, 236.0, sp, f"RIB CORE  ·  3D-PRINTED PA-CF  ·  {fmt(L - sp.cap_length)} × "
                f"{fmt(sp.width)} × {fmt(C.core_t)} mm", "1:2, 2:1", f"3 / {SHEETS}", "A3",
                title=f"RIB CORE – {sp.name}", material="PA-CF (NOTE 1)")
    return d


# --------------------------------------------------------------------------- PB-GR-001: grip assembly
GRIP_NO = "PB-GR-001"


def grip_notes(sp: PaddleSpec) -> list[str]:
    g = grip_dims(sp)
    return [
        f"GRIP: {fmt(g['wrap_w'])} × {fmt(g['wrap_t'])} R{g['wrap_r']:g} OVER THE WRAP = CIRCUMFERENCE "
        f"{g['grip_circumference']:.1f} (4¼ in). WRAP LENGTH {fmt(g['wrap_top'] - g['wrap_bot'])}.",
        f"HANDLE {fmt(sp.handle_length)} INCL. BUTT CAP. BODY {fmt(sp.handle_width)} × {fmt(sp.thickness)} "
        f"(CF {fmt(C.face_t)} / CORE {fmt(C.core_t)} / CF {fmt(C.face_t)}).",
        f"SLEEVE (2): BOND TO THE HANDLE WITH EPOXY, {fmt(C.sleeve_clear)} GAP PER SIDE FOR THE ADHESIVE.",
        "WRAP (3): REPLACEABLE PU GRIP, SPIRAL FROM THE CAP SKIRT UP TO UNDER THE COLLAR.",
        f"COLLAR (4): SLIDE OVER THE WRAP END, BOND TO THE SLEEVE; TOP AT y = {fmt(g['collar_top'])}.",
        f"INSERT (7): HEAT-SET AT ≈250 °C, FLUSH WITH THE CORE BUTT FACE (y = {fmt(sp.cap_length)}), SQUARE WITHIN 1°.",
        "SCREW (6): LOW-STRENGTH THREADLOCKER; TIGHTEN UNTIL THE CAP SEATS, MAX 0.8 N·m.",
        f"BUTT CAP (5): BASE {fmt(sp.cap_length)} + SKIRT {fmt(C.cap_skirt)} OVER THE SLEEVE; THE BASE COUNTS IN "
        f"THE {fmt(sp.length)} OVERALL LENGTH.",
        "SAME HANDLE ON PB-EL-001 AND PB-HY-001. ALL DIMENSIONS IN mm.",
    ]


def grip_sheet(sp: PaddleSpec, masses: dict | None = None) -> Doc:
    """masses: {design key: mass_properties} for the BOM mass column (optional)."""
    g = grip_dims(sp)
    d = Doc(420, 297, f"{GRIP_NO} grip and butt-cap assembly")
    H = hatches(d)
    frame_iso(d)
    h, T, hc, y0 = sp.handle_width / 2, sp.thickness / 2, C.core_t / 2, sp.cap_length
    yc = sp.cap_length + C.cap_skirt

    # ---- face view of the handle, 1:1 (y = 0 .. 160)
    cx, butt_y = 72.0, 248.0
    fv = View(d, (cx, butt_y), 1.0)
    P = fv.P
    from .geometry import build
    o = build(sp)
    clip = box(-200, g["collar_top"] - 0.01, 200, 140)
    from shapely.geometry import Polygon
    outline = Polygon(o.polyline(0.3))
    for seg in _segments(outline.exterior.intersection(clip)):
        d.poly([P(q) for q in seg], "vis")
    break_line(d, P((-25, 140)), P((25, 140)), 1.2)
    grip_front(d, fv, sp)
    fv.line((0, -6), (0, 146), "ctr")
    xl, xl2 = cx - g["collar_w"] / 2 - 10, cx - g["collar_w"] / 2 - 19
    d.dim_linear(P((-g["cap_w"] / 2, 0)), P((-g["cap_w"] / 2, yc)), "y", xl, fmt(yc), outside=True)
    d.dim_linear(P((-g["wrap_w"] / 2, g["wrap_bot"])), P((-g["wrap_w"] / 2, g["wrap_top"])), "y", xl,
                 fmt(g["wrap_top"] - g["wrap_bot"]))
    d.dim_linear(P((-g["collar_w"] / 2, g["collar_bot"])), P((-g["collar_w"] / 2, g["collar_top"])), "y", xl,
                 fmt(C.collar_h), outside=True)
    d.dim_linear(P((-g["cap_w"] / 2, 0)), P((-h, sp.handle_length)), "y", xl2, fmt(sp.handle_length))
    d.dim_linear(P((-g["cap_w"] / 2, 0)), P((g["cap_w"] / 2, 0)), "x", butt_y + 13, fmt(g["cap_w"]))
    d.dim_linear(P((-g["collar_w"] / 2, g["collar_top"])), P((g["collar_w"] / 2, g["collar_top"])), "x",
                 P((0, 147))[1], fmt(g["collar_w"]))
    d.dim_linear(P((-g["wrap_w"] / 2, 95)), P((g["wrap_w"] / 2, 95)), "x", P((0, 95))[1], fmt(g["wrap_w"]))
    # cutting planes E-E (across) and F-F (along the centre line)
    fv.section_line(70.0, -g["wrap_w"] / 2 - 9, g["wrap_w"] / 2 + 9, "E")
    for p, s in ((P((0, 46)), 1), (P((0, -6.5)), -1)):  # plane x = 0, looking towards -x
        d.line(p, (p[0], p[1] + s * 4), "cut")
        tail = (p[0], p[1] + s * 2)
        d.line(tail, (tail[0] - 6, tail[1]), "thin")
        d.arrow((tail[0] - 7.5, tail[1]), (-1, 0), 3.0, 1.4)
        d.text((tail[0] - 9.5, tail[1] + 1.8), "F", 5.0, anchor="end", weight="bold")
    for k, (n, y) in enumerate(((5, 4.0), (3, 60.0), (4, 124.0))):
        hw = (g["cap_w"], g["wrap_w"], g["collar_w"])[k] / 2
        _balloon(d, P((hw, y)), (P((hw, y))[0] + 16, P((hw, y))[1] - 6), n)
    view_label(d, cx, 270, "HANDLE (FACE VIEW)", "SCALE 1:1")

    # ---- section E-E across the grip, 2:1
    S2 = 2.0
    xe, ze = 160.0, 62.0

    def E(x: float, z: float):
        return (xe + x * S2, ze - z * S2)

    for zb, zt, key in ((hc, T, "cf"), (-hc, hc, "core"), (-T, -hc, "cf")):
        p, q = E(-h, zt), E(h, zb)
        d.rect(p[0], p[1], q[0] - p[0], q[1] - p[1], "vis", extra=fill(H[key]))
    ci_w, ci_t = sp.handle_width + 2 * C.sleeve_clear, sp.thickness + 2 * C.sleeve_clear
    d.path(rrect_path(xe, ze, g["sleeve_w"] * S2, g["sleeve_t"] * S2, C.sleeve_r * S2) + " " +
           rrect_path(xe, ze, ci_w * S2, ci_t * S2, 0.6 * S2), "vis",
           extra=f'style="fill:{H["grip"]}" fill-rule="evenodd"')
    d.path(rrect_path(xe, ze, g["wrap_w"] * S2, g["wrap_t"] * S2, g["wrap_r"] * S2) + " " +
           rrect_path(xe, ze, g["sleeve_w"] * S2, g["sleeve_t"] * S2, C.sleeve_r * S2), "vis",
           extra='style="fill:#000" fill-rule="evenodd"')
    ww, wt = g["wrap_w"] / 2, g["wrap_t"] / 2
    d.dim_linear(E(-h, T), E(h, T), "x", ze - wt * S2 - 5, fmt(sp.handle_width))
    d.dim_linear(E(-g["sleeve_w"] / 2, g["sleeve_t"] / 2), E(g["sleeve_w"] / 2, g["sleeve_t"] / 2), "x",
                 ze - wt * S2 - 11, fmt(g["sleeve_w"]))
    d.dim_linear(E(-ww, wt), E(ww, wt), "x", ze - wt * S2 - 17, fmt(g["wrap_w"]))
    d.dim_linear(E(h, T), E(h, -T), "y", xe + ww * S2 + 5, fmt(sp.thickness))
    d.dim_linear(E(g["sleeve_w"] / 2, g["sleeve_t"] / 2), E(g["sleeve_w"] / 2, -g["sleeve_t"] / 2), "y",
                 xe + ww * S2 + 11, fmt(g["sleeve_t"]))
    d.dim_linear(E(ww, wt), E(ww, -wt), "y", xe + ww * S2 + 17, fmt(g["wrap_t"]))
    d.leader_note(E(-g["sleeve_w"] / 2 + 0.9, -3.0), (E(-ww, 0)[0] - 7, ze + 9),
                  f"SLEEVE (2) R{fmt(C.sleeve_r)}, WALL {fmt(C.sleeve_wall)}", 2.6, dot=True, arrow=False)
    d.leader_note(E(-ww + 0.35, -wt + 4.0), (E(-ww, 0)[0] - 7, ze + 17),
                  f"WRAP (3) {C.wrap_t:g}, R{g['wrap_r']:g}", 2.6)
    d.line((xe - ww * S2 - 4, ze), (xe + ww * S2 + 2, ze), "ctr")
    d.line((xe, ze - wt * S2 - 2), (xe, ze + wt * S2 + 3), "ctr")
    view_label(d, xe, ze + wt * S2 + 18, "SECTION E–E", "SCALE 2:1")

    # ---- section F-F through the screw, butt end (y = 0 .. 40), 2:1
    yf1 = 40.0
    xf, zf = 270.0, 62.0

    def F(y: float, z: float):
        return (xf + y * S2, zf - z * S2)

    def box_(y_a, y_b, z_a, z_b, style, cls="vis"):
        p, q = F(y_a, max(z_a, z_b)), F(y_b, min(z_a, z_b))
        d.rect(p[0], p[1], q[0] - p[0], q[1] - p[1], cls, extra=style)

    # body: face sheets and core (with the insert bore and the screw clearance)
    for zb, zt in ((hc, T), (-T, -hc)):
        box_(y0, yf1, zb, zt, fill(H["cf"]))
    r1, r2 = C.insert_d / 2, C.screw_relief_d / 2
    yi, yr = y0 + C.insert_depth, y0 + C.screw_relief_depth
    core = [F(y0, r1), F(yi, r1), F(yi, r2), F(yr, r2), F(yr, -r2), F(yi, -r2), F(yi, -r1), F(y0, -r1),
            F(y0, -hc), F(yf1, -hc), F(yf1, hc), F(y0, hc)]
    d.poly(core, "vis", closed=True, extra=fill(H["core"]))
    # sleeve and wrap
    zs0, zs1 = sp.thickness / 2 + C.sleeve_clear, g["sleeve_t"] / 2
    for s in (1, -1):
        box_(y0, yf1, s * zs0, s * zs1, fill(H["grip"]))
        box_(g["wrap_bot"], yf1, s * zs1, s * wt, 'style="fill:#000"')
    # butt cap: base with counterbore + hole, skirt over the sleeve
    zc0 = g["cap_t"] / 2
    cb, hole = C.cb_d / 2, C.cap_hole_d / 2
    for s in (1, -1):
        cap = [F(0, s * cb), F(C.cb_depth, s * cb), F(C.cb_depth, s * hole), F(y0, s * hole), F(y0, s * zs1),
               F(yc, s * zs1), F(yc, s * zc0), F(0, s * zc0)]
        d.poly(cap, "vis", closed=True, extra=fill(H["cap"]))
    # heat-set insert (sectioned) and screw (not sectioned, ISO 128-50)
    ins_l, ins_i = 8.1, 1.7
    for s in (1, -1):
        box_(y0, y0 + ins_l, s * ins_i, s * r1, fill(H["metal"]))
    yb = C.cb_depth
    head = [F(yb - 2.2, 3.0), F(yb - 2.2, -3.0), F(yb - 1.4, -3.8), F(yb, -3.8), F(yb, 3.8), F(yb - 1.4, 3.8)]
    d.poly(head, "vis", closed=True, extra='style="fill:#fff"')
    box_(yb, yb + C.screw_len, -2.0, 2.0, 'style="fill:#fff"')
    for s in (1, -1):                                 # thread root lines
        d.line(F(y0 + 0.3, s * 1.62), F(yb + C.screw_len - 0.4, s * 1.62), "thin")
    d.line(F(yb - 2.2, 1.25), F(yb - 2.2 + 1.3, 1.25), "thin")   # hex socket
    d.line(F(yb - 2.2, -1.25), F(yb - 2.2 + 1.3, -1.25), "thin")
    d.line(F(yb - 2.2 + 1.3, 1.25), F(yb - 2.2 + 1.3, -1.25), "thin")
    break_line(d, F(yf1, wt + 1.5), F(yf1, -wt - 1.5))
    d.line(F(-3, 0), F(yf1 + 3, 0), "ctr")
    # dimensions / callouts
    d.dim_linear(F(0, zc0), F(yc, zc0), "x", zf - zc0 * S2 - 6, fmt(yc))
    d.dim_linear(F(0, zc0), F(y0, zc0), "x", zf - zc0 * S2 - 12, fmt(y0), outside=True)
    d.dim_linear(F(yc, -zc0), F(yc, zc0), "y", xf - 9, fmt(g["cap_t"]))
    d.leader_note(F(C.cb_depth / 2, -cb), (F(0, 0)[0] - 4, zf + wt * S2 + 9), f"⌴Ø{fmt(C.cb_d)} ↧{fmt(C.cb_depth)}, "
                  f"Ø{fmt(C.cap_hole_d)} THRU", 2.6)
    d.leader_note(F(y0 + 3.5, -r1), (F(y0, 0)[0] + 14, zf + wt * S2 + 9),
                  f"BORE Ø{fmt(C.insert_d)} × {fmt(C.insert_depth)}, Ø{fmt(C.screw_relief_d)} × "
                  f"{fmt(C.screw_relief_depth)}", 2.6)
    d.leader_note(F(y0 + 6, ins_i + 0.4), (F(16, 0)[0] + 18, zf - zc0 * S2 - 6), "INSERT M4 Ø5.6 × 8.1 (7)", 2.6)
    d.leader_note(F(yb + 9, 0.5), (F(yf1, 0)[0] + 8, zf - 3), "ISO 7380 M4 × 12 (6)", 2.6, dot=True, arrow=False)
    view_label(d, F(yf1 / 2, 0)[0], zf + wt * S2 + 18, "SECTION F–F (BUTT END)", "SCALE 2:1")

    # ---- bill of materials
    bx, by = 130.0, 128.0
    cols = (("ITEM", 11), ("PART", 50), ("MATERIAL / SPECIFICATION", 92), ("QTY", 11), ("MASS g (EL / HY)", 33))
    rh = 5.4
    xx = bx
    for cap, w in cols:
        cell(d, xx, by, w, rh + 0.6, "", cap, 2.5, weight="bold")
        xx += w

    def mass(part: str) -> str:
        if not masses:
            return "–"
        v = [masses[k]["parts"][part]["mass_g"] for k in masses]
        return " / ".join(f"{x:.1f}" if x < 10 else f"{x:.0f}" for x in v) if len(set(round(x, 1) for x in v)) > 1 \
            else (f"{v[0]:.1f}" if v[0] < 10 else f"{v[0]:.0f}")
    rows = [("1", "Face sheet", f"Woven carbon/epoxy plate {fmt(C.face_t)} thk, cut to profile DXF", "2",
             mass("face_sheet_top")),
            ("1a", "Rib core", "PA-CF, 3D printed – sheet 3 of PB-EL-001 / PB-HY-001", "1", mass("rib_core")),
            ("2", "Grip sleeve", f"TPU 95A, printed or moulded, {fmt(g['sleeve_w'])} × {fmt(g['sleeve_t'])} "
             f"R{fmt(C.sleeve_r)}", "1", mass("grip_sleeve")),
            ("3", "Grip wrap", f"PU replacement grip {C.wrap_t:g} thk, {fmt(g['wrap_top'] - g['wrap_bot'])} long",
             "1", mass("grip_wrap")),
            ("4", "Throat collar", f"TPU 95A, {fmt(g['collar_w'])} × {fmt(g['collar_t'])} × {fmt(C.collar_h)}", "1",
             mass("throat_collar")),
            ("5", "Butt cap", f"TPU 95A, {fmt(g['cap_w'])} × {fmt(g['cap_t'])}, base {fmt(y0)} + skirt "
             f"{fmt(C.cap_skirt)}", "1", mass("butt_cap")),
            ("6", "Screw", "ISO 7380-1 M4 × 12 button head, A2 stainless", "1", mass("screw_M4x12_ISO7380")),
            ("7", "Threaded insert", "M4 heat-set, brass, OD 5.6 × 8.1", "1", mass("insert_M4_heatset")),
            ("8", "Adhesive", "Structural epoxy (core–sheets, sleeve, collar)", "a/r", "–")]
    for i, r in enumerate(rows):
        yy = by + rh + 0.6 + i * rh
        xx = bx
        for k, (cap, w) in enumerate(cols):
            cell(d, xx, yy, w, rh, "", r[k], 2.45, anchor="start" if k in (1, 2) else "middle")
            xx += w
    if masses:
        yy = by + rh + 0.6 + len(rows) * rh
        tot = " / ".join(f"{masses[k]['mass_g']:.0f}" for k in masses)
        cell(d, bx, yy, sum(w for _, w in cols[:4]), rh, "", "COMPLETE PADDLE (3D MODEL)", 2.45, weight="bold",
             anchor="start")
        cell(d, bx + sum(w for _, w in cols[:4]), yy, cols[4][1], rh, "", tot, 2.45, weight="bold")

    # ---- notes + title block
    notes_block(d, 228.0, 192.0, grip_notes(sp), size=2.3, lead=3.5)
    title_block(d, 225.0, 236.0, None, f"HANDLE {fmt(sp.handle_length)} × {fmt(sp.handle_width)} × "
                f"{fmt(sp.thickness)}  ·  GRIP {g['grip_circumference']:.1f} (4¼ in)  ·  BOTH PADDLES",
                "1:1, 2:1", "1 / 1", "A3", title="GRIP AND BUTT-CAP ASSEMBLY", drawing_no=GRIP_NO,
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
