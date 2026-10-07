"""Detecta los golpes de la canción y arma la línea de tiempo del reel (en qué cuadro va cada corte).

Uso: python3 timeline.py  -> output/timeline.json (y muestra el tempo detectado)
"""
import json
import sys
from pathlib import Path

import librosa
import numpy as np

ROOT = Path(__file__).resolve().parent.parent


def load_config():
    return json.loads((ROOT / "config.json").read_text())


def detect_beats(cfg):
    song = ROOT / cfg["song"]["file"]
    y, sr = librosa.load(song, sr=22050, offset=cfg["song"]["start"], duration=75, mono=True)
    tempo, beats = librosa.beat.beat_track(y=y, sr=sr, units="time", tightness=120)
    tempo = float(np.atleast_1d(tempo)[0])
    return tempo, np.asarray(beats, float)


def build(cfg):
    fps = cfg["fps"]
    tempo, beats = detect_beats(cfg)
    period = float(np.median(np.diff(beats)))
    bps = max(1, int(round(cfg["shot_seconds"] / period)))         # golpes por plano
    hook_beats = max(bps * 2, int(round(cfg["hook"]["seconds"] / period / bps)) * bps)
    film_beats = bps * cfg["shots_per_film"]
    outro_beats = max(2, int(round(cfg["outro"]["seconds"] / period)))
    need = hook_beats + film_beats * len(cfg["films"]) + outro_beats + 1
    if len(beats) < need:                                           # si la canción es corta, extiendo la grilla
        extra = beats[-1] + period * np.arange(1, need - len(beats) + 1)
        beats = np.concatenate([beats, extra])
    t0 = beats[0]
    bf = [int(round((b - t0) * fps)) for b in beats[:need]]          # golpes en cuadros, el reel arranca en el primero

    tl = {"fps": fps, "tempo": round(tempo, 1), "beats_per_shot": bps, "audio_offset": cfg["song"]["start"] + float(t0),
          "beat_frames": bf, "segments": []}
    i = 0
    hook_shots = cfg["hook"]["shots"] or [{}]
    per = hook_beats // len(hook_shots)
    cuts = [bf[i + k * per] for k in range(len(hook_shots))]
    tl["segments"].append({"kind": "hook", "f0": bf[i], "f1": bf[i + hook_beats], "cuts": cuts,
                           "beats": bf[i:i + hook_beats + 1]})
    i += hook_beats
    for film in cfg["films"]:
        cuts = [bf[i + k * bps] for k in range(cfg["shots_per_film"])]
        tl["segments"].append({"kind": "film", "id": film["id"], "f0": bf[i], "f1": bf[i + film_beats], "cuts": cuts,
                               "beats": bf[i:i + film_beats + 1]})
        i += film_beats
    tl["segments"].append({"kind": "outro", "f0": bf[i], "f1": bf[i + outro_beats], "cuts": [bf[i]], "beats": bf[i:i + outro_beats + 1]})
    tl["total_frames"] = bf[i + outro_beats]
    return tl


if __name__ == "__main__":
    cfg = load_config()
    tl = build(cfg)
    (ROOT / "output").mkdir(exist_ok=True)
    (ROOT / "output" / "timeline.json").write_text(json.dumps(tl, indent=1))
    print(f"tempo {tl['tempo']} BPM · {tl['beats_per_shot']} golpe(s) por plano · duración {tl['total_frames'] / tl['fps']:.2f} s")
    for s in tl["segments"]:
        print(f"  {s['kind']:6s} {s.get('id', ''):24s} {s['f0'] / 30:6.2f}s → {s['f1'] / 30:6.2f}s")
    sys.exit(0)
