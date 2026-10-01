"""QA suite for the side rack v3 (frame + swing, bolted hinges). python3 side3_test.py [N ...]  -> side3/qa_N.json"""
import sys, json
import numpy as np
import manifold3d as m3d
import side3_cad as C
import side3_print as PR
from foldout_cad import rot_about

PHI_MAX = 90


def to_manifold(mesh):
    return m3d.Manifold(m3d.Mesh(vert_properties=np.asarray(mesh.vertices, dtype=np.float32), tri_verts=np.asarray(mesh.faces, dtype=np.uint32)))


def closure(R, P):
    worst = 0.0
    for phi in range(0, PHI_MAX + 1, 5):
        TH, TF = rot_about(phi, 0, 0), rot_about(phi, R.h0, -R.D)
        tr = C.pose_transforms(R, P, phi)
        for j in range(R.N):
            J1 = np.array([0, R.s[j], 0, 1.0]); J2 = np.array([0, R.s[j] + R.h0, -R.D, 1.0])
            T = tr[f"arm{j}_R"]
            worst = max(worst, np.linalg.norm((T @ J1 - TH @ J1)[:3]), np.linalg.norm((T @ J2 - TF @ J2)[:3]))
    return worst


def interference(R, P, step=3, search=2.0):
    names = [n for n, d in P.items() if not d.get("hardware")] + [n for n, d in P.items() if d.get("hardware")]
    manis = {n: to_manifold(P[n]["mesh"]) for n in names}
    grp = {n: P[n]["group"] for n in names}
    res = dict(bad=[], min_gap={}, poses=0)
    phis = list(range(0, PHI_MAX + 1, step))
    if PHI_MAX not in phis: phis.append(PHI_MAX)
    for phi in phis:
        tr = C.pose_transforms(R, P, phi)
        pm, bb = {}, {}
        for n in names:
            T = tr[n]
            pm[n] = manis[n].transform(np.asarray(T[:3, :4], dtype=np.float64))
            v = P[n]["mesh"].vertices @ T[:3, :3].T + T[:3, 3]
            bb[n] = (v.min(0), v.max(0))
        for tag, sg in (("R", 1), ("L", -1)):
            rm = C.spring_mesh(R, phi, sg)
            pm["rod_" + tag] = to_manifold(rm); bb["rod_" + tag] = (rm.vertices.min(0), rm.vertices.max(0)); grp["rod_" + tag] = "rod"
        res["poses"] += 1
        allnames = names + ["rod_R", "rod_L"]
        for a in range(len(allnames)):
            for b in range(a + 1, len(allnames)):
                na, nb = allnames[a], allnames[b]
                if grp[na] == grp[nb] and phi != 0: continue
                if grp[na] == "fixed" and grp[nb] == "fixed": continue
                (la, ha), (lb, hb) = bb[na], bb[nb]
                if np.any(la > hb + search) or np.any(lb > ha + search): continue
                vol = (pm[na] ^ pm[nb]).volume()
                gap = 0.0 if vol > 1e-6 else pm[na].min_gap(pm[nb], search)
                key = tuple(sorted((na, nb)))
                if vol > 1e-3: res["bad"].append((phi, na, nb, round(vol, 3)))
                if gap < res["min_gap"].get(key, (1e9, 0))[0]: res["min_gap"][key] = (gap, phi)
    return res


def masses(R, P, card_g=40.0, rho=1.27e-3):
    hw_mass = {"dowel": 3.0, "stud_R": 4.5, "stud_L": 4.5}          # g, hardware riding on the swing
    m = {}
    for n, d in P.items():
        if d["group"] == "fixed":
            continue
        if n.startswith("card"):
            j = int(n[4:]); m[n] = (card_g, np.array([0, R.yb[j] + C.CARD_H * 0.4, R.zr[j] + 6.0]))
        elif d.get("hardware"):
            m[n] = (hw_mass.get(n, 0.0), np.asarray(d["mesh"].center_mass, dtype=float))
        else:
            m[n] = (d["mesh"].volume * rho, np.asarray(d["mesh"].center_mass, dtype=float))
    return m


def torque_curve(R, P, ms):
    g = 9.81e-3
    phis = np.arange(0, 91.01, 0.5)
    U = []
    for p in phis:
        tr = C.pose_transforms(R, P, p)
        U.append(sum(mass * g * (tr[n] @ np.append(com, 1.0))[1] for n, (mass, com) in ms.items()))
    return phis, np.array(U), -np.gradient(np.array(U), np.radians(phis))


