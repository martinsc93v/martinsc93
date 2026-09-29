"""Banda sonora original del reel (100% sintetizada, sin samples ni música con derechos).

Tonalidad Re menor, 120 BPM en la sección rítmica. Cada evento está sincronizado con
los tiempos de las escenas de reel.html. Genera output/_audio_raw.wav (48 kHz, estéreo).
"""
from pathlib import Path

import numpy as np
from scipy import signal
from scipy.io import wavfile

SR = 48000
DUR = 20.0
N = int(SR * DUR)
OUT = Path(__file__).resolve().parent.parent / "output"
rng = np.random.default_rng(1985)

dry = np.zeros((2, N))
send = np.zeros((2, N))  # envío a reverb


# ------------------------------------------------------------------ utilidades
def tt(d):
    return np.arange(int(d * SR)) / SR


def db(x):
    return 10 ** (x / 20)


def noise(d):
    return rng.standard_normal(int(d * SR))


def filt(x, kind, f, order=2):
    sos = signal.butter(order, f, kind, fs=SR, output="sos")
    return signal.sosfilt(sos, x)


def svf(x, fc, q=0.8, mode="lp"):
    """Filtro de estado variable (Chamberlin) con frecuencia de corte variable en el tiempo."""
    fc = np.broadcast_to(np.asarray(fc, float), x.shape)
    f = 2 * np.sin(np.pi * np.minimum(fc, SR / 7) / SR)
    damp = 1 / q
    low = band = 0.0
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
    """Suma una señal mono (o estéreo 2xn) en el segundo `at`."""
    i = int(round(at * SR))
    if i >= N:
        return
    if sig.ndim == 1:
        th = (pan + 1) * np.pi / 4
        sig = np.vstack([sig * np.cos(th), sig * np.sin(th)]) * np.sqrt(2)
    n = min(sig.shape[1], N - i)
    if i < 0:
        sig, n, i = sig[:, -i:], n + i, 0
    dry[:, i:i + n] += sig[:, :n] * gain
    if rev:
        send[:, i:i + n] += sig[:, :n] * gain * rev


def saw(f, t, phase=0.0):
    return signal.sawtooth(2 * np.pi * f * t + phase)


def sweep_sine(f_of_t):
    return np.sin(2 * np.pi * np.cumsum(f_of_t) / SR)


# ------------------------------------------------------------------ instrumentos
def beep(f=1000, d=0.1):
    return fades(np.sin(2 * np.pi * f * tt(d)), .003, .01)


def projector(d, level=1.0):
    """Traqueteo de proyector: clics a 24 Hz + motor."""
    n = int(d * SR)
    out = np.zeros(n)
    click = filt(noise(0.004), "bandpass", [1500, 5200]) * np.exp(-tt(0.004) / 0.0012)
    for k in range(int(d * 24)):
        i = int(k / 24 * SR + rng.uniform(-40, 40))
        if 0 <= i < n - len(click):
            out[i:i + len(click)] += click * rng.uniform(.5, 1) * (1.0 if k % 2 == 0 else .6)
    t = tt(d)
    motor = filt(noise(d), "bandpass", [120, 520]) * .25 + .18 * np.sin(2 * np.pi * 48 * t) + .08 * np.sin(2 * np.pi * 96 * t)
    motor *= 1 + .3 * np.sin(2 * np.pi * 24 * t)
    return fades((out * 1.4 + motor) * level, .02, .03)


def braam(f0, d=2.6, bright=2400):
    t = tt(d)
    v = np.zeros_like(t)
    for mul, amp in [(1, 1), (1.004, .8), (.996, .8), (2, .55), (2.006, .4), (3, .3), (4.01, .15)]:
        v += amp * saw(f0 * mul, t, rng.uniform(0, 6.28))
    v = np.tanh(v * .9)
    cutoff = 140 + (bright - 140) * (1 - np.exp(-t / .05)) * np.exp(-t / 1.1) + 260
    v = svf(v, cutoff, q=1.4, mode="lp")
    env = (1 - np.exp(-t / .018)) * np.exp(-t / 1.5)
    sub = np.sin(2 * np.pi * f0 / 2 * t) * np.exp(-t / 1.2) * .35
    return fades(np.tanh((v * 1.8 + sub) * env * 1.3), .002, .4)


