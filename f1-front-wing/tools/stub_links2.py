"""Element-end <-> end-plate-stub joints, computed in each part's own coordinates (part-to-part)."""
import os, sys, pickle, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from joints import load_parts
from faces import frame_for, register2d_multi, mirror_poly, transform_from_match
from endmatch import skin_continuity
from stubs import poly_of
from refine import boundary_vertices, icp_refine_exact

def stub_tips_part(m, par=0.995, win=2.5):
    ctr = m.vertices.mean(0)
    w, V = np.linalg.eigh(np.cov((m.vertices - ctr).T)); nrm = V[:, 0]
    zp = np.median((m.vertices - ctr) @ nrm)
    tips = []
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
            lvl = np.abs(zc).max()
            near = np.where(np.abs(zc) > lvl - 6)[0]
            nn = q.face_normals[near]; aa = q.area_faces[near]
            nd = (nn * aa[:, None])[nn @ (sgn * nrm) > 0.7].sum(0)
            if np.linalg.norm(nd) == 0:
                continue
            nd /= np.linalg.norm(nd)
            proj = q.triangles_center @ nd
            tip = np.where((q.face_normals @ nd > par) & (proj > proj.max() - win))[0]
            a = q.area_faces[tip].sum()
            if not (250 < a < 700):
                continue
            u, v = frame_for(nd)
            dplane = np.average(proj[tip], weights=q.area_faces[tip])
            o = nd * dplane
            tips.append(dict(area=a, n=nd, u=u, v=v, o=o, mesh=q, faces=tip, poly=poly_of(q.triangles[tip], o, u, v)))
    return tips

def end_face(m):
    sel = np.where((m.face_normals[:, 2] < -0.999) & (m.triangles_center[:, 2] < 0.5))[0]
    n = np.array([0, 0, -1.0]); u, v = frame_for(n); o = np.zeros(3)
    return dict(area=m.area_faces[sel].sum(), poly=poly_of(m.triangles[sel], o, u, v), n=n, u=u, v=v, o=o, faces=sel)

if __name__ == '__main__':
    P = load_parts()
    ENDS = {p: end_face(P[p]) for p in [6, 7, 9, 10, 13, 14, 42, 43]}
    joints = []
    for ep in [11, 12, 16, 41]:
        for t in stub_tips_part(P[ep]):
            best = None
            for p, e in ENDS.items():
                if not (0.85 < t['area'] / e['area'] < 1.18):
                    continue
                for s, th, tt in register2d_multi(t['poly'], mirror_poly(e['poly'])):
                    if s < 0.9:
                        continue
                    T = transform_from_match(t, e, th, tt)
                    sk, cov = skin_continuity(t['mesh'], t['faces'], P[p], e['faces'], T)
                    if best is None or s - sk / 30 > best[0]:
                        best = (s - sk / 30, p, s, sk, T)
            if best is None:
                continue
            _, p, s, sk, T = best
            bA = boundary_vertices(t['mesh'], t['faces']); bB = boundary_vertices(P[p], ENDS[p]['faces'])
            T2, rms, frac = icp_refine_exact(bA, bB, T)
            print(f"stub on obj_{ep} <-> obj_{p}: iou {s:.3f} skin {sk:.2f} deg  -> exact pairs {frac*100:.0f}% rms {rms:.4f}")
            joints.append(dict(A=ep, B=p, kind='stub', T_refined=T2, bA=bA, bB=bB))
    pickle.dump(joints, open('stub_joints.pkl', 'wb'))
