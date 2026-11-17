"""Preview images for the print set (run after print_ready.py, in the same folder).

    python3 make_previews.py [--stl stl] [--out preview]

assembled.png   - the assembled model, pins in red
exploded.png    - every piece pulled apart along its joint, so the sockets, keys and pins show
joints.png      - close-ups: centre block, end plate keys, body joint
print_files.png - every file the way it sits on the 420 x 420 mm bed
"""
import argparse, os, sys, pickle, glob
import numpy as np, trimesh
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from render import render
from print_ready import cyl, PIN_D
from merge import from_manifold

RED, BODY, BLOCK, WING, EP, GREY = (215, 40, 40), (200, 205, 215), (230, 160, 60), (70, 165, 80), (70, 110, 205), (150, 150, 150)


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


def colour(name):
    if name.startswith('body'):
        return BODY
    if name.startswith('centre'):
        return BLOCK
    if 'end plate' in name:
        return EP
    return WING


def moved(m, d):
    m = m.copy(); m.apply_translation(d); return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--stl', default='stl')
    ap.add_argument('--out', default='preview')
    ap.add_argument('--bed', nargs=3, type=float, default=[420, 420, 450])
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    D = pickle.load(open('print_ready_assembled.pkl', 'rb'))
    P, pins, up = D['pieces'], D['pins'], np.asarray(D['up_nose'])
    names = list(P)
    pin_m = [from_manifold(cyl(p0, p1, PIN_D / 2, 24)) for _, p0, p1 in pins]

    # assembled
    ims = []
    for az, el, txt in [(35, 28, 'assembled (52 %), from front-left'), (-35, -30, 'from below')]:
        im, _, _ = render([P[n] for n in names], [colour(n) for n in names], azim=az, elev=el, size=(900, 560))
        ims.append(label(im, txt))
    tile(ims, 1).save(os.path.join(a.out, 'assembled.png'))

    # exploded: blades pulled out of the centre block and the end plates, body lifted and split open
    off = {}
    for n in names:
        if n.startswith('blade'):
            side = 1 if n.endswith('_L') else -1
            off[n] = (0, side * 30, 0)
        elif 'end plate' in n:
            off[n] = (0, (1 if n.startswith('left') else -1) * 60, 0)
        elif n == 'body front':
            off[n] = tuple(up * 40 + np.array([0, 0, 60]))
        elif n == 'body rear':
            off[n] = (0, 0, 60)
        else:
            off[n] = (0, 0, 0)
    im, _, _ = render([moved(P[n], off[n]) for n in names], [colour(n) for n in names], azim=35, elev=30, size=(1400, 800))
    label(im, 'exploded: 8 separate blades, centre block (orange), end plates (blue) with a key per blade, body in 2 pieces').save(
        os.path.join(a.out, 'exploded.png'))

    # joints
    ims = []
    blk = P['centre block']
    roots = [moved(P[n].slice_plane([0, (1 if n.endswith('_L') else -1) * 60, 0], [0, -(1 if n.endswith('_L') else -1), 0]),
                   (0, (1 if n.endswith('_L') else -1) * 18, 0)) for n in names if n.startswith('blade') and 'flap' not in n]
    bpins = [m for m, (lab, _, _) in zip(pin_m, pins) if 'centre block' in lab]
    for az, el, txt in [(35, 35, 'centre block: sockets for the 6 inner blade ends, 2 pins for the body'),
                        (-35, -35, 'centre block from below')]:
        im, _, _ = render([blk] + roots + bpins, [BLOCK] + [WING] * len(roots) + [RED] * len(bpins), azim=az, elev=el, size=(900, 520))
        ims.append(label(im, txt))
    ep = P['left end plate']
    tips = [moved(P[n].slice_plane([0, 200, 0], [0, 1, 0]), (0, -25, 0)) for n in names if n.startswith('blade') and n.endswith('_L')]
    for az, el, txt in [(-60, 25, 'left end plate: a key on each stub slides into a slot in the blade tip'), (-120, -30, 'same, from behind / below')]:
        im, _, _ = render([ep] + tips, [EP] + [WING] * len(tips), azim=az, elev=el, size=(900, 520))
        ims.append(label(im, txt))
    # close-up of the keys: end plate stubs only, blade tips pulled back
    ys = ep.bounds[0, 1]
    stub = ep.slice_plane([0, ys + 14, 0], [0, -1, 0])
    tips2 = [moved(P[n].slice_plane([0, ys - 12, 0], [0, 1, 0]), (0, -14, 0)) for n in names if n.startswith('blade') and n.endswith('_L')]
    im, _, _ = render([stub] + tips2, [EP] + [WING] * len(tips2), azim=-75, elev=35, size=(900, 520))
    ims.append(label(im, 'close-up: the 4 keys on the left end plate and the matching slots in the blade tips'))
    rear, front = P['body rear'], P['body front']
    cpins = [m for m, (lab, _, _) in zip(pin_m, pins) if 'body rear' in lab]
    for az, el, txt in [(200, 35, 'body joint: front half lifted off, 2 pins in bosses inside the side walls')]:
        im, _, _ = render([rear, moved(front, up * 45)] + cpins, [BODY, BODY] + [RED] * len(cpins), azim=az, elev=el, size=(900, 520))
        ims.append(label(im, txt))
    tile(ims, 2).save(os.path.join(a.out, 'joints.png'))

    # print files on the bed
    files = sorted(os.path.basename(f) for f in glob.glob(os.path.join(a.stl, '*.stl')))
    bed = trimesh.creation.box(extents=[a.bed[0], a.bed[1], 2.0]); bed.apply_translation([0, 0, -1.0])
    ims = []
    for f in files:
        c = BODY if f.startswith('1') else BLOCK if f.startswith('2') else WING if f.startswith(('3', '4')) else EP if f.startswith('5') else RED
        m = trimesh.load(os.path.join(a.stl, f), force='mesh')
        parts_f = m.split(only_watertight=False)
        main_ = max(parts_f, key=lambda p: p.volume)
        extra = [p for p in parts_f if p is not main_]
        colours = [c] + [GREY if f.startswith(('3', '4')) else c] * len(extra)
        ext = m.extents
        if f.startswith('6'):
            im, _, _ = render([m], [c], azim=-60, elev=30, size=(450, 450))
        else:
            both = trimesh.util.concatenate([bed, m])
            _, sc, ce = render([both], [c], azim=-60, elev=22, size=(450, 450))
            base, _, _ = render([bed], [(225, 225, 225)], azim=-60, elev=22, size=(450, 450), scale=sc, center=ce)
            im, _, _ = render([main_] + extra, colours, azim=-60, elev=22, size=(450, 450), scale=sc, center=ce, base_img=base)
        ims.append(label(im, f'{f.replace(".stl", "")}: {ext[0]:.0f} x {ext[1]:.0f} x {ext[2]:.0f} mm'))
    tile(ims, 4).save(os.path.join(a.out, 'print_files.png'))
    print('previews written to', a.out)


if __name__ == '__main__':
    main()
