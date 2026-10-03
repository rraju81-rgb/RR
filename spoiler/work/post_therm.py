import numpy as np, sys, json; sys.path.insert(0,'.')
from post_common import *
res={}
for case,G,EN,inp in [('hot +80C','0.10','4','thermal'),('cold -30C','1.5','40','cold')]:
    X=coords(f'fe/{inp}.inp'); t=open(f'fe/{inp}.inp').read()
    nsplitN=int(t[t.index('TYPE=C3D10,ELSET=EBOTTOM'):].split('\n')[1].split(',')[1])-1
    R=read_frd(f'fe/{inp}.frd'); d=[r for r in R if r['name']=='DISP'][-1]; s=[r for r in R if r['name']=='STRESS'][-1]
    st,f=stress_stats(s,X,nsplitN); np.savez(f'f_{inp}.npz',**f)
    U=np.zeros((len(X)+1,3)); U[d['ids']]=d['vals'][:,:3]
    bn,ba=np.load(f'bond_{inp}.npy'); bn=bn.astype(int)
    ut=np.hypot(U[bn,0],U[bn,2]); un=U[bn,1]
    P=X[f['ids']-1]; top=f['ids']<=nsplitN
    cuts={}
    for c,part in [(0,'TOP'),(217,'TOP'),(433,'TOP'),(108,'BOTTOM'),(323,'BOTTOM')]:
        m=(np.abs(P[:,0]-c)<3)&(top if part=='TOP' else ~top)
        cuts[f'{part} x={c}']=dict(sxx_max=f['sxx'][m].max(),sxx_min=f['sxx'][m].min(),sxx_p99=np.percentile(f['sxx'][m],99))
    res[case]=dict(regions=st,cuts=cuts,tape_shear_max=float(float(G)*ut.max()/1.1),tape_shear_strain_max=float(ut.max()/1.1),
                  tape_tension_max=float(float(EN)*un.max()/1.1),slip_max=float(ut.max()))
    print(case); print(json.dumps(res[case],indent=1,default=lambda v: round(float(v),2)))
json.dump(res,open('res_therm.json','w'),indent=1,default=float)
