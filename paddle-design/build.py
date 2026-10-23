#!/usr/bin/env python3
"""Generate the paddle drawings, templates, DXF profiles and renders into ./output.

    python build.py              # SVG + DXF + PDF + PNG (PDF/PNG need Playwright Chromium)
    python build.py --no-raster  # SVG + DXF only
"""
from __future__ import annotations

import argparse
from pathlib import Path

from paddle.export import Chromium, merge_pdfs, write_dxf
from paddle.geometry import DESIGNS, build
from paddle.render import board
from paddle.sheets import ga_sheet, template_sheet

OUT = Path(__file__).resolve().parent / "output"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--no-raster", action="store_true", help="write SVG and DXF only (skip PDF/PNG)")
    ap.add_argument("--dpi", type=float, default=200, help="PNG resolution (default 200)")
    args = ap.parse_args()

    jobs = []                      # (svg path, doc)
    outlines = []
    for sp in DESIGNS:
        o = build(sp)
        outlines.append(o)
        d = OUT / sp.key
        d.mkdir(parents=True, exist_ok=True)
        for stem, doc in ((f"{sp.drawing_no}_sheet1_general_arrangement", ga_sheet(o)),
                          (f"{sp.drawing_no}_sheet2_template_1to1", template_sheet(o))):
            p = d / f"{stem}.svg"
            p.write_text(doc.svg(), encoding="utf-8")
            jobs.append((p, doc))
        write_dxf(o, d / f"{sp.drawing_no}_profile.dxf")
        print(f"{sp.name:9s} area {o.area / 100:.1f} cm2, perimeter {o.perimeter:.1f} mm -> {d}")

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
