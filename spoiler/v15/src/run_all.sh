#!/bin/sh
# Rebuild the v15 package: the six parts of v10 (3 across x front/rear) as a thin shell, open underneath: a 4 mm skin
# under the top, thickening smoothly to the joint lands at the cuts; solid where the part is thinner than 7 mm (the
# front band, where the tape goes, and the ducktail lip near its tip), and the opening starts from both with the same
# 30-degree ramp: no band, no hook, nothing wrapped round the back edge; the ducktail lip ends blended into the body
# (v14); pinned 30-degree joints. Run from the spoiler/ folder:  sh v15/src/run_all.sh
# (about an hour on 4 cores). v15 cores the same outer body as v14 (v14/out/E4.stl, built by the v14 scripts from
# the v6 solid and the car body under it); everything is built first if missing.
set -e
[ -f v6/out/E2.stl ] || sh v6/src/run_all.sh
[ -f v6/car/out/car_body_conf.ply ] || python3 v6/car/src/car_build_all.py
mkdir -p v14/out v15/out v15/print v15/docs
[ -f v14/out/E3.stl ] || python3 v14/src/e3_corners.py   # the body with both ducktail corners blended -> v14/out/E3.stl
[ -f v14/out/E4.stl ] || python3 v14/src/e4_underside.py # and the step along the back of the underside faired out -> v14/out/E4.stl
python3 v15/src/p1_core.py        # three sections cored to the 4 mm shell, open underneath                 -> out/cored_L|C|R.stl
python3 v15/src/p2_parts.py       # front/rear cuts, pins, tongues and grooves                            -> out/assembled/
python3 v15/src/p3_validate.py    # meshes, thickness <= 10 mm, overlaps, clearances, hole walls          (stops if a check fails)
python3 v15/src/p4_place.py       # bed placement for 420 x 420 x 500, each part on its cut face           -> print/
python3 v15/src/p5_figures.py     # figures                                                                -> docs/
python3 v15/src/gen_readme.py     # the README, from the reports                                           -> README.md
python3 v15/src/p6_package.py     # zip of README + print/ + docs/                                         -> Polo_spoiler_v15_print_package.zip
