"""PB-MO-004 machining blueprint of the aluminium stack mould, PB-MO-005 CNC machining diagram.

PB-MO-004 (A2, blueprint colours): the four machined faces in machine orientation (X along the plate)
at 1:3 with the G54 datum, sections across the teeth and along a tooth ramp at 2:1, the hole table, the
tooth table, tolerances, finish and material.
PB-MO-005 (A2): the process (set-ups in order), the fixture set-up with clamps, pins, bolts and G54, the
toolpaths of the four face programs coloured by tool, tool list, program list, operation sequence and
the simulation check.
"""
from __future__ import annotations

import base64
import math
from pathlib import Path

from shapely.affinity import scale as sh_scale
from shapely.affinity import translate
from shapely.geometry import Polygon, box

from . import cam_mould as CM
from .geometry import CONSTRUCTION as C
from .mould import BOTTOM, MOULD, TOP, ring, vent_span
from .sheets import GREY, cell, fill, hatches, notes_block, polygon_path, title_block
from .sheets_construction import break_line, view_label
from .sheets_mould import section_geometry
from .svgkit import Doc, fmt, frame_iso

M = MOULD
TOOL_COLOURS = {1: "#6b6b6b", 2: "#1f6fd1", 3: "#1a9c4a", 4: "#e07b00", 5: "#d1263b", 6: "#8e3fc7", 7: "#00838f",
                8: "#5d4037", 9: "#5d4037", 10: "#5d4037", 11: "#5d4037", 12: "#5d4037"}


# ------------------------------------------------------------------------------------------ blueprint colours
BP_BG, BP_GRID, BP_INK, BP_SOFT = "#17497f", "#2a5d96", "#eef5ff", "#a8c6ea"


def blueprint(svg: str) -> str:
    """Recolour a black-on-white sheet as a blueprint: white ink on blue with a 5 mm grid."""
    s = svg.replace("stroke:#000", f"stroke:{BP_INK}").replace('stroke="#000"', f'stroke="{BP_INK}"')
    s = s.replace("fill:#000", f"fill:{BP_INK}").replace('fill="#000"', f'fill="{BP_INK}"')
    s = s.replace(f'fill="{GREY}"', f'fill="{BP_SOFT}"').replace(f"stroke:{GREY}", f"stroke:{BP_SOFT}")
    s = s.replace("fill:#fff", f"fill:{BP_BG}").replace('fill="#fff"', f'fill="{BP_BG}"', 1)
    grid = (f'<pattern id="bpgrid" width="5" height="5" patternUnits="userSpaceOnUse">'
            f'<path d="M5,0 L0,0 0,5" fill="none" stroke="{BP_GRID}" stroke-width="0.15"/></pattern>')
    s = s.replace("</defs>", grid + "\n</defs>", 1)
    i = s.index(f'fill="{BP_BG}"/>') + len(f'fill="{BP_BG}"/>')
    w = s[s.index('viewBox="0 0 ') + 13:].split('"')[0].split()
    s = s[:i] + f'\n<rect x="0" y="0" width="{w[0]}" height="{w[1]}" fill="url(#bpgrid)"/>' + s[i:]
    return s


# ------------------------------------------------------------------------------------------ geometry of the faces
def faces_geometry() -> dict:
    """Machine-plan geometry of the four machined faces (shapely, mm)."""
    outlines, lay = CM.layout_cache()
    pair = (outlines[TOP], outlines[BOTTOM])
    plate = CM.to_m(CM.plate_outline(pair))
    out = {}
    for key, paddle, side, title in (("main_A", TOP, -1, "MAIN PLATE – FACE A (OP 20)"),
                                     ("main_B", BOTTOM, -1, "MAIN PLATE – FACE B (OP 30)"),
                                     ("top", TOP, +1, "TOP CLAMP PLATE (OP 20)"),
                                     ("bottom", BOTTOM, +1, "BOTTOM CLAMP PLATE (OP 20)")):
        o = outlines[paddle]
        t = CM.Teeth(o, side)
        g = dict(title=title, paddle=o.spec.name, side=side, plate=plate,
                 feet=[CM.to_m(p) for p in t.footprints()],
                 tips=[CM.to_m(p) for p in CM.cam.polygons(t.slices(CM.Z_TOP - 1e-4))],
                 inner=CM.to_m(t.inner), table=t.tooth_table(),
                 notches=[CM.to_m(CM.notch_rect(n)) for n in lay.notches],
                 bolts=[CM.pt_m(*b) for b in lay.bolts], dowels=[CM.pt_m(*d) for d in lay.dowels])
        if side < 0:
            g["pocket"] = CM.to_m(Polygon(o.polyline(0.2)))
            g["groove"] = [CM.to_m(Polygon(ring(o, M.land))), CM.to_m(Polygon(ring(o, M.land + M.groove_w)))]
            g["vents"] = [(CM.pt_m(*a), CM.pt_m(*b)) for a, b in (vent_span(o, v) for v in lay.vents)]
        out[key] = g
    return out


def _T(cx: float, cy: float, S: float):
    return lambda X, Y: (cx + X * S, cy - Y * S)


def draw_face(d: Doc, g: dict, cx: float, cy: float, S: float, ink_tips: bool = True) -> None:
    """Plan of one machined face (machine orientation: X to the right, Y up)."""
    T = _T(cx, cy, S)
    d.path(polygon_path(g["plate"], T), "vis")
    if "pocket" in g:
        d.path(polygon_path(g["pocket"], T), "vis")
        for gr in g["groove"]:
            d.path(polygon_path(gr, T), "thin")
        for (ax, ay), (bx, by) in g["vents"]:
            L = math.hypot(bx - ax, by - ay)
            nx, ny = -(by - ay) / L * M.vent_w / 2, (bx - ax) / L * M.vent_w / 2
            for sgn in (-1, 1):
                d.line(T(ax + sgn * nx, ay + sgn * ny), T(bx + sgn * nx, by + sgn * ny), "thin")
    else:
        d.path(polygon_path(g["inner"], T), "phan")              # where the part's frame ends (reference)
    for fp in g["feet"]:
        d.path(polygon_path(fp, T), "vis")
    if ink_tips:
        for tp in g["tips"]:
            d.path(polygon_path(tp, T), "xthin")
    for n in g["notches"]:
        d.path(polygon_path(n.intersection(g["plate"]), T), "thin")
    for x, y in g["bolts"]:
        d.circle(T(x, y), M.bolt_d / 2 * S, "vis")
    for x, y in g["dowels"]:
        d.circle(T(x, y), M.dowel_d / 2 * S, "vis")
        p = T(x, y)
        d.line((p[0] - 2.2, p[1]), (p[0] + 2.2, p[1]), "thin")
        d.line((p[0], p[1] - 2.2), (p[0], p[1] + 2.2), "thin")
    x0, y0, x1, y1 = g["plate"].bounds
    d.line(T(x0 - 6, 0), T(x1 + 6, 0), "ctr")
    datum(d, T(0, 0))


