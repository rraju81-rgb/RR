"""
Door-strap module for the Hyundai i20 N (BC3, 2021-) front doors
=================================================================

Parametric CadQuery model of a drop-in replacement for the OEM inner
door-release handle.  A webbing strap drives a bell-crank lever that pulls
the ORIGINAL release cable, so the stock latch, central locking and
"one pull unlocks + opens" behaviour are kept.

Coordinate system (LH / driver door of a LHD car; RH unit is the mirror):
    X  along the module, +X = towards the FRONT of the car
    Y  depth, +Y = into the door (away from the occupant). Face apex at Y=0
    Z  up
Units: millimetres.

!!  Interface dimensions (mounting ears, cable anchor, nipple seat) are
!!  ESTIMATES made from photographs.  Measure your OEM handle and update the
!!  values in the "VEHICLE INTERFACE" block before printing (see README).
"""

from __future__ import annotations

import math
import cadquery as cq

# =============================================================================
# PARAMETERS
# =============================================================================

# ---- visible face ----------------------------------------------------------
FACE_L = 140.0        # face length (X)
FACE_H_REAR = 78.0    # face height at the rear end (Z)
FACE_H_FRONT = 72.0   # face height at the front end (gentle "D" taper)
R_REAR = 24.0         # rear corner radius
R_FRONT = 34.0        # front corner radius
CROWN_RX = 1500.0     # face curvature radius, horizontal section
CROWN_RZ = 160.0      # face curvature radius, vertical section
FACE_EDGE_FILLET = 3.0
FACE_T = 3.0          # face shell thickness
WALL_T = 2.4          # side-wall thickness
DEPTH = 40.0          # face apex -> open back

# decorative grooves (continue the door-trim "parametric" lines)
GROOVE_Z = (-28.75, -17.25, -5.75, 5.75, 17.25, 28.75)
GROOVE_R = 5.5        # groove tool radius (soft, wide "wave" grooves)
GROOVE_E = 4.3        # tool centre outside surface -> depth = R - E = 1.2
GROOVE_INSET = 7.0    # groove ends this far inside the outline

# badge (customisable insert, sits in a pocket on the face)
BADGE_X = (10.0, 46.0)
BADGE_H = 22.0
BADGE_R = 5.0
BADGE_FLOOR_Y = 3.4   # flat pocket floor
BADGE_PROUD = 1.0     # insert stands this far out of the face
BADGE_CLEAR = 0.15

# ---- VEHICLE INTERFACE (verify against the OEM handle!) ----------------------
FLANGE_Y0 = 9.0       # front plane of the retaining flange (behind trim rim)
FLANGE_T = 2.5
FLANGE_W = 3.5        # flange overhang beyond the face outline
EARS = (              # screw ears: (x, z) of hole centre
    (-78.5, 0.0),
    (78.5, 0.0),
)
EAR_Y = (11.5, 16.0)  # ear plate Y range (door-card boss contact face = 16.0)
EAR_HOLE_D = 4.5      # clearance for the OEM 4 mm tapping screws
EAR_W = 14.0
PEGS = (20.0,)          # square locating peg(s) on the top wall: x position
PEG = (5.0, 5.0, 6.0)   # peg size x, y, height

# ---- mechanism -------------------------------------------------------------
PIVOT = (-34.0, 14.0)  # pivot axis (X, Y), vertical (parallel to Z)
PIN_D = 4.0            # stainless pins (pivot + strap)
PIN_HOLE_PRESS = 4.0   # housing / cheek holes (press or ream to suit)
PIN_HOLE_RUN = 4.2     # lever hub bore (running fit)
PIVOT_PIN_L = 70.0
STRAP_PIN_L = 35.0
HUB_D = 10.0
HUB_HALF = 26.0        # hub spans Z = +-26
WASHER = (4.3, 9.0, 0.8)  # ISO 7089 M4: id, od, thickness
BOSS_GAP = 0.4         # axial play
LEVER_ROT = 40.0       # total lever rotation rest -> full pull (deg)
STRAP_ARM = 30.0       # pivot -> strap pin
STRAP_ARM_MID = 11.4   # strap-arm angle at mid travel (deg, lever frame)
HOOK_R = 17.0          # pivot -> nipple bearing face (sets cable travel)
CHEEK_Z = (13.5, 17.5)  # cheek plates, mirrored about Z=0 (27 mm webbing gap)
HOOK_HALF_T = 6.0      # hook arm thickness / 2
FINGER = (4.5, 10.5, 30.0, (-25.5, -20.0))  # stop finger r0, r1, width deg, z
STOP_SECTOR = (5.6, 12.5, (-37.5, -19.5))   # housing stop ring r0, r1, z

