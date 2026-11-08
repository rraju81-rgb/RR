import numpy as np, trimesh
from PIL import Image
def render(mesh, view_dir, up, res=700, path=None, extra=None):
    # orthographic raster of triangle centroids splatted with lambert shading (sample dense points)
    d=np.array(view_dir,float); d/=np.linalg.norm(d)
    u=np.array(up,float); u-=d*u.dot(d); u/=np.linalg.norm(u)
    r=np.cross(u,d)
    pts,fi=trimesh.sample.sample_surface_even(mesh, 1500000) if False else trimesh.sample.sample_surface(mesh, 2500000)
    n=mesh.face_normals[fi]
    x=pts@r; y=pts@u; z=pts@d
    lo=np.array([x.min(),y.min()]); span=max(x.max()-x.min(), y.max()-y.min())*1.05
    px=((x-lo[0])/span*res).astype(int); py=(res-1-((y-lo[1])/span*res)).astype(int)
    ok=(px>=0)&(px<res)&(py>=0)&(py<res)
    shade=np.clip(-(n@d),0,1)*0.8+0.15
    order=np.argsort(-z[ok])  # far first, near last overwrite
    img=np.full((res,res),60,np.uint8)
    idx=np.where(ok)[0][order]
    img[py[idx],px[idx]]=(shade[idx]*255).astype(np.uint8)
    im=Image.fromarray(img)
    if path: im.save(path)
    return im
