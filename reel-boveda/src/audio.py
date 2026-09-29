"""Banda sonora original del reel de La Bóveda Pochoclera (100% sintetizada, sin samples).

Groove retro a 120 BPM en Sol menor (Gm - Eb - Bb - F). Cada efecto está sincronizado con
los tiempos de reel.html. Genera output/_audio_raw.wav (48 kHz, estéreo).
"""
from pathlib import Path

import numpy as np
from scipy import signal
from scipy.io import wavfile

SR = 48000
DUR = 24.0
N = int(SR * DUR)
OUT = Path(__file__).resolve().parent.parent / "output"
rng = np.random.default_rng(2026)

dry = np.zeros((2, N))
send = np.zeros((2, N))


# ------------------------------------------------------------------ utilidades
def tt(d):
    return np.arange(int(d * SR)) / SR


def db(x):
    return 10 ** (x / 20)


def noise(d):
    return rng.standard_normal(int(d * SR))


def filt(x, kind, f, order=2):
    return signal.sosfilt(signal.butter(order, f, kind, fs=SR, output="sos"), x)


def svf(x, fc, q=0.8, mode="lp"):
    fc = np.broadcast_to(np.asarray(fc, float), x.shape)
    f = 2 * np.sin(np.pi * np.minimum(fc, SR / 7) / SR)
    damp, low, band = 1 / q, 0.0, 0.0
    out = np.empty_like(x)
    for n in range(len(x)):
        high = x[n] - low - damp * band
        band += f[n] * high
        low += f[n] * band
        out[n] = low if mode == "lp" else band if mode == "bp" else high
    return out


def fades(x, a=0.003, r=0.01):
    x = x.copy()
    na, nr = int(a * SR), int(r * SR)
    if na:
        x[..., :na] *= np.linspace(0, 1, na)
    if nr:
        x[..., -nr:] *= np.linspace(1, 0, nr)
    return x


def add(sig, at, gain=1.0, pan=0.0, rev=0.0):
    i = int(round(at * SR))
    if i >= N:
        return
    if sig.ndim == 1:
        th = (pan + 1) * np.pi / 4
        sig = np.vstack([sig * np.cos(th), sig * np.sin(th)]) * np.sqrt(2)
    n = min(sig.shape[1], N - i)
    dry[:, i:i + n] += sig[:, :n] * gain
    if rev:
        send[:, i:i + n] += sig[:, :n] * gain * rev


def sweep_sine(f):
    return np.sin(2 * np.pi * np.cumsum(f) / SR)


def saw(f, t, ph=0.0):
    return signal.sawtooth(2 * np.pi * f * t + ph)


# ------------------------------------------------------------------ instrumentos
def kick(d=.42, punch=1.0):
    t = tt(d)
    body = sweep_sine(50 + 150 * np.exp(-t / .03)) * np.exp(-t / .24)
    knock = sweep_sine(120 + 90 * np.exp(-t / .01)) * np.exp(-t / .03) * .5 * punch
    click = filt(noise(d), "highpass", 2500) * np.exp(-t / .0015) * .5
    return fades(np.tanh((body + knock + click) * 1.7), .0005, .05)


def clap(d=.32):
    t = tt(d)
    out = np.zeros_like(t)
    for off in (0, .011, .023):
        i = int(off * SR)
        seg = filt(noise(.04), "bandpass", [900, 4200]) * np.exp(-tt(.04) / .007)
        out[i:i + len(seg)] += seg
    out += filt(noise(d), "bandpass", [1100, 6000]) * np.exp(-t / .09) * .6
    return fades(out, .0005, .04)


def hat(d=.07, open_=False):
    t = tt(d)
    return fades(filt(noise(d), "highpass", 7000, 4) * np.exp(-t / (.09 if open_ else .02)), .0005, .01)


def shaker(d=.06):
    t = tt(d)
    return fades(filt(noise(d), "bandpass", [5000, 11000]) * np.sin(np.pi * t / d) ** 2, .001, .005)


def bass(f, d=.22):
    t = tt(d)
    v = np.sin(2 * np.pi * f * t) * .9 + saw(f, t) * .45 + np.sin(2 * np.pi * 2 * f * t) * .25
    v = filt(v, "lowpass", 900, 2)
    return fades(np.tanh(v * 1.8) * np.exp(-t / .14), .003, .03)


