"""Tests of the fold-down rack mechanism (run: python3 foldout_test.py [N ...]).

1. Kinematic closure: for every degree 0..90 each cross-arm pin lands exactly on the hole centre
   of the panel (B1) and of B2, and every arm keeps its direction (so cards stay upright).
2. Interference: exact boolean intersection volume between every pair of parts that can meet,
   at every STEP degrees, plus the minimum gap between them.
3. Tolerance: Monte-Carlo of printed hole-position errors on the over-constrained parallelogram.
4. Statics/dynamics: gravity torque on the hinge, hold-open and closing force, opening speed.
"""
import sys
import json
import numpy as np
import manifold3d as m3d
import foldout_cad as C

STEP_DEG = 2


def to_manifold(mesh):
    mm = m3d.Mesh(vert_properties=np.asarray(mesh.vertices, dtype=np.float32),
                  tri_verts=np.asarray(mesh.faces, dtype=np.uint32))
    return m3d.Manifold(mm)


def kinematic_closure(R, P):
    worst_pin, worst_dir = 0.0, 0.0
    for phi in range(0, 91):
        TH, TF = C.rot_about(phi, 0, 0), C.rot_about(phi, R.h0, -R.D)
        tr = C.pose_transforms(R, P, phi)
        for j in range(R.N):
            J1 = np.array([0, R.s[j], 0, 1.0])
            J2 = np.array([0, R.s[j] + R.h0, -R.D, 1.0])
            # arm translated: arm B1-end must be at the panel's joint, arm B2-end at B2's joint
            a1 = tr[f"arm{j}_R"] @ J1
            a2 = tr[f"arm{j}_R"] @ J2
            worst_pin = max(worst_pin, np.linalg.norm((a1 - TH @ J1)[:3]), np.linalg.norm((a2 - TF @ J2)[:3]))
            # arm direction unchanged (pure translation)
            R3 = tr[f"arm{j}_R"][:3, :3]
            worst_dir = max(worst_dir, np.abs(R3 - np.eye(3)).max())
    return worst_pin, worst_dir


def interference(R, P, step=STEP_DEG, search=3.0):
    names = list(P)
    manis = {n: to_manifold(P[n]["mesh"]) for n in names}
    groups = {n: P[n]["group"] for n in names}
    results = dict(max_vol=0.0, bad=[], min_gap={}, poses=0)
    for phi in list(range(0, 91, step)) + ([90] if 90 % step else []):
        tr = C.pose_transforms(R, P, phi)
        pm, bb = {}, {}
        for n in names:
            T = tr[n]
            M = np.asarray(T[:3, :4], dtype=np.float64)
            pm[n] = manis[n].transform(M)
            v = P[n]["mesh"].vertices @ T[:3, :3].T + T[:3, 3]
            bb[n] = (v.min(0), v.max(0))
        for tag, sg in (("R", 1), ("L", -1)):
            rm = C.spring_mesh(R, phi, sg)
            pm["rod_" + tag] = to_manifold(rm)
            bb["rod_" + tag] = (rm.vertices.min(0), rm.vertices.max(0))
        results["poses"] += 1
        allnames = names + ["rod_R", "rod_L"]
        for a in range(len(allnames)):
            for b in range(a + 1, len(allnames)):
                na, nb = allnames[a], allnames[b]
                ga, gb = groups.get(na, "rod"), groups.get(nb, "rod")
                if ga == gb and phi != 0:
                    continue
                if ga == 'fixed' and gb == 'fixed':
                    continue
                (la, ha), (lb, hb) = bb[na], bb[nb]
                if np.any(la > hb + search) or np.any(lb > ha + search):
                    continue
                vol = (pm[na] ^ pm[nb]).volume()
                gap = 0.0 if vol > 1e-6 else pm[na].min_gap(pm[nb], search)
                key = tuple(sorted((na, nb)))
                if vol > 1e-3:
                    results["bad"].append((phi, na, nb, round(vol, 3)))
                    results["max_vol"] = max(results["max_vol"], vol)
                if gap < results["min_gap"].get(key, (1e9, 0))[0]:
                    results["min_gap"][key] = (gap, phi)
    return results


