import re, numpy as np, sys
src=sys.argv[1]; out=sys.argv[2]
t=open(src).read()
v=np.array(re.findall(r'<vertex x="([^"]+)" y="([^"]+)" z="([^"]+)"',t),dtype=np.float64)
f=np.array(re.findall(r'<triangle v1="(\d+)" v2="(\d+)" v3="(\d+)"',t),dtype=np.int64)
m=[5.629981,-2.21628463,0.172160178,0.925777008,3.00276241,3.19922457,-2.03285508,-4.77050828,1.93374684,122.70952,129.53599,23.4770537]
M=np.array(m[:9]).reshape(3,3); T=np.array(m[9:])
w=v@M+T
np.savez(out,v=w,f=f)
print(v.shape,f.shape,w.min(0),w.max(0))
