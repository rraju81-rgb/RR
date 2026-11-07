"""Preview images for the pinned print set (run after print_ready.py, in the same folder).

    python3 make_previews.py [--stl stl] [--out preview]

assembled.png   - the assembled model with the 5 mm pins in red
joints.png      - close-ups of the pin holes and bosses
print_files.png - every file the way it sits on the 420 x 420 mm bed
"""
import argparse, os, sys, pickle
import numpy as np, trimesh
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from render import render
from print_ready import pin_axes, cyl, PIN_D
from merge import from_manifold

RED, BODY, WING, EP, GREY = (215, 40, 40), (200, 205, 215), (70, 165, 80), (70, 110, 205), (150, 150, 150)


def label(im, text):
    ImageDraw.Draw(im).text((8, 6), text, fill=(20, 20, 20))
    return im


def tile(ims, cols, bg=(255, 255, 255)):
    w, h = ims[0].size
    rows = (len(ims) + cols - 1) // cols
    S = Image.new('RGB', (w * cols, h * rows), bg)
    for i, im in enumerate(ims):
        S.paste(im, ((i % cols) * w, (i // cols) * h))
    return S


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--stl', default='stl')
    ap.add_argument('--out', default='preview')
    ap.add_argument('--bed', nargs=3, type=float, default=[420, 420, 450])
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    D = pickle.load(open('print_ready_assembled.pkl', 'rb'))
    parts = [D['NOSE'], D['WL'], D['WR'], D['EPL'], D['EPR']]
    cols = [BODY, WING, WING, EP, EP]
    pins = [from_manifold(cyl(p0, p1, PIN_D / 2, 24)) for _, p0, p1 in pin_axes(D['lr'], D['nz'], D['ep'])]

    # assembled, with the pins
    ims = []
    for az, el, txt in [(35, 28, 'assembled (52 %), from front-left'), (-35, -30, 'from below: end plate pins in red (the 4 centre pins are hidden in the seat block)')]:
        im, _, _ = render(parts + pins, cols + [RED] * len(pins), azim=az, elev=el, size=(900, 560))
        ims.append(label(im, txt))
    tile(ims, 1).save(os.path.join(a.out, 'assembled.png'))

    # joints: exploded slightly so the holes show
    def moved(m, d):
        m = m.copy(); m.apply_translation(d); return m
    ims = []
    # centre: wing halves pulled apart, nose lifted
    def clip(m, x0, x1, y0, y1):
        return m.slice_plane([x0, 0, 0], [1, 0, 0]).slice_plane([x1, 0, 0], [-1, 0, 0]).slice_plane([0, y0, 0], [0, 1, 0]).slice_plane([0, y1, 0], [0, -1, 0])
    cen = [moved(clip(D['WL'], -15, 125, 0, 45), (0, 22, 0)), moved(clip(D['WR'], -15, 125, -45, 0), (0, -22, 0)),
           moved(clip(D['NOSE'], -15, 125, -70, 70), (0, 0, 40))]
    pc = [(lab, p0, p1) for lab, p0, p1 in pin_axes(D['lr'], D['nz'], D['ep']) if 'end plate' not in lab]
    pins_c = []
    for lab, p0, p1 in pc:                                  # show each pin in one of its two holes
        d = (0, 0, 0)
        if lab.startswith('body'):
            d = (0, 22 if 'left' in lab else -22, 0)
        else:
            d = (0, -22, 0)
        pins_c.append(moved(from_manifold(cyl(p0, p1, PIN_D / 2, 24)), d))
    for az, el, txt in [(35, 35, 'centre: seat block (in both wing halves) under the nose, pulled apart'),
                        (-40, -35, 'centre from below: the nose underside with its 2 pin holes')]:
        im, _, _ = render(cen + pins_c, [WING, WING, BODY] + [RED] * len(pins_c), azim=az, elev=el, size=(900, 520))
        ims.append(label(im, txt))
    # left tip: end plate pulled outboard
    tip = [D['WL'].slice_plane([0, 200, 0], [0, 1, 0]), moved(D['EPL'], (0, 25, 0))]
    pins_t = [p for p, (lab, _, _) in zip(pins, pin_axes(D['lr'], D['nz'], D['ep'])) if lab.startswith('left wing <-> left end')]
    for az, el, txt in [(-60, 25, 'left wing tip and end plate pulled apart: 2 pins in teardrop bosses'),
                        (-120, -30, 'same joint from below / behind')]:
        im, _, _ = render(tip + pins_t, [WING, EP] + [RED] * len(pins_t), azim=az, elev=el, size=(900, 520))
        ims.append(label(im, txt))
    tile(ims, 2).save(os.path.join(a.out, 'joints.png'))

    # print files on the bed
    files = [('1_body.stl', BODY), ('2_left_wing.stl', WING), ('3_right_wing.stl', WING), ('4_end_plates.stl', EP), ('5_pins.stl', RED)]
    bed = trimesh.creation.box(extents=[a.bed[0], a.bed[1], 2.0]); bed.apply_translation([0, 0, -1.0])
    ims = []
    for f, c in files:
        m = trimesh.load(os.path.join(a.stl, f), force='mesh')
        parts_f = m.split(only_watertight=False)
        main_ = max(parts_f, key=lambda p: p.volume)
        extra = [p for p in parts_f if p is not main_]
        colours = [c] + [GREY if f.startswith(('2', '3')) else c] * len(extra)
        ext = m.extents
        if f == '5_pins.stl':
            im, _, _ = render([m], [c], azim=-60, elev=30, size=(600, 600))
        else:
            both = trimesh.util.concatenate([bed, m])
            _, sc, ce = render([both], [c], azim=-60, elev=22, size=(600, 600))
            base, _, _ = render([bed], [(225, 225, 225)], azim=-60, elev=22, size=(600, 600), scale=sc, center=ce)
            im, _, _ = render([main_] + extra, colours, azim=-60, elev=22, size=(600, 600), scale=sc, center=ce, base_img=base)
        ims.append(label(im, f'{f}: {ext[0]:.0f} x {ext[1]:.0f} x {ext[2]:.0f} mm' + ('  (grey = break-away supports)' if f.startswith(('2', '3')) else '')))
    tile(ims, 3).save(os.path.join(a.out, 'print_files.png'))
    print('previews written to', a.out)


if __name__ == '__main__':
    main()
