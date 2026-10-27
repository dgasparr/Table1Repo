"""Render the animated capture-rules cartoon -> assets/capture_rules.png (APNG).

    python tools/make_capture_rules.py

One scene per rule, each animating from a good shot to the ways it goes wrong,
then a do/don't summary card. app.py shows the file with st.image(), which
passes RGBA PNG bytes through untouched, so browsers play the animation.
"""
from __future__ import annotations

import math
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

OUT = Path(__file__).resolve().parent.parent / "assets" / "capture_rules.png"

W = H = 640
AREA_TOP, AREA_BOT = 84, 548          # cartoon area between header and footer
HOLD_MS, MOVE_FRAMES, MOVE_MS = 2200, 10, 70
SUMMARY_MS = 7000

BG = (255, 248, 236)
INK = (43, 45, 66)
GOOD = (46, 158, 91)
BAD = (215, 38, 61)
NEUTRAL = (200, 196, 188)
WALL = (233, 220, 201)
WALL_DARK = (196, 178, 152)
FLOOR = (178, 150, 120)
PAPER = (255, 255, 255)
TAPE = (240, 205, 120, 200)
LINE = (255, 45, 85)
SCREEN = (60, 64, 84)


def font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    for name in (("arialbd.ttf", "DejaVuSans-Bold.ttf") if bold else ("arial.ttf", "DejaVuSans.ttf")):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            pass
    return ImageFont.load_default(size)


def fit_font(text: str, max_w: int, size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    while size > 12 and font(size, bold).getlength(text) > max_w:
        size -= 1
    return font(size, bold)


def smooth(t: float) -> float:
    return t * t * (3 - 2 * t)


def lerp(a, b, t):
    return a + (b - a) * t


# ----------------------------------------------------------------------------
# Shared pieces
# ----------------------------------------------------------------------------
_DICT = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
_BITS = [cv2.aruco.generateImageMarker(_DICT, i, 6) < 128 for i in range(4)]  # True = black
_ORIGINS = [(0, 0), (4, 0), (0, 4), (4, 4)]   # inches; IDs 0 TL, 1 TR, 2 BL, 3 BR
PAPER_LO, PAPER_HI = -0.75, 7.75               # paper extends 3/4" past the 7" board


def quad_map(quad):
    """Bilinear map from board inches to pixels for a paper quad (TL, TR, BR, BL)."""
    (x0, y0), (x1, y1), (x2, y2), (x3, y3) = quad

    def f(ix, iy):
        u = (ix - PAPER_LO) / (PAPER_HI - PAPER_LO)
        v = (iy - PAPER_LO) / (PAPER_HI - PAPER_LO)
        tx, ty = lerp(x0, x1, u), lerp(y0, y1, u)
        bx, by = lerp(x3, x2, u), lerp(y3, y2, u)
        return lerp(tx, bx, v), lerp(ty, by, v)

    return f


def draw_board(d: ImageDraw.ImageDraw, f, outline: bool = True) -> None:
    """Draw the paper and the 2x2 ArUco board through the mapping f(inch_x, inch_y)."""
    n = 12
    edge = []
    for k in range(n):
        edge.append(f(lerp(PAPER_LO, PAPER_HI, k / n), PAPER_LO))
    for k in range(n):
        edge.append(f(PAPER_HI, lerp(PAPER_LO, PAPER_HI, k / n)))
    for k in range(n):
        edge.append(f(lerp(PAPER_HI, PAPER_LO, k / n), PAPER_HI))
    for k in range(n):
        edge.append(f(PAPER_LO, lerp(PAPER_HI, PAPER_LO, k / n)))
    d.polygon(edge, fill=PAPER, outline=(150, 150, 150) if outline else None)
    for bits, (ox, oy) in zip(_BITS, _ORIGINS):
        for r in range(6):
            for c in range(6):
                if bits[r, c]:
                    x, y = ox + c * 0.5, oy + r * 0.5
                    d.polygon([f(x, y), f(x + 0.5, y), f(x + 0.5, y + 0.5), f(x, y + 0.5)], fill=(20, 20, 20))


def square_quad(cx, cy, size):
    h = size / 2
    return [(cx - h, cy - h), (cx + h, cy - h), (cx + h, cy + h), (cx - h, cy + h)]


def check_icon(d, cx, cy, r, color=GOOD):
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=color)
    d.line([(cx - r * .5, cy), (cx - r * .12, cy + r * .4), (cx + r * .5, cy - r * .38)],
           fill="white", width=max(3, int(r * .28)), joint="curve")


