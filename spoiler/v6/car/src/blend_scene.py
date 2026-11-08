"""Blender Cycles studio scene for the Polo + v6 spoiler. Usage:
   python3 v6/car/src/blend_scene.py <view> <out.png> <W> <H> <samples> [paint=white|red|grey] [studio=dark|light]"""
import os, sys, math, numpy as np
sys.path.insert(0, 'v6/car/src')
import bpy, trimesh
from car_body import Y_G

def to_bl(V):   # car mm (x, y-up, z-rear) -> blender m (X, Y-forward, Z-up), ground at Z=0
    V = np.asarray(V, float)
    return np.column_stack([V[:, 0], -V[:, 2], V[:, 1] - Y_G]) * 0.001

def cached_normals(tm, key, **kw):
    """feature-preserving smoothed vertex normals (car frame), cached in v6/car/out/normals_<key>.npy"""
    from car_zones import smooth_normals
    p = f'v6/car/out/normals_{key}.npy'
    if os.path.exists(p):
        N = np.load(p)
        if len(N) == len(tm.vertices): return N
    N = smooth_normals(np.asarray(tm.vertices), np.asarray(tm.faces), **kw).astype(np.float32)
    np.save(p, N)
    return N

def split_normals(tm, Nv, split_deg=30.0):
    """per-corner normals: the smoothed vertex normal, or the flat face normal across edges sharper than split_deg"""
    F = np.asarray(tm.faces); fn = np.asarray(tm.face_normals); Nc = np.asarray(Nv)[F]
    use_v = np.einsum('fj,fkj->fk', fn, Nc) > np.cos(np.radians(split_deg))
    return np.where(use_v[..., None], Nc, fn[:, None, :]).reshape(-1, 3)

def spoiler_normals(tm):
    """de-noised split normals for a spoiler piece: smooth surfaces, sharp lip / seam edges kept"""
    from car_zones import smooth_normals
    return split_normals(tm, smooth_normals(tm.vertices, tm.faces, iters=30, tau=0.012), 30.0)

def new_mesh(name, tm, mats, mat_idx=None, smooth=True, auto=None, normals=None, loop_normals=None):
    me = bpy.data.meshes.new(name)
    V = to_bl(tm.vertices); F = np.asarray(tm.faces, np.int32)
    me.vertices.add(len(V)); me.vertices.foreach_set('co', V.astype(np.float32).ravel())
    me.loops.add(len(F) * 3); me.loops.foreach_set('vertex_index', F.ravel())
    me.polygons.add(len(F)); me.polygons.foreach_set('loop_start', np.arange(0, len(F) * 3, 3, dtype=np.int32))
    me.update(calc_edges=True)
    for m in mats: me.materials.append(m)
    if mat_idx is not None:
        assert len(me.polygons) == len(mat_idx), (len(me.polygons), len(mat_idx))
        me.polygons.foreach_set('material_index', np.asarray(mat_idx, np.int32))
    me.update()
    if smooth: me.shade_smooth()
    if normals is not None:   # custom per-vertex normals, rotated into Blender's frame like to_bl
        Nb = np.column_stack([normals[:, 0], -normals[:, 2], normals[:, 1]]).astype(np.float64)
        me.normals_split_custom_set_from_vertices(Nb.tolist())
    if loop_normals is not None:
        Nl = np.column_stack([loop_normals[:, 0], -loop_normals[:, 2], loop_normals[:, 1]]).astype(np.float64)
        me.normals_split_custom_set(Nl.tolist())
    ob = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(ob)
    if auto is not None:
        bpy.context.view_layer.objects.active = ob; ob.select_set(True)
        try: bpy.ops.object.shade_smooth_by_angle(angle=math.radians(auto))
        except Exception as e: print('smooth_by_angle failed', e)
        ob.select_set(False)
    return ob