# webbing
STRAP_W = 25.0
STRAP_T = 1.6
SLOT_X = -6.0          # strap slot centre (X)
SLOT_W = 6.0
SLOT_LEN = 26.4

# Bowden cable (OEM) - typical values, measure yours
CABLE_Z = 0.0
CABLE_D = 2.0          # inner cable incl. coating
NIPPLE_D = 6.0         # cylindrical end slug
NIPPLE_L = 7.0
SHEATH_D = 5.2
FITTING = (8.0, 8.6)   # sheath end-fitting body: length (X), width (Z)

# cable anchor slider (adjusts the cable free length)
SLIDER_L = 13.0
SLIDER_HALF_W = 13.0
CHANNEL_X = (-67.4, -48.2)
CHANNEL_HALF_W = 13.2
CHANNEL_FLOOR_Y = 24.0
CLAMP_Z = -9.0
INSERT_D = 4.0         # M3 heat-set insert pilot (M3 x 5.7)
INSERT_L = 5.7

# =============================================================================
# DERIVED
# =============================================================================
R_MAJ = CROWN_RX - CROWN_RZ          # torus major radius
TORUS_C = cq.Vector(0, CROWN_RX, 0)  # torus centre (axis parallel to Z)
HALF_ROT = LEVER_ROT / 2.0
POSE_REST = +HALF_ROT
POSE_FULL = -HALF_ROT
SLIDER_X_NOM = 0.5 * (CHANNEL_X[0] + SLIDER_L / 2 + CHANNEL_X[1] - SLIDER_L / 2)
SLIDER_TRAVEL = (CHANNEL_X[1] - CHANNEL_X[0]) - SLIDER_L


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
        rows.append(dict(rot=POSE_REST - pose, cable=hx - hx0,
                         strap_y=sp0[1] - sp[1],
                         strap=math.dist(sp, sp0)))
    return rows


# =============================================================================
# 2-D / primitive helpers
# =============================================================================

def face_corners():
    """Sharp-corner face polygon in (x, z), counter-clockwise."""
    xr, xf = -FACE_L / 2, FACE_L / 2
    return [(xr, -FACE_H_REAR / 2), (xf, -FACE_H_FRONT / 2),
            (xf, FACE_H_FRONT / 2), (xr, FACE_H_REAR / 2)]


FACE_RADII = (R_REAR, R_FRONT, R_FRONT, R_REAR)


def rounded_poly(pts, radii, off=0.0):
    """Corner fillets of a convex CCW polygon, offset by `off` (+ = out).

    Returns per corner: (tangent_in, arc_mid, tangent_out, centre, radius).
    Offsetting keeps the fillet centres, so all offsets stay concentric.
    """
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


def outline_points(off=0.0, pts=None, radii=None, n_arc=32):
    segs = rounded_poly(pts or face_corners(), radii or FACE_RADII, off)
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


def _crossings(P, value, axis):
    o = 1 - axis
    hits = []
    for p, q in zip(P, P[1:] + P[:1]):
        if (p[axis] - value) * (q[axis] - value) <= 0 and p[axis] != q[axis]:
            t = (value - p[axis]) / (q[axis] - p[axis])
            hits.append(p[o] + t * (q[o] - p[o]))
    return (min(hits), max(hits)) if hits else None


def outline_x_extent(z, off=0.0):
    """(x_min, x_max) of the (offset) face outline at height z, or None."""
    return _crossings(outline_points(off), z, 1)


def outline_z_extent(x, off=0.0):
    """(z_min, z_max) of the (offset) face outline at position x, or None."""
    return _crossings(outline_points(off), x, 0)


def outline_prism(off, y0, y1):
    """Face outline offset by `off` (+ = outwards) extruded from Y=y0 to y1."""
    return (poly_wire(face_corners(), FACE_RADII, off)
            .extrude(-(y1 - y0)).translate((0, y0, 0)))


def pin_bottom_z():
    """Blind end of the pivot-pin bore (1.2 mm above the bottom wall)."""
    return outline_z_extent(PIVOT[0], -WALL_T)[0] + 1.2


def torus(minor_offset=0.0):
    """Solid torus whose outer surface is the face surface offset outwards."""
    return cq.Workplane().add(
        cq.Solid.makeTorus(R_MAJ, CROWN_RZ + minor_offset, TORUS_C,
                           cq.Vector(0, 0, 1)))


def face_y(x, z, minor_offset=0.0):
    """Y of the (offset) face surface at (x, z)."""
    rho = R_MAJ + math.sqrt((CROWN_RZ + minor_offset) ** 2 - z * z)
    return CROWN_RX - math.sqrt(rho * rho - x * x)


