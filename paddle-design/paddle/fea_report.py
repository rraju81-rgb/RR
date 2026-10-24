"""Stress-analysis post-processing: result statistics, contour figures and the HTML/PDF report.

Reads the CalculiX runs written by tools/run_fea_case.py (mesh.npz, paddle.dat, paddle.frd)
and caches the parsed integration-point stresses and nodal displacements next to them.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from . import fea, wave
from . import fea_plots as fp
from .geometry import CONSTRUCTION as C
from .geometry import GRIP, Outline

Y_MIN = fea.GRIP_Y[1] + 8.0          # results closer than 8 mm to the rigid clamp edge are not assessed
SETS = ("E_TOP", "E_CORE", "E_BOT")
B_AMP = 3.6                          # wave amplitude of the first core version (baseline run)
LC_SHORT = {"LC1": "sweet spot", "LC2": "tip"}


@dataclass
class Case:
    name: str
    o: Outline
    m: fea.Mesh
    stress: list[dict[str, np.ndarray]]     # per load case: element set -> rows (elem, ip, sxx..syz)
    disp: list[np.ndarray]                  # per load case: (n_nodes, 3)


def load_case(o: Outline, wd: Path, n_loads: int = len(fea.LOADS)) -> Case:
    m = fp.load_mesh(wd / "mesh.npz")
    cache = wd / "post_cache.npz"
    if cache.exists():
        z = np.load(cache)
        stress = [{k: z[f"s{i}_{k}"] for k in SETS} for i in range(n_loads)]
        disp = [z[f"u{i}"] for i in range(n_loads)]
    else:
        stress = fea.read_dat_stresses(wd / "paddle.dat")[:n_loads]
        disp = fea.read_frd_displacements(wd / "paddle.frd")[:n_loads]
        np.savez_compressed(cache, **{f"s{i}_{k}": s[k] for i, s in enumerate(stress) for k in SETS},
                            **{f"u{i}": u for i, u in enumerate(disp)})
    return Case(o.spec.name, o, m, stress, disp)


# ---------------------------------------------------------------- statistics
def _elem_index(m: fea.Mesh, key: str, rows: np.ndarray) -> np.ndarray:
    return rows[:, 0].astype(np.int64) - int(m.eids[key][0])


def bond_points(c: Case, i: int) -> dict[str, np.ndarray]:
    """Integration points of the core elements bonded to a face sheet, outside the clamp zone."""
    rows = c.stress[i]["E_CORE"]
    idx = _elem_index(c.m, "CORE", rows)
    cen = fea.element_ip_coords(c.m, "CORE")[idx]
    on = fea.interface_elements(c.m)[idx] & (cen[:, 1] >= Y_MIN)
    s = rows[on, 2:]
    return dict(y=cen[on, 1], z=cen[on, 2], shear=np.hypot(s[:, 4], s[:, 5]), peel=np.maximum(s[:, 2], 0.0))


def bond_profile(c: Case, i: int, step: float = 5.0) -> dict[str, list[float]]:
    """Bond-line shear along the paddle: max, 99th percentile and mean per band of the blade height."""
    b = bond_points(c, i)
    out: dict[str, list[float]] = {"y": [], "max": [], "p99": [], "mean": []}
    y0 = Y_MIN
    while y0 < c.o.spec.length:
        sel = (b["y"] >= y0) & (b["y"] < y0 + step)
        if sel.sum() >= 20:
            v = b["shear"][sel]
            out["y"].append(round(y0 + step / 2, 1))
            out["max"].append(round(float(v.max()), 2))
            out["p99"].append(round(float(np.percentile(v, 99)), 2))
            out["mean"].append(round(float(v.mean()), 2))
        y0 += step
    return out


def case_stats(c: Case, i: int) -> dict:
    """fea.evaluate() peaks + deflection + the bond-line statistics used in the report."""
    r = fea.evaluate(c.m, c.o, c.stress[i], y_min=Y_MIN)
    uz = np.abs(c.disp[i][:, 2])
    k = int(np.argmax(uz))
    r["max_deflection"] = dict(value=round(float(uz[k]), 3), at=[round(float(v), 1) for v in c.m.nodes[k]])
    b = bond_points(c, i)
    ys = r["bond_shear"]["at"][1]
    hot = np.abs(b["y"] - ys) <= 5.0                               # 10 mm band through the peak
    r["bond_shear_stats"] = dict(p99_hot_band=round(float(np.percentile(b["shear"][hot], 99)), 2),
                                 p99_all=round(float(np.percentile(b["shear"], 99)), 2),
                                 mean_all=round(float(b["shear"].mean()), 2))
    yp = r["bond_peel"]["at"][1]
    hot = np.abs(b["y"] - yp) <= 5.0
    r["bond_peel_stats"] = dict(p99_hot_band=round(float(np.percentile(b["peel"][hot], 99)), 2),
                                p99_all=round(float(np.percentile(b["peel"], 99)), 2))
    r["rf"]["bond_hot_band"] = round(min(fea.ALLOW["bond_shear"] / r["bond_shear_stats"]["p99_hot_band"],
                                         fea.ALLOW["bond_peel"] / max(r["bond_peel_stats"]["p99_hot_band"], 1e-9)), 2)
    return r


# ---------------------------------------------------------------- figures
def _title(c: Case, lc: fea.LoadCase) -> str:
    return f"{c.name}\n{lc.key} {LC_SHORT.get(lc.key, lc.title)} (y = {lc.y:g})"


def _peak(m: fea.Mesh, key: str, elem_vals: np.ndarray) -> tuple[float, float, float]:
    cen = fea.element_ip_coords(m, key)
    v = np.where(cen[:, 1] >= Y_MIN, elem_vals, -np.inf)
    k = int(np.argmax(v))
    return float(cen[k, 0]), float(cen[k, 1]), float(v[k])


def _ceil(v: float, step: float) -> float:
    return float(np.ceil(v / step) * step)


def fig_deflection(cases: list[Case], out: Path) -> float:
    panels = []
    for c in cases:
        tris, _ = fp.plane_tris(c.m, "TOP", 2, C.thickness / 2)
        used = np.unique(tris) - 1
        for lc, u in zip(fea.LOADS, c.disp):
            uz = np.abs(u[:, 2])
            k = used[int(np.argmax(uz[used]))]
            panels.append(dict(o=c.o, m=c.m, tris=tris, nodal=uz, lc=lc, title=_title(c, lc),
                               peak=(c.m.nodes[k, 0], c.m.nodes[k, 1], uz[k])))
    vmax = _ceil(max(p["peak"][2] for p in panels), 0.5)
    fp.contour_figure(panels, "out-of-plane deflection |u_z|  [mm]", out, cmap="Blues", vmax=vmax, unit="mm",
                      fmt_peak="{:.2f}")
    return vmax


def fig_face_stress(cases: list[Case], out: Path) -> float:
    """Rows: impact (top) face sheet, back (bottom) face sheet; columns: design x load case."""
    rows: list[list[dict]] = [[], []]
    for c in cases:
        for i, lc in enumerate(fea.LOADS):
            for r, (key, z) in enumerate((("TOP", C.thickness / 2), ("BOT", -C.thickness / 2))):
                s = c.stress[i]["E_" + key]
                ev = fp.element_max(c.m, key, s, fp.fibre_stress(s[:, 2:]))
                tris, _ = fp.plane_tris(c.m, key, 2, z)
                rows[r].append(dict(o=c.o, m=c.m, tris=tris, nodal=fp.nodal_average(c.m, key, ev),
                                    lc=lc if key == "TOP" else None, peak=_peak(c.m, key, ev),
                                    title=_title(c, lc) if r == 0 else ""))
    vmax = _ceil(max(p["peak"][2] for r in rows for p in r), 10.0)
    fp.contour_figure(rows, "carbon face sheet: max in-plane fibre stress |σ11|, |σ22|  [MPa]", out, vmax=vmax,
                      extend="max", row_labels=["impact (top) face sheet", "back (bottom) face sheet"])
    return vmax


def fig_bond_shear(cases: list[Case], out: Path) -> float:
    """Shear stress in the bond line between the core lands / frame and each face sheet."""
    rows: list[list[dict]] = [[], []]
    iface_cache = {}
    for c in cases:
        cen = fea.element_ip_coords(c.m, "CORE")
        zc = c.m.nodes[c.m.elems["CORE"][:, :4] - 1, 2]
        iface_cache[c.name] = [np.sum(np.abs(zc - z) < 1e-6, axis=1) >= 3 for z in (C.core_t / 2, -C.core_t / 2)]
        for i, lc in enumerate(fea.LOADS):
            s = c.stress[i]["E_CORE"]
            ev = fp.element_max(c.m, "CORE", s, fp.transverse_shear(s[:, 2:]))
            for r, z in enumerate((C.core_t / 2, -C.core_t / 2)):
                on = iface_cache[c.name][r]
                tris, _ = fp.plane_tris(c.m, "CORE", 2, z)
                pk = _peak(c.m, "CORE", np.where(on & (cen[:, 1] >= Y_MIN), ev, -np.inf))
                rows[r].append(dict(o=c.o, m=c.m, tris=tris, nodal=fp.nodal_average(c.m, "CORE", ev, on),
                                    lc=lc if r == 0 else None, peak=pk, title=_title(c, lc) if r == 0 else ""))
    vmax = _ceil(max(p["peak"][2] for r in rows for p in r), 1.0)
    fp.contour_figure(rows, "bond-line shear stress τ = √(τxz² + τyz²)  [MPa]", out, vmax=vmax, fmt_peak="{:.1f}",
                      extend="max", row_labels=["bond line to impact (top) sheet", "bond line to back (bottom) sheet"])
    return vmax


def fig_bond_profile(profiles: dict[str, dict], out: Path, allowable: float) -> None:
    """Small multiples (one per design): bond shear along the blade for the tip impact."""
    import matplotlib.pyplot as plt
    ink, muted, grid = "#0b0b0b", "#52514e", "#e4e2dc"
    series = (("max", "#2a78d6", 1.0, "max in band"), ("p99", "#eb6834", 2.0, "99th percentile"),
              ("mean", "#1baf7a", 2.0, "mean"))
    fig, axes = plt.subplots(1, len(profiles), figsize=(4.6 * len(profiles), 3.4), sharey=True, squeeze=False)
    for ax, (name, p) in zip(axes[0], profiles.items()):
        ax.axvspan(Y_MIN, C.solid_to, color="#f0efec", lw=0)
        ax.axvspan(C.solid_to, C.solid_to + C.runout_len, color="#e4e2dc", lw=0)
        ax.text((Y_MIN + C.solid_to) / 2, 10.6, "solid\ncore", color=muted, fontsize=7.5, ha="center", va="top")
        for key, col, lw, label in series:
            ax.plot(p["y"], p[key], color=col, lw=lw, label=label)
        ax.axhline(allowable, color=muted, lw=1.0, ls=(0, (4, 3)))
        ax.text(p["y"][-1], allowable + 0.25, f"design allowable {allowable:g} MPa", color=muted, fontsize=8,
                ha="right", va="bottom")
        ax.set_ylim(0, 11)
        ax.set_title(name, fontsize=10, fontweight="bold", color=ink, loc="left")
        ax.set_xlabel("height from butt y  [mm]", color=muted)
        ax.grid(True, color=grid, lw=0.6)
        ax.set_axisbelow(True)
        for sp in ("top", "right"):
            ax.spines[sp].set_visible(False)
        for sp in ("left", "bottom"):
            ax.spines[sp].set_color("#b5b3ac")
        ax.tick_params(colors=muted, labelsize=8)
    axes[0][0].set_ylabel("bond-line shear  [MPa]", color=muted)
    h, lab = axes[0][0].get_legend_handles_labels()
    fig.legend(h, lab, loc="upper right", ncol=3, frameon=False, fontsize=8, bbox_to_anchor=(0.99, 1.0))
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    fig.savefig(out, dpi=200)
    plt.close(fig)


def core_vm_ply(c: Case, i: int, path: Path, vmax: float) -> float:
    """Boundary of the rib core, mirrored to the full paddle, coloured by von Mises stress."""
    s = c.stress[i]["E_CORE"]
    ev = fp.element_max(c.m, "CORE", s, fea.von_mises(s[:, 2:]))
    fp.mirrored_surface_ply(c.m, "CORE", fp.nodal_average(c.m, "CORE", ev), vmax, path)
    return _peak(c.m, "CORE", ev)[2]


# ---------------------------------------------------------------- report (HTML -> PDF)
CSS = """
@page { size: A4; margin: 15mm 16mm 16mm 16mm;
        @bottom-right { content: counter(page); } }
