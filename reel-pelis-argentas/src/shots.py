"""Hoja de contactos de los planos de un clip, para elegir cuáles van al reel.

Detecta los cortes de escena y guarda una miniatura por plano con su segundo de inicio y su duración.
Uso: python3 shots.py clips/nueve-reinas.mp4 [umbral]  -> output/planos/nueve-reinas.jpg y .json
"""
import json
import re
import subprocess
import sys
from pathlib import Path

import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
FF = imageio_ffmpeg.get_ffmpeg_exe()


def duration(path):
    err = subprocess.run([FF, "-hide_banner", "-i", str(path)], capture_output=True, text=True).stderr
    h, m, s = re.search(r"Duration: (\d+):(\d+):([\d.]+)", err).groups()
    return int(h) * 3600 + int(m) * 60 + float(s)


def scenes(path, thr):
    err = subprocess.run([FF, "-hide_banner", "-i", str(path), "-vf", f"select='gt(scene,{thr})',showinfo", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    cuts = [0.0] + [float(x) for x in re.findall(r"pts_time:([\d.]+)", err)] + [duration(path)]
    return [(a, b) for a, b in zip(cuts, cuts[1:]) if b - a >= .5]


def thumb(path, t):
    out = subprocess.run([FF, "-hide_banner", "-loglevel", "error", "-ss", f"{t:.2f}", "-i", str(path), "-frames:v", "1",
                          "-vf", "scale=320:-2", "-f", "image2pipe", "-vcodec", "png", "-"], capture_output=True).stdout
    from io import BytesIO
    return Image.open(BytesIO(out)).convert("RGB")


if __name__ == "__main__":
    path = ROOT / sys.argv[1]
    thr = float(sys.argv[2]) if len(sys.argv) > 2 else .3
    sc = scenes(path, thr)
    ims = []
    font = ImageFont.load_default(size=22)
    for i, (a, b) in enumerate(sc):
        im = thumb(path, a + min(.4, (b - a) / 2))
        d = ImageDraw.Draw(im)
        d.rectangle([0, 0, 200, 30], fill=(0, 0, 0))
        d.text((6, 3), f"#{i} {a:.1f}s ({b - a:.1f}s)", fill=(255, 220, 80), font=font)
        ims.append(im)
    cols = 6
    w, h = ims[0].size
    sheet = Image.new("RGB", (cols * (w + 6), ((len(ims) + cols - 1) // cols) * (h + 6)), (255, 0, 255))
    for i, im in enumerate(ims):
        sheet.paste(im, ((i % cols) * (w + 6), (i // cols) * (h + 6)))
    out = ROOT / "output" / "planos"
    out.mkdir(parents=True, exist_ok=True)
    sheet.save(out / f"{path.stem}.jpg", quality=88)
    (out / f"{path.stem}.json").write_text(json.dumps([{"n": i, "start": round(a, 2), "dur": round(b - a, 2)} for i, (a, b) in enumerate(sc)], indent=1))
    print(f"{len(sc)} planos ->", out / f"{path.stem}.jpg")