def badge_prism(off, y0, y1):
    x0, x1 = BADGE_X[0] - off, BADGE_X[1] + off
    h, r = BADGE_H + 2 * off, BADGE_R + off
    sk = cq.Sketch().rect(x1 - x0, h).vertices().fillet(r)
    return (cq.Workplane("XZ").center((x0 + x1) / 2, 0).placeSketch(sk)
            .extrude(-(y1 - y0)).translate((0, y0, 0)))


def capsule_xy(p1, r1, p2, r2, z0, z1):
    """Convex hull of two circles in the XY plane, extruded Z = z0..z1."""
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
    """Annular sector from angle a0 to a1 (deg, CCW), extruded Z = z0..z1.

    Built from true arcs (clean B-rep, clean drawings).  `n` is ignored and
    kept only for backwards compatibility.
    """
    cx, cy = center

    def pt(r, a):
        a = math.radians(a)
        return (cx + r * math.cos(a), cy + r * math.sin(a))

    am = 0.5 * (a0 + a1)
    w = (cq.Workplane("XY").workplane(offset=z0).moveTo(*pt(r1, a0))
         .threePointArc(pt(r1, am), pt(r1, a1)).lineTo(*pt(r0, a1))
         .threePointArc(pt(r0, am), pt(r0, a0)).close())
    return w.extrude(z1 - z0)


