import json, numpy as np, trimesh
from scipy.optimize import brentq
from scipy.spatial import ConvexHull
from trimesh.proximity import signed_distance
import build_right_fixed_rack_kickstand as E
cfg = json.load(open('_ks12.json'))
P = trimesh.load('_ks12_rack.stl'); L = trimesh.load('_ks12_leg.stl'); R0 = E.rack()
mv = lambda m, M: trimesh.Trimesh(trimesh.transform_points(m.vertices, M), m.faces)
r = dict(hinge_y=E.YH, lean_deg=E.ALPHA, open_deg=E.PSI)
# the supplied rack is untouched: it lies entirely inside the new rack body, and nothing was cut from it
r['original_rack_volume_cm3'] = round(R0.volume/1000, 2)
r['original_rack_kept_cm3'] = round(E.I(R0, P)/1000, 2)
r['added_hinge_cm3'] = round((P.volume - R0.volume)/1000, 2)
# print-in-place clearance
sh = [np.array(v)*0.45 for v in [(1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1)]]
r['printed_overlap_mm3'] = round(E.I(P, L), 4)
r['shift045_overlap_mm3'] = round(max(E.I(P, L.copy().apply_translation(v)) for v in sh), 4)
pts = L.sample(80000); r['min_print_gap_mm'] = round(float((-signed_distance(P, pts)).min()), 3)
slide = lambda dx: E.I(P, L.copy().apply_translation([dx, 0, 0]))
play = lambda sg: brentq(lambda dx: slide(sg*dx) - 0.05, 0.0, 4.0, xtol=0.02)
r['leg_axial_play_mm'] = dict(toward_bed_end=round(play(-1), 2), toward_rack_barrel=round(play(1), 2))
n, c = L.face_normals, L.triangles_center
r['leg_overhang_over_45deg_mm2'] = round(float(L.area_faces[(n[:, 0] < -0.75) & (c[:, 0] > 0.05)].sum()), 2)
r['sweep_overlap_mm3'] = {a: round(E.I(P, mv(L, E.rot(a))), 3) for a in [0, 5, 10, 15, 20, 25, 30, 34, 34.8, 36, 38, -2]}
r['stop_deg'] = cfg['stop']
# stability, open at 35 deg, 6 cards (30 g car + 10 g card each)
T = E.tilt(E.ALPHA, P); Pw = mv(P, T); Lw = mv(L, T @ E.rot(E.PSI))
r['foot_Z_min'] = round(Lw.bounds[0][2], 3)
pts = [(Pw.volume*1.24e-3*0.75, *Pw.center_mass), (Lw.volume*1.24e-3*0.75, *Lw.center_mass)]
for k in range(6):
    zc = 4.6*k + 4.5
    for m, y, z in [(30, 55*k + 53, zc + 12), (10, 55*k + 3 + 82.5, zc)]:
        p = (T @ np.array([28 + 54, y, z, 1]))[:3]; pts.append((m, *p))
M = sum(p[0] for p in pts); com = sum(p[0]*np.array(p[1:]) for p in pts)/M
yf = Pw.vertices[Pw.vertices[:, 2] < 0.3][:, 1].min(); yr = Lw.vertices[Lw.vertices[:, 2] < 0.3][:, 1].max()
r.update(mass_stand_g=round(pts[0][0] + pts[1][0]), mass_loaded_g=round(M),
         tip_front_deg=round(np.degrees(np.arctan2(com[1] - yf, com[2])), 1), tip_rear_deg=round(np.degrees(np.arctan2(yr - com[1], com[2])), 1))
G = np.vstack([Pw.vertices[Pw.vertices[:, 2] < 0.3][:, :2], Lw.vertices[Lw.vertices[:, 2] < 0.3][:, :2]]); hull = G[ConvexHull(G).vertices]
c2 = com[:2]; side = []
for i in range(len(hull)):
    a, b = hull[i], hull[(i + 1) % len(hull)]; e = b - a
    if abs(e[1]) > 0.3*np.linalg.norm(e): side.append(abs(e[0]*(c2 - a)[1] - e[1]*(c2 - a)[0])/np.linalg.norm(e))
r['tip_sideways_deg'] = round(np.degrees(np.arctan2(min(side), com[2])), 1)
r['standing_W_D_H_mm'] = np.round(trimesh.util.concatenate([Pw, Lw]).extents, 1).tolist()
S = trimesh.load('right_fixed_rack_kickstand_PRINT.stl'); r['stl_watertight'] = bool(S.is_watertight); r['stl_bodies'] = len(S.split())
r['stl_bounds_same_as_original'] = [np.round(S.bounds, 1).tolist(), np.round(trimesh.load(E.SRC).bounds, 1).tolist()]
print(json.dumps(r, indent=1)); json.dump(r, open('right_fixed_rack_kickstand_report.json', 'w'), indent=1)
