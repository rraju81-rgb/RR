"""
Universal M-Style Rear Trunk Lip Spoiler, 98 cm, for hatchback and sedan.

Parametric Blender model. All dimensions are in millimetres.
Axes:  X = across the car (left/right), Y = fore/aft (+Y = towards rear bumper), Z = up.
The underside (mounting face) sits on Z = 0 at the centre of the span.

Run headless:
    blender -b -P build_spoiler.py -- [--out OUTPUT_DIR] [--render]
"""
import bpy, bmesh, math, os, sys
from mathutils import Vector

# ---------------------------------------------------------------- parameters
# Shape matched to the reference product photos (Zelix "Universal M-Style Rear
# Spoiler 98cm"): a roof/hatch wing whose outer sections are deeper and raised,
# joined to a shorter centre section by an angled step; angle-cut tips that turn
# down into small end plates; thin gloss blade with a flat mounting pad up front.
P = dict(
    length        = 980.0,  # overall tip-to-tip length (98 cm)
    chord_center  = 72.0,   # front-to-back depth of the centre section
    chord_outer   = 100.0,  # depth of the outer (stepped) wing sections
    step_at       = 0.40,   # |x|/half where the step starts (fraction of half span)
    step_len      = 0.10,   # span fraction over which the angled step happens
    outer_raise   = 6.0,    # outer wings sit higher than the centre at the trailing edge
    nose_thick    = 15.0,   # thickness at the mounting nose
    te_height     = 9.0,    # trailing edge top height above the mount face (centre)
    te_thick      = 2.2,    # trailing edge thickness
    kick          = 4.0,    # upturn of the trailing edge (gurney-style kick)
    pad_frac      = 0.38,   # flat adhesive mounting pad as a fraction of chord
    tip_cut       = 0.11,   # span fraction of the angled tip cut
    endplate_drop = 24.0,   # how far the tips turn down (end plates)
    plan_sweep    = 30.0,   # tips pulled forward in plan view (follows roof curve)
    crown_drop    = 16.0,   # tips drop down (follows roof crown)
    stations      = 301,
    prof_pts      = 40,
)

def smooth(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)

def section(x):
    """Closed cross-section polygon (list of (y, z)) at span position x.
    y = rearward from the nose, z = up from the mounting face."""
    half = P["length"] / 2
    u = abs(x) / half
    step = smooth((u - P["step_at"]) / P["step_len"])        # 0 centre -> 1 outer
    chord = P["chord_center"] + (P["chord_outer"] - P["chord_center"]) * step
    raise_ = P["outer_raise"] * step
    # angled tip cut: the trailing edge sweeps forward over the last tip_cut of span
    tc = smooth((u - (1 - P["tip_cut"])) / P["tip_cut"])
    chord *= (1 - 0.55 * tc)
    # end plate: the rear of the blade turns down at the very tips
    ep = smooth((u - (1 - P["tip_cut"])) / P["tip_cut"]) ** 2
    drop = P["endplate_drop"] * ep

    y0 = -P["plan_sweep"] * u ** 2
    z0 = -P["crown_drop"] * u ** 2
    nose = P["nose_thick"] * (1 - 0.35 * tc)
    te_top = P["te_height"] + raise_
    te_bot = te_top - P["te_thick"]
    pad = P["pad_frac"] * chord

    n = P["prof_pts"]
    # rounded nose (front face), mount face -> top
    pts = [(0.0, 0.0), (1.2, nose * 0.5), (2.5, nose * 0.85), (4.5, nose)]
    # top surface: nose -> trailing edge; slight fall then the ducktail kick
    for i in range(1, n + 1):
        s = i / n
        y = 4.5 + s * (chord - 4.5)
        base = nose + (te_top - nose) * (1 - (1 - s) ** 1.6)
        k = P["kick"] * (1 - ep) * smooth((s - 0.82) / 0.18) ** 1.4
        z = base + k - 0.35 * drop * smooth((s - 0.45) / 0.55)
        pts.append((y, z))
    # trailing edge face
    pts.append((chord + 0.6, pts[-1][1] - P["te_thick"] * 0.5))
    # underside: trailing edge -> end of pad (thin blade, rising underside)
    for i in range(n, -1, -1):
        s = i / n
        y = pad + s * (chord - pad)
        zt = te_bot + P["kick"] * (1 - ep) * smooth((s - 0.82) / 0.18) ** 1.4
        sg = (y - 4.5) / (chord - 4.5)              # same parameter as the top surface
        # at the tips the underside fills down into a solid end-plate wedge
        z = zt * (s ** 1.25) * (1 - ep) - drop * smooth((sg - 0.30) / 0.70)
        pts.append((y, z))
    # flat mounting pad back to the nose
    for i in range(1, 5):
        pts.append((pad * (1 - i / 5), 0.0))
    return [(y0 + y, z0 + z) for (y, z) in pts]

