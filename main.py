#!/usr/bin/env python3
"""news-image-20261123 v2 — a one-page newspaper front page for Monday 23 Nov 2026.

Draws the whole page at runtime from embedded story data, using a clean
vector (single-stroke) sans-serif font defined in this file. Pure Python 3.13
standard library only: no PIL, no external font files, no network.

How it works:
  * A Hershey-style stroke font: every glyph is a set of polylines in a
    100-unit cap-height space, authored here by hand. Curves are short
    straight runs, so diagonal letterforms are smooth instead of blocky.
  * Text is drawn into a 2x supersampled grayscale mask and then blended
    onto the page, which anti-aliases the strokes.
  * The PNG is encoded by hand (zlib + struct), RGB, no filter tricks.

The program writes $MAKEFUN_OUTPUT_DIR/entry.png (default: ./out/entry.png).
Deterministic: same bytes on every run.
"""

import math
import os
import struct
import sys
import time
import zlib


# ---------------------------------------------------------------- PNG writer

def _chunk(typ, data):
    out = struct.pack(">I", len(data)) + typ + data
    out += struct.pack(">I", zlib.crc32(typ + data) & 0xFFFFFFFF)
    return out


def write_png(path, w, h, rgb):
    """rgb: bytearray, 3 bytes per pixel, row-major, top to bottom."""
    raw = bytearray()
    stride = w * 3
    for y in range(h):
        raw.append(0)  # filter: none
        raw += rgb[y * stride:(y + 1) * stride]
    png = b"\x89PNG\r\n\x1a\n"
    png += _chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
    png += _chunk(b"IDAT", zlib.compress(bytes(raw), 6))
    png += _chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)
    return len(png)


# ---------------------------------------------------------------- stroke font
# Each glyph: (advance width, "stroke|stroke|..."); a stroke is a run of
# "x,y" points. Coordinates are font units: y=0 baseline, y=100 cap top,
# y=70 x-height, y<0 descender. A stroke of two identical points is a dot.
# The font is a single-stroke geometric sans, authored for this entry.