def cross_icon(d, cx, cy, r, color=BAD):
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=color)
    k, w = r * .42, max(3, int(r * .28))
    d.line([(cx - k, cy - k), (cx + k, cy + k)], fill="white", width=w)
    d.line([(cx - k, cy + k), (cx + k, cy - k)], fill="white", width=w)


def label(d, xy, text, size=20, fg=INK, bg=(255, 255, 255, 235), anchor="mm"):
    f = font(size)
    x0, y0, x1, y1 = d.textbbox(xy, text, font=f, anchor=anchor)
    d.rounded_rectangle([x0 - 8, y0 - 5, x1 + 8, y1 + 5], radius=8, fill=bg)
    d.text(xy, text, font=f, fill=fg, anchor=anchor)


def phone(d, box):
    """Phone body; returns the screen box."""
    x0, y0, x1, y1 = box
    d.rounded_rectangle(box, radius=28, fill=INK)
    d.rounded_rectangle([(x0 + x1) / 2 - 30, y0 + 8, (x0 + x1) / 2 + 30, y0 + 16], radius=4, fill=(20, 20, 30))
    return (x0 + 12, y0 + 26, x1 - 12, y1 - 26)


def screen_layer(screen_box, bg=WALL):
    x0, y0, x1, y1 = screen_box
    img = Image.new("RGB", (int(x1 - x0), int(y1 - y0)), bg)
    return img, ImageDraw.Draw(img, "RGBA")


def person_side(d, x, floor_y):
    """Side view, facing right, holding a phone at eye level."""
    w = 6
    d.ellipse([x - 15, floor_y - 134, x + 15, floor_y - 104], fill=(250, 214, 170), outline=INK, width=3)
    d.ellipse([x + 5, floor_y - 123, x + 9, floor_y - 119], fill=INK)
    d.line([(x, floor_y - 104), (x, floor_y - 48)], fill=INK, width=w)
    d.line([(x, floor_y - 48), (x - 13, floor_y)], fill=INK, width=w)
    d.line([(x, floor_y - 48), (x + 13, floor_y)], fill=INK, width=w)
    d.line([(x, floor_y - 92), (x + 22, floor_y - 108)], fill=INK, width=w, joint="curve")
    d.rounded_rectangle([x + 22, floor_y - 122, x + 30, floor_y - 98], radius=2, fill=SCREEN)


# ----------------------------------------------------------------------------
# Scenes: each is (title, render(p) -> (Image, verdict | None), stops)
# A verdict is (ok: bool, text). Stops are p values to hold on.
# ----------------------------------------------------------------------------
def canvas():
    img = Image.new("RGB", (W, H), BG)
    return img, ImageDraw.Draw(img, "RGBA")


