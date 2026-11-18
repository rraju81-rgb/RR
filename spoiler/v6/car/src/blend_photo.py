"""Outdoor, photo-style Cycles scene of the Polo-class car with the spoiler, styled after the customer's reference photo
(blue hot hatch, rear three-quarter view): blue metallic paint, gloss-black spoiler, mirror caps and 18" multi-spoke
wheels, red calipers, smoked tail lamps, black diffuser with fins and twin exhaust, black side-skirt lips, lowered
20 mm, under an overcast sky on asphalt.
Environment: Poly Haven CC0 assets in v6/car/env/ (HDRI kloofendal_overcast_puresky, texture asphalt_pit_lane).
Usage (from spoiler/):  python3 v6/car/src/blend_photo.py <view> <out.png> <W> <H> <samples> [paint=blue|white|red|grey] [cam=x,y,z,tx,ty,tz,f]
The car keeps the spoiler's frame and the same body, fit and zones as blend_scene.py; no badges or logos."""
import os, sys, math, numpy as np
sys.path.insert(0, 'v6/car/src')
import bpy, trimesh, manifold3d as mf
from mathutils import Vector
import blend_scene as BS
from car_body import Z_F, Y_G, S_FA, S_RA, TRACK, s_of, h_of
from trimesh.ray.ray_pyembree import RayMeshIntersector
ENV = 'v6/car/env'
DROP = 0.028                     # body lowered 28 mm on its wheels (m)
R_TYRE, W_TYRE, R_RIM = 323.0, 225.0, 229.0      # 225/40 R18 (fills the arches like the lowered car in the photo)
PAINTS = {'blue': (0.0035, 0.032, 0.34), 'white': (0.62, 0.63, 0.64), 'red': (0.42, 0.012, 0.016), 'grey': (0.20, 0.21, 0.22)}

def to_tm(M):
    g = M.to_mesh(); return trimesh.Trimesh(np.asarray(g.vert_properties[:, :3]), np.asarray(g.tri_verts), process=True)

def rim18(spokes=10):
    """18" multi-spoke alloy, concave: barrel + dished face with 10 straight spokes (axis z, outer face at +z)"""
    r, hw = R_RIM, W_TYRE / 2 - 12
    barrel = mf.Manifold.cylinder(2 * hw, r, r, 128).translate([0, 0, -hw]) - mf.Manifold.cylinder(2 * hw + 2, r - 8, r - 8, 128).translate([0, 0, -hw - 1])
    lip = mf.Manifold.cylinder(12, r + 6, r + 6, 128).translate([0, 0, hw - 12]) - mf.Manifold.cylinder(14, r - 14, r - 14, 128).translate([0, 0, hw - 13])
    face = mf.Manifold.cylinder(26, r - 10, r - 10, 160).translate([0, 0, hw - 46])          # set back: concave look
    hub = mf.Manifold.cylinder(34, 74, 58, 64).translate([0, 0, hw - 50])
    for k in range(spokes):
        a = 2 * np.pi * (k + 0.5) / spokes; da = np.pi / spokes
        r0, r1 = 82.0, r - 18.0
        P = np.array([[r0 * np.cos(a - da * 0.55), r0 * np.sin(a - da * 0.55)], [r1 * np.cos(a - da * 0.80), r1 * np.sin(a - da * 0.80)],
                      [r1 * np.cos(a + da * 0.80), r1 * np.sin(a + da * 0.80)], [r0 * np.cos(a + da * 0.55), r0 * np.sin(a + da * 0.55)]])
        cs = mf.CrossSection([P]).offset(-7, mf.JoinType.Round).offset(7, mf.JoinType.Round)
        face = face - cs.extrude(40).translate([0, 0, hw - 50])
    # spokes run up to the outer lip: thin ribs from the face to the lip plane give depth (concave profile)
    ribs = []
    for k in range(spokes):
        a = 2 * np.pi * k / spokes
        rib = mf.Manifold.cube([r - 60, 16, 22], True).translate([(r - 60) / 2 + 52, 0, hw - 30])
        ribs.append(rib.rotate([0, 0, math.degrees(a)]))
    M = barrel + lip + face + hub
    for rb in ribs: M = M + (rb - mf.Manifold.cylinder(60, 70, 70, 48).translate([0, 0, hw - 60]))
    nuts = [mf.Manifold.cylinder(10, 8, 8, 20).translate([46 * np.cos(2 * np.pi * k / 5), 46 * np.sin(2 * np.pi * k / 5), hw - 17]) for k in range(5)]
    for n_ in nuts: M = M + n_
    cap = mf.Manifold.cylinder(6, 30, 30, 48).translate([0, 0, hw - 17])
    m = to_tm(M + cap); m.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [0, 1, 0]))   # axis z -> x
    return m