def tolerance_mc(R, trials=20000, sigma=0.10, clearance=(C.HOLE_D - C.PIN_D) / 2, seed=1):
    """Over-constrained parallelogram: arm length errors from printed hole positions.
    Each arm length error ~ sqrt(4) * sigma (4 holes). Residual pin offset ~ deviation from consensus / 2."""
    rng = np.random.default_rng(seed)
    N = R.N
    lens = rng.normal(0, np.sqrt(4) * sigma, size=(trials, N))
    # bars: B1/B2 hole pitch errors shift each joint pair too (2 more holes per joint)
    lens += rng.normal(0, np.sqrt(2) * sigma, size=(trials, N))
    consensus = np.median(lens, axis=1, keepdims=True) if N > 2 else lens.mean(1, keepdims=True)
    off = np.abs(lens - consensus) / 2 * 1.0
    worst = off.max(1)
    return float((worst > clearance).mean()), float(np.percentile(worst, 95)), clearance


def mass_properties(R, P, card_g=40.0, rho=1.27e-3):
    """(mass_g, pose-dependent centre of mass) per rigid group; cards modeled as card_g grams."""
    m = {}
    for n, d in P.items():
        if n.startswith(("post", "top_crossbar", "bottom_crossbar", "spacer", "pinH", "pinF")):
            continue
        mesh = d["mesh"]
        if n.startswith("card"):
            mass = card_g
            com = np.array([0, R.yb[int(n[4:])] + C.CARD_H * 0.4, R.zr[int(n[4:])] + 6.0])
        elif n.startswith("pin"):
            mass = 1.5
            com = mesh.center_mass
        else:
            mass = mesh.volume * rho
            com = mesh.center_mass
        m[n] = (mass, np.asarray(com, dtype=float))
    return m


def potential_and_torque(R, P, masses, card_g=40.0):
    """U(phi) = sum m g y_cm ; torque tau(phi) = -dU/dphi  [N mm]. Positive => opens."""
    g = 9.81e-3   # N per gram -> N (mass in g) ; use mm for lever => N*mm
    phis = np.radians(np.arange(0, 90.01, 0.5))
    U = []
    for p in phis:
        tr = C.pose_transforms(R, P, np.degrees(p))
        u = 0.0
        for n, (mass, com) in masses.items():
            c = tr[n] @ np.append(com, 1.0)
            u += mass * g * c[1]
        U.append(u)
    U = np.array(U)
    tau = -np.gradient(U, phis)
    return np.degrees(phis), U, tau


def simulate_open(R, P, masses, friction_nmm, phis, tau, dt=1e-3):
    """1-DOF swing under gravity with constant hinge friction.
    Returns (hold_angle_deg, impact_speed_m_s_at_free_end, time_s).
    hold_angle: below this angle the friction alone keeps the panel at rest.
    The swing is started from just above that angle (released by hand)."""
    def i_eff(phi):
        eps = 1e-3
        T0 = C.pose_transforms(R, P, phi)
        T1 = C.pose_transforms(R, P, phi + np.degrees(eps))
        k = 0.0
        for n, (mass, com) in masses.items():
            a = (T0[n] @ np.append(com, 1))[:3]
            b = (T1[n] @ np.append(com, 1))[:3]
            v = (b - a) / eps
            k += 0.5 * mass * 1e-3 * (np.linalg.norm(v) * 1e-3) ** 2
        return 2 * k
    grid = np.linspace(0, 90, 91)
    Ie = np.array([i_eff(p) for p in grid])
    taus = lambda deg: np.interp(deg, phis, tau) * 1e-3
    fr = friction_nmm * 1e-3
    above = [p for p in phis if taus(p) > fr]
    if not above:
        return 90.0, 0.0, 0.0          # friction holds it at every angle
    hold = float(above[0])
    phi, w, t = np.radians(hold + 0.5), 0.0, 0.0
    while phi < np.radians(90) and t < 30:
        deg = np.degrees(phi)
        net = taus(deg) - fr
        a = net / np.interp(deg, grid, Ie)
        w = max(w + a * dt, 0.0)
        phi += w * dt
        t += dt
    return hold, w * R.L * 1e-3, t