def principled(name, base, rough=0.4, metal=0.0, coat=0.0, coat_rough=0.03, emis=None, emis_str=0.0, spec=0.5, trans=0.0, ior=1.45):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes.get('Principled BSDF')
    b.inputs['Base Color'].default_value = (*base, 1)
    b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metal
    b.inputs['Coat Weight'].default_value = coat
    b.inputs['Coat Roughness'].default_value = coat_rough
    b.inputs['Specular IOR Level'].default_value = spec
    b.inputs['Transmission Weight'].default_value = trans
    b.inputs['IOR'].default_value = ior
    if emis is not None:
        b.inputs['Emission Color'].default_value = (*emis, 1); b.inputs['Emission Strength'].default_value = emis_str
    return m

DEBUG_ZONES = False
NORMALS = True      # de-noised custom normals on the body and spoiler (normals=0 on the command line turns them off)
def zone_material(M, names):
    """ONE Principled BSDF; its inputs are blended per zone with masks (interpolated attribute z_<zone> > 0).
    (Stacking one BSDF per zone exceeds Cycles' 64-closure limit.)"""
    order = [('plastic', 'plastic_black'), ('glass', 'glass'), ('trim', 'trim_black'), ('tail', 'tail_lamp'),
             ('rev', 'rev_lamp'), ('head', 'head_lamp'), ('chrome', 'grille_chrome'), ('hidden', 'tape')]
    order = [o for o in order if o[0] in names]
    m = bpy.data.materials.new('body'); nt = m.node_tree
    for n in list(nt.nodes): nt.nodes.remove(n)
    out = nt.nodes.new('ShaderNodeOutputMaterial'); bsdf = nt.nodes.new('ShaderNodeBsdfPrincipled')
    nt.links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])
    def val(mat, key):
        return mat.node_tree.nodes.get('Principled BSDF').inputs[key].default_value
    masks = {}
    for zn, mk in order:
        att = nt.nodes.new('ShaderNodeAttribute'); att.attribute_type = 'GEOMETRY'; att.attribute_name = 'z_' + zn
        gt = nt.nodes.new('ShaderNodeMath'); gt.operation = 'GREATER_THAN'; gt.inputs[1].default_value = 0.0
        nt.links.new(att.outputs['Fac'], gt.inputs[0]); masks[zn] = gt.outputs[0]
    props = [('Base Color', 'RGBA'), ('Roughness', 'FLOAT'), ('Metallic', 'FLOAT'), ('Coat Weight', 'FLOAT'),
             ('Coat Roughness', 'FLOAT'), ('Specular IOR Level', 'FLOAT'), ('Emission Color', 'RGBA'), ('Emission Strength', 'FLOAT')]
    for key, dt in props:
        cur = None; base_v = val(M['paint'], key)
        ia, ib, io = (6, 7, 2) if dt == 'RGBA' else (2, 3, 0)
        for zn, mk in order:
            mix = nt.nodes.new('ShaderNodeMix'); mix.data_type = dt
            nt.links.new(masks[zn], mix.inputs[0])
            if cur is None: mix.inputs[ia].default_value = base_v
            else: nt.links.new(cur, mix.inputs[ia])
            mix.inputs[ib].default_value = val(M[mk], key)
            cur = mix.outputs[io]
        if cur is not None: nt.links.new(cur, bsdf.inputs[key])
        else: bsdf.inputs[key].default_value = base_v
    bsdf.inputs['Coat IOR'].default_value = 1.5
    return m

PAINTS = {'white': (0.58, 0.59, 0.60), 'red': (0.42, 0.012, 0.016), 'grey': (0.20, 0.21, 0.22), 'blue': (0.02, 0.07, 0.25)}

