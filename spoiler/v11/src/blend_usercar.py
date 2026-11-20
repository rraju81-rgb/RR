"""v11: Cycles render of the spoiler on the owner's Polo GTI model (FINAL_MODEL_11.fbx).
  - The model is imported, scaled to metres (it comes in at 1/100) and placed in the spoiler's car frame by its bumpers
    and ground (as v11/out/user_exterior_carframe0.ply), then into Blender's frame exactly as v6's renders.
  - Its factory roof spoiler (and the third brake light in it) is hidden: ours replaces it.
  - Our spoiler (v6/out/E2.stl, the finished one-piece part) goes where v11/src/fit_spoiler.py placed it (v11/out/fit.json).
  - The model's texture images are not included, so materials are set from their names (blue metallic paint as the
    owner's car, black trim, glass, lamps, dark wheels, red calipers).
Usage (from spoiler/):  python3 v11/src/blend_usercar.py <view> <out.png> <W> <H> <samples> [fbx=path] [cam=x,y,z,tx,ty,tz,f] [wing=1]"""
import os, sys, math, json, numpy as np
sys.path.insert(0, 'v6/car/src')
import bpy, trimesh
from mathutils import Vector, Matrix
import blend_scene as BS
import blend_photo as BP
from car_body import Y_G
FBX = 'v11/input/FINAL_MODEL_11.fbx'
CY, CZ = -14.4 + Y_G, -1409.0                  # model (m, X across, Y to the rear, Z up) -> car frame (mm): bumpers + ground
WING = ('winga', 'trunk_tail_light', 'trunk_body_2')

def user_to_blender():
    """4x4: model world coordinates (after the 1/100 import scale is undone) -> Blender frame of the v6 renders"""
    # car = (-X*1000, Z*1000 + CY, Y*1000 + CZ); blender = (x/1000, -z/1000, (y - Y_G)/1000)
    M = np.zeros((4, 4)); M[3, 3] = 1.0
    M[0, 0] = -1.0                              # X_b = -X
    M[1, 1] = -1.0; M[1, 3] = -CZ / 1000.0      # Y_b = -(Y + CZ/1000)
    M[2, 2] = 1.0;  M[2, 3] = (CY - Y_G) / 1000.0   # Z_b = Z + (CY - Y_G)/1000
    return Matrix(M.tolist())

def materials():
    P = BS.principled
    return {
        'paint': BP.mat_paint('paint', BP.PAINTS['blue']),
        'trim': P('trim_black', (0.008, 0.008, 0.009), rough=0.08, coat=0.8, coat_rough=0.02),
        'plastic': P('plastic_black', (0.012, 0.012, 0.013), rough=0.45, spec=0.4),
        'rubber': P('rubber', (0.010, 0.010, 0.010), rough=0.8, spec=0.25),
        'tyre': P('tyre', (0.022, 0.022, 0.024), rough=0.82, spec=0.3),
        'rim': P('rim_dark', (0.035, 0.036, 0.040), rough=0.22, metal=0.85, coat=0.6, coat_rough=0.05),
        'metal': P('metal', (0.45, 0.45, 0.47), rough=0.25, metal=1.0),
        'caliper': P('caliper_red', (0.55, 0.012, 0.012), rough=0.25, coat=0.9),
        'glass': P('glass', (0.0015, 0.0018, 0.002), rough=0.02, spec=0.24),
        'lamp_glass': P('lamp_glass', (0.55, 0.56, 0.58), rough=0.03, metal=0.6, coat=1.0, coat_rough=0.01),
        'head': P('head_lamp', (0.62, 0.64, 0.66), rough=0.05, metal=0.7, coat=1.0),
        'red': P('tail_red', (0.20, 0.004, 0.004), rough=0.05, coat=1.0, coat_rough=0.01, emis=(1.0, 0.03, 0.015), emis_str=0.25),
        'amber': P('amber', (0.45, 0.16, 0.01), rough=0.05, coat=1.0),
        'mirror': P('mirror_chrome', (0.70, 0.71, 0.72), rough=0.02, metal=1.0),
        'under': P('underbody', (0.015, 0.015, 0.016), rough=0.7),
        'interior': P('interior', (0.018, 0.018, 0.020), rough=0.65, spec=0.3),
        'spoiler': P('spoiler_gloss_black', (0.010, 0.010, 0.011), rough=0.08, coat=1.0, coat_rough=0.015),
    }

