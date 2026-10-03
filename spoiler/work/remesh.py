import pymeshlab as ml, sys, trimesh, numpy as np
name, L = sys.argv[1], float(sys.argv[2])
ms=ml.MeshSet(); ms.load_new_mesh(f'work/half_{name}.stl')
ms.meshing_isotropic_explicit_remeshing(targetlen=ml.PureValue(L), featuredeg=35, iterations=8, adaptive=False, checksurfdist=True, maxsurfdist=ml.PureValue(0.05))
for it in range(6):
    ms.compute_selection_by_self_intersections_per_face()
    n=ms.current_mesh().selected_face_number(); print('iter',it,'selfint',n)
    if n==0: break
    ms.apply_selection_dilatation(); 
    ms.meshing_remove_selected_vertices_and_faces()
    ms.meshing_remove_unreferenced_vertices()
    ms.meshing_close_holes(maxholesize=200, newfaceselected=False)
ms.save_current_mesh(f'work/rem_{name}.stl')
m=trimesh.load(f'work/rem_{name}.stl')
print(name,len(m.faces),'wt',m.is_watertight,'vol',m.volume/1e3)
