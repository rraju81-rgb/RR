import trimesh, numpy as np, json
exec(open('easel_v5.py').read().split("if __name__ == '__main__':")[0])
P, B, L = [trimesh.load(f'_easel5_{TAGN}_{n}.stl') for n in ('panel', 'base', 'leg')]
I = lambda a, b: trimesh.boolean.intersection([a, b], engine='manifold').volume
moved = lambda m, M: (lambda c: (c.apply_transform(M), c)[1])(m.copy())
rep = {}
# 1. as printed (folded): separate, with clearance
rep['printed_overlap'] = round(I(P, B) + I(P, L) + I(B, L), 3)
rep['printed_0.45mm_shift_overlap'] = round(max(I(trimesh.Trimesh(m.vertices + d, m.faces), o)
    for m, o in [(B, P), (L, P), (L, B)] for d in np.eye(3)[[0, 1, 2]] * 0.45 for d in [d, -d]), 3)
# 1b. hinge printability: downward-facing area flatter than 45 deg inside the hinge zones (print: x is up, bed at x = X0)
def flat_down(m, H, xa, xb):
    c = m.triangles_center; n = m.face_normals
    zone = (np.hypot(c[:, 1] - H['y'], c[:, 2] - H['z']) < H['R'] + 1) & (c[:, 0] > xa + 0.3) & (c[:, 0] < xb + 1)
    return round(float(m.area_faces[zone & (n[:, 0] < -0.72)].sum()), 2)
rep['hinge_flat_overhang_mm2'] = {'bottom hinge (panel/base)': flat_down(P, H1, X0, X1) + flat_down(B, H1, X0, X1),
                                  'leg hinge (panel/leg)': flat_down(P, H2, X0, X0 + LEG_W) + flat_down(L, H2, X0, X0 + LEG_W)}
# 2. unfolding: leg out first (0..110 deg) with the base folded, then base down (0..85 deg) with the leg at 110
rep['leg_sweep_max_overlap'] = round(max(I(moved(L, rot(H2, a)), P) + I(moved(L, rot(H2, a)), B) for a in range(0, 111, 5)), 3)
Lo = moved(L, rot(H2, 110))
rep['base_sweep_max_overlap'] = round(max(I(moved(B, rot(H1, -a)), P) + I(moved(B, rot(H1, -a)), Lo) for a in range(0, 86, 5)), 3)
# 3. standing at each display angle
grooves = json.load(open(f'_easel5_grooves_{TAGN}.json')); rho = 1.24e-3; st = {}
for alpha, s in grooves:
    T = tilt(alpha); phi = base_angle(alpha); psi, _ = leg_angle(alpha)
    Pw, Bw, Lw = moved(P, T), moved(B, T @ rot(H1, -phi)), moved(L, T @ rot(H2, psi))
    cards = []
    for k in range(N):
        zg = 3.7 + 4.6*k + 0.3
        c = box(bounds=[[1.5, 55*k + 3.2, zg], [109.5, 55*k + 3.2 + 165, zg + 0.5]]); c.apply_transform(T); cards.append(c)
    pts = [(m.volume*rho, *m.center_mass) for m in (Pw, Bw, Lw)]
    for k in range(N):
        for mass, yl, dz in [(30, 55*k + 53, 12.0), (10, 55*k + 85.5, 0.0)]:   # per card
            pts.append((mass, *apply(T, [55, yl, 3.7 + 4.6*k + 0.5 + dz])))
    M = sum(p[0] for p in pts); com = sum(p[0]*np.array(p[1:]) for p in pts) / M
    allw = trimesh.util.concatenate([Pw, Bw, Lw])
    zmin_panel = Pw.bounds[0, 2]
    contact = allw.vertices[allw.vertices[:, 2] < 0.6]               # table contacts
    yf, yr = contact[:, 1].min(), contact[:, 1].max()
    st[alpha] = dict(base_flat_bottom_Z=round(Bw.bounds[0, 2], 2), panel_lowest_Z=round(zmin_panel, 2),
                     overlap_panel_base=round(I(Pw, Bw), 2), overlap_leg_panel=round(I(Lw, Pw), 2), foot_in_groove_overlap=round(I(Lw, Bw), 2),
                     card_clash=round(sum(I(c, allw) for c in cards), 2), height=round(allw.bounds[1, 2], 1), depth=round(allw.extents[1], 1),
                     mass_g=round(M), tip_front_deg=round(np.degrees(np.arctan2(com[1] - yf, com[2])), 1), tip_rear_deg=round(np.degrees(np.arctan2(yr - com[1], com[2])), 1))
rep['display'] = st
print(json.dumps(rep, indent=1)); json.dump(rep, open(f'easel5_report_{TAGN}.json', 'w'), indent=1)