def lights_only(sc):
    # studio lights (softboxes)
    def area(name, loc, rot, size, size_y, energy, color=(1, 1, 1)):
        L = bpy.data.lights.new(name, 'AREA'); L.shape = 'RECTANGLE'; L.size = size; L.size_y = size_y; L.energy = energy; L.color = color
        o = bpy.data.objects.new(name, L); o.location = loc; o.rotation_euler = rot; bpy.context.collection.objects.link(o); return o
    def aim(o, target):
        from mathutils import Vector
        d = Vector(target) - o.location; o.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    area('top', (0, 1.9, 5.2), (0, 0, 0), 2.4, 6.5, 200)
    k1 = area('key_rear_left', (-3.6, -2.8, 2.6), (0, 0, 0), 2.6, 1.6, 260); aim(k1, (0, -0.2, 1.0))
    k2 = area('fill_right', (3.8, 1.0, 2.0), (0, 0, 0), 3.0, 1.4, 110); aim(k2, (0, 1.0, 0.8))
    r1 = area('rim_left', (-3.2, 3.8, 1.6), (0, 0, 0), 0.5, 5.0, 200); aim(r1, (0, 1.4, 1.0))
    r2 = area('rim_right', (3.2, -3.4, 1.8), (0, 0, 0), 0.5, 5.0, 200); aim(r2, (0, 0.0, 1.0))
    back = area('back_strip', (0, -4.8, 2.2), (0, 0, 0), 5.0, 0.6, 180); aim(back, (0, 0, 1.3))
    sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'
    sc.cycles.use_denoising = True
    try: sc.cycles.denoiser = 'OPENIMAGEDENOISE'
    except Exception: pass
    sc.render.threads_mode = 'FIXED'; sc.render.threads = 4
    sc.view_settings.view_transform = 'AgX'; sc.view_settings.exposure = -0.3
    try: sc.view_settings.look = 'AgX - Medium High Contrast'
    except Exception: pass
    sc.cycles.max_bounces = 8; sc.cycles.glossy_bounces = 6; sc.cycles.transparent_max_bounces = 4
    sc.cycles.sample_clamp_indirect = 2.0; sc.cycles.sample_clamp_direct = 0.0
    sc.cycles.blur_glossy = 1.0; sc.cycles.caustics_reflective = False; sc.cycles.caustics_refractive = False


def build_parts(mode='parts', studio='dark'):
    """spoiler pieces only: 'parts' = 3 pieces apart, keys in front; 'joint' = upside down, keys above the pockets"""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    M = {'spoiler': principled('spoiler_raw_print', (0.030, 0.030, 0.033), rough=0.45, spec=0.5),   # raw printed sections: satin, not painted
         'key': principled('key', (0.90, 0.13, 0.016), rough=0.40, coat=0.2),     # brand orange, so the keys read clearly
         'floor': principled('floor', (0.035, 0.036, 0.04) if studio == 'dark' else (0.55, 0.56, 0.58), rough=0.35 if studio == 'dark' else 0.55)}
    import json as _j
    meta = _j.load(open('v6/out/_parts_meta.json'))
    gapx = {'L': -150.0, 'C': 0.0, 'R': 150.0}
    for k in 'LCR':
        m = trimesh.load(f'v6/assembled/{k}.stl')
        if mode == 'joint':
            m.apply_transform(trimesh.transformations.rotation_matrix(np.pi, [0, 0, 1]))      # flip about the long (z) axis
            m.apply_translation([-gapx[k] * 0.3 if False else 0, 0, 0])
        m.apply_translation([gapx[k] * (0.35 if mode == 'joint' else 1.0) * (-1 if mode == 'joint' else 1), 0, 0])
        if NORMALS: new_mesh('spoiler_' + k, m, [M['spoiler']], loop_normals=spoiler_normals(m))
        else: new_mesh('spoiler_' + k, m, [M['spoiler']], auto=30)
    for i in range(4):
        km = trimesh.load(f'v6/assembled/KEY_{i + 1}.stl')
        T = np.array(meta['frames'][i]['T']); A = T[:, 2]; side = np.sign(meta['frames'][i]['seam'])
        if mode == 'joint':
            km.apply_transform(trimesh.transformations.rotation_matrix(np.pi, [0, 0, 1]))
            km.apply_translation([-side * gapx['R'] * 0.35 / 2 * 0, 0, 0])
            km.apply_translation(np.array([0, 0, 0]))
            # lift keys out of their pockets (pocket axis also flipped)
            A2 = np.array([-A[0], -A[1], A[2]])
            km.apply_translation(-A2 * 55.0 + np.array([-side * 150.0 * 0.35 / 2, 0, 0]))
        else:
            # keys lying flat in front of the pieces
            kl = trimesh.load('v6/out/_key_local.stl'); kl.apply_transform(trimesh.transformations.rotation_matrix(-np.pi / 2, [1, 0, 0]))
            sx = [-1, -1, 1, 1][i]; zz = [60.0, 200.0, 60.0, 200.0][i]
            kl.apply_translation([sx * (433.3 / 2 + 75.0), -88.0, zz]); km = kl
        new_mesh(f'key_{i}', km, [M['key']], auto=30)
    # drop everything onto the floor
    mins = []
    for o in bpy.data.objects:
        if o.type == 'MESH':
            mins.append(min((o.matrix_world @ __import__('mathutils').Vector(c)).z for c in o.bound_box))
    dz = -min(mins) + 0.002
    for o in bpy.data.objects:
        if o.type == 'MESH': o.location.z += dz
    bpy.ops.mesh.primitive_plane_add(size=40, location=(0, 0, 0)); fl = bpy.context.active_object; fl.data.materials.append(M['floor'])
    w = bpy.data.worlds.new('world'); sc.world = w; w.use_nodes = True
    w.node_tree.nodes['Background'].inputs['Color'].default_value = (0.004, 0.0045, 0.005, 1) if studio == 'dark' else (0.55, 0.56, 0.58, 1)
    return sc, dz

