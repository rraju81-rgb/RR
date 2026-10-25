#!/usr/bin/env python3
"""Hand check of the sandwich lay-up: beam + plate formulas, calibrated against the REV C FEA.

    python tools/hand_check.py

The full CalculiX model meshes the face sheets with solid tetrahedra, which a 0.3 mm skin cannot be
meshed with, so the thin-skin lay-up is checked by hand instead:
  1. beam:     the paddle as a cantilever from the grip clamp (y = 112) to the ball (LC1 y = 265, LC2 y = 345),
               500 N, flexural rigidity of skins + core section by section -> skin stress, core stress, deflection;
  2. skin:     the skin between two bond lands under the ball's contact pressure, as a clamped strip with
               immovable edges, solved with membrane stretching (large deflection) -> local skin stress;
  3. dimpling: compression buckling of the skin between lands, k = 4 (simply supported long plate).
Cases: REV C (4 / 8 / 4, printed PA-CF core), REV D (0.3 / 10 / 0.3, PA-CF core) and REV E (the same
lay-up with the rib support moulded in carbon fibre).
The same method run on the REV C lay-up (4 / 8 / 4) is compared with its FEA to give calibration factors
for the skin stress (FEA / beam = 1.4: the throat fillet and plate effects) and the deflection (1.7: shear
and the flexible handle).  The core is quoted as the plain beam bending stress: its REV C FEA peak was a
local one at the flute run-outs, so it calibrates nothing; local core peaks come on top.
Writes analysis/hand_check.json.
"""
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402

from paddle import fea, wave  # noqa: E402
from paddle.geometry import CONSTRUCTION, DESIGNS, build  # noqa: E402

EF, NUF = fea.CF["E1"], fea.CF["nu12"]
A = fea.ALLOW
# core materials: modulus [MPa] and bending allowable [MPa].  Moulded chopped carbon/epoxy is taken
# conservatively for a hand-laid part with some voids (pressed SMC-grade parts reach 35-40 GPa, 250 MPa).
CORES = {"PA-CF print": dict(E=fea.CORE["E"], allow=A["core_vm"]), "moulded carbon": dict(E=25000.0, allow=120.0)}
CORE = dict(CORES["PA-CF print"])
REV_C = dict(face_t=4.0, core_t=8.0, rib_amp=4.0, runout_len=8.0)      # analysed by FEA
LAYUP = dict(face_t=0.3, core_t=10.0, rib_amp=5.2, runout_len=10.0)     # REV D and E
CASES = (("REV_C", REV_C, "PA-CF print"), ("REV_D", LAYUP, "PA-CF print"), ("REV_E", LAYUP, "moulded carbon"))
FEA_C = dict(LC1=dict(deflection=2.25), LC2=dict(deflection=3.85, cf=141.0, core=17.5))   # elongated, REV C report


def lay_up(**kw):
    """Temporarily switch the shared construction (frozen dataclass) to another lay-up."""
    for k, v in kw.items():
        object.__setattr__(CONSTRUCTION, k, v)


def wave_I_per_width() -> float:
    """Second moment of the wave walls about the mid-plane per mm of width (mm^4 / mm)."""
    lam = CONSTRUCTION.rib_pitch
    poly = wave.wall_polygon(-lam / 2, lam / 2, 800)
    from shapely.geometry import Polygon
    g = Polygon(poly).buffer(0)
    xs = np.linspace(-lam / 2, lam / 2, 1601)
    zs = np.linspace(-CONSTRUCTION.core_t / 2, CONSTRUCTION.core_t / 2, 401)
    X, Z = np.meshgrid(xs, zs)
    from shapely import contains_xy
    inside = contains_xy(g, X, Z)
    dA = (xs[1] - xs[0]) * (zs[1] - zs[0])
    return float((Z ** 2 * inside).sum() * dA / lam)