def datum(d: Doc, p, size: float = 3.2) -> None:
    """G54 work-offset symbol: quartered circle with axis arrows."""
    x, y = p
    d.circle((x, y), size / 2, "vis")
    d.path(f"M{x},{y} L{x + size / 2},{y} A{size / 2},{size / 2} 0 0 0 {x},{y - size / 2} Z", "thin",
           extra='style="fill:#000"')
    d.path(f"M{x},{y} L{x - size / 2},{y} A{size / 2},{size / 2} 0 0 0 {x},{y + size / 2} Z", "thin",
           extra='style="fill:#000"')
    d.text((x - 2.6, y - 2.4), "G54", 2.2, anchor="end", weight="bold")


def axes(d: Doc, p, L: float = 9.0) -> None:
    x, y = p
    d.line((x, y), (x + L, y), "vis")
    d.arrow((x + L, y), (1, 0), 2.0, 1.0)
    d.text((x + L + 1.2, y + 1.0), "X", 2.6, anchor="start", weight="bold")
    d.line((x, y), (x, y - L), "vis")
    d.arrow((x, y - L), (0, -1), 2.0, 1.0)
    d.text((x - 1.2, y - L - 0.8), "Y", 2.6, anchor="end", weight="bold")


def ordinates_x(d: Doc, T, marks: list[tuple[float, str]], y_feature: float, y_base: float, size: float = 2.2) -> None:
    """Ordinate dimensions along X from the G54 datum: a leg from the feature down to the base line."""
    for X, lab in marks:
        a, b = T(X, y_feature), T(X, y_base)
        d.line(a, b, "xthin")
        d.text((b[0] + 0.8, b[1] + 1.0), lab, size, anchor="end", rot=-90)


def table(d: Doc, x: float, y: float, widths, rows, h: float = 4.6, size: float = 2.2, head_bold: bool = True) -> float:
    yy = y
    for i, row in enumerate(rows):
        xx = x
        for w, val in zip(widths, row):
            cell(d, xx, yy, w, h, "", str(val), size=size, weight="bold" if (i == 0 and head_bold) else "normal",
                 anchor="middle" if w < 14 else "start")
            xx += w
        yy += h
    return yy


# ------------------------------------------------------------------------------------------ PB-MO-004
def blueprint_notes() -> list[str]:
    return [
        f"MATERIAL: {CM.MATERIAL}. BLANKS {fmt(CM.BLANK[2] - CM.BLANK[0])} × {fmt(CM.BLANK[3] - CM.BLANK[1])}: "
        f"MAIN PLATE {fmt(CM.STOCK_T['main'])} THICK (FACES AS SUPPLIED),\nCLAMP PLATES {fmt(CM.STOCK_T['clamp'])} "
        f"THICK (BACK AS SUPPLIED). STEP: output/mould/mould_*.step. PROGRAMS: PB-MO-005.",
        "DATUM (ALL FACES): G54 X0 ON THE PADDLE BUTT REFERENCE, Y0 ON THE CENTRE LINE, Z0 ON THE TOP OF THE STOCK. "
        "X ALONG\nTHE PLATE (HANDLE TOWARDS -X). EVERY FACE IS SYMMETRIC ABOUT Y0; FACE B IS MACHINED TURNED OVER ABOUT X.",
        "TOLERANCES UNLESS STATED: ISO 2768-mK. CAVITY DEPTH 10.00 ±0.02, TOOTH HEIGHT 8.40 ±0.02, TOOTH WIDTHS ±0.02,\n"
        "SEAT FACE TO TOOTH TIPS 8.40 ±0.02, HOLE POSITIONS ±0.02, DOWEL HOLES Ø6 H7 (REAMED).",
        "TOOTH SIDES 1.5° DRAFT EACH SIDE (WIDER AT THE ROOT), CUT BY A 1.5°/SIDE TAPERED END MILL; THE SIDES OF A "
        "TOOTH\nCUT OFF BY THE FRAME LINE ALSO GET 1.5° (≤ 0.22 OFF THE CAD AT THE TIP: THE PART'S FRAME 0.22 "
        "THICKER = MORE RELEASE).",
        "TOOTH HANDLE ENDS: 45° RAMPS (ROOT AT X150, TIP AT X158.4), BALL-NOSE FINISH, ≤ R0.25 LEFT AT THE ROOT. "
        "CAVITY\nCORNERS AT THE BUTT R3 (TOOL), NOTCH CORNERS R3. ALL OTHER EDGES SHARP AS DRAWN.",
        "SURFACES IN CONTACT WITH THE PART (CAVITY FLOOR AND WALL, TEETH, SEAT FACES): Ra 0.8 MACHINED, THEN POLISH TO\n"
        "Ra 0.4 (P800 → P1500 → POLISH) FOR RELEASE. OTHER SURFACES Ra 3.2. DEBURR 0.2 EXCEPT THE CAVITY AND TOOTH EDGES.",
        f"OVERFLOW GROOVE {fmt(M.groove_w)} × {fmt(M.groove_d)} AT {fmt(M.land)} FROM THE CAVITY EDGE; "
        f"{len(layout_vents())} VENTS {fmt(M.vent_w)} × {fmt(M.vent_d)} TO THE PLATE EDGE; "
        f"PRY NOTCHES {fmt(M.notch_w)} × {fmt(M.notch_depth)} × {fmt(M.notch_h)}\nAT BOTH PARTING FACES "
        f"(CLAMP PLATES: IN THE SEAT FACE).",
        "CHECK BEFORE USE: STACK CLOSES ON THE 2 DOWEL PINS WITH BOTH TRIAL RIB SUPPORTS (PLA PRINTS) IN PLACE; "
        "CLAMP\nPLATES SEAT FLAT (0.02 FEELER MUST NOT ENTER). MOULD USE AND CURE: PB-MO-003 (WARM CURE UP TO 120 °C).",
    ]


def layout_vents():
    return CM.layout_cache()[1].vents


