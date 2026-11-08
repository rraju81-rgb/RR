import numpy as np, trimesh, manifold3d as mf
from scipy import ndimage as ndi
from skimage import measure
from shapely.geometry import Polygon, box as sbox
from shapely.geometry.polygon import orient
from hm2 import heightmap

P=dict(rear_cut=48.0, wall=2.2, fascia_y=-47.0,
       wheel_r=9.5, wheel_w=11.0, arch_r=11.0, hoop_t=2.2,
       front_axle=-35.0, rear_axle=32.0, splitter_out=3.0, splitter_t=1.4)

d=np.load('al.npz'); V,F=d['v'],d['f']
def M_from(v,f): return mf.Manifold(mf.Mesh(vert_properties=np.asarray(v,np.float32),tri_verts=np.asarray(f,np.uint32)))
body=M_from(V,F)
BIG=400
def cube(x0,x1,y0,y1,z0,z1): return mf.Manifold.cube([x1-x0,y1-y0,z1-z0]).translate([x0,y0,z0])

# ---------- heightmap (0.25mm) ----------
res=0.25
top,bot,x0,y0,_=heightmap(V,F,res=res,n=14000000)
foot=ndi.binary_fill_holes(ndi.binary_closing(top>=0,iterations=2))
# fill empty cells inside footprint with nearest sample
valid=top>=0
_,ind=ndi.distance_transform_edt(~valid,return_indices=True)
topf=top[ind[0],ind[1]]; botf=bot[ind[0],ind[1]]
low=heightmap.low; lv=low<999
_,ind2=ndi.distance_transform_edt(~lv,return_indices=True)
lowf=np.minimum(low[ind2[0],ind2[1]],topf)
lowf=ndi.median_filter(lowf,size=9)            # kill isolated spurious samples
lowf=np.where((topf-lowf)<8.0, np.minimum(lowf,topf), topf)   # only real overhang pockets (eyes)
pocket=ndi.binary_dilation((topf-lowf)>1.0,iterations=16)&foot
lowf[pocket]=ndi.grey_erosion(lowf,size=17)[pocket]           # extra margin around eye sockets
topf[~foot]=-50; botf[~foot]=999
H,W=top.shape
xs=x0+np.arange(W)*res; ys=y0+np.arange(H)*res

def heightfield(Z,zb):
    """watertight prism: top surface Z (H,W) over grid, flat bottom zb"""
    H,W=Z.shape
    X,Y=np.meshgrid(xs,ys)
    vt=np.c_[X.ravel(),Y.ravel(),Z.ravel()]
    vb=np.c_[X.ravel(),Y.ravel(),np.full(H*W,zb)]
    v=np.vstack([vt,vb]); n=H*W
    idx=np.arange(n).reshape(H,W)
    a=idx[:-1,:-1].ravel(); b=idx[:-1,1:].ravel(); c=idx[1:,1:].ravel(); e=idx[1:,:-1].ravel()
    ft=np.r_[np.c_[a,b,c],np.c_[a,c,e]]
    fb=np.r_[np.c_[a,c,b],np.c_[a,e,c]]+n
    walls=[]
    def strip(line,flip):
        p=line[:-1]; q=line[1:]
        t1=np.c_[p,q,q+n]; t2=np.c_[p,q+n,p+n]
        t=np.r_[t1,t2]
        if flip: t=t[:,[0,2,1]]
        walls.append(t)
    strip(idx[0,:],True)
    strip(idx[-1,:],False)
    strip(idx[:,0],False)
    strip(idx[:,-1],True)
    f=np.vstack([ft,fb]+walls)
    m=M_from(v,f)
    if m.volume()<0 or m.status()!=mf.Error.NoError:
        f=f[:,[0,2,1]]; m=M_from(v,f)
    assert m.status()==mf.Error.NoError, m.status()
    return m

# ---------- interior cavity: exact ball offset of the top skin ----------
t=P['wall']; r=int(np.ceil(t/res))
Z=np.full_like(topf,np.inf)
lowf[~foot]=-50
pad=np.pad(lowf,r,constant_values=-50)
for dy in range(-r,r+1):
    for dx in range(-r,r+1):
        dd=np.hypot(dx,dy)*res
        if dd>t: continue
        sh=pad[r+dy:r+dy+H, r+dx:r+dx+W]
        Z=np.minimum(Z, sh-np.sqrt(t*t-dd*dd))
Z=np.maximum(Z,-4.0)
Z[ys>P['rear_cut']-t,:]=-4.0
cavity=heightfield(Z,-6.0)
print('cavity ok',cavity.volume())

# ---------- footprint outline polygon ----------
cs=measure.find_contours(foot.astype(float),0.5)
cmax=max(cs,key=len)
poly=Polygon(np.c_[x0+cmax[:,1]*res, y0+cmax[:,0]*res]).buffer(0).simplify(0.05)
def extrude(shp,z0,z1):
    shp=shp if shp.geom_type=='Polygon' else max(shp.geoms,key=lambda g:g.area)
    shp=orient(shp,1.0)
    pts=np.array(shp.exterior.coords)[:-1]
    cs_=mf.CrossSection([pts.tolist()])
    return mf.Manifold.extrude(cs_,z1-z0).translate([0,0,z0])

# ---------- front fascia (green): fill under nose down to plate + splitter ----------
front=poly.intersection(sbox(-BIG,-BIG,BIG,P['fascia_y']))
Zf=np.where(foot, topf-0.2, -2.0); Zf=np.maximum(Zf,-2.0)
under_skin=heightfield(Zf,-3.0)
fascia=extrude(front,-2,40)^under_skin
spl=poly.buffer(P['splitter_out']).intersection(sbox(-BIG,-BIG,BIG,P['fascia_y']-2))
splitter=extrude(spl,-2,P['splitter_t'])

