#!/bin/sh
# Rebuild the v6 spoiler from the v5 STLs. Run from the spoiler/ folder:  sh v6/src/run_all.sh
# needs: pip install trimesh manifold3d scipy shapely rtree embreex triangle pymeshlab numba pillow matplotlib
set -e
mkdir -p v6/out v6/print v6/assembled v6/docs
python3 v6/src/s1_classify.py     # outer skin vs internal faces of v5 TOP/BOTTOM
python3 v6/src/s2_stitch.py       # one solid: TOP skin + BOTTOM underside, glue gap stitched  -> out/E0.stl
python3 v6/src/s3_smooth_top.py   # step line on the rear top surface: cubic bridge per column
python3 v6/src/s3c_move.py        # move top vertices onto the bridge                          -> out/E1.stl
python3 v6/src/s3e_refill.py      # re-triangulate the bridged band (1 mm, 28 deg min angle)    -> out/E2.stl
python3 v6/src/s4_parts.py        # 3 pieces + bow-tie pockets + key                            -> assembled/
python3 v6/src/s5_validate.py     # watertight / self-intersection / clearance / flush checks
python3 v6/src/s6_place.py        # bed placement for 420 x 420 x 500                           -> print/
python3 v6/src/s7_render.py       # figures                                                      -> docs/
python3 v6/src/s8_drawings.py     # key drawing, sections, hero, before/after
