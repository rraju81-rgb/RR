"""v10 layout: the v6 spoiler shape (same outside as v6-v9) in SIX PARTS as the owner marked them: three sections across
the span (cut at the v9 seams x = +-216.7 mm), each cut again into a FRONT and a REAR part near the middle of the chord.
Cored from the hidden underside to a skin no thicker than 10 mm (as v9), with a new smooth GROOVED RIM at the back where
the spoiler sits on the car, and pinned joints with 30-degree self-centring tongues and grooves.
Shared by the v10 scripts. Car coordinates as v6-v9: X across the car, Y up, +Z to the rear, mm."""
import numpy as np

E_PATH = 'v6/out/E2.stl'          # solid spoiler body, built by v6/src/run_all.sh
CAR_PATH = 'v6/car/out/car_body_conf.ply'   # car body under the spoiler (1.5 mm tape gap)
OUT, ASM, PRN, DOC = 'v10/out', 'v10/assembled', 'v10/print', 'v10/docs'
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

# Coring (as v9): every visible surface stays exactly as it is; material deeper than T_SKIN below them is removed from the
# hidden underside, so no part is thicker than 10 mm. The fin tips keep a thinner wall (S_FIN).
T_SKIN = 8.5
S_FIN, FIN_X = 5.5, (585.0, 600.0)
VOX = 0.5                         # voxel size (mm); grids are aligned to one global lattice so sections match at seams
MARGIN = 12.0                     # each section's voxel grid reaches this far past its seams
UNDER_GAP = 4.0                   # a face sits on the car if the car is within this along its normal
CUT_GAP = 120.0                   # a face faces the car (may be trimmed) if the car is within this along its normal

# Grooved rim (new in v10). Along one smooth line where the spoiler sits on the car at the back: behind the line, the
# spoiler's original underside (the SKIRT, below); in front of it, a GROOVE for a bead of PU adhesive, RIM_GAP + RIM_LEG
# wide at the car, then a FRONT LEG RIM_LEG wide on the car, leaning forward at RIM_SLOPE up to the skin; then the pocket.
# The leg is a clean sweep along the smooth line, and every face that looks forward leans at 45 degrees, so the rear
# parts print standing on their front cut without support.
RIM_G = (2.0, 2.5)                # the rim's rear edge follows the contact boundary between these gaps (car to underside)
RIM_WIN, RIM_SIG = 41.0, 25.0     # rim curve: lower envelope over 41 mm, then Gaussian smoothing over 25 mm
RIM_LEG, RIM_GAP = 4.0, 3.0       # leg width on the car, groove mouth
RIM_SLOPE = 45.0                  # legs lean this far from vertical
RIM_X = 560.0                     # the rim runs |x| <= RIM_X (the skin meets the car just inside this)
RIM_S = 14.0                      # legs are built to this height above the car (above the deepest pocket)
# Behind the rim line the skin under the top is T_SKIN + LIP_EXTRA (7 mm), reached over LIP_RAMP, so that with the skirt
# below it (SKIRT) nothing there is thicker than 9.5 mm; the room in between is hollow, out of sight above the skirt.
LIP_EXTRA, LIP_RAMP = -1.5, 4.0
# Behind the rim line the spoiler's own underside (the rear contact land and the lip's underside) stays exactly as it
# is, as a SKIRT at least SKIRT thick: any material that has to come out there to stay under 10 mm is taken from above
# the skirt, out of sight, through the groove. From outside the back edge looks exactly like the original spoiler.
SKIRT = 2.5

# Joints. Span seams (x = +-216.67): a tongue on the side parts and a groove in the centre parts, with two dowel pins per
# front and per rear segment. Front/rear cuts: both parts print standing on the cut, so both faces carry a groove and
# loose double-sided splines sit between them, with dowel pins between and beyond the splines.
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

# Parts (the owner's numbering): 1 left rear, 2 left front, 3 centre rear, 4 centre front, 5 right rear, 6 right front
PARTS = [('P1', 'L', 'rear', 'v10_1_LEFT_REAR', 'left rear'), ('P2', 'L', 'front', 'v10_2_LEFT_FRONT', 'left front (with the fin)'),
         ('P3', 'C', 'rear', 'v10_3_CENTRE_REAR', 'centre rear'), ('P4', 'C', 'front', 'v10_4_CENTRE_FRONT', 'centre front'),
         ('P5', 'R', 'rear', 'v10_5_RIGHT_REAR', 'right rear'), ('P6', 'R', 'front', 'v10_6_RIGHT_FRONT', 'right front (with the fin)')]
IDS = [p[0] for p in PARTS]
SEC = {p[0]: p[1] for p in PARTS}; HALF_OF = {p[0]: p[2] for p in PARTS}
STEM = {p[0]: p[3] for p in PARTS}; LABEL = {p[0]: p[4] for p in PARTS}
def part_id(sec, half):
    return [p[0] for p in PARTS if p[1] == sec and p[2] == half][0]