# ---------- wheels / arches (red front, blue rear) ----------
def edge_x(yc):
    seg=poly.intersection(sbox(-BIG,yc-3,BIG,yc+3)).bounds
    return seg[0],seg[2]
def cyl_x(xa,xb,yc,zc,rad):
    c=mf.Manifold.cylinder(xb-xa,rad,rad,128).rotate([0,90,0]).translate([xa,yc,zc])
    return c
hoops=[]; cuts=[]; wheels=[]
R=P['wheel_r']; w=P['wheel_w']; ra=P['arch_r']; ht=P['hoop_t']
for ya in (P['front_axle'],P['rear_axle']):
    xl,xr=edge_x(ya)
    for side,edge in ((-1,xl),(1,xr)):
        outer=edge-side*1.0; inner=outer-side*w
        a,b=sorted([inner,outer])
        ro=ra+ht
        c1=cyl_x(a-1.5,b+1.5,ya,R,ro)
        ib=a-1.5 if side>0 else b+1.5            # inboard face
        c2=cyl_x(ib-12,ib,ya,R-2,0.55*ro) if side>0 else cyl_x(ib,ib+12,ya,R-2,0.55*ro)
        e=mf.Manifold.sphere(1,96).scale([w/2+1.5,1.6*ro,0.5*ro]).translate([(a+b)/2,ya,R-2])
        hoop=mf.Manifold.batch_hull([c1,c2,e])^cube(-BIG,BIG,-BIG,P['rear_cut'],1.0,60)
        hoops.append(hoop)
        ca,cb=(a-1.5,b+40) if side>0 else (a-40,b+1.5)
        cuts.append(cyl_x(ca,cb,ya,R,ra))
        wheels.append((round(ya,1),round((a+b)/2,1)))
print('wheel centres (y,x):',wheels)

# ---------- grille + side intakes ----------
def front_y(x):
    g=poly.intersection(sbox(x-0.01,-BIG,x+0.01,BIG))
    return g.bounds[1]
ci=lambda x,y:(int(round((y-y0)/res)),int(round((x-x0)/res)))
grille=[]
def slot_col(x,zlo,zhi,depth=4.0):
    yf=front_y(x+0.5)
    i,j=ci(x+0.5,yf+1.0); zmax=botf[i,j]-0.9 if foot[i,j] else 0
    zh=min(zhi,zmax)
    if zh-zlo>=0.7: grille.append(cube(x,x+1.0,yf-3,yf+depth,zlo,zh))
for x in np.arange(-2,36,1.0):
    for lo,hi in ((1.9,3.0),(3.6,4.7),(5.3,6.4)):
        slot_col(x,lo,hi)
for x in list(np.arange(-50,-40,1.0))+list(np.arange(40,48,1.0)):
    slot_col(x,1.9,8.0)
grille=mf.Manifold.batch_boolean(grille,mf.OpType.Add)

for nm,o in [("body",body),("fascia",fascia),("under",under_skin),("splitter",splitter),("grille",grille)]+[("hoop",h) for h in hoops]+[("cut",c) for c in cuts]: print(nm,o.status(),o.num_tri())
# ---------- assemble ----------
car=body^cube(-BIG,BIG,-BIG,P['rear_cut'],-BIG,BIG)
car=mf.Manifold.batch_boolean([car,fascia,splitter]+hoops,mf.OpType.Add)
car=car-cavity-grille
car=car-mf.Manifold.batch_boolean(cuts,mf.OpType.Add)
car=car^cube(-BIG,BIG,-BIG,BIG,0,BIG)
print('status',car.status(),'tris',car.num_tri(),'vol',car.volume(),'genus',car.genus())
mesh=car.to_mesh()
v=np.asarray(mesh.vert_properties)[:,:3]; f=np.asarray(mesh.tri_verts)
np.savez('car.npz',v=v,f=f)
# wall-thickness check: cavity roof must stay >= wall from the original skin
import trimesh
orig=trimesh.Trimesh(V,F,process=False)
cm=cavity.to_mesh(); cv=np.asarray(cm.vert_properties)[:,:3]
cv=cv[(cv[:,2]>0.5)&(cv[:,1]<P['rear_cut']-3)]
cv=cv[np.random.default_rng(0).choice(len(cv),min(40000,len(cv)),replace=False)]
ii=((cv[:,1]-y0)/res).astype(int); jj=((cv[:,0]-x0)/res).astype(int)
inside=(cv[:,2]>botf[ii,jj]+0.05)&(cv[:,2]<topf[ii,jj])
print('cavity roof points inside original material: %d of %d'%(inside.sum(),len(cv)))
cv=cv[inside]
upf=orig.face_normals[:,2]>-0.2
outer=trimesh.Trimesh(V,F[upf],process=False)
_,dist,_=trimesh.proximity.closest_point(outer,cv)
thin=cv[dist<1.0]; print('thin pts',len(thin)); 
for p in thin: 
    i,j=int((p[1]-y0)/res),int((p[0]-x0)/res); print('  %.1f %.1f %.1f  top %.1f bot %.1f low %.1f'%(p[0],p[1],p[2],topf[i,j],botf[i,j],lowf[i,j]))
print('cavity-to-skin distance: min %.2f  p1 %.2f  median %.2f'%(dist.min(),np.percentile(dist,1),np.median(dist)))
print('bounds',v.min(0),v.max(0))
