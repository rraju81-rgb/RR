#!/bin/sh
# Final renders (Cycles CPU, ~35 min on 4 cores). Run from spoiler/:  sh v6/car/src/render_final.sh
# hero_* are rendered at the brochure's hero aspect (210 x 124 mm); the rest at 16:10.
# The joint and parts views show the current split, v7 (4 pieces, 6 keys). Add ver=v6 for the 3-piece split.
W=2200; H=1375; S=128; O=v6/car/renders
python3 v6/car/src/blend_scene.py hero     $O/hero_white.png  2480 1464 $S paint=white
python3 v6/car/src/blend_scene.py side     $O/side.png        $W $H $S paint=white
python3 v6/car/src/blend_scene.py top_rear $O/top_rear.png    $W $H $S paint=white
python3 v6/car/src/blend_scene.py fin      $O/detail_fin.png  $W $H $S paint=white
python3 v6/car/src/blend_scene.py joint    $O/joints.png      2200 1238 $S studio=light   # the brochure's joint box, 96 x 54 mm
python3 v6/car/src/blend_scene.py hero     $O/hero_red.png    2480 1464 $S paint=red
python3 v6/car/src/blend_scene.py parts    $O/parts.png       $W $H $S studio=light
python3 v6/car/src/blend_scene.py rear     $O/rear.png        $W $H $S paint=white
# JPEG copies (these are the ones kept in git)
python3 -c "
import glob
from PIL import Image
for p in sorted(glob.glob('$O/*.png')):
    Image.open(p).convert('RGB').save(p[:-4] + '.jpg', quality=92, optimize=True); print('jpg', p[:-4] + '.jpg')
"
echo ALL_DONE
