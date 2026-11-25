"""
Door-strap module for the Hyundai i20 N (BC3, 2021-) front doors  -  v3
======================================================================

Parametric CadQuery model of a drop-in replacement for the OEM inner
door-release handle.  A webbing strap drives a bell-crank lever that pulls
the ORIGINAL release cable, so the stock latch, central locking and
"one pull unlocks + opens" behaviour are kept.

Geometry comes from cad/oem_trace.py -> cad/oem_trace.json:
  * face outline (v3): the red outlines on the two in-car photos of the
    fitted strap plate, perspective-rectified from the rib lines and placed
    on the OEM handle; groove heights from the measured rib pitch
  * housing outline: red loop on the photo of the back of the OEM handle
  * snap clips, door-card screw (under the square cap), lever pivot: the
    OEM photos (front photo + AE Spares photo, averaged)

Native frame = RH unit seen from the cabin (the LH unit is its mirror):
    X  along the module, +X = REAR of the car (mechanism/pivot end = -X)
    Y  depth, +Y = into the door (away from the occupant). Face apex at Y=0
    Z  up
Units: millimetres.

!!  The photo scale (oem_trace.py, default 7.0 px/mm -> 185 mm overall), the
!!  in-car camera focal length and the cable details are estimates.  Measure
!!  your OEM handle / door-card opening, re-run oem_trace.py with
!!  --overall/--height (and --face-length), and check the cable values below.
"""

from __future__ import annotations

import functools
import json
import math
import os

import cadquery as cq
import numpy as np
from scipy.interpolate import splev, splprep

HERE = os.path.dirname(os.path.abspath(__file__))
TRACE = json.load(open(os.path.join(HERE, "oem_trace.json")))

# =============================================================================
# PARAMETERS
# =============================================================================

# ---- face & housing (from the trace) -----------------------------------------
LOOP_POINTS = 40           # control points of the smoothed outline splines
CROWN_RX = 1500.0          # face curvature radius, horizontal section
CROWN_RZ = 160.0           # face curvature radius, vertical section
FACE_EDGE_FILLET = 2.5
FACE_T = 3.0               # face shell thickness
WALL_T = 2.4               # wall thickness
DEPTH = 40.0               # face apex -> open back
FLANGE_Y0 = 6.5            # face plate meets the housing; 2 mm deck behind

# decorative grooves (continue the door-trim "parametric" lines); heights
# from the rib pitch measured on the rectified in-car photos
GROOVE_Z = tuple(TRACE.get("grooves", {}).get(
    "z", (-28.75, -17.25, -5.75, 5.75, 17.25, 28.75)))
GROOVE_R = 5.5             # groove tool radius (soft, wide "wave" grooves)
GROOVE_E = 4.3             # tool centre outside surface -> depth = 1.2
GROOVE_INSET = 6.5         # groove ends this far inside the face outline
GROOVE_KEEPOUT = 6.0       # grooves stop this far from the badge

# ---- vehicle interface (traced; verify) ----------------------------------------
CLIP_Y = 15.0              # depth of the snap-clip centre line
CLIP_T = 4.0               # clip thickness (Y)
CLIP_HEAD_L = 2.6          # length of the T-head
SCREW = TRACE["screw"]["centre"]       # door-card screw axis (X, Z)
SCREW_HOLE_D = 6.0         # clearance for the OEM door-card screw
SCREW_HEAD_D = 12.5        # counterbore for head + screwdriver
SCREW_SEAT_Y = 34.0        # depth of the screw-head seat (OEM cup floor)
SCREW_BOSS_D = 18.0

# badge = magnetic cover over the door-card screw
BADGE_W, BADGE_H, BADGE_R = 32.0, 22.0, 5.0
BADGE_FLOOR_Y = 3.4        # flat pocket floor
BADGE_PROUD = 1.0          # badge stands this far out of the face
BADGE_CLEAR = 0.15
MAGNET = (6.0, 2.0)        # disc magnet d x t (2 per badge, 2 in the pocket)
MAGNET_DX = 10.5           # magnet offset from the screw axis
PRY_NOTCH = (8.0, 2.2)     # finger notch at the bottom edge (w, depth)

# ---- mechanism -----------------------------------------------------------------
PIVOT = (round(TRACE["pivot"]["top"][0], 2), 14.0)  # OEM pivot X, depth Y
PIN_D = 4.0                # stainless pins (pivot + strap)
PIN_HOLE_PRESS = 4.0       # housing / cheek holes (press or ream to suit)
PIN_HOLE_RUN = 4.2         # lever hub bore (running fit)
HUB_D = 10.0
HUB_HALF = 20.5            # hub spans Z = +-20.5 (v3 face is lower-edged
                           # near the pivot: leaves room for the lower boss)
