import os, json, numpy as np, trimesh
os.environ.setdefault('KS_N', '3')
import build_table_easel_kickstand_v11 as E
TAG = E.TAG; cfg = json.load(open(f'_ks11_{TAG}.json'))
P = trimesh.load(f'_ks11_{TAG}_panel.stl'); L = trimesh.load(f'_ks11_{TAG}_leg.stl')
mv = lambda m, M: trimesh.Trimesh(trimesh.transform_points(m.vertices, M), m.faces)
r = dict(N=E.N, hinge_y=E.YH, lean_deg=E.ALPHA, open_deg=E.PSI)
Q = trimesh.load(f'_ks11_{TAG}_pin.stl')
r['assembled_overlap_mm3'] = dict(panel_leg=round(E.I(P, L), 4), panel_pin=round(E.I(P, Q), 4), leg_pin=round(E.I(L, Q), 4))
r['pin_hole_radial_clearance_mm'] = E.R_HOLE - E.R_PIN
r['snap'] = dict(barb_dia=2*E.BARB['r'], hole_dia=2*E.R_HOLE, prong_deflection_mm=round(E.BARB['r'] - E.R_HOLE, 2), slot_mm=E.BARB['slot'])
# captured: the leg can't slide either way along the pin
slide = lambda a, d: round(E.I(E.U(P, Q), mv(L, trimesh.transformations.translation_matrix([d, 0, 0]) @ E.rot(a))), 2)
r['leg_slide_overlap_mm3'] = {f'{a}deg': dict(minus_1mm=slide(a, -1), plus_1mm=slide(a, 1)) for a in (0, 35)}
P = E.U(P, Q)   # the pin rides with the panel for the sweep
# sweep: free from 0 to 35, blocked beyond (stop), blocked below 0 (folded against panel)
sweep = {a: round(E.I(P, mv(L, E.rot(a))), 3) for a in [0, 5, 10, 15, 20, 25, 30, 34, 34.8, 36, 38, -2]}
r['sweep_overlap_mm3'] = sweep
r['stop_deg'] = cfg['stop']
# stability, deployed at lean ALPHA with leg at 35 deg
T = E.tilt(E.ALPHA, P); Pw = mv(P, T); Lw = mv(L, T @ E.rot(E.PSI))
r['foot_Z_min'] = round(Lw.bounds[0][2], 3); r['panel_Z_min'] = round(Pw.bounds[0][2], 3)
pts = [(Pw.volume*1.24e-3*0.75, *Pw.center_mass[1:]), (Lw.volume*1.24e-3*0.75, *Lw.center_mass[1:])]
xs = [(pts[0][0], Pw.center_mass[0]), (pts[1][0], Lw.center_mass[0])]
for k in range(E.N):
    for m, y, z in [(30, 55*k + 53, 3.7 + 4.6*k + 12.5), (10, 55*k + 3 + 82.5, 4.2 + 4.6*k)]:
        p = (T @ np.array([55.5, y, z, 1]))[:3]; pts.append((m, p[1], p[2])); xs.append((m, p[0]))
M = sum(p[0] for p in pts); com = sum(p[0]*np.array(p[1:]) for p in pts)/M
yf = Pw.vertices[Pw.vertices[:, 2] < 0.3][:, 1].min(); yr = Lw.vertices[Lw.vertices[:, 2] < 0.3][:, 1].max()
r.update(mass_stand_g=round(pts[0][0] + pts[1][0]), mass_loaded_g=round(M), footprint_depth_mm=round(yr - yf, 1),
         tip_front_deg=round(np.degrees(np.arctan2(com[0] - yf, com[1])), 1), tip_rear_deg=round(np.degrees(np.arctan2(yr - com[0], com[1])), 1))
from scipy.spatial import ConvexHull
xc = sum(m*x for m, x in xs)/M
G = np.vstack([Pw.vertices[Pw.vertices[:, 2] < 0.3][:, :2], Lw.vertices[Lw.vertices[:, 2] < 0.3][:, :2]]); hull = G[ConvexHull(G).vertices]
c2 = np.array([xc, com[0]]); side = []
for i in range(len(hull)):
    a, b = hull[i], hull[(i + 1) % len(hull)]; e = b - a; dist = abs(e[0]*(c2 - a)[1] - e[1]*(c2 - a)[0])/np.linalg.norm(e)
    if abs(e[1]) > 0.3*np.linalg.norm(e): side.append(dist)   # edges running front-to-back = sideways tipping lines
r['tip_sideways_deg'] = round(np.degrees(np.arctan2(min(side), com[1])), 1) if side else None
# cards slide path clear of leg in deployed pose (cards are on the front face; leg is behind panel)
r['hinge'] = dict(type='3-barrel, separate snap pin (barrels as LiftOffHinge.stl)', barrel_dia_mm=2*E.R_BAR, panel_barrel_len_mm=E.PB, leg_barrel_len_mm=E.LB, pin_dia_mm=2*E.R_PIN, hole_dia_mm=2*E.R_HOLE,
                  axis_height_on_panel_mm=E.YH, axis_height_above_table_mm=round(float((T @ np.array([0, E.YH, E.H['z'], 1]))[2]), 1))
for part in ('panel', 'leg', 'pin'):
    S = trimesh.load(f'table_kickstand_{TAG}_v11_{part}.stl'); r[f'stl_{part}_watertight'] = bool(S.is_watertight); r[f'stl_{part}_bodies'] = len(S.split())
print(json.dumps(r, indent=1)); json.dump(r, open(f'table_kickstand_{TAG}_v11_report.json', 'w'), indent=1)