def section_main(d: Doc, H_, x0: float, y0: float, S: float, y_cut: float) -> None:
    """Section A-A: the main plate across the teeth at X = y_cut, right-hand edge (paddle x 46 .. plate edge)."""
    outlines, lay = CM.layout_cache()
    g = section_geometry(outlines, y_cut)
    f = M.face
    win = box(46.0, -f - 1, g["x_plate"] + 1, f + 1)
    main = g["main"].intersection(win)

    def X(xp, z):                       # paddle x -> sheet x (Y machine = -x: drawn with -Y to the right)
        return (x0 + (xp - 46.0) * S, y0 - (z - f) * S)
    d.path(polygon_path(main, X), "vis", extra=fill(H_["metal"]) + ' fill-rule="evenodd"')
    break_line(d, X(46.0, f + 0.6), X(46.0, -f - 0.6), 1.0)
    info = g["info"][TOP]
    aw, xi = info["aw"], info["xi"]
    xp = g["x_plate"]
    # dimensions (machine values)
    d.dim_linear(X(xp, f), X(xp, -f), "y", X(xp, 0)[0] + 9, fmt(M.main))
    d.dim_linear(X(xp, f), X(xp, f - C.core_t), "y", X(xp, 0)[0] + 3.5, fmt(C.core_t))
    d.dim_linear(X(xp, -f), X(xp, -f + C.core_t), "y", X(xp, 0)[0] + 3.5, fmt(C.core_t))
    teeth = [iv for iv in sorted(CM.Teeth(outlines[TOP], -1).intervals(CM.Z_FLOOR + 1e-4))
             if iv[0] > 46 and iv[1] < xi + 1e-6]                      # the real teeth: inside the frame
    tips = sorted(CM.Teeth(outlines[TOP], -1).intervals(CM.Z_TOP - 1e-4))
    a0, b0 = teeth[-1]
    a1, b1 = min(tips, key=lambda iv: abs(iv[0] + iv[1] - a0 - b0))
    zf, zt = f - C.core_t, f - C.core_t + M.teeth
    d.dim_linear(X(a0, zf), X(b0, zf), "x", X(0, zf)[1] + 4.5, f"{b0 - a0:.2f}")
    d.dim_linear(X(a1, zt), X(b1, zt), "x", X(0, f)[1] - 4.0, f"{b1 - a1:.2f}")
    a2, b2 = teeth[-2]
    d.dim_linear(X(a0 - 1.0, zf), X(a0 - 1.0, zt), "y", X(a0, 0)[0] - 4.0, fmt(M.teeth))
    d.dim_linear(X((a2 + b2) / 2, zt), X((a0 + b0) / 2, zt), "x", X(0, f)[1] - 9.0, fmt(C.rib_pitch))
    d.leader_note(X(a2 + 0.06, zf + 4.0), (X(a2, 0)[0] - 14, X(0, f)[1] - 6.0), "1.5° DRAFT EACH SIDE", 2.2)
    d.leader_note(X((info["g0"] + info["g1"]) / 2, f - M.groove_d / 2), (X(xp, 0)[0] + 4, X(0, f)[1] - 14.0),
                  f"GROOVE {fmt(M.groove_w)}×{fmt(M.groove_d)}", 2.2)
    d.dim_linear(X(xi, zf), X(aw, zf), "x", X(0, zf)[1] + 4.5, fmt(C.frame_w))
    d.text(X((aw + xp) / 2, -2.0), "WEB", 2.2, fill=GREY)
    d.text(X(52, f - C.core_t - 3.0), "FACE A CAVITY (ELONGATED)", 2.0, anchor="start", fill=GREY)
    d.text(X(52, -f + C.core_t + 1.5), "FACE B CAVITY (HYBRID)", 2.0, anchor="start", fill=GREY)


def section_ramp(d: Doc, H_, x0: float, y0: float, S: float) -> None:
    """Section B-B along a tooth of face A through its 45 deg ramp (machine X 138 .. 176), top 20 mm."""
    zf, zt = CM.Z_FLOOR, CM.Z_TOP
    Xa, Xb = 138.0, 176.0
    y_r0, y_r1 = CM.Teeth.y_ramp(zf), CM.Teeth.y_ramp(zt)
    prof = Polygon([(Xa, -20.0), (Xa, zf), (y_r0, zf), (y_r1, zt), (Xb, zt), (Xb, -20.0)])

    def P(X, Z):
        return (x0 + (X - Xa) * S, y0 - Z * S)
    d.path(polygon_path(prof, P), "vis", extra=fill(H_["metal"]))
    break_line(d, P(Xa, -20.6), P(Xb, -20.6), 1.0)
    d.line(P(Xa - 2, 0), P(Xb + 2, 0), "phan")
    d.text(P(Xa - 1, 0.6), "Z0 (FACE)", 2.0, anchor="start", fill=GREY)
    d.dim_linear(P(Xa, 0), P(Xa, zf), "y", P(Xa, 0)[0] - 5, fmt(-zf))
    d.leader_note(P(Xb - 2.0, zt), (P(Xb, 0)[0] + 4, P(0, zt)[1] + 9), f"TOOTH TOP Z{fmt(zt, 1)}", 2.2)
    d.dim_linear(P(y_r0, zf), P(y_r1, zf), "x", P(0, zf)[1] + 5, fmt(y_r1 - y_r0, 1))
    d.text((P(y_r0, zf)[0], P(0, zf)[1] + 11.0), f"X{fmt(y_r0)}", 2.2)
    d.text((P(y_r1, zf)[0] + 3, P(0, zf)[1] + 11.0), f"X{fmt(y_r1, 1)}", 2.2)
    d.leader_note(P((y_r0 + y_r1) / 2, (zf + zt) / 2), (P(y_r0, 0)[0] - 6, P(0, zt)[1] - 4), "45°", 2.4)


