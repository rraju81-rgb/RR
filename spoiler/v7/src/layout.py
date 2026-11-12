"""v7 layout: the solid v6 spoiler cut into FOUR EQUAL pieces (325 mm each) with six bow-tie keys.
Shared by the v7 scripts. The key itself is the v6 key (v6/src/bowtie.py); only the cuts and pocket positions change."""
E_PATH = 'v6/out/E2.stl'          # solid spoiler body, built by v6/src/run_all.sh
OUT, ASM, PRN, DOC = 'v7/out', 'v7/assembled', 'v7/print', 'v7/docs'
HALF = 650.0                      # the spoiler spans x = -650 .. +650 mm
SEAMS = [-325.0, 0.0, 325.0]      # three cuts -> four pieces of 325 mm

# Key centres along the chord (z), per seam. The underside has a V-shaped kink line where the roof meets the tailgate;
# it runs at z = 148 on the centre line and curves forward to z = 141 at x = +-325. Each pocket sits fully on one flat
# facet, at least 3 mm clear of that kink and of the roof-edge bend behind it (z = 177-180), so the key ends flush.
KEY_Z = {-325.0: [123.0, 161.0], 0.0: [132.0, 165.0], 325.0: [123.0, 161.0]}

# id, x from, x to, file stem, label
PIECES = [
    ('P1', -650.0, -325.0, 'v7_1_LEFT_END', 'left end (fin)'),
    ('P2', -325.0, 0.0, 'v7_2_LEFT_MID', 'left middle'),
    ('P3', 0.0, 325.0, 'v7_3_RIGHT_MID', 'right middle'),
    ('P4', 325.0, 650.0, 'v7_4_RIGHT_END', 'right end (fin)'),
]
IDS = [p[0] for p in PIECES]
STEM = {p[0]: p[3] for p in PIECES}
LABEL = {p[0]: p[4] for p in PIECES}
N_KEYS = sum(len(v) for v in KEY_Z.values())     # 6
COL = {'P1': (70, 74, 82), 'P2': (232, 118, 34), 'P3': (246, 176, 66), 'P4': (70, 74, 82)}
KEY_COL = (60, 170, 230)