def scene_distance(p):
    ft = p
    img, d = canvas()
    floor = 500
    wall_x = 596
    d.rectangle([wall_x, AREA_TOP + 12, W, floor], fill=WALL, outline=WALL_DARK, width=3)
    d.rectangle([0, floor, W, AREA_BOT], fill=(236, 226, 210))
    d.line([(0, floor), (W, floor)], fill=INK, width=3)
    d.rectangle([wall_x - 7, 330, wall_x, 392], fill=INK)
    label(d, (wall_x - 44, 306), "board", 20)

    px = 30                                   # pixels per foot
    face = wall_x - 7
    for a, b, col in ((0, 3, BAD), (3, 10, GOOD), (10, 16.5, BAD)):
        d.rectangle([face - b * px, floor + 3, face - a * px, floor + 13], fill=col + (200,))
    for v in (0, 3, 10, 15):
        x = face - v * px
        d.line([(x, floor + 3), (x, floor + 18)], fill=INK, width=2)
        d.text((x, floor + 20), f"{v} ft", font=font(19), fill=INK, anchor="mt")

    phone_x = face - ft * px
    person_side(d, phone_x - 30, floor)
    y = 466
    d.line([(phone_x, y), (face, y)], fill=INK, width=2)
    for x, s in ((phone_x, 1), (face, -1)):
        d.polygon([(x, y), (x + 9 * s, y - 5), (x + 9 * s, y + 5)], fill=INK)
    label(d, ((phone_x + face) / 2, y - 18), f"{ft:.0f} ft", 22)

    # Inset: what the phone sees.
    scr = phone(d, (40, 96, 200, 300))
    layer, ld = screen_layer(scr)
    size = 150 * 0.42 * 6 / max(ft, 0.5)
    draw_board(ld, quad_map(square_quad(layer.width / 2, layer.height / 2, size)))
    img.paste(layer, (int(scr[0]), int(scr[1])))
    d.text((120, 310), "phone view", font=font(20), fill=INK, anchor="mt")

    if abs(ft - round(ft)) > 1e-6:
        return img, None
    if ft < 3:
        return img, (False, "Too close: board won't fit")
    if ft > 10:
        return img, (False, "Too far: markers too small")
    return img, (True, "3–10 ft away: just right")


def scene_angle(p):
    theta = p
    img, d = canvas()
    cx, cy, R = 320, 124, 420
    wedge = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    wd = ImageDraw.Draw(wedge)
    wd.pieslice([cx - R, cy - R, cx + R, cy + R], 45, 135, fill=GOOD + (70,))
    wd.pieslice([cx - R, cy - R, cx + R, cy + R], 0, 45, fill=BAD + (55,))
    wd.pieslice([cx - R, cy - R, cx + R, cy + R], 135, 180, fill=BAD + (55,))
    for a in (45, 135):
        r = math.radians(a)
        wd.line([(cx, cy), (cx + R * math.cos(r), cy + R * math.sin(r))], fill=INK + (120,), width=2)
    img.paste(wedge, (0, 0), wedge)
    d.rectangle([20, cy - 16, W - 20, cy - 4], fill=WALL_DARK)
    d.text((24, cy - 44), "wall (seen from above)", font=font(20), fill=INK)
    d.rectangle([cx - 36, cy - 6, cx + 36, cy + 2], fill=INK)
    label(d, (cx, cy + 26), "board", 20)
    label(d, (cx + 150, cy + 150), "45°", 22, fg=GOOD)
    label(d, (cx - 150, cy + 150), "45°", 22, fg=GOOD)
    label(d, (92, cy + 46), "too steep", 22, fg=BAD)
    label(d, (W - 92, cy + 46), "too steep", 22, fg=BAD)

    phi = math.radians(90 + theta)
    pr = 290
    hx, hy = cx + pr * math.cos(phi), cy + pr * math.sin(phi)
    ux, uy = (cx - hx) / pr, (cy - hy) / pr
    ph = (hx + 30 * ux, hy + 30 * uy)
    d.polygon([ph, (cx - 36, cy), (cx + 36, cy)], fill=(255, 255, 255, 90))
    d.line([ph, (cx, cy)], fill=INK + (150,), width=2)
    d.ellipse([hx - 30 * uy - 12, hy + 30 * ux - 12, hx - 30 * uy + 12, hy + 30 * ux + 12], fill=(90, 110, 160))
    d.ellipse([hx + 30 * uy - 12, hy - 30 * ux - 12, hx + 30 * uy + 12, hy - 30 * ux + 12], fill=(90, 110, 160))
    d.ellipse([hx - 19, hy - 19, hx + 19, hy + 19], fill=(250, 214, 170), outline=INK, width=3)
    d.ellipse([ph[0] - 7, ph[1] - 7, ph[0] + 7, ph[1] + 7], fill=SCREEN)
    label(d, (hx, hy + 40), f"{theta:.0f}°", 22)

    # Inset: the board foreshortens as the angle grows.
    box = (452, 352, 620, 540)
    d.rounded_rectangle(box, radius=14, fill=WALL, outline=INK, width=3)
    d.text(((box[0] + box[2]) / 2, box[1] - 6), "phone view", font=font(20), fill=INK, anchor="mb")
    bx, by, s = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2, 104
    t = math.radians(theta)
    hw = s / 2 * math.cos(t)
    near, far = s / 2 * (1 + 0.35 * math.sin(t)), s / 2 * (1 - 0.35 * math.sin(t))
    draw_board(d, quad_map([(bx - hw, by - near), (bx + hw, by - far), (bx + hw, by + far), (bx - hw, by + near)]))

    if abs(theta - round(theta)) > 1e-6 or round(theta) % 5:
        return img, None
    if theta > 45:
        return img, (False, "Steep angle: markers squash")
    if theta == 0:
        return img, (True, "Straight-on is best")
    return img, (True, "Within 45° is OK")


