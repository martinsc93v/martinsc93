"""Coreografía de los pochoclos 3D del reel (fuente única para el video y el audio).

Genera src/popdata.js (window.POPDATA) con todas las partículas y expone build() para audio.py,
que usa los mismos tiempos para que cada estallido suene en el cuadro exacto.
Coordenadas en px del cuadro 1080x1920, tiempos en segundos.
"""
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
META = json.loads((HERE.parent / "assets" / "bucket_meta.json").read_text())

# ubicación del balde en la escena 1 (misma que usa reel.html)
BUCKET = {"left": 575, "top": 1175, "width": 470}
K = BUCKET["width"] / META["w"]
MOUTH_X = BUCKET["left"] + META["mouth"][0] * K
MOUTH_Y = BUCKET["top"] + META["top"][1] * K + 20
MOUTH_R = META["mouth_r"] * K


def build():
    r = np.random.default_rng(1234)
    P, sounds = [], []

    def piece(layer, t0, x, y, vx, vy, size, g=2600, life=2.2, pop=False, blur=0, grow=0, kernel=False, shadow=True, puff=False):
        P.append({"l": layer, "t0": round(t0, 4), "x": round(x, 1), "y": round(y, 1), "vx": round(vx, 1), "vy": round(vy, 1),
                  "g": g, "s": round(size, 1), "v": -1 if kernel else int(r.integers(10)), "f0": float(r.uniform(0, 16)),
                  "fps": float(r.uniform(14, 30) * r.choice([-1, 1])), "r0": float(r.uniform(-25, 25)), "vr": float(r.uniform(-70, 70)),
                  "life": life, "pop": pop, "blur": blur, "grow": grow, "sh": shadow, "puff": puff})

    def burst(t, cx, cy, n, spread_x, spread_y, a0, a1, v0, v1, s0, s1, layer="f", kernels=0, snd=True):
        for i in range(n):
            a = np.radians(r.uniform(a0, a1))
            v = r.uniform(v0, v1)
            tt = t + r.uniform(0, .07)
            piece(layer, tt, cx + r.uniform(-spread_x, spread_x), cy + r.uniform(-spread_y, spread_y),
                  np.cos(a) * v, np.sin(a) * v, r.uniform(s0, s1), pop=True)
            if snd and i % 2 == 0:
                sounds.append(tt)
        for _ in range(kernels):
            a = np.radians(r.uniform(a0, a1))
            v = r.uniform(v0, v1) * .8
            piece(layer, t + r.uniform(0, .06), cx + r.uniform(-spread_x, spread_x), cy, np.cos(a) * v, np.sin(a) * v,
                  r.uniform(26, 36), kernel=True)

    # --- gancho: pochoclos gigantes pasando frente a la cámara (desenfocados)
    for (x, y, vx, vy, s) in [(-40, 1500, 520, -1500, 380), (1120, 1650, -600, -1700, 430), (980, 420, 700, -900, 300),
                              (80, 360, -500, -1000, 280), (1150, 980, -300, -1200, 340)]:
        piece("f", 0.0, x, y, vx, vy, s, g=900, life=1.1, blur=9, grow=.35, shadow=False)
    # --- gancho: pochoclos que revientan y saltan del balde
    tt = 1.45
    while tt < 2.9:
        x = MOUTH_X + r.uniform(-.55, .55) * MOUTH_R
        piece("f", tt, x, MOUTH_Y, r.uniform(-260, 260) + (x - MOUTH_X) * 1.2, -r.uniform(950, 1350), r.uniform(72, 100), life=1.6, pop=True, puff=True)
        sounds.append(tt)
        tt += r.uniform(.07, .16)
    # --- apertura de la bóveda: explosión grande
    burst(10.08, 540, 1020, 70, 60, 60, 0, 360, 700, 2300, 60, 140, kernels=8)
    for i in range(6):                     # hacia la cámara
        a = np.radians(r.uniform(0, 360))
        piece("f", 10.1 + i * .03, 540, 1020, np.cos(a) * 900, np.sin(a) * 900, 120, g=600, life=.9, blur=4, grow=3.2, pop=True, shadow=False)
    # --- "MÁS CINE."
    burst(14.9, 130, 1150, 10, 30, 80, -175, -110, 800, 1500, 60, 110)
    burst(14.9, 950, 1150, 10, 30, 80, -70, -5, 800, 1500, 60, 110)
    # --- ticket del precio
    burst(17.25, 150, 1190, 12, 30, 60, -175, -110, 800, 1500, 60, 110)
    burst(17.25, 930, 1190, 12, 30, 60, -70, -5, 800, 1500, 60, 110)
    # --- TELEGRAM
    burst(20.85, 540, 985, 14, 380, 8, -160, -20, 800, 1500, 60, 110, kernels=3)
    burst(20.85, 110, 1110, 5, 10, 60, -175, -120, 800, 1400, 60, 105)
    burst(20.85, 970, 1110, 5, 10, 60, -60, -5, 800, 1400, 60, 105)
    # --- lluvia suave de fondo en el cierre
    for i in range(10):
        piece("b", 22.4 + i * .16, r.uniform(120, 960), -120, r.uniform(-40, 40), r.uniform(150, 300), r.uniform(50, 80), g=700, life=2.5)
    return {"bucket": BUCKET, "p": P}, sorted(sounds)


if __name__ == "__main__":
    data, sounds = build()
    (HERE / "popdata.js").write_text("window.POPDATA = " + json.dumps(data, separators=(",", ":")) + ";\n")
    print("ok", len(data["p"]), "pochoclos,", len(sounds), "estallidos con sonido")