def build(paint='white', studio='dark', car_path='v6/car/out/car_body_conf.ply'):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    car = trimesh.load(car_path, process=False)
    M = {
        'paint': principled('paint', PAINTS[paint], rough=0.32, coat=1.0, coat_rough=0.025, metal=0.0 if paint == 'white' else 0.25),
        'glass': principled('glass', (0.006, 0.007, 0.009), rough=0.07, spec=0.7),   # 0.07: softbox reflections fall off softly
        'trim_black': principled('trim_black', (0.01, 0.01, 0.011), rough=0.08, coat=0.6),
        'plastic_black': principled('plastic_black', (0.018, 0.018, 0.02), rough=0.55),
        'tail_lamp': principled('tail_lamp', (0.30, 0.003, 0.005), rough=0.22, coat=1.0, coat_rough=0.22, emis=(1.0, 0.02, 0.015), emis_str=0.9),
        'rev_lamp': principled('rev_lamp', (0.55, 0.55, 0.56), rough=0.15, metal=0.6, coat=1.0, coat_rough=0.15),
        'head_lamp': principled('head_lamp', (0.62, 0.64, 0.66), rough=0.05, metal=0.7, coat=1.0),
        'grille_chrome': principled('chrome', (0.9, 0.9, 0.92), rough=0.05, metal=1.0),
        'tyre': principled('tyre', (0.025, 0.025, 0.027), rough=0.78),
        'rim': principled('rim', (0.70, 0.71, 0.73), rough=0.22, metal=1.0),
        'disc': principled('disc', (0.35, 0.35, 0.36), rough=0.45, metal=0.9),
        'caliper': principled('caliper', (0.45, 0.02, 0.02), rough=0.3, coat=0.8),
        'spoiler': principled('spoiler_gloss_black', (0.012, 0.012, 0.013), rough=0.12, coat=1.0, coat_rough=0.02),
        'gap': principled('gap', (0.004, 0.004, 0.004), rough=0.9),
        'tape': principled('tape', (0.006, 0.006, 0.006), rough=0.85),
        'plate': principled('plate', (0.80, 0.80, 0.78), rough=0.35),
        'ink': principled('ink', (0.01, 0.01, 0.01), rough=0.4),
        'floor': principled('floor', (0.035, 0.036, 0.04) if studio == 'dark' else (0.62, 0.63, 0.65), rough=0.35 if studio == 'dark' else 0.6, spec=0.5),
    }
    from car_zones import fields
    try:
        base = trimesh.load('v6/car/out/car_body_base.ply', process=False)
        assert len(base.vertices) == len(car.vertices)
        # zones from the un-conformed body. The normal components the zone tests read get extra isotropic smoothing
        # (the position terms stay exact), so edges set by a normal test, like the side windows' top edge, are clean.
        from car_zones import smooth_fields
        Nb = cached_normals(base, 'base')
        Ns = smooth_fields({'x': Nb[:, 0], 'y': Nb[:, 1], 'z': Nb[:, 2]}, np.asarray(base.faces), len(base.vertices), iters=25)
        Nz = np.column_stack([Ns['x'], Ns['y'], Ns['z']]); Nz /= np.maximum(np.linalg.norm(Nz, axis=1, keepdims=True), 1e-9)
        Fz = fields(base.vertices, Nz)
        cov = np.load('v6/car/out/covered.npy')
        Fz['hidden'] = (cov * 2 - 1) * 10.0
        # only the binary under-spoiler mask is smoothed: uniform smoothing on this irregular mesh drifts the
        # positional fields sideways and gave saw-tooth zone edges; the other fields are smooth already
        Fz['hidden'] = smooth_fields({'hidden': Fz['hidden']}, np.asarray(base.faces), len(base.vertices), iters=20)['hidden']
        Fz['hidden'] = Fz['hidden'] - 2.0
    except Exception as e:
        print('zones from conformed body', e); Fz = fields(car.vertices, car.vertex_normals)
    body_mat = zone_material(M, list(Fz.keys()))
    ob = new_mesh('car_body', car, [body_mat], normals=cached_normals(car, 'conf') if NORMALS else None)
    me = ob.data
    for nm, arr in Fz.items():
        at = me.attributes.new('z_' + nm, 'FLOAT', 'POINT'); at.data.foreach_set('value', np.clip(arr, -50, 50).astype(np.float32))
    for k in ['tyre', 'rim', 'disc', 'caliper']:
        new_mesh(k, trimesh.load(f'v6/car/out/{k}.stl'), [M[k]], auto=35)
    for k, mk, au in [('ribbons', 'gap', None), ('handles', 'paint', 40), ('mirrors', 'paint', 40), ('plates', 'plate', 30)]:
        try: new_mesh(k, trimesh.load(f'v6/car/out/{k}.stl'), [M[mk]], auto=au)
        except Exception as e: print('skip', k, e)
    # plate lettering (Michroma), rear plate sits at the tailgate centre
    try:
        pl = trimesh.load('v6/car/out/plates.stl'); c = to_bl(pl.vertices).mean(0); ymin = to_bl(pl.vertices)[:, 1].min()
        fnt = bpy.data.fonts.load(os.path.abspath('v6/brochure/assets/fonts/michroma.ttf'))
        cu = bpy.data.curves.new('plate_txt', 'FONT'); cu.body = 'CARBON 6'; cu.font = fnt; cu.size = 0.062; cu.extrude = 0.0006
        cu.align_x = 'CENTER'; cu.align_y = 'CENTER'
        tob = bpy.data.objects.new('plate_txt', cu); bpy.context.collection.objects.link(tob)
        tob.rotation_euler = (math.radians(90), 0, 0); tob.location = (c[0], ymin - 0.0006, c[2])
        cu.materials.append(M['ink'])
    except Exception as e: print('plate text failed', e)
    # the finished spoiler is one painted part (seams filled), i.e. the solid envelope the three pieces are cut from
    sp_m = trimesh.load('v6/out/E2.stl')
    if NORMALS: new_mesh('spoiler', sp_m, [M['spoiler']], loop_normals=spoiler_normals(sp_m))
    else: new_mesh('spoiler', sp_m, [M['spoiler']], auto=30)
    # floor
    bpy.ops.mesh.primitive_plane_add(size=60, location=(0, 1.6, 0)); fl = bpy.context.active_object; fl.data.materials.append(M['floor'])
    # world
    w = bpy.data.worlds.new('world'); sc.world = w; w.use_nodes = True
    bg = w.node_tree.nodes['Background']; bg.inputs['Color'].default_value = ((0.004, 0.0045, 0.005, 1) if studio == 'dark' else (0.8, 0.8, 0.82, 1)); bg.inputs['Strength'].default_value = 1.0
    lights_only(sc)
    return sc

