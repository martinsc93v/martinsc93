"""Balde de pochoclos realista: cono de cartón a rayas con el logo impreso, lleno de pochoclos 3D.

Raymarching del balde (cono truncado + borde enrollado) con cámara en perspectiva y luz de estudio;
la montaña de pochoclos se compone con los sprites 3D de popcorn3d.py usando prueba de profundidad
contra el balde (los de adelante desbordan sobre el borde, los de adentro quedan tapados).

Uso: python3 bucket3d.py  -> assets/bucket.png
"""
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
A = ROOT / "assets"
W, H = 880, 1120          # imagen final
SS = 2
BH, RB, RT = 1.55, .56, .80   # alto, radio base, radio boca
rng = np.random.default_rng(8)

# ---------------- cámara
cam = np.array([0, 2.5, -6.7])
tgt = np.array([0, 1.05, 0])
fwd = (tgt - cam) / np.linalg.norm(tgt - cam)
right = np.cross(np.array([0, 1.0, 0]), fwd); right /= np.linalg.norm(right)
up = np.cross(fwd, right)
FOV = np.radians(24)
SCALE = np.tan(FOV / 2)


def project(p):
    v = p - cam
    z = v @ fwd
    x, y = (v @ right) / (z * SCALE), (v @ up) / (z * SCALE)
    aspect = W / H
    return (x / aspect * .5 + .5) * W, (.5 - y * .5) * H, z


# ---------------- SDF
def capped_cone(p):
    q = np.stack([np.hypot(p[:, 0], p[:, 2]), p[:, 1] - BH / 2], 1)
    h = BH / 2
    k1 = np.array([RT, h])
    k2 = np.array([RT - RB, 2 * h])
    r = np.where(q[:, 1] < 0, RB, RT)
    ca = np.stack([q[:, 0] - np.minimum(q[:, 0], r), np.abs(q[:, 1]) - h], 1)
    cb = q - k1 + k2 * np.clip(((k1 - q) @ k2) / (k2 @ k2), 0, 1)[:, None]
    s = np.where((cb[:, 0] < 0) & (ca[:, 1] < 0), -1, 1)
    return s * np.sqrt(np.minimum((ca ** 2).sum(1), (cb ** 2).sum(1))) - .008


def rim(p):
    return np.hypot(np.hypot(p[:, 0], p[:, 2]) - RT, p[:, 1] - BH) - .034


def sdf(p):
    return np.minimum(capped_cone(p), rim(p))


# ---------------- raymarch del balde
s_w, s_h = W * SS, H * SS
xs = ((np.arange(s_w) + .5) / s_w * 2 - 1) * (W / H)
ys = 1 - (np.arange(s_h) + .5) / s_h * 2
XX, YY = np.meshgrid(xs, ys)
dirs = fwd[None, :] + (XX.ravel()[:, None] * right + YY.ravel()[:, None] * up) * SCALE
dirs /= np.linalg.norm(dirs, axis=1, keepdims=True)
t = np.full(len(dirs), 3.5)
hit = np.zeros(len(dirs), bool)
act = np.arange(len(dirs))
for _ in range(120):
    if act.size == 0:
        break
    p = cam + dirs[act] * t[act, None]
    d = sdf(p)
    h = d < .0008
    hit[act[h]] = True
    t[act] += np.where(h, 0, d)
    act = act[~h & (t[act] < 9)]
idx = np.where(hit)[0]
P = cam + dirs[idx] * t[idx, None]
e = .002
nrm = np.stack([sdf(P + [e, 0, 0]) - sdf(P - [e, 0, 0]), sdf(P + [0, e, 0]) - sdf(P - [0, e, 0]), sdf(P + [0, 0, e]) - sdf(P - [0, 0, e])], 1)
nrm /= np.linalg.norm(nrm, axis=1, keepdims=True)

