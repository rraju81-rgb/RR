#!/usr/bin/env python3
"""Photoreal 3-D renders of both paddles (needs Blender with Cycles on PATH).

    python tools/render_3d.py [--samples 128] [--res 1920 1200] [--shots hero cutaway ...]
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from paddle.geometry import DESIGNS, build  # noqa: E402
from paddle.render3d import SHOTS, render_all  # noqa: E402

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("--samples", type=int, default=128)
ap.add_argument("--res", type=int, nargs=2, default=(1920, 1200))
ap.add_argument("--shots", nargs="*", default=list(SHOTS))
a = ap.parse_args()
render_all([build(sp) for sp in DESIGNS], ROOT / "output" / "render", tuple(a.res), a.samples, a.shots)
