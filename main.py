#!/usr/bin/env python3
"""18 November 2026 in one image.

A pure-Python (standard library only) picture generator. It draws a
newspaper front page: a masthead naming the day, six panels in a 3 by 2
grid, one per story of Wednesday 18 November 2026, each with a drawn
scene, a headline and a caption, plus a ticker of three more stories.
No network, no clock, no randomness: the same bytes come out on every
run. Writes $MAKEFUN_OUTPUT_DIR/entry.png (or /output/entry.png).
"""

import binascii
import os
import struct
import zlib

W, H = 1024, 1024

PAPER = (246, 240, 220)   # cream newsprint
INK = (24, 24, 24)        # near-black ink
RED = (172, 32, 24)       # masthead red
GREY = (96, 92, 82)
WHITE = (255, 255, 255)
DARKRED = (138, 31, 26)   # caption red

# ------------------------------------------------------------------ font
# A 5x7 bitmap font written for this entry. Each glyph is 7 rows of 5
# bits; bit 4 (value 16) is the leftmost pixel. Capitals only.
FONT = {
    'A': (0x0E, 0x11, 0x11, 0x1F, 0x11, 0x11, 0x11),
    'B': (0x1E, 0x11, 0x11, 0x1E, 0x11, 0x11, 0x1E),
    'C': (0x0E, 0x11, 0x10, 0x10, 0x10, 0x11, 0x0E),
    'D': (0x1E, 0x11, 0x11, 0x11, 0x11, 0x11, 0x1E),
    'E': (0x1F, 0x10, 0x10, 0x1E, 0x10, 0x10, 0x1F),
    'F': (0x1F, 0x10, 0x10, 0x1E, 0x10, 0x10, 0x10),
    'G': (0x0E, 0x11, 0x10, 0x17, 0x11, 0x11, 0x0F),
    'H': (0x11, 0x11, 0x11, 0x1F, 0x11, 0x11, 0x11),
    'I': (0x0E, 0x04, 0x04, 0x04, 0x04, 0x04, 0x0E),
    'J': (0x07, 0x02, 0x02, 0x02, 0x02, 0x12, 0x0C),
    'K': (0x11, 0x12, 0x14, 0x18, 0x14, 0x12, 0x11),
    'L': (0x10, 0x10, 0x10, 0x10, 0x10, 0x10, 0x1F),
    'M': (0x11, 0x1B, 0x15, 0x15, 0x11, 0x11, 0x11),
    'N': (0x11, 0x19, 0x15, 0x13, 0x11, 0x11, 0x11),
    'O': (0x0E, 0x11, 0x11, 0x11, 0x11, 0x11, 0x0E),
    'P': (0x1E, 0x11, 0x11, 0x1E, 0x10, 0x10, 0x10),
    'Q': (0x0E, 0x11, 0x11, 0x11, 0x15, 0x12, 0x0D),
    'R': (0x1E, 0x11, 0x11, 0x1E, 0x14, 0x12, 0x11),
    'S': (0x0F, 0x10, 0x10, 0x0E, 0x01, 0x01, 0x1E),
    'T': (0x1F, 0x04, 0x04, 0x04, 0x04, 0x04, 0x04),
    'U': (0x11, 0x11, 0x11, 0x11, 0x11, 0x11, 0x0E),
    'V': (0x11, 0x11, 0x11, 0x11, 0x11, 0x0A, 0x04),
    'W': (0x11, 0x11, 0x11, 0x15, 0x15, 0x1B, 0x11),
    'X': (0x11, 0x11, 0x0A, 0x04, 0x0A, 0x11, 0x11),
    'Y': (0x11, 0x11, 0x0A, 0x04, 0x04, 0x04, 0x04),
    'Z': (0x1F, 0x01, 0x02, 0x04, 0x08, 0x10, 0x1F),
    '0': (0x0E, 0x11, 0x13, 0x15, 0x19, 0x11, 0x0E),
    '1': (0x04, 0x0C, 0x04, 0x04, 0x04, 0x04, 0x0E),
    '2': (0x0E, 0x11, 0x01, 0x06, 0x08, 0x10, 0x1F),
    '3': (0x1E, 0x01, 0x01, 0x0E, 0x01, 0x01, 0x1E),
    '4': (0x02, 0x06, 0x0A, 0x12, 0x1F, 0x02, 0x02),
    '5': (0x1F, 0x10, 0x1E, 0x01, 0x01, 0x11, 0x0E),
    '6': (0x0E, 0x10, 0x10, 0x1E, 0x11, 0x11, 0x0E),
    '7': (0x1F, 0x01, 0x02, 0x04, 0x08, 0x08, 0x08),
    '8': (0x0E, 0x11, 0x11, 0x0E, 0x11, 0x11, 0x0E),
    '9': (0x0E, 0x11, 0x11, 0x0F, 0x01, 0x01, 0x0E),
    ' ': (0, 0, 0, 0, 0, 0, 0),
    '.': (0, 0, 0, 0, 0, 0x0C, 0x0C),
    ',': (0, 0, 0, 0, 0x0C, 0x04, 0x08),
    ':': (0, 0x0C, 0x0C, 0, 0x0C, 0x0C, 0),
    ';': (0, 0x0C, 0x0C, 0, 0x0C, 0x04, 0x08),
    '!': (0x04, 0x04, 0x04, 0x04, 0x04, 0, 0x04),
    '?': (0x0E, 0x11, 0x01, 0x06, 0x04, 0, 0x04),
    "'": (0x04, 0x04, 0x08, 0, 0, 0, 0),
    '-': (0, 0, 0, 0x0E, 0, 0, 0),
    '$': (0x04, 0x0F, 0x14, 0x0E, 0x05, 0x1E, 0x04),
    '%': (0x19, 0x1A, 0x02, 0x04, 0x08, 0x0B, 0x13),
    '(': (0x02, 0x04, 0x08, 0x08, 0x08, 0x04, 0x02),
    ')': (0x08, 0x04, 0x02, 0x02, 0x02, 0x04, 0x08),
    '/': (0x01, 0x02, 0x02, 0x04, 0x08, 0x08, 0x10),
    '&': (0x0C, 0x12, 0x14, 0x08, 0x15, 0x12, 0x0D),
    '+': (0, 0x04, 0x04, 0x1F, 0x04, 0x04, 0),
    '=': (0, 0, 0x1F, 0, 0x1F, 0, 0),
    '"': (0x0A, 0x0A, 0, 0, 0, 0, 0),
}