:root { --ink:#0b0b0b; --ink2:#52514e; --muted:#7a7873; --rule:#d9d7d0; --fill:#f4f3ef;
        --good:#0ca30c; --warn:#b07800; --bad:#d03b3b; --accent:#2a78d6; }
html { font-family: Inter, 'DejaVu Sans', sans-serif; font-size: 9.6pt; color: var(--ink); line-height: 1.42; }
body { margin: 0; background: #fff; }
h1 { font-size: 21pt; margin: 2mm 0 1.5mm; letter-spacing: -0.2pt; }
h2 { font-size: 12.5pt; margin: 7mm 0 2mm; padding-top: 2mm; border-top: 1.2pt solid var(--ink); }
h3 { font-size: 10pt; margin: 4mm 0 1.5mm; }
p { margin: 0 0 2.2mm; }
.kicker { font-size: 8pt; letter-spacing: 1.4pt; text-transform: uppercase; color: var(--ink2); }
.sub { color: var(--ink2); margin-bottom: 4mm; }
ul { margin: 0 0 2.5mm; padding-left: 5mm; }
li { margin-bottom: 1.3mm; }
table { border-collapse: collapse; width: 100%; margin: 1.5mm 0 3.5mm; font-size: 8.6pt;
        font-variant-numeric: tabular-nums; }
th, td { padding: 1.2mm 2mm; border-bottom: 0.5pt solid var(--rule); text-align: left; vertical-align: top; }
th { font-weight: 600; color: var(--ink2); border-bottom: 1pt solid var(--ink2); }
td.n, th.n { text-align: right; white-space: nowrap; }
tr.sub td { color: var(--ink2); }
.ok { color: var(--good); font-weight: 600; white-space: nowrap; }
.warn { color: var(--warn); font-weight: 600; white-space: nowrap; }
.bad { color: var(--bad); font-weight: 600; white-space: nowrap; }
figure { margin: 2mm 0 4mm; break-inside: avoid; }
figure img { width: 100%; display: block; }
figcaption { font-size: 8.3pt; color: var(--ink2); margin-top: 1.5mm; }
.note { background: var(--fill); padding: 2.5mm 3.5mm; margin: 2mm 0 3.5mm; font-size: 8.8pt; break-inside: avoid; }
.grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: 5mm; }
.pb { break-before: page; }
.keep { break-inside: avoid; }
table { break-inside: avoid; }
table.mat td:first-child { width: 27%; } table.mat td:nth-child(2) { width: 37%; }
figure.half { width: 78%; margin-left: auto; margin-right: auto; }
.small { font-size: 8.2pt; color: var(--ink2); }
"""


def _f(v: float, nd: int = 1) -> str:
    return f"{v:.{nd}f}"


def _status(rf: float) -> str:
    if rf >= 1.5:
        return f'<span class="ok">✔ RF {rf:.2f}</span>'
    if rf >= 1.0:
        return f'<span class="warn">▲ RF {rf:.2f}</span>'
    return f'<span class="bad">✖ RF {rf:.2f}</span>'


def _rows(rows: list[tuple]) -> str:
    out = []
    for r in rows:
        cls = ' class="sub"' if r[0].startswith("·") else ""
        cells = "".join(f'<td class="n">{c}</td>' if i else f"<td>{c}</td>" for i, c in enumerate(r))
        out.append(f"<tr{cls}>{cells}</tr>")
    return "\n".join(out)


def write_report(ctx: dict, out_html: Path) -> None:
    """ctx: stats {design: {LC: case_stats}}, baseline {LC: case_stats}, mesh {design: {...}},
    modal {design: [Hz]}, mass {key: mass_properties}, figs {name: relative path or None}, date."""
    A = fea.ALLOW
    S, B, M, F = ctx["stats"], ctx["baseline"], ctx["mass"], ctx["figs"]
    names = list(S)                                   # ["ELONGATED", "HYBRID"]
    keys = [k for k in M if k != "grip"]              # ["elongated", "hybrid"]; M["grip"] names the drawn grip
    typical = lambda k: M[k]["mass_g"] / 225.0                                # noqa: E731  vs a 210-240 g paddle
    el, hy = (S[n]["LC2"] for n in names)
    worst = lambda f: max(f(S[n][lc]) for n in names for lc in S[n])          # noqa: E731
    least = lambda f: min(f(S[n][lc]) for n in names for lc in S[n])          # noqa: E731
    faces = {k: M[k]["parts"]["face_sheet_top"]["mass_g"] + M[k]["parts"]["face_sheet_bottom"]["mass_g"] for k in keys}
    f1 = {n: ctx["modal"][n][0] for n in names}
    layer_rf = lambda r: A["core_layer"] / r["core_shear"]["value"]          # noqa: E731
    band_rf = lambda r: A["bond_shear"] / r["bond_shear_stats"]["p99_hot_band"]  # noqa: E731
    peel_rf = lambda r: A["bond_peel"] / r["bond_peel"]["value"]              # noqa: E731
    shear_rf = lambda r: A["bond_shear"] / r["bond_shear"]["value"]           # noqa: E731
    lc1, lc2 = fea.LOADS

    summary = _rows([
        ("Deflection, sweet spot / tip impact", *(f'{_f(S[n]["LC1"]["max_deflection"]["value"], 2)} / '
                                                  f'{_f(S[n]["LC2"]["max_deflection"]["value"], 2)} mm' for n in names), "—"),
        ("Carbon face sheets, max fibre stress", *(f'{_f(S[n]["LC2"]["cf_fibre"]["value"], 0)} MPa' for n in names),
         _status(least(lambda r: r["rf"]["cf"]))),
        ("Printed core, von Mises", *(f'{_f(S[n]["LC2"]["core_vm"]["value"])} MPa' for n in names),
         _status(least(lambda r: r["rf"]["core"]))),
        ("Printed core, shear across the print layers", *(f'{_f(S[n]["LC2"]["core_shear"]["value"])} MPa'
                                                          for n in names), _status(least(layer_rf))),
        ("Bond line, peel (tension)", *(f'{_f(S[n]["LC2"]["bond_peel"]["value"])} MPa' for n in names),
         _status(least(peel_rf))),
        ("Bond line, shear: 99th percentile in the hot band", *(f'{_f(S[n]["LC2"]["bond_shear_stats"]["p99_hot_band"])} MPa'
                                                                for n in names), _status(least(band_rf))),
        ("Bond line, shear: local peak", *(f'{_f(S[n]["LC2"]["bond_shear"]["value"])} MPa' for n in names),
         _status(least(shear_rf))),
        ("First bending mode (grip held)", *(f"{f1[n]:.0f} Hz" for n in names), "—"),
        ("Mass", *(f'{M[k]["mass_g"]:.0f} g' for k in keys),
         f'<span class="warn">▲ {min(map(typical, keys)):.1f}–{max(map(typical, keys)):.1f} × typical</span>'),
    ])

    def detail(r1, r2, h1, h2):
        def v(r, k, nd=1):
            return _f(r[k]["value"], nd)
        rows = [("Max deflection [mm]", "—", *(_f(r["max_deflection"]["value"], 2) for r in (r1, r2, h1, h2))),
                ("Carbon: fibre stress |σ11|, |σ22| [MPa]", f'{A["cf_t"]:g} t / {A["cf_c"]:g} c',
                 *(v(r, "cf_fibre", 0) for r in (r1, r2, h1, h2))),
                ("Carbon: in-plane shear τ12 [MPa]", f'{A["cf_s"]:g}', *(v(r, "cf_inplane_shear") for r in (r1, r2, h1, h2))),
                ("Carbon: interlaminar shear [MPa]", f'{A["cf_ilss"]:g}',
                 *(v(r, "cf_interlaminar_shear") for r in (r1, r2, h1, h2))),
                ("Carbon: max-stress failure index", "1.00", *(v(r, "cf_failure_index", 2) for r in (r1, r2, h1, h2))),
                ("· carbon fibre stress at the clamp edge (not assessed)", "", *(_f(r["cf_fibre_at_clamp_edge"], 0)
                                                                              for r in (r1, r2, h1, h2))),
                ("Core: von Mises [MPa]", f'{A["core_vm"]:g}', *(v(r, "core_vm") for r in (r1, r2, h1, h2))),
                ("Core: through-thickness compression under the ball [MPa]", f'{A["core_vm"]:g}',
                 *(v(r, "core_crush") for r in (r1, r2, h1, h2))),
                ("Core: shear across the print layers √(τxz²+τyz²) [MPa]", f'{A["core_layer"]:g}',
                 *(v(r, "core_shear") for r in (r1, r2, h1, h2))),
                ("Bond: shear, local peak [MPa]", f'{A["bond_shear"]:g}', *(v(r, "bond_shear") for r in (r1, r2, h1, h2))),
                ("· at height y [mm]", "", *(f'{r["bond_shear"]["at"][1]:.0f}' for r in (r1, r2, h1, h2))),
                ("Bond: shear, 99th percentile in the 10 mm band at the peak [MPa]", f'{A["bond_shear"]:g}',
                 *(_f(r["bond_shear_stats"]["p99_hot_band"]) for r in (r1, r2, h1, h2))),
                ("Bond: shear, mean over the whole bond [MPa]", "", *(_f(r["bond_shear_stats"]["mean_all"], 2)
                                                                     for r in (r1, r2, h1, h2))),
                ("Bond: peel, local peak [MPa]", f'{A["bond_peel"]:g}', *(v(r, "bond_peel") for r in (r1, r2, h1, h2))),
                ("Bond: peel, 99th percentile in the band at the peak [MPa]", f'{A["bond_peel"]:g}',
                 *(_f(r["bond_peel_stats"]["p99_hot_band"]) for r in (r1, r2, h1, h2)))]
        return _rows(rows)

    b2 = B["LC2"]
    e2 = S[names[0]]["LC2"]
    iteration = _rows([
        ("Bond peel, local peak", f'{_f(b2["bond_peel"]["value"])} MPa at y = {b2["bond_peel"]["at"][1]:.0f}',
         f'{_f(e2["bond_peel"]["value"])} MPa at y = {e2["bond_peel"]["at"][1]:.0f}'),
        ("Bond peel, 99th percentile in the band at the peak", f'{_f(b2["bond_peel_stats"]["p99_hot_band"])} MPa',
         f'{_f(e2["bond_peel_stats"]["p99_hot_band"])} MPa'),
        ("Bond shear, local peak", f'{_f(b2["bond_shear"]["value"])} MPa at y = {b2["bond_shear"]["at"][1]:.0f}',
         f'{_f(e2["bond_shear"]["value"])} MPa at y = {e2["bond_shear"]["at"][1]:.0f}'),
        ("Bond shear, 99th percentile in the band at the peak", f'{_f(b2["bond_shear_stats"]["p99_hot_band"])} MPa',
         f'{_f(e2["bond_shear_stats"]["p99_hot_band"])} MPa'),
        ("Bond reserve factor, local peaks (shear and peel)", _status(b2["rf"]["bond"]), _status(e2["rf"]["bond"])),
        ("Bond reserve factor, 99th percentile in the band", _status(b2["rf"]["bond_hot_band"]),
         _status(e2["rf"]["bond_hot_band"])),
        ("Core von Mises", f'{_f(b2["core_vm"]["value"])} MPa', f'{_f(e2["core_vm"]["value"])} MPa'),
        ("Carbon fibre stress", f'{_f(b2["cf_fibre"]["value"], 0)} MPa', f'{_f(e2["cf_fibre"]["value"], 0)} MPa'),
        ("Tip deflection", f'{_f(b2["max_deflection"]["value"], 2)} mm', f'{_f(e2["max_deflection"]["value"], 2)} mm'),
    ])

    parts = ("face_sheet_top", "rib_core", "face_sheet_bottom", "grip", "screw_M3x12_DIN7984", "insert_M3_heatset")
    grip = M.get("grip", {}).get("name", "rev 8").title()
    labels = {"face_sheet_top": "Carbon face sheet, top (4 mm)", "rib_core": "Wave-rib core with frame (PA-CF)",
              "face_sheet_bottom": "Carbon face sheet, bottom (4 mm)", "grip": f"Printed grip, PLA ({grip})",
              "screw_M3x12_DIN7984": "Screw DIN 7984 M3 × 12", "insert_M3_heatset": "Heat-set insert M3 (brass)"}
    mass_rows = _rows([(labels[p], *(f'{M[k]["parts"][p]["mass_g"]:.1f} g' for k in keys)) for p in parts] + [
        ("<b>Total</b>", *(f'<b>{M[k]["mass_g"]:.0f} g</b>' for k in keys)),
        ("Balance point from the butt", *(f'{M[k]["balance_mm"]:.0f} mm' for k in keys)),
        ("Swing weight about a pivot 100 mm from the butt", *(f'{M[k]["swing_weight_kgcm2"]:.0f} kg·cm²' for k in keys))])

    mesh = ctx["mesh"]
    mesh_rows = _rows([(n, f'{mesh[n]["n_nodes"]:,}', f'{mesh[n]["n_elems"]:,}', f'{3 * mesh[n]["n_nodes"]:,}',
                        f'{mesh[n]["patch_area"]:.0f} mm²') for n in names])

    def fig(key: str, caption: str, cls: str = "") -> str:
        if not F.get(key):
            return ""
        return f'<figure class="{cls}"><img src="{F[key]}"><figcaption>{caption}</figcaption></figure>'

    lay = C
    html_doc = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>Structural analysis – wave-rib sandwich paddles</title><style>{CSS}</style></head><body>

<div class="kicker">Structural analysis · REV C · {ctx["date"]}</div>
<h1>Wave-rib sandwich pickleball paddles</h1>
<p class="sub">PB-EL-001 Elongated (390 × 200 × 16 mm) and PB-HY-001 Hybrid (390 × 190 × 16 mm).
Linear static and modal finite-element analysis.</p>

<h2>1 Summary</h2>
<p>Both paddles were analysed as a {lay.face_t:g} mm carbon / {lay.core_t:g} mm printed wave-rib / {lay.face_t:g} mm carbon
sandwich. Each was held at the grip and loaded by a {lc1.force:.0f} N ball impact, first at the sweet spot
(y = {lc1.y:g} mm from the butt) and then at the tip (y = {lc2.y:g} mm). The tip impact is the worst case for
every quantity.</p>
<ul>
<li><b>The carbon face sheets and the printed core have large margins.</b> The carbon reaches at most
{worst(lambda r: r["cf_fibre"]["value"]):.0f} MPa (reserve factor ≥ {least(lambda r: r["rf"]["cf"]):.1f}). The core reaches
{worst(lambda r: r["core_vm"]["value"]):.1f} MPa von Mises (RF ≥ {least(lambda r: r["rf"]["core"]):.1f}). The highest
face-sheet stress is in the throat, where the 30 mm handle widens into the blade.</li>
<li><b>The adhesive bond between the core and the carbon is the critical item.</b> Bond shear peaks at
{worst(lambda r: r["bond_shear"]["value"]):.1f} MPa on the centre lands, 15–30 mm above the solid part of the core. Across
that band the 99th-percentile value is {worst(lambda r: r["bond_shear_stats"]["p99_hot_band"]):.1f} MPa. Against the
{A["bond_shear"]:g} MPa allowable assumed for an epoxy bond to printed PA-CF, the band passes
(RF {least(band_rf):.2f}) but the local peaks do not (RF {least(shear_rf):.2f}). §5 and §7 cover the cause and the fixes.</li>
<li><b>Stiffness.</b> Under {lc1.force:.0f} N the blade deflects {el["max_deflection"]["value"]:.1f} mm for a tip
impact and {S[names[0]]["LC1"]["max_deflection"]["value"]:.1f} mm at the sweet spot. With the grip held, the first
bending mode is {f1[names[0]]:.0f} Hz (Elongated) and {f1[names[1]]:.0f} Hz (Hybrid).</li>
<li><b>Weight.</b> The Elongated paddle weighs {M[keys[0]]["mass_g"]:.0f} g and the Hybrid {M[keys[1]]["mass_g"]:.0f} g,
about {typical(keys[0]):.1f} and {typical(keys[1]):.1f} times a typical 210–240 g paddle. The two 4 mm carbon sheets alone weigh {faces[keys[0]]:.0f} g /
{faces[keys[1]]:.0f} g. §6 has the breakdown.</li>
</ul>
<table><tr><th>Worst case (tip impact, {lc2.force:.0f} N)</th><th class="n">{names[0].title()}</th>
<th class="n">{names[1].title()}</th><th class="n">Status (both)</th></tr>
{summary}</table>
<p class="small">Reserve factor RF = allowable ÷ calculated stress; RF ≥ 1 passes. ✔ means RF ≥ 1.5,
▲ means 1.0–1.5 and ✖ means below 1. The carbon RF uses the max-stress failure index (RF = 1 / index).</p>

<h2>2 Construction analysed</h2>
<ul>
<li><b>Face sheets.</b> Woven carbon/epoxy plates, {lay.face_t:g} mm thick. Top and bottom are identical and cover
the full outline, blade and handle.</li>
<li><b>Core.</b> {lay.core_t:g} mm high, 3D-printed in PA-CF (carbon-filled nylon), printed flat. A closed
{lay.frame_w:g} mm perimeter frame covers the whole edge. Inside it is a sinusoidal wave rib: pitch {lay.rib_pitch:g} mm,
wall {lay.rib_t:g} mm, amplitude {lay.rib_amp:g} mm. The flutes run along the paddle. The crests are cut flat
where they meet the sheets, which gives bond lands {wave.land_width():.2f} mm wide.</li>
<li><b>Solid zone.</b> The core is solid from the butt to y = {lay.solid_to:g} mm (handle and throat). Each flute
starts with a 45° run-out, {lay.runout_len:g} mm long, which prints without support. The butt end holds an M3 heat-set
insert for the grip screw.</li>
<li><b>Grip.</b> A printed PLA grip ({grip} drawn; any of the ten rev-8 designs fits) slides over the handle:
{GRIP.length:g} mm long, slot {GRIP.slot_w:g} × {GRIP.slot_t:g} mm, solid {GRIP.base:g} mm base. A DIN 7984 M3 × 12 screw
through the base into the insert holds it on. The grip is not load-carrying in this model. The hand is
represented by a clamp (§3).</li>
<li><b>Revision C.</b> The printed grip replaced the REV B sleeve, wrap, collar and butt cap, and the insert
changed from M4 to M3. The body now starts {GRIP.base:g} mm above the butt, on the grip base, instead of 4 mm. All of
this sits below or inside the clamped band (y = {fea.GRIP_Y[0]:g}–{fea.GRIP_Y[1]:g} mm), which carries no assessed
stress, so the stress and modal results stand and the cases were not re-solved. The masses in §6 are REV C.</li>
</ul>
{fig("cutaway", "Cutaway render: the top sheet and the core are cut back to show the wave rib between the sheets.", "half")}

<div class="keep"><h2>3 Finite-element model</h2>
<ul>
<li><b>Geometry.</b> Half model, symmetric about the centre line. Top sheet, core and bottom sheet are meshed
together, so the bond is perfect and shares nodes. The core is modelled exactly as drawn: frame, solid zone,
run-outs, wave walls and lands.</li>
</ul></div><ul>
<li><b>Mesh.</b> 10-node quadratic tetrahedra (C3D10). Element size is 1.6 mm in the core, which puts at least two
elements through every wave wall, and 3.5 mm in the sheets. Meshed in gmsh, solved in CalculiX 2.21.</li>
<li><b>Support.</b> The outer surfaces of the handle from y = {fea.GRIP_Y[0]:g} to {fea.GRIP_Y[1]:g} mm are fixed,
which stands in for the hand on the grip. Next to a rigid clamp the stresses are artificially high, so results
closer than 8 mm to its edge (y &lt; {Y_MIN:g} mm) are not assessed. Table 2 lists them for reference.</li>
<li><b>Load.</b> {lc1.force:.0f} N spread uniformly over a Ø{lc1.diameter:g} mm patch (the ball contact) on the top
sheet, at LC1 (x = 0, y = {lc1.y:g}) or LC2 (x = 0, y = {lc2.y:g}). The load is applied as a static peak force. A
26 g ball that changes speed by about 33 m/s during a 4 ms contact gives about 215 N on average and about 340 N
peak. The 500 N used is about 1.5 times that, to cover harder hits and some dynamic amplification.</li>
<li><b>Modal.</b> Natural frequencies with the same grip support, on a coarser 3 / 5 mm mesh.</li>
</ul>
<table><tr><th>Model</th><th class="n">Nodes</th><th class="n">Elements</th><th class="n">Degrees of freedom</th>
<th class="n">Load patch area (half)</th></tr>{mesh_rows}</table>
<h3>Materials and allowables</h3>
<table class="mat"><tr><th>Material</th><th>Stiffness</th><th>Allowables (design values)</th></tr>
<tr><td>Woven carbon/epoxy plate<br><span class="small">0/90 fabric, ρ = {fea.CF["rho"] * 1e9:.2f} g/cm³</span></td>
<td>E₁ = E₂ = {fea.CF["E1"] / 1000:g} GPa, E₃ = {fea.CF["E3"] / 1000:g} GPa<br>G₁₂ = {fea.CF["G12"] / 1000:g} GPa,
G₁₃ = G₂₃ = {fea.CF["G13"] / 1000:g} GPa<br>ν₁₂ = {fea.CF["nu12"]:g}, ν₁₃ = ν₂₃ = {fea.CF["nu13"]:g}</td>
<td>Tension {A["cf_t"]:g} MPa, compression {A["cf_c"]:g} MPa<br>In-plane shear {A["cf_s"]:g} MPa<br>
Interlaminar shear {A["cf_ilss"]:g} MPa</td></tr>
<tr><td>Printed PA-CF core<br><span class="small">solid walls, ρ = {fea.CORE["rho"] * 1e9:.2f} g/cm³</span></td>
<td>E = {fea.CORE["E"] / 1000:g} GPa, ν = {fea.CORE["nu"]:g}<br>(isotropic)</td>
<td>von Mises {A["core_vm"]:g} MPa<br>Across the print layers {A["core_layer"]:g} MPa</td></tr>
<tr><td>Epoxy bond, carbon to printed core</td><td>— (perfect bond)</td>
<td>Shear {A["bond_shear"]:g} MPa, peel {A["bond_peel"]:g} MPa<br><span class="small">Conservative values for abraded and
primed nylon. Confirm them by coupon tests (§7).</span></td></tr></table>
<p class="small">These are typical design values, not supplier data. When the actual carbon plate, filament
and adhesive are chosen, replace them with the supplier's values. Every reserve factor scales directly
with its allowable.</p>

<div class="keep"><h2>4 Results</h2>
{fig("deflection", "Fig. 1 – Out-of-plane deflection under 500 N. Dashed circle: ball contact patch. Hatched: grip clamp.")}
</div>
<table><tr><th>Table 2 – all results</th><th class="n">Allowable</th><th class="n">{names[0].title()} LC1</th>
<th class="n">{names[0].title()} LC2</th><th class="n">{names[1].title()} LC1</th><th class="n">{names[1].title()} LC2</th></tr>
{detail(S[names[0]]["LC1"], S[names[0]]["LC2"], S[names[1]]["LC1"], S[names[1]]["LC2"])}</table>
{fig("face", "Fig. 2 – Carbon face sheets, largest in-plane fibre stress. The stress concentrates in the throat; "
     "the colour scale saturates at the clamp edge, which is not assessed.")}
{fig("bond", f"Fig. 3 – Shear stress in the bond line, plotted on the core's bonded surfaces: the {lay.frame_w:g} mm "
     f"frame, the solid zone and the {wave.land_width():.2f} mm lands. White stripes are the open flutes.")}
{fig("profile", f"Fig. 4 – Bond shear along the paddle for the tip impact, in 5 mm bands: largest value, 99th "
     f"percentile and mean. Shaded: solid core and the {lay.runout_len:g} mm run-out.")}
{fig("core", "Fig. 5 – Printed core coloured by von Mises stress for the tip impact, top sheet removed. "
     "Left: Elongated, right: Hybrid.")}

<div class="keep"><h2>5 Design iteration: flute ends and land width</h2>
<p>The first version of the core had square flute ends at y = {lay.solid_to:g} mm and lands {wave.land_width(B_AMP):.2f} mm wide (amplitude
{B_AMP:g} mm). Its bond peeled at the step where each flute starts: {_f(b2["bond_peel"]["value"])} MPa against a
{A["bond_peel"]:g} MPa allowable. The final core starts each flute with a 45° run-out, so the core meets the sheet in a
thin wedge instead of a step. Its amplitude is {lay.rib_amp:g} mm, which widens the lands to {wave.land_width():.2f} mm. Elongated, tip impact:</p>
<table><tr><th></th><th class="n">First version</th><th class="n">Final</th></tr>{iteration}</table></div>
<p>The peel peak has gone. The shear peaks now sit on the centre lands just above the solid zone. There the shear
from the whole blade funnels into the 30 mm wide throat. With the wider lands, the wall under each land is
thinner ({wave.under_land_wall():.1f} mm instead of {wave.under_land_wall(B_AMP):.1f} mm), which sharpens those local
peaks. Across that band the 99th-percentile level rose a little, from {_f(b2["bond_shear_stats"]["p99_hot_band"])} to
{_f(e2["bond_shear_stats"]["p99_hot_band"])} MPa. Fig. 4 shows the peaks are narrow spikes and that the 99th-percentile
line stays below the allowable along the whole blade. Spikes like these depend on the mesh
and on the sharp corner where the wall meets the sheet. In the real part, the adhesive fillet at the land edge
rounds that corner off.</p>

<div class="keep"><h2>6 Mass, balance and swing weight</h2>
<table><tr><th>Part (from the CAD model)</th><th class="n">{names[0].title()}</th><th class="n">{names[1].title()}</th></tr>
{mass_rows}</table></div>
<p>A typical competition paddle weighs 210–240 g (7.5–8.5 oz). Its swing weight is roughly 100–130 kg·cm² about
the same pivot. These paddles are about {typical(keys[0]):.1f} and {typical(keys[1]):.1f} times as heavy and about twice the swing weight. The 4 mm carbon
sheets make up {100 * faces[keys[0]] / M[keys[0]]["mass_g"]:.0f} % of the mass. The printed core weighs
{M[keys[0]]["parts"]["rib_core"]["mass_g"]:.0f} g, an effective density of about
{M[keys[0]]["parts"]["rib_core"]["mass_g"] / M[keys[0]]["parts"]["face_sheet_top"]["volume_cm3"] * lay.face_t / lay.core_t * 1000:.0f} kg/m³.
A polypropylene honeycomb core is typically 80–120 kg/m³. The margins in §4 show how much strength there is to
give up.</p>

<div class="keep"><h2>7 Recommendations</h2>
<h3>Bond line (before the first build)</h3>
<ul>
<li>Use a toughened structural epoxy or MMA adhesive that is rated for nylons. Abrade both surfaces, then
clean and prime them as the adhesive supplier specifies. Leave a small fillet of adhesive along every land edge.</li>
<li>Test single-lap shear coupons of carbon plate bonded to printed PA-CF (ISO 4587 / ASTM D1002 layout) and
flatwise-tension coupons (ASTM C297). Use the measured strengths as the bond allowables in this analysis.</li>
<li>If the coupons give less than about 12 MPa in shear, lower the peak at the start of the wave. Either thicken
the wall under the centre lands (wall 2.0 mm instead of 1.6 mm), or extend the solid zone up the centre of the
blade by about 30 mm, then re-run the analysis.</li>
</ul></div>
<h3>Weight</h3>
<ul>
<li>For a playable paddle, the sheets and the core both need to be much lighter. One option is 0.5–1.0 mm
carbon sheets on a 14–15 mm core of honeycomb, foam or a much thinner-walled print, which keeps the 16 mm
thickness. Because a sandwich gets its bending stiffness from the distance between the sheets, thin sheets
on a thicker core can stay stiff. All the geometry is parametric (paddle/geometry.py), so a lighter lay-up can
be re-analysed with the same tools.</li>
<li>If the 4/8/4 build is meant as a prototype or a training paddle, the structure as analysed is strong
enough. The bond line is the only item to qualify.</li>
</ul>
<h3>Validation on the first parts</h3>
<ul>
<li>Static stiffness check: clamp the grip and hang a known load at the tip. The analysis predicts
{el["max_deflection"]["value"] / lc2.force * 100:.2f} mm per 100 N at y = {lc2.y:g} mm for the Elongated and
{hy["max_deflection"]["value"] / lc2.force * 100:.2f} mm per 100 N for the Hybrid.</li>
<li>Tap test: the first bending mode should ring at about {f1[names[0]]:.0f} Hz (Elongated) and {f1[names[1]]:.0f} Hz
(Hybrid), with the handle held firmly.</li>
<li>Check for bond-line voids (tap or ultrasound) and for cracks at the throat after impact tests.</li>
</ul>

<h2 class="keep">8 Assumptions and limitations</h2>
<ul class="small">
<li>Linear elastic, small deflection, quasi-static peak load. No fatigue, no damage growth, no strain-rate effects.</li>
<li>The bond is perfect. The adhesive layer is not modelled; bond stresses are read in the core elements next to
each sheet.</li>
<li>The printed core is treated as isotropic and fully dense. Real prints are weaker and softer across the layers
(covered by the separate {A["core_layer"]:g} MPa allowable) and depend on the print settings.</li>
<li>The grip is a rigid clamp. A real hand and grip are softer, which lowers the stress at the throat slightly
and raises the deflection slightly. Edge guard, paint and grip parts are not modelled.</li>
<li>Peak values at sharp re-entrant corners depend on the mesh. Percentile and band values (Fig. 4) are the
robust measures.</li>
</ul>
</body></html>"""
    out_html.write_text(html_doc, encoding="utf-8")
