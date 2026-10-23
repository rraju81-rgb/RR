import sys, time, json
sys.path.insert(0, '/home/user/RR/paddle-design')
from pathlib import Path
import numpy as np
from paddle.geometry import build, ELONGATED, HYBRID
from paddle import fea
key, hc, hp, wd, modes = sys.argv[1], float(sys.argv[2]), float(sys.argv[3]), Path(sys.argv[4]), int(sys.argv[5])
wd.mkdir(exist_ok=True)
sp = {'elongated': ELONGATED, 'hybrid': HYBRID}[key]
o = build(sp)
t0 = time.time(); fea.half_model_step(o, wd / 'half.step'); print('step %.1fs' % (time.time() - t0), flush=True)
t0 = time.time(); m = fea.mesh_half_model(wd / 'half.step', hc, hp); print('mesh %.1fs nodes %d elems %s' % (time.time() - t0, len(m.nodes), {k: len(v) for k, v in m.elems.items()}), flush=True)
np.savez_compressed(wd / 'mesh.npz', nodes=m.nodes, **{f'el_{k}': v for k, v in m.elems.items()}, **{f'id_{k}': v for k, v in m.eids.items()})
loads = fea.LOADS if modes == 0 else []
info = fea.write_inp(m, o, wd / 'paddle.inp', loads=loads, modes=modes); print('inp', json.dumps(info), flush=True)
t, mb = fea.run_ccx(wd / 'paddle.inp'); print('ccx %.1fs peak %.0f MB' % (t, mb), flush=True)
if modes:
    print('freqs', fea.read_frequencies(wd / 'paddle.dat'))
else:
    st = fea.read_dat_stresses(wd / 'paddle.dat')[:len(loads)]
    res = {lc.key: fea.evaluate(m, o, s) for lc, s in zip(loads, st)}
    U = fea.read_frd_displacements(wd / 'paddle.frd')
    for lc, u in zip(loads, U):
        res[lc.key]['max_deflection'] = round(float(np.abs(u[:, 2]).max()), 3)
    json.dump(res, open(wd / 'results.json', 'w'), indent=1)
    print(json.dumps(res, indent=1))
print('DONE')
