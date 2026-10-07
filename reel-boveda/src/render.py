"""Renderiza reel.html cuadro por cuadro con Chromium (Playwright) y lo codifica con ffmpeg.

Uso:
  python3 render.py preview 0.2 2.4 ...   -> PNGs sueltos + hoja de contactos en output/preview/
  python3 render.py video                 -> output/_video_mudo_raw.mp4 (sin audio, 1080x1920, 30 fps)
"""
import os
import subprocess
import sys
from pathlib import Path

import imageio_ffmpeg
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
HTML = ROOT / "src" / "reel.html"
OUT = ROOT / "output"
FPS, DUR = 30, 24
CHROMIUM = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"


def open_page(p):
    browser = p.chromium.launch(executable_path=CHROMIUM if os.path.exists(CHROMIUM) else None, args=["--allow-file-access-from-files", "--force-color-profile=srgb"])
    page = browser.new_page(viewport={"width": 1080, "height": 1920}, device_scale_factor=1)
    page.goto(HTML.as_uri())
    page.wait_for_function("window.READY === true", timeout=120_000)
    return browser, page


def frame(page, t):
    page.evaluate(f"render({t})")
    return page.screenshot(type="png", clip={"x": 0, "y": 0, "width": 1080, "height": 1920})


def preview(times):
    from PIL import Image
    d = OUT / "preview"
    d.mkdir(parents=True, exist_ok=True)
    shots = []
    with sync_playwright() as p:
        browser, page = open_page(p)
        for t in times:
            f = d / f"t{t:05.2f}.png"
            f.write_bytes(frame(page, t))
            shots.append(f)
        browser.close()
    cols = min(5, len(shots))
    rows = (len(shots) + cols - 1) // cols
    w, h = 270, 480
    sheet = Image.new("RGB", (cols * (w + 8), rows * (h + 8)), "#ff00ff")
    for i, f in enumerate(shots):
        sheet.paste(Image.open(f).convert("RGB").resize((w, h), Image.LANCZOS), ((i % cols) * (w + 8), (i // cols) * (h + 8)))
    sheet.save(d / "sheet.png")
    print("ok", d / "sheet.png")


def video():
    OUT.mkdir(exist_ok=True)
    dst = OUT / "_video_mudo_raw.mp4"
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    cmd = [ff, "-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", str(FPS), "-c:v", "png", "-i", "-",
           "-c:v", "libx264", "-preset", "slow", "-crf", "12", "-pix_fmt", "yuv420p", "-r", str(FPS), str(dst)]
    enc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    with sync_playwright() as p:
        browser, page = open_page(p)
        n = FPS * DUR
        for i in range(n):
            enc.stdin.write(frame(page, i / FPS))
            if i % 60 == 0:
                print(f"cuadro {i}/{n}", flush=True)
        browser.close()
    enc.stdin.close()
    enc.wait()
    print("ok", dst)


def cover(t=2.5):
    from io import BytesIO

    from PIL import Image
    with sync_playwright() as p:
        browser, page = open_page(p)
        page.evaluate("window.NO_DUST = true")
        png = frame(page, t)
        browser.close()
    Image.open(BytesIO(png)).convert("RGB").save(OUT / "portada-boveda.jpg", quality=95)
    print("ok", OUT / "portada-boveda.jpg")


if __name__ == "__main__":
    if sys.argv[1] == "preview":
        preview([float(x) for x in sys.argv[2:]])
    elif sys.argv[1] == "cover":
        cover()
    else:
        video()