WASHER = (4.3, 9.0, 0.8)   # ISO 7089 M4: id, od, thickness
BOSS_GAP = 0.4
LEVER_ROT = 40.0           # lever rotation rest -> full pull (deg)
STRAP_ARM = 30.0           # pivot -> strap pin
STRAP_ARM_MID = 11.4       # strap-arm angle at mid travel (deg, lever frame)
HOOK_R = 17.0              # pivot -> nipple bearing face (sets cable travel)
HOOK_HALF_T = 6.0
FINGER = (4.5, 10.5, 30.0, (-20.5, -16.0))   # stop finger r0, r1, width, z
STOP_SECTOR = (5.6, 12.5, (-40.0, -15.8))    # housing stop ring r0, r1, z

# webbing
STRAP_W = 20.0             # 20 mm (3/4") webbing suits the 68 mm face
STRAP_T = 1.6
CHEEK_Z = (STRAP_W / 2 + 1.0, STRAP_W / 2 + 5.0)   # cheek plates (mirrored)
SLOT_W = 6.0
SLOT_LEN = STRAP_W + 1.4

# Bowden cable (OEM) - typical values, measure yours
CABLE_Z = 0.0
CABLE_D = 2.0
NIPPLE_D = 6.0
NIPPLE_L = 7.0
SHEATH_D = 5.2
FITTING = (8.0, 8.6)       # sheath end-fitting body: length (X), width (Z)

# cable anchor slider (adjusts the cable free length), at the pivot end
SLIDER_L = 13.0
SLIDER_HALF_W = 13.0
CHANNEL_X = (PIVOT[0] - 33.4, PIVOT[0] - 14.2)
CHANNEL_HALF_W = 13.2
CHANNEL_FLOOR_Y = 24.0
CLAMP_Z = -9.0
INSERT_D = 4.0             # M3 heat-set insert pilot (M3 x 5.7)
INSERT_L = 5.7

# =============================================================================
# DERIVED
# =============================================================================
R_MAJ = CROWN_RX - CROWN_RZ
TORUS_C = cq.Vector(0, CROWN_RX, 0)
HALF_ROT = LEVER_ROT / 2.0
POSE_REST = +HALF_ROT
POSE_FULL = -HALF_ROT
SLIDER_X_NOM = 0.5 * (CHANNEL_X[0] + CHANNEL_X[1])
SLIDER_TRAVEL = (CHANNEL_X[1] - CHANNEL_X[0]) - SLIDER_L
SLOT_X = PIVOT[0] + 28.3
STRAP_PIN_L = 2 * CHEEK_Z[1]


def lever_point(p_lever, pose_deg):
    """Lever-frame (x, y) -> global (X, Y) for a given pose angle."""
    a = math.radians(pose_deg)
    x, y = p_lever
    return (PIVOT[0] + x * math.cos(a) - y * math.sin(a),
            PIVOT[1] + x * math.sin(a) + y * math.cos(a))


STRAP_PIN_LF = (STRAP_ARM * math.cos(math.radians(STRAP_ARM_MID)),
                STRAP_ARM * math.sin(math.radians(STRAP_ARM_MID)))
HOOK_LF = (0.0, HOOK_R)
CABLE_Y = lever_point(HOOK_LF, POSE_REST)[1]
CABLE_TRAVEL = 2 * HOOK_R * math.sin(math.radians(HALF_ROT))


def kinematics_table(steps=9):
    rows = []
    hx0 = lever_point(HOOK_LF, POSE_REST)[0]
    sp0 = lever_point(STRAP_PIN_LF, POSE_REST)
    for i in range(steps):
        pose = POSE_REST - LEVER_ROT * i / (steps - 1)
        hx = lever_point(HOOK_LF, pose)[0]
        sp = lever_point(STRAP_PIN_LF, pose)
        rows.append(dict(rot=POSE_REST - pose, cable=abs(hx - hx0),
                         strap_y=sp0[1] - sp[1],
                         strap=math.dist(sp, sp0)))
    return rows


# =============================================================================
# outlines
# =============================================================================

def _resample(pts, n=LOOP_POINTS):
    a = np.asarray(pts, float)
    tck, _ = splprep([a[:, 0], a[:, 1]], s=len(a) * 0.5, per=1)
    u = np.linspace(0, 1, n, endpoint=False)
    x, z = splev(u, tck)
    return [(float(p), float(q)) for p, q in zip(x, z)]


