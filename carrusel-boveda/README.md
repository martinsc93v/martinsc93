# Carrusel fijado · La Bóveda Pochoclera

Carrusel de 8 placas (1080×1350, 4:5) para fijar en el perfil. Es un panorama continuo: el papel, las reglas del marco, las pinceladas, el avioncito y los pochoclos 3D cruzan de una placa a la siguiente para invitar a deslizar. El marco sólo se cierra en la primera y la última placa.

## Placas (`output/placa-01.jpg` … `placa-08.jpg`)

| # | Rol | Contenido |
|---|---|---|
| 1 | Gancho (portada) | "¿NUNCA SABÉS QUÉ VER?", balde realista, "La Bóveda Pochoclera: un canal de Telegram con todo el cine curado y ordenado", botón DESLIZÁ |
| 2 | Dolor (segundo gancho: Instagram la muestra a quien no deslizó) | "Tenés mil plataformas, mil listas y mil recomendaciones sueltas…" + panel nocturno con cronómetro 30:00 |
| 3 | Giro | "El problema no es falta de cine. Es falta de orden." Caos de tarjetas → grilla ordenada |
| 4 | Solución | La bóveda abierta, logo, "Un canal de Telegram", "pensado para tener cine ordenado, actualizado y fácil de encontrar" |
| 5 | Qué hay | "Acá está todo curado y ordenado": Películas / Series / Estrenos / Clásicos / Subtitulado + ficha de catálogo + "Menos búsqueda. Más cine." |
| 6 | Cómo entrás | 1. Comentá TELEGRAM · 2. Te paso todo · 3. Pago único y listo |
| 7 | Oferta | Acceso único $6000, pago único, sin suscripción, entrás una vez, acceso a la bóveda + "Curado por El Pochoclos" |
| 8 | Acción | "¿Querés más info? Comentá la palabra TELEGRAM y te paso todo" + flecha al botón de comentarios + "Guardá este post" |

`output/vista-completa.jpg` muestra las 8 placas juntas para revisar la continuidad.

## Volver a renderizar

Usa los recursos del reel (`../reel-boveda/assets`: tipografías, logos, pinceladas, balde y pochoclos 3D).

```bash
cd src
python3 assets_carrusel.py    # papel y desgaste de tinta panorámicos
python3 render_carrusel.py    # renderiza el panorama y lo corta en 8 placas
```
