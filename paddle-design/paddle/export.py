"""SVG -> PDF / PNG through headless Chromium (Playwright), and DXF export (ezdxf)."""
from __future__ import annotations

import math
from pathlib import Path

from .geometry import Arc, Outline

_HTML = ('<!doctype html><html><head><meta charset="utf-8"><style>@page{{size:{w}mm {h}mm;margin:0}}'
         'html,body{{margin:0;padding:0;background:#fff}}svg{{display:block}}</style></head>'
         '<body>{svg}</body></html>')


class Chromium:
    """Context manager holding one browser for all conversions."""

    def __enter__(self) -> "Chromium":
        from playwright.sync_api import sync_playwright
        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch()
        return self

    def __exit__(self, *exc) -> None:
        self._browser.close()
        self._pw.stop()

    def pdf(self, svg: str, w_mm: float, h_mm: float, out: Path) -> None:
        page = self._browser.new_page()
        page.set_content(_HTML.format(w=w_mm, h=h_mm, svg=svg), wait_until="load")
        page.pdf(path=str(out), prefer_css_page_size=True, print_background=True)
        page.close()

    def png(self, svg: str, w_mm: float, h_mm: float, out: Path, dpi: float = 200) -> None:
        w_px, h_px = math.ceil(w_mm / 25.4 * 96), math.ceil(h_mm / 25.4 * 96)
        page = self._browser.new_page(viewport={"width": w_px, "height": h_px},
                                      device_scale_factor=dpi / 96)
        page.set_content(_HTML.format(w=w_mm, h=h_mm, svg=svg), wait_until="load")
        page.screenshot(path=str(out), clip={"x": 0, "y": 0, "width": w_mm / 25.4 * 96,
                                              "height": h_mm / 25.4 * 96})
        page.close()

    def png_px(self, svg: str, w_px: int, h_px: int, out: Path, scale: float = 2.0) -> None:
        page = self._browser.new_page(viewport={"width": int(w_px), "height": int(h_px)},
                                      device_scale_factor=scale)
        page.set_content(f'<!doctype html><html><head><meta charset="utf-8"><style>html,body{{margin:0}}'
                         f'svg{{display:block}}</style></head><body>{svg}</body></html>', wait_until="load")
        page.screenshot(path=str(out))
        page.close()


def merge_pdfs(parts: list[Path], out: Path) -> None:
    from pypdf import PdfWriter
    w = PdfWriter()
    for p in parts:
        w.append(str(p))
    with open(out, "wb") as fh:
        w.write(fh)


def write_dxf(o: Outline, out: Path) -> None:
    """1:1 cut profile in mm: one closed LWPOLYLINE (bulge arcs) + centre line + throat line."""
    import ezdxf
    from ezdxf import units

    doc = ezdxf.new("R2000", setup=True)
    doc.units = units.MM
    doc.header["$MEASUREMENT"] = 1
    doc.layers.add("PROFILE", color=7)
    doc.layers.add("CENTRE", color=1, linetype="CENTER")
    doc.layers.add("REFERENCE", color=8, linetype="DASHED")
    doc.layers.add("NOTES", color=3)
    msp = doc.modelspace()
    verts = []
    for s in o.segments:
        bulge = math.tan(s.sweep / 4) if isinstance(s, Arc) else 0.0
        verts.append((s.p0[0], s.p0[1], 0.0, 0.0, bulge))
    msp.add_lwpolyline(verts, format="xyseb", close=True, dxfattribs={"layer": "PROFILE"})
    sp = o.spec
    msp.add_line((0, -10), (0, sp.length + 10), dxfattribs={"layer": "CENTRE", "ltscale": 0.5})
    h = sp.handle_width / 2
    msp.add_line((-h - 20, sp.handle_length), (h + 20, sp.handle_length), dxfattribs={"layer": "REFERENCE"})
    msp.add_text(f"{sp.drawing_no} {sp.name} {sp.length:g}x{sp.width:g}x{sp.thickness:g} mm - throat line y={sp.handle_length:g}",
                 height=4.0, dxfattribs={"layer": "NOTES"}).set_placement((h + 25, sp.handle_length - 2))
    doc.saveas(out)
