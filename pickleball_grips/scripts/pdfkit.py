"""Small drawing toolkit on top of reportlab's canvas.  All coordinates are millimetres measured
from the TOP-LEFT corner of the A4 page (y grows downward); conversion to PDF points happens here."""
import io
from pathlib import Path

from PIL import Image
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas as rl_canvas

MM = 72.0 / 25.4
PAGE_W, PAGE_H = 210.0, 297.0

_FD = Path("/usr/share/fonts/truetype/liberation")
for key, fn in (("R", "LiberationSans-Regular.ttf"), ("B", "LiberationSans-Bold.ttf"),
                ("I", "LiberationSans-Italic.ttf"), ("BI", "LiberationSans-BoldItalic.ttf")):
    pdfmetrics.registerFont(TTFont(f"LS-{key}", str(_FD / fn)))
pdfmetrics.registerFontFamily("LS-R", normal="LS-R", bold="LS-B", italic="LS-I", boldItalic="LS-BI")
F_R, F_B, F_I, F_BI = "LS-R", "LS-B", "LS-I", "LS-BI"

INK = "#16202B"
MUTED = "#5D6875"
SUBTLE = "#8B95A1"
HAIR = "#D5DAE0"
PANEL = "#F3F4F6"
PANEL2 = "#E7EAEE"
DIM = "#1E5AA8"
RED = "#C0392B"
GREEN = "#2E7D5B"
WHITE = "#FFFFFF"


def hexrgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


def tint(h, k):
    """Blend colour h toward white by k (0 = colour, 1 = white)."""
    r, g, b = hexrgb(h)
    return "#%02X%02X%02X" % tuple(int(round((c + (1 - c) * k) * 255)) for c in (r, g, b))


def shade(h, k):
    r, g, b = hexrgb(h)
    return "#%02X%02X%02X" % tuple(int(round(c * (1 - k) * 255)) for c in (r, g, b))


def sw(text, font, size):
    return pdfmetrics.stringWidth(text, font, size)


def wrap(text, font, size, width_mm):
    """Greedy word wrap -> list of lines (each fits in width_mm)."""
    out = []
    for para in str(text).split("\n"):
        words, line = para.split(), ""
        for w in words:
            t = (line + " " + w).strip()
            if sw(t, font, size) / MM <= width_mm or not line:
                line = t
            else:
                out.append(line)
                line = w
        out.append(line)
    return out


_img_cache = {}


def image_reader(path, jpeg=True, quality=90, max_px=None, crop=None):
    """PNG -> (optionally) JPEG in memory so the PDF stays small; cached per path.
    crop = (left, top, right, bottom) in fractions of the image."""
    key = (str(path), jpeg, quality, max_px, crop)
    if key not in _img_cache:
        im = Image.open(path)
        if crop:
            W, H = im.size
            im = im.crop((int(crop[0] * W), int(crop[1] * H), int(crop[2] * W), int(crop[3] * H)))
        if max_px and max(im.size) > max_px:
            k = max_px / max(im.size)
            im = im.resize((int(im.width * k), int(im.height * k)), Image.LANCZOS)
        if jpeg:
            buf = io.BytesIO()
            im.convert("RGB").save(buf, "JPEG", quality=quality, subsampling=0, optimize=True)
            buf.seek(0)
            _img_cache[key] = ImageReader(buf)
        else:
            _img_cache[key] = ImageReader(im.convert("RGB"))
    return _img_cache[key]


