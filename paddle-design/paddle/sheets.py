"""Engineering drawing sheets (REV B: carbon / wave-rib sandwich with grip assembly).

Per paddle:
  Sheet 1 - A3 landscape general arrangement: front view with the grip, side view with the
            4 / 8 / 4 lay-up, sections A-A (blade, wave core) and B-B (handle + grip),
            isometric view, notes, title block; first-angle projection, 1:2.
  Sheet 2 - A3 portrait full-size (1:1) body profile template with the geometry table.
  Sheet 3 - rib core (sheets_construction.core_sheet).
Shared by both paddles: PB-GR-001 grip and butt-cap assembly (sheets_construction.grip_sheet).
"""
from __future__ import annotations

from . import wave
from .geometry import CONSTRUCTION as C
from .geometry import Outline, PaddleSpec, grip_dims
from .pictorial import ISOMETRIC, project
from .svgkit import Doc, View, f, fmt, frame_iso, hatch_pattern, projection_symbol_first_angle

ISSUE = {"rev": "B", "date": "2026-10-23", "drawn": "Claude Code", "status": "ISSUED FOR REVIEW"}
SHEETS = 3                                  # sheets per paddle drawing
USAP_SUM, USAP_LEN = 609.6, 431.8          # 24 in (length + width), 17 in (length)
GREY = "#555"


# --------------------------------------------------------------------------- helpers
def draw_pictorial(d: Doc, o: Outline, frame, centre, scale: float, wall_fill: str = "#e4e4e4",
                   face_fill: str = "#fff", lw: float = 0.35) -> tuple[float, float, float, float]:
    """Hidden-surface line drawing of the extruded paddle; returns its sheet bbox."""
    pic = project(o, frame)
    u0, v0, u1, v1 = pic.bbox
    ox = centre[0] - (u0 + u1) / 2 * scale
    oy = centre[1] + (v0 + v1) / 2 * scale

    def S(p):
        return (ox + p[0] * scale, oy - p[1] * scale)

    edge = f'stroke="#000" stroke-width="{lw}" stroke-linecap="round"'
    for w in pic.walls:
        d.poly([S(p) for p in w.quad], "", closed=True,
               extra=f'fill="{wall_fill}" stroke="{wall_fill}" stroke-width="0.15"')
        d.line(S(w.back_edge[0]), S(w.back_edge[1]), "", edge)
        for a, b in w.silhouette:
            d.line(S(a), S(b), "", edge)
    d.poly([S(p) for p in pic.face], "", closed=True,
           extra=f'fill="{face_fill}" stroke="#000" stroke-width="{lw}" stroke-linejoin="round"')
    return S((u0, v1)) + S((u1, v0))


def core_inner(o: Outline):
    """Inner edge of the core's perimeter frame (shapely polygon, model mm)."""
    from shapely.geometry import Polygon
    return Polygon(o.polyline(0.5)).buffer(-C.frame_w, join_style=1, quad_segs=32)


def cell(d: Doc, x: float, y: float, w: float, h: float, caption: str, value: str = "",
         size: float = 3.2, weight: str = "normal", anchor: str = "middle") -> None:
    d.rect(x, y, w, h, "thin")
    if caption:
        d.text((x + 1.2, y + 2.6), caption, 1.9, anchor="start", fill=GREY)
    if value:
        tx = x + w / 2 if anchor == "middle" else x + 2.5
        d.text((tx, y + h / 2 + 0.35 * size + (1.0 if caption else 0)), value, size, anchor=anchor,
               weight=weight)


