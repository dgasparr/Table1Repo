"""Render assets/capture_rules.png: do/don't capture rules for the in-app help. Owner: Pair C.

Rules are the ones tested in A13 (plan/A13_stress_results.md). Uses the real board (IDs 0-3).
    python tools/make_capture_rules.py
"""
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "capture_rules.png"

W, ROW_H, ICON = 900, 170, 220
GREEN, RED, INK, GREY, PAPER = (30, 150, 70), (210, 45, 45), (25, 25, 25), (150, 150, 150), (255, 255, 255)

DO = [
    ("dist", "Stand 3–10 ft away", "Board big enough to read, close enough to be sharp"),
    ("angle_ok", "Within 45° of straight-on", "Up to 60° is OK when you're close (3–6 ft)"),
    ("still", "Hold still, main 1× lens", "Shake is fine up to 10 ft, not beyond"),
    ("frame_ok", "Whole board in the frame", "Keep it away from the photo edges"),
    ("near", "Board right next to the thing", "Measure within about a foot of the board"),
]
DONT = [
    ("wide", "No 0.5× ultra-wide lens", "It bends straight lines"),
    ("angle_bad", "No steep angles", "Past 60° the board gets hard to read"),
    ("frame_bad", "Don't cut the board off", "All 4 markers should be visible"),
    ("curl", "No curled paper or glare", "Tape all 4 edges flat"),
    ("far", "Don't measure far from it", "Stay on the board's flat surface; long reaches get a big ±"),
]


