"""Blender (bpy) renderer for the door-strap model.

usage: python render.py <mesh_dir> <out_dir> <scene> [samples]
scenes: hero, front, back, exploded, cut, installed
"""
import json
import math
import os
import sys

import bpy  # noqa: I001  (bpy must be imported before bmesh/mathutils)
import bmesh
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Euler, Matrix, Vector

MESH, OUT, SCENE = sys.argv[1], sys.argv[2], sys.argv[3]
SAMPLES = int(sys.argv[4]) if len(sys.argv) > 4 else 128
S = 0.001  # mm -> m
CUT_CX, CUT_CY, CUT_ORTHO = -0.035, 0.020, 0.17   # cut-away camera (m)

MATS = {}


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = SAMPLES
    sc.cycles.use_denoising = True
    try:
        sc.cycles.denoiser = "OPENIMAGEDENOISE"
    except Exception:
        pass
    sc.cycles.max_bounces = 8
    sc.render.film_transparent = True
    sc.view_settings.view_transform = os.environ.get("VIEW", "Standard")
    sc.view_settings.exposure = float(os.environ.get("EXPOSURE", "-1.6"))
    sc.view_settings.gamma = 1.0
    if sc.view_settings.view_transform == "AgX":
        for look in ("AgX - Punchy", "Punchy"):
            try:
                sc.view_settings.look = look
                break
            except Exception:
                pass
    world = bpy.data.worlds.new("w")
    sc.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (0.012, 0.012, 0.014, 1)
    bg.inputs[1].default_value = 1.0
    return sc


def principled(name, color, metal=0.0, rough=0.5, coat=0.0, bump=None,
               sheen=0.0, spec=None):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    p = nt.nodes["Principled BSDF"]
    p.inputs["Base Color"].default_value = (*color, 1)
    p.inputs["Metallic"].default_value = metal
    p.inputs["Roughness"].default_value = rough
    if coat:
        p.inputs["Coat Weight"].default_value = coat
        p.inputs["Coat Roughness"].default_value = 0.25
    if sheen:
        p.inputs["Sheen Weight"].default_value = sheen
    if spec is not None:
        p.inputs["Specular IOR Level"].default_value = spec
    if bump == "fine":
        n = nt.nodes.new("ShaderNodeTexNoise")
        n.inputs["Scale"].default_value = 4000.0
        b = nt.nodes.new("ShaderNodeBump")
        b.inputs["Strength"].default_value = 0.08
        nt.links.new(n.outputs["Fac"], b.inputs["Height"])
        nt.links.new(b.outputs["Normal"], p.inputs["Normal"])
    elif bump == "leather":
        n = nt.nodes.new("ShaderNodeTexVoronoi")
        n.inputs["Scale"].default_value = 900.0
        n2 = nt.nodes.new("ShaderNodeTexNoise")
        n2.inputs["Scale"].default_value = 2500.0
        mix = nt.nodes.new("ShaderNodeMath")
        mix.operation = "ADD"
        nt.links.new(n.outputs["Distance"], mix.inputs[0])
        nt.links.new(n2.outputs["Fac"], mix.inputs[1])
        b = nt.nodes.new("ShaderNodeBump")
        b.inputs["Strength"].default_value = 0.25
        nt.links.new(mix.outputs[0], b.inputs["Height"])
        nt.links.new(b.outputs["Normal"], p.inputs["Normal"])
    elif bump == "weave":
        uv = nt.nodes.new("ShaderNodeTexCoord")
        sep = nt.nodes.new("ShaderNodeSeparateXYZ")
        nt.links.new(uv.outputs["UV"], sep.inputs[0])
        # u: 1 unit = 25 mm along the strap; v: 0..1 across 25 mm
        w1 = nt.nodes.new("ShaderNodeMath")
        w1.operation = "MULTIPLY"
        w1.inputs[1].default_value = 21.0 * 2 * math.pi
        nt.links.new(sep.outputs["X"], w1.inputs[0])
        s1 = nt.nodes.new("ShaderNodeMath")
        s1.operation = "SINE"
        nt.links.new(w1.outputs[0], s1.inputs[0])
        w2 = nt.nodes.new("ShaderNodeMath")
        w2.operation = "MULTIPLY"
        w2.inputs[1].default_value = 30.0 * 2 * math.pi
        nt.links.new(sep.outputs["Y"], w2.inputs[0])
        s2 = nt.nodes.new("ShaderNodeMath")
        s2.operation = "SINE"
        nt.links.new(w2.outputs[0], s2.inputs[0])
        mul = nt.nodes.new("ShaderNodeMath")
        mul.operation = "MULTIPLY"
        nt.links.new(s1.outputs[0], mul.inputs[0])
        nt.links.new(s2.outputs[0], mul.inputs[1])
        ab = nt.nodes.new("ShaderNodeMath")
        ab.operation = "ABSOLUTE"
        nt.links.new(mul.outputs[0], ab.inputs[0])
        b = nt.nodes.new("ShaderNodeBump")
        b.inputs["Strength"].default_value = 0.55
        b.inputs["Distance"].default_value = 0.0004
        nt.links.new(ab.outputs[0], b.inputs["Height"])
        nt.links.new(b.outputs["Normal"], p.inputs["Normal"])
        # subtle colour variation along the weave
        ramp = nt.nodes.new("ShaderNodeMixRGB")
        ramp.blend_type = "MULTIPLY"
        ramp.inputs["Fac"].default_value = 0.35
        ramp.inputs["Color1"].default_value = (*color, 1)
        nt.links.new(ab.outputs[0], ramp.inputs["Color2"])
        nt.links.new(ramp.outputs[0], p.inputs["Base Color"])
    return m


