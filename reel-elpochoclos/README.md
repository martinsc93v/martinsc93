# Reel promocional · @elpochoclos

Reel vertical de 20 s (1080×1920, 30 fps) en formato de tráiler de cine.

## Archivos finales (`output/`)

| Archivo | Uso |
|---|---|
| `elpochoclos-reel-con-audio.mp4` | Con banda sonora original sintetizada (sin derechos), normalizada a -14 LUFS |
| `elpochoclos-reel-mudo.mp4` | Sin audio, para sumarle un audio en tendencia desde Instagram |
| `portada-reel.jpg` | Portada sugerida (la banda verde); el recorte 4:5 del perfil queda centrado |

## Guion

| Tiempo | Escena |
|---|---|
| 0,0–1,5 s | Cola de proyección 3-2-1 · "El Pochoclos presenta un avance" |
| 1,5–3,5 s | Banda verde: "Todo público con conciencia social" · ATP |
| 3,5–5,5 s | "En un país donde quieren apagar la pantalla" + apagado de tele |
| 5,5–7,5 s | Proyector: "Pero acá el proyector sigue prendido" |
| 7,5–9,5 s | Tiras de fílmico con portadas · Cine argento / Terror / Drama / Memoria |
| 9,5–11,5 s | Cortes rápidos de portadas |
| 11,5–15 s | Laureles: 77,8 mil seguidorxs · 488,7 mil visualizaciones en 30 días · 344 mil vistas en un solo post |
| 15–17 s | Bandera: "Militando la conciencia social desde el cine" |
| 17–20 s | Logo + @elpochoclos + botón Seguir → Siguiendo |

Los números salen de las capturas del perfil del 29/09/2026.

## Volver a renderizar

```bash
pip install playwright pillow numpy scipy imageio-ffmpeg
cd src
python3 audio.py          # banda sonora -> output/_audio_raw.wav
python3 render.py video   # cuadros con Chromium -> output/_video_mudo_raw.mp4
python3 render.py cover   # portada
python3 build.py          # exporta las dos versiones finales
python3 render.py preview 2.4 8.2 17.6   # cuadros sueltos para revisar
```

Los textos, tiempos y colores están en `src/reel.html`. Los eventos de sonido están en `src/audio.py`, sincronizados con esos mismos tiempos.