def section_clamp(d: Doc, H_, x0: float, y0: float, S: float, y_cut: float) -> None:
    """Section C-C: top clamp plate across the teeth, teeth up as machined (Z0 = top of the 20 mm blank)."""
    outlines, _ = CM.layout_cache()
    g = section_geometry(outlines, y_cut)
    f, c = M.face, M.clamp
    top = sh_scale(g["top"], 1, -1, origin=(0, 0))               # turned over: teeth up
    top = translate(top, 0, f + c - 5.0 + 5.0)                    # z_world -> -z + (f + c): back face at 0
    win = box(46.0, -1, g["x_plate"] + 1, 30)
    top = top.intersection(win)
    Zs = CM.STOCK_T["clamp"]

    def P(xp, z):                      # z above the back face -> machine Z = z - 20
        return (x0 + (xp - 46.0) * S, y0 - (z - Zs) * S)
    d.path(polygon_path(top, P), "vis", extra=fill(H_["metal"]) + ' fill-rule="evenodd"')
    break_line(d, P(46.0, -0.6), P(46.0, Zs - 1.0), 1.0)
    d.line(P(46, Zs), P(g["x_plate"] + 2, Zs), "phan")
    d.text(P(47, Zs + 0.8), "Z0 = TOP OF THE 20 BLANK", 2.0, anchor="start", fill=GREY)
    xp = g["x_plate"]
    d.dim_linear(P(xp, 0), P(xp, c), "y", P(xp, 0)[0] + 4, fmt(c))
    d.dim_linear(P(xp, 0), P(xp, c + M.teeth), "y", P(xp, 0)[0] + 10, fmt(c + M.teeth, 1))
    xi = g["info"][TOP]["xi"]
    teeth = [iv for iv in sorted(CM.Teeth(outlines[TOP], +1).intervals(CM.Z_FLOOR + 1e-4))
             if iv[0] > 46 and iv[1] < xi + 1e-6]
    a0, b0 = teeth[-1]
    d.dim_linear(P(b0 + 1, c), P(b0 + 1, c + M.teeth), "y", P(b0, 0)[0] + 5.0, fmt(M.teeth))
    d.dim_linear(P(a0, c), P(b0, c), "x", P(0, 0)[1] + 4.0, f"{b0 - a0:.2f}")
    d.text(P((b0 + xp) / 2, c + 2.0), "SEAT FACE", 2.0, fill=GREY)


def machining_blueprint(report: dict | None = None) -> Doc:
    """PB-MO-004, A2, blueprint colours (the caller recolours the SVG with blueprint())."""
    d = Doc(594, 420, f"{CM.BLUEPRINT_NO} stack mould machining blueprint")
    H_ = hatches(d)
    frame_iso(d)
    G = faces_geometry()
    S = 1 / 3
    X0, X1 = -17.0, 412.0
    pos = {"main_A": (40.0, 30.0), "main_B": (222.0, 30.0), "top": (40.0, 148.0), "bottom": (222.0, 148.0)}
    for key, (sx, sy) in pos.items():
        g = G[key]
        cx, cy = sx - X0 * S, sy + 122.0 * S
        T = _T(cx, cy, S)
        draw_face(d, g, cx, cy, S)
        marks = [(X0, fmt(X0)), (0.0, "0"), (C.solid_to, fmt(C.solid_to))]
        if "pocket" in g:
            marks += [(5.0, "5"), (390.0, "390")]
        marks += [(X1, fmt(X1)), (g["dowels"][0][0], f"{g['dowels'][0][0]:.2f}")]
        ordinates_x(d, T, marks, -122.0, -131.0, 2.0)
        for Y, lab in ((122.0, "+122"), (-122.0, "−122"), (g["dowels"][0][1], f"{g['dowels'][0][1]:+.0f}"),
                       (g["dowels"][1][1], f"{g['dowels'][1][1]:+.0f}")):
            a, b = T(X0, Y), T(X0 - 8.0, Y)
            d.line(a, b, "xthin")
            d.text((b[0] - 0.6, b[1] + 0.8), lab.replace("+-", "−"), 2.0, anchor="end")
        sub = (f"SCALE 1:3 · {g['paddle']} CAVITY {fmt(C.core_t)}.00 DEEP, {len(g['feet'])} TEETH {M.teeth:.2f} HIGH"
               if "pocket" in g else
               f"SCALE 1:3 · TEETH SIDE UP · SEAT FACE Z−{fmt(C.core_t)}, {len(g['feet'])} TEETH {M.teeth:.2f} HIGH "
               f"({g['paddle']})")
        view_label(d, sx + (X1 - X0) * S / 2, sy + 244 * S + 21, g["title"], sub)
    axes(d, (25.0 + 8.0, 138.0))
    d.text((33.0, 145.0), "MACHINE AXES", 2.0, anchor="start", fill=GREY)
    T = _T(pos["main_A"][0] - X0 * S, pos["main_A"][1] + 122 * S, S)
    d.leader_note(T(*CM.pt_m(10.6, 300.0)), (T(300, 140)[0] + 8, T(300, 140)[1] - 1), "TOOTH (FOOTPRINT AT THE ROOT)",
                  2.0, dot=True, arrow=False)
    dw = max(G["main_A"]["dowels"], key=lambda q: q[1])
    d.leader_note(T(*dw), (T(332, 140)[0] + 20, T(332, 140)[1] + 4), f"2 × Ø{fmt(M.dowel_d)} H7 THRU", 2.0)
    T = _T(pos["top"][0] - X0 * S, pos["top"][1] + 122 * S, S)
    d.leader_note(T(*CM.pt_m(-95.0, 300.0)), (T(300, 140)[0] + 8, T(300, 140)[1] - 1),
                  "FRAME LINE OF THE PART (REF.)", 2.0, dot=True, arrow=False)

    # sections, right-hand column
    S2 = 2.0
    y_cut = 250.0
    x_sec = 400.0
    section_main(d, H_, x_sec, 34.0, S2, y_cut)
    view_label(d, x_sec + 70, 112.0, "SECTION A–A", f"SCALE 2:1 · MAIN PLATE ACROSS THE TEETH AT X{fmt(y_cut)}")
    section_ramp(d, H_, x_sec + 2, 150.0, S2)
    view_label(d, x_sec + 38, 207.0, "SECTION B–B", "SCALE 2:1 · ALONG A TOOTH: THE 45° RAMP")
    section_clamp(d, H_, x_sec, 238.0, S2, y_cut)
    view_label(d, x_sec + 70, 300.0, "SECTION C–C", f"SCALE 2:1 · CLAMP PLATE ACROSS THE TEETH AT X{fmt(y_cut)}")
    for key in ("main_A", "top"):
        sx, sy = pos[key]
        T = _T(sx - X0 * S, sy + 122 * S, S)
        a, b = T(y_cut, 126), T(y_cut, -126)
        d.line(a, b, "ctr")
        lab = "A" if key == "main_A" else "C"
        for p in (a, b):
            d.text((p[0] + 1.5, p[1] + (-0.8 if p is a else 3.0)), lab, 3.2, anchor="start", weight="bold")
    T = _T(pos["main_A"][0] - X0 * S, pos["main_A"][1] + 122 * S, S)
    d.line(T(135, -10.6), T(180, -10.6), "ctr")
    d.text((T(135, -10.6)[0] - 1.0, T(135, -10.6)[1] + 1.0), "B", 3.2, anchor="end", weight="bold")

    # hole table
    _, lay = CM.layout_cache()
    pts = sorted({(round(CM.pt_m(x, y)[0], 2), round(abs(CM.pt_m(x, y)[1]), 2)) for x, y in lay.bolts})
    rows = [("HOLE", "X", "Y", "SIZE", "QTY")]
    for k, (X, Y) in enumerate(pts, 1):
        rows.append((f"B{k}", f"{X:.2f}", "0" if Y == 0 else f"±{Y:.2f}", f"Ø{fmt(M.bolt_d)} THRU", 1 if Y == 0 else 2))
    dX, dY = CM.pt_m(*lay.dowels[0])
    rows.append(("D1", f"{dX:.2f}", f"±{abs(dY):.2f}", f"Ø{fmt(M.dowel_d)} H7 THRU", 2))
    tx, ty = 30.0, 272.0
    d.text((tx, ty - 2.5), "HOLE TABLE – ALL THREE PLATES (G54)", 3.0, anchor="start", weight="bold")
    yy = table(d, tx, ty, (13, 22, 22, 30, 11), rows, 4.4, 2.2)
    d.text((tx, yy + 4.0), "B: M6 STACK BOLTS (SPOT 0.4×45°). D: DOWEL PINS Ø6 h6, GROUND.", 2.0, anchor="start")

    # tooth table
    rows = [("FACE", "TOOTH Y", "ROOT W", "TIP W", "X FROM (EL / HY)", "X TO (EL / HY)")]
    for side, faces, label in ((-1, ("main_A", "main_B"), "MAIN A / B"), (+1, ("top", "bottom"), "CLAMPS")):
        ta, tb = G[faces[0]]["table"], G[faces[1]]["table"]
        for ra in ta:
            yc = (ra["x_base"][0] + ra["x_base"][1]) / 2
            if yc < -1e-6:
                continue
            rb = min(tb, key=lambda r: abs((r["x_base"][0] + r["x_base"][1]) / 2 - yc))
            ys = "0" if abs(yc) < 1e-6 else f"±{yc:.1f}"
            wb = rb["x_base"][1] - rb["x_base"][0]
            root = f"{ra['x_base'][1] - ra['x_base'][0]:.2f}" + ("" if abs(wb - (ra['x_base'][1] - ra['x_base'][0])) < 0.01
                                                                    else f" / {wb:.2f}")
            rows.append((label, ys, root, f"{ra['x_tip'][1] - ra['x_tip'][0]:.2f}",
                         f"{ra['y_from']:.1f} / {rb['y_from']:.1f}", f"{ra['y_to']:.1f} / {rb['y_to']:.1f}"))
            label = ""
    tx2 = 135.0
    d.text((tx2, ty - 2.5), "TOOTH TABLE (MACHINE COORDINATES)", 3.0, anchor="start", weight="bold")
    yy2 = table(d, tx2, ty, (19, 16, 22, 14, 32, 32), rows, 4.4, 2.2)
    d.text((tx2, yy2 + 4.0), "ROOT W AT THE FLOOR / SEAT, TIP W 8.40 ABOVE; BOTH SIDES 1.5°. RAMP 45° AT THE X-FROM END,",
           2.0, anchor="start")
    d.text((tx2, yy2 + 7.0), "WHERE THE TOOTH ROOT STARTS AT X150 (ELSE THE FRAME LINE CUTS IT). HY CLAMP: OUTER TEETH CUT TO 4.83.",
           2.0, anchor="start")

    notes_block(d, 30.0, 336.0, blueprint_notes(), size=2.15, lead=3.05)
    title_block(d, 399.0, 359.0, None, f"ALUMINIUM MAIN PLATE {fmt(M.main)} + 2 CLAMP PLATES (BLANK 20) · "
                f"MACHINING DATA FOR PB-MO-003 · G54 / 2 DOWELS", "1:3, 2:1", "1 / 1", "A2",
                title="STACK MOULD – MACHINING BLUEPRINT", drawing_no=CM.BLUEPRINT_NO, material="AL 6061-T651 / CAST PLATE")
    return d