FONT_RAW = {
    # ---- uppercase (cap height 100) ----
    "A": (100, "8,0 50,100 92,0|28,38 72,38"),
    "B": (90, "8,0 8,100|8,100 55,100 78,88 78,62 55,50 8,50|8,50 60,50 82,38 82,12 60,0 8,0"),
    "C": (92, "85,85 60,100 25,100 8,78 8,22 25,0 60,0 85,15"),
    "D": (90, "8,0 8,100|8,100 55,100 82,78 82,22 55,0 8,0"),
    "E": (88, "8,0 8,100 80,100|8,50 62,50|8,0 80,0"),
    "F": (88, "8,0 8,100 80,100|8,52 62,52"),
    "G": (92, "85,85 60,100 25,100 8,78 8,22 25,0 62,0 85,22 85,45 58,45"),
    "H": (100, "8,0 8,100|92,0 92,100|8,50 92,50"),
    "I": (60, "10,100 50,100|30,100 30,0|10,0 50,0"),
    "J": (85, "70,100 70,25 55,0 28,0 12,16"),
    "K": (92, "8,0 8,100|85,100 8,45|30,60 85,0"),
    "L": (90, "8,0 8,100|8,0 82,0"),
    "M": (100, "8,0 8,100 50,35 92,100 92,0"),
    "N": (100, "8,0 8,100 92,0 92,100"),
    "O": (100, "30,0 70,0 92,25 92,75 70,100 30,100 8,75 8,25 30,0"),
    "P": (90, "8,0 8,100|8,100 60,100 82,85 82,62 60,48 8,48"),
    "Q": (100, "30,0 70,0 92,25 92,75 70,100 30,100 8,75 8,25 30,0|62,25 92,-8"),
    "R": (90, "8,0 8,100|8,100 60,100 82,85 82,62 60,48 8,48|45,48 88,0"),
    "S": (100, "78,88 60,100 30,100 12,88 12,68 30,52 70,48 88,32 88,12 70,0 40,0 22,12"),
    "T": (100, "8,100 92,100|50,100 50,0"),
    "U": (100, "8,100 8,22 25,0 75,0 92,22 92,100"),
    "V": (100, "8,100 50,0 92,100"),
    "W": (100, "8,100 25,0 50,55 75,0 92,100"),
    "X": (100, "8,100 92,0|92,100 8,0"),
    "Y": (100, "8,100 50,45 92,100|50,45 50,0"),
    "Z": (100, "8,100 92,100 8,0 92,0"),
    # ---- lowercase (x-height 70, ascender 100, descender -25) ----
    "a": (80, "15,55 30,70 55,70 70,55 70,15 55,0 30,0 15,15 15,55|70,70 70,0"),
    "b": (80, "10,0 10,100|10,50 25,70 55,70 70,55 70,15 55,0 25,0 10,15 10,50"),
    "c": (76, "65,60 50,70 25,70 12,55 12,15 25,0 50,0 65,10"),
    "d": (76, "10,55 25,70 50,70 65,55 65,15 50,0 25,0 10,15 10,55|65,100 65,0"),
    "e": (78, "12,38 66,38|66,38 66,15 55,0 28,0 12,15 12,38 28,52 55,52 68,38"),
    "f": (68, "55,100 35,100 25,88 25,0|12,68 58,68"),
    "g": (80, "15,55 30,70 55,70 70,55 70,15 55,0 30,0 15,15 15,55|70,0 70,-18 55,-25 35,-25 25,-15"),
    "h": (52, "10,0 10,100|10,70 28,70 40,52 40,0"),
    "i": (40, "30,0 30,70|30,90 30,90"),
    "j": (40, "30,70 30,-15 15,-25 5,-18|30,90 30,90"),
    "k": (76, "10,0 10,100|65,70 10,30|28,45 65,0"),
    "l": (40, "30,0 30,100"),
    "m": (72, "10,0 10,70|35,0 35,70|10,70 25,70 35,55 35,0|35,70 50,70 60,55 60,0"),
    "n": (52, "10,0 10,70|10,70 28,70 40,52 40,0"),
    "o": (76, "20,0 50,0 65,15 65,55 50,70 20,70 5,55 5,15 20,0"),
    "p": (80, "10,0 10,-25|10,50 25,70 55,70 70,55 70,15 55,0 25,0 10,15 10,50"),
    "q": (76, "10,55 25,70 50,70 65,55 65,15 50,0 25,0 10,15 10,55|65,70 65,-25"),
    "r": (58, "10,0 10,70|10,55 25,70 40,70 48,62"),
    "s": (70, "55,62 42,70 22,70 10,60 10,45 22,35 48,33 60,22 60,8 48,0 28,0 16,8"),
    "t": (62, "30,100 30,0 45,0|12,68 52,68"),
    "u": (70, "10,70 10,15 22,0 48,0 60,15 60,70"),
    "v": (72, "8,70 35,0 62,70"),
    "w": (72, "8,70 20,0 35,35 50,0 62,70"),
    "x": (72, "8,70 62,0|62,70 8,0"),
    "y": (72, "8,70 35,0 62,70|35,0 35,-18 22,-25"),
    "z": (72, "8,70 62,70 8,0 62,0"),
}

FONT_RAW.update({
    # ---- digits (cap height 100) ----
    "0": (95, "28,0 68,0 90,25 90,75 68,100 28,100 8,75 8,25 28,0"),
    "1": (70, "55,100 30,75|55,100 55,0|30,0 80,0"),
    "2": (90, "15,85 30,100 65,100 82,85 82,60 60,35 15,0 85,0"),
    "3": (90, "15,85 30,100 65,100 82,85 82,65 65,50 82,35 82,15 65,0 30,0 15,15"),
    "4": (92, "75,100 20,40 85,40|70,100 70,0"),
    "5": (90, "85,100 15,100 15,55 55,55 80,40 80,15 60,0 30,0 15,12"),
    "6": (90, "78,88 60,100 30,100 12,82 12,45 25,18 55,18 72,32 72,55 55,70 25,70 12,55"),
    "7": (90, "12,100 88,100 35,0"),
    "8": (95, "30,100 65,100 78,85 78,65 65,52 30,52 18,65 18,85 30,100|30,52 65,52 80,38 80,15 65,0 30,0 15,15 15,38 30,52"),
    "9": (90, "15,62 30,48 65,48 80,62 80,85 65,100 30,100 15,85 15,62|80,100 80,0"),
    # ---- punctuation ----
    ".": (40, "20,4 20,4"),
    ",": (40, "22,4 22,4|26,2 16,-18"),
    ":": (40, "20,65 20,65|20,20 20,20"),
    ";": (40, "20,65 20,65|26,20 16,-14"),
    "'": (30, "18,100 12,74"),
    '"': (55, "14,100 8,74|40,100 34,74"),
    "!": (40, "20,100 20,28|20,6 20,6"),
    "?": (78, "15,85 30,100 60,100 72,88 72,68 55,52 32,45|32,45 32,30|32,6 32,6"),
    "-": (60, "8,45 52,45"),
    "\u2013": (80, "8,45 72,45"),   # en dash
    "\u2014": (100, "5,45 95,45"),  # em dash
    "&": (95, "65,85 50,100 30,100 18,88 18,70 30,55 55,42 75,22 75,5 60,0 40,0 28,10|18,42 72,72"),
    "%": (100, "15,100 85,0|28,78 45,78 53,86 53,96 45,104 28,104 20,96 20,86 28,78|48,4 65,4 73,-4 73,-14 65,-22 48,-22 40,-14 40,-4 48,4"),
    "(": (45, "35,100 15,75 15,25 35,0"),
    ")": (45, "10,100 30,75 30,25 10,0"),
    "+": (85, "42,15 42,85|15,50 70,50"),
    "=": (85, "12,62 73,62|12,38 73,38"),
    "$": (90, "70,85 52,100 28,100 12,85 12,65 28,50 62,48 78,32 78,12 62,0 38,0 22,12|45,108 45,-8"),
    "*": (80, "40,100 40,0|8,80 72,20|72,80 8,20"),
    "/": (70, "18,0 58,100"),
    "_": (90, "5,-8 85,-8"),
    "\u2022": (45, "22,45 22,45"),  # bullet
    " ": (28, ""),
})