def scene_frame(p):
    img, d = canvas()
    scr = phone(d, (175, 92, 465, 546))
    layer, ld = screen_layer(scr)
    lw, lh = layer.size
    margin = 18
    ld.rectangle([0, 0, lw, margin], fill=BAD + (90,))
    ld.rectangle([0, lh - margin, lw, lh], fill=BAD + (90,))
    ld.rectangle([0, margin, margin, lh - margin], fill=BAD + (90,))
    ld.rectangle([lw - margin, margin, lw, lh - margin], fill=BAD + (90,))
    # p: 0 centered, 1 touching the edge zone, 2 cut off.
    if p <= 1:
        dx = lerp(0, lw / 2 - margin - 40, p)
    else:
        dx = lerp(lw / 2 - margin - 40, lw / 2 + 10, p - 1)
    dy = -lerp(0, 60, min(p, 1))
    draw_board(ld, quad_map(square_quad(lw / 2 + dx, lh / 2 + dy, 120)))
    ld.ellipse([lw / 2 - 26, lh - 72, lw / 2 + 26, lh - 20], fill=(255, 255, 255, 220), outline=INK, width=3)
    img.paste(layer, (int(scr[0]), int(scr[1])))
    d.text((70, 300), "edge\nzone", font=font(24), fill=BAD, anchor="mm", align="center")
    d.line([(108, 300), (186, 300)], fill=BAD, width=3)
    d.polygon([(190, 300), (180, 294), (180, 306)], fill=BAD)

    if abs(p - round(p)) > 1e-6:
        return img, None
    return img, [(True, "Whole board, well inside frame"),
                 (False, "Too near the edge"),
                 (False, "Board cut off: corners missing")][round(p)]


def scene_lens(p):
    img, d = canvas()
    scr = phone(d, (175, 92, 465, 546))
    layer, ld = screen_layer(scr)
    lw, lh = layer.size
    k = 0.32 * p
    zoom = 1 - 0.35 * p
    half = lw / 2

    def f(x, y):
        """World (screen half-widths at 1x) -> screen px, with zoom + barrel distortion."""
        x, y = x * zoom, y * zoom
        r2 = x * x + (y * half / half) ** 2
        s = 1 / (1 + k * r2)
        return lw / 2 + x * s * half, lh / 2 + y * s * half

    def poly(pts, **kw):
        ld.line([f(*q) for q in pts], **kw)

    steps = [i / 20 for i in range(-60, 61)]
    for g in range(-6, 7):
        gx = g * 0.36
        poly([(gx, t) for t in steps], fill=WALL_DARK, width=2)
        poly([(t, gx) for t in steps], fill=WALL_DARK, width=2)
    door = [(0.55, -1.4), (1.35, -1.4), (1.35, 1.9), (0.55, 1.9), (0.55, -1.4)]
    dense = []
    for a, b in zip(door, door[1:]):
        dense += [(lerp(a[0], b[0], t / 20), lerp(a[1], b[1], t / 20)) for t in range(21)]
    ld.polygon([f(*q) for q in dense], fill=(150, 110, 80))
    poly(dense, fill=INK, width=4)
    s = 0.42 / 8.5
    draw_board(ld, lambda ix, iy: f(-0.75 + (ix - PAPER_LO) * s * 2, -0.55 + (iy - PAPER_LO) * s * 2))

    sel = 0 if p < 0.5 else 1
    for i, (txt, cx) in enumerate((("1×", lw / 2 + 34), ("0.5×", lw / 2 - 34))):
        on = i == sel
        ld.ellipse([cx - 26, lh - 64, cx + 26, lh - 12], fill=(255, 210, 60) if on else (30, 30, 40, 200))
        ld.text((cx, lh - 38), txt, font=font(18), fill=INK if on else (230, 230, 230), anchor="mm")
    img.paste(layer, (int(scr[0]), int(scr[1])))

    if abs(p - round(p)) > 1e-6:
        return img, None
    return img, [(True, "1× main lens: straight lines"), (False, "0.5× ultra-wide bends lines")][round(p)]