def organ(freqs, d=.16, bright=2600):
    """Stab de órgano retro (onda cuadrada filtrada)."""
    t = tt(d)
    v = sum(np.sign(np.sin(2 * np.pi * f * t + rng.uniform(0, 6))) * .6 + np.sin(2 * np.pi * 2 * f * t) * .3 for f in freqs)
    v = filt(v / len(freqs), "lowpass", bright, 2)
    return fades(v * np.exp(-t / .09), .002, .03)


def pluck(f, d=.5):
    """Marimba/pluck para las pastillas."""
    t = tt(d)
    v = np.sin(2 * np.pi * f * t) * np.exp(-t / .22) + .35 * np.sin(2 * np.pi * 4 * f * t) * np.exp(-t / .04)
    v += .2 * np.sin(2 * np.pi * 2 * f * t) * np.exp(-t / .12)
    return fades(v, .001, .05)


def boom(d=1.6, f_lo=46, f_hi=150, decay=.7):
    t = tt(d)
    body = sweep_sine(f_lo + f_hi * np.exp(-t / .05)) * np.exp(-t / decay) * .75
    thud = sweep_sine(105 + 120 * np.exp(-t / .03)) * np.exp(-t / .09) * .7
    trans = filt(noise(d), "bandpass", [200, 5000]) * np.exp(-t / .016) * .9
    return fades(np.tanh((body + thud + trans) * 2.2), .001, .2)


def brass(freqs, d=1.6):
    t = tt(d)
    v = np.zeros_like(t)
    for f in freqs:
        for m, a in [(1, 1), (1.004, .7), (.996, .7)]:
            v += a * saw(f * m, t, rng.uniform(0, 6))
    v = np.tanh(v / len(freqs) * 1.2)
    cutoff = 300 + 2600 * (1 - np.exp(-t / .04)) * np.exp(-t / .8)
    v = svf(v, cutoff, q=1.2)
    env = (1 - np.exp(-t / .012)) * np.exp(-t / 1.0)
    return fades(v * env * 1.6, .002, .3)


def whoosh(d=.4, f0=300, f1=4500, p0=-.7, p1=.7, rev=False):
    t = tt(d)
    x = t / d
    v = svf(noise(d), f0 * (f1 / f0) ** np.sin(x * np.pi / 2), q=2.2, mode="bp") * np.sin(np.pi * x) ** 2
    if rev:
        v = v * x ** 1.5
    th = (p0 + (p1 - p0) * x + 1) * np.pi / 4
    return np.vstack([v * np.cos(th), v * np.sin(th)]) * np.sqrt(2)


def riser(d, f0=150, f1=900):
    t = tt(d)
    x = t / d
    nz = svf(noise(d), 300 * (7000 / 300) ** x, q=1.6, mode="bp")
    tone = filt(signal.sawtooth(2 * np.pi * np.cumsum(f0 * (f1 / f0) ** x) / SR), "lowpass", 3000) * .3
    return fades((nz + tone) * x ** 2.2, .05, .004)


def crash(d=2.4):
    t = tt(d)
    return fades(np.vstack([filt(noise(d), "highpass", 3200) * np.exp(-t / .9) for _ in range(2)]), .001, .3)


def shimmer(d=1.2, n=10, lo=2600, hi=7500):
    out = np.zeros((2, int(d * SR)))
    for _ in range(n):
        f, dec, st = rng.uniform(lo, hi), rng.uniform(.2, .6), rng.uniform(0, .2)
        t = tt(d - st)
        v = np.sin(2 * np.pi * f * t) * np.exp(-t / dec) * rng.uniform(.3, 1)
        th = (rng.uniform(-.8, .8) + 1) * np.pi / 4
        i = int(st * SR)
        out[0, i:i + len(v)] += v * np.cos(th)
        out[1, i:i + len(v)] += v * np.sin(th)
    return out / n * 2.5


def pop():
    t = tt(.05)
    d = rng.uniform(.004, .011)
    b = filt(noise(.05), "bandpass", sorted([rng.uniform(900, 1700), rng.uniform(2400, 5200)])) * np.exp(-t / (d / 2.5))
    return fades(b * 2 + np.sin(2 * np.pi * rng.uniform(180, 380) * t) * np.exp(-t / .008) * .5, .0003, .01)


