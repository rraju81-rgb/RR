"""Convert the final renders (v6/car/renders/*.png) to the brochure JPEGs in img/. Run from anywhere.
hero_* are rendered at the hero box's aspect, so only the side view needs a crop (it sits in a wide strip)."""
import os
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
R = os.path.join(HERE, '..', 'car', 'renders'); O = os.path.join(HERE, 'img')
NAMES = ['hero_white', 'hero_red', 'top_rear', 'side', 'detail_fin', 'joints', 'parts', 'rear']
# x0, y0, x1, y1 as fractions of the render. The side view goes in a 210 x 66 mm strip (3.18:1); in the render the car
# spans x 0.17-0.83 and y 0.29-0.68, so this window keeps all of it, roof and spoiler lip included.
CROPS = {'side': (0.031, 0.25, 0.965, 0.72),
         'joints': (0.10, 0.02, 1.0, 0.92)}       # same aspect as the render, trims the empty floor so the keys read larger
os.makedirs(O, exist_ok=True)
for k in NAMES:
    src = os.path.join(R, k + '.png')
    if not os.path.exists(src): src = os.path.join(R, k + '.jpg')
    if not os.path.exists(src):
        print('MISSING', k); continue
    im = Image.open(src).convert('RGB')
    if k in CROPS:
        x0, y0, x1, y1 = CROPS[k]; W, H = im.size
        im = im.crop((int(x0 * W), int(y0 * H), int(x1 * W), int(y1 * H)))
    im.save(os.path.join(O, k + '.jpg'), quality=90, optimize=True)
    print(k, im.size)
