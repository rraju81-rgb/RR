import numpy as np
def read_frd(fn):
    """returns list of (name, step, dict node->values array) for DISP and STRESS blocks; also mode eigen values"""
    res=[]; cur=None; nodes=None
    with open(fn) as f:
        for line in f:
            if line.startswith('    1PSTEP'): step=int(line.split()[2]) if len(line.split())>2 else None
            if line.startswith(' -4'):
                name=line.split()[1]; cur=dict(name=name,ids=[],vals=[]); continue
            if cur is not None:
                if line.startswith(' -1'):
                    s=line[3:]; nid=int(s[:10]); v=[float(s[10+12*i:22+12*i]) for i in range((len(s.rstrip())-10)//12)]
                    cur['ids'].append(nid); cur['vals'].append(v)
                elif line.startswith(' -3'):
                    cur['ids']=np.array(cur['ids']); cur['vals']=np.array(cur['vals']); res.append(cur); cur=None
    return res
