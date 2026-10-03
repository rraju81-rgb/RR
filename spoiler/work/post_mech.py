import numpy as np, sys
sys.path.insert(0,'.'); from frd import read_frd
R=read_frd('fe/mech.frd')
inp=open('fe/mech.inp').read()
# node coords
a=inp.index('*NODE\n')+6; b=inp.index('*ELEMENT')
X=np.array([list(map(float,l.split(',')[1:])) for l in inp[a:b].strip().split('\n')])
nTop=int(inp[inp.index('TYPE=C3D10,ELSET=EBOTTOM'):].split('\n')[1].split(',')[1])-1
names=['LC1 aero 250 km/h + gravity','LC2 150 N push down, rear lip','LC3 100 N pull up, rear lip','LC4 50 N down, fin tip','LC5 50 N outward, fin tip']
D=[r for r in R if r['name']=='DISP']; S=[r for r in R if r['name']=='STRESS']
bn,ba=np.load('bond_mech.npy'); bn=bn.astype(int)
kS=0.30/1.1*0.6; kN=10/1.1*0.6
out=[]
for i,(d,s) in enumerate(zip(D,S)):
    u=np.zeros((len(X)+1,3)); u[d['ids']]=d['vals'][:,:3]
    sv=s['vals'][:,:6]; ids=s['ids']
    sxx,syy,szz,sxy,syz,szx=sv.T
    vm=np.sqrt(0.5*((sxx-syy)**2+(syy-szz)**2+(szz-sxx)**2)+3*(sxy**2+syz**2+szx**2))
    p1=np.array([np.linalg.eigvalsh(np.array([[a,d_,f],[d_,b,e],[f,e,c]])).max() for a,b,c,d_,e,f in sv])
    top=ids<=nTop
    um=np.linalg.norm(u,axis=1)
    j=np.argmax(um)
    # tape stresses
    un=u[bn,1]; ut=np.hypot(u[bn,0],u[bn,2])
    peel=(kN*un).max()/0.6 ; shear=(kS*ut).max()/0.6   # stress in covered tape
    lift=(kN*un*ba).sum()*2  # net tape normal force (full part), + = tape in compression? un>0 means moving up -> tension
    r=dict(case=names[i],umax=um.max(),uat=X[j-1].round(0).tolist(),vm_top=vm[top].max(),vm_bot=vm[~top].max(),
           p1=p1.max(),syy_t=syy.max(),tape_tension=peel,tape_shear=shear,netF=lift)
    out.append(r); print({k:(round(v,3) if isinstance(v,float) else v) for k,v in r.items()})
    np.savez(f'res_lc{i+1}.npz',ids=ids,vm=vm,p1=p1,syy=syy,sxx=sxx,u=u)
import json; json.dump(out,open('res_mech.json','w'),indent=1,default=float)
