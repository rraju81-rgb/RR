import numpy as np, sys
sys.path.insert(0,'.'); from frd import read_frd
def coords(inp):
    t=open(inp).read(); a=t.index('*NODE\n')+6; b=t.index('*ELEMENT')
    X=np.array([list(map(float,l.split(',')[1:])) for l in t[a:b].strip().split('\n')])
    nTop=int(t[t.index('TYPE=C3D10,ELSET=EBOTTOM'):].split('\n')[1].split(',')[1])
    return X
def stress_stats(blk,X,nsplit):
    ids=blk['ids']; sv=blk['vals'][:,:6]
    sxx,syy,szz,sxy,syz,szx=sv.T
    vm=np.sqrt(0.5*((sxx-syy)**2+(syy-szz)**2+(szz-sxx)**2)+3*(sxy**2+syz**2+szx**2))
    M=np.zeros((len(sv),3,3)); M[:,0,0]=sxx;M[:,1,1]=syy;M[:,2,2]=szz;M[:,0,1]=M[:,1,0]=sxy;M[:,1,2]=M[:,2,1]=syz;M[:,0,2]=M[:,2,0]=szx
    ev=np.linalg.eigvalsh(M); p1=ev[:,2]; p3=ev[:,0]
    P=X[ids-1]
    regions={'main body (|x|<520)':(P[:,0]<520)&(ids<=nsplit),'fin zone (|x|>520)':(P[:,0]>=520)&(ids<=nsplit),'BOTTOM plate':ids>nsplit}
    out={}
    for k,m in regions.items():
        if m.sum()==0: continue
        out[k]=dict(vm995=np.percentile(vm[m],99.5),vm_max=vm[m].max(),p1_995=np.percentile(p1[m],99.5),p3_005=np.percentile(p3[m],0.5),syy995=np.percentile(syy[m],99.5))
    return out,dict(ids=ids,vm=vm,p1=p1,p3=p3,sxx=sxx,syy=syy)