def _body_outline(face_pts, housing_pts, margin=0.6, close=1.2, n=56):
    """One clean housing outline: union(face + margin, traced housing),
    morphologically closed to remove slivers, refitted as a smooth loop."""
    from shapely.geometry import Polygon
    u = Polygon(face_pts).buffer(margin, join_style="round").union(
        Polygon(housing_pts).buffer(0))
    u = u.buffer(close, join_style="round").buffer(-close, join_style="round")
    if u.geom_type != "Polygon":
        u = max(u.geoms, key=lambda g: g.area)
    ring = np.asarray(u.exterior.coords)[:-1]
    if Polygon(ring).exterior.is_ccw is False:
        ring = ring[::-1]
    seg = np.hypot(*np.diff(np.vstack([ring, ring[:1]]), axis=0).T)
    t = np.concatenate([[0], np.cumsum(seg)])
    tt = np.linspace(0, t[-1], 240, endpoint=False)
    closed = np.vstack([ring, ring[:1]])
    pts = np.column_stack([np.interp(tt, t, closed[:, 0]),
                           np.interp(tt, t, closed[:, 1])])
    return _resample(pts, n)


LOOPS = {"face": _resample(TRACE["face"])}
LOOPS["housing"] = _resample(TRACE["body"])
LOOPS["body"] = _body_outline(LOOPS["face"], LOOPS["housing"])


@functools.lru_cache(maxsize=None)
def loop_wire(name, off=0.0):
    e = cq.Workplane("XZ").spline(LOOPS[name], periodic=True).val()
    w = cq.Wire.assembleEdges([e])
    if abs(off) > 1e-9:
        w = w.offset2D(off, "arc")[0]
    return w


def loop_prism(name, off, y0, y1):
    f = cq.Face.makeFromWires(loop_wire(name, off))
    s = cq.Solid.extrudeLinear(f, cq.Vector(0, y1 - y0, 0))
    return cq.Workplane().add(s.translate(cq.Vector(0, y0, 0)))


@functools.lru_cache(maxsize=None)
def loop_points(name, off=0.0, n=480):
    w = loop_wire(name, off)
    return [(v.x, v.z) for v in (w.positionAt(t) for t in
                                 np.linspace(0, 1, n, endpoint=False))]


def _intervals(P, value, axis):
    """Sorted inside-intervals of the closed polyline P along the other axis."""
    o = 1 - axis
    hits = []
    for p, q in zip(P, P[1:] + P[:1]):
        if (p[axis] - value) * (q[axis] - value) < 0:
            t = (value - p[axis]) / (q[axis] - p[axis])
            hits.append(p[o] + t * (q[o] - p[o]))
    hits.sort()
    return list(zip(hits[0::2], hits[1::2]))


def _crossings(P, value, axis):          # (min, max) - kept for the mock-up
    iv = _intervals(P, value, axis)
    return (iv[0][0], iv[-1][1]) if iv else None


def z_extent(x, off=0.0):
    """(z_min, z_max) of the housing (body) outline at X = x."""
    return _crossings(loop_points("body", off), x, 0)


def x_extent(z, off=0.0):
    """(x_min, x_max) of the housing (body) outline at height z."""
    return _crossings(loop_points("body", off), z, 1)


def outline_points(off=0.0, pts=None, radii=None, n_arc=32):
    """Face outline polyline (or a rounded polygon for the trim mock-up)."""
    if pts is None:
        return loop_points("face", off)
    segs = rounded_poly(pts, radii, off)
    P = []
    for a, m, b, c, R in segs:
        a0 = math.atan2(a[1] - c[1], a[0] - c[0])
        a1 = math.atan2(b[1] - c[1], b[0] - c[0])
        while a1 < a0:
            a1 += 2 * math.pi
        for k in range(n_arc + 1):
            t = a0 + (a1 - a0) * k / n_arc
            P.append((c[0] + R * math.cos(t), c[1] + R * math.sin(t)))
    return P


def outline_prism(off, y0, y1):
    return loop_prism("face", off, y0, y1)


def rounded_poly(pts, radii, off=0.0):
    """Corner fillets of a convex CCW polygon (used by the trim mock-up)."""
    n = len(pts)
    out = []
    for i in range(n):
        p0, p1, p2 = pts[i - 1], pts[i], pts[(i + 1) % n]
        e1 = (p1[0] - p0[0], p1[1] - p0[1])
        e2 = (p2[0] - p1[0], p2[1] - p1[1])
        l1, l2 = math.hypot(*e1), math.hypot(*e2)
        e1 = (e1[0] / l1, e1[1] / l1)
        e2 = (e2[0] / l2, e2[1] / l2)
        n1 = (e1[1], -e1[0])
        n2 = (e2[1], -e2[0])
        r = radii[i]
        t = r * (n1[0] * n2[0] + n1[1] * n2[1] - 1) / (e1[0] * n2[0]
                                                      + e1[1] * n2[1])
        c = (p1[0] - r * n1[0] + t * e1[0], p1[1] - r * n1[1] + t * e1[1])
        R = r + off
        bis = (n1[0] + n2[0], n1[1] + n2[1])
        lb = math.hypot(*bis)
        a = (c[0] + R * n1[0], c[1] + R * n1[1])
        b = (c[0] + R * n2[0], c[1] + R * n2[1])
        m = (c[0] + R * bis[0] / lb, c[1] + R * bis[1] / lb)
        out.append((a, m, b, c, R))
    return out


