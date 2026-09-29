"""Genera las texturas del reel (papel, desgaste de tinta, pinceladas) y recorta los logos.

Uso: python3 assets.py <logo_fondo_crema.png> <logo_fondo_rojo.png>
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

A = Path(__file__).resolve().parent.parent / "assets"
W, H = 1080, 1920
rng = np.random.default_rng(42)


def smooth_noise(h, w, scale, octaves=4):
    """Ruido multiescala (0..1) con interpolación bicúbica."""
    out = np.zeros((h, w))
    amp, tot = 1.0, 0.0
    for o in range(octaves):
        s = max(2, int(scale / 2 ** o))
        small = rng.random((h // s + 2, w // s + 2))
        img = Image.fromarray((small * 255).astype(np.uint8)).resize((w + 2 * s, h + 2 * s), Image.BICUBIC)
        out += amp * np.asarray(img, float)[s:s + h, s:s + w] / 255
        tot += amp
        amp *= .5
    return out / tot


# ---------- papel envejecido
base = np.array([241, 226, 193], float)
mott = smooth_noise(H, W, 260, 5)
fib = smooth_noise(H, W, 6, 2)
paper = base[None, None, :] * (0.94 + 0.08 * mott[..., None]) - (fib[..., None] - .5) * 14
yy, xx = np.mgrid[0:H, 0:W]
edge = np.clip(np.hypot((xx - W / 2) / (W * .62), (yy - H / 2) / (H * .6)), 0, 1.4)
paper *= (1 - .10 * edge ** 3)[..., None]
paper[..., 2] -= 6 * edge ** 2
spots = (smooth_noise(H, W, 40, 2) > .82) * rng.random((H, W)) * 10
paper -= spots[..., None] * np.array([0.6, 0.8, 1.0])
Image.fromarray(np.clip(paper, 0, 255).astype(np.uint8)).save(A / "paper.jpg", quality=92)

# ---------- desgaste de tinta: motitas crema que "comen" la tinta roja y negra
wear = np.zeros((H, W, 4), np.uint8)
m = rng.random((H, W))
patch = smooth_noise(H, W, 120, 3)
thr = .965 - .05 * np.clip((patch - .45) / .3, 0, 1)      # más motas en algunas zonas, pocas en otras
dots = m > thr
alpha = (dots * rng.uniform(110, 210, (H, W))).astype(np.uint8)
wear[..., :3] = (241, 226, 193)
wear[..., 3] = alpha
Image.fromarray(wear).filter(ImageFilter.GaussianBlur(.45)).save(A / "wear.png")


# ---------- pincelada roja (borde áspero + estrías de pincel seco)
def brush(w, h, seed, red=(176, 42, 30)):
    r = np.random.default_rng(seed)
    y = np.arange(h)[:, None] / h
    x = np.arange(w)[None, :] / w
    edge_noise = smooth_noise(h, w, 30, 3)
    top = .18 + .10 * np.sin(x * 7 + seed) + (edge_noise - .5) * .22
    bot = .82 + .08 * np.sin(x * 5 + seed * 2) + (edge_noise - .5) * .22
    inside = (y > top) & (y < bot)
    streak = np.asarray(Image.fromarray((r.random((h, 1)) * 255).astype(np.uint8)).resize((w, h), Image.BILINEAR), float) / 255
    dry = (streak > .12) | (x > .15)
    fade_in = np.clip(x / .12, 0, 1)
    a = inside * dry * (0.75 + .25 * smooth_noise(h, w, 8, 2)) * np.clip(fade_in + (r.random((h, w)) > .5) * .0, 0, 1)
    a *= ~((r.random((h, w)) > .985) & (x < .5))
    img = np.zeros((h, w, 4), np.uint8)
    img[..., :3] = red
    img[..., 3] = (np.clip(a, 0, 1) * 255).astype(np.uint8)
    return Image.fromarray(img).filter(ImageFilter.GaussianBlur(.8))


brush(1600, 420, 3).save(A / "brush1.png")
brush(1600, 420, 11).save(A / "brush2.png")


# ---------- logos: recorte circular del badge
def cut_badge(src, out, pick_red_ring):
    im = Image.open(src).convert("RGB")
    a = np.asarray(im).astype(int)
    if pick_red_ring:   # badge rojo sobre papel crema
        mask = (a[..., 0] > 120) & (a[..., 1] < 110) & (a[..., 2] < 100)
    else:               # badge crema sobre fondo rojo
        mask = (a[..., 0] > 200) & (a[..., 1] > 180) & (a[..., 2] > 130)
    ys, xs = np.where(mask)
    x0, x1, y0, y1 = np.percentile(xs, .2), np.percentile(xs, 99.8), np.percentile(ys, .2), np.percentile(ys, 99.8)
    cx, cy, rad = (x0 + x1) / 2, (y0 + y1) / 2, max(x1 - x0, y1 - y0) / 2 + 2
    s = 4  # máscara antialiasing
    big = Image.new("L", (im.width * s, im.height * s), 0)
    from PIL import ImageDraw
    ImageDraw.Draw(big).ellipse([(cx - rad) * s, (cy - rad) * s, (cx + rad) * s, (cy + rad) * s], fill=255)
    rgba = im.convert("RGBA")
    rgba.putalpha(big.resize(im.size, Image.LANCZOS))
    box = (int(cx - rad) - 2, int(cy - rad) - 2, int(cx + rad) + 3, int(cy + rad) + 3)
    rgba.crop(box).save(A / out)
    print(out, box)


cut_badge(sys.argv[1], "badge-rojo.png", True)
cut_badge(sys.argv[2], "badge-crema.png", False)
print("ok")