# ------------------------------------------------------------------------------------------ PB-MO-005
PROCESS = [("OP 00", "FIXTURE PLATE", "O0100", "tap the bolt pattern, ream\nthe dowels, relief groove"),
           ("OP 10", "DRILL 3 BLANKS", "O0110 / O0210", "on the fixture, no pins:\n18 bolt + 2 dowel holes"),
           ("PINS", "FIT 2 DOWEL PINS", "manual", "press Ø6 m6 × 20 into\nthe fixture, 8 proud"),
           ("OP 20", "MAIN PLATE FACE A", "O0120", "on the pins, 18 bolts:\nElongated cavity"),
           ("OP 30", "MAIN PLATE FACE B", "O0130", "turned over about X:\nHybrid cavity + profile"),
           ("OP 20", "TOP CLAMP PLATE", "O0220", "teeth, ramps, seat;\nM0: bolts in, profile"),
           ("OP 20", "BOTTOM CLAMP PLATE", "O0320", "teeth, ramps, seat;\nM0: bolts in, profile")]


def process_strip(d: Doc, x0: float, y0: float, w: float = 70.0, h: float = 24.0, gap: float = 8.6) -> None:
    for k, (op, title, prog, txt) in enumerate(PROCESS):
        x = x0 + k * (w + gap)
        d.rect(x, y0, w, h, "vis")
        d.rect(x, y0, 17, 7, "thin", extra='style="fill:#000"')
        d.text((x + 8.5, y0 + 5.0), op, 2.6, weight="bold", fill="#fff")
        d.text((x + 20, y0 + 5.0), title, 2.6, anchor="start", weight="bold")
        d.text((x + w - 2, y0 + 11.0), prog, 2.2, anchor="end", fill=GREY)
        for i, ln in enumerate(txt.split("\n")):
            d.text((x + 3, y0 + 15.5 + i * 3.6), ln.upper(), 2.2, anchor="start")
        if k < len(PROCESS) - 1:
            a, b = (x + w + 1.0, y0 + h / 2), (x + w + gap - 1.0, y0 + h / 2)
            d.line(a, b, "vis")
            d.arrow(b, (1, 0), 2.2, 1.2)


