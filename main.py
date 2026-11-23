#!/usr/bin/env python3
"""news-image-20261123: draw the complete front page of Monday 23 November 2026.

A program that draws one 1024x1024 PNG newspaper front page at runtime from
story data embedded below, and writes it to $MAKEFUN_OUTPUT_DIR/entry.png.

Pure Python 3.13 standard library (os, zlib, struct, binascii). No network, no
clock, no randomness: the same program always writes the same bytes. The text
is rendered with a 5x7 bitmap font defined in this file, so the image needs no
system fonts and no image library.
"""

import binascii
import os
import struct
import zlib

W = 1024
H = 1024
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (178, 0, 0)

# 5x7 bitmap font. Each glyph is 7 rows of 5 characters; '#' is ink.
FONT = {
    'A': (".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    'B': ("####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."),
    'C': (".####", "#....", "#....", "#....", "#....", "#....", ".####"),
    'D': ("####.", "#...#", "#...#", "#...#", "#...#", "#...#", "####."),
    'E': ("#####", "#....", "#....", "####.", "#....", "#....", "#####"),
    'F': ("#####", "#....", "#....", "####.", "#....", "#....", "#...."),
    'G': (".####", "#....", "#....", "#.###", "#...#", "#...#", ".###."),
    'H': ("#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    'I': ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "#####"),
    'J': ("..###", "...#.", "...#.", "...#.", "...#.", "#..#.", ".##.."),
    'K': ("#...#", "#..#.", "#.#..", "##...", "#.#..", "#..#.", "#...#"),
    'L': ("#....", "#....", "#....", "#....", "#....", "#....", "#####"),
    'M': ("#...#", "##.##", "#.#.#", "#.#.#", "#...#", "#...#", "#...#"),
    'N': ("#...#", "##..#", "#.#.#", "#..##", "#...#", "#...#", "#...#"),
    'O': (".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    'P': ("####.", "#...#", "#...#", "####.", "#....", "#....", "#...."),
    'Q': (".###.", "#...#", "#...#", "#...#", "#.#.#", "#..#.", ".##.#"),
    'R': ("####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"),
    'S': (".####", "#....", "#....", ".###.", "....#", "....#", "####."),
    'T': ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."),
    'U': ("#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    'V': ("#...#", "#...#", "#...#", "#...#", "#...#", ".#.#.", "..#.."),
    'W': ("#...#", "#...#", "#...#", "#.#.#", "#.#.#", "##.##", "#...#"),
    'X': ("#...#", "#...#", ".#.#.", "..#..", ".#.#.", "#...#", "#...#"),
    'Y': ("#...#", "#...#", ".#.#.", "..#..", "..#..", "..#..", "..#.."),
    'Z': ("#####", "....#", "...#.", "..#..", ".#...", "#....", "#####"),
    '0': (".###.", "#...#", "#..##", "#.#.#", "##..#", "#...#", ".###."),
    '1': ("..#..", ".##..", "..#..", "..#..", "..#..", "..#..", ".###."),
    '2': (".###.", "#...#", "....#", "...#.", "..#..", ".#...", "#####"),
    '3': ("####.", "....#", "....#", ".###.", "....#", "....#", "####."),
    '4': ("...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#."),
    '5': ("#####", "#....", "####.", "....#", "....#", "#...#", ".###."),
    '6': (".###.", "#....", "#....", "####.", "#...#", "#...#", ".###."),
    '7': ("#####", "....#", "...#.", "..#..", ".#...", ".#...", ".#..."),
    '8': (".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###."),
    '9': (".###.", "#...#", "#...#", ".####", "....#", "....#", ".###."),
    ' ': (".....", ".....", ".....", ".....", ".....", ".....", "....."),
    ':': (".....", "..#..", ".....", ".....", ".....", "..#..", "....."),
    ';': (".....", "..#..", ".....", ".....", ".....", "..#..", ".#..."),
    ',': (".....", ".....", ".....", ".....", ".....", "..#..", ".#..."),
    '.': (".....", ".....", ".....", ".....", ".....", ".##..", ".##.."),
    '-': (".....", ".....", ".....", ".###.", ".....", ".....", "....."),
    "'": ("..#..", "..#..", ".#...", ".....", ".....", ".....", "....."),
    '$': ("..#..", ".####", "#.#..", ".###.", "..#.#", "####.", "..#.."),
    '%': ("##..#", "##.#.", "...#.", "..#..", ".#...", "#.##.", "#..##"),
    '&': (".##..", "#..#.", "#..#.", ".#...", "#.#.#", "#..#.", ".##.#"),
    '/': ("....#", "...#.", "...#.", "..#..", ".#...", ".#...", "#...."),
    '(': ("...#.", "..#..", ".#...", ".#...", ".#...", "..#..", "...#."),
    ')': (".#...", "..#..", "...#.", "...#.", "...#.", "..#..", ".#..."),
    '?': (".###.", "#...#", "....#", "...#.", "..#..", ".....", "..#.."),
    '!': ("..#..", "..#..", "..#..", "..#..", "..#..", ".....", "..#.."),
}


class Canvas:
    """RGB framebuffer with rectangle and bitmap-text drawing."""

    def __init__(self, w, h, bg):
        self.w = w
        self.h = h
        self.px = bytearray(bg * (w * h))

    def rect(self, x, y, w, h, color):
        # Clip to the canvas: a write past the edge must never extend the
        # framebuffer (a slice assignment past the end would grow it and
        # shift every later row).
        if w <= 0 or h <= 0:
            return
        x0 = max(0, x)
        y0 = max(0, y)
        x1 = min(self.w, x + w)
        y1 = min(self.h, y + h)
        if x1 <= x0 or y1 <= y0:
            return
        w = x1 - x0
        row = bytes(color) * w
        base = (y0 * self.w + x0) * 3
        step = self.w * 3
        for i in range(y1 - y0):
            off = base + i * step
            self.px[off:off + w * 3] = row

    def char(self, ch, x, y, scale, color):
        glyph = FONT.get(ch)
        if glyph is None:
            raise ValueError("no glyph for %r" % ch)
        for r, bits in enumerate(glyph):
            for c, bit in enumerate(bits):
                if bit == '#':
                    self.rect(x + c * scale, y + r * scale, scale, scale, color)

    def text(self, s, x, y, scale, color):
        cx = x
        for ch in s:
            self.char(ch, cx, y, scale, color)
            cx += 6 * scale

    def text_width(self, s, scale):
        return len(s) * 6 * scale - scale

    def text_centered(self, s, y, scale, color):
        x = (self.w - self.text_width(s, scale)) // 2
        self.text(s, x, y, scale, color)


def png_bytes(canvas):
    """Encode the framebuffer as a PNG (filter 0, zlib level 9)."""
    raw = bytearray()
    row_len = canvas.w * 3
    for y in range(canvas.h):
        raw.append(0)
        raw += canvas.px[y * row_len:(y + 1) * row_len]
    data = zlib.compress(bytes(raw), 9)

    def chunk(kind, payload):
        out = struct.pack(">I", len(payload)) + kind + payload
        out += struct.pack(">I", binascii.crc32(kind + payload) & 0xFFFFFFFF)
        return out

    ihdr = struct.pack(">IIBBBBB", canvas.w, canvas.h, 8, 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", data)
        + chunk(b"IEND", b"")
    )

# ---------------------------------------------------------------------------
# The day's news. 34 stories, 8 regions, every one happened or first reported
# on Monday 23 November 2026. Each list item is (region tag, headline).
# Headlines are kept to 46 characters so they fit one line at scale 3.
# ---------------------------------------------------------------------------

LEAD_HEADLINE = "TRUMP VOWS TO SINK IRANIAN VESSELS"
LEAD_DETAIL = "U.S. STRIKE ON A TANKER PUSHES HORMUZ TO THE BRINK"

STORIES = [
    ("WORLD", "COP31 COLLAPSES WITH NO DEAL, FIRST SINCE 2009"),
    ("WORLD", "US FUTURES REBOUND AFTER AI ROUT SHAKES ASIA"),
    ("WORLD", "CLAUDE CLAIMS PROOF OF RIEMANN HYPOTHESIS"),
    ("WORLD", "CHINESE HACKERS SUSPECTED IN AI CAMPUS ATTACKS"),
    ("USA", "DEMOCRATS WIN 258 HOUSE SEATS, MOST SINCE 1992"),
    ("USA", "TRUMP BACKS 10% CREDIT-CARD INTEREST CAP"),
    ("USA", "DELTA: 1,600 FLIGHTS DELAYED BY COMPUTER FAULT"),
    ("USA", "ARMY TO DETONATE IOWA EXPLOSIVES DESPITE COURT"),
    ("USA", "ICE DETENTION AT SEATTLE AIRPORT DRAWS ANGER"),
    ("USA", "METS SIGN SKUBAL FOR $450M, A RECORD DEAL"),
    ("S. AMERICA", "BOLSONARO IN INTENSIVE CARE, BOWEL BLOCKAGE"),
    ("S. AMERICA", "COLOMBIA ASKS X TO SUSPEND EX-PRESIDENT PETRO"),
    ("S. AMERICA", "HEZBOLLAH 'FINANCIER' ARRESTED IN BRAZIL"),
    ("EUROPE", "FRENCH LEADERS BOTH QUESTION UKRAINE AID"),
    ("EUROPE", "FRENCH STUDENTS PLAN NATIONWIDE PROTESTS"),
    ("EUROPE", "LAGARDE TO STEP DOWN AS ECB CHIEF IN FEB 2027"),
    ("EUROPE", "FIFA TO NAME UK AS 2035 WOMEN'S WORLD CUP HOST"),
    ("EUROPE", "MANCHESTER ARENA EVACUATED IN TEAR-GAS SCARE"),
    ("EUROPE", "AUDI PROFITS FALL AS CHINA MARKET WEAKENS"),
    ("MIDEAST", "HAWKS PRESS TRUMP ON IRAN; HE SAYS NO RUSH"),
    ("MIDEAST", "RUSSIAN FRIGATE MERKURY SINKS OFF LIBYA"),
    ("MIDEAST", "GAZA WAR LEFT 'TOXIC WASTELAND', EXPERTS FIND"),
    ("MIDEAST", "SETTLERS TORCH 12 PALESTINIAN VEHICLES"),
    ("AFRICA", "SUDAN: DRONES HIT KHARTOUM, UN SITE DAMAGED"),
    ("AFRICA", "EGYPT REJECTS RIVAL GOVERNMENT IN SUDAN"),
    ("E. ASIA", "SOUTH KOREA EXPORTS PASS $1 TRILLION, A FIRST"),
    ("E. ASIA", "KOSPI PLUNGES 5% IN AI ROUT; SEOUL ACTS"),
    ("E. ASIA", "TAIWAN STOCKS SWING 1,578 POINTS; TSMC UP 2%"),
    ("E. ASIA", "SOUTH KOREA MINISTER QUITS OVER EXAM-CHEATING"),
    ("E. ASIA", "MONGOLIA PRESIDENT RESIGNS, PARLIAMENT AGREES"),
    ("S.E. ASIA", "MAYON ERUPTION RAISES FEARS OF BIGGER BLAST"),
    ("S.E. ASIA", "INDONESIA: 50 MISSING AFTER FACTORY FIRE"),
    ("S. ASIA", "NEPAL PM BALEN SHAH VISITS INDIA ON FIRST TRIP"),
]

MASTHEAD_DATE = "MONDAY 23 NOVEMBER 2026"
MASTHEAD_SUB = "34 STORIES - 8 REGIONS - THE WORLD IN ONE DAY"
FOOTER = "ALL EVENTS REPORTED MONDAY 23 NOVEMBER 2026"


def draw():
    c = Canvas(W, H, WHITE)

    # Masthead: the date, big and centered, then the story count.
    c.text_centered(MASTHEAD_DATE, 16, 6, BLACK)
    c.text_centered(MASTHEAD_SUB, 70, 2, BLACK)
    c.rect(28, 94, W - 56, 3, BLACK)
    c.rect(28, 100, W - 56, 2, RED)

    # Lead story.
    c.text(LEAD_HEADLINE, 28, 116, 4, BLACK)
    c.text(LEAD_DETAIL, 28, 150, 2, RED)
    c.rect(28, 172, W - 56, 1, BLACK)

    # The story list: red region tag right-aligned in its column, then the
    # headline in black. One line per story, 24 px leading. Every headline
    # must fit the 46-character budget (166 + 46*18 = 994 <= 996); fail
    # loudly here rather than drawing past the edge.
    for _tag, headline in STORIES:
        if len(headline) > 46:
            raise ValueError("headline too long: %r" % headline)
    y = 184
    for tag, headline in STORIES:
        tag_w = c.text_width(tag, 2)
        c.text(tag, 150 - tag_w, y, 2, RED)
        c.text(headline, 166, y, 3, BLACK)
        y += 24

    # Footer.
    c.text_centered(FOOTER, 988, 2, BLACK)
    return c


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR")
    if not out_dir:
        raise SystemExit("MAKEFUN_OUTPUT_DIR is not set")
    canvas = draw()
    data = png_bytes(canvas)
    path = os.path.join(out_dir, "entry.png")
    with open(path, "wb") as f:
        f.write(data)


if __name__ == "__main__":
    main()
