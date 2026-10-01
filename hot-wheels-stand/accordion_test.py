"""Tests for the accordion hook rack. python3 accordion_test.py [N ...]
1 closure of every pin  2 interference + gaps over the whole fold  3 static pin forces at the open stop
4 printability checks  5 worst-case droop from pin clearance (linear program)."""
import sys, json
import numpy as np
import manifold3d as m3d
from scipy.optimize import linprog
import accordion_cad as C

STEP_DEG = 2


def to_manifold(mesh):
    return m3d.Manifold(m3d.Mesh(vert_properties=np.asarray(mesh.vertices, dtype=np.float32),
                                 tri_verts=np.asarray(mesh.faces, dtype=np.uint32)))


def link_world_points(A, th, i, tag):
    """end0, centre, end1 of link A_i or B_i."""
    w, h = A.wh(th)
    ang = th if tag == "A" else -th
    c = np.array([(i - 0.5) * w, h / 2])
    d = np.array([np.cos(ang), np.sin(ang)]) * A.L / 2
    return c - d, c, c + d


def closure(A):
    worst = 0.0
    ths = np.radians(np.arange(14, 70.1, 1.0))
    for th in ths:
        w, h = A.wh(th)
        for i in range(1, A.K + 1):
            a0, ac, a1 = link_world_points(A, th, i, "A")
            b0, bc, b1 = link_world_points(A, th, i, "B")
            worst = max(worst, np.linalg.norm(ac - bc))                        # centre pivot
            worst = max(worst, np.linalg.norm(a0 - [(i - 1) * w, 0]), np.linalg.norm(a1 - [i * w, h]))
            worst = max(worst, np.linalg.norm(b0 - [(i - 1) * w, h]), np.linalg.norm(b1 - [i * w, 0]))
        for k in range(1, A.K):
            _, _, b1 = link_world_points(A, th, k, "B")
            a0, _, _ = link_world_points(A, th, k + 1, "A")
            worst = max(worst, np.linalg.norm(b1 - a0))                         # H_k shared by B_k and A_{k+1}
            _, _, a1 = link_world_points(A, th, k, "A")
            b0, _, _ = link_world_points(A, th, k + 1, "B")
            worst = max(worst, np.linalg.norm(a1 - b0))                         # U_k shared
    return worst


def interference(A, T, step=STEP_DEG, search=3.0, plate=None):
    res = dict(bad=[], min_gap={}, poses=0, max_vol=0.0, with_cards=0)
    hw = {k: to_manifold(m) for k, m in C.hardware(A).items()}
    plate_m = to_manifold(plate)
    ths = list(range(14, 71, step)) + ([70] if 70 % step else [])
    for d in ths:
        th = np.radians(d)
        w, h = A.wh(th)
        cards = w >= C.CARD_W + 2.0
        parts = C.assembly(A, th, dict(T, plate=plate), with_cards=cards)
        res["poses"] += 1
        res["with_cards"] += int(cards)
        man, bb, grp = {}, {}, {}
        for n, (m, g) in parts.items():
            man[n] = plate_m if n == "plate" else to_manifold(m)
            bb[n] = (m.vertices.min(0), m.vertices.max(0))
            grp[n] = g
        for n, mm in hw.items():
            man[n] = mm
            v = C.hardware(A)[n].vertices
            bb[n] = (v.min(0), v.max(0))
            grp[n] = "fixed"
        names = list(man)
        for a in range(len(names)):
            for b in range(a + 1, len(names)):
                na, nb = names[a], names[b]
                if grp[na] == grp[nb] and d != 14:
                    continue
                if grp[na] == "fixed" and grp[nb] == "fixed":
                    continue
                (la, ha), (lb, hb) = bb[na], bb[nb]
                if np.any(la > hb + search) or np.any(lb > ha + search):
                    continue
                vol = (man[na] ^ man[nb]).volume()
                gap = 0.0 if vol > 1e-6 else man[na].min_gap(man[nb], search)
                key = tuple(sorted((na, nb)))
                if vol > 1e-3:
                    res["bad"].append((d, na, nb, round(vol, 3)))
                    res["max_vol"] = max(res["max_vol"], vol)
                if gap < res["min_gap"].get(key, (1e9, 0))[0]:
                    res["min_gap"][key] = (gap, d)
    return res