def tyre18():
    """215/40 R18: low sidewall with a rounded shoulder (revolved), axis x"""
    R, hw, rr = R_TYRE, W_TYRE / 2, R_RIM
    prof = [(rr - 4, -hw + 14), (rr + 4, -hw + 3)]
    for k in np.linspace(0, 1, 10)[1:]: prof.append((rr + 4 + k * (R - 22 - rr - 4), -hw - 3.5 * np.sin(np.pi * k)))
    for a in np.linspace(0, np.pi / 2, 9)[1:]: prof.append((R - 22 + 22 * np.sin(a), -hw + 22 - 22 * np.cos(a)))
    for k in np.linspace(0, 1, 7)[1:-1]: prof.append((R + 1.0 * np.sin(np.pi * k), -hw + 22 + k * (2 * hw - 44)))
    for a in np.linspace(np.pi / 2, np.pi, 9)[:-1]: prof.append((R - 22 + 22 * np.sin(a), hw - 22 - 22 * np.cos(a)))
    for k in np.linspace(0, 1, 10)[:-1]: prof.append((R - 22 - k * (R - 22 - rr - 4), hw + 3.5 * np.sin(np.pi * k)))
    prof += [(rr + 4, hw - 3), (rr - 4, hw - 14)]
    from car_parts import revolve
    return revolve(prof, n=160)

def brakes():
    disc = trimesh.creation.annulus(r_min=60, r_max=168, height=26, sections=128)
    disc.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [0, 1, 0]))
    cal = trimesh.creation.box(extents=[56, 100, 150]); cal.vertices[:, 1] *= np.where(cal.vertices[:, 2] > 0, 0.85, 1.0)
    cal.apply_translation([-26, 0, 0]); cal.apply_transform(trimesh.transformations.rotation_matrix(-0.55, [1, 0, 0]))
    cal.apply_translation([0, 0, 168 - 36])
    return disc, cal

def wheels():
    out = {'tyre': [], 'rim': [], 'disc': [], 'caliper': []}
    T, Rm = tyre18(), rim18(); D, Ca = brakes()
    for sa in (S_FA, S_RA):
        z = Z_F + sa; y = Y_G + R_TYRE - 7.0
        for side in (-1, 1):
            xc = side * (TRACK / 2 + 8.0)
            for key, m in (('tyre', T), ('rim', Rm), ('disc', D), ('caliper', Ca)):
                mm = m.copy()
                if side < 0: mm.apply_transform(np.diag([-1, 1, 1, 1])); mm.invert()
                off = {'tyre': 0, 'rim': 0, 'disc': -side * 62, 'caliper': -side * 58}[key]
                mm.apply_translation([xc + off, y, z]); out[key].append(mm)
    return {k: trimesh.util.concatenate(v) for k, v in out.items()}

