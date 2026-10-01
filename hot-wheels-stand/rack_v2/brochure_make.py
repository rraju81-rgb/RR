"""2-page A4 brochure -> brochure/FanOut_Card_Rack_Brochure.pdf (+ page PNGs)"""
from PIL import Image, ImageDraw, ImageFont
W, H = 1654, 2339            # A4 @200 dpi
M = 90
INK, MUTE, ACC, ACC2, PAPER, BAND = (28, 32, 40), (96, 102, 112), (232, 84, 28), (24, 74, 160), (250, 249, 246), (236, 233, 227)
FD = "/usr/share/fonts/truetype/dejavu/"
fb = lambda s: ImageFont.truetype(FD + "DejaVuSans-Bold.ttf", s)
fr = lambda s: ImageFont.truetype(FD + "DejaVuSans.ttf", s)
img = lambda n: Image.open(f"brochure/{n}.png").convert("RGB")


def paste_fit(page, im, box, radius=28):
    x0, y0, x1, y1 = box
    bw, bh = x1 - x0, y1 - y0
    s = max(bw / im.width, bh / im.height)
    im2 = im.resize((int(im.width * s) + 1, int(im.height * s) + 1), Image.LANCZOS)
    l, t = (im2.width - bw) // 2, (im2.height - bh) // 2
    im2 = im2.crop((l, t, l + bw, t + bh))
    mask = Image.new("L", (bw, bh), 0); ImageDraw.Draw(mask).rounded_rectangle((0, 0, bw - 1, bh - 1), radius, fill=255)
    page.paste(im2, (x0, y0), mask)


def wrap(d, text, font, width):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if d.textlength(t, font=font) <= width: cur = t
        else: lines.append(cur); cur = w
    return lines + [cur]


def para(d, x, y, text, font, width, fill=INK, gap=10):
    for ln in wrap(d, text, font, width):
        d.text((x, y), ln, font=font, fill=fill); y += font.size + gap
    return y


def caption(d, x, y, t):
    d.text((x, y), t, font=fr(26), fill=MUTE)


def feature(d, x, y, n, title, body, width):
    d.ellipse((x, y, x + 62, y + 62), fill=ACC)
    d.text((x + 31, y + 31), str(n), font=fb(34), fill="white", anchor="mm")
    d.text((x + 86, y + 2), title, font=fb(33), fill=INK)
    return para(d, x + 86, y + 48, body, fr(27), width - 86, MUTE, 8) + 22