def statics(A, th, card_w=0.4, link_w=0.097):
    """pin forces with the open stop engaged (worst case). unknowns: pin forces and wall reactions."""
    K = A.K
    if K == 0:
        return dict(max_pin_N=0.0, hook_load_N=card_w)
    w, h = A.wh(th)
    bodies = [(i, t) for i in range(1, K + 1) for t in "AB"]
    bi = {b: n for n, b in enumerate(bodies)}
    J = []                                   # (pos, body_a, body_b)
    for i in range(1, K + 1):
        J.append(((((i - 0.5) * w), h / 2), (i, "A"), (i, "B")))
    for k in range(1, K):
        J.append(((k * w, 0.0), (k, "B"), (k + 1, "A")))
        J.append(((k * w, h), (k, "A"), (k + 1, "B")))
    nU = 2 * len(J)
    nunk = nU + 4                            # + H0 (2) on A1, U0 (2) on B1
    rows = 3 * len(bodies)
    M = np.zeros((rows, nunk))
    rhs = np.zeros(rows)

    def add_force(body, pos, col_x, sign):
        n = bi[body]
        cen = np.array([(body[0] - 0.5) * w, h / 2])
        r = np.array(pos) - cen
        M[3 * n, col_x] += sign
        M[3 * n + 1, col_x + 1] += sign
        M[3 * n + 2, col_x] += sign * (-r[1])
        M[3 * n + 2, col_x + 1] += sign * r[0]

    for j, (pos, a, b) in enumerate(J):
        add_force(a, pos, 2 * j, +1)
        add_force(b, pos, 2 * j, -1)
    add_force((1, "A"), (0.0, 0.0), nU, +1)
    add_force((1, "B"), (0.0, h), nU + 2, +1)
    def known(body, pos, fx, fy):
        n = bi[body]
        cen = np.array([(body[0] - 0.5) * w, h / 2])
        rx, ry = pos[0] - cen[0], pos[1] - cen[1]
        rhs[3 * n] -= fx
        rhs[3 * n + 1] -= fy
        rhs[3 * n + 2] -= (rx * fy - ry * fx)

    for body in bodies:                           # link weights at their centres
        known(body, ((body[0] - 0.5) * w, h / 2), 0.0, -link_w)
    for k in range(A.N):                          # card weight on the hook pin at H_k
        body = (K, "B") if k == K else (k + 1, "A")
        known(body, (k * w, 0.0), 0.0, -card_w)
    sol, *_ = np.linalg.lstsq(M, rhs, rcond=None)
    resid = np.linalg.norm(M @ sol - rhs)
    pins = [np.hypot(sol[2 * j], sol[2 * j + 1]) for j in range(len(J))]
    return dict(max_pin_N=float(max(pins)), wall_H0_N=float(np.hypot(sol[nU], sol[nU + 1])),
                slot_U0_N=float(np.hypot(sol[nU + 2], sol[nU + 3])), residual=float(resid), hook_load_N=card_w)


def droop(A, th, slack=0.4):
    """worst-case downward displacement of the last hook caused by pin clearance (linear program)."""
    K = A.K
    if K == 0:
        return 0.0
    w, h = A.wh(th)
    bodies = [(i, t) for i in range(1, K + 1) for t in "AB"]
    bi = {b: n for n, b in enumerate(bodies)}
    nb = len(bodies)
    J = []
    for i in range(1, K + 1):
        J.append(((i - 0.5) * w, h / 2, (i, "A"), (i, "B")))
    for k in range(1, K):
        J.append((k * w, 0.0, (k, "B"), (k + 1, "A")))
        J.append((k * w, h, (k, "A"), (k + 1, "B")))
    nj = len(J)
    nvar = 3 * nb + 2 * nj + 3          # body motions, joint slacks, ground slacks (H0 xy, U0 x)
    A_eq, b_eq = [], []

    def disp_row(body, px, py):
        n = bi[body]
        cx, cy = (body[0] - 0.5) * w, h / 2
        rx, ry = px - cx, py - cy
        ux = np.zeros(nvar); uy = np.zeros(nvar)
        ux[3 * n] = 1; ux[3 * n + 2] = -ry
        uy[3 * n + 1] = 1; uy[3 * n + 2] = rx
        return ux, uy

    for j, (px, py, a, b) in enumerate(J):
        uax, uay = disp_row(a, px, py)
        ubx, uby = disp_row(b, px, py)
        ex, ey = np.zeros(nvar), np.zeros(nvar)
        ex[3 * nb + 2 * j] = 1
        ey[3 * nb + 2 * j + 1] = 1
        A_eq.append(uax - ubx - ex); b_eq.append(0)
        A_eq.append(uay - uby - ey); b_eq.append(0)
    ux, uy = disp_row((1, "A"), 0.0, 0.0)               # H0 in the plate hole
    g = 3 * nb + 2 * nj
    e = np.zeros(nvar); e[g] = 1; A_eq.append(ux - e); b_eq.append(0)
    e = np.zeros(nvar); e[g + 1] = 1; A_eq.append(uy - e); b_eq.append(0)
    ux, uy = disp_row((1, "B"), 0.0, h)                 # U0: slot, x within slack, y fixed (resting on the stop)
    e = np.zeros(nvar); e[g + 2] = 1; A_eq.append(ux - e); b_eq.append(0)
    A_eq.append(uy); b_eq.append(0)
    tx, ty = disp_row((K, "B"), K * w, 0.0)             # last hook (end of B_K)
    c = ty.copy()                                        # minimise uy  => maximum droop
    bounds = [(-5, 5)] * (3 * nb)
    bounds += [(-slack, slack)] * (2 * nj)
    bounds += [(-slack, slack), (-slack, slack), (-slack - 0.2, slack + 0.2)]
    r = linprog(c, A_eq=np.array(A_eq), b_eq=np.array(b_eq), bounds=bounds, method="highs")
    return float(-r.fun) if r.success else float("nan")