def spring_fit(R, phis, tau):
    """Counterbalance with two extension springs (one per side): from a post on the panel bar at
    height A_SP to a wall anchor at height d_sp straight above the hinge. Force F = c0 + k*l.
    Torque from both springs = 2*(c0/l + k)*A*d*sin(phi). Least-squares fit to cancel gravity."""
    A, d = C.A_SP, R.d_sp
    ph = np.radians(phis)
    l = np.sqrt(A * A + d * d - 2 * A * d * np.cos(ph))     # post-to-anchor distance
    geo = 2 * A * d * np.sin(ph) / 1.0                       # mm^2
    X = np.column_stack([geo / l, geo])                      # unknowns c0 [N], k [N/mm] -> torque N*mm
    sol, *_ = np.linalg.lstsq(X[1:], tau[1:], rcond=None)
    c0, k = sol
    spring_tau = X @ sol
    resid = tau - spring_tau
    lmin, lmax = l.min(), l.max()
    F_closed, F_open = c0 + k * lmin, c0 + k * lmax
    return dict(c0_N=float(c0), k_N_per_mm=float(k), l_min=float(lmin), l_max=float(lmax),
                force_closed_N_each=float(F_closed), force_open_N_each=float(F_open),
                resid_max_Nm=float(np.abs(resid).max() * 1e-3), tau_spring=spring_tau, resid=resid)


def simulate_with(R, P, masses, phis, resid_nmm, friction_nmm, phi0=45.0, dt=1e-3):
    """swing under the residual torque (gravity - spring) with hinge friction; start at phi0 at rest.
    returns final angle, time, max free-end speed."""
    def i_eff(phi):
        eps = 1e-3
        T0 = C.pose_transforms(R, P, phi)
        T1 = C.pose_transforms(R, P, phi + np.degrees(eps))
        k = 0.0
        for n, (mass, com) in masses.items():
            a = (T0[n] @ np.append(com, 1))[:3]
            b = (T1[n] @ np.append(com, 1))[:3]
            v = (b - a) / eps
            k += 0.5 * mass * 1e-3 * (np.linalg.norm(v) * 1e-3) ** 2
        return 2 * k
    grid = np.linspace(0, 90, 91)
    Ie = np.array([i_eff(p) for p in grid])
    tr = lambda deg: np.interp(deg, phis, resid_nmm) * 1e-3
    fr = friction_nmm * 1e-3
    phi, w, t, vmax = np.radians(phi0), 0.0, 0.0, 0.0
    while t < 20:
        deg = np.degrees(phi)
        net = tr(deg)
        if abs(w) < 1e-9 and abs(net) <= fr:
            break                                    # stuck by friction
        a = (net - np.sign(w if w != 0 else net) * fr) / np.interp(deg, grid, Ie)
        w_new = w + a * dt
        if w != 0 and np.sign(w_new) != np.sign(w):
            w_new = 0.0
        w = w_new
        phi += w * dt
        vmax = max(vmax, abs(w) * R.L * 1e-3)
        t += dt
        if phi >= np.radians(90) or phi <= 0:
            phi = min(max(phi, 0.0), np.radians(90))
            break
    return float(np.degrees(phi)), t, vmax