def title_block(d: Doc, x: float, y: float, sp: PaddleSpec | None, subtitle: str, scale: str, sheet: str,
                size: str, w: float = 180.0, title: str | None = None, drawing_no: str | None = None,
                material: str = "SEE NOTES") -> None:
    """ISO 7200-style title block, top-left corner at (x, y), 46 mm tall."""
    d.rect(x, y, w, 46, "frame")
    cell(d, x, y, w, 16, "", "")
    d.text((x + 3, y + 7.6), title or f"PICKLEBALL PADDLE – {sp.name}", 5.6, anchor="start", weight="bold")
    d.text((x + 3, y + 13.2), subtitle, 3.0, anchor="start")
    y2 = y + 16
    for i, (cap, val) in enumerate((("DRAWN", ISSUE["drawn"]), ("DATE", ISSUE["date"]),
                                    ("CHECKED", ""), ("APPROVED", ""))):
        cell(d, x + i * w / 4, y2, w / 4, 10, cap, val)
    y3 = y2 + 10
    cols = (("DRAWING No.", drawing_no or sp.drawing_no, 52), ("REV", ISSUE["rev"], 16), ("SHEET", sheet, 22),
            ("SIZE", size, 18), ("SCALE", scale, 32), ("UNITS", "mm", 40))
    xx = x
    for cap, val, cw in cols:
        cell(d, xx, y3, cw, 10, cap, val, 3.4 if cap == "DRAWING No." else 3.2,
             weight="bold" if cap == "DRAWING No." else "normal")
        xx += cw
    y4 = y3 + 10
    cell(d, x, y4, 46, 10, "PROJECTION")
    projection_symbol_first_angle(d, x + 14, y4 + 6.2, 5.0)
    cell(d, x + 46, y4, 64, 10, "MATERIAL", material, 3.0)
    cell(d, x + 110, y4, w - 110, 10, "STATUS", ISSUE["status"], 3.0)


def notes_block(d: Doc, x: float, y: float, lines: list[str], size: float = 2.75, lead: float = 4.35) -> None:
    d.text((x, y), "NOTES", 3.5, anchor="start", weight="bold")
    yy = y + 5.6
    for i, ln in enumerate(lines, 1):
        parts = ln.split("\n")
        d.text((x, yy), f"{i}.", size, anchor="start")
        for k, p in enumerate(parts):
            d.text((x + 5, yy), p, size, anchor="start")
            yy += lead
        yy += 0.4


def ga_notes(o: Outline, mass: dict | None = None) -> list[str]:
    sp = o.spec
    g = grip_dims(sp)
    s = sp.length + sp.width
    notes = [
        "ALL DIMENSIONS IN MILLIMETRES. DO NOT SCALE THE DRAWING. UNLESS STATED: LINEAR ±0.5, ANGULAR ±0.5°.",
        "PROFILE SYMMETRICAL ABOUT THE CENTRE LINE. ALL ARCS TANGENT TO ADJOINING EDGES.",
        f"SANDWICH: CF FACE SHEET {fmt(C.face_t)} + WAVE-RIB CORE {fmt(C.core_t)} + CF FACE SHEET {fmt(C.face_t)} = "
        f"{fmt(sp.thickness)} ±0.3, UNIFORM OVER\nBLADE AND HANDLE. BODY (SHEETS + CORE) FROM y = {fmt(sp.cap_length)} "
        f"TO THE TIP; BUTT CAP y = 0 … {fmt(sp.cap_length + C.cap_skirt)}.",
        f"FACE SHEETS (2 OFF, IDENTICAL): WOVEN CARBON/EPOXY PLATE {fmt(C.face_t)} THK, CUT TO "
        f"{sp.drawing_no}_profile.dxf,\nOUTER EDGES R0.8. TEMPLATE: SHEET 2.",
        f"CORE: 3D-PRINTED PA-CF, CLOSED FRAME {fmt(C.frame_w)}, WAVE RIB λ{fmt(C.rib_pitch)} / WALL {fmt(C.rib_t)} / "
        f"LANDS {wave.land_width():.2f}, SOLID TO\ny = {fmt(C.solid_to)} WITH 45° FLUTE RUN-OUT – SEE SHEET 3.",
        "BOND CORE TO SHEETS: STRUCTURAL EPOXY, ABRADED + PRIMED SURFACES, FILLET ALL LAND EDGES\n"
        "(CRITICAL ITEM – SEE THE STRESS REPORT).",
        f"GRIP: SLEEVE + WRAP + COLLAR + BUTT CAP, ISO 7380 M4×12 SCREW INTO M4 HEAT-SET INSERT –\n"
        f"SEE PB-GR-001. GRIP {fmt(g['wrap_w'])} × {fmt(g['wrap_t'])}, CIRCUMFERENCE "
        f"{g['grip_circumference']:.1f} (4¼ in).",
        f"USA PICKLEBALL LIMITS: L + W = {fmt(s)} ≤ {fmt(USAP_SUM)} (24 in), L = {fmt(sp.length)} ≤ {fmt(USAP_LEN)} "
        f"(17 in), INCL. BUTT CAP.\nAN EDGE GUARD COUNTS TOWARDS THESE LIMITS (MARGIN {fmt(USAP_SUM - s)}).",
    ]
    if mass:
        notes.append(f"MASS {mass['mass_g']:.0f} g, BALANCE POINT {mass['balance_mm']:.0f} FROM THE BUTT "
                     f"(FROM THE 3D MODEL).")
    return notes


