"""Photoreal 3-D renders (Blender / Cycles) of the sandwich paddles.

Python side: tessellates the build123d parts to OBJ, paints the face-sheet artwork
(carbon weave, accent inlay, name) into textures with Chromium, writes one JSON scene
per shot and runs tools/blender_scene.py in headless Blender.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

from .cad import PartDef, assembly, tessellate
from .geometry import Outline
from .grip import PADDLE_GRIP
from .render import SANS, THEMES, defs_for, inset_polyline, model_path
from .svgkit import f, fmt

ROOT = Path(__file__).resolve().parent.parent
BLENDER_SCRIPT = ROOT / "tools" / "blender_scene.py"


def hex_rgb(h: str) -> tuple[float, float, float]:
    """sRGB hex -> linear RGB (Blender colour inputs are linear)."""
    def lin(c):
        c /= 255.0
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    return tuple(lin(int(h[i:i + 2], 16)) for i in (1, 3, 5))


# ---------------------------------------------------------------- textures
def face_texture_svg(o: Outline, key: str, with_text: bool, px_per_mm: float) -> tuple[str, tuple]:
    sp = o.spec
    th = THEMES[sp.key]
    x0, y0 = -sp.width / 2 - 3, sp.cap_length - 3
    w, h = sp.width + 6, sp.length - sp.cap_length + 6
    t = sp.handle_length
    name_y = o.pts["side_lo"][1] + 14
    text = ""
    if with_text:
        text = f"""
  <g transform="translate(0 {f(name_y)}) scale(1 -1)">
    <text x="0" y="0" font-family="{SANS}" font-size="9.5" font-weight="700" letter-spacing="2.2"
          text-anchor="middle" fill="{th['accent']}">{sp.name}</text></g>
  <g transform="translate(0 {f(name_y - 8.5)}) scale(1 -1)">
    <text x="0" y="0" font-family="{SANS}" font-size="4.2" letter-spacing="1.2" text-anchor="middle"
          fill="#d9dde2" opacity="0.75">{fmt(sp.length)} × {fmt(sp.width)} × {fmt(sp.thickness)} mm</text></g>"""
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{f(w * px_per_mm)}" height="{f(h * px_per_mm)}"
     viewBox="{f(x0)} 0 {f(w)} {f(h)}"><defs>{defs_for(o, key, th)}</defs>
<g transform="translate(0 {f(y0 + h)}) scale(1 -1)">
  <rect x="{f(x0)}" y="{f(y0)}" width="{f(w)}" height="{f(h)}" fill="#141517"/>
  <rect x="{f(x0)}" y="{f(y0)}" width="{f(w)}" height="{f(h)}" fill="url(#carbon-{key})"/>
  <g clip-path="url(#blade-{key})">
    <polyline points="{inset_polyline(o, 11.0, t + 6)}" fill="none" stroke="{th['accent']}" stroke-width="1.4"
              stroke-linejoin="round"/>
    <polyline points="{inset_polyline(o, 14.0, t + 9)}" fill="none" stroke="{th['accent']}" stroke-width="0.5"
              stroke-linejoin="round" opacity="0.6"/>
  </g>{text}
  <path d="{model_path(o)}" fill="none" stroke="#0b0b0c" stroke-width="1.6"/>
</g></svg>"""
    return svg, (x0 / 1000, y0 / 1000, w / 1000, h / 1000)


def write_textures(o: Outline, outdir: Path, px_per_mm: float = 10.0) -> dict:
    from .export import Chromium
    outdir.mkdir(parents=True, exist_ok=True)
    maps = {}
    with Chromium() as c:
        for side, text in (("top", True), ("bottom", False)):
            svg, tex_map = face_texture_svg(o, f"tx{side}", text, px_per_mm)
            p = outdir / f"{o.spec.key}_face_{side}.png"
            w = int(round(tex_map[2] * 1000 * px_per_mm))
            h = int(round(tex_map[3] * 1000 * px_per_mm))
            c.png_px(svg, w, h, p, scale=1.0)
            maps[side] = (str(p), tex_map)
    return maps


