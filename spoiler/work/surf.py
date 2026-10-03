import numpy as np, trimesh
from collections import defaultdict
def load(name):
    d=np.load(f'work/tet_{name}.npz'); N=d['nodes'].astype(float); E=d['elems'].astype(np.int64)
    v=np.einsum('ij,ij->i',np.cross(N[E[:,1]]-N[E[:,0]],N[E[:,2]]-N[E[:,0]]),N[E[:,3]]-N[E[:,0]])
    E[v<0]=E[v<0][:,[0,2,1,3]]
    return N,E
# ccx face definitions (0-based local)
FACES=[(0,1,2),(0,3,1),(1,3,2),(2,3,0)]
def boundary(E):
    allf=np.vstack([E[:,f] for f in FACES]); key=np.sort(allf,1)
    eid=np.tile(np.arange(len(E)),4); fid=np.repeat(np.arange(4),len(E))
    _,inv,cnt=np.unique(key,axis=0,return_inverse=True,return_counts=True)
    b=cnt[inv]==1
    return allf[b],eid[b],fid[b]
if __name__=='__main__':
    for n in ['TOP','BOTTOM']:
        N,E=load(n); f,e,k=boundary(E)
        tri=N[f]; nrm=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0])
        # check outward: compare to mesh
        print(n,len(E),'bfaces',len(f))