def box(x0, x1, y0, y1, z0, z1):
    return (cq.Workplane("XY").box(x1 - x0, y1 - y0, z1 - z0)
            .translate(((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2)))


def zcyl(x, y, d, z0, z1):
    return (cq.Workplane("XY").workplane(offset=z0).center(x, y)
            .circle(d / 2).extrude(z1 - z0))


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
        # +0.02 avoids an exactly tangent sphere/tube seam (non-manifold STL)
        ring = ring.union(cq.Workplane().sphere(GROOVE_R + 0.02).translate(
            (rho_c * math.sin(a), -rho_c * math.cos(a), z_c)))
    return ring.translate((0, CROWN_RX, 0))


# =============================================================================
# PARTS
# =============================================================================

def build_housing():
    """Main body: crowned ribbed face + open-back tub + all vehicle features."""
    big = torus()
    # --- outer skin ------------------------------------------------------
    body = outline_prism(0, -5, DEPTH).intersect(big)
    body = body.faces("%TORUS").edges().fillet(FACE_EDGE_FILLET)
    flange = outline_prism(FLANGE_W, FLANGE_Y0, FLANGE_Y0 + FLANGE_T)
    body = body.union(flange)
    for (ex, ez) in EARS:
        xw = math.copysign(FACE_L / 2 - 4.0, ex)
        ear = (cq.Workplane("XZ").center((xw + ex) / 2, ez)
               .rect(abs(ex - xw), EAR_W).extrude(-(EAR_Y[1] - EAR_Y[0]))
               .translate((0, EAR_Y[0], 0)))
        ear = ear.union(cq.Workplane("XZ").center(ex, ez).circle(EAR_W / 2)
                        .extrude(-(EAR_Y[1] - EAR_Y[0]))
                        .translate((0, EAR_Y[0], 0)))
        body = body.union(ear)
    for px in PEGS:
        pz = outline_z_extent(px)[1]
        body = body.union(box(px - PEG[0] / 2, px + PEG[0] / 2,
                              EAR_Y[1] - PEG[1], EAR_Y[1],
                              pz - 3.0, pz + PEG[2]))

    # --- hollow it (open back) -----------------------------------------------
    cavity = outline_prism(-WALL_T, -5, DEPTH + 5).intersect(torus(-FACE_T))
    body = body.cut(cavity)

    # --- internal structure (clipped so it fuses with the walls) ------------
    clip = outline_prism(-(WALL_T - 0.6), -5, DEPTH).intersect(
        torus(-(FACE_T - 0.6)))
    px, py = PIVOT
    zb = HUB_HALF + WASHER[2] + BOSS_GAP
    inner = (zcyl(px, py, HUB_D, zb, 40)
             .union(zcyl(px, py, HUB_D, -40, -zb))
             .union(box(px - 1.5, px + 1.5, -2, py, zb, 40))
             .union(box(px - 1.5, px + 1.5, -2, py, -40, -zb)))
    # travel-stop ring around the lower hub; gap = finger travel
    r0, r1, (sz0, sz1) = STOP_SECTOR
    f_w = FINGER[2]
    gap0 = 180.0 + POSE_FULL - f_w / 2
    gap1 = 180.0 + POSE_REST + f_w / 2
    inner = inner.union(annular_sector(PIVOT, r0, r1, gap1, gap0 + 360.0,
                                       sz0, sz1, n=96))
    # cable-anchor block
    inner = inner.union(box(-71, CHANNEL_X[1] + 2.2, 16.0, DEPTH + 1,
                            -16.0, 16.0))
    # pad behind the badge
    inner = inner.union(badge_prism(3.0, -2.0, 6.6))
    inner = inner.intersect(clip)
    body = body.union(inner)

    # --- cuts --------------------------------------------------------------
    # pivot pin (inserted from the top, blind at the bottom)
    body = body.cut(zcyl(px, py, PIN_HOLE_PRESS, pin_bottom_z(), 45))
    # strap slot
    slot = (cq.Workplane("XZ").center(SLOT_X, 0)
            .slot2D(SLOT_LEN, SLOT_W, angle=90).extrude(-15)
            .translate((0, -5, 0)))
    body = body.cut(slot)
    # decorative grooves
    for zg in GROOVE_Z:
        ext = outline_x_extent(zg, -GROOVE_INSET)
        if ext:
            body = body.cut(groove_tool(zg, ext[0] + GROOVE_R,
                                        ext[1] - GROOVE_R))
    # badge pocket (flat floor)
    body = body.cut(badge_prism(0.0, -5.0, BADGE_FLOOR_Y))
    # cable channel, sheath exit, cable pass-through, clamp insert
    body = body.cut(box(CHANNEL_X[0], CHANNEL_X[1], CHANNEL_FLOOR_Y,
                        DEPTH + 2, -CHANNEL_HALF_W, CHANNEL_HALF_W))
    body = body.cut(box(-80, CHANNEL_X[0] + 1, CABLE_Y - SHEATH_D / 2 - 0.4,
                        DEPTH + 2, -(SHEATH_D / 2 + 0.4), SHEATH_D / 2 + 0.4))
    body = body.cut(box(CHANNEL_X[1] - 1, CHANNEL_X[1] + 4,
                        CABLE_Y - CABLE_D / 2 - 0.3, DEPTH + 2,
                        -(CABLE_D / 2 + 0.3), CABLE_D / 2 + 0.3))
    ins = (cq.Workplane("XZ").center(SLIDER_X_NOM, CLAMP_Z)
           .circle(INSERT_D / 2).extrude(-(INSERT_L + 0.5))
           .translate((0, CHANNEL_FLOOR_Y - INSERT_L, 0)))
    body = body.cut(ins)
    # ear holes
    for (ex, ez) in EARS:
        body = body.cut(cq.Workplane("XZ").center(ex, ez)
                        .circle(EAR_HOLE_D / 2).extrude(-40)
                        .translate((0, -5, 0)))
    return body


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
    # stiffening web between the cheeks (stays clear of the webbing loop)
    web_end = (18.0 * math.cos(math.radians(STRAP_ARM_MID)),
               18.0 * math.sin(math.radians(STRAP_ARM_MID)))
    lev = lev.union(capsule_xy((0, 0), 2.0, web_end, 1.5,
                               -CHEEK_Z[0] - 0.01, CHEEK_Z[0] + 0.01))
    # hook arm + nipple block
    hx, hy = HOOK_LF
    lev = lev.union(capsule_xy((0, 0), 6.0, (hx, hy), 5.5,
                               -HOOK_HALF_T, HOOK_HALF_T))
    lev = lev.union(box(hx - 3.5, hx + 9.0, hy - 6.0, hy + 5.0,
                        -HOOK_HALF_T, HOOK_HALF_T))
    # stop finger
    fr0, fr1, fw, (fz0, fz1) = FINGER
    lev = lev.union(annular_sector((0, 0), fr0, fr1, 180 - fw / 2,
                                   180 + fw / 2, fz0, fz1, n=24))
    # --- cuts ---------------------------------------------------------------
    lev = lev.cut(zcyl(0, 0, PIN_HOLE_RUN, -40, 40))
    lev = lev.cut(zcyl(sp[0], sp[1], PIN_HOLE_PRESS, -30, 30))
    # cable slot: fan of +-23 deg around -X, open towards +Y for fitting
    cw = CABLE_D / 2 + 0.3
    t = math.tan(math.radians(23))
    fan = (cq.Workplane("XY").workplane(offset=-cw)
           .polyline([(hx + 0.5, hy - cw), (hx - 15, hy - cw - 15 * t),
                      (hx - 15, hy + 30), (hx + 0.5, hy + 30)]).close()
           .extrude(2 * cw))
    lev = lev.cut(fan)
    # nipple cradle on the +X side of the bearing face, open towards +Y
    nr = NIPPLE_D / 2 + 0.6
    cradle = box(hx, hx + 12, hy, hy + 30, -nr, nr).union(
        cq.Workplane("YZ").workplane(offset=hx).center(hy, 0).circle(nr)
        .extrude(12))
    lev = lev.cut(cradle)
    return lev


def pose_lever(shape, pose_deg):
    return (shape.rotate((0, 0, 0), (0, 0, 1), pose_deg)
            .translate((PIVOT[0], PIVOT[1], 0)))


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
    # two clamp slots (Z = +-CLAMP_Z) so the same slider fits LH and RH
    for zc in (CLAMP_Z, -CLAMP_Z):
        slot = (cq.Workplane("XZ").center(0, zc)
                .slot2D(2 * trav + 3.4, 3.4, angle=0).extrude(-(y1 - y0 + 2))
                .translate((0, y0 - 1, 0)))
        cbore = (cq.Workplane("XZ").center(0, zc)
                 .slot2D(2 * trav + 6.2, 6.2, angle=0).extrude(-4.0)
                 .translate((0, y1 - 3.5, 0)))
        s = s.cut(slot).cut(cbore)
    return s.translate((x_center, 0, 0))


def build_fit_gauge(housing=None):
    """Quick-print slice (flange, ears, pegs) to test-fit the door card."""
    housing = housing if housing is not None else build_housing()
    # (EAR_Y[1] - 0.1: a cut exactly tangent to the pin bore is non-manifold)
    return housing.intersect(box(-120, 120, FLANGE_Y0 - 1.5, EAR_Y[1] - 0.1,
                                 -60, 60))


def build_badge():
    """Customisable badge insert (generic stripe motif - replace with yours)."""
    b = badge_prism(-BADGE_CLEAR, -6.0, BADGE_FLOOR_Y).intersect(
        torus(BADGE_PROUD))
    # three slanted engraved stripes, 0.6 deep
    cx = 0.5 * (BADGE_X[0] + BADGE_X[1])
    stripes = None
    for i in (-1, 0, 1):
        st = (cq.Workplane("XZ").center(cx + i * 8.0, 0)
              .rect(3.2, 40).extrude(-20).translate((0, -10, 0))
              .rotate((cx + i * 8.0, 0, 0), (cx + i * 8.0, 1, 0), 25))
        stripes = st if stripes is None else stripes.union(st)
    shell = torus(BADGE_PROUD + 1.0).cut(torus(BADGE_PROUD - 0.6))
    b = b.cut(stripes.intersect(shell).intersect(
        badge_prism(-BADGE_CLEAR - 1.6, -6.0, BADGE_FLOOR_Y)))
    return b


def build_hardware(pose_deg=POSE_REST):
    """Stainless pins, washers, M3 clamp screw + insert (assembly position)."""
    px, py = PIVOT
    zb = HUB_HALF + WASHER[2] + BOSS_GAP
    bottom = pin_bottom_z()
    hw = {}
    hw["pivot_pin"] = (zcyl(px, py, PIN_D, bottom, bottom + PIVOT_PIN_L)
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
                    .polygon(6, 2.9).extrude(-2.0).translate((0, y_top + 1.0, 0)))
    hw["clamp_screw"] = screw.union(head)
    hw["insert"] = (cq.Workplane("XZ").center(SLIDER_X_NOM, CLAMP_Z)
                    .circle(2.3).circle(1.5).extrude(-INSERT_L)
                    .translate((0, CHANNEL_FLOOR_Y - INSERT_L, 0)))
    return hw


def build_cable(pose_deg=POSE_REST, slider_x=SLIDER_X_NOM):
    """Representative OEM cable end: sheath, fitting, inner cable, nipple."""
    hx, hy = lever_point(HOOK_LF, pose_deg)
    fx = slider_x - FITTING[0] / 2          # sheath seat face
    sheath = (cq.Workplane("YZ").workplane(offset=-110).center(CABLE_Y, CABLE_Z)
              .circle(SHEATH_D / 2).extrude(fx - 2 - (-110)))
    fitting = (cq.Workplane("YZ").workplane(offset=fx).center(CABLE_Y, CABLE_Z)
               .rect(FITTING[1] - 1.0, FITTING[1] - 1.0).extrude(FITTING[0] - 0.4)
               .edges("|X").fillet(1.5))
    # inner cable runs straight from the fitting exit to the bearing face;
    # the nipple seats square on the (rotating) bearing face
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
    print("cable travel", round(CABLE_TRAVEL, 2), "mm; slider travel",
          SLIDER_TRAVEL, "mm")