def pick(objname, matname, M):
    n, m = objname.lower(), matname.lower()
    if 'cockpit' in n and 'glass' not in n and 'mirror' not in m: return M['interior']
    if m == 'carpaint': return M['paint']
    if 'caliper' in n: return M['caliper']
    if m in ('rim', 'rimc'): return M['rim']
    if m == 'tyre': return M['tyre']
    if m == 'rubber': return M['rubber']
    if m == 'window': return M['glass']
    if m == 'red_glass': return M['red']
    if m == 'ambar_glass': return M['amber']
    if m == 'glass_light': return M['lamp_glass']
    if m == 'light_1': return M['red'] if ('tail' in n or 'rear' in n) else M['head']
    if m == 'mirrors': return M['mirror']
    if m == 'under': return M['under']
    if m == 'ext_metal': return M['metal']
    if m in ('ext_plastic',): return M['plastic']
    if m in ('ext', 'ext_t', 'glass_surr'): return M['trim']
    return M['interior']

def build(fbx=FBX, show_wing=False):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    bpy.ops.import_scene.fbx(filepath=os.path.abspath(fbx))
    M = materials(); U2B = user_to_blender(); S100 = Matrix.Scale(100.0, 4)
    meshes = [o for o in bpy.data.objects if o.type == 'MESH']
    for o in meshes:                                                   # bake the placement into the meshes
        o.data.transform(U2B @ S100 @ o.matrix_world)
    for o in [o for o in bpy.data.objects]:
        o.parent = None; o.matrix_world = Matrix.Identity(4)
    hidden = []
    for o in meshes:
        if not show_wing and any(k in o.name.lower() for k in WING):
            o.hide_render = True; hidden.append(o.name); continue
        names = [s.material.name if s.material else '' for s in o.material_slots] or ['']
        o.data.materials.clear()
        for nm in names: o.data.materials.append(pick(o.name, nm, M))
        for p in o.data.polygons: p.use_smooth = True
    for o in bpy.data.objects:
        if o.type == 'EMPTY': bpy.data.objects.remove(o)
    fit = json.load(open('v11/out/fit.json')); R = np.array(fit['R']); t = np.array(fit['t'])
    sp = trimesh.load('v6/out/E2.stl'); sp.vertices = sp.vertices @ R.T + t
    BS.new_mesh('spoiler', sp, [M['spoiler']], loop_normals=BS.spoiler_normals(sp))
    BP.world_and_ground(sc)
    sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.use_denoising = True
    try: sc.cycles.denoiser = 'OPENIMAGEDENOISE'
    except Exception: pass
    sc.render.threads_mode = 'FIXED'; sc.render.threads = int(os.environ.get('BL_THREADS', 4))
    sc.view_settings.view_transform = 'AgX'
    try: sc.view_settings.look = 'AgX - Medium High Contrast'
    except Exception: pass
    sc.cycles.max_bounces = 8; sc.cycles.glossy_bounces = 6; sc.cycles.sample_clamp_indirect = 3.0
    sc.cycles.use_adaptive_sampling = True; sc.cycles.adaptive_threshold = 0.02
    # the cameras of the v6 views, moved with the spoiler (its placement on this model differs from the old car model)
    E0 = trimesh.load('v6/out/E2.stl'); c0 = BS.to_bl(E0.vertices).mean(0); c1 = BS.to_bl(sp.vertices).mean(0)
    print('hidden:', hidden); print('spoiler moved (Blender m):', np.round(c1 - c0, 3))
    return sc, c1 - c0

VIEWS = dict(BP.VIEWS)
VIEWS['detail'] = ((-1.20, -1.05, 1.85), (-0.38, 0.12, 1.33), 58, 4.0)

if __name__ == '__main__':
    view, out, Wd, Hd, spp = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5])
    kw = dict(a.split('=') for a in sys.argv[6:])
    sc, shift = build(kw.get('fbx', FBX), show_wing=kw.get('wing') == '1')
    loc, tgt, f, fs = VIEWS[view]
    if 'cam' in kw:
        c = list(map(float, kw['cam'].split(','))); loc, tgt, f = tuple(c[:3]), tuple(c[3:6]), c[6]; fs = c[7] if len(c) > 7 else fs
    else:
        loc = tuple(np.add(loc, shift)); tgt = tuple(np.add(tgt, shift))
    BP.VIEWS[view] = (loc, tgt, f, fs); BP.camera(view)
    sc.render.resolution_x = Wd; sc.render.resolution_y = Hd; sc.render.resolution_percentage = 100
    sc.cycles.samples = spp; sc.render.filepath = out
    import time; t0 = time.time()
    bpy.ops.render.render(write_still=True)
    print('rendered', out, '%.1fs' % (time.time() - t0))
