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
| `src/photo_cam.py`, `src/photo_match.py` | Camera model and camera solve for the owner's photo -> `data/photo_camera.json`. |
| `src/blend_photo_comp.py`, `src/render_photo_comp.sh` | Render passes for the photo composite -> `out/photo_comp/` (not in git). |
| `src/photo_composite.py` | The composite: old wing out, our spoiler in -> `../brochure/photo/owner_car_with_spoiler.png`. |

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

## Photo-style renders (current brochure)

`src/blend_photo.py` renders the same car and spoiler outdoors, styled after the customer's reference photo of a blue Polo GTI:
- blue metallic paint;
- gloss-black spoiler, mirror caps and 18" multi-spoke wheels with red calipers;
- smoked tail lamps with a silver rim and an LED strip;
- black diffuser with fins, twin exhaust and red reflectors;
- black side-skirt lips;
- the body lowered 28 mm on its wheels.

The setting is an overcast lake-and-hills sky over asphalt. Both are Poly Haven CC0 assets, in `env/`.

| File | View |
|---|---|
| `hero_blue.jpg` | Rear three-quarter, low, like the reference photo (the spec sheet) |
| `side_blue.jpg`, `top_rear_blue.jpg`, `detail_fin_blue.jpg` | Side profile, high rear view, fin close-up (brochure page 2) |
| `joints_v8.jpg` | The six v8 sections upside down, with the ten keys lifted out of their pockets (`blend_scene.py joint ... ver=v8`) |

`sh v6/car/src/render_photo.sh` renders them all (about 40 min on 4 cores). It is still our own Polo-class model, not Volkswagen's CAD data, and has no VW badges. The older studio renders listed below are kept for reference.

## Owner's photo with the spoiler (brochure page 1)

Page 1 of the brochure is the owner's own photo of their blue Polo GTI (`../brochure/photo/owner_car_original.png`, 510 × 392 px). The car in it wore a different, larger wing. That wing was removed and our spoiler rendered into the photo:

1. **Camera** (`src/photo_match.py` -> `data/photo_camera.json`). A pinhole camera in Blender's terms (lens on a 36 mm wide sensor, lens shift) is solved against the 3D car. It uses:
   - the right-hand wheel rims;
   - the car's outline against the sky and background, weighted up round the rear pillars and roof, with the old wing left out;
   - lines across the car's rear that must point at the lateral vanishing point (the tailgate crease, the bottom of the rear window, the lamp corners, the plate).
   Free parameters besides the camera: the body's ride height on its wheels and the rim size. Result: camera 0.41 m high, turned 15° to the car, 78 mm-equivalent lens; the photo is an off-centre crop (lens shift −0.23 of the width). The body sits 22 mm lower than the model and the wheels are about 20 in. Wheel points fit to 2.8 px rms and the lines across the rear to 0.5 px.
2. **Render passes** (`src/render_photo_comp.sh`, which runs `src/blend_photo_comp.py`; about 1 min). From that camera:
   - the spoiler alone (gloss black; the car and the ground are holdouts);
   - the car with and without the spoiler, whose ratio is the spoiler's shade on the car;
   - the bare environment, for the exposure.
3. **Composite** (`src/photo_composite.py` -> `../brochure/photo/owner_car_with_spoiler.png`):
   - The old wing is removed. Above our spoiler, the sky is filled from the clear sky around it. Below the new lip, the top of the rear window becomes its black band in shade, blended into the glass.
   - The spoiler is placed with its shade.
   - It is graded to the photo's look: the photo's black level and its blue-tinted blacks, read off the diffuser and the old wing; sky glints rolled off to grey.
   - Its edges are softened and sharpened to match the photo.
   Only the wing's area changes (x 136–325, y 71–123 px).

`src/photo_cam.py` holds the shared camera model, the old wing's traced outline and a fast rasterizer for overlays.

**Limits.**
- The generic model's roof and rear window sit about 30–40 mm (5 px) lower than the real car's, measured on the roof edge beside the old wing, the bottom of the rear window and the left pillar. So the rendered spoiler and its shade are moved 2 px left and 5.5 px up in the composite (`SHIFT_PX`).
- The old wing's outline is traced by hand in 510 × 392 px. A larger original needs it traced again.
- The result shows how our spoiler would look on this car. It is not a photo of a printed part.

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