def rear_parts(car):
    """diffuser fins, twin exhaust tips, rear reflectors (car frame, mm)"""
    R = RayMeshIntersector(car)
    def rear_z(x, h):                        # z of the rear surface at lateral x and height h
        o = np.array([[x, Y_G + h, Z_F + 6000.0]]); loc, ir, it = R.intersects_location(o, [[0, 0, -1.0]], multiple_hits=False)
        return loc[0][2] if len(loc) else None
    fins = []
    for x in (-180.0, -90.0, 0.0, 90.0, 180.0, 270.0):
        zr = rear_z(x, 250.0)
        if zr is None: continue
        f = trimesh.creation.box(extents=[5.0, 120.0, 300.0]); f.vertices[:, 1] -= np.where(f.vertices[:, 2] > 0, 22.0 * (f.vertices[:, 2] / 150.0), 0)
        f.apply_translation([x, Y_G + 205.0, zr - 140.0]); fins.append(f)
    tips = []
    for x in (-470.0, -365.0):
        zr = rear_z(x, 255.0)
        if zr is None: continue
        t = trimesh.creation.annulus(r_min=38.0, r_max=44.0, height=90.0, sections=72)          # axis z
        t.apply_translation([x, Y_G + 252.0, zr - 30.0]); tips.append(t)
        inner = trimesh.creation.cylinder(radius=38.5, height=8.0, sections=72); inner.apply_translation([x, Y_G + 252.0, zr - 52.0]); tips.append(inner)
    refl = []
    for side in (-1, 1):
        x = side * 690.0; zr = rear_z(x, 330.0)
        if zr is None: continue
        b = trimesh.creation.box(extents=[110.0, 22.0, 10.0]); b.apply_translation([x, Y_G + 330.0, zr + 1.0]); refl.append(b)
    return dict(fins=trimesh.util.concatenate(fins), tips=trimesh.util.concatenate(tips) if tips else None,
                reflectors=trimesh.util.concatenate(refl) if refl else None)

def skirt_lips(car):
    """thin black blade along each sill: 26 mm proud of the side, 7 mm thick, from behind the front arch to the rear arch"""
    R = RayMeshIntersector(car); out = []
    s_vals = np.linspace(S_FA + 400.0, S_RA - 395.0, 60); h = 228.0
    for side in (-1, 1):
        P = []
        for s in s_vals:
            o = np.array([[side * 1500.0, Y_G + h, Z_F + s]]); loc, ir, it = R.intersects_location(o, [[-side, 0, 0.0]], multiple_hits=False)
            if len(loc): P.append(loc[0])
        P = np.array(P); n = len(P)
        if n < 4: continue
        V = []
        for p in P:
            x0 = p[0] - side * 4.0; x1 = p[0] + side * 26.0
            V += [[x0, p[1] + 3.5, p[2]], [x1, p[1] + 1.0, p[2]], [x1, p[1] - 6.0, p[2]], [x0, p[1] - 3.5, p[2]]]
        V = np.array(V); F = []
        for i in range(n - 1):
            for k in range(4):
                a, b = i * 4 + k, i * 4 + (k + 1) % 4; c, d = a + 4, b + 4
                F += [[a, b, d], [a, d, c]]
        F += [[0, 2, 1], [0, 3, 2], [(n - 1) * 4, (n - 1) * 4 + 1, (n - 1) * 4 + 2], [(n - 1) * 4, (n - 1) * 4 + 2, (n - 1) * 4 + 3]]
        m = trimesh.Trimesh(V, np.array(F), process=True); trimesh.repair.fix_normals(m); out.append(m)
    return trimesh.util.concatenate(out)


def zone_material_photo(M, names):
    """as blend_scene.zone_material, with two extra zones in the tail lamps: a silver rim and a red LED strip"""
    order = [('plastic', 'plastic_black'), ('glass', 'glass'), ('trim', 'trim_black'), ('tail', 'tail_lamp'),
             ('tailrim', 'lamp_rim'), ('led', 'tail_led'), ('rev', 'rev_lamp'), ('head', 'head_lamp'), ('chrome', 'grille_chrome'),
             ('hidden', 'tape')]
    order = [o for o in order if o[0] in names]
    saved = None
    import blend_scene as _bs
    src = _bs.zone_material.__code__
    m = bpy.data.materials.new('body'); nt = m.node_tree
    for n in list(nt.nodes): nt.nodes.remove(n)
    out = nt.nodes.new('ShaderNodeOutputMaterial'); bsdf = nt.nodes.new('ShaderNodeBsdfPrincipled')
    nt.links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])
    def val(mat, key): return mat.node_tree.nodes.get('Principled BSDF').inputs[key].default_value
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

def mat_paint(name, base):
    """metallic car paint with clear coat; fine flake noise on the base roughness"""
    m = BS.principled(name, base, rough=0.30, metal=0.50, coat=1.0, coat_rough=0.012)
    return m