def spring_fit(R, phis, tau):
    A, d = R.a_sp, R.d_sp
    ph = np.radians(phis)
    l = np.sqrt(A * A + d * d - 2 * A * d * np.cos(ph))
    geo = 2 * A * d * np.sin(ph)
    Xm = np.column_stack([geo / l, geo])
    sol, *_ = np.linalg.lstsq(Xm[1:], tau[1:], rcond=None)
    resid = tau - Xm @ sol
    return dict(c0_N=float(sol[0]), k_N_per_mm=float(sol[1]), l_min=float(l.min()), l_max=float(l.max()),
                force_closed_N_each=float(sol[0] + sol[1] * l.min()), force_open_N_each=float(sol[0] + sol[1] * l.max()), resid_max_Nm=float(np.abs(resid).max() * 1e-3)), resid


def i_eff_table(R, P, ms):
    grid = np.linspace(0, 90, 91)
    out = []
    for phi in grid:
        T0, T1 = C.pose_transforms(R, P, phi), C.pose_transforms(R, P, phi + np.degrees(1e-3))
        k = 0.0
        for n, (mass, com) in ms.items():
            a = (T0[n] @ np.append(com, 1))[:3]; b = (T1[n] @ np.append(com, 1))[:3]
            k += 0.5 * mass * 1e-3 * (np.linalg.norm((b - a) / 1e-3) * 1e-3) ** 2
        out.append(2 * k)
    return grid, np.array(out)


def swing_sim(R, grid, Ie, phis, torque_nmm, friction_nmm, phi0, dt=1e-3):
    tr = lambda deg: np.interp(deg, phis, torque_nmm) * 1e-3
    fr = friction_nmm * 1e-3
    phi, w, t, vmax = np.radians(phi0), 0.0, 0.0, 0.0
    while t < 20:
        deg = np.degrees(phi); net = tr(deg)
        if w == 0.0 and abs(net) <= fr: break
        a = (net - np.sign(w if w != 0 else net) * fr) / np.interp(deg, grid, Ie)
        w_new = w + a * dt
        if w != 0 and np.sign(w_new) != np.sign(w): w_new = 0.0
        w = w_new; phi += w * dt
        vmax = max(vmax, abs(w) * R.Lb * 1e-3); t += dt
        if phi >= np.radians(90) or phi <= 0: break
    return float(np.degrees(phi)), t, float(vmax)


def structural(R, P, ms, card_g=40.0):
    """PETG allowables: 22 MPa in-layer, 10 MPa across layers. Handling load 10 N pushing a card in its plane."""
    out = {}
    F_hand = 10.0
    per_pin = F_hand / 2.0
    lever = (C.X_B0 - 0.0) - (C.X_A0 + C.X_A1) / 2.0                    # from bar face to arm mid-plane
    M = per_pin * lever
    sig = M / (np.pi * C.PIN_D ** 3 / 32)
    out["arm_pin_bending_MPa_at_10N_handling"] = round(sig, 2); out["arm_pin_SF_across_layers"] = round(10.0 / sig, 2)
    bear = per_pin / (C.PIN_D * (C.X_A1 - C.X_A0))
    out["arm_hole_bearing_MPa"] = round(bear, 2); out["arm_hole_bearing_SF"] = round(22.0 / bear, 1)
    W = sum(m for n, (m, c) in ms.items()) * 9.81e-3
    out["moving_weight_N"] = round(W, 2)
    F_h = max(W, F_hand * R.N) * 1.0
    bolt_bear = F_h / 2.0 / (4.0 * (C.X_B1 - C.X_B0))                    # hinge bolt in the bar, 2 hinges per side x 2 sides
    out["hinge_bearing_MPa_at_max(weight,10N per card)"] = round(bolt_bear, 2); out["hinge_bearing_SF"] = round(22.0 / bolt_bear, 1)
    out["hinge_bolt_shear_SF(A2-70)"] = round(270.0 / (F_h / 4.0 / (np.pi * 4.0 ** 2 / 4.0)), 0)
    # cheek bending: bolt reaction at 20 mm from the plate, wall 6 thick x 54 long
    Mw = (F_h / 2.0) * 25.0
    Z = (54.0 * C.X_P1 * 0 + 54.0 * 6.0 ** 2 / 6.0)
    out["cheek_wall_bending_MPa"] = round(Mw / (54.0 * 6.0 ** 2 / 6.0) * 0 + (F_h / 2.0 * 0.0), 3) if False else round((F_h / 2.0 * 25.0) / (54.0 * 6.0 ** 2 / 6.0), 3)
    return out


