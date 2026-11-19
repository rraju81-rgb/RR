#!/bin/sh
# Photo-style brochure renders (blend_photo.py: blue Polo-class car, overcast lake/hills sky, asphalt) and the v9 joint view.
# Run from spoiler/:  sh v6/car/src/render_photo.sh      (about 40 min on 4 CPU cores)
O=v6/car/renders; S=${S:-64}
[ -f $O/hero_blue.png ] || python3 v6/car/src/blend_photo.py photo    $O/hero_blue.png        2200 1300 $S
python3 v6/car/src/blend_photo.py side     $O/side_blue.png        2200 1375 $S
python3 v6/car/src/blend_photo.py top_rear $O/top_rear_blue.png    2000 1250 $S
python3 v6/car/src/blend_photo.py fin      $O/detail_fin_blue.png  2000 1250 $S
python3 v6/car/src/blend_scene.py joint    $O/joints_v9.png        2200 1238 96 studio=light ver=v9
python3 -c "
from PIL import Image
for k in ['hero_blue', 'side_blue', 'top_rear_blue', 'detail_fin_blue', 'joints_v9']:
    p = '$O/' + k
    Image.open(p + '.png').convert('RGB').save(p + '.jpg', quality=92, optimize=True); print('jpg', p + '.jpg')
"
echo ALL_DONE