def materials(strap_color=(0.33, 0.0025, 0.006)):
    MATS.update({
        "housing": principled("housing", (0.016, 0.016, 0.018), rough=0.5),
        "badge": principled("badge", (0.012, 0.012, 0.013), rough=0.18,
                            coat=0.3),
        "lever": principled("lever", (0.035, 0.035, 0.038), rough=0.7,
                            bump="fine"),
        "slider": principled("slider", (0.035, 0.035, 0.038), rough=0.7,
                             bump="fine"),
        "steel": principled("steel", (0.86, 0.86, 0.88), metal=1.0,
                            rough=0.2),
        "brass": principled("brass", (0.86, 0.62, 0.3), metal=1.0,
                            rough=0.3),
        "zinc": principled("zinc", (0.25, 0.25, 0.27), metal=1.0,
                           rough=0.45),
        "sheath": principled("sheath", (0.01, 0.01, 0.01), rough=0.55),
        "strap": principled("strap", strap_color, rough=0.9, bump="weave",
                            sheen=0.12, spec=0.15),
        "trim": principled("trim", (0.028, 0.028, 0.03), rough=0.58,
                           bump="leather"),
        "trim_pocket": principled("trim_pocket", (0.02, 0.02, 0.022),
                                  rough=0.5),
    })


MAT_OF = {"housing": "housing", "badge": "badge", "lever": "lever",
          "slider": "slider", "pivot_pin": "steel", "strap_pin": "steel",
          "washers": "steel", "clamp_screw": "steel", "insert": "brass",
          "cable_sheath": "sheath", "cable_inner": "steel", "strap": "strap",
          "trim": "trim", "magnets": "steel", "door_screw": "zinc"}


def finish_mesh(obj, angle=32.0):
    me = obj.data
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-7)
    bm.to_mesh(me)
    bm.free()
    for poly in me.polygons:
        poly.use_smooth = True
    try:
        me.set_sharp_from_angle(angle=math.radians(angle))
    except Exception:
        pass


def load_dir(d, prefix="", skip=()):
    objs = {}
    for f in sorted(os.listdir(d)):
        name, ext = os.path.splitext(f)
        if name in skip:
            continue
        path = os.path.join(d, f)
        before = set(bpy.data.objects)
        if ext == ".stl":
            bpy.ops.wm.stl_import(filepath=path, global_scale=S,
                                  forward_axis="Y", up_axis="Z")
        elif ext == ".obj":
            bpy.ops.wm.obj_import(filepath=path, global_scale=S,
                                  forward_axis="Y", up_axis="Z")
        else:
            continue
        new = [o for o in bpy.data.objects if o not in before]
        o = new[0]
        o.name = prefix + name
        finish_mesh(o, 60.0 if name == "strap" else 32.0)
        o.data.materials.clear()
        o.data.materials.append(MATS[MAT_OF.get(name, "housing")])
        objs[name] = o
    return objs


def group(objs, name):
    e = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(e)
    for o in objs.values():
        o.parent = e
    return e


def area(name, loc, target, energy, size, size_y=None, color=(1, 1, 1)):
    ld = bpy.data.lights.new(name, "AREA")
    ld.energy = energy
    ld.color = color
    ld.shape = "RECTANGLE"
    ld.size = size
    ld.size_y = size_y or size
    o = bpy.data.objects.new(name, ld)
    bpy.context.scene.collection.objects.link(o)
    o.location = Vector(loc)
    d = Vector(target) - o.location
    o.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    return o


def camera(loc, target, lens=85.0, ortho=None, res=(1600, 1600)):
    cd = bpy.data.cameras.new("cam")
    cd.lens = lens
    cd.clip_start = 0.005
    cd.clip_end = 20
    if ortho:
        cd.type = "ORTHO"
        cd.ortho_scale = ortho
    o = bpy.data.objects.new("cam", cd)
    bpy.context.scene.collection.objects.link(o)
    o.location = Vector(loc)
    d = Vector(target) - o.location
    o.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    sc = bpy.context.scene
    sc.camera = o
    sc.render.resolution_x, sc.render.resolution_y = res
    return o


def studio(scale=1.0):
    area("key", (-0.35 * scale, -0.45 * scale, 0.55 * scale), (0, 0, 0),
         55 * scale ** 2, 0.45 * scale, 0.3 * scale, (1.0, 0.97, 0.93))
    area("fill", (0.55 * scale, -0.35 * scale, 0.1 * scale), (0, 0, 0),
         14 * scale ** 2, 0.6 * scale, 0.6 * scale, (0.92, 0.95, 1.0))
    area("rim", (0.15 * scale, 0.5 * scale, 0.45 * scale), (0, 0, 0),
         40 * scale ** 2, 0.3 * scale, 0.6 * scale)
    area("top", (0, 0, 0.7 * scale), (0, 0, 0), 12 * scale ** 2,
         0.8 * scale)


