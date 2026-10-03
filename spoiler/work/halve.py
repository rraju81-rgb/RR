import trimesh, numpy as np, manifold3d as mf
def tomf(m): return mf.Manifold(mf.Mesh(vert_properties=np.asarray(m.vertices,np.float32), tri_verts=np.asarray(m.faces,np.uint32)))
def totm(M):
    g=M.to_mesh(); return trimesh.Trimesh(g.vert_properties[:,:3], g.tri_verts, process=True)
for n in ['TOP','BOTTOM']:
    m=trimesh.load(f'input/v5_{n}.stl')
    box=mf.Manifold.cube([800,400,500]).translate([0,-200,-100])
    h=totm(tomf(m)^box)
    print(n,len(h.faces),h.is_watertight,h.bounds.round(1))
    h.export(f'work/half_{n}.stl')