# ---------------------------------------------------------------- meshes
def write_obj(shape, path: Path, tol: float = 0.02) -> None:
    import trimesh
    v, t = tessellate(shape, tol, 0.12)
    m = trimesh.Trimesh(v, t, process=True)
    m.export(str(path))


def export_meshes(parts: list[PartDef], outdir: Path, stem: str) -> dict[str, str]:
    outdir.mkdir(parents=True, exist_ok=True)
    out = {}
    for p in parts:
        path = outdir / f"{stem}_{p.name}.obj"
        write_obj(p.shape, path)
        out[p.name] = str(path)
    return out


# ---------------------------------------------------------------- scenes
def materials(key: str, tex: dict) -> dict:
    th = THEMES[key]
    acc = hex_rgb(th["accent"])
    return {
        f"cf_top_{key}": dict(texture=tex["top"][0], tex_map=tex["top"][1], roughness=0.55, coat=0.08,
                              coat_roughness=0.3, specular=0.28),
        f"cf_bottom_{key}": dict(texture=tex["bottom"][0], tex_map=tex["bottom"][1], roughness=0.55, coat=0.08,
                                 coat_roughness=0.3, specular=0.28),
        f"core_{key}": dict(color=acc, roughness=0.55, specular=0.35,
                            bump=dict(type="bands", direction="Z", scale=1100.0, strength=0.08, distance=0.0002)),
        f"accent_{key}": dict(color=acc, roughness=0.32, specular=0.5),
        f"grip_{key}": dict(color=GRIP_COLOUR[key], roughness=0.58, specular=0.32),     # printed PLA grip
        "steel": dict(color=(0.62, 0.63, 0.66), metallic=1.0, roughness=0.22),
        "brass": dict(color=(0.75, 0.55, 0.22), metallic=1.0, roughness=0.28),
    }


PART_MATERIAL = {"face_sheet_top": "cf_top", "face_sheet_bottom": "cf_bottom", "rib_core": "core", "grip": "grip",
                 "screw_M3x12_DIN7984": "steel", "insert_M3_heatset": "brass", "piece_A": "core", "piece_B": "core"}
GRIPS = PADDLE_GRIP                     # any of the ten grips fits both paddles
GRIP_COLOUR = {"elongated": (0.022, 0.022, 0.025), "hybrid": (0.05, 0.052, 0.058)}


def part_list(key: str, meshes: dict[str, str], offsets: dict | None = None, skip=()) -> list[dict]:
    out = []
    for name, mesh in meshes.items():
        if name in skip:
            continue
        mat = PART_MATERIAL[name]
        if mat in ("cf_top", "cf_bottom", "core", "accent", "grip"):
            mat = f"{mat}_{key}"
        out.append(dict(name=name, mesh=mesh, material=mat, offset=(offsets or {}).get(name, (0, 0, 0)),
                        smooth_angle=28))
    return out


STUDIO = dict(backdrop=dict(color=(0.035, 0.037, 0.04), wall_y=1.6, radius=0.9, height=3.0, width=8.0, depth=4.0),
              world_bottom=(0.05, 0.05, 0.055), world_top=(0.42, 0.44, 0.48), world_strength=0.3,
              look="AgX - Medium High Contrast")


def studio_lights(target=(0, 0, 0.25), k: float = 1.0) -> list[dict]:
    return [dict(type="AREA", location=(-1.0, -1.3, 1.5), target=target, size=1.2, size_y=0.8, energy=150 * k),
            dict(type="AREA", location=(1.3, -1.0, 0.7), target=target, size=1.0, energy=45 * k,
                 color=(0.9, 0.95, 1.0)),
            dict(type="AREA", location=(-0.9, 1.0, 1.1), target=target, size=0.5, size_y=1.6, energy=140 * k),
            dict(type="AREA", location=(0.9, 1.0, 1.1), target=target, size=0.5, size_y=1.6, energy=140 * k),
            dict(type="AREA", location=(0.0, -0.4, 2.4), target=target, size=1.6, energy=30 * k)]


def write_scene(path: Path, **cfg) -> Path:
    path.write_text(json.dumps(cfg, indent=1))
    return path