def world_and_ground(sc, hdri='shudu_lake_2k.hdr', rot_deg=230.0, strength=1.0, haze_col=(0.50, 0.53, 0.57)):
    w = bpy.data.worlds.new('world'); sc.world = w; w.use_nodes = True; nt = w.node_tree
    for n in list(nt.nodes): nt.nodes.remove(n)
    out = nt.nodes.new('ShaderNodeOutputWorld'); bg = nt.nodes.new('ShaderNodeBackground')
    env = nt.nodes.new('ShaderNodeTexEnvironment'); env.image = bpy.data.images.load(os.path.abspath(f'{ENV}/{hdri}'))
    tc = nt.nodes.new('ShaderNodeTexCoord'); mp = nt.nodes.new('ShaderNodeMapping'); mp.inputs['Rotation'].default_value[2] = math.radians(rot_deg)
    nt.links.new(tc.outputs['Generated'], mp.inputs['Vector']); nt.links.new(mp.outputs['Vector'], env.inputs['Vector'])
    nt.links.new(env.outputs['Color'], bg.inputs['Color']); bg.inputs['Strength'].default_value = strength
    nt.links.new(bg.outputs['Background'], out.inputs['Surface'])
    # asphalt ground, 2 km wide; fades to the horizon haze with distance (cheap aerial perspective)
    bpy.ops.mesh.primitive_plane_add(size=2000.0, location=(0, 0, 0)); g = bpy.context.active_object; g.name = 'ground'
    m = bpy.data.materials.new('asphalt'); m.use_nodes = True; nt = m.node_tree; b = nt.nodes.get('Principled BSDF')
    tc = nt.nodes.new('ShaderNodeTexCoord'); mp = nt.nodes.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (0.42, 0.42, 0.42)
    nt.links.new(tc.outputs['Object'], mp.inputs['Vector'])
    def img(fn, cs):
        t = nt.nodes.new('ShaderNodeTexImage'); t.image = bpy.data.images.load(os.path.abspath(f'{ENV}/{fn}')); t.image.colorspace_settings.name = cs
        nt.links.new(mp.outputs['Vector'], t.inputs['Vector']); return t
    dif = img('asphalt_pit_lane_diff_2k.jpg', 'sRGB'); rough = img('asphalt_pit_lane_rough_2k.jpg', 'Non-Color'); nor = img('asphalt_pit_lane_nor_gl_2k.jpg', 'Non-Color')
    darken = nt.nodes.new('ShaderNodeMix'); darken.data_type = 'RGBA'; darken.blend_type = 'MULTIPLY'; darken.inputs[0].default_value = 1.0
    nt.links.new(dif.outputs['Color'], darken.inputs[6]); darken.inputs[7].default_value = (0.80, 0.81, 0.84, 1)
    # distance haze: mix the asphalt colour towards a pale grey-blue with camera distance
    cam = nt.nodes.new('ShaderNodeCameraData'); ramp = nt.nodes.new('ShaderNodeMapRange')
    ramp.inputs['From Min'].default_value = 25.0; ramp.inputs['From Max'].default_value = 420.0
    nt.links.new(cam.outputs['View Distance'], ramp.inputs['Value'])
    haze = nt.nodes.new('ShaderNodeMix'); haze.data_type = 'RGBA'
    nt.links.new(ramp.outputs['Result'], haze.inputs[0]); nt.links.new(darken.outputs[2], haze.inputs[6]); haze.inputs[7].default_value = (*haze_col, 1)
    nt.links.new(haze.outputs[2], b.inputs['Base Color'])
    rr = nt.nodes.new('ShaderNodeMapRange'); rr.inputs['To Min'].default_value = 0.55; rr.inputs['To Max'].default_value = 0.95
    nt.links.new(rough.outputs['Color'], rr.inputs['Value']); nt.links.new(rr.outputs['Result'], b.inputs['Roughness'])
    nm = nt.nodes.new('ShaderNodeNormalMap'); nm.inputs['Strength'].default_value = 0.6
    nt.links.new(nor.outputs['Color'], nm.inputs['Color']); nt.links.new(nm.outputs['Normal'], b.inputs['Normal'])
    b.inputs['Specular IOR Level'].default_value = 0.35
    g.data.materials.append(m)
    return g

