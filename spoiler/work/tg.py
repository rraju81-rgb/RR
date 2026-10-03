import tetgen, trimesh, numpy as np, time, sys
name=sys.argv[1]
m=trimesh.load(f'work/{sys.argv[2]}_{name}.stl')
t=time.time()
tg=tetgen.TetGen(np.asarray(m.vertices),np.asarray(m.faces))
nodes,elems=tg.tetrahedralize(quality=True, minratio=2.0, nobisect=True, verbose=0)[:2]
print(name,'nodes',len(nodes),'tets',len(elems),round(time.time()-t,1),'s')
np.savez(f'work/tet_{name}.npz',nodes=nodes,elems=elems)