def run_blender(scene: Path, log: Path | None = None) -> None:
    r = subprocess.run(["blender", "-b", "--factory-startup", "--python", str(BLENDER_SCRIPT), "--", str(scene)],
                       capture_output=True, text=True)
    if log:
        log.write_text(r.stdout[-20000:] + r.stderr[-20000:])
    if "RENDERED" not in r.stdout:
        raise RuntimeError(f"Blender failed for {scene}:\n{r.stdout[-3000:]}\n{r.stderr[-3000:]}")


def cutaway(o: Outline):
    """Top face sheet and rib core with a window cut out on the right of the blade.

    The core is sectioned across the flutes, so the wave profile between the two face
    sheets shows on the cut face (as in the construction sketch)."""
    from build123d import Box, Pos

    from .cad import face_sheet, rib_core
    x0, y0, y_sec = 4.0, 232.0, 300.0
    top = face_sheet(o, True) - Pos(x0 + 75, (y0 + 420) / 2, 6) * Box(150, 420 - y0, 6)
    core = rib_core(o) - Pos(x0 + 75, (y0 + y_sec) / 2, 0) * Box(150, y_sec - y0, 10)
    return top, core


SHOTS = ("hero", "cutaway", "exploded_elongated", "exploded_hybrid", "handle", "rib_support")
EXPLODE = {"face_sheet_top": (0, 0, 58), "face_sheet_bottom": (0, 0, -58), "grip": (0, -150, 0),
           "screw_M3x12_DIN7984": (0, -185, 0), "insert_M3_heatset": (0, -8, 0)}
HANDLE_EXPLODE = {"grip": (0, -175, 0), "screw_M3x12_DIN7984": (0, -215, 0), "insert_M3_heatset": (0, -9, 0)}


def shot_scene(shot: str, meshes: dict, cut: dict, pieces: dict | None = None) -> tuple[list[dict], dict, tuple]:
    """Paddle groups (placement in metres / degrees), camera and light target of one shot."""
    def parts(key, offsets=None, cutaway=False):
        p = part_list(key, meshes[key], offsets)
        for q in p if cutaway else []:
            q["mesh"] = cut[key].get(q["name"], q["mesh"])
        return p
    if shot == "hero":
        return ([dict(name="EL", location=(-0.135, 0.0, 0.035), rotation=(90, 0, 34), parts=parts("elongated")),
                 dict(name="HY", location=(0.135, 0.06, 0.035), rotation=(90, 0, -36), parts=parts("hybrid"))],
                dict(location=(0.05, -1.55, 0.47), target=(0.0, 0.02, 0.215), lens=62), (0, 0.03, 0.23))
    if shot == "cutaway":
        return ([dict(name="EL", location=(-0.145, 0.0, 0.07), rotation=(52, 0, 9),
                      parts=parts("elongated", cutaway=True)),
                 dict(name="HY", location=(0.145, 0.02, 0.07), rotation=(52, 0, -9),
                      parts=parts("hybrid", cutaway=True))],
                dict(location=(0.0, -0.98, 0.52), target=(0.0, 0.13, 0.20), lens=50), (0, 0.1, 0.15))
    if shot.startswith("exploded_"):
        key = shot.split("_", 1)[1]
        return ([dict(name="X", location=(0.02, -0.02, 0.135), rotation=(10, 0, -32), parts=parts(key, EXPLODE))],
                dict(location=(0.50, -0.62, 0.52), target=(0.075, 0.13, 0.11), lens=42), (0.05, 0.12, 0.12))
    if shot == "handle":                          # grip pulled off the handle: slot mouth, slits, insert, screw
        return ([dict(name="H", location=(0.0, 0.0, 0.0184), rotation=(0, 0, -60),
                      parts=parts("elongated", HANDLE_EXPLODE))],
                dict(location=(0.135, -0.269, 0.228), target=(-0.032, -0.022, 0.012), lens=45,
                     dof=dict(fstop=8.0, distance=0.38)), (-0.03, -0.02, 0.02))
    if shot == "rib_support":                     # the two print pieces of the core, lying flat, joint opened up
        ps = part_list("elongated", pieces["elongated"], {"piece_B": (0, 22, 0)})
        return ([dict(name="R", location=(-0.05, -0.06, 0.004), rotation=(0, 0, -35), parts=ps)],
                dict(location=(-0.21, -0.31, 0.27), target=(0.075, 0.105, 0.0), lens=48), (0.07, 0.1, 0.0))
    raise ValueError(shot)