def build_photo(paint='blue'):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    car = trimesh.load('v6/car/out/car_body_conf.ply', process=False)
    P = BS.principled
    M = {
        'paint': mat_paint('paint', PAINTS[paint]),
        'glass': P('glass', (0.0015, 0.0018, 0.002), rough=0.02, spec=0.24),
        'trim_black': P('trim_black', (0.008, 0.008, 0.009), rough=0.06, coat=0.8, coat_rough=0.02),
        'plastic_black': P('plastic_black', (0.012, 0.012, 0.013), rough=0.42, spec=0.4),
        'tail_lamp': P('tail_lamp_smoked', (0.020, 0.0015, 0.002), rough=0.04, coat=1.0, coat_rough=0.01, emis=(1.0, 0.02, 0.01), emis_str=0.18),
        'lamp_rim': P('lamp_rim_silver', (0.42, 0.43, 0.45), rough=0.12, metal=0.9, coat=1.0, coat_rough=0.02),
        'tail_led': P('tail_led', (0.35, 0.01, 0.01), rough=0.1, coat=1.0, emis=(1.0, 0.03, 0.015), emis_str=2.6),
        'rev_lamp': P('rev_lamp_smoked', (0.05, 0.05, 0.055), rough=0.04, coat=1.0, coat_rough=0.01),
        'head_lamp': P('head_lamp', (0.62, 0.64, 0.66), rough=0.05, metal=0.7, coat=1.0),
        'grille_chrome': P('chrome', (0.05, 0.05, 0.055), rough=0.08, coat=0.8),
        'tyre': P('tyre', (0.022, 0.022, 0.024), rough=0.82, spec=0.3),
        'rim': P('rim_gloss_black', (0.010, 0.010, 0.011), rough=0.10, metal=0.3, coat=1.0, coat_rough=0.03),
        'disc': P('disc', (0.33, 0.33, 0.34), rough=0.38, metal=0.9),
        'caliper': P('caliper_red', (0.55, 0.012, 0.012), rough=0.25, coat=0.9),
        'spoiler': P('spoiler_gloss_black', (0.010, 0.010, 0.011), rough=0.08, coat=1.0, coat_rough=0.015),
        'mirror': P('mirror_gloss_black', (0.010, 0.010, 0.011), rough=0.08, coat=1.0, coat_rough=0.015),
        'gap': P('gap', (0.004, 0.004, 0.004), rough=0.9),
        'tape': P('tape', (0.006, 0.006, 0.006), rough=0.85),
        'plate': P('plate', (0.80, 0.80, 0.78), rough=0.35),
        'ink': P('ink', (0.01, 0.01, 0.01), rough=0.4),
        'tip': P('exhaust_tip', (0.30, 0.30, 0.32), rough=0.18, metal=1.0),
        'soot': P('soot', (0.006, 0.006, 0.006), rough=0.9),
        'reflector': P('reflector', (0.25, 0.004, 0.004), rough=0.08, coat=1.0, emis=(1.0, 0.03, 0.02), emis_str=0.25),
    }
    # zones, as blend_scene.build, plus black side sills
    from car_zones import fields, smooth_fields
    base = trimesh.load('v6/car/out/car_body_base.ply', process=False)
    Nb = BS.cached_normals(base, 'base')
    Ns = smooth_fields({'x': Nb[:, 0], 'y': Nb[:, 1], 'z': Nb[:, 2]}, np.asarray(base.faces), len(base.vertices), iters=25)
    Nz = np.column_stack([Ns['x'], Ns['y'], Ns['z']]); Nz /= np.maximum(np.linalg.norm(Nz, axis=1, keepdims=True), 1e-9)
    Fz = fields(base.vertices, Nz)
    V = np.asarray(base.vertices); s = s_of(V[:, 2]); h = h_of(V[:, 1])
    sill = np.minimum.reduce([s - (S_FA + 395.0), (S_RA - 390.0) - s, 262.0 - h])
    Fz['plastic'] = np.maximum(Fz['plastic'], sill)
    # larger lamps than blend_scene's, reaching further onto the tailgate like the Polo's two-part clusters
    ax = np.abs(V[:, 0]); a_in = np.maximum(805.0 - ax, 0.0)
    b_fw = np.maximum(np.interp(h, [774, 872, 958, 1013], [3910, 3880, 3842, 3796]) - s, 0.0)
    tl_hi = 1012.0 - 0.11 * a_in; tl_lo = 858.0 + 0.075 * a_in + 0.03 * b_fw
    tail_big = np.minimum.reduce([s - 3680.0, ax - 405.0, h - tl_lo, tl_hi - h])
    Fz['rev'] = np.minimum.reduce([tail_big, 610.0 - ax, 935.0 - h])   # reversing lamp: lower inner corner
    Fz['tail'] = np.minimum(tail_big, -Fz['rev'])
    lamp = np.maximum(Fz['tail'], Fz['rev'])                         # whole lamp (signed distance ~ mm, + inside)
    Fz['tailrim'] = np.minimum(lamp, 7.0 - lamp)                      # 7 mm silver rim round each lamp
    Fz['led'] = np.minimum.reduce([lamp - 15.0, 20.5 - lamp, -Fz['rev']])   # LED strip 15-20 mm inside the rim
    cov = np.load('v6/car/out/covered.npy')
    Fz['hidden'] = smooth_fields({'hidden': (cov * 2 - 1) * 10.0}, np.asarray(base.faces), len(base.vertices), iters=20)['hidden'] - 2.0
    body_mat = zone_material_photo(M, list(Fz.keys()))
    ob = BS.new_mesh('car_body', car, [body_mat], normals=BS.cached_normals(car, 'conf'))
    for nm, arr in Fz.items():
        at = ob.data.attributes.new('z_' + nm, 'FLOAT', 'POINT'); at.data.foreach_set('value', np.clip(arr, -50, 50).astype(np.float32))
    body_objs = [ob]
    for k, mk, au in [('ribbons', 'gap', None), ('handles', 'paint', 40), ('mirrors', 'mirror', 40), ('plates', 'plate', 30)]:
        try: body_objs.append(BS.new_mesh(k, trimesh.load(f'v6/car/out/{k}.stl'), [M[mk]], auto=au))
        except Exception as e: print('skip', k, e)
    try:
        pl = trimesh.load('v6/car/out/plates.stl'); c = BS.to_bl(pl.vertices).mean(0); ymin = BS.to_bl(pl.vertices)[:, 1].min()
        fnt = bpy.data.fonts.load(os.path.abspath('v6/brochure/assets/fonts/michroma.ttf'))
        cu = bpy.data.curves.new('plate_txt', 'FONT'); cu.body = 'CARBON 6'; cu.font = fnt; cu.size = 0.062; cu.extrude = 0.0006
        cu.align_x = 'CENTER'; cu.align_y = 'CENTER'
        tob = bpy.data.objects.new('plate_txt', cu); bpy.context.collection.objects.link(tob)
        tob.rotation_euler = (math.radians(90), 0, 0); tob.location = (c[0], ymin - 0.0006, c[2]); cu.materials.append(M['ink'])
        body_objs.append(tob)
    except Exception as e: print('plate text failed', e)
    sp_m = trimesh.load('v6/out/E2.stl')
    body_objs.append(BS.new_mesh('spoiler', sp_m, [M['spoiler']], loop_normals=BS.spoiler_normals(sp_m)))
    rp = rear_parts(car)
    body_objs.append(BS.new_mesh('diffuser_fins', rp['fins'], [M['plastic_black']], auto=30))
    if rp['tips'] is not None: body_objs.append(BS.new_mesh('exhaust_tips', rp['tips'], [M['tip']], auto=30))
    if rp['reflectors'] is not None: body_objs.append(BS.new_mesh('reflectors', rp['reflectors'], [M['reflector']], auto=30))
    body_objs.append(BS.new_mesh('skirt_lips', skirt_lips(car), [M['plastic_black']], auto=35))
    for o in body_objs: o.location.z -= DROP                         # lowered on its wheels
    W = wheels()
    for k in ('tyre', 'rim', 'disc', 'caliper'): BS.new_mesh(k, W[k], [M[k]], auto=35)
    world_and_ground(sc)
    sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.use_denoising = True
    try: sc.cycles.denoiser = 'OPENIMAGEDENOISE'
    except Exception: pass
    sc.render.threads_mode = 'FIXED'; sc.render.threads = int(os.environ.get('BL_THREADS', 4))
    sc.view_settings.view_transform = 'AgX'
    try: sc.view_settings.look = 'AgX - Medium High Contrast'
    except Exception: pass
    sc.view_settings.exposure = 0.0
    sc.cycles.max_bounces = 8; sc.cycles.glossy_bounces = 6; sc.cycles.sample_clamp_indirect = 3.0
    sc.cycles.use_adaptive_sampling = True; sc.cycles.adaptive_threshold = 0.02
    return sc

