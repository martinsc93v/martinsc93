"""Beat original (sin derechos) para el reel: 128 BPM, La menor (Am - F - C - G), 40 s -> audio/beat.wav"""
from pathlib import Path

import numpy as np
from scipy import signal
from scipy.io import wavfile

SR, BPM, DUR = 44100, 128, 40
B = 60 / BPM
N = int(SR * DUR)
rng = np.random.default_rng(5)
mix = np.zeros((2, N))


def tt(d):
    return np.arange(int(d * SR)) / SR


def filt(x, kind, f, o=2):
    return signal.sosfilt(signal.butter(o, f, kind, fs=SR, output="sos"), x)


def add(x, at, g=1.0, pan=0.0):
    i = int(at * SR)
    if i >= N:
        return
    x = x[:N - i]
    th = (pan + 1) * np.pi / 4
    mix[0, i:i + len(x)] += x * g * np.cos(th) * 1.41
    mix[1, i:i + len(x)] += x * g * np.sin(th) * 1.41


def kick():
    t = tt(.4)
    return np.tanh(2 * np.sin(2 * np.pi * np.cumsum(48 + 150 * np.exp(-t / .03)) / SR) * np.exp(-t / .25))


def clap():
    t = tt(.3)
    out = filt(rng.standard_normal(len(t)), "bandpass", [1000, 6000]) * np.exp(-t / .09)
    for o in (0, .01, .021):
        i = int(o * SR)
        out[i:i + 400] += filt(rng.standard_normal(400), "bandpass", [900, 4000]) * 1.2
    return out * .7


def hat(open_=False):
    t = tt(.15)
    return filt(rng.standard_normal(len(t)), "highpass", 7000, 4) * np.exp(-t / (.07 if open_ else .02))


def bass(f, d):
    t = tt(d)
    v = np.sin(2 * np.pi * f * t) + .4 * signal.sawtooth(2 * np.pi * f * t)
    return np.tanh(1.6 * filt(v, "lowpass", 400)) * np.minimum(1, t / .01) * np.exp(-t / .5)


def pad(freqs, d):
    t = tt(d)
    v = sum(signal.sawtooth(2 * np.pi * f * (1 + c) * t + rng.uniform(0, 6)) for f in freqs for c in (-.004, 0, .004))
    return filt(v / (3 * len(freqs)), "lowpass", 1400) * np.minimum(1, t / .3) * np.minimum(1, (d - t) / .3)


def pluck(f):
    t = tt(.5)
    return (np.sin(2 * np.pi * f * t) + .3 * np.sin(4 * np.pi * f * t)) * np.exp(-t / .18)


PROG = [(55.0, [220.0, 261.63, 329.63]), (43.65, [174.61, 220.0, 261.63]), (65.41, [196.0, 261.63, 329.63]), (49.0, [196.0, 246.94, 293.66])]
ARP = [[440.0, 523.25, 659.25, 523.25], [349.23, 440.0, 523.25, 440.0], [392.0, 523.25, 659.25, 523.25], [392.0, 493.88, 587.33, 493.88]]
bars = int(DUR / (4 * B))
for bar in range(bars):
    t0 = bar * 4 * B
    root, chord = PROG[bar % 4]
    intro = bar < 2
    add(pad(chord, 4 * B), t0, .5)
    for k in range(8):
        add(pluck(ARP[bar % 4][k % 4] * (2 if k % 2 else 1)), t0 + k * B / 2, .16, pan=(-.4 if k % 2 else .4))
    for b in range(4):
        at = t0 + b * B
        if not intro or b in (0, 2):
            add(kick(), at, .9)
        if not intro and b % 2:
            add(clap(), at, .45)
        add(hat(), at + B / 2, .18, .3)
        if not intro:
            add(bass(root, B * .9), at, .45)
            add(hat(True), at + B * .75, .08, -.3)

mix = filt(mix, "highpass", 30)
mix = np.tanh(mix / np.abs(mix).max() * 1.8) / np.tanh(1.8) * .9
out = Path(__file__).resolve().parent.parent / "audio" / "beat.wav"
wavfile.write(out, SR, mix.T.astype(np.float32))
print("ok", out)
