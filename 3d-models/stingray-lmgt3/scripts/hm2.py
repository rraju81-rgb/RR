import numpy as np, trimesh, sys
def heightmap(v,f,res=0.5,n=6000000,pad=10):
    m=trimesh.Trimesh(v,f,process=False)
    x0,y0=v[:,0].min()-pad,v[:,1].min()-pad
    W=int((v[:,0].max()+pad-x0)/res)+1; H=int((v[:,1].max()+pad-y0)/res)+1
    top=np.full((H,W),-1.0); bot=np.full((H,W),999.0)
    pts,fi=trimesh.sample.sample_surface(m,n)
    ix=((pts[:,0]-x0)/res).astype(int); iy=((pts[:,1]-y0)/res).astype(int)
    np.maximum.at(top,(iy,ix),pts[:,2]); np.minimum.at(bot,(iy,ix),pts[:,2])
    up=m.face_normals[fi][:,2]>0.05
    low=np.full((H,W),999.0); np.minimum.at(low,(iy[up],ix[up]),pts[up,2])
    heightmap.low=low
    return top,bot,x0,y0,res
if __name__=='__main__':
    d=np.load('al.npz'); top,bot,x0,y0,res=heightmap(d['v'],d['f'])
    np.savez('hm_al.npz',top=top,bot=bot,x0=x0,y0=y0,res=res)
    for y in range(-78,92,6):
        r=int((y-y0)/res); row=top[r]; cols=np.where(row>=0)[0]
        if len(cols)==0: print(y,'empty');continue
        xs=x0+cols*res
        # height at x offsets
        hs=[row[int((xx-x0)/res)] for xx in (-50,-40,-30,0,30,40,50)]
        print('%4d x %5.0f..%4.0f maxz %5.1f | z@-50,-40,-30,0,30,40,50: '%(y,xs.min(),xs.max(),row.max())+' '.join('%5.1f'%h for h in hs),' bot0 %.1f'%bot[r][int((0-x0)/res)])
