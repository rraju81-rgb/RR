#!/bin/sh
# Rebuild the v13 package: the six parts of v10 (3 across x front/rear), cored to <= 10 mm, with no brim at the back
# (the spoiler's own underside runs flush to the back edge), the ducktail corners blended into the body, and pinned
# 30-degree joints. Run from the spoiler/ folder:  sh v13/src/run_all.sh        (about 50 minutes on 4 cores)
# v13 starts from the same solid body as v6-v11 (v6/out/E2.stl) and the car body under it (v6/car/out/); both are built
# first if missing.
set -e
[ -f v6/out/E2.stl ] || sh v6/src/run_all.sh
[ -f v6/car/out/car_body_conf.ply ] || python3 v6/car/src/car_build_all.py
mkdir -p v13/out v13/print v13/assembled v13/docs
[ -f v13/out/E3.stl ] || python3 v13/src/e3_corners.py   # the body with both ducktail corners blended -> out/E3.stl
python3 v13/src/p1_core.py        # three sections cored (skin 8.5 mm), no brim, hidden channel along the back -> out/cored_L|C|R.stl
python3 v13/src/p2_parts.py       # front/rear cuts, pins, tongues and grooves                            -> assembled/
python3 v13/src/p3_validate.py    # meshes, thickness <= 10 mm, overlaps, clearances, hole walls          (stops if a check fails)
python3 v13/src/p4_place.py       # bed placement for 420 x 420 x 500, each part on its cut face           -> print/
python3 v13/src/p5_figures.py     # figures                                                                -> docs/
python3 v13/src/p6_package.py     # zip of README + print/ + assembled/ + docs/                            -> Polo_spoiler_v13_print_package.zip