def tolerance(R, trials=20000, sigma=0.10, seed=1):
    rng = np.random.default_rng(seed)
    rad = (C.HOLE_D - C.PIN_D) / 2.0
    # pin position error + hole position error (both ~ sigma per axis) and diameter error; arm centre distance error between its two pins
    dpin = rng.normal(0, sigma, (trials, 2, R.N)); dhole = rng.normal(0, sigma, (trials, 2, R.N))
    dia = rng.normal(0.0, 0.08, (trials, R.N))                           # pin swell / hole shrink
    off = np.linalg.norm(dpin - dhole, axis=2)                            # centre offset at each of the two joints
    clearance = rad + dia / 2.0 - off.max(1, keepdims=True) * 0.5          # remaining radial play (two joints share the offset)
    # arm length error between its two joints must be absorbed by the two clearances
    return dict(p_bind_pin_in_arm=float((clearance.min(1) <= 0).mean()), min_play_p1_mm=float(np.percentile(clearance.min(1), 1)), radial_clearance=rad)


def run(N):
    R, P = C.build(N)
    out = dict(N=N, open_reach=round(R.Lb, 1), post_height=round(R.Lp, 1), printed_parts=3, designs=2)
    out["closure_err_mm"] = closure(R, P)
    res = interference(R, P)
    out["poses_tested"] = res["poses"]
    out["overlaps"] = [b for b in res["bad"]][:10]
    out["n_overlaps"] = len(res["bad"])
    gaps = sorted(((g, k, ph) for k, (g, ph) in res["min_gap"].items()), key=lambda x: x[0])
    out["tightest_pairs"] = [(round(g, 2), k[0], k[1], ph) for g, k, ph in gaps if g > 0][:10]
    out["touching_pairs_at_some_pose"] = [(k[0], k[1], ph) for g, k, ph in gaps if g <= 0][:12]
    out["print"] = {nm: PR.analyse(m) for nm, m in (("frame", C.print_frame(R)), ("swing", C.print_swing(R, 1)))}
    ms = masses(R, P)
    phis, U, tau = torque_curve(R, P, ms)
    out["mass_moving_g"] = round(float(sum(m for m, _ in ms.values())), 1)
    out["tau_max_Nm"] = round(float(tau.max() * 1e-3), 4)
    grid, Ie = i_eff_table(R, P, ms)
    out["unbraked"] = {}
    for f in (0, 50, 100):
        above = [p for p in phis if np.interp(p, phis, tau) * 1e-3 > f * 1e-3]
        hold = float(above[0]) if above else 90.0
        ang, tt, v = swing_sim(R, grid, Ie, phis, tau, f, max(hold + 0.5, 1.0)) if above else (90.0, 0.0, 0.0)
        out["unbraked"][f] = dict(hold_deg=round(hold, 1), impact_m_s=round(v, 2))
    sp, resid = spring_fit(R, phis, tau)
    out["spring"] = {k: round(v, 4) for k, v in sp.items()}
    out["with_spring"] = {}
    for start in (10.0, 45.0, 80.0):
        ang, tt, v = swing_sim(R, grid, Ie, phis, resid, 1.25 * sp["resid_max_Nm"] * 1e3, start)
        out["with_spring"][f"released_at_{int(start)}deg"] = dict(rests_at_deg=round(ang, 1), max_free_end_speed_m_s=round(v, 3))
    out["spring_post_height"], out["spring_anchor_height"] = round(R.a_sp, 1), round(R.d_sp, 1)
    out["structural"] = structural(R, P, ms)
    out["tolerance"] = tolerance(R)
    out["filament_g"] = {"frame": round(C.print_frame(R).volume * 1.27e-3, 0), "swing_each": round(C.print_swing(R, 1).volume * 1.27e-3, 0)}
    out["print_sizes_mm"] = {"frame": [round(float(v), 1) for v in C.print_frame(R).extents], "swing": [round(float(v), 1) for v in C.print_swing(R, 1).extents]}
    return out


if __name__ == "__main__":
    for N in [int(a) for a in sys.argv[1:]] or [3]:
        r = run(N)
        json.dump(r, open(f"side3/qa_{N}.json", "w"), indent=1, default=str)
        print(N, "closure", r["closure_err_mm"], "overlaps", r["n_overlaps"], r["overlaps"][:6]); print(" touching", r["touching_pairs_at_some_pose"]); print(" tightest", r["tightest_pairs"][:5])
