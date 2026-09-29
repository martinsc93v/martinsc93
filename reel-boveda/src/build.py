"""Exporta las versiones finales a partir del render crudo y del audio.

  output/boveda-reel-con-audio.mp4  -> H.264 + AAC, audio normalizado a -14 LUFS
  output/boveda-reel-mudo.mp4       -> H.264 sin pista de audio (para sumar un audio en tendencia desde Instagram)
  output/portada-boveda.jpg                -> portada 1080x1920 (el recorte 4:5 del perfil queda centrado)
"""
import json
import re
import subprocess
from pathlib import Path

import imageio_ffmpeg

OUT = Path(__file__).resolve().parent.parent / "output"
FF = imageio_ffmpeg.get_ffmpeg_exe()
RAW_V, RAW_A = OUT / "_video_mudo_raw.mp4", OUT / "_audio_raw.wav"

# 9 Mbps en dos pasadas: cada MP4 queda por debajo de 30 MB (Instagram lo recomprime igual a ~3-5 Mbps)
VIDEO = ["-c:v", "libx264", "-preset", "slow", "-b:v", "9000k", "-maxrate", "12M", "-bufsize", "18M",
         "-profile:v", "high", "-level", "4.2", "-pix_fmt", "yuv420p", "-r", "30", "-g", "30",
         "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", "-movflags", "+faststart"]


def run(args):
    return subprocess.run([FF, "-hide_banner", "-y", *args], check=True, capture_output=True, text=True)


# loudnorm en dos pasadas (modo lineal: no comprime, sólo ajusta ganancia)
target = "I=-14:TP=-1.0:LRA=11"
meas = run(["-i", str(RAW_A), "-af", f"loudnorm={target}:print_format=json", "-f", "null", "-"]).stderr
m = json.loads(re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", meas, re.S).group(0))
af = (f"loudnorm={target}:measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}"
      f":measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true,aresample=48000")

PASS = str(OUT / "_x264pass")
run(["-i", str(RAW_V), "-an", *VIDEO, "-pass", "1", "-passlogfile", PASS, "-f", "mp4", "/dev/null"])
run(["-i", str(RAW_V), "-an", *VIDEO, "-pass", "2", "-passlogfile", PASS, str(OUT / "boveda-reel-mudo.mp4")])
run(["-i", str(RAW_V), "-i", str(RAW_A), "-map", "0:v", "-map", "1:a", *VIDEO, "-pass", "2", "-passlogfile", PASS,
     "-af", af, "-c:a", "aac", "-b:a", "320k", "-ar", "48000", "-shortest", str(OUT / "boveda-reel-con-audio.mp4")])
print("ok")