# --------------------------------------------------------------------------- sheet 1
def rrect_path(cx: float, cy: float, w: float, h: float, r: float) -> str:
    """Closed SVG path of a rounded rectangle centred on (cx, cy) (sheet units)."""
    x0, y0, x1, y1 = cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2
    r = min(r, w / 2, h / 2)
    if r <= 0:
        return f"M{f(x0)},{f(y0)} H{f(x1)} V{f(y1)} H{f(x0)} Z"
    a = f"A{f(r)},{f(r)} 0 0 1"
    return (f"M{f(x0 + r)},{f(y0)} H{f(x1 - r)} {a} {f(x1)},{f(y0 + r)} V{f(y1 - r)} {a} {f(x1 - r)},{f(y1)} "
            f"H{f(x0 + r)} {a} {f(x0)},{f(y1 - r)} V{f(y0 + r)} {a} {f(x0 + r)},{f(y0)} Z")


def hatches(d: Doc) -> dict[str, str]:
    """Section fills: a different hatch per part (ISO 128-50); thin parts are filled solid."""
    return {"cf": hatch_pattern(d, "h_cf", 0.9, 45), "core": hatch_pattern(d, "h_core", 1.4, -45),
            "grip": hatch_pattern(d, "h_grip", 2.2, 30), "metal": hatch_pattern(d, "h_metal", 0.7, 60),
            "cap": hatch_pattern(d, "h_cap", 1.8, -60)}


def fill(pattern: str) -> str:
    return f'style="fill:{pattern}"'


def grip_front(d: Doc, v: View, sp: PaddleSpec, white: str = "#fff") -> None:
    """Butt cap, grip wrap and throat collar in the face (XY) view; the handle inside is hidden."""
    g = grip_dims(sp)
    for hw, y0, y1 in ((g["cap_w"] / 2, 0.0, sp.cap_length + C.cap_skirt), (g["wrap_w"] / 2, g["wrap_bot"], g["wrap_top"]),
                       (g["collar_w"] / 2, g["collar_bot"], g["collar_top"])):
        p, q = v.P((-hw, y1)), v.P((hw, y0))
        d.rect(p[0], p[1], q[0] - p[0], q[1] - p[1], "vis", extra=f'style="fill:{white}"')
    h = sp.handle_width / 2
    for sx in (-1, 1):
        v.line((sx * h, sp.cap_length), (sx * h, g["collar_top"]), "hid")
    v.line((-h, sp.cap_length), (h, sp.cap_length), "hid")