def run(N):
    R, P = C.build(N)
    out = dict(N=N, D=R.D, La=R.La, L=R.L, parts=len(P))
    out["closure_pin_err"], out["closure_dir_err"] = kinematic_closure(R, P)
    res = interference(R, P)
    out["interference_max_vol"] = res["max_vol"]
    out["interference_bad"] = res["bad"][:10]
    out["poses_tested"] = res["poses"]
    def intended(k):
        a, b = k
        if a.startswith(("pin", "spacer", "springpost")) or b.startswith(("pin", "spacer", "springpost")):
            return True                                   # bolts / spacers sit against faces by design
        if a.startswith("arm") and b.startswith("card") and a[3:].split("_")[0] == b[4:]:
            return True                                   # card rests on its own cradle floor
        if {a[:4], b[:4]} == {"pane", "post"} or "rod_" in a + b:
            return True                                   # panel on its stop at 90 deg / spring ends
        return False
    gaps = sorted(((g, k, ph) for k, (g, ph) in res["min_gap"].items() if not intended(k)), key=lambda x: x[0])
    out["tightest"] = [(round(g, 2), k[0], k[1], ph) for g, k, ph in gaps[:8]]
    out["contacts_at_stops"] = [(k[0], k[1], ph) for g, k, ph in sorted(((g, k, ph) for k, (g, ph) in res["min_gap"].items()),
                                                                       key=lambda x: x[0]) if g < 0.01 and intended(k)
                                and not (k[0].startswith(("pin", "spacer", "springpost")) or k[1].startswith(("pin", "spacer", "springpost")))][:8]

    pf, p95, cl = tolerance_mc(R)
    out["tol_fail_rate"], out["tol_p95_offset"], out["pin_clearance"] = pf, p95, cl
    masses = mass_properties(R, P)
    phis, U, tau = potential_and_torque(R, P, masses)
    out["tau_max_Nm"] = float(tau.max() * 1e-3)
    out["tau_at_5deg_Nm"] = float(np.interp(5, phis, tau) * 1e-3)
    out["tau_at_90deg_Nm"] = float(np.interp(89.5, phis, tau) * 1e-3)
    out["mass_moving_g"] = float(sum(m for m, _ in masses.values()))
    fr = {}
    for f in (0, 50, 100, 150, 200, 300):
        hold, v, t = simulate_open(R, P, masses, f, phis, tau)
        fr[f] = dict(hold_deg=round(hold, 1), impact_m_s=round(v, 2), time_s=round(t, 2))
    out["opening_by_friction_Nmm"] = fr
    sp = spring_fit(R, phis, tau)
    out["spring"] = {k: (round(v, 4) if isinstance(v, float) else v) for k, v in sp.items() if k not in ("tau_spring", "resid")}
    fr_need = 1.25 * sp["resid_max_Nm"] * 1e3
    out["friction_needed_Nmm"] = round(fr_need, 1)
    out["with_spring"] = {}
    for start in (10.0, 45.0, 80.0):
        ang, tt, vmax = simulate_with(R, P, masses, phis, sp["resid"], fr_need, phi0=start)
        out["with_spring"][f"released_at_{int(start)}deg"] = dict(rests_at_deg=round(ang, 1), max_free_end_speed_m_s=round(vmax, 3))
    out["spring_tolerance_friction_Nmm"] = {"+-10%": round(0.10 * out["tau_max_Nm"] * 1e3, 1),
                                            "+-20%": round(0.20 * out["tau_max_Nm"] * 1e3, 1)}
    out["hand_force_at_free_end_N"] = round((sp["resid_max_Nm"] + fr_need * 1e-3) / (R.L * 1e-3), 2)
    # closing effort at the free end: max torque / lever
    out["lift_force_N_at_free_end"] = float(tau.max() * 1e-3 / (R.L * 1e-3))
    return out


if __name__ == "__main__":
    Ns = [int(a) for a in sys.argv[1:]] or [1, 2, 3, 4, 5, 6]
    allres = {}
    for N in Ns:
        r = run(N)
        allres[N] = r
        print(json.dumps(r, indent=1, default=str))
    json.dump(allres, open("foldout_test_results.json", "w"), indent=1, default=str)
