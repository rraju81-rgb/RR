"""Tests for the side-mechanism rack (v2). python3 side_test.py [N ...]
1 closure  2 interference + gaps over the whole swing  3 print-in-place clearances
4 tolerance Monte Carlo  5 gravity torque, counterbalance spring fit, swing simulation."""
import sys
import json
import numpy as np
import manifold3d as m3d
import side_cad as C

PHI_MAX = 90          # the open stop sits 0.4 mm away, so the panel really settles at about 90.8 degrees


def to_manifold(mesh):
    return m3d.Manifold(m3d.Mesh(vert_properties=np.asarray(mesh.vertices, dtype=np.float32),
                                 tri_verts=np.asarray(mesh.faces, dtype=np.uint32)))


def closure(R, P):
    worst, worst_dir = 0.0, 0.0
    for phi in range(0, PHI_MAX + 1):
        TH, TF = C.rot_about(phi, 0, 0), C.rot_about(phi, R.h0, -R.D)
        tr = C.pose_transforms(R, P, phi)
        for j in range(R.N):
            J1 = np.array([0, R.s[j], 0, 1.0])
            J2 = np.array([0, R.s[j] + R.h0, -R.D, 1.0])
            T = tr[f"arm{j}_R"]
            worst = max(worst, np.linalg.norm((T @ J1 - TH @ J1)[:3]), np.linalg.norm((T @ J2 - TF @ J2)[:3]))
            worst_dir = max(worst_dir, np.abs(T[:3, :3] - np.eye(3)).max())
    return worst, worst_dir


def interference(R, P, step=2, search=3.0, allpairs_at_zero=True):
    names = [n for n, d in P.items() if not d.get("hardware")] + [n for n, d in P.items() if d.get("hardware")]
    manis = {n: to_manifold(P[n]["mesh"]) for n in names}
    grp = {n: P[n]["group"] for n in names}
    res = dict(bad=[], min_gap={}, gap0={}, poses=0, max_vol=0.0)
    phis = list(range(0, PHI_MAX + 1, step))
    if PHI_MAX not in phis:
        phis.append(PHI_MAX)
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
            pm["rod_" + tag] = to_manifold(rm)
            bb["rod_" + tag] = (rm.vertices.min(0), rm.vertices.max(0))
            grp["rod_" + tag] = "rod"
        res["poses"] += 1
        allnames = names + ["rod_R", "rod_L"]
        for a in range(len(allnames)):
            for b in range(a + 1, len(allnames)):
                na, nb = allnames[a], allnames[b]
                if grp[na] == grp[nb] and phi != 0:
                    continue
                if grp[na] == "fixed" and grp[nb] == "fixed":
                    continue
                (la, ha), (lb, hb) = bb[na], bb[nb]
                if np.any(la > hb + search) or np.any(lb > ha + search):
                    continue
                vol = (pm[na] ^ pm[nb]).volume()
                gap = 0.0 if vol > 1e-6 else pm[na].min_gap(pm[nb], search)
                key = tuple(sorted((na, nb)))
                if vol > 1e-3:
                    res["bad"].append((phi, na, nb, round(vol, 3)))
                    res["max_vol"] = max(res["max_vol"], vol)
                if phi == 0:
                    res["gap0"][key] = gap
                if gap < res["min_gap"].get(key, (1e9, 0))[0]:
                    res["min_gap"][key] = (gap, phi)
    return res


def tolerance_mc(R, trials=20000, sigma=0.10, seed=1):
    clearance = (C.HOLE_D - C.PIN_D) / 2
    rng = np.random.default_rng(seed)
    lens = rng.normal(0, np.sqrt(4) * sigma, size=(trials, R.N)) + rng.normal(0, np.sqrt(2) * sigma, size=(trials, R.N))
    cons = np.median(lens, axis=1, keepdims=True) if R.N > 2 else lens.mean(1, keepdims=True)
    worst = (np.abs(lens - cons) / 2).max(1)
    return float((worst > clearance).mean()), float(np.percentile(worst, 95)), clearance


def masses(R, P, card_g=40.0, rho=1.27e-3):
    m = {}
    for n, d in P.items():
        if d["group"] == "fixed" or d.get("hardware"):
            continue
        if n.startswith("card"):
            j = int(n[4:])
            m[n] = (card_g, np.array([0, R.yb[j] + C.CARD_H * 0.4, R.zr[j] + 6.0]))
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
                force_closed_N_each=float(sol[0] + sol[1] * l.min()), force_open_N_each=float(sol[0] + sol[1] * l.max()),
                resid_max_Nm=float(np.abs(resid).max() * 1e-3)), resid


def i_eff_table(R, P, ms):
    grid = np.linspace(0, 90, 91)
    out = []
    for phi in grid:
        T0, T1 = C.pose_transforms(R, P, phi), C.pose_transforms(R, P, phi + np.degrees(1e-3))
        k = 0.0
        for n, (mass, com) in ms.items():
            a = (T0[n] @ np.append(com, 1))[:3]
            b = (T1[n] @ np.append(com, 1))[:3]
            k += 0.5 * mass * 1e-3 * (np.linalg.norm((b - a) / 1e-3) * 1e-3) ** 2
        out.append(2 * k)
    return grid, np.array(out)