def ga_sheet(o: Outline, mass: dict | None = None) -> Doc:
    sp = o.spec
    g = grip_dims(sp)
    d = Doc(420, 297, f"{sp.drawing_no} {sp.name} paddle - general arrangement")
    H = hatches(d)
    frame_iso(d)
    a, h, t, L = sp.width / 2, sp.handle_width / 2, sp.handle_length, sp.length
    S = 0.5
    cx, tip_y = 117.0, 40.0
    butt_y = tip_y + L * S
    fv = View(d, (cx, butt_y), S)
    P = fv.P
    cw = g["cap_w"] / 2

    # ---- front view: body outline, grip over the handle
    d.path(fv.outline_path(o), "vis")
    grip_front(d, fv, sp)
    fv.line((0, -9), (0, L + 9), "ctr")
    top_ref = (-o.pts["crown"][0], L) if sp.head == "square" else (0.0, L)
    yside = o.pts["side_hi"][1]
    d.dim_linear(P((-a, yside)), P((a, yside)), "x", tip_y - 11, fmt(sp.width))
    d.dim_linear(P((-cw, 0)), P((cw, 0)), "x", butt_y + 9, fmt(g["cap_w"]))
    x1, x2 = cx - a * S - 20, cx - a * S - 31
    d.dim_linear(P((-cw, 0)), P((-h, t)), "y", x1, fmt(sp.handle_length))
    d.dim_linear(P((-h, t)), P(top_ref), "y", x1, fmt(sp.blade_length))
    d.dim_linear(P((-cw, 0)), P(top_ref), "y", x2, fmt(sp.length))
    d.text((x1 + 2.2, P((0, t / 2))[1] + 13), "HANDLE", 2.5, rot=-90, fill=GREY)
    d.text((x1 + 2.2, P((0, t + sp.blade_length / 2))[1] + 12), "BLADE", 2.5, rot=-90, fill=GREY)
    d.leader_note(P((g["wrap_w"] / 2, 62)), (P((0, 0))[0] + 26, P((0, 72))[1]), "GRIP – SEE PB-GR-001", 3.0)

    tv = (h, o.info["throat_vertex_y"])
    fv.line(o.pts["taper_lo"], tv)
    fv.line(tv, (h + 44, tv[1]))
    fv.dim_angle(tv, 0.0, sp.taper_deg, 19.0, f"{fmt(sp.taper_deg)}°", text_r=24.0)
    c, r = o.centres["throat"]
    fv.dim_radius(c, r, 150, f"2×R{fmt(r)}", 25, side="in")
    c, r = o.centres["shoulder"]
    fv.dim_radius(c, r, -32, f"2×R{fmt(r)}", 13, side="out")
    if sp.head == "square":
        c, r = o.centres["corner"]
        fv.dim_radius(c, r, 45, f"2×R{fmt(r)}", 15, side="in")
    else:
        c, r = o.centres["dome"]
        fv.centre_mark(c)
        fv.dim_radius_from_centre(c, r, 76, f"R{fmt(r)}")
        c, r = o.centres["dome_shoulder"]
        fv.dim_radius(c, r, 30, f"2×R{fmt(r)}", 11, side="out")

    fv.section_line(280.0, -a - 15, a + 15, "A")
    fv.section_line(70.0, -g["collar_w"] / 2 - 12, g["collar_w"] / 2 + 12, "B")
    d.text((cx, 259), "FRONT VIEW", 3.5, weight="bold")

    # ---- side view (from the left, placed on the right: first angle)
    sv_x = 212.0
    sv = View(d, (sv_x, butt_y), S)
    T, hc = sp.thickness / 2, C.core_t / 2
    y0 = sp.cap_length
    d.poly([sv.P((-T, y0)), sv.P((T, y0)), sv.P((T, L)), sv.P((-T, L))], "vis", closed=True)
    for z in (-hc, hc):                                   # bond lines between sheets and core
        sv.line((z, g["collar_top"]), (z, L), "vis")
    for ht, ya, yb in ((g["cap_t"] / 2, 0.0, y0 + C.cap_skirt), (g["wrap_t"] / 2, g["wrap_bot"], g["wrap_top"]),
                       (g["collar_t"] / 2, g["collar_bot"], g["collar_top"])):
        p, q = sv.P((-ht, yb)), sv.P((ht, ya))
        d.rect(p[0], p[1], q[0] - p[0], q[1] - p[1], "vis", extra='style="fill:#fff"')
    for z in (-T, T):
        sv.line((z, y0), (z, g["collar_top"]), "hid")
    sv.line((0, -9), (0, L + 9), "ctr")
    d.dim_linear(sv.P((-T, L)), sv.P((T, L)), "x", tip_y - 11, fmt(sp.thickness), outside=True)
    d.text((sv_x, 259), "SIDE VIEW", 3.5, weight="bold")
    d.text((sv_x, 263.5), f"LAY-UP {fmt(C.face_t)} / {fmt(C.core_t)} / {fmt(C.face_t)}", 2.6)

    # ---- section A-A (blade, 1:2): face sheets, closed frame and the wave rib
    xa, ya = 287.0, 118.0
    aw = o.half_width_at(280.0)

    def A(x: float, z: float):
        return (xa + x * S, ya - z * S)

    for z0 in (hc, -hc - C.face_t):
        p, q = A(-aw, z0 + C.face_t), A(aw, z0)
        d.rect(p[0], p[1], q[0] - p[0], q[1] - p[1], "vis", extra=fill(H["cf"]))
    for sx in (-1, 1):
        x_in, x_out = sorted((sx * (aw - C.frame_w), sx * aw))
        p, q = A(x_in, hc), A(x_out, -hc)
        d.rect(p[0], p[1], q[0] - p[0], q[1] - p[1], "vis", extra=fill(H["core"]))
    d.poly([A(x, z) for x, z in wave.wall_polygon(-(aw - C.frame_w), aw - C.frame_w)], "", closed=True,
           extra='fill="#000" stroke="none"')
    d.dim_linear(A(-aw, T), A(aw, T), "x", ya - T * S - 8, fmt(2 * aw))
    d.dim_linear(A(aw, T), A(aw, -T), "y", xa + aw * S + 8, fmt(sp.thickness), outside=True)
    d.line((xa - aw * S - 6, ya), (xa + aw * S + 6, ya), "ctr")
    d.text((xa, ya + 12), "SECTION A–A", 3.5, weight="bold")
    d.text((xa, ya + 16.2), f"SCALE 1:2 · CF {fmt(C.face_t)} / WAVE-RIB CORE {fmt(C.core_t)} / CF {fmt(C.face_t)} · "
           "CORE DETAIL: SHEET 3", 2.5)

    # ---- section B-B (handle with grip, 1:1)
    xb, yb = 370.0, 118.0

    def B(x: float, z: float):
        return (xb + x, yb - z)

    for z0, key in ((hc, "cf"), (-hc, "core"), (-T, "cf")):
        zt = z0 + (C.face_t if key == "cf" else C.core_t)
        p, q = B(-h, zt), B(h, z0)
        d.rect(p[0], p[1], q[0] - p[0], q[1] - p[1], "vis", extra=fill(H[key]))
    ci_w, ci_t = sp.handle_width + 2 * C.sleeve_clear, sp.thickness + 2 * C.sleeve_clear
    d.path(rrect_path(xb, yb, g["sleeve_w"], g["sleeve_t"], C.sleeve_r) + " " + rrect_path(xb, yb, ci_w, ci_t, 0.6),
           "vis", extra=f'style="fill:{H["grip"]}" fill-rule="evenodd"')
    d.path(rrect_path(xb, yb, g["wrap_w"], g["wrap_t"], g["wrap_r"]) + " " +
           rrect_path(xb, yb, g["sleeve_w"], g["sleeve_t"], C.sleeve_r), "vis",
           extra='style="fill:#000" fill-rule="evenodd"')
    ww, wt = g["wrap_w"] / 2, g["wrap_t"] / 2
    d.dim_linear(B(-h, T), B(h, T), "x", yb - wt - 4.5, fmt(sp.handle_width))
    d.dim_linear(B(-ww, wt), B(ww, wt), "x", yb - wt - 10.5, fmt(g["wrap_w"]))
    d.dim_linear(B(h, T), B(h, -T), "y", xb + ww + 4.5, fmt(sp.thickness))
    d.dim_linear(B(ww, wt), B(ww, -wt), "y", xb + ww + 10.5, fmt(g["wrap_t"]))
    d.line((xb - ww - 4, yb), (xb + ww + 2, yb), "ctr")
    d.line((xb, yb - wt - 2), (xb, yb + wt + 3), "ctr")
    d.text((xb, yb + wt + 9), "SECTION B–B", 3.5, weight="bold")
    d.text((xb, yb + wt + 13.2), "SCALE 1:1 · GRIP: PB-GR-001", 2.5)

    # ---- isometric view
    draw_pictorial(d, o, ISOMETRIC, (318.0, 52.0), 0.25)
    d.text((318.0, 91.0), "ISOMETRIC VIEW", 3.5, weight="bold")
    d.text((318.0, 95.5), "SCALE 1:4 (BODY ONLY)", 2.8)

    # ---- notes + title block
    notes_block(d, 228.0, 152.0, ga_notes(o, mass), size=2.5, lead=3.75)
    title_block(d, 225.0, 236.0, sp, f"GENERAL ARRANGEMENT  ·  {fmt(sp.length)} × {fmt(sp.width)} "
                f"× {fmt(sp.thickness)} mm  ·  CF / WAVE-RIB SANDWICH", "1:2", f"1 / {SHEETS}", "A3")
    return d


