# Plantilla de reels "pelis 10/10" · @elpochoclos

Replica la fórmula de los edits de recomendación: gancho de ~4 s y después cada peli en 4 planos cortados en los golpes de la canción, con el título grande con brillo y "DIRECTOR | AÑO" abajo. Cierra con @elpochoclos, "¿Cuál agregarías?" (para sumar comentarios) y "Seguime para la pt. 2".

Formato: 1080×1920, 30 fps. Exporta una versión con la canción y otra muda.

## Parte 1 · Pelis argentas 10/10

| Orden | Peli | Crédito en pantalla | Color del título |
|---|---|---|---|
| 1 | Nueve reinas | FABIÁN BIELINSKY \| 2000 | verde |
| 2 | El secreto de sus ojos | JUAN JOSÉ CAMPANELLA \| 2009 | dorado |
| 3 | Relatos salvajes | DAMIÁN SZIFRON \| 2014 | rojo |
| 4 | La historia oficial | LUIS PUENZO \| 1985 | crema |
| 5 | Argentina, 1985 | SANTIAGO MITRE \| 2022 | celeste |

## Cómo armar cada parte

1. Poné un clip por peli en `clips/` con el nombre del `file` de `config.json`. Sirve el tráiler oficial, idealmente en 1080p.
2. Poné la canción en `audio/cancion.mp3`. En `song.start` va el segundo desde donde arranca el reel.
3. Elegí los planos:
   ```bash
   cd src
   python3 shots.py clips/nueve-reinas.mp4   # hoja de contactos con el segundo de cada plano
   ```
   En `config.json` va cada plano como `{"start": 12.4, "focus": 0.5}`. `focus` corre el encuadre vertical de izquierda (0) a derecha (1). Para un plano abierto que no conviene recortar va `"fit": true` (cuadro completo sobre fondo desenfocado). Si una peli no tiene planos elegidos, la plantilla toma 4 repartidos.
4. Renderizá:
   ```bash
   python3 edit.py --preview 2 6 10   # cuadros sueltos para revisar
   python3 edit.py                    # reel completo -> output/
   python3 edit.py --test             # prueba con material generado (no necesita clips ni canción)
   ```

La duración de cada plano sale del tempo de la canción: si el tema va a ~144 BPM, cada plano dura 2 golpes (~0,83 s, como en la referencia).

## Archivos

- `config.json`: textos del gancho, pelis, colores, planos, canción y cierre.
- `src/timeline.py`: detecta los golpes de la canción y arma la línea de tiempo.
- `src/overlay.html`: títulos animados (capa transparente).
- `src/edit.py`: encuadre vertical, look (contraste, color, viñeta, grano), cortes, títulos y exportación.
- `src/shots.py`: hoja de contactos de planos de un clip.

Los clips y la canción no se suben al repo (`.gitignore`).
