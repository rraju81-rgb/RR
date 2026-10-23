"""Engineering drawing sheets.

Sheet 1 - A3 landscape general arrangement (front view, side view, sections,
          isometric view, notes, title block), first-angle projection, 1:2.
Sheet 2 - A3 portrait full-size (1:1) profile template with the geometry table.
"""
from __future__ import annotations

from .geometry import Outline, PaddleSpec
from .pictorial import ISOMETRIC, project
from .svgkit import Doc, View, fmt, frame_iso, hatch_pattern, projection_symbol_first_angle

ISSUE = {"rev": "A", "date": "2026-10-23", "drawn": "Claude Code", "status": "ISSUED FOR REVIEW"}
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


def cell(d: Doc, x: float, y: float, w: float, h: float, caption: str, value: str = "",
         size: float = 3.2, weight: str = "normal", anchor: str = "middle") -> None:
    d.rect(x, y, w, h, "thin")
    if caption:
        d.text((x + 1.2, y + 2.6), caption, 1.9, anchor="start", fill=GREY)
    if value:
        tx = x + w / 2 if anchor == "middle" else x + 2.5
        d.text((tx, y + h / 2 + 0.35 * size + (1.0 if caption else 0)), value, size, anchor=anchor,
               weight=weight)


def title_block(d: Doc, x: float, y: float, sp: PaddleSpec, subtitle: str, scale: str, sheet: str,
                size: str, w: float = 180.0) -> None:
    """ISO 7200-style title block, top-left corner at (x, y), 46 mm tall."""
    d.rect(x, y, w, 46, "frame")
    cell(d, x, y, w, 16, "", "")
    d.text((x + 3, y + 7.6), f"PICKLEBALL PADDLE – {sp.name}", 5.6, anchor="start", weight="bold")
    d.text((x + 3, y + 13.2), subtitle, 3.0, anchor="start")
    y2 = y + 16
    for i, (cap, val) in enumerate((("DRAWN", ISSUE["drawn"]), ("DATE", ISSUE["date"]),
                                    ("CHECKED", ""), ("APPROVED", ""))):
        cell(d, x + i * w / 4, y2, w / 4, 10, cap, val)
    y3 = y2 + 10
    cols = (("DRAWING No.", sp.drawing_no, 52), ("REV", ISSUE["rev"], 16), ("SHEET", sheet, 22),
            ("SIZE", size, 18), ("SCALE", scale, 32), ("UNITS", "mm", 40))
    xx = x
    for cap, val, cw in cols:
        cell(d, xx, y3, cw, 10, cap, val, 3.4 if cap == "DRAWING No." else 3.2,
             weight="bold" if cap == "DRAWING No." else "normal")
        xx += cw
    y4 = y3 + 10
    cell(d, x, y4, 46, 10, "PROJECTION")
    projection_symbol_first_angle(d, x + 14, y4 + 6.2, 5.0)
    cell(d, x + 46, y4, 64, 10, "MATERIAL", "SEE NOTE 9", 3.0)
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


def ga_notes(o: Outline) -> list[str]:
    sp = o.spec
    s = sp.length + sp.width
    return [
        "ALL DIMENSIONS IN MILLIMETRES. DO NOT SCALE THE DRAWING.",
        "PROFILE SYMMETRICAL ABOUT THE CENTRE LINE. ALL ARCS TANGENT TO ADJOINING EDGES.",
        f"THICKNESS {fmt(sp.thickness)} ±0.2 UNIFORM OVER BLADE AND HANDLE (CORE + FACE SKINS).",
        "UNLESS STATED: LINEAR ±0.5, ANGULAR ±0.5°. BREAK ALL SHARP EDGES.",
        "EDGE GUARD, GRIP WRAP, HANDLE BUILD-UP AND BUTT CAP NOT SHOWN.",
        f"HANDLE CORE {fmt(sp.handle_width)} × {fmt(sp.thickness)} (PERIMETER "
        f"{fmt(2 * (sp.handle_width + sp.thickness))}): BUILD UP ≈2–2.5 PER SIDE\n"
        "FOR A 4¼ in (108) GRIP CIRCUMFERENCE.",
        f"USA PICKLEBALL PADDLE LIMITS: L + W = {fmt(s)} ≤ {fmt(USAP_SUM)} (24 in),  L = {fmt(sp.length)} "
        f"≤ {fmt(USAP_LEN)} (17 in).\nEDGE GUARD AND BUTT CAP COUNT TOWARDS THESE LIMITS "
        f"(MARGIN {fmt(USAP_SUM - s)} mm).",
        f"PROFILE AREA {o.area / 100:.0f} cm² (INCL. HANDLE), PERIMETER {o.perimeter:.0f}. FULL-SIZE "
        f"TEMPLATE: SHEET 2.\nCNC CUT PROFILE: {sp.drawing_no}_profile.dxf (1:1, mm).",
        "FACE SKIN AND CORE MATERIALS TO BE SPECIFIED.",
    ]