def printability(A, T):
    parts = dict(link=T["link"], pivot_pin=T["pivot"], hook_pin=T["hook"], wall_plate=C.wall_plate(A))
    out = {}
    for n, m in parts.items():
        out[n] = dict(size_mm=[round(float(x), 1) for x in m.extents], fits_300_bed=bool(max(m.extents) < C.BED), watertight=bool(m.is_watertight))
    out["min_features_mm"] = dict(
        link_hole_wall=(C.LINK_W - C.HOLE_D) / 2, pin_barb_arm=(C.PIN_D - 1.0) / 2, plate_front_after_groove=C.PLATE_Z1 - C.PLATE_FRONT_Z0,
        hook_peg_diameter=C.PEG_D, card_hole_diameter=C.CARD_HOLE_D, pin_to_hole_clearance=(C.HOLE_D - C.PIN_D) / 2)
    out["overhangs"] = "none beyond 45 degrees: links flat; pins and hooks lie on their side; plate rear face down (8 mm groove bridges)"
    return out


def run(N):
    A = C.Acc(N)
    T = C.build_templates()
    plate = C.wall_plate(A)
    out = dict(N=N, K=A.K, links=2 * A.K, pivot_pins=2 * A.K, hook_pins=N, open_spacing=A.w_open, closed_spacing=A.w_closed,
               rack_width_open=A.K * A.w_open + C.CARD_W, rack_width_closed=A.K * A.w_closed + 30.0,
               height_open=A.h_min + C.LINK_W, height_closed=A.h_max + C.LINK_W)
    out["closure_err_mm"] = closure(A) if A.K else 0.0
    res = interference(A, T, plate=plate)
    out["poses"], out["poses_with_cards"] = res["poses"], res["with_cards"]
    out["interference_bad"], out["interference_max_vol"] = res["bad"][:8], res["max_vol"]
    gaps = sorted(((g, k, ph) for k, (g, ph) in res["min_gap"].items()), key=lambda x: x[0])
    out["tightest"] = [(round(g, 2), k[0], k[1], ph) for g, k, ph in gaps[:6]]
    st = statics(A, C.TH_MIN) if A.K else dict(max_pin_N=0, hook_load_N=0.4)
    out["statics_open"] = {k: round(v, 3) for k, v in st.items()}
    out["droop_mm"] = {"slack_0.4": round(droop(A, C.TH_MIN, 0.4), 2), "slack_0.2": round(droop(A, C.TH_MIN, 0.2), 2)} if A.K else {}
    out["printability"] = printability(A, T)
    return out


if __name__ == "__main__":
    Ns = [int(a) for a in sys.argv[1:]] or [1, 2, 3, 4, 5, 6]
    allres = {}
    for N in Ns:
        r = run(N)
        allres[N] = r
        print(f"N={N} closure={r['closure_err_mm']:.1e} poses={r['poses']} (cards on {r['poses_with_cards']}) bad={r['interference_bad'][:3]} "
              f"tight={r['tightest'][:2]} statics={r['statics_open']} droop={r['droop_mm']}", flush=True)
    json.dump(allres, open("accordion_test_results.json", "w"), indent=1, default=str)
