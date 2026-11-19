"""v9 layout: the v6 spoiler shape cut into SIX EQUAL pieces across the span, cored from the hidden underside to a skin
no thicker than 10 mm, joined with dowel pins in holes and a self-centring tongue and groove with 30 degree flanks.
Shared by the v9 scripts. Car coordinates as v6-v8: X across the car, Y up, +Z to the rear, mm."""
E_PATH = 'v6/out/E2.stl'          # solid spoiler body, built by v6/src/run_all.sh (same outer shape as v6-v8)
CAR_PATH = 'v6/car/out/car_body_conf.ply'   # car body under the spoiler (the 1.5 mm tape gap): tells the underside apart
OUT, ASM, PRN, DOC = 'v9/out', 'v9/assembled', 'v9/print', 'v9/docs'
HALF = 650.0                      # the spoiler spans x = -650 .. +650 mm
N_PIECES = 6
W_PIECE = 2 * HALF / N_PIECES     # 216.67 mm
SEAMS = [-HALF + W_PIECE * k for k in range(1, N_PIECES)]      # -433.3, -216.7, 0, 216.7, 433.3

# Coring. The top, the lip edge, the ends and the fins' outer faces stay exactly as they are. Material more than T_SKIN
# below them is removed from underneath, so no part of a piece is thicker than 10 mm:
# - under the ridge, a pocket opens onto the hidden underside (the car side);
# - where the lip leaves the car its root was 11-13 mm thick between the top and its own underside: that underside is
#   trimmed to T_SKIN below the top (at most ~3 mm, on the underside of the lip, only where it was thicker);
# - a SEAL RIM, RIM_W wide, is kept where the underside leaves the car at the back, so the spoiler still sits on the car
#   there and no gap shows under the lip;
# - the fin tips, solid triangles ~13.5 mm across, keep a thinner wall (S_FIN) and are cored from the pillar side.
# Where the spoiler is thinner than T_SKIN (the front band on the roof, the lip) it stays solid.
T_SKIN = 8.5                      # main skin; the voxel distance is good to +-0.45 mm, so 8.05-8.95 mm
S_FIN, FIN_X = 5.5, (585.0, 600.0)        # fin-tip wall, and the |x| range over which the skin blends to it
RIM_W = 3.5                       # seal rim width (mm, in plan), on the car side of the line where the underside leaves the car
VOX = 0.5                         # voxel size for the distance field (mm)
UNDER_GAP = 4.0                   # a face sits on the car if the car is within this along its normal (tape gap 1.5)
CUT_GAP = 120.0                   # a face faces the car (may be trimmed) if the car is within this along its normal

# Joints at the five seams. Every seam: two dowel pins in holes, and a tongue on one face that seats in a groove in the
# other. The tongue runs along the middle of the skin; its sides lean CHAMFER_DEG off the joining direction, so the
# pieces slide together and centre themselves (the reference the outer surfaces line up on), and it prints without
# support. Female faces (groove) go on the bed; a male face (tongue) is always printed on top.
CHAMFER_DEG = 30.0
TONGUE_BASE, TONGUE_H = 4.5, 2.5          # tongue width at the face and height (top width 4.5 - 2*2.5*tan30 = 1.6 mm)
CLEAR = 0.20                              # groove clearance per side; the groove is also 0.3 mm deeper than the tongue
GROOVE_EXTRA = 0.30
MIN_SKIN_TONGUE = 7.5                     # the tongue runs only where the skin is at least this thick (shoulders >= 1.5)
# 3 mm dowel pins (steel or brass rod, or printed), 18 mm long, in 3.3 mm holes 9.5 mm deep each side. Near the ends the
# skin slopes ~6 degrees along the span, so a straight hole drifts ~1.1 mm off the skin's middle 9.5 mm in: a 3 mm pin
# still leaves >= 1.5 mm of wall there (a 4 mm pin 12 mm deep left only 0.7 mm at the outer seams).
PIN_D, HOLE_D, HOLE_DEPTH = 3.0, 3.3, 9.5
PIN_L = 18.0
HOLE_CHAMFER = 0.4                        # 30-degree lead-in round each hole mouth (radial)
MIN_SKIN_PIN = 8.0                        # pins sit where the skin is at least this thick (walls >= 2.35 mm at the face)
PIN_GAP = 3.0                             # gap between a pin hole and the end of the tongue

# Which face of each seam carries the tongue (male, 'M') and which the groove ('F'). The end pieces print standing on
# their only cut face, so it must be a groove; each middle piece stands on its groove face with its tongue face on top.
# With six pieces and five seams that leaves the centre seam groove-to-groove: it takes a loose double-sided spline.
SEAM_SIDES = {-433.3: ('F', 'M'), -216.7: ('F', 'M'), 0.0: ('F', 'F'), 216.7: ('M', 'F'), 433.3: ('M', 'F')}   # (left, right)
SPLINE_SEAM = 0.0

# id, x from, x to, file stem, label
PIECES = [('P%d' % (k + 1), -HALF + W_PIECE * k, -HALF + W_PIECE * (k + 1), 'v9_%d_%s' % (k + 1, s), lab)
          for k, (s, lab) in enumerate([('LEFT_END', 'left end (with the fin)'), ('LEFT_OUTER', 'left outer'),
                                        ('LEFT_CENTRE', 'left of centre'), ('RIGHT_CENTRE', 'right of centre'),
                                        ('RIGHT_OUTER', 'right outer'), ('RIGHT_END', 'right end (with the fin)')])]
IDS = [p[0] for p in PIECES]
STEM = {p[0]: p[3] for p in PIECES}
LABEL = {p[0]: p[4] for p in PIECES}

def seam_key(x):
    return round(x, 1) if abs(x) > 1e-6 else 0.0

def sides(x):
    return SEAM_SIDES[seam_key(x)]
