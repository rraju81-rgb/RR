"""Linear-elastic finite-element stress analysis of the sandwich paddle (gmsh + CalculiX).

Half model (x >= 0, symmetry plane x = 0) of the two carbon-fibre face sheets and the
wave-rib core, meshed conformally with quadratic tetrahedra (C3D10).  The hand grip
is modelled as a rigid clamp over the handle; ball impacts are quasi-static pressure
patches.  Units: mm, N, MPa, tonne/mm^3.
"""
from __future__ import annotations

import json
import math
import os
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from .geometry import CONSTRUCTION as C
from .geometry import Outline

# --------------------------------------------------------------------------- materials / allowables
CF = dict(E1=60000.0, E2=60000.0, E3=8000.0, nu12=0.05, nu13=0.30, nu23=0.30,
          G12=4500.0, G13=3500.0, G23=3500.0, rho=1.55e-9)          # woven CF/epoxy plate
CORE = dict(E=4000.0, nu=0.35, rho=1.18e-9)                        # 3D-printed PA-CF, 100 % infill
ALLOW = dict(cf_t=600.0, cf_c=500.0, cf_s=90.0, cf_ilss=55.0,      # CF plate strengths [MPa]
             core_vm=45.0, core_layer=25.0,                         # printed core: von Mises / inter-layer
             bond_shear=8.0, bond_peel=5.0)                         # epoxy bond CF <-> printed core


@dataclass
class LoadCase:
    key: str
    title: str
    force: float          # N, total on the full paddle
    x: float
    y: float
    diameter: float = 30.0


LOADS = [LoadCase("LC1", "Sweet-spot ball impact", 500.0, 0.0, 265.0),
         LoadCase("LC2", "Tip ball impact", 500.0, 0.0, 345.0)]
GRIP_Y = (14.0, 112.0)        # hand-grip clamp band on the handle


@dataclass
class Mesh:
    nodes: np.ndarray                     # (N, 3) coordinates, node id = index + 1
    elems: dict[str, np.ndarray]          # set name -> (M, 10) node ids (Abaqus C3D10 order), 1-based
    eids: dict[str, np.ndarray] = field(default_factory=dict)


# --------------------------------------------------------------------------- geometry + mesh
def half_model_step(o: Outline, path: Path) -> None:
    from build123d import Box, Compound, Pos, export_step

    from . import cad
    half = Pos(250, 200, 0) * Box(500, 500, 100)
    top = cad.face_sheet(o, True, edge_r=0) & half
    core = cad.rib_core(o, with_hole=False) & half
    bot = cad.face_sheet(o, False, edge_r=0) & half
    export_step(Compound(children=[top, core, bot]), str(path))


def mesh_half_model(step: Path, h_core: float = 1.6, h_plate: float = 3.5) -> Mesh:
    import gmsh
    gmsh.initialize()
    gmsh.option.setNumber("General.Terminal", 0)
    gmsh.model.occ.importShapes(str(step))
    gmsh.model.occ.synchronize()
    vols = gmsh.model.getEntities(3)
    gmsh.model.occ.fragment([vols[0]], vols[1:])
    gmsh.model.occ.synchronize()
    groups: dict[str, list[int]] = {"CORE": [], "TOP": [], "BOT": []}
    for d, tag in gmsh.model.getEntities(3):
        z0, z1 = gmsh.model.getBoundingBox(d, tag)[2], gmsh.model.getBoundingBox(d, tag)[5]
        key = "CORE" if z0 > -C.core_t / 2 - 1e-3 and z1 < C.core_t / 2 + 1e-3 else ("TOP" if z0 > 0 else "BOT")
        groups[key].append(tag)
    fields = []
    for tags, h in ((groups["CORE"], h_core), (groups["TOP"] + groups["BOT"], h_plate)):
        fid = gmsh.model.mesh.field.add("Constant")
        gmsh.model.mesh.field.setNumbers(fid, "VolumesList", tags)
        gmsh.model.mesh.field.setNumber(fid, "VIn", h)
        gmsh.model.mesh.field.setNumber(fid, "VOut", 1e3)
        fields.append(fid)
    fmin = gmsh.model.mesh.field.add("Min")
    gmsh.model.mesh.field.setNumbers(fmin, "FieldsList", fields)
    gmsh.model.mesh.field.setAsBackgroundMesh(fmin)
    for k, v in (("Mesh.MeshSizeExtendFromBoundary", 0), ("Mesh.MeshSizeFromPoints", 0),
                 ("Mesh.MeshSizeFromCurvature", 0), ("Mesh.Algorithm", 6), ("Mesh.Algorithm3D", 10),
                 ("General.NumThreads", 4), ("Mesh.ElementOrder", 2), ("Mesh.SecondOrderLinear", 1)):
        gmsh.option.setNumber(k, v)
    gmsh.model.mesh.generate(3)
    tags, coords, _ = gmsh.model.mesh.getNodes()
    order = np.argsort(tags)
    tags = tags[order]
    xyz = coords.reshape(-1, 3)[order]
    remap = np.zeros(int(tags.max()) + 1, dtype=np.int64)
    remap[tags.astype(np.int64)] = np.arange(1, len(tags) + 1)
    elems = {}
    for key, vtags in groups.items():
        conn = []
        for t in vtags:
            etypes, _, enodes = gmsh.model.mesh.getElements(3, t)
            for et, en in zip(etypes, enodes):
                assert et == 11, "expected 10-node tetrahedra"
                conn.append(en.reshape(-1, 10).astype(np.int64))
        c = remap[np.vstack(conn)]
        elems[key] = c[:, [0, 1, 2, 3, 4, 5, 6, 7, 9, 8]]          # gmsh -> Abaqus/CalculiX node order
    gmsh.finalize()
    m = Mesh(xyz, elems)
    start = 1
    for key in ("TOP", "CORE", "BOT"):
        m.eids[key] = np.arange(start, start + len(elems[key]))
        start += len(elems[key])
    return m


