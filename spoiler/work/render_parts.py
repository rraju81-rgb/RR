import pyvista as pv, trimesh, numpy as np, glob, json
pv.OFF_SCREEN=True
rep=json.load(open('print/parts_report.json'))
def pvm(m): return pv.wrap(m)
cols={'TOP':'#4a6fa5','BOTTOM':'#c8553d','SPLICE_TOP':'#f2c14e','SPLICE_BOTTOM':'#5fad56'}
# exploded assembly
p=pv.Plotter(off_screen=True,window_size=(1800,900))
for r in rep:
    n=r['name']; m=trimesh.load(f'print/assembled_ref/{n}.stl')
    k='SPLICE_TOP' if n.startswith('SPLICE_TOP') else 'SPLICE_BOTTOM' if n.startswith('SPLICE_BOTTOM') else n.split('_')[0]
    cx=m.centroid[0]; dx=np.sign(cx)*min(abs(cx),500)*0.12
    dy={'TOP':60,'BOTTOM':-60,'SPLICE_TOP':0,'SPLICE_BOTTOM':-30}[k]
    m.apply_translation([dx,dy,0])
    p.add_mesh(pvm(m),color=cols[k],smooth_shading=True,specular=0.3)
p.camera_position=[(700,900,-1100),(0,0,110),(0,1,0)]
p.add_text('Exploded: TOP sections (blue), BOTTOM sections (red), TOP splices (yellow), BOTTOM splices (green)',font_size=11)
p.screenshot('work/exploded.png'); p.close()
# bed layouts
names=[r['name'] for r in rep if r['name'] in ('TOP_R1','TOP_R2','TOP_R3','BOTTOM_C','BOTTOM_R2','SPLICE_TOP_x+217')]
p=pv.Plotter(off_screen=True,shape=(2,3),window_size=(1800,1200))
for i,n in enumerate(names):
    p.subplot(i//3,i%3); m=trimesh.load(f'print/{n}.stl')
    k='SPLICE_TOP' if n.startswith('SPLICE_TOP') else n.split('_')[0]
    p.add_mesh(pvm(m),color=cols[k],smooth_shading=True)
    bed=pv.Plane(center=(128,128,-0.5),i_size=256,j_size=256); p.add_mesh(bed,color='#333333',opacity=0.9)
    p.add_mesh(pv.Box((0,256,0,256,0,256)).extract_all_edges(),color='grey',line_width=1)
    p.camera_position=[(560,-330,380),(128,128,100),(0,0,1)]
    p.add_text(n+'  (%.0f x %.0f x %.0f mm)'%tuple(m.extents),font_size=11)
p.screenshot('work/bed_layouts.png'); p.close()
