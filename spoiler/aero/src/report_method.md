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
