# Proyectos de @elpochoclos

| Carpeta | Qué es |
|---|---|
| `reel-elpochoclos/` | Reel promo de la cuenta (tráiler de 20 s) |
| `reel-boveda/` | Reel de venta de La Bóveda Pochoclera (24 s, pochoclos 3D y balde realista) |
| `carrusel-boveda/` | Carrusel fijado de La Bóveda (8 placas 1080×1350) |
| `reel-pelis-argentas/` | Plantilla "pelis 10/10" con cortes al ritmo (parte 1 configurada, faltan clips y canción) |
| `reel-netflix/` | **Plantilla "reel netflix"**: 5 pelis con logo de Netflix, cortes al ritmo y cierre con pochoclos 3D |

Cada carpeta tiene su propio README con los pasos para volver a renderizar.

## Instalación en tu compu (una sola vez)

1. Instalá Python 3.11 o más nuevo desde python.org (en Windows, tildá "Add Python to PATH").
2. En una terminal, dentro de esta carpeta:
   ```bash
   pip install playwright pillow numpy scipy imageio-ffmpeg librosa
   python -m playwright install chromium
   ```
   ffmpeg viene incluido con `imageio-ffmpeg`, no hace falta instalarlo aparte.

En Windows usá `python` donde los README dicen `python3`.

## Hacer un nuevo "reel netflix"

1. Copiá la carpeta `reel-netflix` con otro nombre.
2. Poné los 5 tráilers en `clips/` (el zip no los trae: son los que tenés en `OneDrive\El Pochoclos\reels`, renombrados como dice `config.json`).
3. En `config.json` cambiá títulos, directores, años, colores y archivos. Para elegir planos:
   `cd src` y después `python shots.py clips/nombre.mp4` (genera una hoja de contactos en `output/planos/`).
4. Si los tráilers tienen franjas negras, ajustá `crop` de cada peli (`[ancho, alto, x, y]`).
5. Música: `python beat.py` genera el beat original; o poné tu canción en `audio/` y cambiá `song.file` y `song.start`.
6. `python edit.py --preview 2 6 10` para revisar cuadros sueltos y `python edit.py` para el reel completo
   (sale en `output/netflix-con-audio.mp4`, `netflix-mudo.mp4` y `netflix-portada.jpg`).

## Qué no viene en el zip

- Los videos finales ya renderizados (ya los tenés de la sesión) y los archivos intermedios: se regeneran con los scripts.
- Los tráilers de `reel-netflix/clips/` (88 MB): usá los tuyos.
- El beat de `reel-netflix/audio/beat.wav`: se regenera con `python beat.py` dentro de `reel-netflix/src`.
- `.git`: el historial completo está en GitHub, rama `ccr-3aa586de-24up3f` del repo `martinsc93v/martinsc93`.

## Estado al cerrar la sesión

El cierre del reel Netflix ya tiene el fondo de pochoclos 3D (montaña, lluvia y estallido detrás del logo) en `reel-netflix/src/overlay.html`, probado con cuadros sueltos. Falta renderizar el reel completo con ese cierre: `python edit.py` dentro de `reel-netflix/src`.
