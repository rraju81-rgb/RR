"""v15 layout: the v14 spoiler (the v6 shape with both ducktail lip ends blended in and the step under the back faired
out) in the same SIX PARTS as v10: three sections across the span (cut at x = +-216.7 mm), each cut again into a FRONT
and a REAR part near the middle of the chord. New in v15: a thin shell, open underneath again (v14's closed underside
made the parts much thicker): a 4 mm skin under every visible surface, the opening faded in at the front (tape band)
and the back (adhesive band) so the underside has no step or line, and joint lands at the cuts for the pins and tongues.
Pinned joints with 30-degree self-centring tongues and grooves, as v10. Shared by the v15 scripts. Car coordinates as
v6-v14: X across the car, Y up, +Z to the rear, mm."""
import numpy as np

E2_PATH = 'v6/out/E2.stl'         # solid spoiler body as in v6-v12, built by v6/src/run_all.sh
E3_PATH = 'v14/out/E3.stl'        # v14: E2 with its two outer rear corners blended (v14/src/e3_corners.py)
E_PATH = 'v14/out/E4.stl'         # v14: E3 with the step along the back of the underside faired out (v14/src/e4_underside.py);
                                  # v15 cores this same body

# Blended outer rear corners (new in v14). At each outer rear corner the ducktail lip is a thin blade sitting on the
# rounded end of the body: a sharp notch under it, a squared end, and a small step beyond it. e3_corners.py rebuilds the
# corner with a rolling-ball fillet (radius R_FILLET) along CORNER_CURVE (the notch and the step, traced from the original
# surface's crease edges; |x| here, mirrored for the left side), fully applied within CORNER_W[0] mm of the curve and
# fading out by CORNER_W[1]; the corner is rebuilt inside CORNER_BOX and spliced in on its faces.
CORNER_CURVE = [(418, 2.0, 182.8), (426, 2.0, 182.8), (435, 1.9, 182.7), (450, 1.8, 182.6), (465, 1.6, 182.2), (478, 1.4, 181.2), (487, 1.3, 180.2),
                (493, 1.0, 179.2), (498, 0.5, 178.0), (503, 0.1, 176.5), (508, -0.2, 174.0), (513, -1.6, 171.8),
                (518, -3.4, 169.8), (523, -4.7, 166.5)]
CORNER_BOX = ((410.0, -28.0, 142.0), (548.0, 26.0, 207.0))     # |x|, y, z
R_FILLET = 4.5
CORNER_W = (8.0, 16.0)
CORNER_WS = (4.0, 9.0)      # the smoothing below applies fully within 4 mm of the corner curve, none beyond 9 mm
CORNER_SIG = 0.8            # Gaussian smoothing (mm) of the closed field: rounds the lip's squared end and its crease
# v14: the lip's outer end (the last stretch of the corner curve): a 12 mm rolling-ball fillet and stronger smoothing there,
# so the lip runs into the rounded end in one broad curve
CORNER_END = [(493, 1.0, 179.2), (498, 0.5, 178.0), (503, 0.1, 176.5), (508, -0.2, 174.0), (513, -1.6, 171.8),
              (518, -3.4, 169.8), (523, -4.7, 166.5)]
R_END = 12.0
CORNER_END_W = (10.0, 24.0)
CORNER_END_SIG = 3.0
# v14: the step along the back of the underside (where the band conformed to the car meets the original underside):
# smoothed (Gaussian, STEP_SIG mm) within STEP_W of its line, faded out over |x| = STEP_X towards the ends
STEP_SIG, STEP_W, STEP_X = 3.5, (8.0, 14.0), (430.0, 495.0)
CAR_PATH = 'v6/car/out/car_body_conf.ply'   # car body under the spoiler (1.5 mm tape gap)
OUT, ASM, PRN, DOC = 'v15/out', 'v15/out/assembled', 'v15/print', 'v15/docs'   # ASM: parts and pins in place on the car (working copies for the checks, figures and renders; not part of the print set)
HALF = 650.0
XS = HALF / 3.0                   # span seams at x = -216.67 and +216.67 (the v9 seams 2|3 and 4|5)
SECTIONS = [('L', -HALF, -XS), ('C', -XS, XS), ('R', XS, HALF)]

