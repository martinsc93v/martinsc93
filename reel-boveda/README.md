# Reel de venta · La Bóveda Pochoclera

Reel vertical de 24 s (1080×1920, 30 fps) con la estética de las placas de la Bóveda: papel envejecido, rojo y crema, y tinta gastada.

## Archivos finales (`output/`)

| Archivo | Uso |
|---|---|
| `boveda-reel-con-audio.mp4` | Con groove retro original sintetizado (sin derechos), normalizado a -14 LUFS |
| `boveda-reel-mudo.mp4` | Sin audio, para sumarle un audio en tendencia desde Instagram |
| `portada-boveda.jpg` | Portada sugerida: el gancho "¿Nunca sabés qué ver?" (en el recorte 4:5 del perfil se lee entero) |

## Guion (estructura problema → agitación → solución → oferta → acción)

| Tiempo | Escena |
|---|---|
| 0–3 s | Gancho: "¿NUNCA SABÉS QUÉ VER?" + celu scrolleando, balde y rollo |
| 3–4,8 s | "Tenés mil plataformas, mil listas y mil recomendaciones sueltas…" y las tarjetas se acumulan |
| 4,8–6,6 s | Se hace de noche: "…terminás scrolleando media hora" con cronómetro 00:00 → 30:00 |
| 6,6–8,6 s | "El problema no es falta de cine. Es falta de orden." y el caos se ordena en grilla |
| 8,6–11,8 s | La bóveda gira, se abre y revela La Bóveda Pochoclera, un canal de Telegram |
| 11,8–16 s | "Acá está todo curado y ordenado": Películas / Series / Estrenos / Clásicos / Subtitulado + "Menos búsqueda. Más cine." |
| 16–20 s | "Acceso único", ticket de $6000 pago único, sin suscripción, entrás una vez, acceso a la bóveda |
| 20–24 s | "¿Querés más info? Comentá la palabra TELEGRAM y te paso todo" + comentario tipeándose y flecha al botón de comentarios |

## Volver a renderizar

```bash
pip install playwright pillow numpy scipy imageio-ffmpeg
cd src
python3 assets.py <logo_fondo_crema.png> <logo_fondo_rojo.png>   # texturas y recorte de logos
python3 audio.py
python3 render.py video
python3 render.py cover
python3 build.py
```
