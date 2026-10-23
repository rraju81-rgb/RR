"""Render a scene described by a JSON file with Blender / Cycles.

    blender -b --factory-startup --python tools/blender_scene.py -- scene.json

Runs inside Blender's own Python.  Meshes are OBJ files in millimetres (model axes:
x across the paddle, y along it, z through the thickness); each paddle is parented to
an empty that places it in the studio (metres, Blender z up).
"""
import json
import math
import sys

import addon_utils
import bpy
from mathutils import Euler, Vector

cfg = json.load(open(sys.argv[sys.argv.index("--") + 1]))
bpy.ops.wm.read_factory_settings(use_empty=True)
addon_utils.enable("cycles", default_set=True)
sc = bpy.context.scene
sc.render.engine = "CYCLES"
sc.cycles.device = "CPU"
sc.cycles.samples = cfg.get("samples", 256)
sc.cycles.use_adaptive_sampling = True
sc.cycles.adaptive_threshold = cfg.get("noise_threshold", 0.01)
sc.cycles.use_denoising = False
sc.cycles.max_bounces = 8
sc.cycles.caustics_reflective = False
sc.cycles.caustics_refractive = False
sc.cycles.blur_glossy = 1.0
sc.render.resolution_x, sc.render.resolution_y = cfg["resolution"]
sc.render.resolution_percentage = 100
sc.render.image_settings.file_format = "PNG"
sc.render.image_settings.color_depth = "8"
sc.view_settings.view_transform = cfg.get("view_transform", "AgX")
sc.view_settings.look = cfg.get("look", "AgX - Base Contrast") if sc.view_settings.view_transform == "AgX" else "None"
sc.view_settings.exposure = cfg.get("exposure", 0.0)
sc.render.threads_mode = "FIXED"
sc.render.threads = cfg.get("threads", 4)


def set_input(node, names, value):
    for n in names if isinstance(names, (list, tuple)) else [names]:
        if n in node.inputs:
            node.inputs[n].default_value = value
            return


# ---------------------------------------------------------------- world
world = bpy.data.worlds.new("World")
sc.world = world
world.use_nodes = True
wn = world.node_tree.nodes
wl = world.node_tree.links
bg = wn["Background"]
grad = wn.new("ShaderNodeTexGradient")
ramp = wn.new("ShaderNodeValToRGB")
coord = wn.new("ShaderNodeTexCoord")
sep = wn.new("ShaderNodeSeparateXYZ")
wl.new(coord.outputs["Generated"], sep.inputs[0])
wl.new(sep.outputs["Z"], ramp.inputs[0])
ramp.color_ramp.elements[0].color = (*cfg.get("world_bottom", (0.55, 0.56, 0.58)), 1)
ramp.color_ramp.elements[1].color = (*cfg.get("world_top", (0.9, 0.92, 0.95)), 1)
wl.new(ramp.outputs[0], bg.inputs["Color"])
bg.inputs["Strength"].default_value = cfg.get("world_strength", 0.35)
del grad


# ---------------------------------------------------------------- materials
def image_texture(nt, path, tex_map, extension="CLIP"):
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    x0, y0, w, h = tex_map
    mp.inputs["Location"].default_value = (-x0 / w, -y0 / h, 0)
    mp.inputs["Scale"].default_value = (1 / w, 1 / h, 1)
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    img = nt.nodes.new("ShaderNodeTexImage")
    img.image = bpy.data.images.load(path)
    img.extension = extension
    img.interpolation = "Cubic"
    nt.links.new(mp.outputs["Vector"], img.inputs["Vector"])
    return img


def make_material(name, d):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    p = nt.nodes["Principled BSDF"]
    set_input(p, "Base Color", (*d.get("color", (0.5, 0.5, 0.5)), 1))
    set_input(p, "Metallic", d.get("metallic", 0.0))
    set_input(p, "Roughness", d.get("roughness", 0.5))
    set_input(p, ["Coat Weight", "Clearcoat"], d.get("coat", 0.0))
    set_input(p, ["Coat Roughness", "Clearcoat Roughness"], d.get("coat_roughness", 0.1))
    set_input(p, ["Specular IOR Level", "Specular"], d.get("specular", 0.5))
    if "texture" in d:
        img = image_texture(nt, d["texture"], d["tex_map"])
        nt.links.new(img.outputs["Color"], p.inputs["Base Color"])
    if d.get("vertex_colors"):
        attr = nt.nodes.new("ShaderNodeAttribute")
        attr.attribute_name = "Col"
        attr.attribute_type = "GEOMETRY"
        nt.links.new(attr.outputs["Color"], p.inputs["Base Color"])
        if d.get("emission", 0):
            nt.links.new(attr.outputs["Color"], p.inputs["Emission Color"])
            set_input(p, "Emission Strength", d["emission"])
    bump = d.get("bump")
    if bump:
        tc = nt.nodes.new("ShaderNodeTexCoord")
        bn = nt.nodes.new("ShaderNodeBump")
        bn.inputs["Strength"].default_value = bump.get("strength", 0.3)
        bn.inputs["Distance"].default_value = bump.get("distance", 0.0005)
        if bump["type"] == "bands":                 # spiral grip wrap / print layer lines
            wv = nt.nodes.new("ShaderNodeTexWave")
            wv.wave_type = "BANDS"
            wv.bands_direction = bump.get("direction", "DIAGONAL")
            wv.inputs["Scale"].default_value = bump.get("scale", 40.0)
            wv.inputs["Distortion"].default_value = 0.0
            mp = nt.nodes.new("ShaderNodeMapping")
            mp.inputs["Rotation"].default_value = [math.radians(a) for a in bump.get("rotation", (0, 0, 0))]
            nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
            nt.links.new(mp.outputs["Vector"], wv.inputs["Vector"])
            nt.links.new(wv.outputs["Fac"], bn.inputs["Height"])
        else:                                        # fine noise
            nz = nt.nodes.new("ShaderNodeTexNoise")
            nz.inputs["Scale"].default_value = bump.get("scale", 400.0)
            nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
            nt.links.new(nz.outputs["Fac"], bn.inputs["Height"])
        nt.links.new(bn.outputs["Normal"], p.inputs["Normal"])
    return m


