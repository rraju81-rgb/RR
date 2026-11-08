"""Hypercar-style stingray shell: wings morphed into wheel pods, pinched waist,
thin open-bottom shell, dorsal blade fin, canopy, fender vents, headlights."""
import numpy as np, trimesh, manifold3d as mf
from scipy import ndimage as ndi
from skimage import measure
from shapely.geometry import Polygon, box as sbox
from shapely.geometry.polygon import orient
from shapely import affinity
from hm2 import heightmap

P=dict(rear_cut=48.0, wall=2.0,
       front_axle=-35.0, rear_axle=25.0, pod_len=21.0,   # half-length of each wheel pod
       lift=21.0, pod_top=31.0, min_lift=6.0, core=18.0, ramp=27.0,                  # wing lift over wheels
       waist=0.16, waist_y=-4.0, waist_sigma=15.0,       # plan-view pinch between pods
       wheel_r=9.5, wheel_w=11.0)
BIG=400
def M_from(v,f): return mf.Manifold(mf.Mesh(vert_properties=np.asarray(v,np.float32),tri_verts=np.asarray(f,np.uint32)))
def mesh_of(m):
    t=m.to_mesh(); return np.asarray(t.vert_properties)[:,:3].astype(np.float64),np.asarray(t.tri_verts)
def cube(x0,x1,y0,y1,z0,z1): return mf.Manifold.cube([x1-x0,y1-y0,z1-z0]).translate([x0,y0,z0])

d=np.load('al.npz')
from shapely.geometry import Point
tailcut=sbox(-90,-120,90,30).union(affinity.scale(Point(0,30).buffer(1,128),72,20))   # rounded rear in plan
def extrude0(shp,z0,z1):
    shp=orient(shp,1.0); return mf.Manifold.extrude(mf.CrossSection([np.array(shp.exterior.coords)[:-1].tolist()]),z1-z0).translate([0,0,z0])
body=M_from(d['v'],d['f'])^extrude0(tailcut,-50,150)            # drop the tail, round the rear
V,F=mesh_of(body)

# ---------------- morph: lift wings into wheel pods, pinch waist ----------------
def smooth(t): t=np.clip(t,0,1); return t*t*(3-2*t)
def pod(y):
    out=np.zeros_like(y)
    for ya in (P['front_axle'],P['rear_axle']):
        u=np.abs(y-ya)/P['pod_len']
        out=np.maximum(out,smooth((1.0-u)/0.65))      # rounded, flat-topped pod over the wheel
    return out
x,y,z=V[:,0],V[:,1],V[:,2]
side=smooth((np.abs(x)-P['core'])/P['ramp'])
hm=np.load('hm_al.npz'); ht=np.where(hm['top']>=0,hm['top'],0.0); ht=ndi.gaussian_filter(ht,6)
htop=ndi.map_coordinates(ht,[(y-hm['y0'])/hm['res'],(x-hm['x0'])/hm['res']],order=1,mode='nearest')
amp=np.clip(P['pod_top']-htop,P['min_lift'],P['lift'])      # equalise pod heights
lift=amp*side*pod(y)
s=1-P['waist']*np.exp(-0.5*((y-P['waist_y'])/P['waist_sigma'])**2)*(1-pod(y))
ax=np.abs(x); xn=np.where(ax>P['core'],np.sign(x)*(P['core']+(ax-P['core'])*s),x)
V2=np.c_[xn,y,z+lift]
body=M_from(V2,F); assert body.status()==mf.Error.NoError

# ---------------- canopy (hollowed with the body) ----------------
cz_top=None
canopy=mf.Manifold.batch_hull([mf.Manifold.sphere(1,96).scale([10,13,7.5]).translate([4,-10,22.5]),mf.Manifold.sphere(1,64).scale([4.5,6,4]).translate([-3,18,21])])
body=body+canopy
V,F=mesh_of(body)

# ---------------- heightmap + exact ball-offset cavity ----------------
res=0.25
top,bot,x0,y0,_=heightmap(V,F,res=res,n=14000000)
foot=ndi.binary_fill_holes(ndi.binary_closing(top>=0,iterations=2))
valid=top>=0
_,ind=ndi.distance_transform_edt(~valid,return_indices=True)
topf=top[ind[0],ind[1]]; botf=bot[ind[0],ind[1]]
low=heightmap.low; lv=low<999
_,ind2=ndi.distance_transform_edt(~lv,return_indices=True)
lowf=np.minimum(low[ind2[0],ind2[1]],topf)
lowf=ndi.median_filter(lowf,size=9)
lowf=np.where((topf-lowf)<8.0,np.minimum(lowf,topf),topf)
pocket=ndi.binary_dilation((topf-lowf)>1.0,iterations=16)&foot
lowf[pocket]=ndi.grey_erosion(lowf,size=17)[pocket]
topf[~foot]=-50; botf[~foot]=999; lowf[~foot]=-50
H,W=top.shape; xs=x0+np.arange(W)*res; ys=y0+np.arange(H)*res

def heightfield(Z,zb):
    X,Y=np.meshgrid(xs,ys); n=H*W
    v=np.vstack([np.c_[X.ravel(),Y.ravel(),Z.ravel()],np.c_[X.ravel(),Y.ravel(),np.full(n,zb)]])
    idx=np.arange(n).reshape(H,W)
    a=idx[:-1,:-1].ravel(); b=idx[:-1,1:].ravel(); c=idx[1:,1:].ravel(); e=idx[1:,:-1].ravel()
    fs=[np.r_[np.c_[a,b,c],np.c_[a,c,e]], np.r_[np.c_[a,c,b],np.c_[a,e,c]]+n]
    def strip(line,flip):
        p=line[:-1]; q=line[1:]; t=np.r_[np.c_[p,q,q+n],np.c_[p,q+n,p+n]]
        fs.append(t[:,[0,2,1]] if flip else t)
    strip(idx[0,:],True); strip(idx[-1,:],False); strip(idx[:,0],False); strip(idx[:,-1],True)
    m=M_from(v,np.vstack(fs)); assert m.status()==mf.Error.NoError, m.status(); return m

