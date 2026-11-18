# Wind test (CFD): the car with and without the roof spoiler

A computer simulation of air flowing over the car at **100 km/h**, once without the spoiler and once with the final
spoiler fitted, everything else identical. It answers: what does the spoiler do to drag, and to lift on each axle?

## Results

| | Without spoiler | With spoiler | Change |
|---|---|---|---|
| Drag coefficient Cd | 0.275 | 0.312 | +0.037 (+13.4 %) |
| Drag at 100 km/h | 269 N | 305 N | +36 N |
| Total lift coefficient Cl | -0.068 | -0.189 | −0.120 |
| Lift, front axle, 100 km/h | -99 N | -101 N | −2 N |
| Lift, rear axle, 100 km/h | +32 N | -83 N | −116 N |
| Friction share of drag | 10 % | 9 % |  |

Lift is positive upwards: a negative change is extra downforce. Drag and lift grow with the square of the speed:

| Speed | Drag without → with | Front-axle lift without → with | Rear-axle lift without → with |
|---|---|---|---|
| 100 km/h | 269 → 305 N | -99 → -101 N | +32 → -83 N |
| 130 km/h | 455 → 516 N | -167 → -171 N | +54 → -141 N |
| 160 km/h | 689 → 782 N | -254 → -259 N | +83 → -213 N |

**The spoiler on its own** (the forces on its surface alone): drag +2.5 N, lift -9.1 N at 100 km/h.
Most of the change comes from how the spoiler alters the flow over the roof, the rear window and the tailgate, not from the force on the part itself.

## What it means

- **Rear-axle lift drops by 116 N at 100 km/h** (195 N at 130 km/h): the rear axle goes from slight lift to downforce.
  The front axle hardly changes (−2 N), so the aerodynamic balance moves rearwards, which makes the car steadier at speed.
- **Drag rises by 36 N at 100 km/h (+13 %)**: the kicked-up lip throws the roof flow higher, so the wake behind
  the tailgate is taller (see `results/midplane_speed.png`). That costs about 1.0 kW more power at 100 km/h.
  This is the usual trade-off of a ducktail lip: rear downforce for some drag.
- **Load on the part itself is small:** the airflow pushes the spoiler down onto the roof (-9 N) and back (+2.5 N)
  at 100 km/h, about 23 N down and 6 N back at 160 km/h. That is tiny for VHB tape, and it presses the part
  onto the tape rather than pulling it off.
- **How sure:** without the spoiler the steady solution keeps a small wake oscillation: between iterations 900 and 1500,
  Cd moves within 0.272–0.280 and the rear-axle lift coefficient within +0.021 to +0.040. With the spoiler it is steadier.
  Both changes are several times larger than that band.

## Pictures

- `results/midplane_speed.png`: air speed on the car's centre line, around the roof and tailgate, without and with the spoiler.
- `results/cp_surface.png`: surface pressure on the car (blue = suction, red = pressure), without and with the spoiler.
- `results/forces_summary.png`: drag and axle lift at 100 and 130 km/h.
- `results/convergence.png`: the coefficients every 300 iterations; they must settle before the numbers count.

## Convergence

| Iteration | Cd without | Cd with | Rear-axle Cl without | Rear-axle Cl with |
|---|---|---|---|---|
| 300 | 0.3720 | 0.3826 | +0.0883 | -0.1006 |
| 600 | 0.2872 | 0.3191 | -0.0368 | -0.1163 |
| 900 | 0.2738 | 0.3125 | +0.0383 | -0.0973 |
| 1200 | 0.2800 | 0.3119 | +0.0209 | -0.0801 |
| 1500 | 0.2718 | 0.3117 | +0.0396 | -0.0781 |

## How the test was run

