"""Build CalculiX half-model (x>=0, symmetry at x=0) of the v5 spoiler assembly."""
import numpy as np, sys
sys.path.insert(0,'work'); from surf import FACES
D=np.load('work/faces.npy',allow_pickle=True).item()
case=sys.argv[1]           # 'mech' or 'thermal'
out=sys.argv[2]
NLG=len(sys.argv)>3
TEND=-30. if case=='cold' else 80.
# ---------------- parameters ----------------
G_TAPE = {'mech':0.30,'thermal':0.10,'cold':1.5}[case]   # MPa, VHB shear modulus (20C / 80C)
EN_TAPE= {'mech':10.0,'thermal':4.0,'cold':40.0}[case]    # MPa, effective normal (compression/tension) modulus of bonded layer
H_TAPE = 1.1                               # mm
COVER  = 0.6                               # fraction of bonded footprint actually covered by tape
V_KMH  = 250.0
q = 0.5*1.225*(V_KMH/3.6)**2*1e-6          # MPa
E_ASA = 1800.; NU=0.35; RHO=1.07e-9
# ---------------- nodes / C3D10 ----------------
nodes=[]; elems=[]; off=0; info={}
EDGES=[(0,1),(1,2),(2,0),(0,3),(1,3),(2,3)]
for part in ['TOP','BOTTOM']:
    d=D[part]; N=d['N']; E=d['E']
    allE=np.vstack([E[:,list(a)] for a in EDGES]); key=np.sort(allE,1)
    uk,inv=np.unique(key,axis=0,return_inverse=True)
    mid=(N[uk[:,0]]+N[uk[:,1]])/2
    NN=np.vstack([N,mid]); mids=inv.reshape(6,-1).T+len(N)
    E10=np.hstack([E,mids])+off+1
    info[part]=dict(off=off,E10=E10,edgekey=uk,nN=len(N))
    nodes.append(NN); elems.append(E10); off+=len(NN)
X=np.vstack(nodes); nE_top=len(elems[0])
eoff={'TOP':0,'BOTTOM':nE_top}
# face -> 6 node ids (corner + midside) in ccx numbering
FMID={0:(4,5,6),1:(7,8,4),2:(8,9,5),3:(9,7,6)}
def face_nodes(part,e,k):
    E10=info[part]['E10'][e]; c=[E10[i] for i in FACES[k]]; m=[E10[i] for i in FMID[k]]
    return c,m
lines=[]; W=lines.append
W('*HEADING\nPolo spoiler v5 half model %s'%case)
W('*NODE')
for i,p in enumerate(X): W('%d,%.5f,%.5f,%.5f'%(i+1,*p))
for part in ['TOP','BOTTOM']:
    W('*ELEMENT,TYPE=C3D10,ELSET=E%s'%part)
    for j,r in enumerate(info[part]['E10']): W('%d,'%(j+1+eoff[part])+','.join(map(str,r)))
W('*ELSET,ELSET=EALL\nETOP,EBOTTOM')
# ---------------- surfaces ----------------
def surf_lines(name,part,mask):
    d=D[part]; W('*SURFACE,NAME=%s,TYPE=ELEMENT'%name)
    for e,k in zip(d['e'][mask],d['k'][mask]): W('%d,S%d'%(e+1+eoff[part],k+1))
glue_t=D['TOP']['dother']<0.6; glue_b=D['BOTTOM']['dother']<0.6
surf_lines('SGLUET','TOP',glue_t)
gb=set()
for e,k in zip(D['BOTTOM']['e'][glue_b],D['BOTTOM']['k'][glue_b]):
    c,m=face_nodes('BOTTOM',e,k); gb.update(c); gb.update(m)
W('*NSET,NSET=NGLUEB'); 
gb=sorted(gb)
for i in range(0,len(gb),12): W(','.join(map(str,gb[i:i+12])))
W('*SURFACE,NAME=SGLUEB,TYPE=NODE\nNGLUEB')
W('*TIE,NAME=GLUE,POSITION TOLERANCE=0.8,ADJUST=NO\nSGLUEB,SGLUET')
# symmetry
sym=np.where(np.abs(X[:,0])<1e-3)[0]+1
W('*NSET,NSET=NSYM')
for i in range(0,len(sym),12): W(','.join(map(str,sym[i:i+12])))
# ---------------- tape springs (bonded underside) ----------------
area=np.zeros(len(X)+1)
bond={}
for part in ['TOP','BOTTOM']:
    d=D[part]; m=d['ext']&(d['n'][:,1]<-0.2)&(d['c'][:,0]<545)
    bond[part]=m
    for e,k,A in zip(d['e'][m],d['k'][m],d['A'][m]):
        c,mm=face_nodes(part,e,k)
        for n in c: area[n]+=A/12
        for n in mm: area[n]+=A/4