# Front/rear cut: one vertical plane per section, n . p = d with n pointing to the rear. The centre plane is z = C0; the
# side planes run from z = C0 at the span seams to z = C1 at x = +-X1, so the three cuts meet at the span seams and the
# cut follows the owner's line (about the middle of the chord, a little further forward towards the ends).
C0, C1, X1 = 122.0, 100.0, 585.0
def chord_plane(sec):
    if sec == 'C':
        return np.array([0.0, 0.0, 1.0]), C0
    sx = -1.0 if sec == 'L' else 1.0
    a = np.array([sx * XS, C0]); b = np.array([sx * X1, C1])            # (x, z) points the plane passes through
    t = (b - a) / np.linalg.norm(b - a)
    n = np.array([-t[1], 0.0, t[0]]) * sx                               # horizontal, perpendicular to the cut line
    if n[2] < 0: n = -n                                                 # pointing to the rear
    return n, float(n[0] * a[0] + n[2] * a[1])

# Coring (v15): every visible surface stays exactly as it is, with a skin T_SKIN thick under it; everything deeper is
# removed, open through the faces that sit on the car (in front of the rim line) and the fins' pillar side. T_SKIN is the
# thickness of the spoiler's own front edge, the thinnest the shape has.
T_SKIN = 4.0
S_FIN, FIN_X = 4.0, (585.0, 600.0)
VOX = 0.5                         # voxel size (mm); grids are aligned to one global lattice so sections match at seams
MARGIN = 12.0                     # each section's voxel grid reaches this far past its seams
UNDER_GAP = 4.0                   # a face sits on the car if the car is within this along its normal
CUT_GAP = 120.0                   # a face faces the car (may be trimmed) if the car is within this along its normal

# Smooth tip (new in v14). One smooth line along the back (as v10: where the spoiler's underside leaves the car at the
# back, smoothed), and on it ONE rounded tip that sits on the car. In front of the tip the pocket ceiling comes down a
# smooth 45-degree slope to the tip (45 degrees so the rear parts still print standing on their front cut without
# support); behind the tip the spoiler's own underside carries on exactly as it is. No groove, no leg, no steps.
RIM_G = (2.0, 2.5)                # the rim line follows the contact boundary between these gaps (car to underside)
RIM_WIN, RIM_SIG = 41.0, 25.0     # rim line: lower envelope over 41 mm, then Gaussian smoothing over 25 mm
RIM_X = 560.0                     # the rim runs |x| <= RIM_X (the skin meets the car just inside this)
RIM_FADE = 12.0                   # (v12 faded the tip out over 548-560 mm, which left a crease where it stopped)
RIM_END = 640.0                   # v14: the tip's field runs on to the spoiler's ends (no switch-off crease)
END_FADE = (340.0, 470.0)    # |x| over which the tip's face moves forward towards the ends
TIP_SHIFT = 10.0             # v14, no brim: the pocket's back face starts this far (mm) forward of the contact line
END_SHIFT = 22.0             # and this far at the spoiler's ends; behind it the spoiler's own underside carries on, flush
                                  # smoothly into the spoiler's own underside; the hidden channel keeps it under 10 mm there
TIP_T = 1.5                       # the tip sits this far forward of the rim line, inside the contact band
EDGE_DROP = 0.4                   # v14: the pocket's round starts this far below the underside, so it leaves it at ~26 deg (a clean edge)
TIP_R = 4.0                       # v14: radius of the round where the pocket's back face leaves the underside
TIP_EPS = 0.05                    # the tip's lowest point is this far below the original underside (so it just touches it)
M_FRONT = 1.0                     # slope of the tip's front face (1 = 45 degrees, the steepest that prints without support)
K_BLEND = 2.5                     # fillet between the pocket ceiling and the slope
# Where the back edge is deeper than C_MIN (the outer zone, |x| > ~180 mm, up to 16 mm deep), a solid tip would be
# thicker than 10 mm. There it is hollow inside: a hidden channel along the back, closed all round by a SKIN_V top skin,
# a SKIRT under it (the spoiler's own underside, unchanged) and the WALL of the 45-degree slope. The channel runs through
# the span seams, so each part's channel opens only on its seam face (one closed shell per part, no trapped cavity);
# once the parts are glued it is sealed. From outside nothing shows.
SKIN_V = 6.0
SKIRT = 2.5
WALL = 3.0                        # the slope's wall, measured square to it
SKIN_MIN = 6.0                    # v14: the top skin over the cavity thins to this where the part is shallow
CAV_MIN = 1.5                     # v14: the cavity is at least this tall wherever it is
FIN_OPEN_X = 570.0                # v14: beyond this |x| (the fins) the cavity opens on the hidden pillar side
JOINT_BAND, JOINT_SKIN, JOINT_CAV = 12.0, 9.5, 1.0   # v14: within JOINT_BAND of a joint face the top skin may be up to
                                  # JOINT_SKIN thick over a cavity of at least JOINT_CAV (room for the pin walls)