def _parse_font():
    out = {}
    for ch, (adv, spec) in FONT_RAW.items():
        strokes = []
        if spec:
            for st in spec.split("|"):
                pts = []
                for tok in st.split():
                    xs, ys = tok.split(",")
                    pts.append((int(xs), int(ys)))
                strokes.append(pts)
        out[ch] = (adv, strokes)
    return out


FONT = _parse_font()


# ---------------------------------------------------------------- rasterizer

class Page:
    """A 1024x1024 RGB page plus a 2x supersampled text mask."""

    def __init__(self, w=1024, h=1024):
        self.w, self.h = w, h
        self.rgb = bytearray(b"\xff" * (w * h * 3))
        self.mask = bytearray(4 * w * h)  # 2x in each dimension

    # ---- flat fills (rules, bands) go straight into the RGB buffer ----
    def fill_rect(self, x0, y0, x1, y1, color):
        r, g, b = color
        x0c = max(0, x0)
        x1c = min(self.w, x1)
        if x1c <= x0c:
            return
        row = bytes((r, g, b)) * (x1c - x0c)
        for y in range(max(0, y0), min(self.h, y1)):
            s = (y * self.w + x0c) * 3
            self.rgb[s:s + 3 * (x1c - x0c)] = row

    # ---- 2x mask strokes ----
    def _stamp(self, cx, cy, r):
        w2 = self.w * 2
        h2 = self.h * 2
        x0 = max(0, cx - r)
        x1 = min(w2 - 1, cx + r)
        y0 = max(0, cy - r)
        y1 = min(h2 - 1, cy + r)
        if x1 < x0 or y1 < y0:
            return
        row = b"\xff" * (x1 - x0 + 1)
        for y in range(y0, y1 + 1):
            s = y * w2 + x0
            self.mask[s:s + (x1 - x0 + 1)] = row

    def line2(self, x0, y0, x1, y1, r):
        """Bresenham line in 2x coordinates, square stamp of half-side r."""
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy
        while True:
            self._stamp(x0, y0, r)
            if x0 == x1 and y0 == y1:
                return
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x0 += sx
            if e2 < dx:
                err += dx
                y0 += sy

    def dot2(self, cx, cy, r):
        self._stamp(cx, cy, r)

    # ---- blend a 1x box of the mask onto the page with an ink colour ----
    def blend_box(self, x0, y0, x1, y1, ink):
        w2 = self.w * 2
        ir, ig, ib = ink
        x0 = max(0, x0)
        y0 = max(0, y0)
        x1 = min(self.w, x1)
        y1 = min(self.h, y1)
        for y in range(y0, y1):
            m0 = (2 * y) * w2
            m1 = (2 * y + 1) * w2
            orow = y * self.w * 3
            for x in range(x0, x1):
                i = m0 + 2 * x
                j = m1 + 2 * x
                m = (self.mask[i] + self.mask[i + 1]
                     + self.mask[j] + self.mask[j + 1]) >> 2
                if m == 0:
                    continue
                o = orow + 3 * x
                if m == 255:
                    self.rgb[o] = ir
                    self.rgb[o + 1] = ig
                    self.rgb[o + 2] = ib
                else:
                    self.rgb[o] = (self.rgb[o] * (255 - m) + ir * m) // 255
                    self.rgb[o + 1] = (self.rgb[o + 1] * (255 - m) + ig * m) // 255
                    self.rgb[o + 2] = (self.rgb[o + 2] * (255 - m) + ib * m) // 255


