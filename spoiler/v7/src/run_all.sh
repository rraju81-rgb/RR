#!/bin/sh
# Rebuild the v7 package (4 equal pieces + 6 bow-tie keys). Run from the spoiler/ folder:  sh v7/src/run_all.sh
# v7 cuts the same solid body as v6, so v6/out/E2.stl is built first if it is missing.
set -e
[ -f v6/out/E2.stl ] || sh v6/src/run_all.sh
mkdir -p v7/out v7/print v7/assembled v7/docs
python3 v7/src/p1_parts.py        # 4 pieces + bow-tie pockets + keys                    -> assembled/
python3 v7/src/p2_validate.py     # watertight / self-intersection / clearance / flush   (stops here if a check fails)
python3 v7/src/p3_place.py        # bed placement for 420 x 420 x 500                    -> print/
python3 v7/src/p4_figures.py      # figures                                              -> docs/
python3 v7/src/p5_package.py      # zip of README + print/ + assembled/ + docs/              -> Polo_spoiler_v7_print_package.zip
