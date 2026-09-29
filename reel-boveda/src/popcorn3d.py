"""Render 3D procedural de pochoclos realistas (raymarching sobre un campo de distancias).

Cada pochoclo es una unión suave de lóbulos elipsoidales con arrugas (ruido de gradiente),
más la cascarita dorada del grano. Se renderiza girando sobre un eje (sprite sheet de F cuadros)
con luz principal cálida, relleno frío, oclusión ambiental, sombras suaves y translucidez en bordes.

Uso:
  python3 popcorn3d.py test        -> un pochoclo de prueba en output/preview/popcorn_test.png
  python3 popcorn3d.py all         -> assets/pop/pop_XX.webp (sheets) + kernel.webp
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import map_coordinates

ROOT = Path(__file__).resolve().parent.parent
G, L = 140, 1.15          # resolución y medio lado de la grilla del campo de distancias
SIZE, SS = 256, 2          # tamaño final del sprite y superamuestreo
FRAMES = 16


# ------------------------------------------------------------------ ruido
class Noise:
    def __init__(self, seed):
        r = np.random.default_rng(seed)
        p = r.permutation(256)
        self.perm = np.concatenate([p, p])
        g = r.normal(size=(256, 3))
        self.grad = g / np.linalg.norm(g, axis=1, keepdims=True)

    def __call__(self, p):
        pi = np.floor(p).astype(np.int64)
        pf = p - pi
        u = pf * pf * pf * (pf * (pf * 6 - 15) + 10)
        pm, gr = self.perm, self.grad
        out = 0
        vals = {}
        for dx in (0, 1):
            for dy in (0, 1):
                for dz in (0, 1):
                    h = pm[(pm[(pm[(pi[:, 0] + dx) & 255] + pi[:, 1] + dy) & 255] + pi[:, 2] + dz) & 255]
                    vals[dx, dy, dz] = (gr[h] * (pf - (dx, dy, dz))).sum(1)
        lx = lambda a, b: a + (b - a) * u[:, 0]
        x00, x10 = lx(vals[0, 0, 0], vals[1, 0, 0]), lx(vals[0, 1, 0], vals[1, 1, 0])
        x01, x11 = lx(vals[0, 0, 1], vals[1, 0, 1]), lx(vals[0, 1, 1], vals[1, 1, 1])
        y0 = x00 + (x10 - x00) * u[:, 1]
        y1 = x01 + (x11 - x01) * u[:, 1]
        return y0 + (y1 - y0) * u[:, 2]


def rand_rot(r):
    q = r.normal(size=4)
    q /= np.linalg.norm(q)
    a, b, c, d = q
    return np.array([[a*a+b*b-c*c-d*d, 2*(b*c-a*d), 2*(b*d+a*c)],
                     [2*(b*c+a*d), a*a-b*b+c*c-d*d, 2*(c*d-a*b)],
                     [2*(b*d-a*c), 2*(c*d+a*b), a*a-b*b-c*c+d*d]])


def axis_rot(axis, ang):
    axis = axis / np.linalg.norm(axis)
    K = np.array([[0, -axis[2], axis[1]], [axis[2], 0, -axis[0]], [-axis[1], axis[0], 0]])
    return np.eye(3) + np.sin(ang) * K + (1 - np.cos(ang)) * K @ K


def ellipsoid(q, r):
    k0 = np.linalg.norm(q / r, axis=-1)
    k1 = np.linalg.norm(q / (r * r), axis=-1)
    return k0 * (k0 - 1) / np.maximum(k1, 1e-6)


def smin(a, b, k):
    h = np.clip(.5 + .5 * (b - a) / k, 0, 1)
    return b * (1 - h) + a * h - k * h * (1 - h)


# ------------------------------------------------------------------ geometría
def grid_points():
    xs = np.linspace(-L, L, G)
    X, Y, Z = np.meshgrid(xs, xs, xs, indexing="ij")
    return np.stack([X, Y, Z], -1).reshape(-1, 3)


def popcorn_fields(seed):
    r = np.random.default_rng(seed)
    core = np.array([.36, .31, .33]) * r.uniform(.9, 1.1, 3)
    n = r.integers(8, 12)
    dirs = r.normal(size=(n, 3))
    dirs /= np.linalg.norm(dirs, axis=1, keepdims=True)
    lobes = []
    for i in range(n):
        wing = i < 2
        rad = (np.array([.44, .32, .13]) if wing else r.uniform(.17, .34, 3)) * r.uniform(.85, 1.1)
        dist = min(r.uniform(.30, .40) if wing else r.uniform(.30, .50), .92 - rad.max())
        lobes.append((dirs[i] * dist, rand_rot(r), rad, r.uniform(.045, .085)))
    n1, n2, n3 = Noise(seed + 1), Noise(seed + 2), Noise(seed + 3)
    off = r.uniform(0, 50, 3)

    def body(P):
        d = ellipsoid(P, core)
        for c, Rm, rad, k in lobes:
            d = smin(d, ellipsoid((P - c) @ Rm, rad), k)
        d = d - .045 * n1(P * 3.6 + off)                          # bultos grandes
        d = d + .018 * (1 - np.abs(n2(P * 7.0 + off))) ** 3       # pliegues
        d = d - .007 * n3(P * 18 + off)                           # textura fina
        return d

    P = grid_points()
    d = body(P)
    # cascarita: una escama curva apoyada sobre la superficie real
    u = r.normal(size=3)
    u /= np.linalg.norm(u)
    rs_line = np.linspace(0, 1.1, 400)
    prof = body(u[None, :] * rs_line[:, None])
    rs = rs_line[np.argmax(prof > 0)]
    R = .22
    c = u * (rs - R + .01)
    shell = np.abs(np.linalg.norm(P - c, axis=1) - R) - .011
    cap = np.linalg.norm(P - u * rs, axis=1) - .14
    hull = np.maximum(shell, cap)
    return d.reshape(G, G, G).astype(np.float32), hull.reshape(G, G, G).astype(np.float32)


def kernel_fields():
    P = grid_points()
    y = P[:, 1]
    q = P.copy()
    q[:, 0] /= (1 - .38 * np.clip(y / .55, 0, 1))
    q[:, 2] /= (1 - .30 * np.clip(y / .55, 0, 1))
    d = ellipsoid(q, np.array([.40, .56, .27])) * .8
    d = d - .006 * Noise(9)(P * 12)
    far = np.full_like(d, 9.0)
    return d.reshape(G, G, G).astype(np.float32), far.reshape(G, G, G).astype(np.float32)


# ------------------------------------------------------------------ render
def sampler(grid):
    def f(p):
        idx = (p + L) / (2 * L) * (G - 1)
        return map_coordinates(grid, idx.T, order=1, mode="nearest")
    return f


def aces(x):
    return np.clip((x * (2.51 * x + .03)) / (x * (2.43 * x + .59) + .14), 0, 1)


def render(fpop, fhull, Rm, kind="pop", seed=0):
    s = SIZE * SS
    u = ((np.arange(s) + .5) / s * 2 - 1) * 1.0
    XX, YY = np.meshgrid(u, -u)
    B = 1.08
    r2 = XX ** 2 + YY ** 2
    m = r2 < B * B
    ox, oy = XX[m], YY[m]
    t = -np.sqrt(B * B - r2[m])
    tmax = -t.copy()
    sp, sh = sampler(fpop), sampler(fhull)
    sdf = lambda p: np.minimum(sp(p), sh(p))
    hit = np.zeros(len(ox), bool)
    act = np.arange(len(ox))
    for _ in range(110):
        if act.size == 0:
            break
        P = np.stack([ox[act], oy[act], t[act]], 1) @ Rm
        d = sdf(P)
        h = d < .0012
        hit[act[h]] = True
        t[act] += np.where(h, 0, d * .7)
        act = act[~h & (t[act] < tmax[act])]
    idx = np.where(hit)[0]
    pc = np.stack([ox[idx], oy[idx], t[idx]], 1)
    po = pc @ Rm
    e = .013
    ex, ey, ez = np.eye(3) * e
    nobj = np.stack([sdf(po + ex) - sdf(po - ex), sdf(po + ey) - sdf(po - ey), sdf(po + ez) - sdf(po - ez)], 1)
    nobj /= np.linalg.norm(nobj, axis=1, keepdims=True) + 1e-9
    n = nobj @ Rm.T
    is_hull = sh(po) < sp(po) + .002
    # iluminación (espacio de cámara: x derecha, y arriba, z hacia adentro)
    Lk = np.array([-.52, .62, -.58]); Lk /= np.linalg.norm(Lk)
    Lf = np.array([.75, .05, -.62]); Lf /= np.linalg.norm(Lf)
    V = np.array([0, 0, -1.0])
    ndl = n @ Lk
    # oclusión ambiental
    occ, sca = 0, 1.0
    for k in range(1, 6):
        hh = .025 * k
        occ = occ + (hh - sdf(po + nobj * hh)) * sca
        sca *= .75
    ao = np.clip(1 - 4.2 * occ, 0, 1)
    # sombra suave hacia la luz principal
    Lo = Lk @ Rm
    res = np.ones(len(idx))
    tt = np.full(len(idx), .03)
    for _ in range(28):
        d = sdf(po + nobj * .012 + Lo * tt[:, None])
        res = np.minimum(res, 9 * d / tt)
        tt += np.clip(d, .02, .15)
    shadow = np.clip(res, 0, 1) ** 1.2
    # color base
    if kind == "pop":
        base = np.array([.87, .76, .54])
        butter = np.array([.72, .42, .10])
        wob = .5 + .5 * np.sin(po @ np.array([5.3, 3.1, 4.7]) + seed) * np.sin(po @ np.array([-2.9, 6.1, 1.7]))
        tint = np.clip((1 - ao) * 1.5 + wob * .3, 0, 1)[:, None]
        alb = base * (1 - tint * .8) + butter * tint * .8
        hull_alb = np.array([.42, .20, .04]) * (.75 + .45 * wob[:, None])
        alb = np.where(is_hull[:, None], hull_alb, alb)
    else:
        wob = .5 + .5 * np.sin(po @ np.array([3.1, 7.3, 2.2]))
        alb = np.array([.60, .24, .02]) * (.8 + .35 * wob[:, None])
        germ = (po[:, 2] < -.10) & (po[:, 1] < .10) & (np.abs(po[:, 0]) < .2)
        alb = np.where(germ[:, None], np.array([.85, .68, .30]), alb)
    wrap = .28 if kind == "pop" else .1
    diff = np.clip((ndl + wrap) / (1 + wrap), 0, 1)[:, None]
    key = np.array([1.0, .91, .78]) * 2.15
    fill = np.array([.75, .82, 1.0]) * .36 * np.clip(n @ Lf * .5 + .5, 0, 1)[:, None]
    sky = np.array([.95, .95, 1.0]) * .30 * (.5 + .5 * n[:, 1:2])
    col = alb * (key * diff * shadow[:, None] + (fill + sky) * ao[:, None])
    # translucidez en bordes finos
    fres = (1 - np.clip(n @ -V, 0, 1)) ** 2
    if kind == "pop":
        col += np.array([1.0, .85, .6]) * (.22 * fres * ao)[:, None] * ~is_hull[:, None]
    # especular (mate en el pochoclo, brillante en la cascarita y el grano)
    Hk = (Lk + -V)
    Hk /= np.linalg.norm(Hk)
    nh = np.clip(n @ Hk, 0, 1)
    glossy = is_hull if kind == "pop" else np.ones(len(idx), bool)
    spec = np.where(glossy, .9 * nh ** 70, .05 * nh ** 10) * shadow
    col += spec[:, None] * np.array([1, .97, .9])
    rgb = aces(col) ** (1 / 2.2)
    img = np.zeros((s * s, 4))
    flat = np.where(m.ravel())[0][idx]
    img[flat, :3] = rgb
    img[flat, 3] = 1
    img = img.reshape(s, s, 4)
    # reducción con premultiplicado (bordes suaves)
    img[..., :3] *= img[..., 3:]
    img = img.reshape(SIZE, SS, SIZE, SS, 4).mean((1, 3))
    a = img[..., 3:]
    img[..., :3] = np.where(a > 0, img[..., :3] / np.maximum(a, 1e-6), 0)
    return (np.clip(img, 0, 1) * 255).astype(np.uint8)


def sheet(fields, seed, kind="pop"):
    r = np.random.default_rng(seed + 100)
    R0 = rand_rot(r)
    axis = r.normal(size=3)
    frames = [render(*fields, axis_rot(axis, 2 * np.pi * f / FRAMES) @ R0, kind, seed) for f in range(FRAMES)]
    return Image.fromarray(np.concatenate(frames, 1), "RGBA")


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "test":
        f = popcorn_fields(int(sys.argv[2]) if len(sys.argv) > 2 else 1)
        r = np.random.default_rng(5)
        ims = [render(*f, rand_rot(r)) for _ in range(4)]
        im = Image.fromarray(np.concatenate(ims, 1), "RGBA")
        bg = Image.new("RGBA", im.size, (241, 226, 193, 255))
        bg.alpha_composite(im)
        out = ROOT / "output" / "preview"
        out.mkdir(parents=True, exist_ok=True)
        bg.save(out / "popcorn_test.png")
        print("ok")
    else:
        d = ROOT / "assets" / "pop"
        d.mkdir(parents=True, exist_ok=True)
        ids = range(10) if len(sys.argv) < 3 else [int(x) for x in sys.argv[2:] if x != "k"]
        for i in ids:
            sheet(popcorn_fields(11 + i * 7), i).save(d / f"pop_{i:02d}.webp", quality=92, method=6)
            print("pop", i, flush=True)
        if len(sys.argv) < 3 or "k" in sys.argv:
            sheet(kernel_fields(), 99, "kernel").save(d / "kernel.webp", quality=92, method=6)
        print("ok")
