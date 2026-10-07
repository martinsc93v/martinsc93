"""Renderiza el panorama del carrusel (8640x1350) y lo corta en 8 placas de 1080x1350.

Uso: python3 render_carrusel.py  -> output/placa-01.jpg ... placa-08.jpg + output/vista-completa.jpg
"""
import os
from io import BytesIO
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "output"
N, W, H = 8, 1080, 1350
CHROMIUM = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"

OUT.mkdir(exist_ok=True)
with sync_playwright() as p:
    b = p.chromium.launch(executable_path=CHROMIUM if os.path.exists(CHROMIUM) else None, args=["--allow-file-access-from-files", "--force-color-profile=srgb"])
    page = b.new_page(viewport={"width": W * N, "height": H}, device_scale_factor=1)
    page.goto((ROOT / "src" / "carrusel.html").as_uri())
    page.wait_for_function("window.READY === true", timeout=120_000)
    pano = Image.open(BytesIO(page.screenshot(type="png"))).convert("RGB")
    b.close()

for i in range(N):
    pano.crop((i * W, 0, (i + 1) * W, H)).save(OUT / f"placa-{i + 1:02d}.jpg", quality=95, subsampling=0)
# vista completa para revisar la continuidad entre placas
gap = 16
view = Image.new("RGB", (N * W + (N - 1) * gap, H), (255, 255, 255))
for i in range(N):
    view.paste(pano.crop((i * W, 0, (i + 1) * W, H)), (i * (W + gap), 0))
view.resize((view.width // 4, H // 4), Image.LANCZOS).save(OUT / "vista-completa.jpg", quality=90)
print("ok")