def boom(d=2.0, f_lo=38, f_hi=150, decay=.9):
    t = tt(d)
    body = sweep_sine(max(f_lo, 46) + f_hi * np.exp(-t / .06)) * np.exp(-t / decay) * .75
    thud = sweep_sine(105 + 120 * np.exp(-t / .03)) * np.exp(-t / .09) * .7
    trans = filt(noise(d), "bandpass", [200, 5000]) * np.exp(-t / .016) * .9
    return fades(np.tanh((body + thud + trans) * 2.2), .001, .2)


def kick(d=0.45):
    t = tt(d)
    body = sweep_sine(47 + 140 * np.exp(-t / .028)) * np.exp(-t / .26)
    click = filt(noise(d), "highpass", 2500) * np.exp(-t / .0015) * .6
    return fades(np.tanh((body + click) * 1.5), .0005, .05)


def snare(d=0.3):
    t = tt(d)
    n = filt(noise(d), "bandpass", [1300, 7500]) * np.exp(-t / .11)
    tone = np.sin(2 * np.pi * 186 * t) * np.exp(-t / .05)
    clap = np.zeros_like(t)
    for off in (0, .009, .019):
        i = int(off * SR)
        seg = filt(noise(.03), "bandpass", [900, 3500]) * np.exp(-tt(.03) / .006)
        clap[i:i + len(seg)] += seg
    return fades(n * .8 + tone * .6 + clap * .7, .0005, .05)


def hat(d=0.06, open_=False):
    t = tt(d)
    return fades(filt(noise(d), "highpass", 7200, 4) * np.exp(-t / (.1 if open_ else .022)), .0005, .01)


def bass(f, d=0.24):
    t = tt(d)
    v = saw(f, t) * .7 + np.sin(2 * np.pi * f * t) * .8
    v = filt(v, "lowpass", 380, 4)
    return fades(np.tanh(v * 1.6) * np.exp(-t / .16), .004, .03)


def whoosh(d=0.45, f0=300, f1=4200, pan0=-.7, pan1=.7):
    t = tt(d)
    x = t / d
    fc = f0 * (f1 / f0) ** np.sin(x * np.pi / 2)
    v = svf(noise(d), fc, q=2.2, mode="bp") * np.sin(np.pi * x) ** 2
    pan = pan0 + (pan1 - pan0) * x
    th = (pan + 1) * np.pi / 4
    return np.vstack([v * np.cos(th), v * np.sin(th)]) * np.sqrt(2)


def riser(d, f0=110, f1=880):
    t = tt(d)
    x = t / d
    nz = svf(noise(d), 300 * (6000 / 300) ** x, q=1.6, mode="bp")
    pitch = f0 * (f1 / f0) ** x
    tone = filt(signal.sawtooth(2 * np.pi * np.cumsum(pitch) / SR), "lowpass", 3000) * .35
    tone += np.sin(2 * np.pi * np.cumsum(pitch * 1.5) / SR) * .2
    return fades((nz + tone) * x ** 2.4, .05, .004)


def reverse_cymbal(d):
    t = tt(d)
    x = t / d
    v = filt(noise(d), "highpass", 3800) * x ** 3
    return fades(np.vstack([v, filt(noise(d), "highpass", 3800) * x ** 3]), .01, .004)


def crash(d=2.5):
    t = tt(d)
    l = filt(noise(d), "highpass", 3000) * np.exp(-t / 1.0)
    r = filt(noise(d), "highpass", 3000) * np.exp(-t / 1.0)
    return fades(np.vstack([l, r]), .001, .3)


def taiko(d=1.6):
    t = tt(d)
    body = sweep_sine(62 + 80 * np.exp(-t / .045)) * np.exp(-t / .5)
    skin = filt(noise(d), "bandpass", [150, 1800]) * np.exp(-t / .035) * .9
    return fades(np.tanh((body + skin) * 1.4), .0008, .2)


def shimmer(d=1.2, n=10, lo=2600, hi=7200):
    out = np.zeros((2, int(d * SR)))
    for _ in range(n):
        f = rng.uniform(lo, hi)
        dec = rng.uniform(.25, .7)
        st = rng.uniform(0, .18)
        t = tt(d - st)
        v = np.sin(2 * np.pi * f * t) * np.exp(-t / dec) * rng.uniform(.3, 1)
        i = int(st * SR)
        p = rng.uniform(-.8, .8)
        th = (p + 1) * np.pi / 4
        out[0, i:i + len(v)] += v * np.cos(th)
        out[1, i:i + len(v)] += v * np.sin(th)
    return out / n * 2.5


