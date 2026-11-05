import sys, re, glob, os
import numpy as np, trimesh
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.dirname(__file__))
from render import render

def pid(p):
    m = re.search(r'obj_(\d+)_.*\.obj_(\d+)\.stl$', os.path.basename(p)); return int(m.group(1))

src, out = sys.argv[1], sys.argv[2]
files = sorted(glob.glob(os.path.join(src, '*.stl')), key=pid)
cell, cols = 260, 6
rows = (len(files) + cols - 1) // cols
sheet = Image.new('RGB', (cols * cell, rows * cell), (255, 255, 255))
d = ImageDraw.Draw(sheet)
for i, f in enumerate(files):
    m = trimesh.load(f, force='mesh')
    m.apply_translation(-m.bounds.mean(0))
    img, _, _ = render([m], [(170, 175, 190)], azim=-55, elev=28, size=(cell, cell - 30), scale=0.75, center=np.zeros(3))
    r, c = divmod(i, cols)
    sheet.paste(img, (c * cell, r * cell + 30))
    sz = m.extents
    d.text((c * cell + 6, r * cell + 4), f"obj_{pid(f)}  {sz[0]:.0f}x{sz[1]:.0f}x{sz[2]:.0f}", fill=(0, 0, 0))
    d.rectangle([c * cell, r * cell, (c + 1) * cell - 1, (r + 1) * cell - 1], outline=(200, 200, 200))
sheet.save(out)
print(len(files), 'parts ->', out)