def scene_paper(p):
    img, d = canvas()
    d.rectangle([0, AREA_TOP, W, AREA_BOT], fill=WALL)
    curl = max(0.0, 1 - abs(p - 1))
    glare = max(0.0, p - 1)
    x0, y0, x1, y1 = 180, 150, 460, 430
    draw_board(d, quad_map([(x0, y0), (x1, y0), (x1, y1), (x0, y1)]))
    for cx, cy, w, h in (((x0 + x1) / 2, y0, 70, 20), ((x0 + x1) / 2, y1, 70, 20),
                         (x0, (y0 + y1) / 2, 20, 70), (x1, (y0 + y1) / 2, 20, 70)):
        d.rectangle([cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2], fill=TAPE)
    if curl > 0:
        s = 130 * curl
        a, b, c = (x1 - s, y1), (x1, y1 - s), (x1, y1)
        d.polygon([a, b, c], fill=WALL)
        d.polygon([(a[0] + 8, a[1] + 8), (b[0] + 8, b[1] + 8), (x1 - s + 8, y1 - s + 8)], fill=(0, 0, 0, 50))
        d.polygon([a, b, (x1 - s, y1 - s)], fill=(225, 225, 230), outline=(150, 150, 150))
    if glare > 0:
        layer = Image.new("L", (W, H), 0)
        ImageDraw.Draw(layer).ellipse([270, 150, 470, 330], fill=int(255 * glare))
        layer = layer.filter(ImageFilter.GaussianBlur(28))
        img.paste((255, 255, 250), (0, 0), layer)
        d = ImageDraw.Draw(img, "RGBA")
        lx, ly = 560, 120
        d.ellipse([lx - 26, ly - 26, lx + 26, ly + 26], fill=(255, 220, 80, int(255 * glare)), outline=INK)
        for i in range(8):
            a = math.radians(i * 45)
            d.line([(lx + 34 * math.cos(a), ly + 34 * math.sin(a)), (lx + 48 * math.cos(a), ly + 48 * math.sin(a))],
                   fill=(230, 160, 0, int(255 * glare)), width=4)
    label(d, (320, 492), "tape all 4 edges", 24)

    if abs(p - round(p)) > 1e-6:
        return img, None
    return img, [(True, "Taped flat on all 4 edges"),
                 (False, "Curled paper bends the grid"),
                 (False, "Glare hides the markers")][round(p)]


