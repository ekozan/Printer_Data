#!/usr/bin/env python3
"""Genere vendor/assets/jubilee_thumbnail.png (vignette du selecteur d'imprimante).
Necessite Pillow. Purement cosmetique."""
from PIL import Image, ImageDraw, ImageFont
import os

SS, N = 4, 256
W = N * SS
BG, PLATE, EDGE, GRID = (30, 33, 38), (52, 57, 65), (96, 104, 116), (70, 76, 86)
AMBER, TXT = (232, 160, 60), (176, 184, 196)
F = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

img = Image.new("RGB", (W, W), BG)
d = ImageDraw.Draw(img)
s = lambda v: int(v * SS)

# Plateau en perspective cavaliere (240 x 175 vu de 3/4)
top, bot, half = s(120), s(196), s(104)
skew = s(34)
plate = [(W // 2 - half + skew, top), (W // 2 + half + skew, top),
         (W // 2 + half, bot), (W // 2 - half, bot)]
d.polygon(plate, fill=PLATE, outline=EDGE, width=s(1.5))
for i in range(1, 5):                       # fuyantes
    t = i / 5
    x = W // 2 - half + int(2 * half * t)
    d.line([(x + skew, top), (x, bot)], fill=GRID, width=s(0.6))
for i in range(1, 4):
    t = i / 4
    y = top + int((bot - top) * t)
    x0 = W // 2 - half + int(skew * (1 - t))
    d.line([(x0, y), (x0 + 2 * half, y)], fill=GRID, width=s(0.6))
# Ligne d'amorce
d.line([(W // 2 - half + s(10), bot - s(6)), (W // 2 + half - s(10), bot - s(6))],
       fill=AMBER, width=s(2))

# Les 5 docks a l'arriere
dock_y = top - s(16)
for i in range(5):
    x = W // 2 + skew - half + s(9) + i * s(38)
    d.rounded_rectangle([x, dock_y, x + s(26), dock_y + s(13)], radius=s(2.5),
                        fill=(62, 68, 78), outline=EDGE, width=s(1))

d.text((W // 2, s(228)), "JUBILEE", font=ImageFont.truetype(F, s(26)), fill=TXT, anchor="mm")

os.makedirs("vendor/assets", exist_ok=True)
img.resize((N, N), Image.LANCZOS).save("vendor/assets/jubilee_thumbnail.png", optimize=True)
print("vendor/assets/jubilee_thumbnail.png", N, "x", N)