def swing(R, grid, Ie, phis, torque_nmm, friction_nmm, phi0, dt=1e-3):
    tr = lambda deg: np.interp(deg, phis, torque_nmm) * 1e-3
    fr = friction_nmm * 1e-3
    phi, w, t, vmax = np.radians(phi0), 0.0, 0.0, 0.0
    while t < 20:
        deg = np.degrees(phi)
        net = tr(deg)
        if w == 0.0 and abs(net) <= fr:
            break
        a = (net - np.sign(w if w != 0 else net) * fr) / np.interp(deg, grid, Ie)
        w_new = w + a * dt
        if w != 0 and np.sign(w_new) != np.sign(w):
            w_new = 0.0
        w = w_new
        phi += w * dt
        vmax = max(vmax, abs(w) * R.Lb * 1e-3)
        t += dt
        if phi >= np.radians(90) or phi <= 0:
            break
    return float(np.degrees(phi)), t, float(vmax)


def run(N):
    R, P = C.build(N)
    out = dict(N=N, D=R.D, Lb=R.Lb, Lf=R.Lf, parts_printed=4, bodies=len(P) - 1)
    out["closure_pin_err"], out["closure_dir_err"] = closure(R, P)
    res = interference(R, P)
    out["poses_tested"], out["interference_bad"], out["interference_max_vol"] = res["poses"], res["bad"][:8], res["max_vol"]
    gaps = sorted(((g, k, ph) for k, (g, ph) in res["min_gap"].items()), key=lambda x: x[0])
    def intended(k):
        a, b = k
        if a.startswith("arm") and b.startswith("card") and a[3:].split("_")[0] == b[4:]:
            return True                                   # card rests on its own cradle floor
        return bool({a, b} & {"tie", "washer"})          # tie bar fits its square holes (0.2 mm) by design
    out["tightest"] = [(round(g, 2), k[0], k[1], ph) for g, k, ph in gaps if not intended(k)][:8]
    # print-in-place: bodies of one module that must not fuse (all gaps at the printed pose)
    pip = [(g, k) for k, g in res["gap0"].items() if k[0].endswith("_R") and k[1].endswith("_R")]
    out["print_in_place_min_gap"] = round(min(g for g, k in pip), 2) if pip else None
    out["print_in_place_tightest"] = [(round(g, 2), k[0], k[1]) for g, k in sorted(pip)[:4]]
    pf, p95, cl = tolerance_mc(R)
    out["tol_fail_rate"], out["tol_p95_offset"], out["pin_clearance"] = pf, p95, cl
    ms = masses(R, P)
    phis, U, tau = torque_curve(R, P, ms)
    out["mass_moving_g"] = float(sum(m for m, _ in ms.values()))
    out["tau_max_Nm"] = float(tau.max() * 1e-3)
    grid, Ie = i_eff_table(R, P, ms)
    out["unbraked"] = {}
    for f in (0, 50, 100):
        above = [p for p in phis if np.interp(p, phis, tau) * 1e-3 > f * 1e-3]
        hold = float(above[0]) if above else 90.0
        ang, tt, v = swing(R, grid, Ie, phis, tau, f, max(hold + 0.5, 1.0)) if above else (90.0, 0.0, 0.0)
        out["unbraked"][f] = dict(hold_deg=round(hold, 1), impact_m_s=round(v, 2))
    sp, resid = spring_fit(R, phis, tau)
    out["spring"] = {k: round(v, 4) for k, v in sp.items()}
    out["spring_post_height"], out["spring_anchor_height"] = R.a_sp, R.d_sp
    out["spring_tolerance_friction_Nmm"] = {"+-10%": round(0.10 * out["tau_max_Nm"] * 1e3, 1),
                                            "+-20%": round(0.20 * out["tau_max_Nm"] * 1e3, 1)}
    out["with_spring"] = {}
    for start in (10.0, 45.0, 80.0):
        ang, tt, v = swing(R, grid, Ie, phis, resid, 1.25 * sp["resid_max_Nm"] * 1e3, start)
        out["with_spring"][f"released_at_{int(start)}deg"] = dict(rests_at_deg=round(ang, 1), max_free_end_speed_m_s=round(v, 3))
    out["lift_force_N_at_free_end"] = float(out["tau_max_Nm"] / (R.Lb * 1e-3))
    return out


if __name__ == "__main__":
    Ns = [int(a) for a in sys.argv[1:]] or [1, 2, 3, 4, 5, 6]
    allres = {}
    for N in Ns:
        r = run(N)
        allres[N] = r
        print(f"N={N} closure={r['closure_pin_err']:.1e}/{r['closure_dir_err']} poses={r['poses_tested']} "
              f"bad={r['interference_bad'][:4]} tightest={r['tightest'][:3]} pip_gap={r['print_in_place_min_gap']}")
    json.dump(allres, open("side_test_results.json", "w"), indent=1, default=str)
