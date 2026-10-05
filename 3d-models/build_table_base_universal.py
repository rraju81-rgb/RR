import trimesh, numpy as np, json
exec(open('rack_base.py').read().split("if __name__ == '__main__':")[0])
H_UP, REAR, TOE = 140.0, 108.0, 8.0          # sized for the 5-card rack; back rests stay below the 3-card rack's top
rep = {}
bases = {}
for N in (3, 5):
    R, Bm, lift, LP = assemble(N, rear=REAR, toe=TOE, H_UP=H_UP)
    r = analyse(R, Bm, lift, N, LP)
    bases[N] = Bm
    r['back_rest_top_below_rack_top_mm'] = round(R.bounds[1, 2] - Bm.bounds[1, 2], 1)
    rep[f'{N}card_on_universal_base'] = r; print(N, json.dumps(r))
    np.save(f'_ub_{N}.npy', [lift, LP]); R.export(f'_ub_rack_{N}.stl')
# the two bases must be the same part
d = trimesh.boolean.difference([bases[3], bases[5]], engine='manifold').volume + trimesh.boolean.difference([bases[5], bases[3]], engine='manifold').volume
print('base for 3 vs base for 5 differ by', round(d, 3), 'mm3')
rep['base_identical_for_both_racks_mm3_diff'] = round(d, 3)
B = bases[5]; B.export('_ub_base.stl')
Bp = B.copy(); Bp.apply_translation(-Bp.bounds[0]); Bp.export('table_base_universal.stl')
print('universal base', np.round(Bp.extents, 1).tolist(), Bp.is_watertight, len(Bp.split()), round(Bp.volume*1.24e-3), 'g')
# gap check: the region the user marked (between back rest and gusset, near the floor) must be solid
for xa in (X0 + 5, X1 - 5):
    s = B.section(plane_origin=[xa, 0, 0], plane_normal=[1, 0, 0])
    print('x', xa, 'section loops', len(s.discrete), '(1 = one solid outline, no gap)')
json.dump(rep, open('universal_base_report.json', 'w'), indent=1)
