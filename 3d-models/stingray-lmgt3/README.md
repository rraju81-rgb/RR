# Stingray LMGT3 car shell

The blue-spotted stingray figure reworked into a GT3 / LMGT3-style car body shell. The ray's sculpted body is kept as the main bodywork.

| Region (from the marked-up screenshot) | What was done |
|---|---|
| Black (main shell) | The original ray body. The tail is cut off flat at the rear (Kamm-tail style). The body is hollowed from below to a 2.2 mm wall, so the bottom is open like an RC body shell. |
| Red (front wheels) | Wheel arches cut at y = -35 mm (19 mm wheel, 11 mm arch radius), with faired fender bulges blending into the wing. |
| Blue (rear wheels) | Same at y = +32 mm (67 mm wheelbase). |
| Green (front grille + bumper) | The gap under the nose is filled down to the plate as a front bumper, with a 3 mm splitter lip, a 3-slot main grille under the snout and two side intakes. |

* `Stingray_LMGT3_shell.3mf`: print-ready, centred for a 256 mm bed (A1). Watertight, about 136 × 128 × 29.5 mm, about 1.0 M triangles.
* `previews/`: quick orthographic renders.
* `scripts/`: the full pipeline (Python: trimesh, manifold3d, scipy, scikit-image, shapely).

## Rebuild
```bash
python3 load.py <unzipped 3mf>/3D/Objects/object_1.model raw.npz   # apply Bambu build transform
python3 align.py                                                   # yaw-align body axis to +Y
python3 build.py                                                   # tail cut, hollow, fascia, grille, arches
```
Edit the `P = dict(...)` block at the top of `build.py` to change the wheelbase, wheel size, wall thickness and so on.

## Printing
The underside rim follows the original ray's wing edges, which are mostly lifted off the plate. Print it upright with tree supports, as for the original figure. Supports are needed under the wing edges and arches.

---

# v2: Hypercar "mutant stingray" shell (`Stingray_Hypercar_shell.3mf`)

A sculptural hypercar version. The wings themselves are morphed into the car (`scripts/build2.py`):

* **Wheel pods:** the outer wings are bent upward over each wheel into rounded, flat-topped pods, so the shell edge waves up over the wheels. All four pods are levelled to about 31 mm. Front axle y = -35, rear axle y = +25.
* **Waist:** the plan view is pinched between the pods, giving a guitar-shaped top view and a "dog-bone" open underside.
* **Shell:** 2 mm thin wall with an open bottom, and the rear rounded off in plan view.
* **Details:** a teardrop canopy over the spine, oval vents through the top of each pod, raked headlight recesses on the front pods, and a 2.6 mm dorsal blade fin replacing the tail, sweeping up to 57 mm behind the car.
* **Size:** about 133 × 163 × 57 mm, watertight. Print upright with tree supports.

Main knobs are in `P = dict(...)` in `build2.py`: `lift`, `pod_top`, `pod_len`, `waist`, axle positions and `wall`.