def scene_plane(p):
    img, d = canvas()
    floor_y = 440
    d.rectangle([0, AREA_TOP, W, floor_y], fill=WALL)
    d.rectangle([0, floor_y, W, AREA_BOT], fill=FLOOR)
    for x in range(-200, W + 200, 70):
        d.line([(x, AREA_BOT), (x + (x - 320) * -0.25, floor_y)], fill=(160, 132, 104), width=2)
    stage = math.floor(p + 1e-6)
    if p >= 1 - 1e-6 and stage == 1:
        d.rectangle([0, AREA_TOP, W, floor_y], fill=GOOD + (40,))
    if stage == 3:
        d.rectangle([0, floor_y, W, AREA_BOT], fill=BAD + (70,))

    draw_board(d, quad_map(square_quad(110, 220, 96)))
    label(d, (110, 292), "board", 20)
    d.rectangle([390, 190, 520, floor_y], fill=(150, 110, 80), outline=INK, width=4)
    d.ellipse([496, 318, 508, 330], fill=(250, 200, 60), outline=INK)
    # A cabinet standing in front of the wall: closer to the camera than the board.
    fx0, fy0, fx1, fy1, dep = 180, 340, 320, 500, 34
    top = [(fx0, fy0), (fx1, fy0), (fx1 + dep, fy0 - dep), (fx0 + dep, fy0 - dep)]
    side = [(fx1, fy0), (fx1 + dep, fy0 - dep), (fx1 + dep, fy1 - dep), (fx1, fy1)]
    d.polygon(top, fill=(120, 150, 190), outline=INK)
    d.polygon(side, fill=(80, 110, 150), outline=INK)
    d.rectangle([fx0, fy0, fx1, fy1], fill=(100, 130, 175), outline=INK, width=3)
    if stage == 2:
        for poly in (top, side):
            d.polygon(poly, fill=BAD + (80,))
        d.rectangle([fx0, fy0, fx1, fy1], fill=BAD + (80,))

    def measure(a, b, t, text, ok):
        if t <= 0:
            return
        e = (lerp(a[0], b[0], t), lerp(a[1], b[1], t))
        d.line([a, e], fill=LINE, width=5)
        for q in (a, e):
            d.ellipse([q[0] - 7, q[1] - 7, q[0] + 7, q[1] + 7], fill=LINE, outline="white", width=2)
        if t >= 1:
            mx, my = (a[0] + b[0]) / 2, min(a[1], b[1]) - 24
            label(d, (mx, my), text, 24, fg=GOOD if ok else BAD)
            if not ok:
                bb = d.textbbox((mx, my), text, font=font(24), anchor="mm")
                d.line([(bb[0] - 4, my), (bb[2] + 4, my)], fill=BAD, width=3)

    t = p - stage if stage < 3 else 1.0
    if stage == 0:
        measure((390, 260), (520, 260), t, "3'-0\"", True)
    elif stage == 1:
        measure((390, 260), (520, 260), 1, "3'-0\"", True)
        measure((fx0, 420), (fx1, 420), t, "2'-4\"", False)
    elif stage == 2:
        measure((fx0, 420), (fx1, 420), 1, "2'-4\"", False)
        measure((60, 500), (150, 535), t, "1'-1\"", False)
    else:
        measure((60, 500), (150, 535), 1, "1'-1\"", False)

    if abs(p - round(p)) > 1e-6:
        return img, None
    return img, [(None, "Which lengths can you trust?"),
                 (True, "Same wall as the board: correct"),
                 (False, "Cabinet sticks out: wrong size"),
                 (False, "Floor is another plane: wrong")][round(p)]


def scene_summary(_p):
    img, d = canvas()
    do = ["3–10 ft away", "Within 45°", "Whole board in frame", "Paper taped flat", "1× lens"]
    dont = ["0.5× lens", "Board at edge", "Steep angle", "Curls or glare", "Points off the board's plane"]
    for col, (items, ok, head) in enumerate(((do, True, "DO"), (dont, False, "DON'T"))):
        x = 24 + col * 308
        d.rounded_rectangle([x, 96, x + 292, 528], radius=18, fill=(255, 255, 255),
                            outline=GOOD if ok else BAD, width=4)
        d.text((x + 146, 128), head, font=font(34), fill=GOOD if ok else BAD, anchor="mm")
        y = 172
        for it in items:
            (check_icon if ok else cross_icon)(d, x + 30, y + 12, 16)
            words, lines = it.split(), [""]
            for w_ in words:
                trial = (lines[-1] + " " + w_).strip()
                if font(25).getlength(trial) > 228:
                    lines.append(w_)
                else:
                    lines[-1] = trial
            for i, ln in enumerate(lines):
                d.text((x + 54, y + i * 30 - 3), ln, font=font(25), fill=INK)
            y += 34 + 30 * len(lines)
    return img, (False, "LIMIT: only the board's flat surface")


