#!/usr/bin/env python3
"""
Genere la texture de plateau PrusaSlicer pour la Jubilee/Trident.

La texture est etiree sur la bounding box de `bed_shape`, donc les
dimensions et l'origine ci-dessous doivent rester alignees sur le profil
imprimante (slicer/prusaslicer/Jubilee_Trident_bundle.ini).

    python3 make_bed_texture.py
    -> bed_texture.png

A charger dans PrusaSlicer :
  Reglages imprimante > General > Forme du plateau > Definir >
  Texture personnalisee > Charger...
"""
from PIL import Image, ImageDraw, ImageFont
import random

# --- Zone d'impression, en coordonnees G-code (cf. README §3) ---------------
X0, X1 = 50.0, 290.0
Y0, Y1 = 39.0, 214.0

# --- Reperes utiles, memes coordonnees --------------------------------------
PRIME_Y, PRIME_X0, PRIME_X1 = 41.0, 55.0, 275.0     # _PRINT_VARS de print_macros.cfg
TOWER_X, TOWER_Y, TOWER_W, TOWER_D = 222.0, 140.0, 60.0, 55.0   # wipe_tower_*

W_MM, D_MM = X1 - X0, Y1 - Y0
SS = 2                      # suréchantillonnage
S = 8 * SS                  # px par mm
W, H = int(W_MM * S), int(D_MM * S)

BG        = (34, 37, 42)
EDGE      = (72, 78, 87)
MINOR     = (255, 255, 255, 14)
MAJOR     = (255, 255, 255, 40)
LABEL     = (140, 148, 160, 255)
LABEL_DIM = (110, 117, 128, 255)
AMBER     = (232, 160, 60, 255)
BLUE      = (96, 156, 224, 255)
CROSS     = (255, 255, 255, 70)

FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
def font(mm, bold=False):
    return ImageFont.truetype(FONT_B if bold else FONT, int(mm * S))

def px(x, y):
    """mm (coordonnees G-code) -> pixels. Y est inverse : le haut de la
    texture correspond au fond du plateau (Y max)."""
    return ((x - X0) * S, (Y1 - y) * S)

img = Image.new("RGB", (W, H), BG)

