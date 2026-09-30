"""Text and parameter content for the specification sheets.  Every number below is derived from the
constants in designs.py / grip_core.py (L = 122.476 mm crest perimeter, relief scale 2.3 mm between the
1.2 mm base wall and the 3.5 mm crest) and cross-checked against the measured peak heights."""

L = 122.476                      # crest perimeter, mm
BASE, CREST = 1.2, 3.5
REL = CREST - BASE               # 2.3 mm of relief between base wall and crest
ZLO, ZHI = 21.5, 116.0
HZ = ZHI - ZLO                   # 94.5 mm textured band


def h(t):                        # height above the bore for relief fraction t
    return BASE + REL * t


CONTENT = {
    "01_vortex_grip": dict(
        id="01", accent="#9C6CDE",
        tagline="Braided over/under helical straps for dynamic multi-point contact.",
        intent="Sixteen straps wound in opposite directions cross in an over/under braid, leaving dark valleys between them. "
               "Every crossing gives the hand an edge to bite on, so the grip works from any hand position on the handle.",
        features=["8 right-hand + 8 left-hand straps on a 36 degree helix",
                  "Over/under weave: the strap on top alternates at every crossing",
                  "Valleys drop to about the 1.2 mm base wall, which keeps the mass low"],
        params=[("Straps", "8 + 8, counter-wound"), ("Helix angle", "36 deg from vertical"),
                ("Strap pitch (around)", f"{L / 8:.2f} mm"), ("Strap width", f"{0.40 * L / 8:.1f} mm around / {0.40 * L / 8 * 0.809:.1f} mm across"),
                ("Strap top height", f"{h(.50):.2f} - {h(.72):.2f} mm above bore"), ("Valley floor", f"{h(.04):.2f} mm above bore"),
                ("Over/under step", f"{.16 * REL:.2f} mm")],
        print_note="Straps rise no faster than 45 degrees, so no supports are needed."),
    "02_cellular_mod": dict(
        id="02", accent="#C81E22",
        tagline="Staggered stacked cells; red cells are recessed pockets for swappable inserts.",
        intent="A wall of staggered, individually pillowed cells. Roughly one cell in five is recessed as an insert pocket "
               "(red in the colourway), sized to take a contrasting insert. No insert parts are included.",
        features=["10 rows x 8 staggered cells with 1.4 mm gaps",
                  "Three cell heights give a subtly stepped surface",
                  "About 22% of cells are recessed 0.7 - 1.2 mm as insert pockets"],
        params=[("Rows x cells", "10 x 8 (staggered)"), ("Row pitch", f"{HZ / 10:.2f} mm"),
                ("Cell size", f"{L / 8:.2f} x {HZ / 10 - 1.4:.2f} mm"), ("Gap between cells", "1.4 mm"),
                ("Cell heights", f"{h(.6):.2f} / {h(.7):.2f} / {h(.8):.2f} mm"), ("Pocket floor", f"{h(.28):.2f} mm above bore"),
                ("Groove floor", f"{BASE:.2f} mm (base wall)")],
        print_note="Cell edges are chamfered; nothing overhangs beyond 45 degrees."),
    "03_tessel_block": dict(
        id="03", accent="#E8742A",
        tagline="Faceted triangular pyramids in staggered rows for enhanced traction.",
        intent="A tessellation of triangular pyramids. Traction comes from many small angled edges rather than one deep texture, and "
               "up-pointing pyramids stand taller than down-pointing ones, giving a two-level, gem-like surface.",
        features=["11 rows x 24 triangles (12 up + 12 down per row)",
                  "Sharp V-grooves between facets",
                  "Up-pyramids 3.44 mm, down-pyramids 3.04 mm above the bore"],
        params=[("Rows", "11"), ("Triangles per row", "24 (12 up + 12 down)"), ("Triangle base", f"{L / 12:.2f} mm"),
                ("Row height", f"{HZ / 11:.2f} mm"), ("Up-pyramid apex", "3.44 mm above bore"),
                ("Down-pyramid apex", f"{h(.8):.2f} mm above bore"), ("Groove floor", "about 1.4 mm above bore")],
        print_note="Facet slopes stay below 45 degrees; rim rows are flat grey bands in the colourway."),
    "04_logic_grip": dict(
        id="04", accent="#2A3C8A",
        tagline="Seamlessly interlocking ergonomic puzzle design.",
        intent="Fifty-six jigsaw pieces tile the grip in alternating colours. Each piece is a shallow pillow separated by fine grooves "
               "and locked to its neighbours by mushroom knobs; knob directions are randomised so no two rows repeat.",
        features=["8 x 7 = 56 pieces in a checkerboard colourway",
                  "Mushroom knobs: 2.9 mm neck, 4.2 mm head, 5.1 mm reach",
                  "0.84 mm grooves cut down to the base wall"],
        params=[("Pieces", "8 x 7 = 56"), ("Piece size", f"{L / 8:.2f} x {HZ / 7:.2f} mm"), ("Knob neck / head", "2.9 mm / dia 4.2 mm"),
                ("Knob reach", "5.1 mm"), ("Groove width", "0.84 mm"), ("Groove floor", f"{BASE:.2f} mm (base wall)"),
                ("Piece top height", f"up to {h(.70):.2f} mm above bore")],
        print_note="Grooves are 0.84 mm wide, about two nozzle widths, and 1.6 mm deep."),
    "05_neuro_tread": dict(
        id="05", accent="#CE1820",
        tagline="Bio-inspired raised neural network over a dimpled adaptive base.",
        intent="A network of 48 neurons joined by curved axon ridges rises to the full 3.5 mm crest, standing proud of a field of small "
               "bumps. The ridges guide the fingers while the bump field provides fine grip.",
        features=["48 somas (8 x 6) joined by curved axons about 1.5 mm wide",
                  "Bump field on a 2.66 mm hex pitch",
                  "Network and somas reach the full 3.5 mm crest"],
        params=[("Neurons (somas)", "48 (8 x 6)"), ("Axon ridge width", "about 1.5 mm"), ("Soma diameter", "about 4.2 mm"),
                ("Network height", f"{CREST:.2f} mm above bore"), ("Bump pitch", f"{L / 46:.2f} mm (hex)"),
                ("Bump field height", "1.4 - 2.4 mm above bore"), ("Ridge / bump colours", "red / black")],
        print_note="Ridges and bumps are gentle slopes; the network is printed in the same material as the base."),
    "06_carbon_matrix": dict(
        id="06", accent="#5C6670",
        tagline="Continuous 2/2 twill weave with selective reinforcement patches.",
        intent="A woven-carbon look built as real geometry: every tow rises over and dives under its neighbours in a 2/2 twill. "
               "Smooth, slightly raised patches suggest selective reinforcement where the palm loads the handle.",
        features=["60 tows around, 2.04 mm pitch, 2/2 twill",
                  "Weave relief about 0.4 mm; every tow is a rounded ridge",
                  "Smooth reinforcement patches stand about 0.5 mm above the weave"],
        params=[("Tows around", "60 (2/2 twill)"), ("Tow pitch", f"{L / 60:.2f} mm"),
                ("Weave heights", "1.7 - 2.2 mm above bore"), ("Patch heights", "2.3 - 2.7 mm above bore"),
                ("Patch coverage", "about 23% of the band"), ("Weave / patch colours", "carbon / grey"), ("Textured band", f"{HZ:.1f} mm tall")],
        print_note="The weave is the finest texture in the set (0.4 mm relief on a 2 mm pitch)."),
    "07_voronoi_core": dict(
        id="07", accent="#8A54E4",
        tagline="Voronoi rib lattice, windows cut through the wall for weight saving and airflow.",
        intent="Irregular Voronoi cells become 2.6 mm ribs with rounded crests, and the cells themselves are open windows through the "
               "wall - so the grip is ventilated and the lightest of the ten. The lattice is relaxed for even cells but keeps a natural irregularity.",
        features=["54 through-windows in the band z 27.5 - 103.5 mm",
                  "2.6 mm ribs standing at the full 3.5 mm crest",
                  "Window roofs trimmed to 60 degrees, longest bridge 3.8 mm"],
        params=[("Windows", "54, through the wall"), ("Rib width", "2.6 mm"), ("Rib height", f"{CREST:.2f} mm above bore"),
                ("Windowed band", "z 27.5 - 103.5 mm (76 mm)"), ("Window corner radius", "1.0 mm"),
                ("Roof limit", "60 deg overhang, 4 mm flat"), ("Open area", "about 64% of the band")],
        print_note="Window roofs are trimmed; the longest bridge is 3.8 mm."),
    "08_topo_flow": dict(
        id="08", accent="#A8744E",
        tagline="Continuous undulating contours mimicking wood grain and terrain.",
        intent="The surface is a contour map of terrain with four wood-like knots. Ridges follow the contours so the lines flow around the "
               "handle like grain in a cut log, giving directional grip that is softer on the hand than sharp knurling.",
        features=["Four knots, contour ridges spaced about 2.5 - 7 mm",
                  "Rounded ridges: crests about 3.1 mm, valleys 1.66 mm above the bore",
                  "Three-tone wood colourway (light / mid / dark)"],
        params=[("Knots", "4"), ("Ridge spacing", "about 2.5 - 7 mm"), ("Ridge crest", "about 3.1 mm above bore"),
                ("Valley floor", f"{h(.20):.2f} mm above bore"), ("Relief", "about 1.4 mm"),
                ("Textured band", f"z {ZLO} - {ZHI} mm"), ("Colourway", "3 wood tones")],
        print_note="Ridge flanks are rounded and below 45 degrees; the grain is geometry, not colour alone."),
    "09_ergo_contour": dict(
        id="09", accent="#4B4F5C",
        tagline="Palm swell, four finger flutes and a thumb rest for hand conformance.",
        intent="A smooth grip shaped for the hand rather than textured: an hourglass swell, a raised palm pad on the back, four finger "
               "flutes and a thumb dish on the front. There are no sharp edges anywhere on the surface.",
        features=["Four finger flutes at z = 44, 58, 72, 86 mm",
                  "Thumb dish at z about 97 mm, palm pad at z about 62 mm",
                  "Hourglass swell 1.73 - 2.33 mm, peaking at about 2.8 mm on the palm pad"],
        params=[("Finger flutes", "4, at z 44 / 58 / 72 / 86"), ("Flute width / depth", "about 9 mm / 0.8 mm"),
                ("Thumb dish", "z 97 mm, depth 0.6 mm"), ("Palm pad", "back face, z 62 mm, +1.0 mm"),
                ("Hourglass swell", f"{h(.23):.2f} - {h(.49):.2f} mm above bore"), ("Peak height", "about 2.8 mm above bore"),
                ("Surface", "smooth, no sharp edges")],
        print_note="The smoothest surface in the set; it prints with the least visible layer texture."),
    "10_hexa_mod": dict(
        id="10", accent="#D63A28",
        tagline="Modular hex pads on four height levels, colour-coded (red = tallest).",
        intent="A honeycomb of individual hex pads, each separated by a 1.7 mm gap and set at one of four heights. The height map is "
               "pseudo-random with a gentle swell along the handle; the tallest pads (red) reach the full 3.5 mm crest.",
        features=["12 columns x 11 rows of pads, 10.2 mm across flats",
                  "Four levels: 2.35 / 2.76 / 3.13 / 3.50 mm above the bore",
                  "Red pads mark the tallest level (about 6% of the band)"],
        params=[("Pad grid", "12 x 11 (pointy-top hex)"), ("Pad across flats", f"{L / 12:.2f} mm"), ("Gap between pads", "1.7 mm"),
                ("Levels", f"{h(.5):.2f} / {h(.68):.2f} / {h(.84):.2f} / {h(1):.2f} mm"), ("Gap floor", f"{BASE:.2f} mm (base wall)"),
                ("Pad edge", "chamfered, about 0.8 mm"), ("Level colours", "3 greys + red")],
        print_note="Pads are chamfered on the lower edge so they never overhang beyond 45 degrees."),
}
