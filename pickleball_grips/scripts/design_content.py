"""Copy for the ten per-design brochures.  Every number below is taken from the measured spec data (spec_content.py /
fitment_report.json / print_report.json) - single-colour wording only: no colour-coded parts."""

# accent colour per design: (on the dark page, on the light page) - derived from the PLA colour the design is shown in
ACCENT = {
    "01_vortex_grip": ("#A98BF5", "#6B3FCB"), "02_cellular_mod": ("#E8EAEE", "#5E6978"), "03_tessel_block": ("#F5A04A", "#D97012"),
    "04_logic_grip": ("#6FA3F5", "#2A5FC0"), "05_neuro_tread": ("#F2636A", "#C01F27"), "06_carbon_matrix": ("#C3CBD6", "#2A2F38"),
    "07_voronoi_core": ("#86DC5E", "#3E8E22"), "08_topo_flow": ("#F3DC55", "#9C7F00"), "09_ergo_contour": ("#A3AEBD", "#4F5866"),
    "10_hexa_mod": ("#3FD0C2", "#14857C"),
}

HANDLE_NOTE = ("A slim sleeve that slides over your paddle handle: closed at the butt, open at the throat, 132.8 mm long and cut to "
               "the exact 32.06 × 26.04 mm bore of the reference handle. The fit is identical on all ten designs, so you can swap "
               "textures freely. A smooth collar at each end keeps the edges kind to your hand.")