def page1():
    p = Image.new("RGB", (W, H), PAPER); d = ImageDraw.Draw(p)
    d.rectangle((0, 0, W, 150), fill=INK)
    d.text((M, 75), "FANOUT", font=fb(46), fill="white", anchor="lm"); d.text((M + 235, 75), "CARD RACK", font=fr(46), fill=(255, 170, 120), anchor="lm")
    d.text((W - M, 75), "3-car  |  5-car  |  3D-printed + M4 hardware", font=fr(28), fill=(190, 195, 205), anchor="rm")
    paste_fit(p, img("img_hero"), (0, 150, W, 980), radius=0)
    y = 1015
    d.text((M, y), "Pick any car.", font=fb(76), fill=INK); y += 92
    d.text((M, y), "Nothing else moves.", font=fb(76), fill=ACC); y += 112
    y = para(d, M, y, "Stacked card racks make you unload every car above the one you want. The FanOut rack spreads your carded die-cast cars "
             "side by side on a fold-out frame, so every car is fully visible and any single card lifts off its own hook.", fr(31), W - 2 * M, MUTE, 11)
    y += 18
    gap = 28; cw = (W - 2 * M - gap) // 2
    paste_fit(p, img("img_pick"), (M, y, M + cw, y + 400))
    paste_fit(p, img("img_hook"), (M + cw + gap, y, W - M, y + 400))
    caption(d, M + 8, y + 410, "Lift one card straight off its hook. The rest stay put.")
    caption(d, M + cw + gap + 8, y + 410, "A printed peg through the card's hang hole.")
    y += 470
    d.rectangle((M, y, W - M, y + 6), fill=ACC)
    d.text((M, y + 24), "Why collectors choose it", font=fb(42), fill=INK); y += 100
    col = (W - 2 * M - 60) // 2
    ya = feature(d, M, y, 1, "Any car out, instantly", "Each card hangs on its own hook. No unstacking.", col)
    yb = feature(d, M + col + 60, y, 2, "All cars on show", "Cards sit side by side; no blister is hidden.", col)
    y = max(ya, yb) - 8
    ya = feature(d, M, y, 3, "Level and steady", "The lower row rides in a rail, so every hook stays level.", col)
    yb = feature(d, M + col + 60, y, 4, "Simple and repairable", "3 printed designs and standard M4 bolts.", col)
    d.text((W // 2, H - 45), "Cars shown for demonstration only. Generic models; not affiliated with any die-cast brand.", font=fr(23), fill=MUTE, anchor="mm")
    return p


def page2():
    p = Image.new("RGB", (W, H), PAPER); d = ImageDraw.Draw(p)
    d.rectangle((0, 0, W, 150), fill=INK)
    d.text((M, 75), "FANOUT", font=fb(46), fill="white", anchor="lm"); d.text((M + 235, 75), "CARD RACK", font=fr(46), fill=(255, 170, 120), anchor="lm")
    d.text((W - M, 75), "Sizes, specs and what you get", font=fr(28), fill=(190, 195, 205), anchor="rm")
    y = 200
    d.text((M, y), "Two sizes. One simple mechanism.", font=fb(62), fill=INK); y += 100
    gap = 28; cw = (W - 2 * M - gap) // 2
    paste_fit(p, img("img_front3"), (M, y, M + cw, y + 560))
    paste_fit(p, img("img_closed"), (M + cw + gap, y, W - M, y + 560))
    caption(d, M + 8, y + 570, "3-car rack, front view.")
    caption(d, M + cw + gap + 8, y + 570, "Frame closed, cards off, for storage.")
    y += 650
    col = (W - 2 * M - 60) // 2
    ya = feature(d, M, y, 5, "Prints without supports", "Fits a 300 mm bed. The long rail comes in joined segments.", col)
    yb = feature(d, M + col + 60, y, 6, "Tested in CAD", "Collision sweep over the whole motion, tolerance and load checks.", col)
    y = max(ya, yb) + 10
    ya = feature(d, M, y, 7, "Wall-ready", "Countersunk screw holes in the rail; no extra bracket.", col)
    yb = feature(d, M + col + 60, y, 8, "No snaps or springs", "Nylon-lock nuts hold every pivot; nothing to break or lose.", col)
    y = max(ya, yb) + 20
    d.rectangle((M, y, W - M, y + 6), fill=ACC); y += 40
    d.text((M, y), "Specifications", font=fb(46), fill=INK); y += 85
    rows = [("", "3-car", "5-car"), ("Rail length", "364 mm", "588 mm"), ("Hook spacing (open)", "112 mm", "112 mm"),
            ("Overall height with cards", "about 270 mm", "about 270 mm"), ("Depth from wall", "about 41 mm", "about 41 mm"),
            ("Printed parts", "3 link A, 3 link B, 2 rail", "5 link A, 5 link B, 3 rail"), ("Hardware", "9 M4 bolts + 9 nuts", "15 M4 bolts + 15 nuts"),
            ("Wall screws", "8", "12"), ("Card size", "105 x 165 mm", "105 x 165 mm")]
    cx = [M, M + 560, M + 1100]
    for i, r in enumerate(rows):
        if i % 2 == 0: d.rectangle((M - 14, y - 6, W - M + 14, y + 52), fill=BAND if i else ACC2)
        for j, t in enumerate(r):
            d.text((cx[j], y + 4), t, font=fb(30) if (i == 0 or j == 0) else fr(30), fill="white" if i == 0 else INK)
        y += 58
    y += 40
    d.text((M, y), "Good to know", font=fb(40), fill=INK); y += 70
    for t in ("Remove the cards before folding the frame closed; cards hang only while it is open.",
              "Hook position suits cards whose hang hole is about 7 mm; check your cards before ordering.",
              "Mount into a stud or use wall anchors rated for 5 kg or more."):
        d.ellipse((M, y + 11, M + 14, y + 25), fill=ACC)
        y = para(d, M + 36, y, t, fr(29), W - 2 * M - 36, INK, 8) + 12
    d.text((W // 2, H - 60), "Cars shown for demonstration only. Generic models; not affiliated with any die-cast brand.", font=fr(23), fill=MUTE, anchor="mm")
    return p


if __name__ == "__main__":
    a, b = page1(), page2()
    a.save("brochure/page1.png"); b.save("brochure/page2.png")
    a.save("brochure/FanOut_Card_Rack_Brochure.pdf", save_all=True, append_images=[b], resolution=200)
    print("ok")
