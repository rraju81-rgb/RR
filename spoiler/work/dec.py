import pymeshlab as ml, sys, trimesh
name,target=sys.argv[1],int(sys.argv[2])
ms=ml.MeshSet(); ms.load_new_mesh(f'work/half_{name}.stl')
ms.meshing_decimation_quadric_edge_collapse(targetfacenum=target, qualitythr=0.5, preserveboundary=True, preservenormal=True, preservetopology=True, optimalplacement=True, planarquadric=True, planarweight=0.002)
ms.compute_selection_by_self_intersections_per_face()
print('selfint',ms.current_mesh().selected_face_number())
ms.save_current_mesh(f'work/dec_{name}.stl')
m=trimesh.load(f'work/dec_{name}.stl'); print(len(m.faces),m.is_watertight,m.volume/1e3)