# ---------------------------------------------------------------- build mesh
def build():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    me = bpy.data.meshes.new("M_Style_Spoiler_98cm")
    bm = bmesh.new()
    half = P["length"] / 2
    N = P["stations"]
    rings = []
    for j in range(N):
        t = -1 + 2 * j / (N - 1)
        # cluster stations towards the tips for a clean rounded end
        x = half * math.copysign(abs(t) ** 0.92, t)
        rings.append([bm.verts.new((x, y, z)) for (y, z) in section(x)])
    m = len(rings[0])
    for a, b in zip(rings[:-1], rings[1:]):
        for i in range(m):
            bm.faces.new((a[i], a[(i + 1) % m], b[(i + 1) % m], b[i]))
    capL = bm.faces.new(list(reversed(rings[0])))
    capR = bm.faces.new(rings[-1])
    bmesh.ops.triangulate(bm, faces=[capL, capR])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(me.name, me)
    bpy.context.scene.collection.objects.link(ob)
    for f in me.polygons:
        f.use_smooth = True
    if hasattr(me, "use_auto_smooth"):          # crisp creases at step, lip and tips
        me.use_auto_smooth = True
        me.auto_smooth_angle = math.radians(40)
    return ob

def material(ob):
    mat = bpy.data.materials.new("Gloss_Black_ABS")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (0.012, 0.012, 0.014, 1)
    bsdf.inputs["Roughness"].default_value = 0.08
    if "Coat Weight" in bsdf.inputs:
        bsdf.inputs["Coat Weight"].default_value = 1.0
    ob.data.materials.append(mat)

# ---------------------------------------------------------------- export
def export(ob, out):
    os.makedirs(out, exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    base = os.path.join(out, "m_style_spoiler_98cm")
    bpy.ops.export_mesh.stl(filepath=base + ".stl", use_selection=True, global_scale=1.0)
    bpy.ops.wm.obj_export(filepath=base + ".obj", export_selected_objects=True,
                          export_materials=True)
    # glTF is metres -> temporarily scale mm to m
    ob.scale = (0.001, 0.001, 0.001)
    bpy.ops.export_scene.gltf(filepath=base + ".glb", use_selection=True, export_format="GLB")
    ob.scale = (1, 1, 1)

# ---------------------------------------------------------------- render
def render(ob, out):
    """Studio renders at real-world scale (metres)."""
    ob.scale = (0.001, 0.001, 0.001)
    scn = bpy.context.scene
    scn.render.engine = "CYCLES"
    scn.cycles.device = "CPU"
    scn.cycles.samples = 128
    scn.cycles.use_denoising = False
    scn.render.resolution_x, scn.render.resolution_y = 1600, 900
    scn.view_settings.exposure = -0.3
    world = bpy.data.worlds.new("W"); scn.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.55, 0.56, 0.58, 1)
    world.node_tree.nodes["Background"].inputs[1].default_value = 0.25
    bpy.context.view_layer.update()
    zmin = min((ob.matrix_world @ v.co).z for v in ob.data.vertices)
    bpy.ops.mesh.primitive_plane_add(size=20, location=(0, 0, zmin - 0.0005))
    fl = bpy.context.active_object
    fm = bpy.data.materials.new("Floor"); fm.use_nodes = True
    fm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.75, 0.76, 0.78, 1)
    fm.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.45
    fl.data.materials.append(fm)
    # long strip softboxes -> crisp reflections along the glossy lip
    for loc, en, sx, sy in [((0, 0.6, 1.0), 120, 2.4, 0.25), ((-1.4, -0.8, 0.9), 45, 1.0, 1.0),
                            ((1.4, -0.4, 0.6), 35, 1.0, 1.0), ((0, -1.2, 0.5), 25, 2.0, 0.3)]:
        L = bpy.data.lights.new("A", "AREA"); L.energy = en
        L.shape = "RECTANGLE"; L.size = sx; L.size_y = sy
        lo = bpy.data.objects.new("A", L); lo.location = loc
        scn.collection.objects.link(lo)
        lo.rotation_euler = (Vector((0, 0.02, 0)) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    cam = bpy.data.cameras.new("C"); cam.clip_start = 0.01; cam.clip_end = 50
    co = bpy.data.objects.new("C", cam); scn.collection.objects.link(co); scn.camera = co
    views = {  # name: (camera location, look-at target, focal length)
        "render_3q_rear":  ((-0.75, 1.05, 0.52), (0, 0.015, 0.0), 45),
        "render_front_3q": ((0.85, -0.95, 0.45), (0, 0.015, 0.0), 45),
        "render_top":      ((0, 0.01, 1.9),      (0, 0.0, 0.0),   50),
        "render_tip_detail": ((-0.78, 0.38, 0.22), (-0.40, 0.02, -0.01), 55),
        "render_rear":     ((0, 1.6, 0.18),      (0, 0.02, 0.0),  50),
    }
    for name, (loc, tgt, lens) in views.items():
        co.location = loc; cam.lens = lens
        co.rotation_euler = (Vector(tgt) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
        scn.render.filepath = os.path.join(out, name + ".png")
        bpy.ops.render.render(write_still=True)
    ob.scale = (1, 1, 1)

if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out = argv[argv.index("--out") + 1] if "--out" in argv else os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
    ob = build()
    material(ob)
    export(ob, out)
    bpy.context.view_layer.update()
    d = ob.dimensions
    print(f"BBOX mm  X={d.x:.1f}  Y={d.y:.1f}  Z={d.z:.1f}  tris={len(ob.data.polygons)}")
    if "--render" in argv:
        render(ob, out)