def kernel_pop():
    """Estallido de un pochoclo: crack corto de banda ancha + cuerpo grave + un soplido de vapor."""
    t = tt(.12)
    crack = filt(noise(.12), "bandpass", [rng.uniform(700, 1300), rng.uniform(4000, 8000)]) * np.exp(-t / rng.uniform(.0025, .006))
    if rng.random() < .5:
        i = int(rng.uniform(.002, .007) * SR)
        crack[i:] += crack[:len(crack) - i] * rng.uniform(.3, .7)
    body = sweep_sine(60 + rng.uniform(150, 320) * np.exp(-t / .02)) * np.exp(-t / .018) * .6
    hiss = filt(noise(.12), "highpass", 5000) * np.exp(-t / .04) * .08
    return fades(crack * 2.2 + body + hiss, .0002, .02)


def tap():
    """Cartita de papel que cae."""
    t = tt(.08)
    return fades(filt(noise(.08), "bandpass", [700, 3500]) * np.exp(-t / .012) + np.sin(2 * np.pi * rng.uniform(160, 240) * t) * np.exp(-t / .02) * .5, .0005, .01)


def snapclick():
    t = tt(.05)
    return fades(np.sin(2 * np.pi * rng.uniform(2200, 2800) * t) * np.exp(-t / .006) + filt(noise(.05), "highpass", 3000) * np.exp(-t / .003) * .6, .0003, .01)


def chime(freqs, d=1.4):
    t = tt(d)
    v = sum(np.sin(2 * np.pi * f * t) * np.exp(-t / .55) + .3 * np.sin(2 * np.pi * f * 2.76 * t) * np.exp(-t / .15) for f in freqs)
    return fades(v / len(freqs), .002, .1)


def clock_ticks(d, start_gap=.25, end_gap=.03):
    n = int(d * SR)
    out = np.zeros(n)
    tick = np.sin(2 * np.pi * 1800 * tt(.012)) * np.exp(-tt(.012) / .003)
    tock = np.sin(2 * np.pi * 1300 * tt(.012)) * np.exp(-tt(.012) / .003)
    tp, k = 0.0, 0
    while tp < d - .015:
        i = int(tp * SR)
        s = tick if k % 2 == 0 else tock
        out[i:i + len(s)] += s
        tp += start_gap * (end_gap / start_gap) ** (tp / d)
        k += 1
    return out


def scratch(d=.35):
    """Scratch de vinilo: un acorde leído hacia adelante y atrás."""
    src = organ([196.0, 233.08, 293.66], .6, 3500) + filt(noise(.6), "bandpass", [500, 3000]) * .15
    t = tt(d)
    pos = (.12 + .1 * np.sin(2 * np.pi * t / d * 1.5) * np.exp(-t / .3)) * SR
    idx = np.clip(pos.astype(int), 0, len(src) - 1)
    v = src[idx] * 1.5
    return fades(v * np.exp(-t / .25), .002, .05)


def clunk(heavy=1.0):
    d = .7
    t = tt(d)
    metal = sum(a * np.sin(2 * np.pi * f * t) * np.exp(-t / dc) for f, a, dc in [(312, .6, .25), (527, .5, .18), (893, .4, .12), (1377, .3, .08)])
    low = sweep_sine(55 + 80 * np.exp(-t / .03)) * np.exp(-t / .2) * heavy
    trans = filt(noise(d), "lowpass", 3000) * np.exp(-t / .01)
    return fades(np.tanh((metal * .6 + low + trans) * 1.5), .0005, .1)


def ratchet(d=.6):
    n = int(d * SR)
    out = np.zeros(n)
    click = lambda f: (np.sin(2 * np.pi * f * tt(.015)) + .6 * np.sin(2 * np.pi * f * 1.62 * tt(.015))) * np.exp(-tt(.015) / .003)
    tp = 0.0
    while tp < d - .02:
        i = int(tp * SR)
        c = click(1800 + 900 * tp / d) * rng.uniform(.6, 1)
        out[i:i + len(c)] += c
        tp += .034 + .02 * np.sin(np.pi * tp / d)
    return out