# --- Grain de la tole poudree ------------------------------------------------
rnd = random.Random(20260911)
# grain genere en gros pixels : aspect poudrage, et PNG bien plus compact
GB = SS * 3
grain = Image.new("L", (W // GB, H // GB))
grain.putdata([rnd.randint(0, 255) for _ in range(grain.width * grain.height)])
grain = grain.resize((W, H), Image.NEAREST).point(lambda v: v // 26)
img = Image.composite(Image.new("RGB", (W, H), (58, 62, 69)), img, grain)

ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
d = ImageDraw.Draw(ov)

def line(p0, p1, fill, w_mm):
    d.line([px(*p0), px(*p1)], fill=fill, width=max(1, int(w_mm * S)))

def dashed(p0, p1, fill, w_mm, dash=2.5, gap=2.0):
    (ax, ay), (bx, by) = p0, p1
    length = ((bx - ax) ** 2 + (by - ay) ** 2) ** 0.5
    if length == 0:
        return
    ux, uy = (bx - ax) / length, (by - ay) / length
    t = 0.0
    while t < length:
        e = min(t + dash, length)
        line((ax + ux * t, ay + uy * t), (ax + ux * e, ay + uy * e), fill, w_mm)
        t = e + gap

def text(xy, s, f, fill, anchor="mm"):
    d.text(px(*xy), s, font=f, fill=fill, anchor=anchor)

# --- Grille 10 mm puis 50 mm, calee sur les coordonnees rondes ---------------
x = (int(X0) // 10) * 10
while x <= X1:
    if x >= X0:
        line((x, Y0), (x, Y1), MINOR, 0.12)
    x += 10
y = (int(Y0) // 10) * 10
while y <= Y1:
    if y >= Y0:
        line((X0, y), (X1, y), MINOR, 0.12)
    y += 10

# --- Graduations 50 mm (celles trop proches d'un coin sont omises) ----------
f_ax = font(3.8)
TICK_Y = Y0 + 11.0          # bandeau des graduations X, en bas
TICK_X = X0 + 6.5           # bandeau des graduations Y, a gauche
for x in range(50, int(X1) + 1, 50):
    line((x, Y0), (x, Y1), MAJOR, 0.22)
    if x - X0 > 18 and X1 - x > 18:
        text((x, TICK_Y), str(x), f_ax, LABEL_DIM)
for y in range(50, int(Y1) + 1, 50):
    line((X0, y), (X1, y), MAJOR, 0.22)
    if y - Y0 > 18 and Y1 - y > 18:
        text((TICK_X, y), str(y), f_ax, LABEL_DIM)

# --- Centre ------------------------------------------------------------------
cx, cy = (X0 + X1) / 2, (Y0 + Y1) / 2
line((cx - 6, cy), (cx + 6, cy), CROSS, 0.2)
line((cx, cy - 6), (cx, cy + 6), CROSS, 0.2)

# --- Ligne d'amorce de PRINT_START (non legendee ici : voir le cartouche) ----
line((PRIME_X0, PRIME_Y), (PRIME_X1, PRIME_Y), AMBER[:3] + (150,), 0.5)

# --- Emprise de la tour de purge (profil 5 outils) --------------------------
tx0, ty0, tx1, ty1 = TOWER_X, TOWER_Y, TOWER_X + TOWER_W, TOWER_Y + TOWER_D
for a, b in (((tx0, ty0), (tx1, ty0)), ((tx1, ty0), (tx1, ty1)),
             ((tx1, ty1), (tx0, ty1)), ((tx0, ty1), (tx0, ty0))):
    dashed(a, b, BLUE[:3] + (130,), 0.2)
text(((tx0 + tx1) / 2, (ty0 + ty1) / 2), "tour\nde purge", font(3.4), BLUE[:3] + (150,))

# --- Cartouche, dans la zone libre en haut a gauche -------------------------
lx, ly = X0 + 9.0, Y1 - 19.0
text((lx, ly), "JUBILEE  ·  TRIDENT", font(5.0, bold=True),
     (168, 175, 186, 230), anchor="ls")
text((lx, ly - 6.0), f"{W_MM:g} × {D_MM:g} mm   ·   Z max 220 mm", font(3.5),
     LABEL_DIM, anchor="ls")
line((lx, ly - 13.0), (lx + 7.0, ly - 13.0), AMBER[:3] + (170,), 0.5)
text((lx + 9.5, ly - 13.0), f"ligne d'amorce  (Y {PRIME_Y:g})", font(3.3),
     AMBER[:3] + (180,), anchor="lm")
dashed((lx, ly - 18.5), (lx + 7.0, ly - 18.5), BLUE[:3] + (150,), 0.2, 1.6, 1.2)
text((lx + 9.5, ly - 18.5), "tour de purge  (profil 5 outils)", font(3.3),
     BLUE[:3] + (170,), anchor="lm")

# --- Coins : coordonnees machine (test de verification du README §3) --------
f_c = font(3.5, bold=True)
for (x, y, ax, ay, anchor) in (
        (X0, Y0,  4.0,  4.5, "ls"), (X1, Y0, -4.0,  4.5, "rs"),
        (X0, Y1,  4.0, -4.5, "la"), (X1, Y1, -4.0, -4.5, "ra")):
    text((x + ax, y + ay), f"X{x:g}  Y{y:g}", f_c, LABEL, anchor=anchor)

# --- Repere de bord ----------------------------------------------------------
text((cx, Y1 - 5.0), "▲   côté docks  ·  Y ≥ 224", font(3.5),
     (118, 125, 136, 205))

img = Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")

# --- Bord de la tole ---------------------------------------------------------
d2 = ImageDraw.Draw(img)
d2.rectangle([0, 0, W - 1, H - 1], outline=EDGE, width=int(0.9 * S))
d2.rectangle([int(1.6 * S)] * 2 + [W - 1 - int(1.6 * S), H - 1 - int(1.6 * S)],
             outline=(50, 54, 61), width=max(1, int(0.18 * S)))

img = img.resize((W // SS, H // SS), Image.LANCZOS)
img.save("bed_texture.png", optimize=True)
print(f"bed_texture.png  {img.width}x{img.height} px  "
      f"({W_MM:g}x{D_MM:g} mm, origine X{X0:g} Y{Y0:g})")
