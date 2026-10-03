import numpy as np, pyvista as pv, sys
pv.OFF_SCREEN=True
sys.path.insert(0,'.')
D=np.load('faces.npy',allow_pickle=True).item()
t=open('fe/mech.inp').read(); nsplitN=int(t[t.index('TYPE=C3D10,ELSET=EBOTTOM'):].split('\n')[1].split(',')[1])-1
def surf(part,field,ids,off):
    d=D[part]; F=d['f']; N=d['N']
    val=np.full(len(N),np.nan); m=(ids>off)&(ids<=off+len(N)); val[ids[m]-1-off]=field[m]
    faces=np.hstack([np.full((len(F),1),3),F]).ravel()
    s=pv.PolyData(N,faces); s['v']=val; return s
def render(fn,field,ids,title,clim,cams,mirror=True,u=None,scale=0):
    p=pv.Plotter(off_screen=True,shape=(1,len(cams)),window_size=(900*len(cams),650),border=False)
    for i,cam in enumerate(cams):
        p.subplot(0,i)
        for part,off in [('TOP',0),('BOTTOM',nsplitN)]:
            s=surf(part,field,ids,off)
            p.add_mesh(s,scalars='v',clim=clim,cmap='turbo',show_scalar_bar=(i==0 and part=='TOP'),scalar_bar_args=dict(title=title,vertical=False,width=0.6,position_x=0.2,position_y=0.02),smooth_shading=True)
            if mirror:
                sm=s.copy(); sm.points[:,0]*=-1; p.add_mesh(sm,color='lightgrey',opacity=1.0,smooth_shading=True)
        p.camera_position=cam; p.add_text(['view %d'%(i+1)][0],font_size=9)
    p.screenshot(fn); p.close()
