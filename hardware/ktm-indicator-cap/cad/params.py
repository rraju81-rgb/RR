"""
Parameters for the KTM indicator slip-on cap.

Everything dimensional lives here. Run `python3 build.py` after editing.

Units: millimetres, degrees.

Lamp coordinate frame (used everywhere):
    x  along the lamp, 0 at the root face of the lamp head, +x towards the tip
    y  0 at the line where the flat top of the black housing meets the lens,
       +y towards the back of the lamp (away from the lens)
    z  0 at the underside of the head, +z up

IMPORTANT
---------
The `Lamp` and `Mount` values below were scaled off product photos, NOT measured
on a motorcycle. They are good enough to prove the design and to make a
cardboard / printed fit-check, and they are NOT good enough to cut steel.
Measure the lamp (see README, "Measure first") and overwrite them.
"""
from dataclasses import dataclass, field, asdict
import math


@dataclass
class Lamp:
    """OEM LED indicator head. Photo-derived estimates -> VERIFY (M1..M8 in README)."""
    L: float = 74.0        # M1  head length, root face to tip
    H: float = 20.0        # M2  head height (top face to underside)
    D_root: float = 26.0   # M3  depth of black housing at the root (lens joint -> back face)
    D_tip: float = 14.0    # M4  depth of black housing at the tip
    lens_run: float = 4.5  # M5  lens top chamfer, horizontal run in front of the joint line
    lens_drop: float = 3.0 # M5  lens top chamfer, vertical drop
    lens_nose: float = 1.5 # extra lens depth in front of the chamfer (schematic only)
    # neck (rubber stalk) between head and the socket on the bike - schematic only
    neck_len: float = 8.0  # M6  root face of head -> face of the socket block
    neck_y0: float = 6.0
    neck_dy: float = 14.0
    neck_dz: float = 13.0

    @property
    def taper(self) -> float:
        """Taper angle of the back face relative to the lamp axis, radians."""
        return math.atan2(self.D_root - self.D_tip, self.L)


@dataclass
class Mount:
    """Fixing point on the bike beside the lamp socket. Photo-derived -> VERIFY (M7, M8)."""
    G_ear: float = 8.0          # M7  root face of head -> seat face of the screw boss (along x)
    hole_from_back: float = 10.0  # M8  screw axis behind the OUTER face of the cap back wall
    screw_d: float = 5.0        # nominal screw diameter (M5 / 5 mm thread-forming screw)


@dataclass
class Cap:
    """The sheet-metal cap itself. These are design choices, change freely."""
    material: str = "Stainless steel 304, 1.5 mm, 2B"
    density: float = 8.0e-3     # g/mm^3
    t: float = 1.5              # sheet thickness
    r: float = 1.5              # inside bend radius
    k: float = 0.42             # K-factor for the bend allowance (air bending, r/t = 1)

    # liner gaps = compressed thickness of the EPDM foam liner in each direction
    gap_z: float = 0.8          # top / bottom (1 mm foam, ~20 % squeeze)
    gap_back: float = 1.5       # back wall     (2 mm foam, ~25 % squeeze)
    gap_tip: float = 2.0        # tip wall      (3 mm foam, ~33 % squeeze)
    gap_tab: float = 0.8        # keeper tab to lens chamfer (1 mm foam)

    # plates
    plate_root_x: float = -3.0  # plates run 3 mm inboard of the head root face
    plate_bend_start: float = 2.0  # gap between tip bend and plate bends (corner relief)
    edge_setback: float = 2.0   # plate front edge sits this far behind the tab bend line
    r_corner: float = 3.0       # exposed outer corner radius (>= 2.5 for external projections)

    # keeper tabs (2 per plate)
    tab_angle: float = 35.0     # bend angle; ideally equal to the lens chamfer angle
    tab_w: float = 12.0
    tab_flat: float = 4.5       # flat length beyond the bend
    tab_x: tuple = (16.0, 60.0) # centres along the lamp

    # tip wall
    tip_h_relief: float = 0.8   # tip wall is this much shorter than the back wall, each side
    tip_front_y: float = 0.0    # tip wall stops at the lens joint line (lens stays uncovered)

    # ear (fixing lug)
    ear_angle: float | None = None  # None -> square to the lamp axis (90 deg - taper)
    ear_slot_len: float = 9.5   # slot long axis, gives +/-2 mm adjustment
    ear_slot_w: float = 5.5

    # lightening / drain slots in the plates ("three slashes")
    slot_x: tuple = (28.0, 38.0, 48.0)
    slot_w: float = 3.0
    slot_angle: float = 60.0    # from the lamp axis
    slot_margin: float = 5.0    # keep-out from bend line and from front edge

    relief: float = 0.8         # bend relief notch depth

    @property
    def ba90(self) -> float:
        return math.pi / 2 * (self.r + self.k * self.t)

    def ba(self, angle_deg: float) -> float:
        """Bend allowance (neutral-axis arc length) for a bend of `angle_deg`."""
        return math.radians(angle_deg) * (self.r + self.k * self.t)


@dataclass
class Design:
    lamp: Lamp = field(default_factory=Lamp)
    mount: Mount = field(default_factory=Mount)
    cap: Cap = field(default_factory=Cap)

    def as_dict(self):
        return asdict(self)


# Lighter alternative: 2.0 mm aluminium 5052-H32, anodised. Same inner cavity.
def aluminium_variant() -> Design:
    d = Design()
    d.cap.material = "Aluminium 5052-H32, 2.0 mm"
    d.cap.density = 2.68e-3
    d.cap.t = 2.0
    d.cap.r = 2.0
    d.cap.k = 0.44
    d.cap.tab_flat = 5.5
    return d
