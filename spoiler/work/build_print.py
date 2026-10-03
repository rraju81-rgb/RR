"""Split v5 TOP/BOTTOM into on-end printable sections and generate conformal joint splices."""
import trimesh, numpy as np, manifold3d as mf, shapely
from shapely.geometry import Polygon, MultiPolygon
from shapely.ops import unary_union
import os, json
os.makedirs('print',exist_ok=True)
T=trimesh.load('input/v5_TOP.stl'); B=trimesh.load('input/v5_BOTTOM.stl')
def tomf(m): return mf.Manifold(mf.Mesh(vert_properties=np.asarray(m.vertices,np.float32), tri_verts=np.asarray(m.faces,np.uint32)))
def totm(M):
    g=M.to_mesh(); V=np.asarray(g.vert_properties[:,:3],np.float64); F=np.asarray(g.tri_verts).copy()
    mf_=np.asarray(g.merge_from_vert); mt=np.asarray(g.merge_to_vert)
    if len(mf_):
        remap=np.arange(len(V)); remap[mf_]=mt; F=remap[F]
    return trimesh.Trimesh(V, F, process=True)
MT,MB=tomf(T),tomf(B)
TOP_CUTS=[-433,-217,0,217,433]; BOT_CUTS=[-323,-108,108,323]
def slab(x0,x1): return mf.Manifold.cube([x1-x0,1000,1000]).translate([x0,-500,-500])
def sections(M,cuts,lo,hi):
    xs=[lo-1]+cuts+[hi+1]; out=[]
    for a,b in zip(xs[:-1],xs[1:]): out.append(((a,b),M^slab(a,b)))
    return out
# ---------- 2D section helpers (plane coords u=y, v=z) ----------
def sec2d(m,x):
    s=m.section(plane_origin=[x,0,0],plane_normal=[1,0,0])
    if s is None: return Polygon()
    polys=[]
    for e in s.discrete:
        if len(e)>=4: polys.append(Polygon(e[:,[1,2]]))
    # even-odd fill
    res=Polygon()
    for p in polys:
        p=p.buffer(0); res=res.symmetric_difference(p)
    return res.buffer(0)
def sweep(P,d):
    """Minkowski sum of P with segment [0, d] along u (y) direction."""
    parts=[P]
    geoms=P.geoms if hasattr(P,'geoms') else [P]
    for g in geoms:
        rings=[g.exterior]+list(g.interiors)
        for r in rings:
            c=np.asarray(r.coords)
            for a,b in zip(c[:-1],c[1:]):
                q=Polygon([a,b,b+[d,0],a+[d,0]])
                if q.area>1e-9: parts.append(q)
    return unary_union(parts)
def cavity(tp,bp):
    u=unary_union([tp,bp]).buffer(0.35,join_style=2)
    geoms=u.geoms if hasattr(u,'geoms') else [u]
    env=unary_union([Polygon(g.exterior) for g in geoms])
    return env.buffer(-0.35).difference(tp).difference(bp)
def splice_profile(x,host,other,below):
    hp=sec2d(T if host=='T' else B,x); op=sec2d(B if host=='T' else T,x)
    tp,bp=(hp,op) if host=='T' else (op,hp)
    cav=cavity(tp,bp)
    band=hp.buffer(2.15).difference(hp.buffer(0.15))
    keep=cav.intersection(band).difference(op.buffer(1.0))
    # insertable: TOP splice inserted from below (-y) => remove pts with host material below them
    blocker=sweep(hp.buffer(0.15), +400 if below else -400)  # host swept upward(+y) marks points above host... 
    keep=keep.difference(blocker)
    keep=keep.buffer(-0.4).buffer(0.4)
    if hasattr(keep,'geoms'): keep=unary_union([g for g in keep.geoms if g.area>20])
    return keep
def cs_from(poly):
    geoms=poly.geoms if hasattr(poly,'geoms') else [poly]
    loops=[]
    for g in geoms:
        if g.is_empty: continue
        loops.append(np.asarray(g.exterior.coords)[:-1])
        for r in g.interiors: loops.append(np.asarray(r.coords)[:-1])
    return mf.CrossSection([l.astype(np.float64) for l in loops], mf.FillRule.EvenOdd)