# --------------------------------------------------------------------------- CalculiX input
FACES = ((0, 1, 2), (0, 3, 1), (1, 3, 2), (2, 3, 0))       # C3D10 faces S1..S4 (corner nodes, 0-based)


def patch_faces(m: Mesh, lc: LoadCase, z: float) -> tuple[list[tuple[int, int]], float]:
    """(element id, face number) of top-sheet faces on plane z inside the impact patch, and their area."""
    out = []
    area = 0.0
    conn, ids = m.elems["TOP"], m.eids["TOP"]
    P = m.nodes
    r = lc.diameter / 2
    for e, c in zip(ids, conn):
        for k, f in enumerate(FACES, 1):
            q = P[c[list(f)] - 1]
            if np.all(np.abs(q[:, 2] - z) < 1e-6):
                cen = q.mean(axis=0)
                if math.hypot(cen[0] - lc.x, cen[1] - lc.y) <= r:
                    out.append((int(e), k))
                    area += 0.5 * np.linalg.norm(np.cross(q[1] - q[0], q[2] - q[0]))
    return out, area


def clamp_nodes(m: Mesh, o: Outline) -> np.ndarray:
    P = m.nodes
    h = o.spec.handle_width / 2
    t2 = C.thickness / 2
    on_surf = (np.abs(np.abs(P[:, 2]) - t2) < 1e-6) | (np.abs(P[:, 0] - h) < 1e-6)
    band = (P[:, 1] >= GRIP_Y[0]) & (P[:, 1] <= GRIP_Y[1]) & (P[:, 0] <= h + 1e-6)
    return np.nonzero(on_surf & band)[0] + 1


