"""Mesh checks: watertight, manifold, self-intersections (pymeshlab), bodies, degenerate faces."""
import numpy as np, trimesh, pymeshlab, sys

def selfx(m):
    ms = pymeshlab.MeshSet()
    ms.add_mesh(pymeshlab.Mesh(vertex_matrix=np.asarray(m.vertices, float), face_matrix=np.asarray(m.faces, np.int32)))
    ms.apply_filter('compute_selection_by_self_intersections_per_face')
    sel = ms.current_mesh().face_selection_array()
    return np.nonzero(sel)[0]

def report(m, name=''):
    sx = selfx(m)
    area = m.area_faces
    bodies = m.split(only_watertight=False)
    r = dict(name=name, faces=len(m.faces), watertight=bool(m.is_watertight), winding=bool(m.is_winding_consistent),
             volume_cm3=round(float(m.volume) / 1000, 2), bodies=len(bodies), selfx_faces=int(len(sx)),
             zero_area=int((area < 1e-10).sum()), min_area=float(area.min()),
             bounds=[[round(float(v), 2) for v in b] for b in m.bounds])
    return r, sx

if __name__ == '__main__':
    for p in sys.argv[1:]:
        m = trimesh.load(p)
        r, sx = report(m, p)
        print(r)
        if len(sx):
            c = m.triangles_center[sx]
            print('  self-x face centers (first 10):', c[:10].round(2).tolist())
