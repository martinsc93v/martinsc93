"""Editor del reel "pelis 10/10": corta los planos en los golpes de la canción, los encuadra en vertical,
les aplica el mismo look, superpone los títulos animados y exporta.

Uso:
  python3 edit.py            -> output/pelis-argentas-con-audio.mp4, pelis-argentas-mudo.mp4, portada.jpg
  python3 edit.py --test     -> lo mismo con clips y canción de prueba generados (para probar la plantilla)
  python3 edit.py --preview 3.2 10 18   -> cuadros sueltos en output/preview/
"""
import os
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter

import timeline

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "output"
FF = imageio_ffmpeg.get_ffmpeg_exe()
W, H = 1080, 1920
CHROMIUM = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
rng = np.random.default_rng(3)


def run(args):
    return subprocess.run([FF, "-hide_banner", "-y", *args], check=True, capture_output=True, text=True)


# ------------------------------------------------------------------ material de prueba
def make_test_material(cfg):
    d = ROOT / "clips" / "_prueba"
    d.mkdir(parents=True, exist_ok=True)
    for i, film in enumerate(cfg["films"]):
        film["file"] = f"clips/_prueba/{film['id']}.mp4"
        if not (ROOT / film["file"]).exists():
            run(["-f", "lavfi", "-i", "testsrc2=s=1920x1080:r=30:d=12", "-vf", f"hue=h={i * 70}:s=1.4,eq=contrast=1.1",
                 "-c:v", "libx264", "-pix_fmt", "yuv420p", str(ROOT / film["file"])])
    from scipy.io import wavfile
    sr, bpm, dur = 44100, 144, 40
    t = np.arange(int(sr * dur)) / sr
    y = np.zeros_like(t)
    beat = 60 / bpm
    for k in range(int(dur / beat)):
        i = int(k * beat * sr)
        n = min(int(.3 * sr), len(t) - i)
        tt = np.arange(n) / sr
        y[i:i + n] += np.sin(2 * np.pi * np.cumsum(50 + 120 * np.exp(-tt / .03)) / sr) * np.exp(-tt / .2) * (1 if k % 4 == 0 else .7)
        j = i + int(beat / 2 * sr)
        if j + 2000 < len(t):
            y[j:j + 2000] += rng.standard_normal(2000) * np.exp(-np.arange(2000) / 300) * .15
    wavfile.write(ROOT / "audio" / "_prueba.wav", sr, (y / np.abs(y).max() * .8).astype(np.float32))
    cfg["song"] = {"file": "audio/_prueba.wav", "start": 0.0}
    cfg["hook"]["shots"] = [{"film": cfg["films"][-1]["id"], "start": 1.0, "focus": .5}]
    return cfg


def auto_shots(path, n):
    """Si no se eligieron planos a mano: toma n planos repartidos a lo largo del clip (evita el principio y el final)."""
    meta = subprocess.run([FF, "-hide_banner", "-i", str(path)], capture_output=True, text=True).stderr
    dur = sum(float(x) * m for x, m in zip(re.search(r"Duration: (\d+):(\d+):([\d.]+)", meta).groups(), (3600, 60, 1)))
    return [{"start": round(dur * (.12 + .76 * k / max(1, n - 1)), 2), "focus": .5} for k in range(n)]


# ------------------------------------------------------------------ títulos (capa transparente)
def render_overlay(cfg, tl, frames, outdir):
    from playwright.sync_api import sync_playwright
    outdir.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=CHROMIUM if os.path.exists(CHROMIUM) else None, args=["--allow-file-access-from-files"])
        page = b.new_page(viewport={"width": W, "height": H})
        page.goto((ROOT / "src" / "overlay.html").as_uri())
        page.wait_for_function("window.READY === true", timeout=60_000)
        page.evaluate("([c, t]) => setup(c, t)", [cfg, tl])
        for k, f in enumerate(frames):
            page.evaluate(f"render({f})")
            page.screenshot(path=str(outdir / f"{f:05d}.png"), omit_background=True)
            if k % 150 == 0:
                print(f"  títulos {k}/{len(frames)}", flush=True)
        b.close()


# ------------------------------------------------------------------ imagen
VIG = None
GRAIN = None