def counter_ticks(d=0.6):
    n = int(d * SR)
    out = np.zeros(n)
    tick = np.sin(2 * np.pi * 3400 * tt(.006)) * np.exp(-tt(.006) / .0015)
    tpos = 0.0
    while tpos < d - .01:
        i = int(tpos * SR)
        out[i:i + len(tick)] += tick
        tpos += .022 + .07 * (tpos / d) ** 2
    return out


def crt_off(d=0.36):
    t = tt(d)
    whine = sweep_sine(60 + 1500 * np.exp(-t / .07)) * np.exp(-t / .12) * .5
    crackle = filt(noise(d), "bandpass", [800, 6000]) * (rng.random(len(t)) < .02) * 3
    thump = sweep_sine(40 + 60 * np.exp(-t / .03)) * np.exp(-t / .09)
    return fades(whine + crackle * np.exp(-t / .15) + thump * .8, .001, .05)


def clack():
    d = .25
    t = tt(d)
    a = filt(noise(d), "lowpass", 2600) * np.exp(-t / .012)
    b = np.sin(2 * np.pi * 110 * t) * np.exp(-t / .045)
    out = a + b * .8
    i = int(.055 * SR)
    out[i:] += (filt(noise(d), "bandpass", [1500, 5000]) * np.exp(-t / .006))[:len(out) - i] * .6
    return fades(out, .0005, .03)


def kachunk():
    d = .22
    t = tt(d)
    ka = filt(noise(d), "highpass", 2200) * np.exp(-t / .004)
    chunk = (filt(noise(d), "lowpass", 900) * np.exp(-t / .02) + np.sin(2 * np.pi * 88 * t) * np.exp(-t / .05))
    out = ka * .7
    i = int(.06 * SR)
    out[i:] += chunk[:len(out) - i]
    return fades(out, .0005, .03)


def tick_wood():
    d = .08
    t = tt(d)
    return fades(np.sin(2 * np.pi * 1750 * t) * np.exp(-t / .012) + filt(noise(d), "bandpass", [2000, 5000]) * np.exp(-t / .004) * .5, .0003, .01)


def pad(freqs, d, att=.4, rel=.8, cutoff=1400, detune=12):
    t = tt(d)
    out = np.zeros((2, len(t)))
    for ch in range(2):
        v = np.zeros_like(t)
        for f in freqs:
            for c in np.linspace(-detune, detune, 5):
                v += saw(f * 2 ** (c / 1200 + rng.uniform(-2, 2) / 1200), t, rng.uniform(0, 6.28))
        out[ch] = filt(v, "lowpass", cutoff, 2) / (len(freqs) * 5)
    env = np.minimum(1, t / att) * np.minimum(1, (d - t) / rel)
    return out * env * 2.2


def drone(d):
    t = tt(d)
    v = np.sin(2 * np.pi * 36.71 * t) * .3 + np.sin(2 * np.pi * 73.42 * t) * .6 + saw(110.0, t) * .12 + saw(146.83, t) * .08
    v *= 1 + .25 * np.sin(2 * np.pi * .9 * t)
    air = filt(noise(d), "bandpass", [150, 600]) * .25
    env = np.minimum(1, t / .3)
    return (v + air) * env


def pop():
    d = rng.uniform(.004, .011)
    t = tt(.05)
    b = filt(noise(.05), "bandpass", sorted([rng.uniform(900, 1700), rng.uniform(2400, 5200)])) * np.exp(-t / (d / 2.5))
    th = np.sin(2 * np.pi * rng.uniform(180, 380) * t) * np.exp(-t / .008) * .5
    return fades(b * 2 + th, .0003, .01)


def bloop():
    d = .18
    t = tt(d)
    v = sweep_sine(480 + 700 * (1 - np.exp(-t / .03))) * np.exp(-t / .06)
    return fades(v, .001, .02)


def chime(freqs, d=1.4):
    t = tt(d)
    v = sum(np.sin(2 * np.pi * f * t) * np.exp(-t / .5) + .3 * np.sin(2 * np.pi * f * 2.76 * t) * np.exp(-t / .15) for f in freqs)
    return fades(v / len(freqs), .002, .1)