def section(o, y: float, i_wave: float) -> tuple[float, float, float]:
    """Width, EI (N mm^2) and the outer-skin lever arm at height y."""
    C = CONSTRUCTION
    w = 2 * o.half_width_at(y)
    h, t = C.core_t / 2, C.face_t
    i_skin = w * 2 * ((h + t) ** 3 - h ** 3) / 3
    if y <= C.solid_to:
        i_core = w * (2 * h) ** 3 / 12
    else:                                        # closed frame both sides + wave walls in between
        i_core = 2 * C.frame_w * (2 * h) ** 3 / 12 + max(w - 2 * C.frame_w, 0.0) * i_wave
    return w, EF * i_skin + CORE["E"] * i_core, h + t


def beam(o, y_load: float, P: float = 500.0) -> dict:
    C = CONSTRUCTION
    y0 = fea.GRIP_Y[1]
    i_wave = wave_I_per_width()
    ys = np.linspace(y0, y_load, 1200)
    secs = [section(o, y, i_wave) for y in ys]
    M = P * (y_load - ys)
    EI = np.array([s[1] for s in secs])
    z_out = np.array([s[2] for s in secs])
    sig_f = M * EF * z_out / EI                  # skin outer fibre
    sig_c = M * CORE["E"] * (C.core_t / 2) / EI   # core extreme fibre
    ok = ys >= y0 + 8.0                          # the FEA does not assess the first 8 mm above the clamp
    k = int(np.argmax(np.where(ok, sig_f, 0)))
    y_tip = o.spec.length
    defl = float(np.trapezoid(M / EI * (y_tip - ys), ys))
    blade = ys >= C.solid_to + C.runout_len       # skin over the wave rib (supported only on the lands)
    kb = int(np.argmax(np.where(blade, sig_f, 0))) if blade.any() else None
    return dict(skin_max=float(sig_f[k]), skin_at_y=float(ys[k]), core_max=float(np.max(np.where(ok, sig_c, 0))),
                tip_deflection=defl, skin_blade_max=float(sig_f[kb]) if kb is not None else 0.0,
                skin_blade_at_y=float(ys[kb]) if kb is not None else None)


def skin_strip(p: float, b: float, t: float, n: int = 201) -> dict:
    """Clamped strip, immovable edges, uniform pressure p: D w'''' - N w'' = p with N from the stretch."""
    D = EF * t ** 3 / (12 * (1 - NUF ** 2))
    x = np.linspace(0, b, n)
    hx = x[1] - x[0]
    N = 0.0
    for _ in range(200):
        # finite differences with ghost-free clamped ends (w = w' = 0) on the interior unknowns
        m = n - 2
        K = np.zeros((m, m))
        for i in range(m):
            for j, c in ((i - 2, 1), (i - 1, -4), (i, 6), (i + 1, -4), (i + 2, 1)):
                if 0 <= j < m:
                    K[i, j] += D * c / hx ** 4
            for j, c in ((i - 1, -1), (i, 2), (i + 1, -1)):
                if 0 <= j < m:
                    K[i, j] += N * c / hx ** 2
        K[0, 0] += D / hx ** 4                    # clamped: mirror node w(-1) = w(1)
        K[-1, -1] += D / hx ** 4
        w = np.zeros(n)
        w[1:-1] = np.linalg.solve(K, np.full(m, p))
        slope = np.gradient(w, hx)
        N_new = EF * t / (1 - NUF ** 2) / (2 * b) * np.trapezoid(slope ** 2, x)
        if abs(N_new - N) < 1e-6 * max(N_new, 1.0):
            N = N_new
            break
        N = 0.5 * N + 0.5 * N_new
    curv = np.gradient(slope, hx)
    sig = N / t + 6 * D * np.abs(curv) / t ** 2
    lin = p * b ** 2 / (2 * t ** 2)
    return dict(stress=float(sig.max()), membrane=float(N / t), deflection=float(w.max()), linear_stress=float(lin))