mats = {k: make_material(k, v) for k, v in cfg["materials"].items()}


# ---------------------------------------------------------------- objects
def import_obj(path):
    if path.endswith(".ply"):                        # PLY keeps per-vertex colours (stress contours)
        bpy.ops.wm.ply_import(filepath=path, forward_axis="Y", up_axis="Z", global_scale=0.001)
    else:
        bpy.ops.wm.obj_import(filepath=path, forward_axis="Y", up_axis="Z", global_scale=0.001,
                              validate_meshes=True)
    obs = list(bpy.context.selected_objects)
    bpy.context.view_layer.objects.active = obs[0]
    if len(obs) > 1:
        bpy.ops.object.join()
    ob = bpy.context.view_layer.objects.active
    if ob.data.users > 1:                            # the PLY importer can leave a second user on the mesh
        ob.data = ob.data.copy()
    # bake the mm -> m import scale into the mesh so 'Object' texture coordinates are in metres
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return ob


def smooth(ob, angle):
    me = ob.data
    me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    if hasattr(me, "use_auto_smooth"):
        me.use_auto_smooth = True
        me.auto_smooth_angle = math.radians(angle)
    me.update()


for grp in cfg["groups"]:
    root = bpy.data.objects.new(grp["name"], None)
    sc.collection.objects.link(root)
    root.location = grp.get("location", (0, 0, 0))
    root.rotation_euler = Euler([math.radians(a) for a in grp.get("rotation", (90, 0, 0))], "XYZ")
    s = grp.get("scale", 1.0)
    root.scale = (s, s, s)
    for part in grp["parts"]:
        ob = import_obj(part["mesh"])
        ob.name = grp["name"] + "_" + part["name"]
        for slot in list(ob.material_slots):
            slot.material = None
        ob.data.materials.clear()
        ob.data.materials.append(mats[part["material"]])
        smooth(ob, part.get("smooth_angle", 32))
        ob.parent = root
        ob.location = [v * 0.001 for v in part.get("offset", (0, 0, 0))]

# ---------------------------------------------------------------- studio backdrop
bd = cfg.get("backdrop")
if bd:
    import bmesh
    me = bpy.data.meshes.new("backdrop")
    bm = bmesh.new()
    W, D, H, R = bd.get("width", 6.0), bd.get("depth", 3.0), bd.get("height", 3.0), bd.get("radius", 0.8)
    wy = bd.get("wall_y", 1.2)
    prof = [(-D, 0.0)]                               # floor, cove (quarter circle), back wall
    n = 24
    for i in range(n + 1):
        a = -math.pi / 2 + (math.pi / 2) * i / n
        prof.append((wy - R + R * math.cos(a), R + R * math.sin(a)))
    prof.append((wy, H))
    rows = []
    for x in (-W / 2, W / 2):
        rows.append([bm.verts.new((x, y, z)) for y, z in prof])
    for i in range(len(prof) - 1):
        bm.faces.new((rows[0][i], rows[1][i], rows[1][i + 1], rows[0][i + 1]))
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new("backdrop", me)
    sc.collection.objects.link(ob)
    me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    ob.data.materials.append(make_material("backdrop", {"color": bd.get("color", (0.8, 0.8, 0.8)),
                                                        "roughness": 0.9, "specular": 0.2}))

# ---------------------------------------------------------------- lights
for i, L in enumerate(cfg["lights"]):
    ld = bpy.data.lights.new(f"L{i}", L.get("type", "AREA"))
    ld.energy = L["energy"]
    ld.color = L.get("color", (1, 1, 1))
    if ld.type == "AREA":
        ld.shape = L.get("shape", "RECTANGLE")
        ld.size = L.get("size", 1.0)
        ld.size_y = L.get("size_y", L.get("size", 1.0))
    lo = bpy.data.objects.new(f"L{i}", ld)
    sc.collection.objects.link(lo)
    lo.location = L["location"]
    d = Vector(L.get("target", (0, 0, 0.2))) - Vector(L["location"])
    lo.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()

# ---------------------------------------------------------------- camera
cd = bpy.data.cameras.new("cam")
cd.lens = cfg["camera"].get("lens", 85)
cd.sensor_width = 36
if cfg["camera"].get("dof"):
    cd.dof.use_dof = True
    cd.dof.aperture_fstop = cfg["camera"]["dof"]["fstop"]
    cd.dof.focus_distance = cfg["camera"]["dof"]["distance"]
co = bpy.data.objects.new("cam", cd)
sc.collection.objects.link(co)
co.location = cfg["camera"]["location"]
d = Vector(cfg["camera"]["target"]) - Vector(cfg["camera"]["location"])
co.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
sc.camera = co

sc.render.filepath = cfg["output"]
bpy.ops.render.render(write_still=True)
print("RENDERED", cfg["output"])