def text_width(text, size, sx=1.0):
    """Width in 1x px of text at cap-height `size`, horizontal scale `sx`."""
    w = 0.0
    for ch in text:
        adv, _ = FONT.get(ch, FONT["?"])
        w += adv * sx
    return w * size / 100.0


def draw_text(page, x, y_base, text, size, ink, align="left", sx=1.0,
              max_w=None):
    """Draw one line; y_base is the baseline. Returns (size_used, width)."""
    if max_w is not None:
        w = text_width(text, size, sx)
        if w > max_w:
            size = size * max_w / w
    w = text_width(text, size, sx)
    if align == "center":
        x0 = x - w / 2.0
    elif align == "right":
        x0 = x - w
    else:
        x0 = float(x)
    # stroke width at 2x: ~15% of cap height, at least 3 (2x px)
    sw = max(3, int(round(0.30 * size)))
    r = sw // 2
    dot_r = max(r, int(round(0.18 * size)))
    cx = x0
    u2 = 2.0 * size / 100.0  # font units -> 2x px
    for ch in text:
        adv, strokes = FONT.get(ch, FONT["?"])
        if ch != " ":
            for pts in strokes:
                if len(pts) == 2 and pts[0] == pts[1]:
                    px, py = pts[0]
                    dx = int(round((cx + px * sx * size / 100.0) * 2))
                    dy = int(round((y_base - py * size / 100.0) * 2))
                    page.dot2(dx, dy, dot_r)
                else:
                    for (ax, ay), (bx, by) in zip(pts, pts[1:]):
                        x0p = int(round((cx + ax * sx * size / 100.0) * 2))
                        y0p = int(round((y_base - ay * size / 100.0) * 2))
                        x1p = int(round((cx + bx * sx * size / 100.0) * 2))
                        y1p = int(round((y_base - by * size / 100.0) * 2))
                        page.line2(x0p, y0p, x1p, y1p, r)
        cx += adv * sx * size / 100.0
    top = int(y_base - size * 1.15)
    bot = int(y_base + size * 0.30) + 1
    page.blend_box(int(x0), top, int(x0 + w) + 1, bot, ink)
    return size, w


def polyline1x(page, pts, r, ink, bbox):
    """Draw a polyline given in 1x float coords, then blend its bbox."""
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):
        page.line2(int(round(ax * 2)), int(round(ay * 2)),
                   int(round(bx * 2)), int(round(by * 2)), r)
    page.blend_box(bbox[0], bbox[1], bbox[2], bbox[3], ink)


def ellipse_pts(cx, cy, rx, ry, n=24):
    pts = []
    for i in range(n + 1):
        a = 2.0 * math.pi * i / n
        pts.append((cx + rx * math.cos(a), cy + ry * math.sin(a)))
    return pts


def draw_globe(page, cx, cy, r, ink):
    """Small line globe: outer circle, equator and meridian ellipses."""
    sw = 2  # stamp half-side at 2x -> 2px stroke at 1x
    bbox = (int(cx - r - 3), int(cy - r - 3), int(cx + r + 4), int(cy + r + 4))
    polyline1x(page, ellipse_pts(cx, cy, r, r, 28), sw, ink, bbox)
    polyline1x(page, ellipse_pts(cx, cy, r, r * 0.38, 28), sw, ink, bbox)
    polyline1x(page, ellipse_pts(cx, cy, r * 0.38, r, 28), sw, ink, bbox)


# ---------------------------------------------------------------- the day

BLACK = (20, 20, 20)
RED = (176, 24, 32)
WHITE = (255, 255, 255)

LEAD = "TRUMP VOWS TO SINK IRANIAN VESSELS"
DECK = "After a U.S. strike on a tanker, Hormuz shipping faces its worst attacks since the war began."