bn=np.where(area>0)[0]
print('bonded area (half) cm2',area.sum()/100,'nodes',len(bn))
np.save(f'work/bond_{case}.npy',np.vstack([bn,area[bn]]))
kS=G_TAPE/H_TAPE*COVER; kN=EN_TAPE/H_TAPE*COVER    # N/mm per mm2
# bin by area (log bins)
bins=np.geomspace(area[bn].min()*0.999,area[bn].max()*1.001,41)
ib=np.digitize(area[bn],bins)
eid=len(np.vstack(elems))+1; 
for b in np.unique(ib):
    sel=bn[ib==b]; Arep=area[sel].mean()
    for dof,k in [(1,kS),(2,kN),(3,kS)]:
        W('*ELEMENT,TYPE=SPRING1,ELSET=SP%d_%d'%(b,dof))
        for n in sel: W('%d,%d'%(eid,n)); eid+=1
        W('*SPRING,ELSET=SP%d_%d\n%d\n%.6g'%(b,dof,dof,k*Arep))
# ---------------- material ----------------
W('*MATERIAL,NAME=ASA')
if case=='mech':
    W('*ELASTIC\n%g,%g'%(E_ASA,NU))
    W('*DENSITY\n%g'%RHO)
else:
    W('*ELASTIC\n%g,%g,-30.\n%g,%g,20.\n%g,%g,80.'%(2200.,NU,E_ASA,NU,1100.,NU))
    W('*EXPANSION,ZERO=20.\n%g,-30.\n%g,80.'%(83e-6,83e-6))   # ASA 95e-6 minus steel roof 12e-6
    W('*DENSITY\n%g'%RHO)
W('*SOLID SECTION,ELSET=EALL,MATERIAL=ASA')
W('*BOUNDARY\nNSYM,1,1,0.')
if case!='mech':
    W('*INITIAL CONDITIONS,TYPE=TEMPERATURE\n1,20.')  # placeholder replaced below
    lines[-1]='*INITIAL CONDITIONS,TYPE=TEMPERATURE'
    for i in range(len(X)): W('%d,20.'%(i+1))
# ---------------- loads helpers ----------------
def exterior_pressure_loads():
    out=[]
    for part in ['TOP','BOTTOM']:
        d=D[part]; m=d['ext']&~bond[part]
        n=d['n'][m]
        cp=np.where(n[:,2]<-0.3, 1.0, np.where(n[:,2]>0.5,1.0, np.where(n[:,1]>0.2,-1.2,-0.5)))
        # rear faces: n_z>0.5 face rearward (+z) -> wake, base pressure
        cp=np.where(n[:,2]>0.5,-0.4,cp)
        for e,k,c in zip(d['e'][m],d['k'][m],cp):
            out.append('%d,P%d,%.6g'%(e+1+eoff[part],k+1,c*q))
    return out
def patch_nodes(sel_fn,part='TOP'):
    d=D[part]; m=d['ext']&sel_fn(d['c'],d['n']); s=set()
    for e,k in zip(d['e'][m],d['k'][m]):
        c,mm=face_nodes(part,e,k); s.update(c); s.update(mm)
    return np.array(sorted(s))
def cload(nodes,F):
    o=[]; Fn=np.array(F)/len(nodes)
    for n in nodes:
        for j in range(3):
            if Fn[j]!=0: o.append('%d,%d,%.6g'%(n,j+1,Fn[j]))
    return o
def step(title,body):
    W('*STEP\n*STATIC'); W('** '+title); lines.extend(body)
    W('*NODE FILE\nU\n*EL FILE\nS\n*END STEP')
zmax=X[:,2].max()
if case=='mech':
    step('LC1 aero 250kmh + gravity',['*DLOAD,OP=NEW']+exterior_pressure_loads()+['EALL,GRAV,9810.,0.,-1.,0.'])
    lip=patch_nodes(lambda c,n:(c[:,0]<25)&(c[:,2]>zmax-25)&(n[:,1]>0.2))
    step('LC2 150N push down on rear lip centre (75N half)',['*DLOAD,OP=NEW','*CLOAD,OP=NEW']+cload(lip,[0,-75,0]))
    lipu=patch_nodes(lambda c,n:(c[:,0]<25)&(c[:,2]>zmax-12)&(n[:,1]<-0.2))
    if len(lipu)==0: lipu=lip
    step('LC3 100N pull up on rear lip centre (50N half)',['*DLOAD,OP=NEW','*CLOAD,OP=NEW']+cload(lipu,[0,50,0]))
    xm=X[:,0].max()
    fin=patch_nodes(lambda c,n:(c[:,0]>xm-15))
    step('LC4 50N down on fin tip',['*DLOAD,OP=NEW','*CLOAD,OP=NEW']+cload(fin,[0,-50,0]))
    step('LC5 50N outward on fin tip',['*DLOAD,OP=NEW','*CLOAD,OP=NEW']+cload(fin,[50,0,0]))
    W('** lip nodes %d lipu %d fin %d'%(len(lip),len(lipu),len(fin)))
else:
    W('*STEP,NLGEOM,INC=200\n*STATIC\n0.1,1.0,1e-4,0.2' if NLG else '*STEP\n*STATIC')
    W('*TEMPERATURE')
    for i in range(len(X)): W('%d,%g'%(i+1,TEND))
    W('*NODE FILE\nU\n*EL FILE\nS\n*END STEP')
open(out,'w').write('\n'.join(lines)+'\n')
print('nodes',len(X),'elements',sum(len(e) for e in elems),'springs',eid-sum(len(e) for e in elems)-1)