def make_splice(c,host,half=12.0,step=1.0):
    xs=np.arange(c-half,c+half+1e-6,step)
    profs=[splice_profile(x,host,None,below=(host=='T')) for x in xs]
    M=None; areas=[]
    for i in range(len(xs)-1):
        p=profs[i].intersection(profs[i+1])
        areas.append(p.area)
        if p.is_empty or p.area<5: continue
        e=cs_from(p).extrude(step+0.02)
        # local (u,v,w)=(y,z,x) -> world (x,y,z)=(w,u,v)
        e=e.transform([[0,0,1,xs[i]-0.01],[1,0,0,0],[0,1,0,0]])
        M=e if M is None else M+e
    return M,min(areas),max(areas)

def resample_ring(poly,N=400):
    r=poly.exterior
    if not r.is_ccw: r=shapely.geometry.LinearRing(list(r.coords)[::-1])
    c=np.asarray(r.coords)[:-1]
    # start at min-z point (v coord = z) to get consistent correspondence
    i0=np.argmin(c[:,1]+1e-3*c[:,0]); c=np.roll(c,-i0,axis=0); c=np.vstack([c,c[:1]])
    seg=np.linalg.norm(np.diff(c,axis=0),axis=1); s=np.concatenate([[0],np.cumsum(seg)]); t=np.linspace(0,s[-1],N,endpoint=False)
    return np.column_stack([np.interp(t,s,c[:,0]),np.interp(t,s,c[:,1])])
def make_splice_loft(c,host,half=12.0,step=1.0,N=480):
    xs=np.arange(c-half,c+half+1e-6,step)
    rings=[]
    for x in xs:
        p=splice_profile(x,host,None,below=(host=='T'))
        if hasattr(p,'geoms'): p=max(p.geoms,key=lambda g:g.area)
        rings.append(resample_ring(p,N))
    V=[];F=[]
    for k,(x,r) in enumerate(zip(xs,rings)):
        V.append(np.column_stack([np.full(N,x),r[:,0],r[:,1]]))
    V=np.vstack(V)
    for k in range(len(xs)-1):
        a=k*N; b=(k+1)*N
        for i in range(N):
            j=(i+1)%N
            F.append([a+i,a+j,b+j]); F.append([a+i,b+j,b+i])
    # caps
    from trimesh.creation import triangulate_polygon
    for k,flip in [(0,True),(len(xs)-1,False)]:
        poly=Polygon(rings[k]); v2,f2=triangulate_polygon(poly,engine='earcut')
        # map cap vertices to ring indices
        idx=[]
        ring=rings[k]
        for p in v2:
            d=np.linalg.norm(ring-p,axis=1); j=np.argmin(d); assert d[j]<1e-6; idx.append(k*N+j)
        idx=np.array(idx); f=idx[f2]
        F.extend((f[:,::-1] if flip else f).tolist())
    m=trimesh.Trimesh(V,np.array(F),process=True)
    if m.volume<0: m.invert()
    return m

def make_splice_sweep(c,host,half=12.0,step=0.5):
    xs=np.arange(c-half,c+half+1e-6,step)
    profs=[]
    for x in xs:
        p=splice_profile(x,host,None,below=(host=='T'))
        if hasattr(p,'geoms'): p=max(p.geoms,key=lambda g:g.area)
        profs.append(p)
    cen=np.array([[p.centroid.x,p.centroid.y] for p in profs])
    # smooth path: quadratic fit of centroid shift vs x
    cy=np.polyfit(xs-c,cen[:,0],2); cz=np.polyfit(xs-c,cen[:,1],2)
    off=lambda x: np.array([np.polyval(cy,x-c),np.polyval(cz,x-c)])
    o0=off(c)
    Q=None
    for x,p in zip(xs,profs):
        d=off(x)-o0
        sp=shapely.affinity.translate(p,-d[0],-d[1])
        Q=sp if Q is None else Q.intersection(sp)
    Q=Q.buffer(-0.05).buffer(0.05)
    if hasattr(Q,'geoms'): Q=max(Q.geoms,key=lambda g:g.area)
    Q=Q.simplify(0.02)
    M=cs_from(Q).extrude(2*half,n_divisions=int(2*half/step))
    M=M.transform([[0,0,1,c-half],[1,0,0,0],[0,1,0,0]])
    def w(v):
        d=off(v[0])-o0; return (v[0],v[1]+d[0],v[2]+d[1])
    M=M.warp(w)
    return totm(M), Q.area