VIEWS = {   # (camera location m, target m, focal mm, f-stop)   Blender frame: X right, Y forward, Z up; car rear at Y = -0.58
    'photo': ((2.95, -5.35, 0.92), (0.10, 0.85, 0.78), 55, 5.6),       # the reference photo's view: right rear three-quarter, low
    'photo_left': ((-3.55, -5.75, 1.05), (-0.25, 0.75, 0.72), 70, 5.6),
    'rear_low': ((0.6, -7.4, 0.95), (0.0, 0.2, 0.85), 85, 5.6),
    'side': ((-12.5, 1.42, 1.0), (0.0, 1.42, 0.66), 70, 8.0),
    'top_rear': ((0.0, -3.3, 3.9), (0.0, 0.35, 1.20), 55, 8.0),
    'fin': ((1.35, -1.30, 1.98), (0.48, 0.06, 1.36), 58, 4.0),
    'front34': ((4.6, 6.4, 1.3), (0.0, 1.5, 0.70), 70, 5.6),
}
def camera(view):
    loc, tgt, f, fs = VIEWS[view]
    cam = bpy.data.cameras.new('cam'); cam.lens = f; cam.sensor_width = 36
    o = bpy.data.objects.new('cam', cam); o.location = loc; bpy.context.collection.objects.link(o)
    d = Vector(tgt) - Vector(loc); o.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    cam.dof.use_dof = True; cam.dof.focus_distance = d.length * 0.92; cam.dof.aperture_fstop = fs
    bpy.context.scene.camera = o
    return o