# --------------------------------------------------------------------------- sheet 1
def ga_sheet(o: Outline) -> Doc:
    sp = o.spec
    d = Doc(420, 297, f"{sp.drawing_no} {sp.name} paddle - general arrangement")
    hatch = hatch_pattern(d)
    frame_iso(d)
    a, h, t, L = sp.width / 2, sp.handle_width / 2, sp.handle_length, sp.length
    S = 0.5
    cx, tip_y = 117.0, 40.0
    butt_y = tip_y + L * S
    fv = View(d, (cx, butt_y), S)
    P = fv.P

    # ---- front view
    d.path(fv.outline_path(o), "vis")
    fv.line((0, -9), (0, L + 9), "ctr")
    top_ref = (-o.pts["crown"][0], L) if sp.head == "square" else (0.0, L)
    # overall width / handle width
    yside = o.pts["side_hi"][1]
    d.dim_linear(P((-a, yside)), P((a, yside)), "x", tip_y - 11, fmt(sp.width))
    d.dim_linear(P((-h, 0)), P((h, 0)), "x", butt_y + 9, fmt(sp.handle_width))
    # lengths (left)
    x1, x2 = cx - a * S - 20, cx - a * S - 31
    d.dim_linear(P((-h, 0)), P((-h, t)), "y", x1, fmt(sp.handle_length))
    d.dim_linear(P((-h, t)), P(top_ref), "y", x1, fmt(sp.blade_length))
    d.dim_linear(P((-h, 0)), P(top_ref), "y", x2, fmt(sp.length))
    d.text((x1 + 2.2, P((0, t / 2))[1] + 13), "HANDLE", 2.5, rot=-90, fill=GREY)
    d.text((x1 + 2.2, P((0, t + sp.blade_length / 2))[1] + 12), "BLADE", 2.5, rot=-90, fill=GREY)

    # taper angle at the (virtual) throat vertex + radii on the right-hand side
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

    # cutting planes
    fv.section_line(280.0, -a - 15, a + 15, "A")
    fv.section_line(70.0, -h - 14, h + 14, "B")
    d.text((cx, 259), "FRONT VIEW", 3.5, weight="bold")

    # ---- side view (view from the left, placed on the right: first angle)
    sv_x = 212.0
    sv = View(d, (sv_x, butt_y), S)
    T = sp.thickness / 2
    d.poly([sv.P((-T, 0)), sv.P((T, 0)), sv.P((T, L)), sv.P((-T, L))], "vis", closed=True)
    sv.line((0, -9), (0, L + 9), "ctr")
    d.dim_linear(sv.P((-T, L)), sv.P((T, L)), "x", tip_y - 11, fmt(sp.thickness), outside=True)
    d.text((sv_x, 259), "SIDE VIEW", 3.5, weight="bold")

    # ---- sections
    ya = 120.0
    xa = 292.0
    w2 = a * S
    d.rect(xa - w2, ya - T * S, 2 * w2, sp.thickness * S, "vis", extra=f'style="fill:{hatch}"')
    d.dim_linear((xa - w2, ya - T * S), (xa + w2, ya - T * S), "x", ya - 10, fmt(sp.width))
    d.dim_linear((xa + w2, ya - T * S), (xa + w2, ya + T * S), "y", xa + w2 + 9, fmt(sp.thickness),
                 outside=True)
    d.line((xa - w2 - 6, ya), (xa + w2 + 6, ya), "ctr")
    d.text((xa, ya + 15), "SECTION A–A", 3.5, weight="bold")

    xb, yb = 375.0, 120.0
    d.rect(xb - h, yb - T, 2 * h, 2 * T, "vis", extra=f'style="fill:{hatch}"')
    d.dim_linear((xb - h, yb - T), (xb + h, yb - T), "x", yb - T - 7, fmt(sp.handle_width))
    d.dim_linear((xb + h, yb - T), (xb + h, yb + T), "y", xb + h + 8, fmt(sp.thickness))
    d.line((xb - h - 5, yb), (xb + h + 5, yb), "ctr")
    d.line((xb, yb - T - 3), (xb, yb + T + 3), "ctr")
    d.text((xb, yb + T + 11), "SECTION B–B", 3.5, weight="bold")
    d.text((xb, yb + T + 15.5), "SCALE 1:1", 2.8)

    # ---- isometric view
    draw_pictorial(d, o, ISOMETRIC, (318.0, 54.0), 0.25)
    d.text((318.0, 93.0), "ISOMETRIC VIEW", 3.5, weight="bold")
    d.text((318.0, 97.5), "SCALE 1:4", 2.8)

    # ---- notes + title block
    notes_block(d, 228.0, 160.0, ga_notes(o))
    title_block(d, 225.0, 236.0, sp, f"GENERAL ARRANGEMENT  ·  {fmt(sp.length)} × {fmt(sp.width)} "
                f"× {fmt(sp.thickness)} mm  ·  HANDLE {fmt(sp.handle_length)} × "
                f"{fmt(sp.handle_width)}", "1:2", "1 / 2", "A3")
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
    d.text((tx, yy), "Origin: centre of the butt end. Y along the paddle, X across.", 2.5, anchor="start",
           fill=GREY)
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
    d.text((tbx + 2.5, tby + 9.3), "FULL-SIZE PROFILE TEMPLATE", 2.6, anchor="start")
    cell(d, tbx, tby + 11, 44, 9, "DRAWING No.", sp.drawing_no, 3.2, weight="bold")
    cell(d, tbx + 44, tby + 11, 16, 9, "REV", ISSUE["rev"], 3.0)
    cell(d, tbx + 60, tby + 11, 20, 9, "SHEET", "2 / 2", 3.0)
    cell(d, tbx + 80, tby + 11, tbw - 80, 9, "SCALE", "1:1", 3.2, weight="bold")
    cell(d, tbx, tby + 20, 44, 9, "DATE", ISSUE["date"], 3.0)
    cell(d, tbx + 44, tby + 20, 36, 9, "DRAWN", ISSUE["drawn"], 2.8)
    cell(d, tbx + 80, tby + 20, tbw - 80, 9, "UNITS", "mm", 3.0)
    cell(d, tbx, tby + 29, tbw, 11, "", "")
    d.text((tbx + tbw / 2, tby + 33.8), "PRINT ON A3 AT 100 % / “ACTUAL SIZE” – NO FIT-TO-PAGE.",
           2.6, weight="bold")
    d.text((tbx + tbw / 2, tby + 37.6), "Verify both scale bars before cutting.", 2.5)
    return d