# ------------------------------------------------------------------ partitura
D2, BB1, C2, A1 = 73.42, 58.27, 65.41, 55.0

# S1 · cola de proyección (0 – 1.5)
for k, at in enumerate([0.0, 0.5, 1.0]):
    add(beep(1000 if k < 2 else 1000, .1), at, db(-13))
add(projector(1.5), 0.0, db(-15))
add(boom(1.2, 50, 120, .3), 0.0, db(-16))
add(riser(1.5, 55, 220), 0.0, db(-24))
add(whoosh(.3, 500, 5000, .5, -.5), 1.22, db(-17))

# S2 · banda verde (1.5 – 3.5)
add(braam(D2, 2.2), 1.5, db(-9), rev=.35)
add(boom(1.4, 38, 90, .5), 1.5, db(-12))
add(boom(1.0, 45, 160, .35), 2.1, db(-9), rev=.2)          # sello
add(snare(), 2.1, db(-14), rev=.4)
add(whoosh(.35, 250, 3000, -.6, .6), 1.78, db(-19))

# S3 · "apagar la pantalla" (3.5 – 5.5)
add(boom(2.0, 34, 80, 1.0), 3.5, db(-10), rev=.3)
dr = drone(1.62)
add(fades(dr, .05, .02), 3.5, db(-19))
for at in np.arange(3.5, 5.1, .5):
    add(tick_wood(), at, db(-24), pan=-.3, rev=.3)
add(whoosh(.55, 200, 2600, -.3, .3), 3.52, db(-22))
for at in (4.0, 4.25):
    add(boom(1.1, 40, 150, .45), at, db(-10), rev=.35)
    add(snare(), at, db(-17), rev=.5)
add(crt_off(), 5.1, db(-13))

# S4 · proyector (5.5 – 7.5)
add(clack(), 5.55, db(-7), rev=.2)
add(projector(1.95, .8), 5.55, db(-16))
add(fades(drone(1.95), .2, .05), 5.55, db(-21))
for at in (5.75, 6.0, 6.25, 6.5):
    add(kachunk(), at, db(-10), pan=.2, rev=.25)
    add(boom(.5, 60, 140, .12), at, db(-19))
add(riser(1.2), 6.3, db(-11))
add(reverse_cymbal(.9), 6.6, db(-19))

# S5 · ritmo (7.5 – 11.25) a 120 BPM
add(boom(2.4, 36, 170, 1.1), 7.5, db(-5), rev=.35)
add(crash(2.6), 7.5, db(-17), rev=.3)
add(braam(D2, 1.4, 3000), 7.5, db(-13), rev=.3)
beat = .5
for b in range(8):                      # compases 7.5 – 11.5
    at = 7.5 + b * beat
    if at >= 11.25:
        break
    add(kick(), at, db(-9))
    if b % 2 == 1:
        add(snare(), at, db(-13), rev=.25)
for k in range(15):                     # corcheas de hi-hat / semicorcheas en los cortes
    at = 7.5 + k * .25
    add(hat(), at + .125, db(-22), pan=.35)
    if at >= 9.5:
        add(hat(), at, db(-25), pan=-.35)
notes = [D2] * 4 + [BB1] * 4 + [C2] * 4 + [A1] * 3
for k, f in enumerate(notes):
    at = 7.5 + k * .25
    add(bass(f * (2 if k % 4 == 2 else 1)), at, db(-13))
for k, at in enumerate([7.5, 8.0, 8.5, 9.0]):  # golpes de palabra
    add(whoosh(.22, 400, 5000, -.4 + .25 * k, .4), at - .18, db(-20))
    add(boom(.6, 60, 200, .18), at, db(-15))
add(boom(1.2, 40, 160, .5), 9.5, db(-9), rev=.3)
for k in range(7):                      # cortes rápidos de portadas
    at = 9.5 + k * .25
    add(hat(.1, True), at, db(-21), pan=(-.5 if k % 2 else .5))
    add(kachunk(), at, db(-24))
for k in range(8):                      # redoble hacia el silencio
    at = 10.75 + k * .0625
    add(snare(.15), at, db(-24 + k * 1.5), pan=(-.2 if k % 2 else .2))