def setup_plan(d: Doc, cx: float, cy: float, S: float) -> None:
    """The mould blank on the fixture plate: pins, bolts, toe clamps, relief groove, G54."""
    outlines, lay = CM.layout_cache()
    pair = (outlines[TOP], outlines[BOTTOM])
    T = _T(cx, cy, S)
    fx0, fy0, fx1, fy1 = CM.FIXTURE
    d.path(polygon_path(box(fx0, fy0, fx1, fy1), T), "vis", extra='style="fill:#ececec"')
    bx0, by0, bx1, by1 = CM.BLANK
    d.path(polygon_path(box(bx0, by0, bx1, by1), T), "phan")
    plate = CM.to_m(CM.plate_outline(pair))
    for off in (CM.TOOLS[1].r - 2.0 - 5.0, CM.TOOLS[1].r + CM.STOCK_WALL + 2.0 + 5.0):
        d.path(polygon_path(plate.buffer(off, join_style="round"), T), "xthin")
    d.path(polygon_path(plate, T), "vis", extra='style="fill:#fff"')
    d.path(polygon_path(CM.to_m(Polygon(outlines[TOP].polyline(0.5))), T), "thin")
    for x, y in lay.bolts:
        p = T(*CM.pt_m(x, y))
        d.circle(p, CM.BOLT_HEAD["r"] * S, "vis")
        d.circle(p, M.bolt_d / 2 * S * 0.6, "thin")
    for x, y in lay.dowels:
        d.circle(T(*CM.pt_m(x, y)), M.dowel_d / 2 * S + 0.3, "thin", extra='style="fill:#000"')
    for (x, y), (sx, sy) in zip(CM.CLAMPS, CM.STUDS):
        ang = math.atan2(sy - y, sx - x)
        L, W = 28.0, 12.0
        c, s_ = math.cos(ang), math.sin(ang)
        pts = [(x - c * 4 + s_ * W / 2, y - s_ * 4 - c * W / 2), (x + c * (L - 4) + s_ * W / 2, y + s_ * (L - 4) - c * W / 2),
               (x + c * (L - 4) - s_ * W / 2, y + s_ * (L - 4) + c * W / 2), (x - c * 4 - s_ * W / 2, y - s_ * 4 + c * W / 2)]
        d.poly([T(*q) for q in pts], "vis", closed=True, extra='style="fill:#bbb"')
        d.circle(T(sx, sy), 2.4 * S * 2, "thin", extra='style="fill:#000"')
    d.line(T(fx0 - 4, 0), T(fx1 + 4, 0), "ctr")
    datum(d, T(0, 0), 3.0)
    axes(d, (T(fx0, fy0)[0] + 3, T(fx0, fy0)[1] - 3), 7.0)
    d.text((T((fx0 + fx1) / 2, fy0)[0], T(0, fy0)[1] + 5.0), "FRONT (OPERATOR, -Y)", 2.2, fill=GREY)
    d.dim_linear(T(fx0, fy1), T(fx1, fy1), "x", T(0, fy1)[1] - 4.0, fmt(fx1 - fx0))
    d.dim_linear(T(fx1, fy0), T(fx1, fy1), "y", T(fx1, 0)[0] + 4.0, fmt(fy1 - fy0))
    d.dim_linear(T(fx0, fy0), T(0, fy0), "x", T(0, fy0)[1] + 9.0, fmt(-fx0))
    dX, dY = CM.pt_m(*lay.dowels[0])
    d.leader_note(T(dX, abs(dY)), (T(fx1, 0)[0] + 9, T(0, 60)[1]), f"2 PINS X{dX:.2f} Y±{abs(dY):.0f}", 2.1)
    d.leader_note(T(*CM.CLAMPS[2]), (T(fx1, 0)[0] + 9, T(0, 150)[1] - 2), "TOE CLAMPS ON THE WASTE", 2.1)
    bolt = min((CM.pt_m(*b) for b in lay.bolts), key=lambda q: (q[1], -q[0]))
    d.leader_note(T(*bolt), (T(250, fy0)[0], T(0, fy0)[1] + 9.0), "18 × M6 SHCS (FACE PROGRAMS)", 2.1)


def setup_section(d: Doc, x0: float, y0: float, S: float) -> None:
    """Schematic section through a dowel pin and a bolt (1:2): table, fixture, plate, pin, bolt, clamp, Z0."""
    def P(u, z):
        return (x0 + u * S, y0 - z * S)
    FT, PT = CM.FIXTURE_T, CM.STOCK_T["main"]
    d.path(polygon_path(box(-6, -FT - 6, 70, -FT), P), "thin", extra='style="fill:#ddd"')
    d.text(P(-4, -FT - 3.6), "MACHINE TABLE", 2.0, anchor="start", fill=GREY)
    fixture = box(0, -FT, 66, 0).difference(box(40 - 2.5, -18, 40 + 2.5, 0)).difference(box(40 - 4, -4, 40 + 4, 0))
    fixture = fixture.difference(box(14 - 3, -12, 14 + 3, 0))
    plate = box(0, 0, 58, PT).difference(box(14 - 3, 0, 14 + 3, PT)).difference(box(40 - 3.3, 0, 40 + 3.3, PT))
    plate = plate.difference(box(0, PT - 10, 6, PT))
    d.path(polygon_path(fixture, P), "vis", extra='style="fill:#cfcfcf"')
    d.path(polygon_path(plate, P), "vis", extra='style="fill:#f4f4f4"')
    d.path(polygon_path(box(14 - 3, -12, 14 + 3, 8), P), "vis", extra='style="fill:#000"')         # dowel pin
    d.path(polygon_path(box(40 - 3, -15, 40 + 3, PT), P), "thin", extra='style="fill:#999"')       # bolt shank
    d.path(polygon_path(box(40 - 5, PT, 40 + 5, PT + 6), P), "vis", extra='style="fill:#999"')     # head
    d.path(polygon_path(box(48, PT, 76, PT + 7), P), "vis", extra='style="fill:#bbb"')             # toe clamp
    d.line(P(-8, 0), P(80, 0), "xthin")
    d.line(P(-8, PT), P(84, PT), "phan")
    d.text(P(85, PT - 1.0), "Z0 = TOP OF STOCK", 2.2, anchor="start", weight="bold")
    d.dim_linear(P(66, -FT), P(66, 0), "y", P(66, 0)[0] + 6, fmt(FT))
    d.dim_linear(P(58, 0), P(58, PT), "y", P(58, 0)[0] + 3, fmt(PT))
    d.leader_note(P(14, -2), (P(30, -FT - 11)[0], P(0, -FT - 11)[1]), "DOWEL PIN Ø6 m6, PRESSED IN THE FIXTURE", 2.1)
    d.leader_note(P(40, PT + 6), (P(30, PT + 18)[0] + 18, P(0, PT + 18)[1]), "M6 SHCS INTO THE FIXTURE", 2.1)
    d.leader_note(P(40, -2), (P(70, -FT + 6)[0] + 14, P(0, -FT + 6)[1]), "Ø8 × 4 DRILL RELIEF", 2.1)
    d.text(P(2, PT - 5), "CAVITY", 2.0, anchor="start", fill=GREY)