CONTENT = {
    "01_vortex_grip": dict(
        tagline="Braided over-under straps for dynamic multi-point contact.",
        story="Sixteen straps wound in opposite directions cross in an over-under braid, leaving deep valleys between them. "
              "Every crossing gives the hand an edge to bite on, so the grip works wherever you hold the handle.",
        features=["8 right-hand and 8 left-hand straps on a 36° helix", "Over-under weave: the top strap alternates at every crossing",
                  "Valleys drop to the thin base wall, which keeps it light"],
        stats=[("16", "STRAPS"), ("36°", "HELIX ANGLE")],
        inspiration="Braided climbing rope and woven leather. The straps twist around the handle the way a rope wraps a post, "
                    "so your fingers always find an edge that points against a slipping hand.",
        tip="Straps rise no faster than 45°, so no supports are needed.", motif="rope"),
    "02_cellular_mod": dict(
        tagline="Staggered stacked cells, with pockets for optional inserts.",
        story="A wall of staggered, individually pillowed cells with chamfered edges. About one cell in five is recessed into "
              "a pocket, sized to take an optional insert. In a single colour the pockets read as shadow.",
        features=["10 rows × 8 staggered cells with 1.4 mm gaps", "Three cell heights give a subtly stepped surface",
                  "About 22 % of the cells are recessed 0.7–1.2 mm"],
        stats=[("80", "CELLS"), ("22 %", "POCKETS")],
        inspiration="Brickwork and stacked stone. The staggered joints lock every cell to its neighbours, and the recessed "
                    "pockets add a rhythm, like windows in a wall.",
        tip="Cell edges are chamfered and nothing overhangs beyond 45°. Inserts are optional and not included.", motif="brick"),
    "03_tessel_block": dict(
        tagline="Faceted triangular pyramids in staggered rows for enhanced traction.",
        story="A tessellation of triangular pyramids. Traction comes from many small angled edges rather than one deep texture, "
              "and up-pointing pyramids stand taller than down-pointing ones, giving a two-level, gem-like surface.",
        features=["11 rows of 24 triangles with sharp V-grooves", "Up-pyramids reach 3.44 mm, down-pyramids 3.04 mm",
                  "Every facet slope stays under 45°"],
        stats=[("264", "FACETS"), ("3.44 mm", "TALLEST APEX")],
        inspiration="Cut gemstones and folded paper. A faceted pattern catches the light at dozens of angles, and under the "
                    "fingertips each small pyramid is a tiny step your skin can grip.",
        tip="Facet slopes stay below 45°, so the pyramids print cleanly without supports.", motif="gem"),
    "04_logic_grip": dict(
        tagline="Seamlessly interlocking ergonomic puzzle design.",
        story="Fifty-six jigsaw pieces tile the grip. Each piece is a shallow pillow separated by fine grooves and locked to "
              "its neighbours by mushroom knobs; the knob directions are randomised so no two rows repeat.",
        features=["8 × 7 = 56 interlocking pieces", "Mushroom knobs with a 2.9 mm neck and 4.2 mm head",
                  "0.84 mm grooves, about two nozzle widths wide"],
        stats=[("56", "PIECES"), ("0.84 mm", "GROOVES")],
        inspiration="Jigsaw puzzles and the satisfying click of the last piece. The surface looks assembled rather than "
                    "moulded, and the grooves give your fingers lanes to settle into.",
        tip="Grooves are 0.84 mm wide and about 1.6 mm deep.", motif="puzzle"),
    "05_neuro_tread": dict(
        tagline="A raised neural network over a dimpled adaptive base.",
        story="A network of 48 neurons joined by curved axon ridges rises to the full 3.5 mm crest, standing proud of a field "
              "of small bumps. The ridges guide the fingers while the bump field adds fine grip.",
        features=["48 nodes (8 × 6) joined by curved 1.5 mm ridges", "Bump field on a 2.66 mm hex pitch, 1.4–2.4 mm high",
                  "Network and nodes reach the full 3.5 mm crest"],
        stats=[("48", "NODES"), ("3.50 mm", "NETWORK HEIGHT")],
        inspiration="Neural networks and leaf veins: branching lines that meet at nodes. The ridges read like a map under "
                    "the palm, while the fine bumps between them work like grip tape.",
        tip="Ridges and bumps are gentle slopes, printed in one material.", motif="neuro"),
    "06_carbon_matrix": dict(
        tagline="A continuous 2/2 twill weave with selective reinforcement patches.",
        story="A woven-carbon look built as real geometry: every tow rises over and dives under its neighbours in a 2/2 twill. "
              "Smooth, slightly raised patches suggest reinforcement where the palm loads the handle.",
        features=["60 tows around at a 2.04 mm pitch, 2/2 twill", "Weave relief about 0.4 mm, the finest texture in the set",
                  "Smooth patches stand about 0.5 mm above the weave"],
        stats=[("60", "TOWS"), ("2.04 mm", "TOW PITCH")],
        inspiration="Carbon-fibre cloth, the material many paddle faces are made from. The twill is printed rather than "
                    "woven, so it feels like a fine fabric under the hand.",
        tip="The weave is the finest texture in the set: 0.4 mm of relief on a 2 mm pitch.", motif="twill"),
    "07_voronoi_core": dict(
        tagline="A Voronoi rib lattice with windows cut through the wall.",
        story="Irregular Voronoi cells become 2.6 mm ribs with rounded crests, and the cells themselves are open windows "
              "through the wall. The grip is ventilated, and the lightest of the ten.",
        features=["54 through-windows in a 76 mm band", "2.6 mm ribs standing at the full 3.5 mm crest",
                  "Window roofs trimmed to 60°, longest bridge 3.8 mm"],
        stats=[("54", "WINDOWS"), ("64 %", "OPEN AREA")],
        inspiration="Dragonfly wings, leaf veins and cracked earth: the same branching cells appear wherever nature needs "
                    "strength without weight. Here they let air reach your palm and make this about six grams lighter than any other design.",
        tip="Window roofs are trimmed so the longest unsupported bridge is 3.8 mm.", motif="wing"),
    "08_topo_flow": dict(
        tagline="Continuous undulating contours, like wood grain and terrain.",
        story="The surface is a contour map with four wood-like knots. Ridges follow the contours so the lines flow around "
              "the handle like grain in a cut log, giving directional grip that is softer on the hand than sharp knurling.",
        features=["Four knots, contour ridges 2.5–7 mm apart", "Rounded crests about 3.1 mm, valleys 1.66 mm",
                  "Ridge flanks stay under 45°"],
        stats=[("4", "KNOTS"), ("3.13 mm", "PEAK RELIEF")],
        inspiration="Topographic maps and the growth rings of a sawn log. Nature draws the same flowing lines wherever a "
                    "surface is shaped gradually, and here they lead your fingers around the handle.",
        tip="Ridge flanks are rounded and below 45°; the grain is geometry, not colour.", motif="contour"),
    "09_ergo_contour": dict(
        tagline="A palm swell, four finger flutes and a thumb rest shaped for the hand.",
        story="A smooth grip shaped for the hand rather than textured: an hourglass swell, a raised palm pad on the back, "
              "four finger flutes and a thumb dish on the front. There is no sharp edge anywhere on the surface.",
        features=["Four finger flutes at 44, 58, 72 and 86 mm", "Thumb dish near 97 mm, palm pad near 62 mm",
                  "Hourglass swell 1.73–2.33 mm, peaking near 2.8 mm"],
        stats=[("4", "FINGER FLUTES"), ("2.77 mm", "PEAK RELIEF")],
        inspiration="A pebble worn smooth by a river, and the cast of a relaxed hand. Instead of texture it offers shape: "
                    "rests where the fingers fall, and a swell where the palm sits.",
        tip="The smoothest surface in the set, so it shows the least layer texture.", motif="pebble"),
    "10_hexa_mod": dict(
        tagline="Modular hex pads on four height levels.",
        story="A honeycomb of individual hex pads, each separated by a 1.7 mm gap and set at one of four heights. The height "
              "map is pseudo-random with a gentle swell along the handle; the tallest pads reach the full 3.5 mm crest.",
        features=["12 columns × 11 rows of pads, 10.2 mm across flats", "Four levels: 2.35 / 2.76 / 3.13 / 3.50 mm",
                  "Gaps drop to the 1.2 mm base wall"],
        stats=[("132", "HEX PADS"), ("4", "HEIGHT LEVELS")],
        inspiration="A beehive, and the hexagonal tiles of an old bathroom floor. Six-sided pads pack with no wasted space, "
                    "and the varied heights mean your fingers find a slightly different edge each time you re-grip.",
        tip="Pads are chamfered on the lower edge so they never overhang beyond 45°.", motif="hex"),
}
