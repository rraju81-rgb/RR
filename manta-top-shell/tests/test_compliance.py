"""Regression tests: both class packages must stay inside their rule envelopes.

Run from the manta-top-shell folder:  python -m pytest -q
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from manta.build import build_variant  # noqa: E402
from manta.checks import mesh_integrity, run_checks, tyre_penetration  # noqa: E402
from manta.design import VARIANTS  # noqa: E402
from manta.solid import thicken  # noqa: E402


@pytest.fixture(scope="module", params=sorted(VARIANTS))
def built(request):
    b = build_variant(VARIANTS[request.param])
    return b, run_checks(b)


def test_all_regulation_checks_pass(built):
    _, report = built
    failed = [f"{c['name']}: {c['value']}" for c in report["checks"] if not c["pass"]]
    assert not failed, "\n".join(failed)


def test_envelope_numbers(built):
    b, report = built
    r = b.variant.rules
    m = report["measured"]
    assert m["length"] <= r.max_length
    assert m["width"] <= r.max_width
    assert m["height"] <= r.max_height
    # the design should use the box, not float inside it
    assert m["length"] >= r.max_length - 10
    assert m["width"] >= r.max_width - 10


def test_shell_is_one_symmetric_manifold_surface(built):
    b, _ = built
    skin = b.parts["top_shell_skin"]
    mi = mesh_integrity(skin)
    assert mi["finite"] and mi["non_manifold_edges"] == 0 and mi["degenerate_faces"] == 0
    # outward orientation: crown normals point up on average, area-weighted
    fn = skin.face_normals(normalize=False)
    assert fn[:, 2].sum() > 0


@pytest.mark.parametrize("thickness", [3.0, 12.5])
def test_thickened_solids_are_watertight(built, thickness):
    b, _ = built
    solid = thicken(b.parts["top_shell_skin"], thickness)
    mi = mesh_integrity(solid)
    assert mi["boundary_edges"] == 0 and mi["non_manifold_edges"] == 0


def test_tyre_model_sign_convention():
    # wheel centre: 145 mm from the nearest boundary (the 290 mm wide sidewalls);
    # 1 m above the centre: 1000 - 355 = 645 mm above the tread
    inside = tyre_penetration(np.array([[0.0, 825.0, 300.0]]), 0.0, 825.0, 300.0, 355.0, 290.0)
    outside = tyre_penetration(np.array([[0.0, 825.0, 1300.0]]), 0.0, 825.0, 300.0, 355.0, 290.0)
    assert inside[0] == pytest.approx(-145.0, abs=0.5)
    assert outside[0] == pytest.approx(645.0, abs=0.5)
    # bump raises the tyre: the same point gets 40 mm closer
    bumped = tyre_penetration(np.array([[0.0, 825.0, 1300.0]]), 0.0, 825.0, 300.0, 355.0, 290.0,
                              bump=40.0)
    assert bumped[0] == pytest.approx(605.0, abs=0.5)


def test_lmh_uses_extra_height_and_lmdh_extra_length():
    lmdh = build_variant(VARIANTS["lmdh"]).shell.vertices
    lmh = build_variant(VARIANTS["lmh"]).shell.vertices
    assert lmh[:, 2].max() > lmdh[:, 2].max() + 50  # taller canopy for the 1150 mm box
    assert np.ptp(lmdh[:, 0]) > np.ptp(lmh[:, 0]) + 50  # longer for the 5100 mm box
