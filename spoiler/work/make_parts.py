exec(open('work/build_print.py').read())
from scipy.spatial import ConvexHull
BED=256.0
def best_rot2d(P):
    h=P[ConvexHull(P).vertices]; best=None
    for a in np.radians(np.arange(0,180,0.5)):
        R=np.array([[np.cos(a),-np.sin(a)],[np.sin(a),np.cos(a)]]); p=h@R.T; ext=p.max(0)-p.min(0)
        sc=max(ext)
        if best is None or sc<best[0]: best=(sc,a,ext)
    return best
def place_on_end(m,up_sign):
    """rotate so +x*up_sign becomes +Z, cross-section rotated to minimise footprint, then sit on bed centred."""
    v=m.vertices.copy()
    # map world -> print: Z = up_sign*x ; (X,Y) = rotated (y,z)
    Z=up_sign*v[:,0]; P=v[:,1:3]*np.array([1,up_sign])  # keep right-handed: det check below
    sc,a,ext=best_rot2d(P)
    R=np.array([[np.cos(a),-np.sin(a)],[np.sin(a),np.cos(a)]])
    XY=P@R.T
    out=np.column_stack([XY,Z])
    mm=trimesh.Trimesh(out,m.faces.copy(),process=False)
    if mm.volume<0: mm.invert()
    mm.apply_translation([-(out[:,0].min()+out[:,0].max())/2+BED/2,-(out[:,1].min()+out[:,1].max())/2+BED/2,-out[:,2].min()])
    return mm,sc
def place_flat(m):
    v=m.vertices.copy(); P=v[:,[0,2]]
    sc,a,ext=best_rot2d(P); R=np.array([[np.cos(a),-np.sin(a)],[np.sin(a),np.cos(a)]])
    XY=P@R.T; out=np.column_stack([XY,v[:,1]])
    mm=trimesh.Trimesh(out,m.faces.copy(),process=False)
    if mm.volume<0: mm.invert()
    mm.apply_translation([-(out[:,0].min()+out[:,0].max())/2+BED/2,-(out[:,1].min()+out[:,1].max())/2+BED/2,-out[:,2].min()])
    return mm,sc
report=[]; assembled=[]
def save(name,m_world,placed,kind,note):
    m_world.export(f'print/assembled_ref/{name}.stl'); placed.export(f'print/{name}.stl')
    e=placed.extents
    r=dict(name=name,kind=kind,watertight=bool(placed.is_watertight),bodies=len(placed.split(only_watertight=False)),
           volume_cm3=round(placed.volume/1000,1),mass_g_ASA=round(placed.volume/1000*1.07,0),print_extent_mm=[round(float(x),1) for x in e],
           fits_256=bool(max(e[:2])<=250 and e[2]<=250),note=note)
    report.append(r); print(r)
os.makedirs('print/assembled_ref',exist_ok=True)
# TOP sections
labels=['L3','L2','L1','R1','R2','R3']
for (rng,M),lab in zip(sections(MT,TOP_CUTS,-650,650),labels):
    m=totm(M); centre=(rng[0]+rng[1])/2
    up=1 if centre>0 else -1   # inboard cut face on the bed, outboard end up
    p,_=place_on_end(m,up)
    save(f'TOP_{lab}',m,p,'TOP section','print standing on its inboard cut face')
labelsB=['L2','L1','C','R1','R2']
for (rng,M),lab in zip(sections(MB,BOT_CUTS,-539,539),labelsB):
    m=totm(M); centre=(rng[0]+rng[1])/2
    up=1 if centre>=0 else -1
    p,_=place_on_end(m,up)
    save(f'BOTTOM_{lab}',m,p,'BOTTOM section','print standing on a cut face')
for c in TOP_CUTS:
    m,_=make_splice_sweep(abs(c),'T')
    if c<0:
        m.vertices[:,0]*=-1; m.invert()
    p,_=place_flat(m)
    save(f'SPLICE_TOP_x{c:+d}',m,p,'TOP joint splice','print lying flat (as installed), tree supports under it')
for c in BOT_CUTS:
    m,_=make_splice_sweep(abs(c),'B')
    if c<0:
        m.vertices[:,0]*=-1; m.invert()
    p,_=place_flat(m)
    save(f'SPLICE_BOTTOM_x{c:+d}',m,p,'BOTTOM joint splice','print lying flat (as installed), tree supports under it')
json.dump(report,open('print/parts_report.json','w'),indent=1)
