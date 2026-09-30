"""Texturas panorámicas del carrusel (8 placas de 1080x1350 unidas): papel envejecido y desgaste de tinta."""
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

A = Path(__file__).resolve().parent.parent / "assets"
A.mkdir(parents=True, exist_ok=True)
N, SW, SH = 8, 1080, 1350
W, H = SW * N, SH
rng = np.random.default_rng(7)


def smooth_noise(h, w, scale, octaves=4):
    out = np.zeros((h, w), np.float32)
    amp, tot = 1.0, 0.0
    for o in range(octaves):
        s = max(2, int(scale / 2 ** o))
        small = rng.random((h // s + 2, w // s + 2))
        img = Image.fromarray((small * 255).astype(np.uint8)).resize((w + 2 * s, h + 2 * s), Image.BICUBIC)
        out += amp * np.asarray(img, np.float32)[s:s + h, s:s + w] / 255
        tot += amp
        amp *= .5
    return out / tot


base = np.array([241, 226, 193], np.float32)
mott = smooth_noise(H, W, 260, 5)
fib = smooth_noise(H, W, 6, 2)
paper = base[None, None, :] * (0.94 + 0.08 * mott[..., None]) - (fib[..., None] - .5) * 14
yy = np.linspace(-1, 1, H, dtype=np.float32)[:, None]
xx = np.linspace(-1, 1, W, dtype=np.float32)[None, :]
edge = np.clip(np.sqrt((xx * 1.02) ** 2 * .35 + yy ** 2), 0, 1.4)
paper *= (1 - .08 * edge ** 3)[..., None]
spots = (smooth_noise(H, W, 40, 2) > .82) * rng.random((H, W)).astype(np.float32) * 10
paper -= spots[..., None] * np.array([0.6, 0.8, 1.0], np.float32)
Image.fromarray(np.clip(paper, 0, 255).astype(np.uint8)).save(A / "paper-pano.jpg", quality=92)

m = rng.random((H, W), dtype=np.float32)
patch = smooth_noise(H, W, 120, 3)
dots = m > (.965 - .05 * np.clip((patch - .45) / .3, 0, 1))
wear = np.zeros((H, W, 4), np.uint8)
wear[..., :3] = (241, 226, 193)
wear[..., 3] = (dots * rng.uniform(110, 210, (H, W))).astype(np.uint8)
Image.fromarray(wear).filter(ImageFilter.GaussianBlur(.45)).save(A / "wear-pano.png")
print("ok")
