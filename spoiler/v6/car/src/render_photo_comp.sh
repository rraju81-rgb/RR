#!/bin/sh
# Render passes for the owner's-photo composite (about 20 min on 4 CPU cores). Run from spoiler/.
O=v6/car/out/photo_comp; mkdir -p $O
python3 v6/car/src/blend_photo_comp.py spoiler $O/spoiler.npy 3 96  border=115,55,355,165
python3 v6/car/src/blend_photo_comp.py with    $O/with.npy    2 128 border=95,55,365,205
python3 v6/car/src/blend_photo_comp.py without $O/without.npy 2 128 border=95,55,365,205
python3 v6/car/src/blend_photo_comp.py sky     $O/sky.npy     1 1
