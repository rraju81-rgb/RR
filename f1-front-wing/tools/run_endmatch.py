import sys, pickle, itertools, numpy as np
sys.path.insert(0, 'tools')
from joints import load_parts
from faces import register2d, register2d_multi, mirror_poly, transform_from_match
from ends import part_ends
from endmatch import *
P = load_parts()
D = pickle.load(open('matches.pkl', 'rb')); faces = D['faces']
by = {}
for f in faces:
    f['tris_world'] = P[f['part']].triangles[f['faces']]
    by.setdefault(f['part'], []).append(f)
ENDS = []
for p, L in by.items():
    for e in part_ends(L):
        o, r = end_faces(e)
        if o is None or e['total'] < 250:
            continue
        # only ends whose levels are just 0 and 19 (cut ends), skip tooth side-walls (levels 0/66.5/133)
        lv = sorted(set(round(x) for x, _ in e['levels']))
        if not set(lv) <= {0, 19}:
            continue
        e.update(part=p, outer=o, rec=r, kind='tab' if r is not None else 'flat')
        ENDS.append(e)
print('ends:', len(ENDS), ' tab:', sum(e['kind'] == 'tab' for e in ENDS), ' flat:', sum(e['kind'] == 'flat' for e in ENDS))
results = []
for i, j in itertools.combinations(range(len(ENDS)), 2):
    A, B = ENDS[i], ENDS[j]
    if A['part'] == B['part'] or A['kind'] != B['kind']:
        continue
    if min(A['total'], B['total']) / max(A['total'], B['total']) < 0.96:
        continue
    if A['kind'] == 'tab':
        fa, fb = A['outer'], B['rec']          # A's outer plane meets B's recessed plane
        fa2, fb2 = A['rec'], B['outer']
    else:
        fa, fb = A['outer'], B['outer']; fa2 = fb2 = None
    fA_all = np.concatenate([f['faces'] for f in A['faces']]); fB_all = np.concatenate([f['faces'] for f in B['faces']])
    best = None
    for s1, th, t in register2d_multi(fa['poly'], mirror_poly(fb['poly'])):
        if s1 < 0.85:
            continue
        T = transform_from_match(fa, fb, th, t)
        s2 = 1.0; gap = 0.0
        if fa2 is not None:
            pb, gap = face_in_plane_poly(fb2, T, fa2)
            pa = fa2['poly']
            inter = pa.intersection(pb).area; s2 = inter / (pa.area + pb.area - inter)
        sk, cov = skin_continuity(P[A['part']], fA_all, P[B['part']], fB_all, T)
        score = min(s1, s2) - sk / 30.0
        if best is None or score > best[0]:
            best = (score, s1, s2, gap, sk, cov, T)
    if best is None:
        continue
    _, s1, s2, gap, sk, cov, T = best
    results.append(dict(i=i, j=j, A=A['part'], B=B['part'], kind=A['kind'], iou=s1, iou2=s2, gap=gap, skin=sk, cov=cov, T=T))
results.sort(key=lambda r: (-(min(r['iou'], r['iou2'])) + r['skin'] / 30))
for r in results:
    if min(r['iou'], r['iou2']) > 0.9:
        print(f"{r['kind']:4} obj_{r['A']:<2} <-> obj_{r['B']:<2}  iou {r['iou']:.3f}/{r['iou2']:.3f}  skin {r['skin']:5.2f}deg cov {r['cov']:.2f}  plane-gap {r['gap']:.2f}")
pickle.dump(dict(ENDS=[{k: v for k, v in e.items() if k not in ('faces', 'outer', 'rec')} | dict(part=e['part']) for e in ENDS], results=results), open('endmatch.pkl', 'wb'))