def write_inp(m: Mesh, o: Outline, path: Path, loads=LOADS, modes: int = 6) -> dict:
    P = m.nodes
    lines = ["*HEADING", f"Paddle {o.spec.name} sandwich half model (x>=0)", "*NODE"]
    lines += [f"{i},{x:.6f},{y:.6f},{z:.6f}" for i, (x, y, z) in enumerate(P, 1)]
    for key in ("TOP", "CORE", "BOT"):
        lines.append(f"*ELEMENT, TYPE=C3D10, ELSET=E_{key}")
        lines += [",".join(str(v) for v in (e, *c)) for e, c in zip(m.eids[key], m.elems[key])]
    lines += ["*ELSET, ELSET=E_PLATES", "E_TOP, E_BOT"]
    sym = np.nonzero(np.abs(P[:, 0]) < 1e-6)[0] + 1
    clamp = clamp_nodes(m, o)
    for name, ids in (("N_SYM", sym), ("N_CLAMP", clamp)):
        lines.append(f"*NSET, NSET={name}")
        lines += [",".join(str(v) for v in ids[i:i + 16]) for i in range(0, len(ids), 16)]
    info = {"n_nodes": len(P), "n_elems": int(sum(len(v) for v in m.elems.values())),
            "n_sym": int(len(sym)), "n_clamp": int(len(clamp)), "patches": {}}
    pressure = {}
    for lc in loads:
        faces, area = patch_faces(m, lc, C.thickness / 2)
        on_axis = abs(lc.x) < 1e-9                                   # patch cut by the symmetry plane
        pressure[lc.key] = (lc.force / 2 if on_axis else lc.force) / area   # exact total force on the model
        info["patches"][lc.key] = dict(faces=len(faces), area=area, pressure=pressure[lc.key])
        lines.append(f"*SURFACE, NAME=S_{lc.key}, TYPE=ELEMENT")
        lines += [f"{e},S{k}" for e, k in faces]
    c = CF
    lines += ["*MATERIAL, NAME=CF_PLATE", "*ELASTIC, TYPE=ENGINEERING CONSTANTS",
              f"{c['E1']},{c['E2']},{c['E3']},{c['nu12']},{c['nu13']},{c['nu23']},{c['G12']},{c['G13']},",
              f"{c['G23']},0.0", "*DENSITY", f"{c['rho']:.4e}",
              "*MATERIAL, NAME=CORE_PACF", "*ELASTIC", f"{CORE['E']},{CORE['nu']}", "*DENSITY", f"{CORE['rho']:.4e}",
              "*SOLID SECTION, ELSET=E_PLATES, MATERIAL=CF_PLATE",
              "*SOLID SECTION, ELSET=E_CORE, MATERIAL=CORE_PACF",
              "*BOUNDARY", "N_SYM,1,1,0.0", "N_CLAMP,1,3,0.0"]
    for i, lc in enumerate(loads):
        lines += ["*STEP", "*STATIC", f"*DSLOAD{', OP=NEW' if i else ''}", f"S_{lc.key},P,{pressure[lc.key]:.6f}",
                  "*NODE FILE", "U", "*EL FILE", "S",
                  "*EL PRINT, ELSET=E_TOP", "S", "*EL PRINT, ELSET=E_CORE", "S", "*EL PRINT, ELSET=E_BOT", "S",
                  "*NODE PRINT, NSET=N_CLAMP, TOTALS=ONLY", "RF", "*END STEP"]
    if modes:
        lines += ["*STEP", "*FREQUENCY", f"{modes}", "*NODE FILE", "U", "*END STEP"]
    path.write_text("\n".join(lines) + "\n")
    return info


def run_ccx(inp: Path, threads: int = 4) -> tuple[float, float]:
    import time
    env = dict(os.environ, OMP_NUM_THREADS=str(threads), CCX_NPROC_EQUATION_SOLVER=str(threads),
               CCX_NPROC_STIFFNESS=str(threads), CCX_NPROC_RESULTS=str(threads))
    t0 = time.time()
    r = subprocess.run(["ccx", "-i", inp.with_suffix("").name], cwd=inp.parent, env=env,
                       capture_output=True, text=True)
    (inp.parent / "ccx.log").write_text(r.stdout + r.stderr)
    if r.returncode != 0 or "ERROR" in r.stdout:
        raise RuntimeError("ccx failed, see " + str(inp.parent / "ccx.log"))
    import resource
    peak_mb = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss / 1024
    return time.time() - t0, peak_mb


# --------------------------------------------------------------------------- results
_NUM = re.compile(r"[-+]?\d*\.\d+(?:[EeDd][-+]?\d+)?|[-+]?\d+(?:[EeDd][-+]?\d+)?")


def read_dat_stresses(dat: Path) -> list[dict[str, np.ndarray]]:
    """Integration-point stresses per step: [{set: array(rows: elem, ip, sxx, syy, szz, sxy, sxz, syz)}]."""
    steps: list[dict[str, list]] = []
    cur = None
    with open(dat) as fh:
        for line in fh:
            if line.lstrip().startswith("stresses"):
                mset = re.search(r"for set (\S+) and time", line)
                name = mset.group(1)
                if not steps or name in steps[-1]:
                    steps.append({})
                steps[-1][name] = []
                cur = steps[-1][name]
                continue
            if cur is None:
                continue
            s = line.split()
            if len(s) == 8:
                try:
                    cur.append([float(v) for v in s])
                except ValueError:
                    cur = None
            elif s:
                cur = None
    return [{k: np.array(v) for k, v in st.items()} for st in steps]