def look(img, flash=0):
    """Mismo tratamiento para todos los planos: contraste, color, viñeta y grano."""
    global VIG, GRAIN
    if VIG is None:
        yy, xx = np.mgrid[0:H, 0:W]
        r = np.hypot((xx - W / 2) / (W * .75), (yy - H / 2) / (H * .62))
        VIG = np.clip(1 - .55 * np.clip(r - .45, 0, 1) ** 1.6, 0, 1)[..., None].astype(np.float32)
        GRAIN = [(rng.standard_normal((H // 2, W // 2, 1)) * 7).astype(np.float32) for _ in range(6)]
    img = ImageEnhance.Contrast(img).enhance(1.1)
    img = ImageEnhance.Color(img).enhance(1.06)
    a = np.asarray(img, np.float32) * VIG
    g = GRAIN[int(rng.integers(6))]
    a += np.repeat(np.repeat(g, 2, 0), 2, 1)
    if flash:
        a = a * (1 - flash) + 255 * flash
    return np.clip(a, 0, 255).astype(np.uint8)


def frame_to_vertical(src, focus, zoom, fit):
    sw, sh = src.size
    if fit:   # plano abierto: cuadro completo sobre fondo desenfocado
        bg = src.resize((W, int(W * sh / sw)), Image.BILINEAR)
        cover = src.resize((int(H * sw / sh), H), Image.BILINEAR)
        cx = (cover.width - W) // 2
        back = cover.crop((cx, 0, cx + W, H)).resize((W // 10, H // 10)).filter(ImageFilter.GaussianBlur(3)).resize((W, H), Image.BILINEAR)
        back = ImageEnhance.Brightness(back).enhance(.45)
        fg = bg.resize((int(bg.width * zoom), int(bg.height * zoom)), Image.BICUBIC)
        back.paste(fg, ((W - fg.width) // 2, 880 - fg.height // 2))
        return back
    cw = min(sw, sh * W / H)
    ch = cw * H / W
    cw, ch = cw / zoom, ch / zoom
    cx = min(max(focus * sw, cw / 2), sw - cw / 2)
    cy = sh / 2
    return src.resize((W, H), Image.BICUBIC, box=(cx - cw / 2, cy - ch / 2, cx + cw / 2, cy + ch / 2))


def active(img, crop):
    """Recorta franjas negras (o subtítulos pegados) del tráiler: crop = [ancho, alto, x, y]."""
    if not crop:
        return img
    w, h, x, y = crop
    return img.crop((x, y, x + w, y + h))


def shot_frames(path, start, n):
    gen = imageio_ffmpeg.read_frames(str(path), input_params=["-ss", f"{start:.3f}"], output_params=["-vf", "fps=30"], pix_fmt="rgb24")
    meta = next(gen)
    size = meta["size"]
    last = None
    for k in range(n):
        try:
            data = next(gen)
            last = Image.frombytes("RGB", size, data)
        except StopIteration:
            pass
        if last is None:
            last = Image.new("RGB", size)
        yield last
    gen.close()


def plan(cfg, tl):
    """Lista de planos con su archivo, inicio, encuadre y cuadros de salida."""
    films = {f["id"]: f for f in cfg["films"]}
    shots = []
    for seg in tl["segments"]:
        if seg["kind"] == "outro":
            continue
        if seg["kind"] == "hook":
            src = cfg["hook"]["shots"]
            files = [films[s["film"]]["file"] for s in src]
            crops = [films[s["film"]].get("crop") for s in src]
        else:
            film = films[seg["id"]]
            src = film["shots"] or auto_shots(ROOT / film["file"], cfg["shots_per_film"])
            files = [film["file"]] * len(src)
            crops = [film.get("crop")] * len(src)
        ends = seg["cuts"][1:] + [seg["f1"]]
        for k, (c0, c1) in enumerate(zip(seg["cuts"], ends)):
            s = src[k % len(src)]
            shots.append({"file": ROOT / files[k % len(files)], "start": s["start"], "focus": s.get("focus", .5),
                          "fit": s.get("fit", False), "crop": crops[k % len(crops)], "f0": c0, "f1": c1, "first_of_seg": k == 0, "kind": seg["kind"]})
    return shots


def compose(cfg, tl, overlay_dir, dst):
    total = tl["total_frames"]
    shots = plan(cfg, tl)
    writer = imageio_ffmpeg.write_frames(str(dst), (W, H), fps=tl["fps"], codec="libx264", quality=None,
                                         output_params=["-crf", "14", "-preset", "medium", "-pix_fmt", "yuv420p"], macro_block_size=8)
    writer.send(None)
    f = 0
    for s in shots:
        n = s["f1"] - s["f0"]
        for k, src in enumerate(shot_frames(s["file"], s["start"], n)):
            prog = k / max(1, n - 1)
            punch = max(0, 1 - k / 4)
            zoom = 1.0 + .05 * prog + .07 * punch
            img = frame_to_vertical(active(src, s["crop"]), s["focus"], zoom, s["fit"])
            if s["kind"] == "hook":
                img = ImageEnhance.Brightness(img).enhance(.85)
            arr = look(img)
            frame = Image.fromarray(arr)
            ov = Image.open(overlay_dir / f"{f:05d}.png")
            frame.paste(ov, (0, 0), ov)
            writer.send(np.asarray(frame).tobytes())
            f += 1
        print(f"  plano {s['kind']} hasta {f / 30:.1f}s", flush=True)
    while f < total:   # cierre: sólo la capa de títulos (fondo propio)
        ov = Image.open(overlay_dir / f"{f:05d}.png").convert("RGBA")
        base = Image.new("RGBA", (W, H), (14, 12, 11, 255))
        base.alpha_composite(ov)
        writer.send(np.asarray(base.convert("RGB")).tobytes())
        f += 1
    writer.close()


def export(cfg, tl, raw, prefix):
    dur = tl["total_frames"] / tl["fps"]
    song = ROOT / cfg["song"]["file"]
    wav = OUT / "_audio.wav"
    fade = .6
    run(["-ss", f"{tl['audio_offset']:.3f}", "-t", f"{dur:.3f}", "-i", str(song),
         "-af", f"afade=t=out:st={dur - fade:.3f}:d={fade},loudnorm=I=-14:TP=-1:LRA=11,aresample=48000", "-ac", "2", str(wav)])
    V = ["-c:v", "libx264", "-preset", "slow", "-b:v", "7000k", "-maxrate", "10M", "-bufsize", "14M", "-profile:v", "high",
         "-level", "4.2", "-pix_fmt", "yuv420p", "-r", "30", "-g", "30", "-movflags", "+faststart"]
    pas = str(OUT / "_x264pass")
    run(["-i", str(raw), "-an", *V, "-pass", "1", "-passlogfile", pas, "-f", "mp4", "/dev/null"])
    run(["-i", str(raw), "-an", *V, "-pass", "2", "-passlogfile", pas, str(OUT / f"{prefix}-mudo.mp4")])
    run(["-i", str(raw), "-i", str(wav), "-map", "0:v", "-map", "1:a", *V, "-pass", "2", "-passlogfile", pas,
         "-c:a", "aac", "-b:a", "256k", "-shortest", str(OUT / f"{prefix}-con-audio.mp4")])
    for p in OUT.glob("_x264pass*"):
        p.unlink()
    # portada: el gancho ya completo
    hook = tl["segments"][0]
    fr = hook["beats"][min(5, len(hook["beats"]) - 1)]
    run(["-ss", f"{fr / tl['fps']:.3f}", "-i", str(raw), "-frames:v", "1", "-q:v", "2", str(OUT / f"{prefix}-portada.jpg")])


def main():
    args = sys.argv[1:]
    cfg = timeline.load_config()
    test = "--test" in args
    if test:
        cfg = make_test_material(cfg)
    tl = timeline.build(cfg)
    OUT.mkdir(exist_ok=True)
    (OUT / "timeline.json").write_text(json.dumps(tl, indent=1))
    print(f"tempo {tl['tempo']} BPM · {tl['beats_per_shot']} golpe(s) por plano · {tl['total_frames'] / tl['fps']:.1f} s")
    ovdir = OUT / "_titulos"
    if "--preview" in args:
        times = [float(x) for x in args[args.index("--preview") + 1:]]
        frames = [int(round(t * tl["fps"])) for t in times]
        render_overlay(cfg, tl, frames, ovdir)
        prev = OUT / "preview"
        prev.mkdir(exist_ok=True)
        shots = plan(cfg, tl)
        for fr in frames:
            s = next((x for x in shots if x["f0"] <= fr < x["f1"]), None)
            if s is None:
                img = Image.new("RGBA", (W, H), (14, 12, 11, 255))
            else:
                k = fr - s["f0"]
                src = list(shot_frames(s["file"], s["start"] + k / 30, 1))[0]
                img = Image.fromarray(look(frame_to_vertical(active(src, s["crop"]), s["focus"], 1.0 + .05 * k / max(1, s["f1"] - s["f0"]), s["fit"]))).convert("RGBA")
            img.alpha_composite(Image.open(ovdir / f"{fr:05d}.png").convert("RGBA"))
            img.convert("RGB").save(prev / f"t{fr / 30:05.2f}.jpg", quality=90)
        print("ok", prev)
        return
    if ovdir.exists():
        shutil.rmtree(ovdir)
    render_overlay(cfg, tl, list(range(tl["total_frames"])), ovdir)
    raw = OUT / "_video_raw.mp4"
    compose(cfg, tl, ovdir, raw)
    export(cfg, tl, raw, "prueba" if test else cfg.get("output", "reel"))
    print("ok")


if __name__ == "__main__":
    main()
