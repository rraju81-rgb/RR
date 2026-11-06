import os, sys, pickle, numpy as np, trimesh
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from joints import load_parts
from faces import frame_for, register2d_multi, mirror_poly, transform_from_match
from endmatch import skin_continuity
from stubs import poly_of
from shapely.geometry import Polygon

P = load_parts(); A = pickle.load(open('assembly.pkl', 'rb'))
comps = A['comps']
def comp_of(p):
    return [c for c in comps if p in c][0]

def stub_tips_relaxed(ids, par=0.9, win=2.5):
    comp = comp_of(ids[0])
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
                # dominant tip direction: area-weighted normal of outward-facing faces near the max level
                zc = (q.triangles_center - ctr) @ nrm - zp
                lvl = np.abs(zc).max()
                near = np.where(np.abs(zc) > lvl - 6)[0]
                nn = q.face_normals[near]; aa = q.area_faces[near]
                nd = (nn * aa[:, None])[nn @ (sgn * nrm) > 0.7].sum(0)
                if np.linalg.norm(nd) == 0:
                    continue
                nd /= np.linalg.norm(nd)
                proj = q.triangles_center @ nd
                pl = proj.max()
                tip = np.where((q.face_normals @ nd > 0.995) & (proj > pl - win))[0]
                a = q.area_faces[tip].sum()
                if not (250 < a < 700):
                    continue
                u, v = frame_for(nd)
                dplane = np.average(proj[tip], weights=q.area_faces[tip])
                o = nd * dplane
                tips.append(dict(part=p, area=a, n=nd, u=u, v=v, o=o, d=dplane,
                                 faces_mesh=q, faces=tip, poly=poly_of(q.triangles[tip], o, u, v)))
    return tips, ms

def end_face(p):
    m = P[p]
    sel = np.where((m.face_normals[:, 2] < -0.999) & (m.triangles_center[:, 2] < 0.5))[0]
    n = np.array([0, 0, -1.0]); u, v = frame_for(n); o = np.zeros(3)
    return dict(area=m.area_faces[sel].sum(), poly=poly_of(m.triangles[sel], o, u, v), n=n, u=u, v=v, o=o, faces=sel)

ENDS = {p: end_face(p) for p in [6, 7, 9, 10, 13, 14, 42, 43]}
links = []   # (endplate_part, element_end_part, T: element-end-part coords -> endplate component coords, iou, skin)
for ids in ([11, 12], [16, 41]):
    tips, ms = stub_tips_relaxed(ids)
    for t in tips:
        best = None
        for p, e in ENDS.items():
            for s, th, tt in register2d_multi(t['poly'], mirror_poly(e['poly'])):
                if s < 0.9:
                    continue
                T = transform_from_match(t, e, th, tt)
                sk, cov = skin_continuity(t['faces_mesh'], t['faces'], P[p], e['faces'], T)
                score = s - sk / 30
                if best is None or score > best[0]:
                    best = (score, p, s, sk, cov, T)
        if best:
            _, p, s, sk, cov, T = best
            print(f"endplate {ids} obj_{t['part']} tip {t['area']:.0f}mm2  <->  obj_{p} end {ENDS[p]['area']:.0f}mm2   iou {s:.3f} skin {sk:.2f}deg cov {cov:.2f}")
            links.append(dict(ep=ids, tip_part=t['part'], elem=p, T=T, iou=s, skin=sk))
pickle.dump(links, open('stub_links.pkl', 'wb'))
