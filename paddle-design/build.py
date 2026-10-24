#!/usr/bin/env python3
"""Generate the paddle drawings, templates, DXF profiles and the 2-D render into ./output.

    python build.py              # SVG + DXF + PDF + PNG (PDF/PNG need Playwright Chromium)
    python build.py --no-raster  # SVG + DXF only

The 3-D model, renders and stress analysis have their own scripts in tools/ (see README).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from paddle.export import Chromium, merge_pdfs, write_dxf
from paddle.geometry import DESIGNS, build
from paddle.render import board
from paddle.sheets import ga_sheet, template_sheet
from paddle.sheets_construction import GRIP_NO, core_sheet, grip_sheet
from paddle.sheets_mould import mould_sheet

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output"
MASS = ROOT / "analysis" / "mass_properties.json"     # written by tools/export_cad.py
MOULD = OUT / "mould" / "mould_report.json"            # written by tools/export_mould.py


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--no-raster", action="store_true", help="write SVG and DXF only (skip PDF/PNG)")
    ap.add_argument("--dpi", type=float, default=200, help="PNG resolution (default 200)")
    args = ap.parse_args()

    mass = json.loads(MASS.read_text()) if MASS.exists() else {}
    mould = json.loads(MOULD.read_text())["designs"] if MOULD.exists() else {}
    jobs = []                      # (svg path, doc)
    outlines = []
    for sp in DESIGNS:
        o = build(sp)
        outlines.append(o)
        d = OUT / sp.key
        d.mkdir(parents=True, exist_ok=True)
        for stem, doc in ((f"{sp.drawing_no}_sheet1_general_arrangement", ga_sheet(o, mass.get(sp.key))),
                          (f"{sp.drawing_no}_sheet2_template_1to1", template_sheet(o)),
                          (f"{sp.drawing_no}_sheet3_rib_core", core_sheet(o, mass.get(sp.key))),
                          (f"{sp.drawing_no}_sheet4_compression_mould", mould_sheet(o, mould.get(sp.key)))):
            p = d / f"{stem}.svg"
            p.write_text(doc.svg(), encoding="utf-8")
            jobs.append((p, doc))
        write_dxf(o, d / f"{sp.drawing_no}_profile.dxf")
        print(f"{sp.name:9s} area {o.area / 100:.1f} cm2, perimeter {o.perimeter:.1f} mm -> {d}")

    d = OUT / "grip"
    d.mkdir(parents=True, exist_ok=True)
    doc = grip_sheet(DESIGNS[0], mass or None)
    p = d / f"{GRIP_NO}_printed_grip_interface.svg"
    p.write_text(doc.svg(), encoding="utf-8")
    jobs.append((p, doc))

    svg, bw, bh = board(outlines)
    render_svg = OUT / "render" / "paddles_2d_render.svg"
    render_svg.parent.mkdir(parents=True, exist_ok=True)
    render_svg.write_text(svg, encoding="utf-8")

    if args.no_raster:
        return
    with Chromium() as c:
        for p, doc in jobs:
            c.pdf(doc.svg(), doc.w, doc.h, p.with_suffix(".pdf"))
            c.png(doc.svg(), doc.w, doc.h, p.with_suffix(".png"), dpi=args.dpi)
        c.png_px(svg, bw, bh, render_svg.with_suffix(".png"), scale=2.0)
    merge_pdfs([p.with_suffix(".pdf") for p, _ in jobs], OUT / "paddle_drawing_set.pdf")
    print(f"drawing set -> {OUT / 'paddle_drawing_set.pdf'}")


if __name__ == "__main__":
    main()
