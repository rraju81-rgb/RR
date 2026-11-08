import sys,numpy as np,trimesh
from render import render
d=np.load(sys.argv[1]); m=trimesh.Trimesh(d['v'],d['f'],process=False); o=sys.argv[2]
render(m,[-1,0.25,-0.35],[0,0,1],path=o+'_side34.png',res=900)   # from +x side, front-right like user's view
render(m,[0.7,0.7,-0.4],[0,0,1],path=o+'_front34.png',res=900)
render(m,[0,1,0],[0,0,1],path=o+'_front.png',res=900)
render(m,[0,0,1],[0,1,0],path=o+'_bottom.png',res=900)
render(m,[-0.6,-0.6,-0.5],[0,0,1],path=o+'_rear34.png',res=900)
