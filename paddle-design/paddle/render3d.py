"""Photoreal 3-D renders (Blender / Cycles) of the sandwich paddles.

Python side: tessellates the build123d parts to OBJ, paints the face-sheet artwork
(carbon weave, accent inlay, name) into textures with Chromium, writes one JSON scene
per shot and runs tools/blender_scene.py in headless Blender.
"""
from __future__ import annotations

import json
import math
import subprocess
from pathlib import Path

import numpy as np

from .cad import PartDef, tessellate
from .geometry import CONSTRUCTION as C
from .geometry import Outline
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
        "grip_wrap": dict(color=(0.012, 0.012, 0.013), roughness=0.78,
                          bump=dict(type="bands", direction="DIAGONAL", scale=26.0, rotation=(0, 0, 0), strength=0.6,
                                    distance=0.0006)),
        "grip_sleeve": dict(color=(0.02, 0.02, 0.022), roughness=0.6),
        "steel": dict(color=(0.62, 0.63, 0.66), metallic=1.0, roughness=0.22),
        "brass": dict(color=(0.75, 0.55, 0.22), metallic=1.0, roughness=0.28),
    }


PART_MATERIAL = {"face_sheet_top": "cf_top", "face_sheet_bottom": "cf_bottom", "rib_core": "core",
                 "grip_sleeve": "grip_sleeve", "grip_wrap": "grip_wrap", "throat_collar": "accent",
                 "butt_cap": "accent", "screw_M4x12_ISO7380": "steel", "insert_M4_heatset": "brass"}


def part_list(key: str, meshes: dict[str, str], offsets: dict | None = None, skip=()) -> list[dict]:
    out = []
    for name, mesh in meshes.items():
        if name in skip:
            continue
        mat = PART_MATERIAL[name]
        if mat in ("cf_top", "cf_bottom", "core", "accent"):
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


def angle_between(a, b) -> float:
    return math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))


def bbox_of(meshes: list[str]) -> np.ndarray:
    import trimesh
    b = np.array([trimesh.load(m).bounds for m in meshes])
    return np.array([b[:, 0].min(axis=0), b[:, 1].max(axis=0)])


__all__ = ["write_textures", "export_meshes", "materials", "part_list", "write_scene", "run_blender",
           "cutaway", "STUDIO", "studio_lights", "hex_rgb", "C"]
