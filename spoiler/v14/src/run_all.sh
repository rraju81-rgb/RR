#!/bin/sh
# Rebuild the v14 package: the six parts of v10 (3 across x front/rear), hollow inside so no wall is over 10 mm, with
# the underside closed (the spoiler's own smooth underside everywhere), the ducktail lip ends blended into the body, and
# pinned 30-degree joints. Run from the spoiler/ folder:  sh v14/src/run_all.sh        (about 50 minutes on 4 cores)
# v14 starts from the same solid body as v6-v11 (v6/out/E2.stl) and the car body under it (v6/car/out/); both are built
# first if missing.
set -e
[ -f v6/out/E2.stl ] || sh v6/src/run_all.sh
[ -f v6/car/out/car_body_conf.ply ] || python3 v6/car/src/car_build_all.py
mkdir -p v14/out v14/print v14/assembled v14/docs
[ -f v14/out/E3.stl ] || python3 v14/src/e3_corners.py   # the body with both ducktail corners blended -> out/E3.stl
[ -f v14/out/E4.stl ] || python3 v14/src/e4_underside.py # and the step along the back of the underside faired out -> out/E4.stl
python3 v14/src/p1_core.py        # three sections hollowed inside (top skin 6-8.5, skirt 2.5 mm), underside closed    -> out/cored_L|C|R.stl
python3 v14/src/p2_parts.py       # front/rear cuts, pins, tongues and grooves                            -> assembled/
python3 v14/src/p3_validate.py    # meshes, thickness <= 10 mm, overlaps, clearances, hole walls          (stops if a check fails)
python3 v14/src/p4_place.py       # bed placement for 420 x 420 x 500, each part on its cut face           -> print/
python3 v14/src/p5_figures.py     # figures                                                                -> docs/
python3 v14/src/p6_package.py     # zip of README + print/ + assembled/ + docs/                            -> Polo_spoiler_v14_print_package.zip
