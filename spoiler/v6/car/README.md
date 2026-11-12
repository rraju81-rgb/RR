# v6 spoiler on the car: model and renders

The renders in `renders/` show the v6 spoiler fitted to a VW Polo 6R / 6C-class 5-door hatchback. They are used in the brochure in `../brochure/`.

**The car is a procedural 3D model, not a scan or a VW CAD model.** It was built for these images from the Polo's published dimensions:
- 3,970 mm long, 1,682 mm wide and 1,469 mm high;
- 2,470 mm wheelbase;
- 1,460 mm track, with 620 mm wheels.

It has no VW badges or logos. The rear plate reads CARBON 6.

## How the spoiler sits on the car

- The car and the spoiler share the spoiler's coordinates: x across the car, y up, z to the rear, in mm.
- The car views show the finished spoiler as one part, with seams filled and painted. That is the solid shape the pieces are cut from: `v6/out/E2.stl`, built by `v6/src/run_all.sh`.
- The joint and parts views use the printed pieces and keys unchanged. They show the current split, v7 (4 pieces, 6 keys, from `../../v7/assembled/`). Add `ver=v6` on the command line for the 3-piece split.
- The roof under the spoiler follows the measured underside of the v6 spoiler (`data/hump_profile.npz`). The spoiler sits on the roof with a **1.5 mm gap for the mounting tape**: that is the median, and 90% of points are between 1.2 and 2.7 mm. Under the fins, the C-pillars are pulled in to the same gap and blended back to their original shape over 70 mm. Along the inner faces of the fins, a few points get closer, down to touching near the fin tips. No point of the car is inside the spoiler.
- This means the fit in the renders is **by construction**: the roof was shaped to the spoiler. The renders show how the part looks on the car. They don't prove that it fits a real Polo, so dry-fit as described in `../README.md`.

## Files

| File | What it is |
|---|---|
| `renders/*.jpg` | Final renders (Cycles, 128 samples, denoised). The PNG originals are not kept in git. |
| `src/car_body.py` | Car body: 2D side and plan profiles turned into an implicit surface, then meshed with marching cubes at 5 mm. |
| `src/car_conform.py` | Fits the roof and C-pillars under the spoiler with the 1.5 mm tape gap. |
| `src/car_zones.py` | Smooth paint / glass / trim / lamp zones (thresholded in the shader), and the edge-preserving normal smoothing used for shading. |
| `src/car_parts.py`, `src/car_detail.py` | Wheels, tyres, brakes, shut lines, door handles, mirrors and number plates. |
| `src/car_mats.py` | Profile helpers (cabin half-width, window outline) used by `car_zones.py`. |
| `src/car_build_all.py` | Builds everything into `out/` (not in git). |
| `src/blend_scene.py` | Blender scene: studio lights, materials, cameras and the views listed below. |
| `src/render_final.sh` | Renders every view in `renders/`. |
| `data/hump_profile.npz` | Roof centre-line height under the spoiler: the spoiler underside minus the 1.5 mm tape gap. |

## Renders

| File | View |
|---|---|
| `hero_white.jpg`, `hero_red.jpg` | Rear three-quarter view (white car and red car). |
| `side.jpg` | Side profile. |
| `top_rear.jpg` | High rear view across the roof. |
| `detail_fin.jpg` | Close-up of the left fin wrapping the rear pillar. |
| `rear.jpg` | Straight rear view. |
| `joints.jpg` | The four printed sections upside down with the six bow-tie keys lifted out of their pockets. The keys are shown in orange for clarity: printed keys are the same material as the spoiler. |
| `parts.jpg` | The four sections and six keys laid out. |

## Rebuilding

Run from `spoiler/`:

```sh
sh v6/src/run_all.sh                 # v6 spoiler, incl. v6/out/E2.stl (skip if already built)
sh v7/src/run_all.sh                 # v7 pieces and keys for the joint and parts views
python3 v6/car/src/car_parts.py      # wheels and brakes  -> v6/car/out/
python3 v6/car/src/car_build_all.py  # body, fit, normals, details -> v6/car/out/  (about 2 min)
sh v6/car/src/render_final.sh        # all renders -> v6/car/renders/  (about 35 min on 4 CPU cores)
```

One view on its own: `python3 v6/car/src/blend_scene.py <view> <out.png> <width> <height> <samples> [paint=white|red|grey|blue] [studio=dark|light]`. The views are listed in `VIEWS` in `blend_scene.py`.

You need Python 3.13 with:
- numpy, scipy, scikit-image, matplotlib and Pillow;
- trimesh with embreex, manifold3d and libigl;
- Blender as a Python module (`pip install bpy`, version 5.2).

## Limits

- The body shape is approximate: a few side and plan profiles, not a measured body. The lamps, grille and glass are simplified. The front is the least accurate part, which is why most views are from the rear.
- The model is meshed at 5 mm. Shading uses de-noised normals, which leave the geometry unchanged, so the fit numbers above stand.
- About 50 small folded faces remain at the very tips of the fins, where the pillars were pulled in under them. None of the camera views show them.