def creak(d=.4):
    t = tt(d)
    rate = 40 + 30 * np.sin(np.pi * t / d) + 10 * np.sin(2 * np.pi * 7 * t)
    ph = np.cumsum(rate) / SR
    pulses = (np.diff(np.floor(ph), prepend=0) > 0).astype(float)
    v = svf(pulses * 3, 700 + 200 * np.sin(2 * np.pi * 3 * t), q=6, mode="bp")
    return fades(v * np.sin(np.pi * t / d), .01, .05)


def kaching():
    d = 1.3
    t = tt(d)
    rattle = np.zeros_like(t)
    for k in range(6):
        i = int(k * .012 * SR)
        seg = filt(noise(.02), "bandpass", [1500, 6000]) * np.exp(-tt(.02) / .004)
        rattle[i:i + len(seg)] += seg * rng.uniform(.5, 1)
    bell = np.zeros_like(t)
    for st, f in ((.08, 2093.0), (.16, 2637.0)):
        i = int(st * SR)
        tb = tt(d - st)
        b = sum(a * np.sin(2 * np.pi * f * m * tb) * np.exp(-tb / dc) for m, a, dc in [(1, 1, .6), (2.4, .45, .25), (4.1, .25, .12)])
        bell[i:i + len(b)] += b
    return fades(rattle * .7 + bell * .55, .0005, .1)


def brushswish(d=.4):
    t = tt(d)
    v = filt(noise(d), "bandpass", [900, 5000]) * np.exp(-t / .15) * (1 - np.exp(-t / .01))
    grit = (rng.random(len(t)) < .012) * rng.standard_normal(len(t)) * 2.5 * np.exp(-t / .2)
    return fades(v + filt(grit, "highpass", 1500), .002, .05)


def typing(n=8, gap=.06):
    out = np.zeros(int((n * gap + .1) * SR))
    for k in range(n):
        i = int(k * gap * SR)
        tk = tt(.03)
        c = filt(noise(.03), "bandpass", [rng.uniform(1500, 2500), rng.uniform(4000, 6500)]) * np.exp(-tk / .004) + np.sin(2 * np.pi * rng.uniform(300, 420) * tk) * np.exp(-tk / .008) * .4
        out[i:i + len(c)] += c * rng.uniform(.7, 1)
    return out


def bloop():
    t = tt(.2)
    return fades(sweep_sine(480 + 800 * (1 - np.exp(-t / .03))) * np.exp(-t / .06), .001, .02)


def pad(freqs, d, att=.3, rel=.5, cutoff=1200):
    t = tt(d)
    out = np.zeros((2, len(t)))
    for ch in range(2):
        v = sum(saw(f * 2 ** (c / 1200), t, rng.uniform(0, 6)) for f in freqs for c in np.linspace(-10, 10, 4))
        out[ch] = filt(v, "lowpass", cutoff) / (len(freqs) * 4)
    return out * np.minimum(1, t / att) * np.minimum(1, (d - t) / rel) * 2


def crackle(d):
    n = int(d * SR)
    v = (rng.random(n) < .0009) * rng.standard_normal(n) * 3
    return filt(v, "bandpass", [800, 7000]) + filt(noise(d), "bandpass", [200, 1200]) * .015


# ------------------------------------------------------------------ partitura
G2, EB2, BB1, F2 = 98.0, 77.78, 58.27, 87.31
CHORDS = {G2: [196.0, 233.08, 293.66], EB2: [155.56, 196.0, 233.08], BB1: [233.08, 293.66, 349.23], F2: [174.61, 220.0, 261.63]}
PROG = [G2, EB2, BB1, F2]


