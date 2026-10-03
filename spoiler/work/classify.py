import numpy as np, trimesh, sys
sys.path.insert(0,'work'); from surf import load, boundary, FACES
data={}
for n in ['TOP','BOTTOM']:
    N,E=load(n); f,e,k=boundary(E)
    tri=N[f]; c=tri.mean(1)
    nr=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]); A=np.linalg.norm(nr,axis=1)/2; nr/=np.linalg.norm(nr,axis=1)[:,None]
    opp=N[E[e,[ [i for i in range(4) if i not in FACES[kk]][0] for kk in k]]]
    s=np.sign(np.einsum('ij,ij->i',nr,c-opp)); nr*=s[:,None]
    data[n]=dict(N=N,E=E,f=f,e=e,k=k,c=c,n=nr,A=A)
# assembly surface (full, both halves, for ray tests) use original stl
T=trimesh.load('input/v5_TOP.stl'); B=trimesh.load('input/v5_BOTTOM.stl')
asm=trimesh.util.concatenate([T,B])
from trimesh.ray.ray_triangle import RayMeshIntersector
R=RayMeshIntersector(asm)
for n,d in data.items():
    o=d['c']+d['n']*0.05
    hit=R.intersects_any(o,d['n'])
    # distance to other part (glue gap)
    other=B if n=='TOP' else T
    _,dist,_=trimesh.proximity.closest_point(other,d['c'])
    d['ext']=~hit; d['dother']=dist
    print(n,'exterior',d['ext'].sum(),'/',len(hit),'area ext cm2',d['A'][d['ext']].sum()/100,'near-other(<0.6mm)',(dist<0.6).sum())
np.save('work/faces.npy',data,allow_pickle=True)