VIEWS = {
    'hero': ((-3.95, -4.55, 2.85), (0.10, 0.40, 0.92), 70),
    'top_rear': ((0.0, -3.3, 3.9), (0.0, 0.35, 1.20), 55),
    'fin': ((-1.35, -1.30, 1.98), (-0.48, 0.06, 1.36), 58),
    'rear': ((0.0, -7.6, 1.75), (0.0, 0.0, 1.0), 70),
    'parts': ((0.50, -1.12, 1.30), (0.0, 0.0, 0.03), 36),
    'joint': ((0.62, -0.78, 0.70), (0.20, -0.10, 0.03), 40),
    # name: (camera location m, target m, focal mm)
    'rear34': ((-4.35, -5.10, 2.05), (0.0, 0.25, 0.95), 70),
    'rear34_high': ((-3.6, -4.4, 3.3), (0.0, 0.0, 1.05), 60),
    'side': ((-12.5, 1.42, 1.0), (0.0, 1.42, 0.66), 70),
    'detail': ((-1.65, -1.55, 1.95), (-0.35, 0.10, 1.38), 70),
    'front34': ((4.6, 6.4, 1.6), (0.0, 1.5, 0.75), 70),
}

def camera(view):
    from mathutils import Vector
    loc, tgt, f = VIEWS[view]
    cam = bpy.data.cameras.new('cam'); cam.lens = f; cam.sensor_width = 36
    o = bpy.data.objects.new('cam', cam); o.location = loc; bpy.context.collection.objects.link(o)
    d = Vector(tgt) - Vector(loc); o.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    bpy.context.scene.camera = o
    return o