def render_all(outlines: list[Outline], out: Path, resolution=(1920, 1200), samples: int = 128,
               shots=SHOTS, log=print) -> list[Path]:
    """Export meshes + textures from the CAD and render every shot to out/paddles_3d_<shot>.png."""
    from .cad import SPLICE_Y, rib_core, split_core
    from .grip import load as load_grip
    work = out / "_work"
    meshes, cut, pieces, mats = {}, {}, {}, {}
    for o in outlines:
        key = o.spec.key
        meshes[key] = export_meshes(assembly(o), work / "mesh", key)
        meshes[key]["grip"] = str(work / "mesh" / f"{key}_grip.ply")
        load_grip(GRIPS[key]).export(meshes[key]["grip"])
        top, core = cutaway(o)
        cut[key] = export_meshes([PartDef("face_sheet_top", top, "cf", (0, 0, 0)),
                                  PartDef("rib_core", core, "core", (0, 0, 0))], work / "mesh", key + "_cut")
        a, b = split_core(rib_core(o, splice=SPLICE_Y), SPLICE_Y, o.half_width_at(SPLICE_Y))
        pieces[key] = export_meshes([PartDef("piece_A", a, "core", (0, 0, 0)), PartDef("piece_B", b, "core", (0, 0, 0))],
                                    work / "mesh", key + "_split")
        mats.update(materials(key, write_textures(o, work / "tex")))
    done = []
    for shot in shots:
        groups, cam, target = shot_scene(shot, meshes, cut, pieces)
        png = out / f"paddles_3d_{shot}.png"
        scene = write_scene(work / f"{shot}.json", resolution=list(resolution), samples=samples, materials=mats,
                            groups=groups, lights=studio_lights(target), camera=cam, output=str(png), **STUDIO)
        run_blender(scene, work / f"{shot}.log")
        done.append(png)
        log(f"rendered {png}")
    return done


def render_stress_cores(plys: dict[str, Path], scale_png: Path, out_png: Path, work: Path,
                        resolution=(1800, 1100), samples: int = 64) -> Path:
    """Both rib cores coloured by von Mises stress (PLY vertex colours), with the colour bar below.

    Rendered with the 'Standard' view transform so the colours match the colour bar."""
    from PIL import Image
    mat = {"stress": dict(vertex_colors=True, roughness=0.55, specular=0.2, emission=0.5)}
    groups = [dict(name=k[:2].upper(), location=loc, rotation=rot,
                   parts=[dict(name="core", mesh=str(p), material="stress", smooth_angle=20)])
              for (k, p), loc, rot in zip(plys.items(), ((-0.145, 0.0, 0.07), (0.145, 0.02, 0.07)),
                                          ((52, 0, 9), (52, 0, -9)))]
    studio = dict(STUDIO, look="None", view_transform="Standard",
                  backdrop=dict(STUDIO["backdrop"], color=(0.22, 0.23, 0.25)), world_strength=0.15)
    raw = work / "core_stress_raw.png"
    scene = write_scene(work / "core_stress.json", resolution=list(resolution), samples=samples, materials=mat,
                        groups=groups, lights=studio_lights((0, 0.1, 0.15), 0.16),
                        camera=dict(location=(0.0, -0.98, 0.52), target=(0.0, 0.13, 0.20), lens=50),
                        output=str(raw), **studio)
    run_blender(scene, work / "core_stress.log")
    img = Image.open(raw).convert("RGB")
    bar = Image.open(scale_png).convert("RGBA")
    bar = bar.resize((int(img.width * 0.42), int(bar.height * img.width * 0.42 / bar.width)), Image.LANCZOS)
    canvas = Image.new("RGB", (img.width, img.height + bar.height + 30), "white")
    canvas.paste(img, (0, 0))
    canvas.paste(bar, ((img.width - bar.width) // 2, img.height + 15), bar)
    canvas.save(out_png)
    return out_png
