"""Wheels: tyres, 5 twin-spoke rims, brake discs and calipers for the procedural Polo body."""
import numpy as np, trimesh
from car_body import Z_F, Y_G, S_FA, S_RA, WHEEL_R, WHEEL_W, TRACK

def revolve(profile, n=96):
    """profile: (r, x) points (closed loop not needed, open polyline from axis to axis) revolved about the x axis."""
    P = np.asarray(profile, float); a = np.linspace(0, 2 * np.pi, n, endpoint=False)
    V = []
    for r, x in P:
        V.append(np.column_stack([np.full(n, x), r * np.cos(a), r * np.sin(a)]))
    V = np.vstack(V); F = []
    m = len(P)
    for i in range(m - 1):
        for j in range(n):
            a0 = i * n + j; a1 = i * n + (j + 1) % n; b0 = (i + 1) * n + j; b1 = (i + 1) * n + (j + 1) % n
            F += [[a0, b0, b1], [a0, b1, a1]]
    return trimesh.Trimesh(V, np.array(F), process=True)

def tyre(R=WHEEL_R, W=WHEEL_W, r_rim=203.0):
    """tyre: rounded section revolved; x is the axle direction (centred at 0)"""
    hw = W / 2
    sw = 0.42 * (R - r_rim)                     # shoulder radius
    prof = [(r_rim - 2, -hw + 12), (r_rim + 8, -hw + 2)]
    # sidewall up to shoulder
    for k in np.linspace(0, 1, 10): prof.append((r_rim + 8 + k * (R - sw - r_rim - 8), -hw - 4 * np.sin(np.pi * k)))
    for a in np.linspace(np.pi, np.pi / 2, 8): prof.append((R - sw + sw * np.sin(a - np.pi / 2 + np.pi / 2) * 0 + (R - sw) * 0 + sw * np.sin(np.pi - a) , -hw + sw - sw * np.cos(np.pi - a) * 0 + (-sw * np.cos(a))))
    prof = [(r_rim - 2, -hw + 12), (r_rim + 6, -hw + 1)]
    for k in np.linspace(0, 1, 12):
        prof.append((r_rim + 6 + k * (R - 28 - r_rim - 6), -hw - 6 * np.sin(np.pi * k)))
    for a in np.linspace(0, np.pi / 2, 10):
        prof.append((R - 28 + 28 * np.sin(a), -hw + 28 - 28 * np.cos(a)))
    for k in np.linspace(0, 1, 8)[1:-1]:
        prof.append((R + 1.5 * np.sin(np.pi * k), -hw + 28 + k * (W - 56)))
    for a in np.linspace(np.pi / 2, np.pi, 10):
        prof.append((R - 28 + 28 * np.sin(a), hw - 28 - 28 * np.cos(a)))
    for k in np.linspace(0, 1, 12):
        prof.append((R - 28 - k * (R - 28 - r_rim - 6), hw + 6 * np.sin(np.pi * k)))
    prof += [(r_rim + 6, hw - 1), (r_rim - 2, hw - 12)]
    m = revolve(prof, n=120)
    return m