# ---------------- materiales
lin = lambda c: (np.array(c) / 255) ** 2.2
RED, CREAM, INSIDE = lin((176, 30, 26)), lin((243, 234, 216)), lin((70, 40, 20))
theta = np.arctan2(P[:, 2], P[:, 0])
NS = 18
f = (theta / (2 * np.pi) * NS + .25) % 1
aa = .035
stripe = np.clip((np.abs(f - .5) - .25) / aa + .5, 0, 1)          # 1 = rojo
alb = CREAM * (1 - stripe[:, None]) + RED * stripe[:, None]
is_rim = rim(P) < capped_cone(P)
is_top = (~is_rim) & (nrm[:, 1] > .9) & (P[:, 1] > BH - .02)
alb[is_rim] = CREAM * .96
alb[is_top] = INSIDE
# logo impreso adelante (mapeo cilíndrico)
badge = np.asarray(Image.open(A / "badge-rojo.png").convert("RGBA").resize((600, 600), Image.LANCZOS)).astype(float) / 255
radius_y = RB + (RT - RB) * P[:, 1] / BH
arc = (theta + np.pi / 2) * radius_y
yc, LR = .80, .36
du, dv = arc / LR, (P[:, 1] - yc) / LR
rr = np.hypot(du, dv)
side = (~is_rim) & (~is_top) & (np.abs(theta + np.pi / 2) < 1.2)
back = side & (rr < 1.0)
alb[back] = CREAM
ring = side & (rr >= .93) & (rr < 1.0)
alb[ring] = RED
bi = side & (rr < .88)
bu = np.clip(((du[bi] / .88) * .5 + .5) * 599, 0, 599).astype(int)
bv = np.clip(((-dv[bi] / .88) * .5 + .5) * 599, 0, 599).astype(int)
bpx = badge[bv, bu]
alb[bi] = alb[bi] * (1 - bpx[:, 3:]) + (bpx[:, :3] ** 2.2) * bpx[:, 3:]
# textura de cartón
grain = 1 + .035 * np.sin(P[:, 1] * 180 + np.sin(theta * 40) * 2) * np.sin(theta * 300) + .02 * rng.standard_normal(len(idx))
alb *= grain[:, None]

# ---------------- luz de estudio
V = -dirs[idx]
Lk = np.array([-.62, .62, -.48]); Lk /= np.linalg.norm(Lk)
Lf = np.array([.8, .2, -.55]); Lf /= np.linalg.norm(Lf)
ndl = np.clip(nrm @ Lk, 0, 1)
col = alb * (np.array([1, .94, .84]) * 2.0 * ndl[:, None]
             + np.array([.75, .82, 1]) * .45 * np.clip(nrm @ Lf, 0, 1)[:, None]
             + np.array([.9, .9, .95]) * .28 * (.6 + .4 * nrm[:, 1:2]))
ao = np.clip(.55 + P[:, 1] / BH * .6, 0, 1)                    # más oscuro abajo
col *= ao[:, None]
Hv = Lk[None, :] + V
Hv /= np.linalg.norm(Hv, axis=1, keepdims=True)
fres = .04 + .96 * (1 - np.clip((nrm * V).sum(1), 0, 1)) ** 5
spec = (np.clip((nrm * Hv).sum(1), 0, 1) ** 45) * .55 + fres * .18
spec[is_top] = 0
col += spec[:, None] * np.array([1, .97, .92])
aces = lambda x: np.clip((x * (2.51 * x + .03)) / (x * (2.43 * x + .59) + .14), 0, 1)
rgb = aces(col) ** (1 / 2.2)

img = np.zeros((s_h * s_w, 4))
img[idx, :3] = rgb
img[idx, 3] = 1
depth = np.full(s_h * s_w, np.inf)
depth[idx] = t[idx] * (dirs[idx] @ fwd)
img = img.reshape(s_h, s_w, 4)
depth = depth.reshape(s_h, s_w)

# ---------------- montaña de pochoclos (sprites 3D con prueba de profundidad)
sheets = [np.asarray(Image.open(A / "pop" / f"pop_{i:02d}.webp").convert("RGBA")).astype(float) / 255 for i in range(10)]
pieces = []
for _ in range(300):                    # montaña sobre la boca
    a, rad = rng.uniform(0, 2 * np.pi), RT * np.sqrt(rng.uniform(0, 1)) * .99
    x, z = rad * np.cos(a), rad * np.sin(a)
    y = BH - .02 + .52 * (1 - (rad / RT) ** 2) ** .75 + rng.uniform(-.12, .05)
    pieces.append((x, y, z))