if __name__ == '__main__':
    view, out, W, H, spp = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5])
    kw = dict(a.split('=') for a in sys.argv[6:])
    if kw.get('debug') == '1': DEBUG_ZONES = True
    if kw.get('normals') == '0': NORMALS = False
    if view in ('parts', 'joint'):
        sc, dz = build_parts(view, studio=kw.get('studio', 'light'))
        lights_only(sc)
    else:
        sc = build(paint=kw.get('paint', 'white'), studio=kw.get('studio', 'dark'), car_path=kw.get('car', 'v6/car/out/car_body_conf.ply'))
    if 'cam' in kw:        # cam=x,y,z,tx,ty,tz,focal overrides the named view (for framing tests)
        c = list(map(float, kw['cam'].split(','))); VIEWS[view] = (tuple(c[:3]), tuple(c[3:6]), c[6])
    camera(view)
    sc.render.resolution_x = W; sc.render.resolution_y = H; sc.render.resolution_percentage = 100
    sc.cycles.samples = spp
    if 'border' in kw:     # border=x0,y0,x1,y1 as image fractions, y from the top: render only that window
        x0, y0, x1, y1 = map(float, kw['border'].split(','))
        sc.render.use_border = True; sc.render.use_crop_to_border = True
        sc.render.border_min_x, sc.render.border_max_x = x0, x1
        sc.render.border_min_y, sc.render.border_max_y = 1.0 - y1, 1.0 - y0
    sc.render.filepath = out
    import time; t = time.time()
    bpy.ops.render.render(write_still=True)
    print('rendered', out, '%.1fs' % (time.time() - t))