t=P['wall']; r=int(np.ceil(t/res)); Z=np.full_like(topf,np.inf)
pad=np.pad(lowf,r,constant_values=-50)
for dy in range(-r,r+1):
    for dx in range(-r,r+1):
        dd=np.hypot(dx,dy)*res
        if dd<=t: Z=np.minimum(Z,pad[r+dy:r+dy+H,r+dx:r+dx+W]-np.sqrt(t*t-dd*dd))
Z=np.maximum(Z,-4.0)
cavity=heightfield(Z,-6.0)

# ---------------- footprint, wheels ----------------
cs=measure.find_contours(foot.astype(float),0.5); cmax=max(cs,key=len)
poly=Polygon(np.c_[x0+cmax[:,1]*res,y0+cmax[:,0]*res]).buffer(0).simplify(0.05)
def edge_x(yc): b=poly.intersection(sbox(-BIG,yc-2,BIG,yc+2)).bounds; return b[0],b[2]
ci=lambda x,y:(int(round((y-y0)/res)),int(round((x-x0)/res)))
R=P['wheel_r']; w=P['wheel_w']; wheels=[]
for ya in (P['front_axle'],P['rear_axle']):
    xl,xr=edge_x(ya)
    for sd,edge in ((-1,xl),(1,xr)):
        outer=edge-sd*2.0; inner=outer-sd*w
        wheels.append((ya,sd,(inner+outer)/2,min(inner,outer),max(inner,outer)))
# clearance report: cavity roof over each wheel footprint vs wheel top
for ya,sd,xc,a,b in wheels:
    clear=[]
    for yy in np.arange(ya-R,ya+R,0.5):
        zt=R+np.sqrt(max(R*R-(yy-ya)**2,0))
        for xx in np.arange(a,b,0.5):
            i,j=ci(xx,yy)
            if foot[i,j]: clear.append(max(Z[i,j],botf[i,j])-zt)
    print('wheel y%.0f x%.1f  min roof clearance %.1f mm'%(ya,xc,min(clear) if clear else 99))

def extrude(shp,z0,z1):
    shp=orient(shp if shp.geom_type=='Polygon' else max(shp.geoms,key=lambda g:g.area),1.0)
    return mf.Manifold.extrude(mf.CrossSection([np.array(shp.exterior.coords)[:-1].tolist()]),z1-z0).translate([0,0,z0])
def engrave(shp,depth):
    """recess that follows the outer skin"""
    return extrude(shp,-10,120)-heightfield(np.where(foot,topf-depth,-5.0).clip(-5),-8.0)

# ---------------- fender vents (through-openings on top of each pod) ----------------
cuts=[]
for ya,sd,xc,a,b in wheels:
    off=-7.0 if ya<0 else 7.0                    # front pods: vent ahead of axle; rear: behind
    e=affinity.rotate(Polygon(np.array([[np.cos(q)*4.2,np.sin(q)*8.5] for q in np.linspace(0,2*np.pi,64,endpoint=False)])),-sd*12)
    e=affinity.translate(e,xc-sd*8.0,ya+off)
    cuts.append(extrude(e,0,80))
# ---------------- headlights: raked recesses on the nose of the front pods ----------------
for ya,sd,xc,a,b in wheels:
    if ya>0: continue
    yf=poly.intersection(sbox(xc-0.5,-BIG,xc+0.5,BIG)).bounds[1]
    hl=Polygon([[-6,0],[6,2.5],[6,5],[-6,3]])
    if sd<0: hl=affinity.scale(hl,-1,1,origin=(0,0))
    hl=affinity.translate(hl,xc-sd*4,yf+2.5)
    cuts.append(engrave(hl,1.0))
    for k in range(3):                            # LED segments inside the lamp
        led=affinity.translate(sbox(-0.6,0,0.6,1.6),xc-sd*(1+k*3.0),yf+2.5+1.0+ (k*0.6 if sd>0 else -k*0.6)+ (1.2 if sd<0 else 0))
        cuts.append(engrave(led,1.6))

# ---------------- dorsal blade fin (the ray's tail reborn) ----------------
prof=Polygon([(10,16),(30,22),(48,27),(62,36),(74,48),(82,57),(86,57),(84,50),(72,34),(56,20),(40,14),(10,12)])
cs_=mf.CrossSection([np.array(orient(prof,1.0).exterior.coords)[:-1].tolist()])
fin=mf.Manifold.extrude(cs_,2.6).translate([0,0,-1.3])        # profile in (y,z), thickness along new z
fin=fin.rotate([90,0,0]).rotate([0,0,90])                       # -> profile in YZ plane, thick along X
fv,ff=mesh_of(fin); print('fin bounds',fv.min(0).round(1),fv.max(0).round(1))
fin=fin.translate([-6.0,0,0])

# ---------------- assemble ----------------
car=body-cavity
car=car-mf.Manifold.batch_boolean(cuts,mf.OpType.Add)
car=car+fin
car=car^cube(-BIG,BIG,-BIG,BIG,0,BIG)
print('status',car.status(),'tris',car.num_tri(),'vol %.0f'%car.volume(),'genus',car.genus())
v,f=mesh_of(car); np.savez('car2.npz',v=v,f=f); print('bounds',v.min(0).round(1),v.max(0).round(1))