def read_frd_displacements(frd: Path) -> list[np.ndarray]:
    """Nodal displacement blocks (DISP) in file order: list of (N, 3) arrays (index = node id - 1)."""
    out = []
    with open(frd) as fh:
        lines = fh.readlines()
    i = 0
    nn = None
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("    2C"):
            nn = int(ln.split()[1])
        if ln.startswith(" -4  DISP"):
            arr = np.zeros((nn, 3))
            i += 5                                       # skip component descriptors
            while not lines[i].startswith(" -3"):
                if lines[i].startswith(" -1"):
                    nid = int(lines[i][3:13])
                    vals = [float(lines[i][13 + 12 * k:25 + 12 * k]) for k in range(3)]
                    arr[nid - 1] = vals
                i += 1
            out.append(arr)
        i += 1
    return out


def read_frequencies(dat: Path) -> list[float]:
    txt = dat.read_text()
    blk = txt.split("E I G E N V A L U E   O U T P U T")
    if len(blk) < 2:
        return []
    freqs = []
    for line in blk[1].splitlines():
        s = line.split()
        if len(s) == 5 and s[0].isdigit():
            freqs.append(float(s[3]))                    # cycles/time (Hz with s as time unit)
    return freqs


def von_mises(s: np.ndarray) -> np.ndarray:
    sxx, syy, szz, sxy, sxz, syz = (s[:, k] for k in range(6))
    return np.sqrt(0.5 * ((sxx - syy) ** 2 + (syy - szz) ** 2 + (szz - sxx) ** 2) + 3 * (sxy ** 2 + sxz ** 2 + syz ** 2))


def element_ip_coords(m: Mesh, key: str) -> np.ndarray:
    """Centroids of the elements of a set (used to locate maxima)."""
    return m.nodes[m.elems[key][:, :4] - 1].mean(axis=1)


def cf_failure_index(s: np.ndarray) -> np.ndarray:
    """Max-stress failure index of the woven CF plate for stress rows (sxx, syy, szz, sxy, sxz, syz)."""
    return np.maximum.reduce([np.where(s[:, 0] > 0, s[:, 0] / ALLOW["cf_t"], -s[:, 0] / ALLOW["cf_c"]),
                              np.where(s[:, 1] > 0, s[:, 1] / ALLOW["cf_t"], -s[:, 1] / ALLOW["cf_c"]),
                              np.abs(s[:, 3]) / ALLOW["cf_s"],
                              np.hypot(s[:, 4], s[:, 5]) / ALLOW["cf_ilss"]])


def interface_elements(m: Mesh) -> np.ndarray:
    """Boolean mask over CORE elements that have a face on a face-sheet bond plane (|z| = core_t/2)."""
    zc = m.nodes[m.elems["CORE"][:, :4] - 1, 2]
    h = C.core_t / 2
    return (np.sum(np.abs(zc - h) < 1e-6, axis=1) >= 3) | (np.sum(np.abs(zc + h) < 1e-6, axis=1) >= 3)


