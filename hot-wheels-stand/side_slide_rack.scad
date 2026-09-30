// Side-Slide Shingle Rack - parametric wall display for carded die-cast cars.
// Units: mm. x = left->right, y = up, z = out from the wall.
//
// Every card stands in its own depth plane (shingled, 'step' apart) and is held
// only by a gutter in its own ledge. Nothing is in front of the cards, and each
// card slides out to the right without touching any other card.
//
// NOTE: not test-rendered in this environment (no OpenSCAD available) - open it
// in OpenSCAD, press F6, and check the echoed numbers before printing.
// MEASURE YOUR CARDS with calipers and edit the first block.

// ---- card (measure these) ----
card_w      = 105;   // card width
card_h      = 165;   // card height
card_t      = 1.2;   // card thickness (cardstock only, excluding blister)
blister_h   = 42;    // height of the car blister measured from card bottom edge
                     // (must fit in the visible window, see assert below)

// ---- layout ----
N           = 8;     // number of cards
pitch       = 55;    // vertical spacing = visible strip per card
step        = 4.6;   // depth spacing between neighbouring cards

// ---- structure ----
back_t      = 3;     // wall plate thickness
spine_w     = 14;    // left spine / end stop width
ledge_h     = 10;    // ledge height (y)
gutter_d    = 6;     // how deep the card bottom sits in the gutter
slop        = 0.3;   // clearance each side of the card in the gutter
rear_wall   = 2.4;   // ledge wall behind the gutter
front_wall  = 2.4;   // ledge wall in front of the gutter
thumb_out   = 8;     // card overhangs the ledge's right end by this much

gw          = card_t + 2*slop;              // gutter width
ledge_w     = spine_w + card_w - thumb_out; // ledge length (x)
H           = (N-1)*pitch + ledge_h - gutter_d + card_h + 5;  // plate height

// z of the rear face of card j (j = 0 is the bottom, rearmost card)
function zc(j) = 1 + j*step;

// ---- sanity checks ----
// ledge j must clear the card behind it (card j-1 passes behind ledge j)
assert(step >= rear_wall + slop + card_t + 0.4, "step too small: ledge rear wall hits the card behind it");
// the blister of card j must fit under ledge j+1
assert(ledge_h - gutter_d + blister_h <= pitch, "blister too tall: it would hit the ledge above; increase pitch");
echo(str("Rack: ", spine_w+card_w, " x ", H, " x ", zc(N-1)+gw+front_wall+back_t, " mm"));

module ledge(j) {
    z0 = zc(j) - slop - rear_wall;           // rear face of the ledge
    z1 = zc(j) + card_t + slop + front_wall; // front face of the ledge
    y0 = j*pitch;
    difference() {
        union() {
            // ledge beam
            translate([0, y0, z0]) cube([ledge_w, ledge_h, z1 - z0]);
            // bridge from ledge back to the wall plate (spine only)
            translate([0, y0, 0]) cube([spine_w, ledge_h, z1]);
        }
        // gutter open to the right, closed by the spine on the left
        translate([spine_w, y0 + ledge_h - gutter_d, zc(j) - slop])
            cube([ledge_w, gutter_d + 1, gw]);
    }
    // tiny detent bump so cards don't creep out
    translate([spine_w + card_w - thumb_out - 12, y0 + ledge_h - gutter_d + 2, zc(j) - slop - 0.4])
        sphere(r = 0.7, $fn = 16);
}

module keyhole(y) {
    translate([spine_w/2, y, -back_t - 1]) {
        cylinder(d = 9,   h = back_t + 2, $fn = 32);
        translate([0, 0, 0]) hull() {
            cylinder(d = 4.5, h = back_t + 2, $fn = 24);
            translate([0, 12, 0]) cylinder(d = 4.5, h = back_t + 2, $fn = 24);
        }
    }
}

module rack() {
    difference() {
        union() {
            translate([0, 0, -back_t]) cube([spine_w, H, back_t]);   // wall plate
            for (j = [0 : N-1]) ledge(j);
        }
        keyhole(ledge_h + 18);
        keyhole((N/2)*pitch + ledge_h + 18 - pitch/2);
        keyhole((N-1)*pitch + ledge_h + 18);
    }
}

rack();

// Preview-only ghost cards (comment out before export). Uncomment to check fit.
// %for (j = [0 : N-1]) translate([spine_w, j*pitch + ledge_h - gutter_d, zc(j)])
//     cube([card_w, card_h, card_t]);
