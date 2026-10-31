"""Regulation envelopes for the two prototype classes the shell is packaged for.

All lengths are in millimetres. Heights are measured from the *reference plane*
(the flat underside of the car), which is also z = 0 of the design coordinate
system used throughout this package.

IMPORTANT: the official FIA/ACO rule books (LMH Technical Regulations, Art. 3
"Bodywork and dimensions"; LMDh Technical Regulations, Art. 3) could not be
fetched from the build environment. The figures below were cross-checked
against published car specifications and press material (see ``sources``)
and must be re-verified against the current edition of each rule book
before the design is used for anything beyond concept work.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Tyre:
    """Michelin endurance-prototype tyre, ISO-style ``width/diameter-rim`` code."""

    code: str
    width: float  # section width [mm]
    diameter: float  # overall diameter [mm]

    @property
    def radius(self) -> float:
        return self.diameter / 2.0


TYRE_29_71_18 = Tyre("29/71-18", 290.0, 710.0)
TYRE_31_71_18 = Tyre("31/71-18", 310.0, 710.0)
TYRE_34_71_18 = Tyre("34/71-18", 340.0, 710.0)


@dataclass(frozen=True)
class ClassRules:
    key: str
    name: str
    max_length: float
    max_width: float
    max_height: float  # above reference plane
    wheelbase_max: float
    wheelbase_note: str
    front_tyre: Tyre
    rear_tyre: Tyre
    # Mandatory openings in the bodywork above each front wheel. The minimum
    # area is an ASSUMPTION carried over from the earlier ACO prototype rule
    # (160 cm^2 per side); confirm against the current Art. 3 text.
    min_front_louvre_area_cm2: float = 160.0
    sources: tuple[str, ...] = field(default_factory=tuple)
    notes: tuple[str, ...] = field(default_factory=tuple)


LMDH = ClassRules(
    key="lmdh",
    name="LMDh (Le Mans Daytona h)",
    max_length=5100.0,
    max_width=2000.0,
    max_height=1060.0,
    wheelbase_max=3148.0,
    wheelbase_note="3148 mm common wheelbase (spec LMP2-derived chassis)",
    front_tyre=TYRE_29_71_18,
    rear_tyre=TYRE_34_71_18,
    sources=(
        "Porsche 963 published data: 5100 x 2000 x 1060 mm, wheelbase 3148 mm, 1030 kg",
        "Motor1 / BMWBlog LMDh coverage: <= 5100 mm long, <= 2000 mm wide, <= 1060 mm high",
        "FIA LMDh Technical Regulations 2024.10.22, Art. 3 (overall dimensions, engine cover fin)",
        "Michelin: LMDh runs 29/71-18 front, 34/71-18 rear",
    ),
    notes=(
        "Survival cell, roll structure, windscreen and door apertures come from the "
        "licensed chassis supplier (Dallara, Ligier, Multimatic, Oreca). The canopy "
        "surface in this design is styling intent and must be fitted to the chosen "
        "supplier's greenhouse hard points.",
        "Engine cover fin is mandatory (FIA LMDh TR Art. 3).",
    ),
)

LMH = ClassRules(
    key="lmh",
    name="LMH (Le Mans Hypercar)",
    max_length=5000.0,
    max_width=2000.0,
    max_height=1150.0,
    wheelbase_max=3150.0,
    wheelbase_note="free up to 3150 mm; this package uses 3100 mm",
    front_tyre=TYRE_29_71_18,
    rear_tyre=TYRE_34_71_18,
    sources=(
        "FIA LMH Technical Regulations (2021-2024 editions), Art. 3.1 overall dimensions",
        "Le Mans Hypercar class summaries: <= 5000 mm long, <= 2000 mm wide",
        "Toyota GR010 Hybrid published data: 4900 x 2000 x 1150 mm",
        "Endurance-Info / Michelin: LMH homologated after 2022-12-31 use 29/71-18 F + 34/71-18 R; "
        "earlier 4WD LMH may run 31/71-18 all round",
    ),
    notes=(
        "LMH survival cell is bespoke, so the canopy shown here can be engineered as drawn "
        "(subject to the windscreen / visibility / door-aperture articles).",
        "Legacy 4WD option: 31/71-18 on both axles (see TYRE_31_71_18).",
    ),
)

CLASSES = {"lmdh": LMDH, "lmh": LMH}