def poly_wire(pts, radii, off=0.0, plane="XZ"):
    segs = rounded_poly(pts, radii, off)
    w = cq.Workplane(plane).moveTo(*segs[0][2])
    for a, m, b, _, _ in segs[1:] + segs[:1]:
        w = w.lineTo(*a).threePointArc(m, b)
    return w.close()


# =============================================================================
# primitives
# =============================================================================

def torus(minor_offset=0.0):
    return cq.Workplane().add(
        cq.Solid.makeTorus(R_MAJ, CROWN_RZ + minor_offset, TORUS_C,
                           cq.Vector(0, 0, 1)))


def face_y(x, z, minor_offset=0.0):
    rho = R_MAJ + math.sqrt((CROWN_RZ + minor_offset) ** 2 - z * z)
    return CROWN_RX - math.sqrt(rho * rho - x * x)


def box(x0, x1, y0, y1, z0, z1):
    return (cq.Workplane("XY").box(x1 - x0, y1 - y0, z1 - z0)
            .translate(((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2)))


def zcyl(x, y, d, z0, z1):
    return (cq.Workplane("XY").workplane(offset=z0).center(x, y)
            .circle(d / 2).extrude(z1 - z0))


def ycyl(x, z, d, y0, y1):
    return (cq.Workplane("XZ").center(x, z).circle(d / 2)
            .extrude(-(y1 - y0)).translate((0, y0, 0)))


def capsule_xy(p1, r1, p2, r2, z0, z1):
    (x1, y1), (x2, y2) = p1, p2
    d = math.dist(p1, p2)
    ang = math.atan2(y2 - y1, x2 - x1)
    beta = math.acos((r1 - r2) / d)
    a1, a2 = ang + beta, ang - beta
    t1a = (x1 + r1 * math.cos(a1), y1 + r1 * math.sin(a1))
    t2a = (x2 + r2 * math.cos(a1), y2 + r2 * math.sin(a1))
    t2b = (x2 + r2 * math.cos(a2), y2 + r2 * math.sin(a2))
    t1b = (x1 + r1 * math.cos(a2), y1 + r1 * math.sin(a2))
    m2 = (x2 + r2 * math.cos(ang), y2 + r2 * math.sin(ang))
    m1 = (x1 - r1 * math.cos(ang), y1 - r1 * math.sin(ang))
    w = (cq.Workplane("XY").workplane(offset=z0).moveTo(*t1a).lineTo(*t2a)
         .threePointArc(m2, t2b).lineTo(*t1b).threePointArc(m1, t1a).close())
    return w.extrude(z1 - z0)


def annular_sector(center, r0, r1, a0, a1, z0, z1, n=None):
    cx, cy = center

    def pt(r, a):
        a = math.radians(a)
        return (cx + r * math.cos(a), cy + r * math.sin(a))

    am = 0.5 * (a0 + a1)
    w = (cq.Workplane("XY").workplane(offset=z0).moveTo(*pt(r1, a0))
         .threePointArc(pt(r1, am), pt(r1, a1)).lineTo(*pt(r0, a1))
         .threePointArc(pt(r0, am), pt(r0, a0)).close())
    return w.extrude(z1 - z0)


def groove_tool(zg, x0, x1):
    """Swept groove following the toroidal face at height zg, x0..x1."""
    sb = zg / CROWN_RZ
    cb = math.sqrt(1 - sb * sb)
    rho_c = R_MAJ + (CROWN_RZ + GROOVE_E) * cb
    z_c = (CROWN_RZ + GROOVE_E) * sb
    p1 = math.degrees(math.asin(x0 / rho_c))
    p2 = math.degrees(math.asin(x1 / rho_c))
    ring = (cq.Workplane("YZ").moveTo(-rho_c, z_c).circle(GROOVE_R)
            .revolve(p2 - p1, (0, 0, 0), (0, 1, 0)))
    ring = ring.rotate((0, 0, 0), (0, 0, 1), p1)
    for p in (p1, p2):
        a = math.radians(p)
        ring = ring.union(cq.Workplane().sphere(GROOVE_R + 0.02).translate(
            (rho_c * math.sin(a), -rho_c * math.cos(a), z_c)))
    return ring.translate((0, CROWN_RX, 0))


def badge_prism(off, y0, y1):
    w, h, r = BADGE_W + 2 * off, BADGE_H + 2 * off, BADGE_R + off
    sk = cq.Sketch().rect(w, h).vertices().fillet(r)
    return (cq.Workplane("XZ").center(SCREW[0], SCREW[1]).placeSketch(sk)
            .extrude(-(y1 - y0)).translate((0, y0, 0)))


def pin_bottom_z():
    return z_extent(PIVOT[0], -WALL_T)[0] + 1.2


def pivot_pin_length():
    top = z_extent(PIVOT[0])[1] - 1.0
    for L in (80, 75, 70, 65, 60, 55, 50):
        if pin_bottom_z() + L <= top:
            return float(L)
    return 50.0


# =============================================================================
# PARTS
# =============================================================================

def _clip(c):
    """OEM-style T-head snap clip + a pad that ties its base to the housing."""
    (tx, tz), (dx, dz), w = c["tip"], c["dir"], max(c["width"], 5.5)
    length = c.get("length", 8.0)
    ux, uz = dx, dz                      # outward direction
    px, pz = -uz, ux                     # perpendicular

    def rect(cx, cz, ln, wd, y0, y1):
        pts = []
        for a, b in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
            pts.append((cx + ux * a * ln / 2 + px * b * wd / 2,
                        cz + uz * a * ln / 2 + pz * b * wd / 2))
        return (cq.Workplane("XZ").polyline(pts).close()
                .extrude(-(y1 - y0)).translate((0, y0, 0)))

    cy0, cy1 = CLIP_Y - CLIP_T / 2, CLIP_Y + CLIP_T / 2
    bx, bz = tx - ux * length, tz - uz * length          # clip base
    stem = rect(tx - ux * (length + 1) / 2, tz - uz * (length + 1) / 2,
                length + 1, 0.68 * w, cy0, cy1)
    head = rect(tx - ux * CLIP_HEAD_L / 2, tz - uz * CLIP_HEAD_L / 2,
                CLIP_HEAD_L, w, cy0, cy1)
    # pad from inside the wall out to the clip base (OEM frame region)
    if ux == 0:
        lo, hi = z_extent(bx)
        edge = hi if uz > 0 else lo
        reach = (bz - edge) * uz
    else:
        lo, hi = x_extent(bz)
        edge = hi if ux > 0 else lo
        reach = (bx - edge) * ux
    pad_len = max(reach, 0.0) + WALL_T + 1.0
    pad = rect(bx - ux * pad_len / 2, bz - uz * pad_len / 2, pad_len,
               w + 5.0, FLANGE_Y0, cy1 + 1.5)
    return stem.union(head).union(pad)


@functools.lru_cache(maxsize=None)
def build_housing():
    """Crowned ribbed face (traced) + open-back housing + vehicle features."""
    big = torus()
    face = loop_prism("face", 0, -5, FLANGE_Y0 + 1).intersect(big)
    body = face.faces("%TORUS").edges().fillet(FACE_EDGE_FILLET)
    body = body.union(loop_prism("body", 0, FLANGE_Y0, DEPTH))
    for c in TRACE["clips"]:
        body = body.union(_clip(c))

    # --- hollow (open back); a 2 mm deck closes the face/housing gap ----------
    cav = loop_prism("face", -WALL_T, -5, FLANGE_Y0 + 2).intersect(
        torus(-FACE_T))
    cav = cav.union(loop_prism("body", -WALL_T, FLANGE_Y0 + 2, DEPTH + 5))
    body = body.cut(cav)

    # --- internal structure ----------------------------------------------------
    clip = loop_prism("face", -(WALL_T - 0.6), -5, FLANGE_Y0 + 2).intersect(
        torus(-(FACE_T - 0.6)))
    clip = clip.union(loop_prism("body", -(WALL_T - 0.6), FLANGE_Y0 + 2,
                                 DEPTH))
    px, py = PIVOT
    zb = HUB_HALF + WASHER[2] + BOSS_GAP
    inner = (zcyl(px, py, HUB_D, zb, 60)
             .union(zcyl(px, py, HUB_D, -60, -zb))
             .union(box(px - 1.5, px + 1.5, -2, py, zb, 60))
             .union(box(px - 1.5, px + 1.5, -2, py, -60, -zb)))
    r0, r1, (sz0, sz1) = STOP_SECTOR
    f_w = FINGER[2]
    gap0 = 180.0 + POSE_FULL - f_w / 2
    gap1 = 180.0 + POSE_REST + f_w / 2
    inner = inner.union(annular_sector(PIVOT, r0, r1, gap1, gap0 + 360.0,
                                       sz0, sz1))
    xe = x_extent(0.0)[0]                            # pivot-end wall at Z=0
    inner = inner.union(box(xe - 6, CHANNEL_X[1] + 2.2, 16.0, DEPTH + 1,
                            -16.0, 16.0))
    inner = inner.union(badge_prism(3.0, -2.0, 6.6))
    inner = inner.union(ycyl(SCREW[0], SCREW[1], SCREW_BOSS_D, -2.0, DEPTH))
    inner = inner.intersect(clip)
    body = body.union(inner)

    # --- cuts --------------------------------------------------------------------
    body = body.cut(zcyl(px, py, PIN_HOLE_PRESS, pin_bottom_z(), 60))
    slot = (cq.Workplane("XZ").center(SLOT_X, 0)
            .slot2D(SLOT_LEN, SLOT_W, angle=90).extrude(-15)
            .translate((0, -5, 0)))
    body = body.cut(slot)
    bx0, bx1 = SCREW[0] - BADGE_W / 2, SCREW[0] + BADGE_W / 2
    bz0, bz1 = SCREW[1] - BADGE_H / 2, SCREW[1] + BADGE_H / 2
    P = loop_points("face", -GROOVE_INSET)
    for zg in GROOVE_Z:
        for a, b in _intervals(P, zg, 1):
            segs = [(a, b)]
            if bz0 - GROOVE_KEEPOUT < zg < bz1 + GROOVE_KEEPOUT:
                segs = [(a, min(b, bx0 - GROOVE_KEEPOUT)),
                        (max(a, bx1 + GROOVE_KEEPOUT), b)]
            for s0, s1 in segs:
                if s1 - s0 > 2 * GROOVE_R + 6:
                    body = body.cut(groove_tool(zg, s0 + GROOVE_R,
                                                s1 - GROOVE_R))
    # badge pocket, magnet pockets, pry notch, screw counterbore + hole
    body = body.cut(badge_prism(0.0, -5.0, BADGE_FLOOR_Y))
    md, mt = MAGNET
    for s in (-1, 1):
        body = body.cut(ycyl(SCREW[0] + s * MAGNET_DX, SCREW[1], md + 0.2,
                             BADGE_FLOOR_Y - 0.1, BADGE_FLOOR_Y + mt + 0.2))
    nw, nd = PRY_NOTCH
    body = body.cut(box(SCREW[0] - nw / 2, SCREW[0] + nw / 2, -5,
                        BADGE_FLOOR_Y - 0.5, bz0 - nd, bz0 + 1))
    body = body.cut(ycyl(SCREW[0], SCREW[1], SCREW_HEAD_D, -5, SCREW_SEAT_Y))
    body = body.cut(ycyl(SCREW[0], SCREW[1], SCREW_HOLE_D, -5, DEPTH + 5))
    # cable channel, sheath exit through the end wall, cable pass, insert
    body = body.cut(box(CHANNEL_X[0], CHANNEL_X[1], CHANNEL_FLOOR_Y,
                        DEPTH + 2, -CHANNEL_HALF_W, CHANNEL_HALF_W))
    body = body.cut(box(xe - 12, CHANNEL_X[0] + 1,
                        CABLE_Y - SHEATH_D / 2 - 0.4, DEPTH + 2,
                        -(SHEATH_D / 2 + 0.4), SHEATH_D / 2 + 0.4))
    body = body.cut(box(CHANNEL_X[1] - 1, CHANNEL_X[1] + 4,
                        CABLE_Y - CABLE_D / 2 - 0.3, DEPTH + 2,
                        -(CABLE_D / 2 + 0.3), CABLE_D / 2 + 0.3))
    body = body.cut(cq.Workplane("XZ").center(SLIDER_X_NOM, CLAMP_Z)
                    .circle(INSERT_D / 2).extrude(-(INSERT_L + 0.5))
                    .translate((0, CHANNEL_FLOOR_Y - INSERT_L, 0)))
    return body


@functools.lru_cache(maxsize=None)
def build_lever():
    """Bell-crank lever in its own frame (pivot at origin, hook arm along +Y).

    Pose it with pose_lever(); rest = +20 deg, full pull = -20 deg.
    """
    hub = zcyl(0, 0, HUB_D, -HUB_HALF, HUB_HALF)
    sp = STRAP_PIN_LF
    lev = hub
    for s in (1, -1):
        z0, z1 = sorted((s * CHEEK_Z[0], s * CHEEK_Z[1]))
        lev = lev.union(capsule_xy((0, 0), HUB_D / 2 + 0.5, sp, 4.5, z0, z1))
    web_end = (18.0 * math.cos(math.radians(STRAP_ARM_MID)),
               18.0 * math.sin(math.radians(STRAP_ARM_MID)))
    lev = lev.union(capsule_xy((0, 0), 2.0, web_end, 1.5,
                               -CHEEK_Z[0] - 0.01, CHEEK_Z[0] + 0.01))
    hx, hy = HOOK_LF
    lev = lev.union(capsule_xy((0, 0), 6.0, (hx, hy), 5.5,
                               -HOOK_HALF_T, HOOK_HALF_T))
    lev = lev.union(box(hx - 3.5, hx + 9.0, hy - 6.0, hy + 5.0,
                        -HOOK_HALF_T, HOOK_HALF_T))
    fr0, fr1, fw, (fz0, fz1) = FINGER
    lev = lev.union(annular_sector((0, 0), fr0, fr1, 180 - fw / 2,
                                   180 + fw / 2, fz0, fz1))
    lev = lev.cut(zcyl(0, 0, PIN_HOLE_RUN, -40, 40))
    lev = lev.cut(zcyl(sp[0], sp[1], PIN_HOLE_PRESS, -30, 30))
    cw = CABLE_D / 2 + 0.3
    t = math.tan(math.radians(23))
    fan = (cq.Workplane("XY").workplane(offset=-cw)
           .polyline([(hx + 0.5, hy - cw), (hx - 15, hy - cw - 15 * t),
                      (hx - 15, hy + 30), (hx + 0.5, hy + 30)]).close()
           .extrude(2 * cw))
    lev = lev.cut(fan)
    nr = NIPPLE_D / 2 + 0.6
    cradle = box(hx, hx + 12, hy, hy + 30, -nr, nr).union(
        cq.Workplane("YZ").workplane(offset=hx).center(hy, 0).circle(nr)
        .extrude(12))
    lev = lev.cut(cradle)
    return lev


def pose_lever(shape, pose_deg):
    return (shape.rotate((0, 0, 0), (0, 0, 1), pose_deg)
            .translate((PIVOT[0], PIVOT[1], 0)))


@functools.lru_cache(maxsize=None)
def build_slider(x_center=SLIDER_X_NOM):
    """Sliding anchor for the cable sheath end-fitting (clamped by M3)."""
    hl = SLIDER_L / 2
    y0, y1 = CHANNEL_FLOOR_Y + 0.15, DEPTH - 0.4
    s = box(-hl, hl, y0, y1, -SLIDER_HALF_W, SLIDER_HALF_W)
    fl, fw = FITTING
    s = s.cut(box(-fl / 2, fl / 2, CABLE_Y - 4.0, y1 + 1, -fw / 2, fw / 2))
    s = s.cut(box(-hl - 1, -fl / 2 + 0.01, CABLE_Y - SHEATH_D / 2 - 0.3,
                  y1 + 1, -(SHEATH_D / 2 + 0.3), SHEATH_D / 2 + 0.3))
    s = s.cut(box(fl / 2 - 0.01, hl + 1, CABLE_Y - CABLE_D / 2 - 0.3, y1 + 1,
                  -(CABLE_D / 2 + 0.3), CABLE_D / 2 + 0.3))
    trav = SLIDER_TRAVEL / 2
    for zc in (CLAMP_Z, -CLAMP_Z):
        slot = (cq.Workplane("XZ").center(0, zc)
                .slot2D(2 * trav + 3.4, 3.4, angle=0).extrude(-(y1 - y0 + 2))
                .translate((0, y0 - 1, 0)))
        cbore = (cq.Workplane("XZ").center(0, zc)
                 .slot2D(2 * trav + 6.2, 6.2, angle=0).extrude(-4.0)
                 .translate((0, y1 - 3.5, 0)))
        s = s.cut(slot).cut(cbore)
    return s.translate((x_center, 0, 0))


@functools.lru_cache(maxsize=None)
def build_badge():
    """Magnetic cover over the door-card screw (generic stripe motif)."""
    b = badge_prism(-BADGE_CLEAR, -6.0, BADGE_FLOOR_Y).intersect(
        torus(BADGE_PROUD))
    stripes = None
    for i in (-1, 0, 1):
        cx = SCREW[0] + i * 7.5
        st = (cq.Workplane("XZ").center(cx, SCREW[1]).rect(3.0, 40)
              .extrude(-20).translate((0, -10, 0))
              .rotate((cx, 0, SCREW[1]), (cx, 1, SCREW[1]), 25))
        stripes = st if stripes is None else stripes.union(st)
    shell = torus(BADGE_PROUD + 1.0).cut(torus(BADGE_PROUD - 0.6))
    b = b.cut(stripes.intersect(shell).intersect(
        badge_prism(-BADGE_CLEAR - 1.6, -6.0, BADGE_FLOOR_Y)))
    md, mt = MAGNET
    for s in (-1, 1):
        b = b.cut(ycyl(SCREW[0] + s * MAGNET_DX, SCREW[1], md + 0.2,
                       BADGE_FLOOR_Y - mt - 0.2, BADGE_FLOOR_Y + 1))
    return b


def build_fit_gauge(housing=None):
    """Quick-print slice through the clips to test-fit the door card."""
    housing = housing if housing is not None else build_housing()
    return housing.intersect(box(-140, 140, FLANGE_Y0 - 1.5,
                                 CLIP_Y + CLIP_T / 2 + 1.0, -80, 80))


def build_hardware(pose_deg=POSE_REST):
    px, py = PIVOT
    zb = HUB_HALF + WASHER[2] + BOSS_GAP
    bottom = pin_bottom_z()
    hw = {}
    hw["pivot_pin"] = (zcyl(px, py, PIN_D, bottom, bottom + pivot_pin_length())
                       .edges().chamfer(0.4))
    spx, spy = lever_point(STRAP_PIN_LF, pose_deg)
    hw["strap_pin"] = (zcyl(spx, spy, PIN_D, -STRAP_PIN_L / 2,
                            STRAP_PIN_L / 2).edges().chamfer(0.4))
    wid, wod, wt = WASHER
    hw["washers"] = (zcyl(px, py, wod, HUB_HALF, HUB_HALF + wt)
                     .cut(zcyl(px, py, wid, -50, 50))
                     .union(zcyl(px, py, wod, -HUB_HALF - wt, -HUB_HALF)
                            .cut(zcyl(px, py, wid, -50, 50))))
    y_top = DEPTH - 0.4 - 3.5
    screw = (cq.Workplane("XZ").center(SLIDER_X_NOM, CLAMP_Z).circle(1.5)
             .extrude(-16).translate((0, y_top - 16, 0)))
    head = (cq.Workplane("XZ").center(SLIDER_X_NOM, CLAMP_Z).circle(2.75)
            .extrude(-3.0).translate((0, y_top, 0)))
    head = head.cut(cq.Workplane("XZ").center(SLIDER_X_NOM, CLAMP_Z)
                    .polygon(6, 2.9).extrude(-2.0)
                    .translate((0, y_top + 1.0, 0)))
    hw["clamp_screw"] = screw.union(head)
    hw["insert"] = (cq.Workplane("XZ").center(SLIDER_X_NOM, CLAMP_Z)
                    .circle(2.3).circle(1.5).extrude(-INSERT_L)
                    .translate((0, CHANNEL_FLOOR_Y - INSERT_L, 0)))
    md, mt = MAGNET
    mags = None
    for s in (-1, 1):
        for y0 in (BADGE_FLOOR_Y - mt - 0.1, BADGE_FLOOR_Y + 0.05):
            m = ycyl(SCREW[0] + s * MAGNET_DX, SCREW[1], md, y0, y0 + mt)
            mags = m if mags is None else mags.union(m)
    hw["magnets"] = mags
    # OEM door-card screw (reused) seated in the boss
    hw["door_screw"] = (ycyl(SCREW[0], SCREW[1], 10.0, SCREW_SEAT_Y - 3.5,
                             SCREW_SEAT_Y)
                        .union(ycyl(SCREW[0], SCREW[1], 5.0, SCREW_SEAT_Y,
                                    SCREW_SEAT_Y + 16)))
    return hw


def build_cable(pose_deg=POSE_REST, slider_x=SLIDER_X_NOM):
    """Representative OEM cable end: sheath, fitting, inner cable, nipple.

    The sheath seat is on the pivot-end (-X) side of the slider pocket; the
    inner cable runs +X to the nipple seated on the lever's bearing face.
    """
    hx, hy = lever_point(HOOK_LF, pose_deg)
    fx = slider_x - FITTING[0] / 2
    x_out = x_extent(0.0)[0] - 30
    sheath = (cq.Workplane("YZ").workplane(offset=x_out)
              .center(CABLE_Y, CABLE_Z).circle(SHEATH_D / 2)
              .extrude(fx - 2 - x_out))
    fitting = (cq.Workplane("YZ").workplane(offset=fx).center(CABLE_Y, CABLE_Z)
               .rect(FITTING[1] - 1.0, FITTING[1] - 1.0)
               .extrude(FITTING[0] - 0.4).edges("|X").fillet(1.5))
    e = cq.Vector(fx + FITTING[0] - 0.4, CABLE_Y, CABLE_Z)
    h = cq.Vector(hx, hy, CABLE_Z)
    inner = cq.Workplane().add(cq.Solid.makeCylinder(
        CABLE_D / 2, (h - e).Length + 0.5, e, (h - e).normalized()))
    a = math.radians(pose_deg)
    u = cq.Vector(math.cos(a), math.sin(a), 0)
    nipple = (cq.Workplane().add(cq.Solid.makeCylinder(
        NIPPLE_D / 2, NIPPLE_L, h + u * 0.05, u)).edges().fillet(0.6))
    return {"cable_sheath": sheath.union(fitting),
            "cable_inner": inner.union(nipple)}


def build_assembly(pose_deg=POSE_REST, mirror=False, with_cable=True):
    parts = {
        "housing": build_housing(),
        "lever": pose_lever(build_lever(), pose_deg),
        "slider": build_slider(),
        "badge": build_badge(),
    }
    parts.update(build_hardware(pose_deg))
    if with_cable:
        parts.update(build_cable(pose_deg))
    if mirror:
        parts = {k: v.mirror("YZ") for k, v in parts.items()}
    return parts


if __name__ == "__main__":
    for r in kinematics_table():
        print("rot {rot:5.1f} deg  cable {cable:5.2f} mm  strap {strap:5.2f} mm"
              .format(**r))
    print("pivot", PIVOT, "slot X", round(SLOT_X, 1), "screw", SCREW,
          "pin L", pivot_pin_length(), "cable travel", round(CABLE_TRAVEL, 2))
