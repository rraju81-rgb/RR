import glob, re, os, numpy as np, trimesh
import os
# Folder holding the original split STLs (obj_1_...stl ... obj_49_Ring_F1-006.stl)
SRC = os.environ.get('F1_PARTS_DIR', 'parts')

def pid(p):
    return int(re.search(r'(?:^|-)obj_(\d+)_', os.path.basename(p)).group(1))

def load_parts(src=SRC):
    P = {}
    for f in glob.glob(os.path.join(src, '*.stl')):
        m = trimesh.load(f, force='mesh')
        m.merge_vertices()
        P[pid(f)] = m
    return dict(sorted(P.items()))

def horizontal_levels(m, cos_tol=0.9998, ztol=0.05, min_area=2.0):
    """Group faces whose normal is +/-z by (sign, z level). Returns list of dicts."""
    n = m.face_normals
    out = {}
    for sgn in (+1, -1):
        sel = np.where(n[:, 2] * sgn > cos_tol)[0]
        if len(sel) == 0:
            continue
        z = m.triangles_center[sel, 2]
        order = np.argsort(z)
        sel, z = sel[order], z[order]
        # cluster by z
        start = 0
        for k in range(1, len(sel) + 1):
            if k == len(sel) or z[k] - z[k - 1] > ztol:
                fs = sel[start:k]
                a = m.area_faces[fs].sum()
                if a >= min_area:
                    out[(sgn, round(float(z[start:k].mean()), 2))] = fs
                start = k
    return [dict(sign=s, z=zz, faces=fs, area=float(m.area_faces[fs].sum())) for (s, zz), fs in out.items()]
