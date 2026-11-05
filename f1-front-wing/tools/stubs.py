import sys, pickle, numpy as np, trimesh
sys.path.insert(0, 'tools')
from joints import load_parts
from faces import frame_for, register2d_multi, mirror_poly
from shapely.geometry import Polygon
from shapely.ops import unary_union

def poly_of(tris, o, u, v):
    t = tris - o
    return unary_union([Polygon(np.c_[x @ u, x @ v]).buffer(1e-4) for x in t]).buffer(-1e-4)

def stub_tips(P, comp, ids):
    """Return list of stub tip faces for an end plate component (world coords of component)."""
    ms = {p: P[p].copy().apply_transform(comp[p]) for p in ids}
    allv = np.vstack([m.vertices for m in ms.values()]); ctr = allv.mean(0)
    w, V = np.linalg.eigh(np.cov((allv - ctr).T)); nrm = V[:, 0]
    zp = np.median((allv - ctr) @ nrm)
    tips = []
    for p, m in ms.items():
        z = (m.triangles_center - ctr) @ nrm - zp
        for sgn in (-1, 1):
            sel = np.where(sgn * z > 6)[0]
            if len(sel) == 0:
                continue
            sub = m.submesh([sel], append=True)
            for q in sub.split(only_watertight=False):
                if q.area < 300:
                    continue
                zc = (q.triangles_center - ctr) @ nrm - zp
                # faces nearly parallel to the plate, near the outermost level of this blob
                par = np.abs(q.face_normals @ nrm) > 0.97
                lvl = np.abs(zc).max()
                tip = np.where(par & (np.abs(zc) > lvl - 2.0))[0]
                a = q.area_faces[tip].sum()
                if not (250 < a < 700):
                    continue
                n = sgn * nrm
                u, v = frame_for(n)
                o = ctr + nrm * (zp + sgn * lvl)
                tips.append(dict(part=p, side=sgn, area=a, n=n, u=u, v=v, o=o,
                                 poly=poly_of(q.triangles[tip], o, u, v), level=lvl))
    return tips

if __name__ == '__main__':
    P = load_parts(); A = pickle.load(open('assembly.pkl', 'rb'))
    ends = {}
    for p in [6, 7, 9, 10, 13, 14, 42, 43]:
        m = P[p]
        sel = np.where((m.face_normals[:, 2] < -0.999) & (m.triangles_center[:, 2] < 0.5))[0]
        n = np.array([0, 0, -1.0]); u, v = frame_for(n); o = np.zeros(3)
        ends[p] = dict(area=m.area_faces[sel].sum(), poly=poly_of(m.triangles[sel], o, u, v), n=n, u=u, v=v, o=o)
    for ids in ([11, 12], [16, 41]):
        comp = [c for c in A['comps'] if set(c) == set(ids)][0]
        for t in stub_tips(P, comp, ids):
            scores = []
            for p, e in ends.items():
                best = max(register2d_multi(t['poly'], mirror_poly(e['poly'])), key=lambda r: r[0])
                scores.append((best[0], p))
            scores.sort(reverse=True)
            print(f"endplate {ids} obj_{t['part']} side {t['side']:+d} tip {t['area']:.0f}mm2 @ {t['level']:.1f}mm:",
                  ', '.join(f"obj_{p} {s:.3f}" for s, p in scores[:4]))