class Page:
    """Thin wrapper: top-left millimetre coordinates + styled primitives."""

    def __init__(self, c):
        self.c = c

    # -- coordinate helpers
    @staticmethod
    def X(x):
        return x * MM

    @staticmethod
    def Y(y):
        return (PAGE_H - y) * MM

    # -- shapes
    def line(self, x1, y1, x2, y2, color=INK, w=0.25, dash=None, cap=0, alpha=None):
        c = self.c
        c.saveState()
        if alpha is not None:
            c.setStrokeAlpha(alpha)
        c.setStrokeColor(hexrgb(color))
        c.setLineWidth(w * MM)
        c.setLineCap(cap)
        if dash:
            c.setDash([d * MM for d in dash], 0)
        c.line(self.X(x1), self.Y(y1), self.X(x2), self.Y(y2))
        c.restoreState()

    def rect(self, x, y, w, h, fill=None, stroke=None, sw_=0.25, r=0, dash=None):
        c = self.c
        c.saveState()
        if fill:
            c.setFillColor(hexrgb(fill))
        if stroke:
            c.setStrokeColor(hexrgb(stroke))
            c.setLineWidth(sw_ * MM)
        if dash:
            c.setDash([d * MM for d in dash], 0)
        if r:
            c.roundRect(self.X(x), self.Y(y + h), w * MM, h * MM, r * MM, stroke=1 if stroke else 0, fill=1 if fill else 0)
        else:
            c.rect(self.X(x), self.Y(y + h), w * MM, h * MM, stroke=1 if stroke else 0, fill=1 if fill else 0)
        c.restoreState()

    def circle(self, x, y, r, fill=None, stroke=None, sw_=0.25):
        c = self.c
        c.saveState()
        if fill:
            c.setFillColor(hexrgb(fill))
        if stroke:
            c.setStrokeColor(hexrgb(stroke))
            c.setLineWidth(sw_ * MM)
        c.circle(self.X(x), self.Y(y), r * MM, stroke=1 if stroke else 0, fill=1 if fill else 0)
        c.restoreState()

    def polygon(self, pts, fill=None, stroke=None, sw_=0.25, close=True, dash=None):
        c = self.c
        c.saveState()
        if fill:
            c.setFillColor(hexrgb(fill))
        if stroke:
            c.setStrokeColor(hexrgb(stroke))
            c.setLineWidth(sw_ * MM)
            c.setLineJoin(1)
        if dash:
            c.setDash([d * MM for d in dash], 0)
        p = c.beginPath()
        p.moveTo(self.X(pts[0][0]), self.Y(pts[0][1]))
        for x, y in pts[1:]:
            p.lineTo(self.X(x), self.Y(y))
        if close:
            p.close()
        c.drawPath(p, stroke=1 if stroke else 0, fill=1 if fill else 0)
        c.restoreState()

    def multipath(self, rings, fill=None, stroke=None, sw_=0.25, dash=None):
        """Several closed rings drawn as ONE path with even-odd fill (outer + holes)."""
        from reportlab.pdfgen.canvas import FILL_EVEN_ODD
        c = self.c
        c.saveState()
        if fill:
            c.setFillColor(hexrgb(fill))
        if stroke:
            c.setStrokeColor(hexrgb(stroke))
            c.setLineWidth(sw_ * MM)
            c.setLineJoin(1)
        if dash:
            c.setDash([d * MM for d in dash], 0)
        p = c.beginPath()
        for ring in rings:
            p.moveTo(self.X(ring[0][0]), self.Y(ring[0][1]))
            for x, y in ring[1:]:
                p.lineTo(self.X(x), self.Y(y))
            p.close()
        c.drawPath(p, stroke=1 if stroke else 0, fill=1 if fill else 0, fillMode=FILL_EVEN_ODD)
        c.restoreState()

    def polyline(self, pts, color=INK, w=0.25, dash=None):
        c = self.c
        c.saveState()
        c.setStrokeColor(hexrgb(color))
        c.setLineWidth(w * MM)
        c.setLineJoin(1)
        if dash:
            c.setDash([d * MM for d in dash], 0)
        p = c.beginPath()
        p.moveTo(self.X(pts[0][0]), self.Y(pts[0][1]))
        for x, y in pts[1:]:
            p.lineTo(self.X(x), self.Y(y))
        c.drawPath(p, stroke=1, fill=0)
        c.restoreState()

    def clip_round(self, x, y, w, h, r):
        p = self.c.beginPath()
        p.roundRect(self.X(x), self.Y(y + h), w * MM, h * MM, r * MM)
        self.c.clipPath(p, stroke=0, fill=0)

    def image(self, path, x, y, w, h, jpeg=True, quality=90, round_=0, max_px=None, crop=None):
        c = self.c
        c.saveState()
        if round_:
            self.clip_round(x, y, w, h, round_)
        c.drawImage(image_reader(path, jpeg, quality, max_px, crop), self.X(x), self.Y(y + h), w * MM, h * MM)
        c.restoreState()

    # -- text
    def text(self, x, y, s, font=F_R, size=9, color=INK, anchor="l", rot=0):
        """y is the text BASELINE (mm from top)."""
        c = self.c
        c.saveState()
        c.setFillColor(hexrgb(color))
        c.setFont(font, size)
        if rot:
            c.translate(self.X(x), self.Y(y))
            c.rotate(rot)
            xx, yy = 0, 0
        else:
            xx, yy = self.X(x), self.Y(y)
        if anchor == "l":
            c.drawString(xx, yy, s)
        elif anchor == "r":
            c.drawRightString(xx, yy, s)
        else:
            c.drawCentredString(xx, yy, s)
        c.restoreState()

    def para(self, x, y, s, width, font=F_R, size=9, color=INK, leading=None, max_lines=None, anchor="l"):
        """Wrapped paragraph; y = top of first line. Returns the y of the bottom (mm)."""
        lead = (leading or size * 1.32) / MM
        lines = wrap(s, font, size, width)
        if max_lines and len(lines) > max_lines:
            lines = lines[:max_lines]
            lines[-1] = lines[-1].rstrip(" .,;") + "..."
        base = y + size / MM * 0.78
        for i, ln in enumerate(lines):
            self.text(x if anchor == "l" else x + width, base + i * lead, ln, font, size, color, anchor=anchor)
        return y + len(lines) * lead

    # -- dimension lines (blue, arrows, white-haloed label)
    def arrow(self, x, y, dx, dy, color=DIM, L=2.0, Wd=0.7):
        """Filled arrowhead with tip at (x,y) pointing along (dx,dy) (unit)."""
        import math
        n = math.hypot(dx, dy) or 1
        dx, dy = dx / n, dy / n
        bx, by = x - dx * L, y - dy * L
        px, py = -dy, dx
        self.polygon([(x, y), (bx + px * Wd, by + py * Wd), (bx - px * Wd, by - py * Wd)], fill=color, stroke=None)

    def dim_h(self, x1, x2, y, label, ext1=None, ext2=None, color=DIM, size=6.6, above=True, out_arrows=None, gap=1.2, over=1.6):
        """Horizontal dimension between x1 and x2 with the dimension line at height y.  ext1/ext2 =
        y of the measured features (extension lines are drawn from there)."""
        for xe, ye in ((x1, ext1), (x2, ext2)):
            if ye is not None:
                s = 1 if y > ye else -1
                self.line(xe, ye + s * gap, xe, y + s * over, color, 0.13)
        span = abs(x2 - x1)
        lab_w = sw(label, F_R, size) / MM + 1.6
        inside = span > lab_w + 5.2 if out_arrows is None else not out_arrows
        if inside:
            self.line(x1, y, x2, y, color, 0.16)
            self.arrow(x1, y, 1, 0, color)
            self.arrow(x2, y, -1, 0, color)
        else:
            self.line(x1 - 5, y, x2 + 5, y, color, 0.16)
            self.arrow(x1, y, 1, 0, color)
            self.arrow(x2, y, -1, 0, color)
        cx = (x1 + x2) / 2
        ty = y - 0.9 if above else y + 2.6
        self.text(cx, ty, label, F_R, size, color, anchor="c")

    def dim_v(self, y1, y2, x, label, ext1=None, ext2=None, color=DIM, size=6.6, left=True, gap=1.2, over=1.6, halo=False):
        for ye, xe in ((y1, ext1), (y2, ext2)):
            if xe is not None:
                s = 1 if x > xe else -1
                self.line(xe + s * gap, ye, x + s * over, ye, color, 0.13)
        self.line(x, y1, x, y2, color, 0.16)
        self.arrow(x, y1, 0, 1, color)
        self.arrow(x, y2, 0, -1, color)
        cy = (y1 + y2) / 2
        lw = sw(label, F_R, size) / MM
        tx = x - 0.9 if left else x + 2.6                      # rotated 90 deg: glyph body lies left of the baseline
        if halo:
            self.rect(tx - 2.2, cy - lw / 2 - 0.8, 2.6, lw + 1.6, fill=WHITE)
        self.text(tx, cy, label, F_R, size, color, anchor="c", rot=90)

    def leader(self, x1, y1, x2, y2, label, color=DIM, size=6.4, anchor="l", dot=True):
        self.line(x1, y1, x2, y2, color, 0.15)
        if dot:
            self.circle(x1, y1, 0.45, fill=color)
        self.text(x2 + (0.8 if anchor == "l" else -0.8), y2 + 0.8, label, F_R, size, color, anchor=anchor)