# --------------------------------------------------------------------------- sheet 2
def geometry_rows(o: Outline) -> list[tuple[str, str, float, float]]:
    """(label, description, x, y) for the right half of the profile."""
    p, c = o.pts, o.centres
    rows = [("P1", "Butt corner", *p["butt"]),
            ("P2", "Handle edge / throat arc", *p["throat"]),
            ("P3", "Throat arc / taper", *p["taper_lo"]),
            ("P4", "Taper / shoulder arc", *p["taper_hi"]),
            ("P5", "Shoulder arc / side", *p["side_lo"])]
    if o.spec.head == "square":
        rows += [("P6", "Side / tip-corner arc", *p["side_hi"]),
                 ("P7", "Tip-corner arc / tip edge", *p["crown"]),
                 ("C1", f"Throat centre  R{fmt(c['throat'][1])}", *c["throat"][0]),
                 ("C2", f"Shoulder centre  R{fmt(c['shoulder'][1])}", *c["shoulder"][0]),
                 ("C3", f"Tip-corner centre  R{fmt(c['corner'][1])}", *c["corner"][0])]
    else:
        rows += [("P6", "Side / crown-shoulder arc", *p["side_hi"]),
                 ("P7", "Crown shoulder / dome", *p["crown"]),
                 ("P8", "Apex (on centre line)", 0.0, o.spec.length),
                 ("C1", f"Throat centre  R{fmt(c['throat'][1])}", *c["throat"][0]),
                 ("C2", f"Shoulder centre  R{fmt(c['shoulder'][1])}", *c["shoulder"][0]),
                 ("C3", f"Crown-shoulder centre  R{fmt(c['dome_shoulder'][1])}", *c["dome_shoulder"][0]),
                 ("C4", f"Dome centre  R{fmt(c['dome'][1])}", *c["dome"][0])]
    return rows


