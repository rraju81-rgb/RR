import os, json, numpy as np, trimesh
os.environ.setdefault('KS_N', '3')
import build_table_easel_kickstand_v6 as E
TAG = E.TAG; cfg = json.load(open(f'_ks_{TAG}.json'))
P = trimesh.load(f'_ks_{TAG}_panel.stl'); L = trimesh.load(f'_ks_{TAG}_leg.stl')
mv = lambda m, M: trimesh.Trimesh(trimesh.transform_points(m.vertices, M), m.faces)
r = dict(N=E.N, hinge_y=E.YH, lean_deg=E.ALPHA, open_deg=E.PSI)
# printed clearance: no overlap, and none when the leg is shifted 0.45 mm in any direction
sh = [np.array(v)*0.45 for v in [(1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1)]]
r['printed_overlap_mm3'] = round(E.I(P, L), 4)
r['shift045_overlap_mm3'] = round(max(E.I(P, L.copy().apply_translation(v)) for v in sh), 4)
# sweep: free from 0 to 35, blocked beyond (stop), blocked below 0 (folded against panel)
sweep = {a: round(E.I(P, mv(L, E.rot(a))), 3) for a in [0, 5, 10, 15, 20, 25, 30, 34, 34.8, 36, 38, -2]}
r['sweep_overlap_mm3'] = sweep
r['stop_deg'] = cfg['stop']
# stability, deployed at lean ALPHA with leg at 35 deg
T = E.tilt(E.ALPHA, P); Pw = mv(P, T); Lw = mv(L, T @ E.rot(E.PSI))
r['foot_Z_min'] = round(Lw.bounds[0][2], 3); r['panel_Z_min'] = round(Pw.bounds[0][2], 3)
pts = [(Pw.volume*1.24e-3*0.75, *Pw.center_mass[1:]), (Lw.volume*1.24e-3*0.75, *Lw.center_mass[1:])]
for k in range(E.N):
    for m, y, z in [(30, 55*k + 53, 3.7 + 4.6*k + 12.5), (10, 55*k + 3 + 82.5, 4.2 + 4.6*k)]:
        p = (T @ np.array([50, y, z, 1]))[:3]; pts.append((m, p[1], p[2]))
M = sum(p[0] for p in pts); com = sum(p[0]*np.array(p[1:]) for p in pts)/M
yf = Pw.vertices[Pw.vertices[:, 2] < 0.3][:, 1].min(); yr = Lw.vertices[Lw.vertices[:, 2] < 0.3][:, 1].max()
r.update(mass_stand_g=round(pts[0][0] + pts[1][0]), mass_loaded_g=round(M), footprint_depth_mm=round(yr - yf, 1),
         tip_front_deg=round(np.degrees(np.arctan2(com[0] - yf, com[1])), 1), tip_rear_deg=round(np.degrees(np.arctan2(yr - com[0], com[1])), 1))
# cards slide path clear of leg in deployed pose (cards are on the front face; leg is behind panel)
r['hinge'] = dict(width_mm=E.HX[1]-E.HX[0], knuckles=3, knuckle_dia_mm=2*E.H['R'], pin_dia_mm=2*E.H['pin'], gap_mm=E.GN,
                  axis_height_on_panel_mm=E.YH, axis_height_above_table_mm=round(float((T @ np.array([0, E.YH, E.H['z'], 1]))[2]), 1))
S = trimesh.load(f'table_kickstand_{TAG}_v6.stl')
r['stl_watertight'] = bool(S.is_watertight); r['stl_bodies'] = len(S.split())
print(json.dumps(r, indent=1)); json.dump(r, open(f'table_kickstand_{TAG}_v6_report.json', 'w'), indent=1)
