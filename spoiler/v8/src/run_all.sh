#!/bin/sh
# Rebuild the v8 package (6 pieces: v7 with each end piece split lengthwise; 10 bow-tie keys).
# Run from the spoiler/ folder:  sh v8/src/run_all.sh
# v8 cuts the same solid body as v6 and v7, so v6/out/E2.stl is built first if it is missing.
set -e
[ -f v6/out/E2.stl ] || sh v6/src/run_all.sh
mkdir -p v8/out v8/print v8/assembled v8/docs
python3 v8/src/p1_parts.py        # 6 pieces + bow-tie pockets + keys                     -> assembled/
python3 v8/src/p2_validate.py     # watertight / self-intersection / clearance / flush    (stops here if a check fails)
python3 v8/src/p3_place.py        # bed placement for 420 x 420 x 500                     -> print/
python3 v8/src/p4_figures.py      # figures                                               -> docs/
python3 v8/src/p5_package.py      # zip of README + print/ + assembled/ + docs/           -> Polo_spoiler_v8_print_package.zip
# (v8/src/p0_marks.py re-traces the user's marked lines into data/user_marks_3d.npz; it needs the v7 files.)