def template_sheet(o: Outline) -> Doc:
    sp = o.spec
    W, H = 297.0, 420.0
    d = Doc(W, H, f"{sp.drawing_no} {sp.name} paddle - full-size template")
    m = 7.0
    d.rect(m, m, W - 2 * m, H - 2 * m, "thin")
    cx, butt_y = W / 2, 405.0
    v = View(d, (cx, butt_y), 1.0)
    L, h = sp.length, sp.handle_width / 2

    # faint fill so the cut shape reads at a glance, then the cut line itself
    d.path(v.outline_path(o), "", extra='fill="#f4f6f8" stroke="none"')
    v.line((0, -4), (0, L + 4), "ctr")
    d.text((cx, v.P((0, 285))[1]), sp.name, 14, weight="bold", fill="#c9cfd6")
    d.text((cx, v.P((0, 285))[1] + 8), f"{fmt(L)} × {fmt(sp.width)} × {fmt(sp.thickness)} mm",
           6, fill="#c9cfd6")
    d.text((cx + 8.5, v.P((0, 65))[1]), f"HANDLE {fmt(sp.handle_width)} × {fmt(sp.handle_length)}",
           3.2, rot=-90, fill="#8a939c")

    # light reference lines: butt-cap base, core frame inner edge, end of the solid core zone
    ref = 'fill="none" stroke="#9aa3ad" stroke-width="0.25" stroke-dasharray="6 1.5 1.5 1.5"'
    d.line(v.P((-h - 22, 0)), v.P((h + 22, 0)), "", ref)
    d.text(v.P((-h - 24, 1.0)), "BUTT-CAP BASE y = 0 (CAP NOT ON THIS TEMPLATE)", 2.4, anchor="end", fill="#7c8590")
    inner = core_inner(o)
    for ring in [inner.exterior]:
        d.poly([v.P(q) for q in ring.coords], "", extra=ref)
    from shapely.geometry import LineString
    seg = LineString([(-200, C.solid_to), (200, C.solid_to)]).intersection(inner)
    if not seg.is_empty:
        (xa0, _), (xa1, _) = seg.coords[0], seg.coords[-1]
        d.line(v.P((xa0, C.solid_to)), v.P((xa1, C.solid_to)), "", ref)
        d.text(v.P((xa1 - 2, C.solid_to + 1.6)), f"CORE: SOLID BELOW y = {fmt(C.solid_to)}", 2.4, anchor="end",
               fill="#7c8590")
    p_lab = v.P((sp.width / 2 - C.frame_w - 2, o.pts["side_lo"][1] + 30))
    d.text(p_lab, f"CORE FRAME INNER EDGE ({fmt(C.frame_w)} INSIDE)", 2.4, anchor="end", rot=-90, fill="#7c8590")

    # throat / handle start line
    yt = sp.handle_length
    v.line((-h - 34, yt), (h + 34, yt), "hid")
    d.text(v.P((h + 36, yt + 1.6)), "BLADE ↑", 3.0, anchor="start", fill=GREY)
    d.text(v.P((h + 36, yt - 4.2)), "HANDLE ↓", 3.0, anchor="start", fill=GREY)
    d.text(v.P((-h - 36, yt - 1.4)), f"{fmt(yt)} FROM BUTT", 3.0, anchor="end", fill=GREY)

    # tangent points, arc centres, labels (right half labelled; left half is the mirror)
    rows = geometry_rows(o)
    for lab, _, x, y in rows:
        if lab.startswith("P"):
            for sx in ((1, -1) if x else (1,)):
                d.circle(v.P((sx * x, y)), 0.9, "thin", extra='style="fill:#fff"')
        else:
            for sx in ((1, -1) if x else (1,)):
                v.centre_mark((sx * x, y), 3.0)
    offsets = {"P1": (3, -4), "P2": (2.0, -5.5), "P3": (2.5, 3.5), "P4": (2, 4), "P5": (2.5, -2), "P6": (2.5, 3.5),
               "P7": (2, 4.5), "P8": (2, 4.5), "C1": (2.5, -3), "C2": (2.5, -3), "C3": (2.5, -3), "C4": (2.5, -3)}
    for lab, _, x, y in rows:
        px, py = v.P((x, y))
        ox, oy = offsets[lab]
        d.text((px + ox, py - oy + 1.2), lab, 3.0, anchor="start", weight="bold",
               fill="#000" if lab.startswith("P") else "#1f5fa8")

    d.path(v.outline_path(o), "", extra='fill="none" stroke="#000" stroke-width="0.35" stroke-linejoin="round"')

    # geometry table (bottom left, beside the handle)
    tx, ty = 12.0, 283.0
    cw = (12.0, 64.0, 18.0, 18.0)
    rh = 5.6
    d.text((tx, ty - 3.0), "PROFILE GEOMETRY (RIGHT HALF; LEFT = MIRROR, X → −X)", 2.8,
           anchor="start", weight="bold")
    hdr = ("ID", "POINT", "X", "Y")
    xx = tx
    for k, wv in enumerate(cw):
        cell(d, xx, ty, wv, rh, "", hdr[k], 2.7, weight="bold")
        xx += wv
    for i, (lab, desc, x, y) in enumerate(rows):
        yy = ty + rh * (i + 1)
        vals = (lab, desc, f"{x:.2f}", f"{y:.2f}")
        xx = tx
        for k, wv in enumerate(cw):
            cell(d, xx, yy, wv, rh, "", vals[k], 2.7, anchor="start" if k == 1 else "middle")
            xx += wv
    yy = ty + rh * (len(rows) + 1) + 4.2
    d.text((tx, yy), f"Origin: centre of the butt-cap base (y = 0); the body starts at y = {fmt(sp.cap_length)}.",
           2.5, anchor="start", fill=GREY)
    d.text((tx, yy + 3.8), "All arcs tangent. Dots = tangent points, + = arc centres.", 2.5,
           anchor="start", fill=GREY)

    # scale check bars (right side, above the title block)
    bx, by = 178.0, 300.0
    d.text((bx, by - 4.5), "SCALE CHECK – MUST MEASURE 100 mm", 2.8, anchor="start", weight="bold")
    d.rect(bx, by, 100, 3.0, "thin")
    for i in range(11):
        hh = 3.0 if i % 5 == 0 else 1.8
        d.line((bx + 10 * i, by + 3.0), (bx + 10 * i, by + 3.0 + hh), "thin")
    for i in range(0, 100, 20):
        d.rect(bx + i, by, 10, 3.0, "", extra='fill="#000"')
    d.text((bx, by + 9.6), "0", 2.6); d.text((bx + 50, by + 9.6), "50", 2.6)
    d.text((bx + 100, by + 9.6), "100 mm", 2.6)
    d.rect(bx + 82, by + 14, 18, 50, "thin")
    d.text((bx + 80, by + 41), "50 mm", 2.6, anchor="end")
    d.text((bx + 80, by + 45), "(height check)", 2.2, anchor="end", fill=GREY)

    # compact title block
    tbx, tby, tbw = 178.0, 372.0, 108.0
    d.rect(tbx, tby, tbw, 40, "frame")
    cell(d, tbx, tby, tbw, 11, "", "")
    d.text((tbx + 2.5, tby + 5.4), f"PICKLEBALL PADDLE – {sp.name}", 4.0, anchor="start", weight="bold")
    d.text((tbx + 2.5, tby + 9.3), "FULL-SIZE BODY TEMPLATE – FACE SHEETS + CORE", 2.6, anchor="start")
    cell(d, tbx, tby + 11, 44, 9, "DRAWING No.", sp.drawing_no, 3.2, weight="bold")
    cell(d, tbx + 44, tby + 11, 16, 9, "REV", ISSUE["rev"], 3.0)
    cell(d, tbx + 60, tby + 11, 20, 9, "SHEET", f"2 / {SHEETS}", 3.0)
    cell(d, tbx + 80, tby + 11, tbw - 80, 9, "SCALE", "1:1", 3.2, weight="bold")
    cell(d, tbx, tby + 20, 44, 9, "DATE", ISSUE["date"], 3.0)
    cell(d, tbx + 44, tby + 20, 36, 9, "DRAWN", ISSUE["drawn"], 2.8)
    cell(d, tbx + 80, tby + 20, tbw - 80, 9, "UNITS", "mm", 3.0)
    cell(d, tbx, tby + 29, tbw, 11, "", "")
    d.text((tbx + tbw / 2, tby + 33.8), "PRINT ON A3 AT 100 % / “ACTUAL SIZE” – NO FIT-TO-PAGE.",
           2.6, weight="bold")
    d.text((tbx + tbw / 2, tby + 37.6), "Verify both scale bars before cutting.", 2.5)
    return d