def evaluate(m: Mesh, o: Outline, stresses: dict[str, np.ndarray], y_min: float = GRIP_Y[1] + 8.0) -> dict:
    """Peak stresses, locations and reserve factors for one load case.

    Results within 8 mm of the rigid grip clamp (y < y_min) are excluded: the idealised
    clamp edge is a stress singularity that a real hand + printed grip does not produce."""
    cent = {k: element_ip_coords(m, k) for k in ("TOP", "CORE", "BOT")}

    def rows_xyz(key: str, rows: np.ndarray) -> np.ndarray:
        return cent[key][rows[:, 0].astype(np.int64) - int(m.eids[key][0])]

    def peak(vals: np.ndarray, xyz: np.ndarray) -> dict:
        k = int(np.argmax(vals))
        return dict(value=round(float(vals[k]), 2), at=[round(float(v), 1) for v in xyz[k]])

    res: dict = {}
    # --- carbon face sheets
    cf = [(stresses["E_" + k], rows_xyz(k, stresses["E_" + k])) for k in ("TOP", "BOT")]
    rows = np.vstack([r for r, _ in cf])
    xyz = np.vstack([c for _, c in cf])
    keep = xyz[:, 1] >= y_min
    s, xyz_k = rows[keep, 2:], xyz[keep]
    res["cf_fibre"] = peak(np.max(np.abs(s[:, :2]), axis=1), xyz_k)
    res["cf_inplane_shear"] = peak(np.abs(s[:, 3]), xyz_k)
    res["cf_interlaminar_shear"] = peak(np.hypot(s[:, 4], s[:, 5]), xyz_k)
    res["cf_failure_index"] = peak(cf_failure_index(s), xyz_k)
    res["cf_fibre_at_clamp_edge"] = round(float(np.max(np.abs(rows[~keep, 2:4]))), 1)
    # --- rib core (frame, solid zone, wave)
    core = stresses["E_CORE"]
    cxyz = rows_xyz("CORE", core)
    sc = core[:, 2:]
    keep = cxyz[:, 1] >= y_min
    vm = von_mises(sc)
    wave = keep & (cxyz[:, 1] > C.solid_to + 6.0)
    res["core_vm"] = peak(np.where(keep, vm, 0), cxyz)
    res["core_vm_wave"] = peak(np.where(wave, vm, 0), cxyz)
    res["core_crush"] = peak(np.where(keep, -sc[:, 2], 0), cxyz)
    res["core_shear"] = peak(np.where(keep, np.hypot(sc[:, 4], sc[:, 5]), 0), cxyz)
    res["core_shear_wave"] = peak(np.where(wave, np.hypot(sc[:, 4], sc[:, 5]), 0), cxyz)
    # --- adhesive bond line: integration points of core elements lying on the face sheets
    iface = interface_elements(m)
    on_bond = iface[core[:, 0].astype(np.int64) - int(m.eids["CORE"][0])] & keep
    bshear = np.where(on_bond, np.hypot(sc[:, 4], sc[:, 5]), 0)
    bpeel = np.where(on_bond, np.maximum(sc[:, 2], 0), 0)
    res["bond_shear"] = peak(bshear, cxyz)
    res["bond_peel"] = peak(bpeel, cxyz)
    wave_bond = on_bond & wave
    res["bond_shear_wave"] = peak(np.where(wave_bond, bshear, 0), cxyz)
    res["bond_peel_wave"] = peak(np.where(wave_bond, bpeel, 0), cxyz)
    # --- reserve factors (allowable / applied)
    res["rf"] = dict(cf=round(1.0 / res["cf_failure_index"]["value"], 2),
                     core=round(ALLOW["core_vm"] / res["core_vm"]["value"], 2),
                     core_wave=round(ALLOW["core_vm"] / max(res["core_vm_wave"]["value"], 1e-9), 2),
                     bond=round(min(ALLOW["bond_shear"] / res["bond_shear"]["value"],
                                    ALLOW["bond_peel"] / max(res["bond_peel"]["value"], 1e-9)), 2),
                     bond_wave=round(min(ALLOW["bond_shear"] / max(res["bond_shear_wave"]["value"], 1e-9),
                                         ALLOW["bond_peel"] / max(res["bond_peel_wave"]["value"], 1e-9)), 2))
    return res


def locate(m: Mesh, key: str, eid: int) -> tuple[float, float, float]:
    i = int(np.nonzero(m.eids[key] == eid)[0][0])
    c = m.nodes[m.elems[key][i, :4] - 1].mean(axis=0)
    return float(c[0]), float(c[1]), float(c[2])


def nodal_field(m: Mesh, key: str, rows: np.ndarray, values: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Average element-mean values onto the corner nodes of one element set: (node ids, values)."""
    eid_to_idx = {int(e): i for i, e in enumerate(m.eids[key])}
    per_elem: dict[int, list[float]] = {}
    for e, v in zip(rows[:, 0].astype(int), values):
        per_elem.setdefault(e, []).append(v)
    acc = np.zeros(len(m.nodes) + 1)
    cnt = np.zeros(len(m.nodes) + 1)
    for e, vs in per_elem.items():
        conn = m.elems[key][eid_to_idx[e]]
        acc[conn] += max(vs)
        cnt[conn] += 1
    ids = np.nonzero(cnt)[0]
    return ids, acc[ids] / cnt[ids]


def save_json(obj, path: Path) -> None:
    path.write_text(json.dumps(obj, indent=2))