def new_canvas(path, title, author="Claude Code", subject="", keywords=""):
    c = rl_canvas.Canvas(str(path), pagesize=(PAGE_W * MM, PAGE_H * MM), pageCompression=1, initialFontName="LS-R", initialFontSize=8)
    c.setTitle(title)
    c.setAuthor(author)
    c.setSubject(subject)
    c.setKeywords(keywords)
    c.setCreator("Pickleball grip spec generator (reportlab)")
    return c


def table(pg, x, y, col_w, rows, header=None, row_h=5.6, size=7.6, hsize=6.6, aligns=None, fonts=None, zebra=True,
          hcolor=MUTED, line=HAIR, pad=1.8, bold_first=False, colors=None, hfill=None):
    """Simple grid-less table (hairline row rules).  rows = list of lists of str.  Returns bottom y."""
    n = len(col_w)
    aligns = aligns or ["l"] * n
    yy = y
    if header:
        if hfill:
            pg.rect(x, yy, sum(col_w), row_h, fill=hfill)
        for j, h in enumerate(header):
            cx = x + sum(col_w[:j])
            ax = cx + pad if aligns[j] == "l" else (cx + col_w[j] - pad if aligns[j] == "r" else cx + col_w[j] / 2)
            pg.text(ax, yy + row_h * 0.68, h.upper(), F_B, hsize, hcolor, anchor=aligns[j] if aligns[j] in "lr" else "c")
        yy += row_h
        pg.line(x, yy, x + sum(col_w), yy, INK, 0.3)
    for i, r in enumerate(rows):
        if zebra and i % 2 == 1:
            pg.rect(x, yy, sum(col_w), row_h, fill=PANEL)
        for j, cell in enumerate(r):
            cx = x + sum(col_w[:j])
            f = (fonts[j] if fonts else (F_B if (bold_first and j == 0) else F_R))
            col = (colors[i][j] if colors and colors[i] and colors[i][j] else INK)
            ax = cx + pad if aligns[j] == "l" else (cx + col_w[j] - pad if aligns[j] == "r" else cx + col_w[j] / 2)
            pg.text(ax, yy + row_h * 0.68, str(cell), f, size, col, anchor=aligns[j] if aligns[j] in "lr" else "c")
        yy += row_h
        pg.line(x, yy, x + sum(col_w), yy, line, 0.15)
    return yy