def main() -> None:
    out = {}
    outlines = {sp.key: build(sp) for sp in DESIGNS}  # plan outlines do not depend on the lay-up
    p = 500.0 / (math.pi * 15.0 ** 2)             # ball contact pressure, 500 N on a 30 mm patch
    for tag, kw, core in CASES:
        lay_up(**kw)
        CORE.update(CORES[core])
        C = CONSTRUCTION
        b = C.rib_pitch - wave.land_width()
        res = dict(lay_up=f"{C.face_t:g} / {C.core_t:g} / {C.face_t:g}", core=core, core_E=CORE["E"],
                   core_allow=CORE["allow"], span_between_lands=round(b, 2), designs={})
        for key, o in outlines.items():
            res["designs"][key] = {lc.key: beam(o, lc.y) for lc in fea.LOADS}
        sk = skin_strip(p, b, C.face_t)
        res["skin_between_lands"] = dict(pressure=round(p, 3), **{k: round(v, 3) for k, v in sk.items()})
        res["dimpling_stress"] = 4 * math.pi ** 2 * EF / (12 * (1 - NUF ** 2)) * (C.face_t / b) ** 2
        out[tag] = res
    # calibration on REV C elongated (FEA results of the REV C report)
    bc = out["REV_C"]["designs"]["elongated"]
    cal = dict(skin=FEA_C["LC2"]["cf"] / bc["LC2"]["skin_max"],
               deflection=float(np.mean([FEA_C[k]["deflection"] / bc[k]["tip_deflection"] for k in ("LC1", "LC2")])))
    out["calibration_fea_over_beam"] = cal
    for tag, _, _ in CASES:
        for key, d in out[tag]["designs"].items():
            for lc, r in d.items():
                r["skin_expected"] = r["skin_max"] * cal["skin"]
                r["rf_core"] = out[tag]["core_allow"] / r["core_max"]   # bending only: no factor, see the docstring
                r["deflection_expected"] = r["tip_deflection"] * cal["deflection"]
                r["rf_skin"] = A["cf_c"] / r["skin_expected"]
                r["rf_dimpling"] = out[tag]["dimpling_stress"] / max(r["skin_blade_max"], 1e-9)
                for k2 in list(r):
                    if isinstance(r[k2], float):
                        r[k2] = round(r[k2], 3)
        out[tag]["dimpling_stress"] = round(out[tag]["dimpling_stress"], 1)
        sk = out[tag]["skin_between_lands"]
        sk["rf"] = round(A["cf_c"] / sk["stress"], 3)
    out["calibration_fea_over_beam"] = {k: round(v, 3) for k, v in cal.items()}
    out["allowables_MPa"] = dict(cf_tension=A["cf_t"], cf_compression=A["cf_c"],
                                 **{f"core_{k}": v["allow"] for k, v in CORES.items()})
    lay_up(**LAYUP)
    (ROOT / "analysis" / "hand_check.json").write_text(json.dumps(out, indent=1))

    print("calibration FEA / beam (REV C elongated):", out["calibration_fea_over_beam"])
    for tag, _, _ in CASES:
        r = out[tag]
        print(f"\n{tag}  lay-up {r['lay_up']}, core {r['core']}  span between lands {r['span_between_lands']} mm")
        for key, d in r["designs"].items():
            for lc, v in d.items():
                print(f"  {key:9s} {lc}: skin {v['skin_expected']:7.0f} MPa (beam {v['skin_max']:6.0f} at y {v['skin_at_y']:5.0f})"
                      f"  RF {v['rf_skin']:5.2f} | core {v['core_max']:5.1f} MPa RF {v['rf_core']:4.2f} | tip deflection "
                      f"{v['deflection_expected']:6.2f} mm | blade skin {v['skin_blade_max']:5.0f} MPa vs dimpling "
                      f"{r['dimpling_stress']:7.0f} (RF {v['rf_dimpling']:.2f})")
        s = r["skin_between_lands"]
        print(f"  skin between lands under the ball: {s['stress']:.0f} MPa (linear {s['linear_stress']:.0f}), "
              f"deflection {s['deflection']:.3f} mm, RF {s['rf']:.2f}")


if __name__ == "__main__":
    main()