# S6 · laureles (11.5 – 15)
add(pad([73.42, 146.83, 174.61, 220.0], 3.6, .5, .5, 900), 11.5, db(-17), rev=.4)
for k in range(3):
    at = 11.65 + k * .7
    add(taiko(), at, db(-7), rev=.45)
    add(counter_ticks(.6), at, db(-27), pan=.2)
    add(shimmer(1.0, 8), at + .55, db(-21), rev=.5)
add(reverse_cymbal(.7), 14.3, db(-17))
add(riser(.6, 220, 660), 14.4, db(-18))

# S7 · manifiesto (15 – 17)
add(braam(BB1, 2.4, 2800), 15.0, db(-6), rev=.35)
add(boom(1.6, 36, 140, .7), 15.0, db(-9))
add(crash(2.2), 15.0, db(-18), rev=.3)
add(pad([116.54, 146.83, 174.61, 233.08], 1.05, .15, .15, 1600), 15.0, db(-18), rev=.4)
add(pad([130.81, 164.81, 196.0, 261.63], 1.0, .1, .2, 1800), 16.0, db(-18), rev=.4)
for at in (15.05, 15.18, 15.3, 15.44):
    add(whoosh(.3, 350, 3500, -.3, .3), at - .1, db(-24))
for at in (15.5, 16.0, 16.5):
    add(kick(), at, db(-15))
add(whoosh(.4, 200, 6000, -.8, .8), 16.62, db(-14))
add(reverse_cymbal(.5), 16.5, db(-16))

# S8 · cierre (17 – 20)
add(boom(2.6, 34, 180, 1.2), 17.0, db(-5), rev=.4)
add(braam(D2, 2.6, 2600), 17.0, db(-11), rev=.35)
add(crash(2.8), 17.0, db(-17), rev=.3)
add(pad([146.83, 185.0, 220.0, 293.66, 440.0], 3.0, .35, 1.6, 2000), 17.0, db(-16), rev=.5)
add(shimmer(2.0, 14, 3000, 8000), 17.05, db(-19), rev=.5)
for _ in range(34):                     # estallido de pochoclos
    add(pop(), 17.02 + rng.gamma(1.6, .12), db(rng.uniform(-22, -14)), pan=rng.uniform(-.9, .9))
add(bloop(), 18.6, db(-14), rev=.2)
add(hat(), 18.6, db(-18))
add(chime([1174.66, 1760.0]), 18.68, db(-19), rev=.4)
for _ in range(12):
    add(pop(), 18.63 + rng.gamma(1.4, .07), db(rng.uniform(-24, -17)), pan=rng.uniform(-.8, .8))

# ------------------------------------------------------------------ reverb + máster
def make_ir(d=2.6, rt=1.9):
    t = tt(d)
    env = 10 ** (-3 * t / rt) * np.minimum(1, t / .006)
    ir = np.vstack([filt(noise(d), "lowpass", 6500) * env, filt(noise(d), "lowpass", 6500) * env])
    pre = np.zeros((2, int(.022 * SR)))
    ir = np.hstack([pre, ir])
    return ir / np.sqrt((ir ** 2).sum() / 2)


ir = make_ir()
wet = np.vstack([signal.fftconvolve(send[c], ir[c])[:N] for c in range(2)]) * .55
mix = dry + wet
mix = np.vstack([filt(mix[c], "highpass", 38, 2) for c in range(2)])
low = np.vstack([filt(mix[c], "lowpass", 110, 4) for c in range(2)])
harm = np.vstack([filt(np.tanh(low[c] / (np.abs(low).max() + 1e-9) * 4), "bandpass", [140, 480]) for c in range(2)])
mix = mix - low * .45 + harm * np.abs(low).max() * .55
mix = mix + np.vstack([filt(mix[c], "bandpass", [1200, 6000]) for c in range(2)]) * .3   # presencia
mix /= np.abs(mix).max()
mix = np.tanh(mix * 1.6) / np.tanh(1.6)       # saturación suave del máster
# cola final: que el loop no corte en seco
tail = int(.35 * SR)
mix[:, -tail:] *= np.linspace(1, 0, tail) ** 1.5
mix *= db(-1.5) / np.abs(mix).max()

OUT.mkdir(exist_ok=True)
wavfile.write(OUT / "_audio_raw.wav", SR, mix.T.astype(np.float32))
print("ok", OUT / "_audio_raw.wav")
