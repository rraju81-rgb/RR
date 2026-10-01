"""Loaded-equilibrium droop of the lattice from pin clearance (energy-minimising LP), and tilt compensation."""
import numpy as np
from scipy.optimize import linprog
import rack_cad as C


def loaded_droop(R, th, slack, slot_x, hook_w=0.4, link_w=0.02):
    K = R.K
    w, h = R.wh(th)
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
    nvar = 3 * nb + 2 * nj + 3

    def disp(body, px, py):
        n = bi[body]
        cx, cy = (body[0] - 0.5) * w, h / 2
        rx, ry = px - cx, py - cy
        ux = np.zeros(nvar); uy = np.zeros(nvar)
        ux[3 * n] = 1; ux[3 * n + 2] = -ry
        uy[3 * n + 1] = 1; uy[3 * n + 2] = rx
        return ux, uy

    Aeq, beq = [], []
    for j, (px, py, a, b) in enumerate(J):
        uax, uay = disp(a, px, py)
        ubx, uby = disp(b, px, py)
        ex = np.zeros(nvar); ey = np.zeros(nvar)
        ex[3 * nb + 2 * j] = 1; ey[3 * nb + 2 * j + 1] = 1
        Aeq += [uax - ubx - ex, uay - uby - ey]; beq += [0, 0]
    g = 3 * nb + 2 * nj
    ux, uy = disp((1, "A"), 0.0, 0.0)
    e = np.zeros(nvar); e[g] = 1; Aeq.append(ux - e); beq.append(0)
    e = np.zeros(nvar); e[g + 1] = 1; Aeq.append(uy - e); beq.append(0)
    ux, uy = disp((1, "B"), 0.0, h)
    e = np.zeros(nvar); e[g + 2] = 1; Aeq.append(ux - e); beq.append(0)
    Aeq.append(uy); beq.append(0)
    bounds = [(-300, 300)] * (3 * nb) + [(-slack, slack)] * (2 * nj) + [(-slack, slack), (-slack, slack), (-slot_x, slot_x)]
    c = np.zeros(nvar)
    for k in range(1, K + 1):
        hx, hy = R.hook_xy(k, th)
        c += hook_w * disp((k, "B"), hx, hy)[1]
    for b in bodies:
        c += link_w * disp(b, (b[0] - 0.5) * w, h / 2)[1]
    r = linprog(c, A_eq=np.array(Aeq), b_eq=np.array(beq), bounds=bounds, method="highs")
    d = {}
    for k in range(1, K + 1):
        hx, hy = R.hook_xy(k, th)
        d[k] = float(-(disp((k, "B"), hx, hy)[1] @ r.x))
    return d


def tilt_for(R, clearance=0.33, hook_w=0.4):
    slot = clearance / 2 + (C.SLOT_W - C.BOLT_D) / 2
    d = loaded_droop(R, C.TH_MIN, clearance, slot, hook_w)
    xs = np.array([R.hook_xy(k, C.TH_MIN)[0] for k in d])
    ds = np.array([d[k] for k in d])
    a = float((ds * xs).sum() / (xs ** 2).sum())          # rad: droop ~ a * x
    return a, d, xs


if __name__ == "__main__":
    for N in (3, 5):
        R = C.Rack(N)
        a, d, xs = tilt_for(R)
        print(f"N={N}: expected droop by hook {[round(v,2) for v in d.values()]} mm at x={[round(x) for x in xs]};  tilt = {np.degrees(a):.2f} deg")
        for c in (0.25, 0.33, 0.40, 0.50):
            dd = loaded_droop(R, C.TH_MIN, c, c / 2 + (C.SLOT_W - C.BOLT_D) / 2)
            res = [dd[k] - a * xs[k - 1] for k in dd]
            print(f"   clearance {c}: droop {[round(v,2) for v in dd.values()]}  after tilt compensation {[round(v,2) for v in res]}")
