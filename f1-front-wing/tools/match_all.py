import sys, time, pickle, itertools
sys.path.insert(0, 'tools')
from joints import load_parts
from faces import *

P = load_parts()
t = time.time()
JF = {i: joint_faces(m, min_area=12, min_sharp=0.6) for i, m in P.items()}
print('extract', round(time.time() - t, 1), 's; faces per part:', {i: len(v) for i, v in JF.items()})
# stats for quick filtering
for i, L in JF.items():
    for f in L:
        f['polyM'] = mirror_poly(f['poly'])
        c, ang, w = shape_stats(f['poly'], res=0.5 if f['area'] < 2000 else 1.0)
        f['stats'] = (c, ang, w)
        f['part'] = i
faces = [f for L in JF.values() for f in L]
print('total faces', len(faces))
cands = []
for a, b in itertools.combinations(range(len(faces)), 2):
    fa, fb = faces[a], faces[b]
    if fa['part'] == fb['part']:
        continue
    ra = min(fa['area'], fb['area']) / max(fa['area'], fb['area'])
    if ra < 0.85:
        continue
    wa, wb = fa['stats'][2], fb['stats'][2]
    if min(wa[0], wb[0]) / max(wa[0], wb[0]) < 0.75 or min(wa[1], wb[1]) / max(wa[1], wb[1], 1e-9) < 0.6:
        continue
    cands.append((a, b))
print('candidate pairs', len(cands))
t = time.time()
res = []
for a, b in cands:
    fa, fb = faces[a], faces[b]
    s, th, tt = register2d(fa['poly'], fb['polyM'])
    if s > 0.7:
        res.append((s, a, b, th, tt))
print('registered in', round(time.time() - t, 1), 's; matches >0.7:', len(res))
res.sort(key=lambda r: -r[0])
for s, a, b, th, tt in res[:200]:
    fa, fb = faces[a], faces[b]
    print(f"IoU {s:.3f}  obj_{fa['part']:<2} [{fa['area']:.0f}]  <->  obj_{fb['part']:<2} [{fb['area']:.0f}]")
pickle.dump(dict(faces=faces, res=res), open('matches.pkl', 'wb'))