for _ in range(22):                     # algunos desbordando por adelante y los costados
    a = rng.uniform(-np.pi * .95, -np.pi * .05)
    rad = RT * rng.uniform(.95, 1.08)
    pieces.append((rad * np.cos(a), BH + rng.uniform(-.06, .05), rad * np.sin(a)))
pieces.sort(key=lambda q: -project(np.array(q))[2])
for (x, y, z) in pieces:
    px, py, pz = project(np.array([x, y, z]))
    size = .30 / (pz * SCALE) * .5 * H * SS * rng.uniform(.85, 1.2)
    sh = sheets[rng.integers(10)]
    fr = rng.integers(16)
    spr = Image.fromarray((sh[:, fr * 256:(fr + 1) * 256] * 255).astype(np.uint8), "RGBA")
    spr = spr.rotate(rng.uniform(-25, 25), resample=Image.BICUBIC).resize((int(size), int(size)), Image.LANCZOS)
    sa = np.asarray(spr).astype(float) / 255
    # sombreado por profundidad: los de atrás y abajo, más oscuros
    shade = np.clip(.74 + .45 * (y - BH) / .5 + .1 * (-z / RT), .7, 1.04)
    sa[..., :3] *= np.array([shade, shade * .96, shade * .88])
    x0, y0 = int(px * SS - size / 2), int(py * SS - size / 2)
    x1, y1 = x0 + sa.shape[1], y0 + sa.shape[0]
    cx0, cy0, cx1, cy1 = max(0, x0), max(0, y0), min(s_w, x1), min(s_h, y1)
    if cx0 >= cx1 or cy0 >= cy1:
        continue
    s_ = sa[cy0 - y0:cy1 - y0, cx0 - x0:cx1 - x0]
    dmask = depth[cy0:cy1, cx0:cx1] > pz - .08          # el balde no está adelante
    al = s_[..., 3] * dmask
    # sombra de contacto suave debajo de cada pochoclo
    region = img[cy0:cy1, cx0:cx1]
    region[..., :3] = region[..., :3] * (1 - al[..., None]) + s_[..., :3] * al[..., None]
    region[..., 3] = np.maximum(region[..., 3], al)
    depth[cy0:cy1, cx0:cx1] = np.where(al > .5, np.minimum(depth[cy0:cy1, cx0:cx1], pz), depth[cy0:cy1, cx0:cx1])

# ---------------- sombra en el piso
bx, by, _ = project(np.array([0, 0, 0]))
yy, xx = np.mgrid[0:s_h, 0:s_w]
ell = ((xx - bx * SS - 40 * SS) / (RB * 1.9 * H * SS / 4.9)) ** 2 + ((yy - by * SS) / (RB * .42 * H * SS / 4.9)) ** 2
sha = np.clip(1 - ell, 0, 1) ** 1.4 * .62
under = img[..., 3] < 1
img[..., :3] = np.where(under[..., None], img[..., :3] * img[..., 3:], img[..., :3])
comb_a = img[..., 3] + sha * (1 - img[..., 3])
shadow_col = np.array([.17, .12, .08])
img[..., :3] = np.where(under[..., None], (img[..., :3] + shadow_col * (sha * (1 - img[..., 3]))[..., None]) / np.maximum(comb_a, 1e-6)[..., None], img[..., :3])
img[..., 3] = comb_a

out = img.reshape(H, SS, W, SS, 4)
a = out[..., 3:].mean((1, 3))
rgbp = (out[..., :3] * out[..., 3:]).mean((1, 3))
final = np.concatenate([np.where(a > 0, rgbp / np.maximum(a, 1e-6), 0), a], -1)
Image.fromarray((np.clip(final, 0, 1) * 255).astype(np.uint8), "RGBA").save(A / "bucket.png")
print("ok", A / "bucket.png")

# ---------------- datos para ubicar la boca del balde en el reel
import json
mx, my, _ = project(np.array([0, BH, 0]))
ex, _, _ = project(np.array([RT, BH, 0]))
tx, ty, _ = project(np.array([0, BH + .42, 0]))
(A / "bucket_meta.json").write_text(json.dumps({"w": W, "h": H, "mouth": [mx, my], "mouth_r": ex - mx, "top": [tx, ty]}))
