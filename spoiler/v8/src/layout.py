"""v8 layout: v7 (four 325 mm pieces) with each END piece split lengthwise into a front half and a rear half, as marked
by the user. Six printed pieces and ten identical bow-tie keys. Shared by the v8 scripts.
The key is the v6 key (v6/src/bowtie.py)."""
E_PATH = 'v6/out/E2.stl'          # solid spoiler body, built by v6/src/run_all.sh
OUT, ASM, PRN, DOC = 'v8/out', 'v8/assembled', 'v8/print', 'v8/docs'
HALF = 650.0                      # the spoiler spans x = -650 .. +650 mm
SEAMS = [-325.0, 0.0, 325.0]      # the three cross seams of v7 (four pieces of 325 mm)

# Lengthwise cut of the two end pieces: the plane z = CUT_Z (car coordinates, +z to the rear). It runs from the middle
# of the end piece's seam face straight out along the piece and leaves through the fin's rear edge at |x| = 592 mm.
# The four lines the user drew wander between z = 30 and 165 mm; averaged along the span they sit at z = 80-100 mm.
# z = 100 is in that band, stays 11 mm clear of the seam's front key pocket (z = 111-135), and puts the cut where the
# part is 12-16 mm thick.
CUT_Z = 100.0

# Bow-tie keys, all identical. Cross-seam keys (as v7): centre (x, z), lying across the seam (x direction).
# The underside has a V-shaped kink line where the roof meets the tailgate (z = 148 on the centre line, curving forward
# to z = 141 at x = +-325 and z = 134 at x = +-400); every pocket sits fully on one flat facet, clear of it.
KEY_Z = {-325.0: [123.0, 161.0], 0.0: [132.0, 165.0], 325.0: [123.0, 161.0]}
# Lengthwise keys across the z = CUT_Z cut, on the underside of each end piece, lying across the cut (z direction).
# |x| = 400 and 430: further in, the front half is too thin over the pocket; further out the underside bends (fin root).
LKEY_X = [400.0, 430.0]

# id, x from, x to, z side ('F' = z <= CUT_Z, 'R' = z >= CUT_Z, None = whole chord), file stem, label
PIECES = [
    ('P1F', -650.0, -325.0, 'F', 'v8_1F_LEFT_END_FRONT', 'left end, front half (with the fin tip)'),
    ('P1R', -650.0, -325.0, 'R', 'v8_1R_LEFT_END_REAR', 'left end, rear half'),
    ('P2', -325.0, 0.0, None, 'v8_2_LEFT_MID', 'left middle'),
    ('P3', 0.0, 325.0, None, 'v8_3_RIGHT_MID', 'right middle'),
    ('P4R', 325.0, 650.0, 'R', 'v8_4R_RIGHT_END_REAR', 'right end, rear half'),
    ('P4F', 325.0, 650.0, 'F', 'v8_4F_RIGHT_END_FRONT', 'right end, front half (with the fin tip)'),
]
IDS = [p[0] for p in PIECES]
STEM = {p[0]: p[4] for p in PIECES}
LABEL = {p[0]: p[5] for p in PIECES}

def key_list():
    """every key: centre (x, z) on the underside, the direction it lies across (unit vector in the xz plane), and the
    two pieces it locks together"""
    keys = []
    for xs in SEAMS:
        a, b = {-325.0: ('P1R', 'P2'), 0.0: ('P2', 'P3'), 325.0: ('P3', 'P4R')}[xs]
        for zc in KEY_Z[xs]:
            keys.append(dict(kind='cross', x=xs, z=zc, across=(1.0, 0.0, 0.0), pieces=(a, b)))
    for side, (f, r) in [(-1, ('P1F', 'P1R')), (1, ('P4F', 'P4R'))]:
        for ax in LKEY_X:
            keys.append(dict(kind='lengthwise', x=side * ax, z=CUT_Z, across=(0.0, 0.0, 1.0), pieces=(f, r)))
    return keys

N_KEYS = len(key_list())          # 10
COL = {'P1F': (110, 116, 128), 'P1R': (58, 62, 70), 'P2': (232, 118, 34), 'P3': (246, 176, 66),
       'P4R': (58, 62, 70), 'P4F': (110, 116, 128)}
KEY_COL = (60, 170, 230)
