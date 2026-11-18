"""Render passes for putting the spoiler into the owner's photo, from the solved camera (v6/car/data/photo_camera.json).
Passes (linear float RGBA, saved as .npy, rows top-down):
  spoiler  - the spoiler alone; car, wheels and ground are holdouts (they hide what is behind them, render transparent)
  with     - the car with the spoiler invisible to the camera but casting its shadows and reflections
  without  - the car without the spoiler        (with / without = how the spoiler changes the light on the car)
  sky      - the environment alone, for matching the exposure to the photo's sky
Usage (from spoiler/): python3 v6/car/src/blend_photo_comp.py <pass> <out.npy> <scale> <samples> [border=x0,y0,x1,y1]
border: render only this box, in photo pixels (the rest stays transparent)."""
import sys, os, json, numpy as np
sys.path.insert(0, 'v6/car/src')
import bpy
import blend_photo as BP

ps, out, k, spp = sys.argv[1], sys.argv[2], float(sys.argv[3]), int(sys.argv[4])
kw = dict(a.split('=') for a in sys.argv[5:])
sc = BP.build_photo('blue')
cd = json.load(open('v6/car/data/photo_camera.json')); b = cd['blender']
cam = bpy.data.cameras.new('cam'); cam.lens = b['lens']; cam.sensor_width = 36.0; cam.sensor_fit = 'AUTO'
cam.shift_x = b['shift_x']; cam.shift_y = b['shift_y']; cam.dof.use_dof = False
o = bpy.data.objects.new('cam', cam); o.location = b['location']; o.rotation_euler = b['rotation_euler']
bpy.context.collection.objects.link(o); sc.camera = o
W, H = round(b['W'] * k), round(b['H'] * k)
sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = W, H, 100
if 'border' in kw:
    x0, y0, x1, y1 = map(float, kw['border'].split(','))
    sc.render.use_border = True; sc.render.use_crop_to_border = False
    sc.render.border_min_x, sc.render.border_max_x = x0 / b['W'], x1 / b['W']
    sc.render.border_min_y, sc.render.border_max_y = 1 - y1 / b['H'], 1 - y0 / b['H']
dz = float(cd.get('dz_body', 0.0))                 # ride height solved with the camera: body lower on its wheels
for ob in bpy.data.objects:
    if ob.type in ('MESH', 'FONT') and ob.name not in ('tyre', 'rim', 'disc', 'caliper', 'ground'): ob.location.z -= dz
sp = bpy.data.objects['spoiler']
others = [ob for ob in bpy.data.objects if ob.type in ('MESH', 'FONT') and ob is not sp]
sc.render.film_transparent = True
if ps == 'spoiler':
    for ob in others: ob.is_holdout = True
elif ps == 'with':
    sp.visible_camera = False
elif ps == 'without':
    sp.hide_render = True
elif ps == 'sky':
    for ob in others + [sp]: ob.hide_render = True
    sc.render.film_transparent = False; spp = 1; sc.cycles.use_denoising = False
sc.cycles.samples = spp
tmp = out[:-4] + '.exr'
sc.render.image_settings.file_format = 'OPEN_EXR'; sc.render.image_settings.color_depth = '32'
sc.render.image_settings.color_mode = 'RGBA'; sc.render.filepath = os.path.abspath(tmp)
import time; t = time.time()
bpy.ops.render.render(write_still=True)
im = bpy.data.images.load(os.path.abspath(tmp)); px = np.empty(W * H * 4, np.float32); im.pixels.foreach_get(px)
np.save(out, px.reshape(H, W, 4)[::-1].copy()); os.remove(tmp)
print('pass', ps, out, W, H, '%.1fs' % (time.time() - t))