def toolpath_plot(d: Doc, ops: list, plate, cx: float, cy: float, S: float, title: str, sub: str) -> None:
    T = _T(cx, cy, S)
    d.path(polygon_path(plate, T), "thin", extra='style="fill:#fafafa"')
    for op in ops:
        col = TOOL_COLOURS.get(op["tool"], "#000")
        sw = 0.08 if op["tool"] in (1, 2, 3) else 0.12
        for ln in op["lines"]:
            pts = " ".join(f"{cx + x * S:.2f},{cy - y * S:.2f}" for x, y, _ in ln)
            d.add(f'<polyline points="{pts}" fill="none" stroke="{col}" stroke-width="{sw}" stroke-linejoin="round"/>')
    datum(d, T(0, 0), 2.4)
    x0, y0, x1, y1 = plate.bounds
    view_label(d, cx + (x0 + x1) / 2 * S, cy - y0 * S + 9.0, title, sub)


def cnc_notes(report: dict | None) -> list[str]:
    return [
        "MACHINE: 3-AXIS VMC, X ≥ 500, Y ≥ 300 TRAVEL, 10 000 rpm, FLOOD COOLANT (ISO PROGRAMS, output/cnc/iso). "
        "ROUTER WITH A 24k\nSPINDLE: output/cnc/generic, ONE FILE PER TOOL, MIST / AIR BLAST. FEEDS ARE STARTING VALUES "
        "– PROVE THEM ON SCRAP.",
        "G54: PROBE THE 2 DOWEL PINS; X0 Y0 LIES 332.17 IN -X FROM THEIR MID-POINT, ON THEIR CENTRE LINE. Z0 ON THE "
        "STOCK TOP.\nTOOL LENGTHS IN H1-H12 (ISO). GENERIC FILES: TOUCH EACH TOOL OFF AT Z0 BEFORE ITS FILE.",
        "CLEARANCE Z30, LINKS AT Z3 (Z12 WHERE A LINK PASSES A BOLT HEAD). MINIMUM STICK-OUTS IN THE TOOL LIST "
        "CLEAR THE BOLT\nHEADS AND CLAMPS. KEEP THE TOE CLAMPS ON THE MARKED WASTE ZONES; NOTHING ELSE MAY STAND ON "
        "THE BLANK.",
        "OP 30 AND THE CLAMP PROFILES CUT THROUGH: THE WASTE STAYS UNDER THE TOE CLAMPS, THE PLATE ON ITS BOLTS. "
        "CLAMP PLATES:\nM0 BEFORE THE PROFILE – FIT THE 18 BOLTS (M6 × 25) THROUGH THE FINISHED FLANGE.",
        "FIXTURE (BLIND HOLES, IT LIES ON THE TABLE): TAP 18 × M6 AND 6 × M10, 15 DEEP, BY HAND OR RIGID TAP; "
        "PINS Ø6 × 20 PRESSED\n12 DEEP. THE T2 RELIEF BORES PLUNGE 4 mm BY DESIGN. THE FIXTURE STAYS ON THE TABLE FOR "
        "ALL SET-UPS.",
        "SIMULATION (tools/verify_cnc.py): EVERY PROGRAM RUN ON A 0.25 mm STOCK MODEL AGAINST THE MOULD STLs – "
        "NO RAPID INTO\nSTOCK, NO FLUTE OVERRUN, NO OBSTACLE HIT; DEVIATIONS ONLY WHERE NOTED IN THE CHECK TABLE.",
        "AFTER MACHINING: DEBURR, POLISH THE CAVITIES AND TEETH (PB-MO-004 NOTE 6), DRY-FIT THE STACK ON THE 2 PINS "
        "WITH THE\nTRIAL RIB SUPPORTS, THEN SEAL AND WAX AS PB-MO-003.",
    ]