C_MIN = 10.0                      # the channel only where the back edge is deeper than this (so it is >= 1.5 mm wide)

# v15 shell, seen from below: the spoiler's own smooth underside everywhere, with ONE opening in the middle, nothing else.
#   front: where the part is thinner than OPEN_H it stays solid (the front band, where the VHB tape goes, 49-85 mm);
#   back:  a band BACK_W mm deep in front of the rim line (where the underside leaves the car at the back) stays closed:
#          the spoiler's own underside, which takes the adhesive bead;
#   the opening starts on those two lines with a 30-degree ramp (K_WALL = 1/tan) up to the 4 mm ceiling, front and
#   back alike: each meets the underside along one clean, crisp line (150 degrees). No rounding there: a round peels a
#   feather-thin sliver off the underside beside the edge, which broke up into a saw-tooth.
#   The back edge is up to 16 mm deep, so inside the back band a hidden channel keeps every wall T_CH thick; it runs
#   along the span and opens only on the span seam faces (one closed shell per part, sealed once the parts are glued).
OPEN_H = 7.0
BACK_W = 25.0
K_WALL = 1.73
T_CH = 4.0
WALL_FADE_X = (530.0, 570.0)      # both ramps fade out towards the spoiler's ends (the fins, open on their pillar side)
# Joint lands: within LAND[0] mm of a joint face (front/rear cut, span seam) the skin is LAND_T thick, for the pins
# (MIN_SKIN_PIN) and tongues (MIN_SKIN_TONGUE); it tapers smoothly back to T_SKIN by LAND[1] mm (a gentle swell, not a
# step). The span seams' lands end at the back band.
LAND_T = 8.6
LAND = (11.0, 36.0)
SHELL_SIG = 1.0                   # Gaussian smoothing (mm) of the removal field: no voxel steps, every inside corner rounded

# Joints. The print set is the six parts and one pin model (printed as many times as needed), nothing else.
# Span seams (x = +-216.67): a 30-degree tongue on the side parts and a groove in the centre parts, with dowel pins.
# Front/rear cuts: both parts print standing on the cut, so nothing may stand proud of it: dowel pins only, about every
# CUT_PIN_PITCH mm (v10 had loose splines here; v14 has none).
CHAMFER_DEG = 30.0
TONGUE_BASE, TONGUE_H = 4.5, 2.5
CLEAR = 0.20
GROOVE_EXTRA = 0.30
END_DEG = 45.0                    # tongue/groove ends taper 45 degrees off the joining direction (print-safe either way up)
MIN_SKIN_TONGUE = 7.5
PIN_D, HOLE_D, HOLE_DEPTH = 3.0, 3.3, 9.5
PIN_L = 18.0
HOLE_CHAMFER = 0.4
MIN_SKIN_PIN = 8.0
PIN_GAP = 3.0
CORNER_KEEP = 14.0                # joints keep this far from the point where four parts meet
CUT_PIN_PITCH = 80.0              # front/rear cuts: one pin about every 80 mm along the cut

# Parts (the owner's numbering): 1 left rear, 2 left front, 3 centre rear, 4 centre front, 5 right rear, 6 right front
PARTS = [('P1', 'L', 'rear', 'v15_1_LEFT_REAR', 'left rear'), ('P2', 'L', 'front', 'v15_2_LEFT_FRONT', 'left front (with the fin)'),
         ('P3', 'C', 'rear', 'v15_3_CENTRE_REAR', 'centre rear'), ('P4', 'C', 'front', 'v15_4_CENTRE_FRONT', 'centre front'),
         ('P5', 'R', 'rear', 'v15_5_RIGHT_REAR', 'right rear'), ('P6', 'R', 'front', 'v15_6_RIGHT_FRONT', 'right front (with the fin)')]
IDS = [p[0] for p in PARTS]
SEC = {p[0]: p[1] for p in PARTS}; HALF_OF = {p[0]: p[2] for p in PARTS}
STEM = {p[0]: p[3] for p in PARTS}; LABEL = {p[0]: p[4] for p in PARTS}
def part_id(sec, half):
    return [p[0] for p in PARTS if p[1] == sec and p[2] == half][0]