# ------------------------------------------------------------------ canvas
buf = bytearray(W * H * 3)


def setpx(x, y, c):
    if 0 <= x < W and 0 <= y < H:
        i = (y * W + x) * 3
        buf[i], buf[i + 1], buf[i + 2] = c


def fill(x, y, w, h, c):
    x0, y0 = max(x, 0), max(y, 0)
    x1, y1 = min(x + w, W), min(y + h, H)
    for yy in range(y0, y1):
        i = (yy * W + x0) * 3
        for xx in range(x0, x1):
            buf[i], buf[i + 1], buf[i + 2] = c
            i += 3


def hline(x0, x1, y, c):
    if x1 < x0:
        x0, x1 = x1, x0
    fill(x0, y, x1 - x0 + 1, 1, c)


def vline(x, y0, y1, c):
    if y1 < y0:
        y0, y1 = y1, y0
    fill(x, y0, 1, y1 - y0 + 1, c)


def seg(x0, y0, x1, y1, c):
    # Bresenham line.
    dx, dy = abs(x1 - x0), abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx - dy
    while True:
        setpx(x0, y0, c)
        if x0 == x1 and y0 == y1:
            return
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x0 += sx
        if e2 < dx:
            err += dx
            y0 += sy


def disc(cx, cy, r, c):
    for dy in range(-r, r + 1):
        dx = int((r * r - dy * dy) ** 0.5)
        hline(cx - dx, cx + dx, cy + dy, c)


