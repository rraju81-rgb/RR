"""Page-1 hero from the owner's photo of their car: crop to the hero box (210 x 124 mm) and, if the photo is small,
upscale it to 2200 px wide (Lanczos, light sharpening and fine grain so the softness reads as photographic).
Run from this folder:  python3 prep_photo.py [photo]      (default: photo/owner_car_original.png)
With a full-size original from the phone no upscaling is needed and the page is sharp in print too."""
import sys
import numpy as np
from PIL import Image, ImageFilter
src = sys.argv[1] if len(sys.argv) > 1 else 'photo/owner_car_original.png'
CY = 0.44                       # vertical centre of the crop, as a fraction of the photo height (car, spoiler and wheels in frame)
ASPECT = 210 / 124
im = Image.open(src).convert('RGB'); W, H = im.size
h = min(H, round(W / ASPECT)); w = round(h * ASPECT)
x0 = (W - w) // 2; y0 = int(min(max(CY * H - h / 2, 0), H - h))
crop = im.crop((x0, y0, x0 + w, y0 + h))
TARGET = 2200
if crop.width < TARGET:
    k = TARGET / crop.width
    crop = crop.resize((TARGET, round(crop.height * k)), Image.LANCZOS)
    if k > 1.5:
        crop = crop.filter(ImageFilter.UnsharpMask(radius=2.2, percent=70, threshold=2))
        a = np.asarray(crop).astype(np.float32)
        a = np.clip(a + np.random.default_rng(1).normal(0, 2.6, a.shape[:2])[..., None], 0, 255).astype(np.uint8)
        crop = Image.fromarray(a)
    print(f'upscaled x{k:.1f} from {W} x {H}: send the full-size original for a sharp print')
crop.save('img/hero_owner_car.jpg', quality=92, optimize=True)
print('img/hero_owner_car.jpg', crop.size)