def root_at(t):
    return PROG[int(t // 2) % 4]


def groove(a, b, full=True):
    """Groove a 120 BPM entre a y b (segundos, sobre la grilla de corcheas)."""
    for k in range(int(round((b - a) / .25))):
        at = a + k * .25
        r = root_at(at)
        beat = k % 2 == 0
        if beat:
            add(kick(), at, db(-8))
            if full and int(round(at / .5)) % 2 == 1:
                add(clap(), at, db(-13), rev=.15)
        else:
            add(hat(.12, True) if full else hat(), at, db(-21 if full else -23), pan=.3)
            if full:
                add(organ(CHORDS[r]), at, db(-19), pan=-.25, rev=.2)
        add(bass(r * (2 if k % 4 == 3 else 1)), at, db(-12))
        if full:
            add(shaker(), at + .125, db(-27), pan=-.4)


add(crackle(DUR), 0, db(-26))                     # crujido de vinilo de fondo

# S1 · gancho
for at, ch in ((0, G2), (.25, G2), (.5, G2)):
    add(boom(1.0, 48, 130, .3), at, db(-11))
    add(organ(CHORDS[ch], .22, 3500), at, db(-15), rev=.25)
add(clap(), .5, db(-12), rev=.3)
add(whoosh(.35, 300, 3500, -.5, .5), .75, db(-20))
add(whoosh(.3, 400, 4000, .5, -.2), .95, db(-22))
groove(1.0, 4.75, full=False)
for k in range(8):
    add(snapclick(), 1.2 + k * .2, db(-30), pan=-.4)   # scroll en el celu
add(whoosh(.3, 200, 5000, -.2, .2), 2.82, db(-17))

# S2 · agitación
cr = np.random.default_rng(77)
for g in range(3):
    for j in range(12):
        add(pop(), 3.0 + g * .5 + j * .03 + .03, db(cr.uniform(-24, -18)), pan=cr.uniform(-.8, .8))
add(whoosh(.3, 250, 4000, .3, -.3), 4.62, db(-18))
add(pad([98.0, 146.83, 196.0, 233.08], 1.9, .3, .3, 600), 4.8, db(-17), rev=.4)
for at in (5.0, 5.5, 6.0):
    add(filt(kick(), "lowpass", 400), at, db(-11))
add(clock_ticks(.9, .12, .025), 5.55, db(-19), pan=.2)
add(riser(1.0, 150, 700), 5.55, db(-16))
add(scratch(), 6.58, db(-9))

# S3 · el giro
for i in range(36):
    add(tap(), 6.62 + cr.uniform(0, .3) + .3, db(cr.uniform(-26, -20)), pan=cr.uniform(-.7, .7))
add(pad([98.0, 196.0], 1.0, .1, .2, 500), 6.6, db(-20))
for at in (6.66, 6.95):
    add(whoosh(.3, 300, 2500, -.2, .2), at - .08, db(-24))
add(boom(1.3, 46, 160, .5), 7.5, db(-7), rev=.3)
add(organ(CHORDS[G2], .3, 3000), 7.5, db(-14), rev=.3)
for i in range(12):
    add(snapclick(), 7.5 + i * .025 + .2, db(-19), pan=((i % 4) - 1.5) / 2)
add(chime([1568.0, 2349.3]), 7.95, db(-18), rev=.4)
add(whoosh(.4, 3000, 300, -.2, .2, rev=True), 8.3, db(-15))

# S4 · la bóveda
add(clunk(1.2), 8.66, db(-10), rev=.25)
add(ratchet(.6), 9.0, db(-15), pan=.15)
add(clunk(.8), 9.72, db(-11), rev=.3)
add(creak(.4), 9.74, db(-15), pan=-.3)
add(riser(.7, 200, 900), 9.35, db(-16))
add(boom(2.2, 44, 170, 1.0), 10.0, db(-5), rev=.35)
add(brass([98.0, 196.0, 233.08, 293.66], 1.8), 10.0, db(-10), rev=.35)
add(crash(2.6), 10.0, db(-16), rev=.3)
add(shimmer(1.6, 14), 10.08, db(-19), rev=.5)
groove(10.0, 24.0)
for at in (10.3, 10.5):
    add(boom(.7, 55, 150, .2), at, db(-14))
add(whoosh(1.0, 400, 3000, -.9, .9), 10.6, db(-19))
add(pop(), 10.82, db(-16))

# S5 · beneficios
for at in (11.6, 11.8, 12.0):
    add(whoosh(.3, 500, 5000, -.6, .6), at - .05, db(-22))
for i, f in enumerate([392.0, 440.0, 466.16, 523.25, 587.33]):
    add(pluck(f), 12.3 + i * .2 + .12, db(-15), pan=(-.3 if i % 2 else .3), rev=.3)
    add(whoosh(.2, 600, 4000, (.5 if i % 2 else -.5), 0), 12.3 + i * .2 - .05, db(-26))
add(chime([1174.66, 1760.0]), 13.42, db(-22), rev=.3)
add(brushswish(), 14.3, db(-14), pan=-.4)
add(brushswish(), 14.72, db(-14), pan=.4)
add(boom(.8, 50, 150, .25), 14.45, db(-12))
add(boom(1.2, 46, 170, .45), 14.9, db(-8), rev=.3)
add(crash(1.2), 14.9, db(-22))

# S6 · oferta
add(whoosh(.3, 300, 5000, .8, -.8), 15.8, db(-16))
for at in (15.9, 16.15):
    add(boom(.8, 50, 160, .25), at, db(-11))
for at in (16.45, 16.7, 16.95):
    add(snapclick(), at, db(-18))
    add(filt(kick(.2), "highpass", 150), at, db(-22))
add(boom(1.5, 44, 180, .55), 17.25, db(-6), rev=.3)
add(kaching(), 17.3, db(-9), rev=.25)
for i, f in enumerate([587.33, 698.46, 783.99]):
    add(pluck(f, .4), 17.75 + i * .2 + .08, db(-18), rev=.3)
add(shimmer(.9, 8), 18.2, db(-22), rev=.4)
add(whoosh(.3, 5000, 300, -.3, .3), 19.78, db(-16))

# S7 · llamado a la acción
add(pop(), 20.0, db(-15))
for at in (20.1, 20.35):
    add(boom(.8, 50, 160, .25), at, db(-11))
add(boom(1.6, 44, 180, .6), 20.85, db(-6), rev=.3)
add(brass([98.0, 196.0, 233.08, 293.66], 1.2), 20.85, db(-13), rev=.3)
add(pop(), 21.62, db(-16))
add(typing(8, .06), 21.95, db(-15), pan=-.1)
add(bloop(), 22.5, db(-14), rev=.2)
add(whoosh(.4, 600, 5000, -.4, .9), 22.52, db(-18))
add(whoosh(.3, 1500, 6000, .2, .8), 22.6, db(-24))
add(chime([1568.0, 2349.3]), 23.0, db(-22), rev=.4)


# pochoclos 3D: cada estallido de la coreografía (popdata.py) suena en su cuadro
from popdata import build as build_pops

_, POP_SOUNDS = build_pops()
for ts in POP_SOUNDS:
    add(kernel_pop(), ts, db(rng.uniform(-18, -11) if ts < 3 else rng.uniform(-22, -15)), pan=rng.uniform(-.8, .8), rev=.08)
add(whoosh(.5, 300, 5000, -.8, .8), 0.0, db(-17))
add(whoosh(.6, 250, 4500, .6, -.6), 10.1, db(-18))


# ------------------------------------------------------------------ reverb + máster
def make_ir(d=2.0, rt=1.4):
    t = tt(d)
    env = 10 ** (-3 * t / rt) * np.minimum(1, t / .006)
    ir = np.vstack([filt(noise(d), "lowpass", 6500) * env for _ in range(2)])
    ir = np.hstack([np.zeros((2, int(.018 * SR))), ir])
    return ir / np.sqrt((ir ** 2).sum() / 2)


ir = make_ir()
wet = np.vstack([signal.fftconvolve(send[c], ir[c])[:N] for c in range(2)]) * .5
mix = dry + wet
mix = np.vstack([filt(mix[c], "highpass", 38, 2) for c in range(2)])
low = np.vstack([filt(mix[c], "lowpass", 110, 4) for c in range(2)])
harm = np.vstack([filt(np.tanh(low[c] / (np.abs(low).max() + 1e-9) * 4), "bandpass", [140, 480]) for c in range(2)])
mix = mix - low * .4 + harm * np.abs(low).max() * .5
mix = mix + np.vstack([filt(mix[c], "bandpass", [1200, 6000]) for c in range(2)]) * .25
mix /= np.abs(mix).max()
mix = np.tanh(mix * 2.3) / np.tanh(2.3)
tail = int(.08 * SR)                      # corte limpio al final del compás (el loop vuelve al gancho)
mix[:, -tail:] *= np.linspace(1, 0, tail)
mix *= db(-1.5) / np.abs(mix).max()

OUT.mkdir(exist_ok=True)
wavfile.write(OUT / "_audio_raw.wav", SR, mix.T.astype(np.float32))
print("ok", OUT / "_audio_raw.wav")
