"""Lay the three parts of a kickstand easel v11 on one build plate, each in its print orientation:
panel on its stop wall, leg on its stop-wall end, pin on its head. Parts sit 6 mm apart."""
import sys, json, numpy as np, trimesh
GAP = 6.0
def plate(tag):
    parts = [trimesh.load(f'table_easel_{tag}_kickstand_v11_{p}.stl') for p in ('panel', 'leg', 'pin')]
    R = np.array([[0, 1, 0, 0], [0, 0, 1, 0], [1, 0, 0, 0], [0, 0, 0, 1]], float)   # rack (x,y,z) -> plate (X=y, Y=z, Z=x)
    out, y = [], 0.0
    for m in parts:
        m = m.copy(); m.apply_transform(R); m.apply_translation([-m.bounds[0][0], y - m.bounds[0][1], -m.bounds[0][2]])
        out.append(m); y = m.bounds[1][1] + GAP
    allm = trimesh.util.concatenate(out)
    # parts must not touch on the plate
    import manifold3d  # noqa
    for i in range(3):
        for j in range(i + 1, 3):
            v = trimesh.boolean.intersection([out[i], out[j]], engine='manifold').volume
            assert v < 1e-6, (i, j, v)
    allm.export(f'table_easel_{tag}_kickstand_v11_plate.stl')
    info = dict(plate_mm=np.round(allm.extents[:2], 1).tolist(), height_mm=round(allm.extents[2], 1), bodies=len(allm.split()),
                watertight=bool(allm.is_watertight), each_on_bed=[round(m.bounds[0][2], 3) for m in out])
    print(tag, info); return info
if __name__ == '__main__':
    json.dump({t: plate(t) for t in sys.argv[1:]}, open('_plate_v11.json', 'w'), indent=1)
