import trimesh, numpy as np, json
from trimesh.creation import box
I = lambda a, b: trimesh.boolean.intersection([a, b], engine='manifold').volume
rep = {}
for name, f, L in [('plain', 'rack_6ledge_130_3mmholes.stl', 130.0), ('hinged', 'rack_v2_hinged_134.stl', 134.0)]:
    r = trimesh.load(f)
    if name == 'hinged': r = trimesh.boolean.union(r.split(), engine='manifold')
    ybot = r.bounds[0, 1]
    fl = trimesh.load(f'foot_left_{name}.stl'); fl.apply_translation([0, ybot - 4.0, 0])
    fr = trimesh.load(f'foot_right_{name}.stl'); fr.apply_translation([0, ybot - 4.0, 0])
    feet = trimesh.util.concatenate([fl, fr])
    d = {}
    d['overlap_seated'] = round(I(r, feet), 3)
    d['touches_floor'] = I(r.copy().apply_translation([0, -0.05, 0]) or r, feet) if False else round(I(trimesh.Trimesh(r.vertices + [0, -0.05, 0], r.faces), feet), 3)
    def play(vec):
        for s in np.arange(0.05, 3.0, 0.05):
            if I(trimesh.Trimesh(r.vertices + np.array(vec)*s, r.faces), feet) > 0.01: return round(float(s), 2)
        return '>3 (free!)'
    d['play_mm'] = {n: play(vv) for n, vv in [('+x', [1,0,0]), ('-x', [-1,0,0]), ('+z', [0,0,1]), ('-z', [0,0,-1])]}
    # lift-out: raised 16 mm the rack is clear of both feet, and the path in between is a straight lift
    d['clear_after_lift'] = round(I(trimesh.Trimesh(r.vertices + [0, 16.5, 0], r.faces), feet), 3)
    # bottom card slides in from the tip side along the groove of tier 0: path from x=60 to x=L+60
    path = box(bounds=[[60, 3.05, 3.8], [L + 60, 3.05 + 165, 4.9]])   # 1.1 mm slab: fits the 1.3 mm groove behind the corner supports
    d['bottom_card_slide_path_blocked_by_feet_mm3'] = round(I(path, feet), 3)
    d['bottom_card_slide_path_blocked_by_rack_mm3'] = round(I(path, r), 3)
    # and a card fully home in the groove (x 25.5..L) is clear of the left foot
    d['left_foot_vs_card'] = round(I(box(bounds=[[25.5, 3.05, 3.75], [L, 168, 5.45]]), fl), 3)
    # stability: rack (solid PLA) + 6 cards (30 g car 50 mm up 12 mm proud, 10 g card at centre), feet on the table
    rho = 1.24e-3; mr = r.volume*rho; mf = feet.volume*rho
    pts = [(mr, *r.center_mass), (mf, *feet.center_mass)]
    for k in range(6):
        zg = 3.7 + 4.6*k + 0.5; y0 = 55*k + 3
        pts += [(30, 80, y0 + 50, zg + 12), (10, 80, y0 + 82, zg)]
    M = sum(p[0] for p in pts); com = np.array([sum(p[0]*np.array(p[1:]) for p in pts)])[0] / M
    ytab = ybot - 4.0; h = com[1] - ytab
    zb, zf = feet.bounds[0, 2], feet.bounds[1, 2]
    d['stability_full'] = dict(mass_g=round(M), com_height=round(h, 1), com_z=round(com[2], 1),
                               tip_back_deg=round(np.degrees(np.arctan2(com[2] - zb, h)), 1),
                               tip_front_deg=round(np.degrees(np.arctan2(zf - com[2], h)), 1),
                               tip_side_deg=round(np.degrees(np.arctan2(min(com[0] - feet.bounds[0, 0], feet.bounds[1, 0] - com[0]), h)), 1))
    rep[name] = d
print(json.dumps(rep, indent=1, default=float)); json.dump(rep, open('feet_report.json', 'w'), indent=1, default=float)