def font(size, bold=False):
    for name in (("arialbd.ttf" if bold else "arial.ttf"), "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            pass
    return ImageFont.load_default()


def board_img(px: int) -> Image.Image:
    """The real 2x2 board (IDs 0-3) as a square image."""
    d = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    m = px * 3 // 7
    g = px - 2 * m
    b = np.full((px, px), 255, np.uint8)
    for i, (c, r) in enumerate([(0, 0), (1, 0), (0, 1), (1, 1)]):
        b[r * (m + g):r * (m + g) + m, c * (m + g):c * (m + g) + m] = cv2.aruco.generateImageMarker(d, i, m)
    return Image.fromarray(b).convert("RGB")


def paste_board(img, xy, px):
    img.paste(board_img(px), xy)
    ImageDraw.Draw(img).rectangle((xy[0] - 4, xy[1] - 4, xy[0] + px + 4, xy[1] + px + 4), outline=GREY, width=2)


def phone(d, x, y, w=46, h=80, color=INK):
    d.rounded_rectangle((x, y, x + w, y + h), 8, outline=color, width=4)
    d.ellipse((x + w // 2 - 5, y + 8, x + w // 2 + 5, y + 18), outline=color, width=3)


def arrow(d, a, b, color, width=4):
    d.line([a, b], fill=color, width=width)
    v = np.subtract(b, a); v = v / np.linalg.norm(v); n = np.array([-v[1], v[0]])
    for tip, s in ((b, -1), (a, 1)):
        p = np.array(tip)
        d.polygon([tuple(p), tuple(p + s * 14 * v + 7 * n), tuple(p + s * 14 * v - 7 * n)], fill=color)


def icon(kind: str, ok: bool) -> Image.Image:
    im = Image.new("RGB", (ICON, ROW_H - 20), PAPER)
    d = ImageDraw.Draw(im)
    col = GREEN if ok else RED
    H = ROW_H - 20
    if kind == "dist":
        paste_board(im, (14, 40), 60)
        phone(d, 160, 30)
        arrow(d, (84, 112), (158, 112), col)
        d.text((92, 118), "3–10 ft", fill=col, font=font(18, True))
    elif kind in ("angle_ok", "angle_bad"):  # top view: wall, board, phone at an angle
        d.line([(20, 30), (200, 30)], fill=INK, width=5)
        d.rectangle((90, 22, 130, 30), fill=INK)
        ang = 40 if ok else 72
        a = np.radians(ang)
        cx, cy, r = 110, 30, 105
        px_, py_ = cx + r * np.sin(a), cy + r * np.cos(a)
        d.line([(cx, cy), (cx, cy + r)], fill=GREY, width=2)
        d.line([(cx, cy), (px_, py_)], fill=col, width=4)
        phone(d, int(px_) - 15, int(py_) - 10, 30, 22, col)
        d.text((cx - 70, cy + 70), f"{ang}°", fill=col, font=font(26, True))
    elif kind == "still":
        phone(d, 85, 20, 50, 90)
        d.text((40, 118), "1×  steady", fill=col, font=font(22, True))
    elif kind in ("frame_ok", "frame_bad"):
        d.rounded_rectangle((30, 10, 190, H - 10), 10, outline=INK, width=4)
        if ok:
            paste_board(im, (80, 40), 60)
        else:
            b = board_img(70)
            im.paste(b.crop((0, 0, 40, 70)), (150, 50))  # only the left part is in frame
            d.rounded_rectangle((30, 10, 190, H - 10), 10, outline=INK, width=4)
    elif kind == "near":
        d.rectangle((20, 10, 110, H - 5), outline=INK, width=4)  # door
        d.ellipse((92, 70, 102, 80), fill=INK)
        paste_board(im, (125, 30), 55)
        arrow(d, (20, H - 22), (110, H - 22), col)
    elif kind == "wide":
        d.text((40, 30), "0.5×", fill=col, font=font(60, True))
    elif kind == "curl":
        b = board_img(70).transform((70, 70), Image.QUAD, (0, 8, 0, 62, 70, 70, 70, 0))
        im.paste(b, (70, 30))
        d.arc((50, 10, 170, 60), 200, 340, fill=GREY, width=4)
        d.ellipse((115, 45, 145, 75), fill=(250, 250, 250), outline=(255, 210, 0), width=4)  # glare
    elif kind == "far":
        paste_board(im, (14, 20), 50)
        d.rectangle((120, 10, 205, H - 5), outline=INK, width=4)
        arrow(d, (20, H - 22), (205, H - 22), col)
        d.text((60, 82), "±±", fill=col, font=font(26, True))
    if not ok:  # red X badge
        d.ellipse((ICON - 42, 4, ICON - 6, 40), fill=RED)
        d.line([(ICON - 33, 13), (ICON - 15, 31)], fill=PAPER, width=5)
        d.line([(ICON - 15, 13), (ICON - 33, 31)], fill=PAPER, width=5)
    else:
        d.ellipse((ICON - 42, 4, ICON - 6, 40), fill=GREEN)
        d.line([(ICON - 34, 22), (ICON - 26, 31), (ICON - 13, 12)], fill=PAPER, width=5)
    return im


def section(title, rows, ok, color):
    h = 70 + ROW_H * len(rows)
    im = Image.new("RGB", (W, h), PAPER)
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, W, 60), fill=color)
    d.text((24, 10), title, fill=PAPER, font=font(38, True))
    for i, (kind, head, sub) in enumerate(rows):
        y = 70 + i * ROW_H
        im.paste(icon(kind, ok), (16, y + 10))
        d.text((ICON + 40, y + 38), head, fill=INK, font=font(34, True))
        d.text((ICON + 40, y + 88), sub, fill=(90, 90, 90), font=font(24))
        d.line([(16, y + ROW_H), (W - 16, y + ROW_H)], fill=(225, 225, 225), width=2)
    return im


def main():
    head = Image.new("RGB", (W, 110), PAPER)
    d = ImageDraw.Draw(head)
    d.text((24, 18), "How to take the photo", fill=INK, font=font(48, True))
    d.text((24, 76), "Follow these for the most accurate measurements", fill=(90, 90, 90),
            font=font(22))
    parts = [head, section("DO", DO, True, GREEN), section("DON'T", DONT, False, RED)]
    out = Image.new("RGB", (W, sum(p.height for p in parts) + 20), PAPER)
    y = 0
    for p in parts:
        out.paste(p, (0, y)); y += p.height + 10
    OUT.parent.mkdir(exist_ok=True)
    out.save(OUT)
    print(f"wrote {OUT} ({out.width}x{out.height})")


if __name__ == "__main__":
    main()