| | |
|---|---|
| Solver | OpenFOAM v1912 (Ubuntu package), `simpleFoam`: steady incompressible RANS |
| Turbulence model | k-ω SST with wall functions; inlet 0.5 % turbulence intensity, eddy-to-molecular viscosity ratio 10 |
| Speed | 100 km/h (27.8 m/s), air at 1.205 kg/m³ |
| Road | Moving ground at road speed, wheels rotating (tyres sunk 8 mm into the ground for the contact patch) |
| Domain | Half car with a symmetry plane on the centre line; 34 m long (10 m ahead, 20 m behind), 6 m to the side, 6 m high; 3 % blockage |
| Mesh | snappyHexMesh, cut cells with 3 prism layers on the body (2 on the wheels); 25 mm cells on the body, 12.5 mm where the surface curves, around the wheels and over the rear roof, 3–6 mm on the spoiler; both variants share the same domain and refinement boxes |
| Convergence | 300 iterations first-order upwind, then 1200 with second-order linear-upwind; residuals and forces checked every 300 iterations. The figures are the mean of iterations 900, 1200 and 1500 (the wake keeps a small oscillation in a steady solver) |
| Forces | Integrated from the solution: pressure on every surface face, plus wall shear stress from the wall functions. Lift per axle from the pitching moment about the wheelbase mid-point at ground level. Doubled for the full car. |
| Reference | Frontal area 2.10 m² (the spoiler adds none: it sits inside the roof's outline), wheelbase 2.47 m |

**The two cars.** Without the spoiler, the car is the original body. With the spoiler, the roof under it is the version shaped to the spoiler's underside (1.5 mm tape gap), the same as in the renders; everywhere else the two bodies are identical. The spoiler is lowered 3 mm so that its underside seals onto the roof, as the tape does on the car. (A first no-spoiler run on the shaped roof was discarded: without the spoiler on top, the shaped roof's rear edge is a step that the real car does not have, and the solution broke down there.)

A speed cap of 80 m/s (about three times the free stream) guards against a blow-up in a few poor cells where the spoiler meets the car. It never acted in either final solution: the highest local speeds were 49 m/s without and 49 m/s with the spoiler.

### Why the forces are computed afterwards
This OpenFOAM package fails in every run-time "function object" (forces, sampling, y+), with an `IOstream "sha1"` error. Installing a newer OpenFOAM from the vendor's repository was not allowed in this environment. So the solver writes its fields every 300 iterations and `a4_forces.py` integrates the forces from them, the same way OpenFOAM's own `forces` and `wallShearStress` tools do.

## How far to trust it

- **Use the changes, not the absolute values.** The car is our modelled Polo-class body, not a scan or VW's CAD: the
  underbody is smooth, the wheel arches simple, there is no engine bay airflow or radiator. A real car has more drag
  and more lift than this model. The difference with and without the spoiler is the useful number.
- Steady RANS with a k-ω SST model on one mesh of 0.74–0.87 M cells (half car). That is a typical "first look" setup;
  a finer mesh, a mesh-independence study, or transient simulation could move the numbers by a few per cent.
- No wind tunnel or road test has been done. Confirm on the car (for example, coast-down or a tuft test on the rear window).

## Files

| File | What it is |
|---|---|
| `results/aero_results.json` | All numbers above, plus the convergence history |
| `results/*.png` | The pictures |
| `src/a1_geometry.py` | CFD surfaces in metres (car body, original body, spoiler, mirrors, wheels) |
| `src/a2_case.py` | Writes the OpenFOAM case for one variant |
| `src/a3_run.sh`, `src/a3_solve.sh` | Mesh and solve; solve again on an existing mesh |
| `src/foamread.py`, `src/a4_forces.py` | Read the OpenFOAM results and integrate the forces |
| `src/a5_figures.py`, `src/a6_report.py` | Figures and this report |

To rerun from `spoiler/` (about 1 hour on 4 cores): `python3 aero/src/a1_geometry.py`, then for each variant
`bash aero/src/a3_run.sh no_spoiler` / `with_spoiler` and `python3 aero/src/a4_forces.py <variant>`, then
`python3 aero/src/a5_figures.py` and `python3 aero/src/a6_report.py`. The raw OpenFOAM cases (several GB) stay in
`aero/out/`, which is not in git.