def rim(r_rim=203.0, W=WHEEL_W, spokes=5):
    """simple 5 twin-spoke alloy: barrel + face disc with cut-outs (manifold3d)"""
    import manifold3d as mf
    hw = W / 2 - 10
    barrel = mf.Manifold.cylinder(2 * hw, r_rim, r_rim, 96).translate([0, 0, -hw]) - mf.Manifold.cylinder(2 * hw + 2, r_rim - 9, r_rim - 9, 96).translate([0, 0, -hw - 1])
    face = mf.Manifold.cylinder(22, r_rim - 4, r_rim - 4, 120).translate([0, 0, hw - 30])
    # windows between twin spokes
    win = []
    for k in range(spokes):
        a = 2 * np.pi * k / spokes + np.pi / spokes
        cs = mf.CrossSection([np.array([[60 * np.cos(a - 0.30), 60 * np.sin(a - 0.30)], [(r_rim - 22) * np.cos(a - 0.38), (r_rim - 22) * np.sin(a - 0.38)],
                                        [(r_rim - 22) * np.cos(a + 0.38), (r_rim - 22) * np.sin(a + 0.38)], [60 * np.cos(a + 0.30), 60 * np.sin(a + 0.30)]])])
        cs = cs.offset(-6, mf.JoinType.Round).offset(6, mf.JoinType.Round)
        win.append(cs.extrude(40).translate([0, 0, hw - 40]))
        a2 = 2 * np.pi * k / spokes
        cs2 = mf.CrossSection([np.array([[95 * np.cos(a2 - 0.05), 95 * np.sin(a2 - 0.05)], [(r_rim - 30) * np.cos(a2 - 0.035), (r_rim - 30) * np.sin(a2 - 0.035)],
                                         [(r_rim - 30) * np.cos(a2 + 0.035), (r_rim - 30) * np.sin(a2 + 0.035)], [95 * np.cos(a2 + 0.05), 95 * np.sin(a2 + 0.05)]])])
        win.append(cs2.extrude(40).translate([0, 0, hw - 40]))
    for w_ in win: face = face - w_
    hub = mf.Manifold.cylinder(30, 68, 60, 64).translate([0, 0, hw - 32])
    nuts = [mf.Manifold.cylinder(14, 9, 9, 24).translate([42 * np.cos(2 * np.pi * k / 5), 42 * np.sin(2 * np.pi * k / 5), hw - 10]) for k in range(5)]
    M = barrel + face + hub
    for n_ in nuts: M = M + n_
    g = M.to_mesh(); m = trimesh.Trimesh(np.asarray(g.vert_properties[:, :3]), np.asarray(g.tri_verts), process=True)
    # cylinder axis is z; rotate to x
    m.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [0, 1, 0]))
    return m

def brake(r=150.0):
    d = trimesh.creation.cylinder(radius=r, height=24, sections=96); d.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [0, 1, 0]))
    cal = trimesh.creation.box(extents=[48, 90, 140]); cal.apply_translation([-30, 0, 0]); cal.apply_transform(trimesh.transformations.rotation_matrix(-0.5, [1, 0, 0]))
    cal.apply_translation([0, 0, r - 30])
    return d, cal

def wheel_set():
    """returns dict of meshes in car coordinates: tyres, rims, discs, calipers"""
    out = {'tyre': [], 'rim': [], 'disc': [], 'caliper': []}
    T = tyre(); Rm = rim(); D, Ca = brake()
    for sa in (S_FA, S_RA):
        z = Z_F + sa; y = Y_G + WHEEL_R - 6.0
        for side in (-1, 1):
            xc = side * (TRACK / 2)
            for key, m in [('tyre', T), ('rim', Rm), ('disc', D), ('caliper', Ca)]:
                mm = m.copy()
                if side < 0: mm.apply_transform(np.diag([-1, 1, 1, 1])); mm.invert()
                off = {'tyre': 0, 'rim': 0, 'disc': -side * 55, 'caliper': -side * 55}[key]
                mm.apply_translation([xc + off, y, z]); out[key].append(mm)
    return {k: trimesh.util.concatenate(v) for k, v in out.items()}

def mirror_mesh():
    """door mirror (left) as an ellipsoid-ish head on a short stalk"""
    head = trimesh.creation.icosphere(subdivisions=4, radius=1.0)
    head.apply_scale([75, 62, 120]); head.vertices[:, 2] = np.where(head.vertices[:, 2] > 0, head.vertices[:, 2] * 0.55, head.vertices[:, 2])
    stalk = trimesh.creation.box(extents=[70, 30, 60]); stalk.apply_translation([45, -40, 10])
    return trimesh.util.concatenate([head, stalk])