def poly(pts, c):
    # Scanline fill of a simple polygon.
    ys = [p[1] for p in pts]
    for y in range(max(min(ys), 0), min(max(ys), H - 1) + 1):
        xs = []
        n = len(pts)
        for i in range(n):
            x0, y0 = pts[i]
            x1, y1 = pts[(i + 1) % n]
            if (y0 <= y < y1) or (y1 <= y < y0):
                xs.append(x0 + (y - y0) * (x1 - x0) // (y1 - y0))
        xs.sort()
        for i in range(0, len(xs) - 1, 2):
            hline(xs[i], xs[i + 1], y, c)


def draw_text(s, x, y, sc, c):
    for ch in s:
        g = FONT.get(ch, FONT[' '])
        for r in range(7):
            row = g[r]
            for col in range(5):
                if row & (16 >> col):
                    fill(x + col * sc, y + r * sc, sc, sc, c)
        x += 6 * sc


def text_w(s, sc):
    return len(s) * 6 * sc - sc if s else 0


def centre_text(s, cx, y, sc, c):
    draw_text(s, cx - text_w(s, sc) // 2, y, sc, c)


# ------------------------------------------------------------------ png
def chunk(typ, data):
    return (struct.pack('>I', len(data)) + typ + data +
            struct.pack('>I', binascii.crc32(typ + data) & 0xFFFFFFFF))


def png_bytes():
    ihdr = struct.pack('>IIBBBBB', W, H, 8, 2, 0, 0, 0)
    raw = bytearray()
    for y in range(H):
        raw.append(0)
        raw += buf[y * W * 3:(y + 1) * W * 3]
    idat = zlib.compress(bytes(raw), 9)
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', ihdr) +
            chunk(b'IDAT', idat) + chunk(b'IEND', b''))

# ------------------------------------------------------------------ scenes
# Every scene draws inside a box (sx, sy, 312, 270). Flat colours, on
# purpose: a clean newspaper illustration.

SW, SH = 312, 270


def scene_gulf(sx, sy):
    fill(sx, sy, SW, 108, (206, 221, 231))          # hazy sky
    disc(sx + 258, sy + 38, 22, (240, 206, 122))   # low sun
    fill(sx, sy + 108, SW, 162, (36, 84, 130))     # the Gulf
    for wy in (sy + 150, sy + 190, sy + 232):
        for wx in range(sx + 14, sx + SW, 52):
            hline(wx, wx + 26, wy, (140, 182, 214))
    # Qeshm Island, right, with smoke rising from the strike.
    poly([(sx + 236, sy + 108), (sx + 262, sy + 78), (sx + 292, sy + 92),
          (sx + 312, sy + 108)], (96, 84, 62))
    disc(sx + 262, sy + 66, 11, (150, 140, 128))
    disc(sx + 276, sy + 52, 8, (170, 160, 148))
    disc(sx + 262, sy + 84, 6, (240, 120, 30))
    # Warship, centre-left.
    poly([(sx + 34, sy + 168), (sx + 170, sy + 168), (sx + 158, sy + 196),
          (sx + 48, sy + 196)], (58, 62, 66))
    fill(sx + 78, sy + 140, 62, 28, (58, 62, 66))
    vline(sx + 108, sy + 112, sy + 140, (40, 42, 46))
    fill(sx + 112, sy + 112, 26, 12, (178, 34, 52))
    # Two jets overhead, contrails behind them.
    for jx, jy in ((sx + 60, sy + 34), (sx + 130, sy + 18)):
        seg(jx - 46, jy + 12, jx - 6, jy + 2, WHITE)
        poly([(jx, jy), (jx + 26, jy + 4), (jx, jy + 8)], (30, 32, 38))
        poly([(jx + 8, jy + 4), (jx + 18, jy - 6), (jx + 22, jy + 4)],
             (30, 32, 38))


def scene_shenzhen(sx, sy):
    bands = [(64, 40, 96), (110, 52, 110), (176, 72, 112),
             (228, 108, 84), (246, 158, 88), (252, 200, 118)]
    for i, c in enumerate(bands):
        fill(sx, sy + i * 45, SW, 45, c)
    disc(sx + 156, sy + 80, 30, (255, 224, 150))    # dusk sun
    # Skyline silhouettes.
    for bx, bh in ((8, 62), (52, 96), (104, 74), (196, 88), (240, 64),
                   (280, 104)):
        fill(sx + bx, sy + SH - bh, 28, bh, (26, 20, 40))
    for wx, wy in ((60, 200), (72, 216), (112, 190), (204, 206),
                   (248, 220), (288, 180)):
        fill(sx + wx, sy + wy, 5, 5, (255, 210, 110))
    # APEC ribbon across the middle.
    fill(sx + 20, sy + 118, 272, 40, (178, 34, 52))
    centre_text("APEC", sx + 156, sy + 124, 4, WHITE)
    # Small flags on two shorter towers, clear of the ribbon.
    fill(sx + 20, sy + 182, 4, 26, (240, 240, 240))
    fill(sx + 24, sy + 182, 22, 12, (222, 41, 16))
    fill(sx + 252, sy + 180, 4, 26, (240, 240, 240))
    fill(sx + 256, sy + 180, 22, 5, WHITE)
    fill(sx + 256, sy + 185, 22, 4, (30, 80, 180))
    fill(sx + 256, sy + 189, 22, 4, (200, 30, 30))


def scene_alaska(sx, sy):
    fill(sx, sy, SW, 150, (168, 196, 220))          # cold sky
    s = 777
    for _ in range(26):                             # fixed-seed stars
        s = (s * 1103515245 + 12345) & 0x7FFFFFFF
        px = sx + 8 + s % 296
        s = (s * 1103515245 + 12345) & 0x7FFFFFFF
        py = sy + 6 + s % 90
        setpx(px, py, WHITE)
    # Snowy ranges.
    poly([(sx, sy + 150), (sx + 80, sy + 70), (sx + 160, sy + 150)],
         (120, 140, 168))
    poly([(sx + 60, sy + 150), (sx + 80, sy + 70), (sx + 100, sy + 150)],
         WHITE)
    poly([(sx + 150, sy + 150), (sx + 240, sy + 58), (sx + 312, sy + 150)],
         (96, 118, 148))
    poly([(sx + 222, sy + 150), (sx + 240, sy + 58), (sx + 258, sy + 150)],
         WHITE)
    fill(sx, sy + 150, SW, 120, (238, 242, 246))    # snowfield
    # Ballot box with a checked paper.
    fill(sx + 96, sy + 176, 120, 62, (28, 44, 92))
    fill(sx + 108, sy + 164, 96, 12, (28, 44, 92))
    fill(sx + 128, sy + 158, 36, 6, INK)
    fill(sx + 118, sy + 118, 56, 44, WHITE)
    seg(sx + 126, sy + 140, sx + 140, sy + 154, (178, 34, 52))
    seg(sx + 140, sy + 154, sx + 166, sy + 126, (178, 34, 52))
    seg(sx + 128, sy + 142, sx + 142, sy + 156, (178, 34, 52))
    seg(sx + 142, sy + 156, sx + 168, sy + 128, (178, 34, 52))
    draw_text("56-44", sx + 116, sy + 208, 3, WHITE)


def scene_nvidia(sx, sy):
    fill(sx, sy, SW, SH, (12, 34, 20))             # dark board
    for ty in (sy + 60, sy + 130, sy + 200):       # circuit traces
        hline(sx + 10, sx + 300, ty, (28, 90, 52))
    for tx in (sx + 60, sx + 150, sx + 240):
        vline(tx, sy + 10, sy + 260, (28, 90, 52))
    draw_text("$115.8B", sx + 16, sy + 16, 4, WHITE)
    # Rising bars.
    bars = [40, 64, 52, 88, 72, 100]
    bx = sx + 26
    for hgt in bars:
        fill(bx, sy + 246 - hgt, 30, hgt, (46, 190, 100))
        bx += 46
    # The chip, top right, clear of the bars.
    fill(sx + 230, sy + 56, 58, 58, (20, 60, 34))
    fill(sx + 243, sy + 69, 32, 32, (118, 185, 0))
    for px0 in range(sx + 236, sx + 282, 14):
        fill(px0, sy + 48, 6, 8, (180, 190, 180))
        fill(px0, sy + 114, 6, 8, (180, 190, 180))
    for py0 in range(sy + 62, sy + 106, 14):
        fill(sx + 222, py0, 8, 6, (180, 190, 180))
        fill(sx + 288, py0, 8, 6, (180, 190, 180))


def scene_anthropic(sx, sy):
    fill(sx, sy, SW, SH, (14, 32, 54))             # dark navy
    for gy in range(sy + 30, sy + 250, 36):
        hline(sx + 12, sx + 300, gy, (30, 58, 88))
    draw_text("$83", sx + 16, sy + 14, 7, WHITE)
    draw_text("ANT", sx + 236, sy + 30, 4, (80, 220, 140))
    # Rising candlesticks.
    bars = [(34, 14), (44, 10), (38, 16), (56, 12), (50, 14), (66, 10),
            (60, 14), (76, 12)]
    bx = sx + 22
    tops = []
    for hgt, wick in bars:
        base = sy + 250
        up = (bx // 46) % 2 == 0
        c = (46, 190, 100) if up else (210, 70, 60)
        vline(bx + 11, base - hgt - wick, base + 4, (150, 170, 150))
        fill(bx, base - hgt, 22, hgt, c)
        tops.append((bx + 11, base - hgt - 6))
        bx += 36
    for i in range(len(tops) - 1):
        seg(tops[i][0], tops[i][1], tops[i + 1][0], tops[i + 1][1], WHITE)
    ex, ey = tops[-1]
    poly([(ex, ey - 16), (ex + 18, ey + 2), (ex - 2, ey + 2)], WHITE)


def scene_ebola(sx, sy):
    fill(sx, sy, SW, SH, (232, 222, 198))          # pale map paper
    # Africa, rough outline.
    africa = [(sx + 148, sy + 22), (sx + 178, sy + 26), (sx + 208, sy + 44),
              (sx + 238, sy + 66), (sx + 262, sy + 96), (sx + 250, sy + 118),
              (sx + 232, sy + 132), (sx + 214, sy + 168), (sx + 196, sy + 210),
              (sx + 178, sy + 244), (sx + 162, sy + 226), (sx + 148, sy + 190),
              (sx + 128, sy + 168), (sx + 104, sy + 150), (sx + 84, sy + 118),
              (sx + 66, sy + 88), (sx + 78, sy + 58), (sx + 104, sy + 34),
              (sx + 126, sy + 24)]
    poly(africa, (196, 164, 118))
    # The outbreak zone, central Africa.
    disc(sx + 158, sy + 138, 16, (178, 34, 52))
    disc(sx + 158, sy + 138, 9, (222, 41, 16))
    # Spread dots.
    for dx, dy in ((120, 100), (186, 112), (140, 168), (196, 168),
                   (172, 196)):
        disc(sx + dx, sy + dy, 4, (178, 34, 52))
    # Medical cross badge, top right.
    disc(sx + 268, sy + 44, 26, WHITE)
    fill(sx + 262, sy + 28, 12, 32, (178, 34, 52))
    fill(sx + 252, sy + 38, 32, 12, (178, 34, 52))
    draw_text("11,000", sx + 30, sy + 236, 3, DARKRED)

# ------------------------------------------------------------------ compose
PANELS = [
    ("THE GULF", (150, 60, 30), scene_gulf,
     "US STRIKES IRAN,", "IRAN HITS BACK",
     "US JETS HIT QESHM ISLAND", "IRAN DRONES AT US BASES"),
    ("SHENZHEN", (40, 70, 140), scene_shenzhen,
     "XI MEETS PUTIN", "TRUMP ARRIVES",
     "APEC SUMMIT IN SHENZHEN", "TRILATERAL ON THURSDAY"),
    ("ALASKA", (30, 110, 140), scene_alaska,
     "PELTOLA WINS", "SENATE 56-44",
     "DEMOCRATS FLIP ALASKA", "LAST RACE CALLED BY AP"),
    ("TECH", (20, 120, 60), scene_nvidia,
     "NVIDIA DOUBLES", "$115.8 BILLION",
     "REVENUE UP 103 PERCENT", "HUANG NOT COMING BACK"),
    ("MARKETS", (20, 60, 120), scene_anthropic,
     "ANTHROPIC IPO", "PRICED AT $83",
     "RECORD $81.3 BILLION", "VALUED AT $1.5 TRILLION"),
    ("HEALTH", (160, 30, 60), scene_ebola,
     "EBOLA PASSES", "11,000 CASES",
     "SECOND LARGEST ON RECORD", "WHO KEEPS EMERGENCY ON"),
]

TICKER = ("ALSO: CYCLONE AKVAN NEARS INDIA - INDIA-JAPAN TALKS - "
          "ETHIOPIA-ERITREA TENSIONS")


def panel(px, py, kick, kc, draw, l1, l2, c1, c2):
    fill(px, py, 324, 3, INK)
    fill(px, py + 416, 324, 3, INK)
    fill(px, py, 3, 419, INK)
    fill(px + 321, py, 3, 419, INK)
    draw(px + 6, py + 6)
    # Kicker tab over the scene's top-left corner.
    tab_w = text_w(kick, 2) + 20
    fill(px + 6, py + 6, tab_w, 24, kc)
    draw_text(kick, px + 16, py + 12, 2, WHITE)
    # Headlines, then a rule, then the caption.
    draw_text(l1, px + 12, py + 288, 3, INK)
    draw_text(l2, px + 12, py + 318, 3, INK)
    hline(px + 12, px + 312, py + 354, INK)
    draw_text(c1, px + 12, py + 366, 2, DARKRED)
    draw_text(c2, px + 12, py + 388, 2, DARKRED)


def compose():
    fill(0, 0, W, H, PAPER)
    # Masthead.
    centre_text("ONE DAY ON EARTH", 512, 16, 6, INK)
    centre_text("WEDNESDAY 18 NOVEMBER 2026", 512, 68, 4, RED)
    hline(16, 1007, 104, INK)
    hline(16, 1007, 107, RED)
    centre_text("SIX STORIES FROM AROUND THE GLOBE", 512, 116, 2, GREY)
    # Panels: 3 columns x 2 rows.
    for i, (kick, kc, draw, l1, l2, c1, c2) in enumerate(PANELS):
        px = 16 + (i % 3) * 334
        py = 140 + (i // 3) * 429
        panel(px, py, kick, kc, draw, l1, l2, c1, c2)
    # Ticker of three more stories.
    hline(16, 1007, 996, INK)
    centre_text(TICKER, 512, 1004, 2, INK)


def main():
    out = os.environ.get("MAKEFUN_OUTPUT_DIR") or "/output"
    os.makedirs(out, exist_ok=True)
    compose()
    with open(os.path.join(out, "entry.png"), "wb") as f:
        f.write(png_bytes())


if __name__ == "__main__":
    main()