SCENES = [
    ("Stand 3–10 ft away", scene_distance, [2, 6, 14]),
    ("Stay within 45° of straight-on", scene_angle, [0, 35, 70]),
    ("Whole board in the frame", scene_frame, [0, 1, 2]),
    ("Use the 1× lens, never 0.5×", scene_lens, [0, 1]),
    ("Paper flat, no glare", scene_paper, [0, 1, 2]),
    ("LIMIT: board's plane only", scene_plane, [0, 1, 2, 3]),
]


def decorate(img, title, idx, verdict, limit=False):
    d = ImageDraw.Draw(img, "RGBA")
    d.rectangle([0, 0, W, AREA_TOP - 4], fill=BAD if limit else BG)
    d.line([(0, AREA_TOP - 4), (W, AREA_TOP - 4)], fill=INK, width=3)
    fg = "white" if limit else INK
    pill = f"{idx}/{len(SCENES)}" if idx else "recap"
    pf = font(20)
    pw = pf.getlength(pill) + 24
    d.rounded_rectangle([W - 20 - pw, 26, W - 20, 58], radius=16,
                        fill=(255, 255, 255, 60) if limit else INK)
    d.text((W - 20 - pw / 2, 42), pill, font=pf, fill="white", anchor="mm")
    d.text((22, 42), title, font=fit_font(title, int(W - 60 - pw), 34), fill=fg, anchor="lm")

    d.rectangle([0, AREA_BOT + 4, W, H], fill=BG)
    box = [24, 566, W - 24, 626]
    if verdict is None:
        d.rounded_rectangle(box, radius=30, fill=NEUTRAL)
        for i in range(3):
            d.ellipse([304 + i * 16 - 4, 592, 304 + i * 16 + 4, 600], fill="white")
        return img
    ok, text = verdict
    if ok is None:
        d.rounded_rectangle(box, radius=30, fill=INK)
        d.text((W / 2, 596), text, font=fit_font(text, W - 100, 30), fill="white", anchor="mm")
        return img
    d.rounded_rectangle(box, radius=30, fill=GOOD if ok else BAD)
    d.ellipse([38, 574, 82, 618], fill="white")
    (check_icon if ok else cross_icon)(d, 60, 596, 17)
    d.text((92, 596), text, font=fit_font(text, W - 140, 30), fill="white", anchor="lm")
    return img


def build():
    frames, durations = [], []
    for idx, (title, render, stops) in enumerate(SCENES, 1):
        limit = title.startswith("LIMIT")
        for i, stop in enumerate(stops):
            if i:
                prev = stops[i - 1]
                for k in range(1, MOVE_FRAMES):
                    img, v = render(lerp(prev, stop, smooth(k / MOVE_FRAMES)))
                    frames.append(decorate(img, title, idx, v, limit))
                    durations.append(MOVE_MS)
            img, v = render(stop)
            frames.append(decorate(img, title, idx, v, limit))
            durations.append(HOLD_MS)
    img, v = scene_summary(0)
    frames.append(decorate(img, "Capture rules", 0, v, limit=False))
    durations.append(SUMMARY_MS)
    # The summary also goes first, so viewers that don't animate PNGs still see the rules.
    frames.insert(0, frames[-1])
    durations.insert(0, 1500)
    return frames, durations


def main():
    frames, durations = build()
    # RGBA on purpose: st.image(output_format="auto") re-encodes an opaque PNG as a
    # JPEG (dropping the animation) but serves a PNG with alpha byte-for-byte.
    frames = [f.convert("RGBA") for f in frames]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(OUT, save_all=True, append_images=frames[1:], duration=durations, loop=0,
                   optimize=True)
    print(f"wrote {OUT} ({len(frames)} frames, {sum(durations) / 1000:.0f} s, "
          f"{OUT.stat().st_size / 1e6:.2f} MB)")


if __name__ == "__main__":
    main()
