"""Aero test, step 4: forces and coefficients from the written fields of one variant (no function objects needed).
Pressure force  F_p = rho * sum(p_f S_f)                     over the wall faces (S_f points out of the fluid)
Friction force  F_v = rho * sum((nu + nut_f) (U_P - U_f)_t / d_P |S_f|)   (wall-function shear stress, as OpenFOAM)
Moments about the wheelbase mid-point at ground level -> front / rear axle lift.  Half model: forces x 2.
Run from spoiler/:  python3 aero/src/a4_forces.py no_spoiler|with_spoiler"""
import sys, os, json, glob, numpy as np
sys.path.insert(0, 'aero/src')
from foamread import read_points, read_labels, read_faces, read_boundary, face_geometry, cell_centres, read_field
VAR = sys.argv[1]; CASE = f'aero/out/{VAR}'
CI = json.load(open(f'{CASE}/case_info.json')); G = json.load(open('aero/out/geometry/geometry_info.json'))
U, NU, RHO = CI['U'], CI['nu'], CI['rho']; XM = CI['x_mid']; AFULL = G['frontal_area_m2_no_spoiler']; WB = G['wheelbase_m']
q = 0.5 * RHO * U ** 2
P = read_points(CASE); flat, starts, sizes = read_faces(CASE)
owner = read_labels(f'{CASE}/constant/polyMesh/owner'); neigh = read_labels(f'{CASE}/constant/polyMesh/neighbour')
ncells = int(max(owner.max(), neigh.max()) + 1); B = read_boundary(CASE)
Cf, Sf = face_geometry(P, flat, starts, sizes); Cc = cell_centres(Cf, Sf, owner, neigh, ncells)
walls = CI['walls']
times = sorted([d for d in os.listdir(CASE) if d.replace('.', '').isdigit() and d != '0'], key=float)
print(VAR, 'cells', ncells, 'faces', len(starts), 'times', times)
def forces_at(t):
    p, pb = read_field(CASE, t, 'p', ncells, B); Uc, Ub = read_field(CASE, t, 'U', ncells, B); nut, nutb = read_field(CASE, t, 'nut', ncells, B)
    res = {}
    for w in walls:
        b = B[w]; fi = np.arange(b['startFace'], b['startFace'] + b['nFaces']); own = owner[fi]
        S = Sf[fi]; A = np.linalg.norm(S, axis=1); n = S / A[:, None]
        pf = p[own] if pb[w] is None else pb[w]
        Fp = RHO * pf[:, None] * S
        Uf = np.zeros((len(fi), 3)) if Ub[w] is None else Ub[w]
        dU = Uc[own] - Uf; dU_t = dU - (dU * n).sum(1)[:, None] * n
        d = np.abs(((Cc[own] - Cf[fi]) * n).sum(1))
        nutf = nut[own] if nutb[w] is None else nutb[w]
        Fv = RHO * (NU + nutf)[:, None] * dU_t / d[:, None] * A[:, None]
        r = Cf[fi] - np.array([XM, 0.0, 0.0])
        res[w] = dict(Fp=Fp.sum(0), Fv=Fv.sum(0), Mp=np.cross(r, Fp).sum(0), Mv=np.cross(r, Fv).sum(0),
                      face_cp=pf / (0.5 * U ** 2), area=A.sum())
    return res
def summarise(res, parts):
    F = sum(res[w]['Fp'] + res[w]['Fv'] for w in parts) * 2.0          # full car
    M = sum(res[w]['Mp'] + res[w]['Mv'] for w in parts) * 2.0
    Fp = sum(res[w]['Fp'] for w in parts) * 2.0; Fv = sum(res[w]['Fv'] for w in parts) * 2.0
    L = F[2]; Lf = 0.5 * (L + M[1] / (WB / 2)); Lr = 0.5 * (L - M[1] / (WB / 2))
    return dict(drag_N=F[0], lift_N=L, lift_front_N=Lf, lift_rear_N=Lr, pitch_moment_Nm=M[1],
                drag_pressure_N=Fp[0], drag_friction_N=Fv[0],
                Cd=F[0] / (q * AFULL), Cl=L / (q * AFULL), Clf=Lf / (q * AFULL), Clr=Lr / (q * AFULL), CdA_m2=F[0] / q)
hist = {}
for t in times:
    res = forces_at(t)
    hist[t] = dict(car=summarise(res, walls), **{w: summarise(res, [w]) for w in walls})
    c = hist[t]['car']
    print(f"t={t:>5}: Cd {c['Cd']:.4f}  Cl {c['Cl']:+.4f}  Clf {c['Clf']:+.4f}  Clr {c['Clr']:+.4f}  drag {c['drag_N']:.1f} N  lift {c['lift_N']:+.1f} N  "
          f"(front {c['lift_front_N']:+.1f}, rear {c['lift_rear_N']:+.1f})  friction share {100 * c['drag_friction_N'] / c['drag_N']:.1f}%")
    if 'spoiler' in walls:
        sp = hist[t]['spoiler']; print(f"         spoiler alone: drag {sp['drag_N']:+.1f} N  lift {sp['lift_N']:+.1f} N")
# residuals from the solver log
import re
resid = {k: [] for k in ('Ux', 'Uy', 'Uz', 'p', 'k', 'omega')}
for line in open(f'{CASE}/log.simpleFoam'):
    m = re.search(r'Solving for (\w+), Initial residual = ([0-9.eE+-]+)', line)
    if m and m.group(1) in resid: resid[m.group(1)].append(float(m.group(2)))
json.dump(dict(variant=VAR, U=U, rho=RHO, Aref_full=AFULL, wheelbase=WB, x_mid=XM, cells=ncells, history=hist,
               residuals={k: v[::5] for k, v in resid.items()}), open(f'aero/out/{VAR}_forces.json', 'w'), indent=1, default=float)
# keep the final surface pressure and the mid-plane / wake data for the pictures
t = times[-1]
p, pb = read_field(CASE, t, 'p', ncells, B); Uc, Ub = read_field(CASE, t, 'U', ncells, B)
np.savez_compressed(f'aero/out/{VAR}_fields.npz', Cc=Cc, p=p, U=Uc, owner=owner,
                    **{f'faces_{w}': np.arange(B[w]['startFace'], B[w]['startFace'] + B[w]['nFaces']) for w in walls + ['midplane']})
np.savez_compressed(f'aero/out/{VAR}_mesh.npz', P=P, flat=flat, starts=starts, sizes=sizes, Cf=Cf, Sf=Sf)
print('saved', f'aero/out/{VAR}_forces.json')