def cnc_diagram(report: dict | None, toolpaths: dict | None, verify: dict | None) -> Doc:
    """PB-MO-005, A2: process, set-up, toolpaths, tools, programs, simulation check."""
    d = Doc(594, 420, f"{CM.DIAGRAM_NO} stack mould CNC machining diagram")
    frame_iso(d)
    outlines, lay = CM.layout_cache()
    plate = CM.to_m(CM.plate_outline((outlines[TOP], outlines[BOTTOM])))
    d.text((32.0, 25.5), "PROCESS", 3.2, anchor="start", weight="bold")
    process_strip(d, 32.0, 28.0)

    # set-up
    d.text((32.0, 64.0), "SET-UP ON THE FIXTURE PLATE (SCALE 1:4)", 3.2, anchor="start", weight="bold")
    S4 = 0.25
    setup_plan(d, 32.0 + 6 - CM.FIXTURE[0] * S4, 70.0 + CM.FIXTURE[3] * S4 + 4, S4)
    d.text((214.0, 64.0), "SECTION THROUGH PIN AND BOLT (1:1, SCHEMATIC)", 3.2, anchor="start", weight="bold")
    setup_section(d, 226.0, 120.0, 1.0)

    # toolpaths, 1:4
    d.text((350.0, 64.0), "TOOLPATHS (SCALE 1:4, COLOUR = TOOL)", 3.2, anchor="start", weight="bold")
    keys = [("OP20_main_plate_face_A_elongated", "O0120 FACE A"), ("OP30_main_plate_face_B_hybrid", "O0130 FACE B"),
            ("OP20_top_clamp_plate", "O0220 TOP CLAMP"), ("OP20_bottom_clamp_plate", "O0320 BOTTOM CLAMP")]
    progs = {p["key"]: p for p in (report or {}).get("profiles", {}).get("vmc", {}).get("programs", [])}
    rprogs = {p["key"]: p for p in (report or {}).get("profiles", {}).get("router", {}).get("programs", [])}
    for k, (key, title) in enumerate(keys):
        col, row = k % 2, k // 2
        cx = 352.0 + col * 116.0 + 17.0 * S4
        cy = 74.0 + row * 86.0 + 122.0 * S4
        sub = f"VMC {progs[key]['minutes']:.0f} MIN" if key in progs else ""
        if key in rprogs:
            sub += f" · ROUTER {rprogs[key]['minutes'] / 60:.1f} h"
        toolpath_plot(d, (toolpaths or {}).get(key, []), plate, cx, cy, S4, title, sub)
    lx, ly = 352.0, 239.0
    used = [1, 2, 3, 4, 5, 6]
    for i, n in enumerate(used):
        x = lx + i * 37.0
        d.line((x, ly), (x + 7, ly), extra=f'style="stroke:{TOOL_COLOURS[n]};stroke-width:1.2"')
        d.text((x + 9, ly + 1.0), f"T{n} {CM.TOOLS[n].kind.upper()} Ø{fmt(CM.TOOLS[n].d)}", 2.2, anchor="start")

    # tool list
    K, R = CM.CUTS["vmc"], CM.CUTS["router"]
    use = {1: ("rough_clamp", "CLAMP PLATES CLEARING, PROFILES, FIXTURE RELIEF"), 2: ("rough", "CAVITY ROUGHING"),
           3: ("floor", "FLOORS, SEAT FACES, CAVITY WALL, NOTCHES"), 4: ("taper", "TOOTH SIDES 1.5° (ONE PASS)"),
           5: ("ball", "45° TOOTH RAMPS (SEMI + FINISH)"), 6: ("groove", "OVERFLOW GROOVES, VENTS"),
           7: ("spot", "SPOT / CHAMFER ALL HOLES"), 8: ("drill66", "18 BOLT HOLES THRU"),
           9: ("drill58", "DOWEL PILOTS"), 10: ("ream", "DOWEL HOLES Ø6 H7"), 11: ("drill50", "FIXTURE M6 TAP DRILL"),
           12: ("drill85", "FIXTURE M10 TAP DRILL")}
    rows = [("T", "TOOL", "STICK-OUT ≥", "VMC S / F", "ROUTER S / F", "USE")]
    for n, t in CM.TOOLS.items():
        u, txt = use[n]
        fv = K[u].feed or K[u].plunge
        fr = R[u].feed or R[u].plunge
        desc = t.desc.split(" - ")[0]
        rows.append((f"T{n}", desc[:48], f"{t.stickout:g}" if t.stickout else "–", f"{K[u].rpm} / {fv:g}",
                     f"{R[u].rpm} / {fr:g}", txt))
    ty = 186.0
    d.text((32.0, ty - 2.5), "TOOL LIST (H = T; STEP-DOWN / STEP-OVER IN THE PROGRAM HEADERS)", 3.0, anchor="start",
           weight="bold")
    table(d, 32.0, ty, (9, 92, 18, 26, 26, 82), rows, 4.4, 2.05)

    # programs
    rows = [("PROGRAM", "SET-UP", "TOOLS", "VMC", "ROUTER")]
    tot_v = tot_r = 0.0
    for key, p in progs.items():
        r = rprogs.get(key)
        rows.append((f"O{p['number']:04d}", p["title"][:44], " ".join(f"T{n}" for n in p["tools"]), f"{p['minutes']:.0f} min",
                     f"{r['minutes'] / 60:.1f} h" if r else "–"))
        tot_v += p["minutes"] * (2 if "drill" in key and "clamp" in key else 1)
        tot_r += (r["minutes"] if r else 0) * (2 if "drill" in key and "clamp" in key else 1)
    rows.append(("TOTAL", "(O0210 RUNS TWICE)", "", f"{tot_v / 60:.1f} h", f"{tot_r / 60:.1f} h"))
    py = 255.0
    d.text((32.0, py - 2.5), "PROGRAMS (output/cnc/iso/O*.nc · output/cnc/generic/<program>/NN_Tn_*.nc)", 3.0,
           anchor="start", weight="bold")
    table(d, 32.0, py, (18, 82, 52, 18, 18), rows, 4.4, 2.1)

    # simulation check
    vy = 255.0
    d.text((228.0, vy - 2.5), "SIMULATION CHECK (0.25 mm STOCK MODEL vs MOULD STL)", 3.0, anchor="start", weight="bold")
    rows = [("FACE", "MOVES", "EVENTS", "GOUGE", "LEFT", "BY DESIGN (LARGEST)")]
    iso = (verify or {}).get("posts", {}).get("iso", {})
    names = {"main_A": "MAIN A", "main_B": "MAIN B", "top_clamp": "TOP CLAMP", "bottom_clamp": "BOTTOM CLAMP"}
    for k, nm in names.items():
        st = iso.get(k)
        if not st:
            continue
        main = k.startswith("main")
        exp = (f"R3 CORNERS {st.get('max_leftover_expected', 0):.1f} DEEP" +
               (f", HOLE CHAMFERS {st.get('max_gouge_expected', 0):.2f}" if main and st.get("max_gouge_expected", 0) > 0.03
                else ""))
        rows.append((nm, f"{st['moves']}", f"{len(st['events'])}", f"{st.get('max_gouge_other', st['max_gouge']):.2f}",
                     f"{st.get('max_leftover_other', st['max_leftover']):.2f}", exp))
    if "fixture" in iso:
        rows.append(("FIXTURE", "–", f"{len(iso['fixture']['events'])}", "–", "–", "T2 RELIEF PLUNGES (BY DESIGN)"))
    table(d, 228.0, vy, (24, 16, 15, 14, 12, 82), rows, 4.4, 2.1)
    d.text((228.0, vy + len(rows) * 4.4 + 4.0), "GOUGE / LEFT: LARGEST DEVIATION FROM THE CAD OUTSIDE THE BY-DESIGN "
           "FEATURES (mm, TOLERANCE ±0.03 AT 0.25 mm CELLS);", 2.0, anchor="start")
    d.text((228.0, vy + len(rows) * 4.4 + 7.0), "R3 = TOOL RADIUS IN THE CAVITY CORNERS AT THE BUTT AND IN THE NOTCH "
           "CORNERS; CHAMFERS 0.4 × 45° ON THE UNMACHINED PARTING FACE.", 2.0, anchor="start")
    img = Path(__file__).resolve().parent.parent / "output" / "cnc" / "sim_main_A.png"
    if img.exists():
        from PIL import Image
        wpx, hpx = Image.open(img).size
        W = 124.0
        H = W * hpx / wpx
        x_i, y_i = 455.0, 352.0 - H
        b64 = base64.b64encode(img.read_bytes()).decode()
        d.add(f'<image x="{x_i}" y="{y_i:.2f}" width="{W}" height="{H:.2f}" href="data:image/png;base64,{b64}"/>')
        d.text((x_i, y_i - 2.5), "SIMULATED: O0110 + O0120 ON THE MAIN PLATE (FACE A)", 2.6, anchor="start", weight="bold")

    notes_block(d, 32.0, 305.0, cnc_notes(report), size=2.15, lead=3.05)
    title_block(d, 399.0, 359.0, None, "FIXTURE · DRILL · MAIN PLATE FACES A + B · CLAMP PLATES · ISO + GENERIC "
                "PROGRAMS · SIMULATED", "1:4, 1:2", "1 / 1", "A2", title="STACK MOULD – CNC MACHINING DIAGRAM",
                drawing_no=CM.DIAGRAM_NO, material="AL 6061-T651 / CAST PLATE")
    return d