# 33 list stories (1 lead + 33 = 34) across 8 regions + a WORLD section.
# Every headline happened or was first reported on Monday 23 November 2026.
# The Lagarde item in v1 was announced 29 Oct, so v2 replaces it with the
# genuinely Monday story: Burnham puts his landmark EU deal to MPs.
STORIES = [
    ("WORLD", "COP31 collapses with no deal, first since 2009"),
    ("WORLD", "US futures rebound after AI rout shakes Asia"),
    ("WORLD", "Claude claims proof of Riemann Hypothesis"),
    ("WORLD", "Chinese hackers suspected in AI campus attacks"),
    ("USA", "Democrats win 258 House seats, most since 1992"),
    ("USA", "Trump backs 10% credit-card interest cap"),
    ("USA", "Delta: 1,600 flights delayed by computer fault"),
    ("USA", "Army to detonate Iowa explosives despite court"),
    ("USA", "ICE detention at Seattle airport draws anger"),
    ("USA", "Mets sign Skubal for $450M, a record deal"),
    ("S. AMERICA", "Bolsonaro in intensive care, bowel blockage"),
    ("S. AMERICA", "Colombia asks X to suspend ex-president Petro"),
    ("S. AMERICA", "Hezbollah 'financier' arrested in Brazil"),
    ("EUROPE", "French leaders both question Ukraine aid"),
    ("EUROPE", "French students plan nationwide protests"),
    ("EUROPE", "Burnham hails landmark EU deal before MPs"),
    ("EUROPE", "FIFA to name UK as 2035 Women's World Cup host"),
    ("EUROPE", "Manchester arena evacuated in tear-gas scare"),
    ("EUROPE", "Audi profits fall as China market weakens"),
    ("MIDEAST", "Hawks press Trump on Iran; he says no rush"),
    ("MIDEAST", "Russian frigate Merkury sinks off Libya"),
    ("MIDEAST", "Gaza war left 'toxic wasteland', experts find"),
    ("MIDEAST", "Settlers torch 12 Palestinian vehicles"),
    ("AFRICA", "Sudan: drones hit Khartoum, UN site damaged"),
    ("AFRICA", "Egypt rejects rival government in Sudan"),
    ("E. ASIA", "South Korea exports pass $1 trillion, a first"),
    ("E. ASIA", "KOSPI plunges 5% in AI rout; Seoul acts"),
    ("E. ASIA", "Taiwan stocks swing 1,578 points; TSMC up 2%"),
    ("E. ASIA", "South Korea minister quits over exam-cheating"),
    ("E. ASIA", "Mongolia president resigns, parliament agrees"),
    ("S.E. ASIA", "Mayon eruption raises fears of bigger blast"),
    ("S.E. ASIA", "Indonesia: 50 missing after factory fire"),
    ("S. ASIA", "Nepal PM Balen Shah visits India on first trip"),
]


def build():
    p = Page()
    # --- masthead: globe mark, date, tagline ---
    draw_globe(p, 58, 44, 18, BLACK)
    draw_text(p, 512, 80, "MONDAY 23 NOVEMBER 2026", 44, BLACK,
              align="center", sx=0.92, max_w=880)
    draw_text(p, 512, 106, "34 STORIES \u2022 8 REGIONS \u2022 THE WORLD IN ONE DAY",
              14, BLACK, align="center")
    p.fill_rect(40, 118, 984, 120, BLACK)
    p.fill_rect(40, 123, 984, 126, RED)
    # --- lead story ---
    draw_text(p, 40, 170, LEAD, 34, BLACK, align="left", sx=0.92, max_w=944)
    draw_text(p, 40, 198, DECK, 16, RED, align="left", max_w=944)
    p.fill_rect(40, 212, 984, 213, BLACK)
    # --- the day's stories: red region label + mixed-case headline ---
    y = 236
    pitch = 22
    for label, head in STORIES:
        draw_text(p, 150, y, label, 12, RED, align="right")
        draw_text(p, 165, y, head, 16, BLACK, align="left")
        y += pitch
    # --- footer band repeats the date ---
    p.fill_rect(40, 948, 984, 988, RED)
    draw_text(p, 512, 974, "ALL EVENTS REPORTED MONDAY 23 NOVEMBER 2026",
              13, WHITE, align="center")
    return p


def main():
    t0 = time.time()
    page = build()
    outdir = os.environ.get("MAKEFUN_OUTPUT_DIR", "out")
    os.makedirs(outdir, exist_ok=True)
    path = os.path.join(outdir, "entry.png")
    n = write_png(path, page.w, page.h, page.rgb)
    dt = time.time() - t0
    print("wrote %s %dx%d %d bytes in %.2f s" % (path, page.w, page.h, n, dt))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