def build_spoiler_only(studio='dark'):
    """the finished spoiler alone (one painted part), gloss black, on a studio floor: product shot for the spec sheet"""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sp = trimesh.load('v6/out/E2.stl')
    mat = BS.principled('spoiler_gloss_black', (0.010, 0.010, 0.011), rough=0.08, coat=1.0, coat_rough=0.015)
    ob = BS.new_mesh('spoiler', sp, [mat], loop_normals=BS.spoiler_normals(sp))
    zmin = min((ob.matrix_world @ Vector(c)).z for c in ob.bound_box); ob.location.z -= zmin - 0.002
    bpy.ops.mesh.primitive_plane_add(size=30, location=(0, 0, 0)); fl = bpy.context.active_object
    fl.data.materials.append(BS.principled('floor', (0.030, 0.031, 0.035) if studio == 'dark' else (0.6, 0.61, 0.63), rough=0.35))
    w = bpy.data.worlds.new('world'); sc.world = w; w.use_nodes = True
    w.node_tree.nodes['Background'].inputs['Color'].default_value = (0.004, 0.0045, 0.005, 1) if studio == 'dark' else (0.6, 0.61, 0.63, 1)
    BS.lights_only(sc)
    sc.render.threads = int(os.environ.get('BL_THREADS', 4))
    return sc
VIEWS['spoiler_only'] = ((1.05, -1.25, 0.95), (0.0, 0.0, 0.03), 50, 8.0)

if __name__ == '__main__':
    view, out, Wd, Hd, spp = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5])
    kw = dict(a.split('=') for a in sys.argv[6:])
    sc = build_spoiler_only(kw.get('studio', 'dark')) if view == 'spoiler_only' else build_photo(paint=kw.get('paint', 'blue'))
    if 'cam' in kw:
        c = list(map(float, kw['cam'].split(','))); VIEWS[view] = (tuple(c[:3]), tuple(c[3:6]), c[6], c[7] if len(c) > 7 else 5.6)
    if 'hdri_rot' in kw: sc.world.node_tree.nodes['Mapping'].inputs['Rotation'].default_value[2] = math.radians(float(kw['hdri_rot']))
    camera(view)
    sc.render.resolution_x = Wd; sc.render.resolution_y = Hd; sc.render.resolution_percentage = 100
    sc.cycles.samples = spp; sc.render.filepath = out
    import time; t = time.time()
    bpy.ops.render.render(write_still=True)
    print('rendered', out, '%.1fs' % (time.time() - t))
