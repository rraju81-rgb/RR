import numpy as np
d=np.load('raw.npz'); v,f=d['v'].copy(),d['f']
h=np.load('hm.npz'); top=h['top']; x0,y0,res=h['x0'],h['y0'],h['res']
ys=[];mids=[]
for y in np.arange(55,172,2.0):
    r=int((y-y0)/res); cols=np.where(top[r]>=0)[0]; xs=x0+cols*res
    ys.append(y); mids.append((xs.min()+xs.max())/2)
a,b=np.polyfit(ys,mids,1); ang=np.arctan(a); print('slope',a,'deg',np.degrees(ang))
c=np.array([np.mean(mids),np.mean(ys)])
R=np.array([[np.cos(ang),-np.sin(ang)],[np.sin(ang),np.cos(ang)]])  # rotate so x mid const
xy=(v[:,:2]-c)@R.T
# check
v2=v.copy(); v2[:,:2]=xy
print(v2.min(0),v2.max(0))
np.savez('al.npz',v=v2,f=f)