def render(name):
    sc = bpy.context.scene
    sc.render.filepath = os.path.join(OUT, name + ".png")
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGBA"
    bpy.ops.render.render(write_still=True)


def label_points(points):
    """Project named world points to normalised image coords (for labels)."""
    sc = bpy.context.scene
    out = {}
    for n, p in points.items():
        v = world_to_camera_view(sc, sc.camera, Vector(p))
        out[n] = (v.x, 1 - v.y)
    return out


def centre_of(o):
    me = o.data
    vs = [o.matrix_world @ v.co for v in me.vertices]
    c = sum(vs, Vector()) / len(vs)
    return c


# =============================================================================
os.makedirs(OUT, exist_ok=True)
reset()
materials()

if SCENE == "hero":
    a = group(load_dir(os.path.join(MESH, "LH_rest")), "A")
    b = group(load_dir(os.path.join(MESH, "RH_rest")), "B")
    for g in (a, b):
        for c in g.children:
            if c.name.startswith(("cable", "door_screw")):
                c.hide_render = True
    a.rotation_euler = Euler((math.radians(14), 0, math.radians(-34)))
    a.location = (-0.040, 0.0, 0.048)
    b.rotation_euler = Euler((math.radians(-4), 0, math.radians(36)))
    b.location = (0.046, 0.025, -0.052)
    studio(0.9)
    camera((0.015, -0.46, 0.15), (0.003, 0.0, -0.002), lens=58,
           res=(1600, 1600))
    render("hero")

elif SCENE == "front":
    o = group(load_dir(os.path.join(MESH, "LH_rest"),
                       skip=("cable_sheath", "cable_inner", "door_screw")),
              "A")
    studio(0.8)
    camera((0.0, -0.9, 0.0), (0.0, 0.0, 0.0), ortho=0.235, res=(1800, 1100))
    render("front")

elif SCENE == "back":
    o = group(load_dir(os.path.join(MESH, "RH_rest")), "A")
    studio(0.9)
    area("backfill", (-0.2, 0.6, 0.2), (0, 0, 0), 35, 0.5)
    camera((-0.36, 0.42, 0.34), (-0.008, 0.016, 0.0), lens=118,
           res=(1800, 1300))
    render("back")

elif SCENE == "exploded":
    objs = load_dir(os.path.join(MESH, "RH_rest"))
    off = {  # mm, assembly frame (+Y = towards the open back / camera)
        "lever": (8, 62, 0), "strap": (8, 62, 0), "washers": (8, 62, 0),
        "strap_pin": (8, 62, 38),
        "pivot_pin": (0, 0, 52),
        "slider": (-22, 52, 0), "clamp_screw": (-22, 84, 0),
        "insert": (-22, 30, 0),
        "cable_sheath": (-70, 52, 0), "cable_inner": (-70, 52, 0),
    }
    for n in ("badge", "magnets", "door_screw"):
        objs[n].hide_render = True
    for n, o in objs.items():
        o.location = Vector(off.get(n, (0, 0, 0))) * S
    studio(1.0)
    area("backkey", (-0.25, 0.55, 0.40), (0, 0.03, 0), 45, 0.5, 0.35,
         (1.0, 0.97, 0.93))
    camera((-0.30, 0.46, 0.27), (-0.030, 0.040, 0.006), lens=82,
           res=(2000, 1500))
    pts = {n: tuple(centre_of(o)) for n, o in objs.items()
           if not o.hide_render}
    json.dump(label_points(pts), open(os.path.join(OUT, "exploded_labels.json"),
                                      "w"), indent=1)
    render("exploded")

elif SCENE == "cut":
    for pose in ("rest", "full"):
        reset()
        materials()
        o = group(load_dir(os.path.join(MESH, f"cut_{pose}")), "A")
        studio(0.9)
        area("down", (0, 0.02, 0.6), (0, 0.02, 0), 30, 0.5)
        camera((CUT_CX, CUT_CY, 0.9), (CUT_CX, CUT_CY, 0.0),
               ortho=CUT_ORTHO, res=(1600, 1250))
        render(f"cut_{pose}")

elif SCENE == "installed":
    objs = load_dir(os.path.join(MESH, "LH_rest"),
                    skip=("cable_sheath", "cable_inner", "door_screw"))
    trim = load_dir(os.path.join(MESH, "trim"))
    bpy.context.scene.render.film_transparent = False
    w = bpy.context.scene.world.node_tree.nodes["Background"]
    w.inputs[0].default_value = (0.02, 0.02, 0.022, 1)
    studio(1.0)
    area("window", (0.05, -0.5, 0.45), (0.05, 0, 0), 60, 0.6, 0.25,
         (0.95, 0.97, 1.0))
    camera((-0.20, -0.36, 0.13), (0.04, 0.0, -0.006), lens=50,
           res=(1800, 1200))
    render("installed")
