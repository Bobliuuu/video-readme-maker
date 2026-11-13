"""Generative background music (numpy only): warm pad + soft pluck arpeggio, seeded so a project always gets the same track."""
import wave, zlib
import numpy as np

SR = 44100
CHORDS = [(57, 60, 64), (53, 57, 60), (48, 52, 55), (55, 59, 62)]  # Am F C G


def _hz(m):
    return 440 * 2 ** ((m - 69) / 12)


def make_music(seconds, seed="vrm", out_wav=None):
    rng = np.random.default_rng(zlib.crc32(seed.encode()))
    n = int(seconds * SR)
    t = np.arange(n) / SR
    bar = 4.0
    mix = np.zeros((2, n))
    for ci in range(int(seconds / bar) + 2):
        ch = CHORDS[ci % 4]
        s, e = int(ci * bar * SR), min(n, int((ci + 1) * bar * SR + SR))
        if s >= n:
            break
        tt = t[s:e] - ci * bar
        env = np.clip(tt / 1.2, 0, 1) * np.clip((bar + 1 - tt) / 1.5, 0, 1)
        for k, m in enumerate(ch):
            for det, pan in ((-0.15, 0.3), (0.15, 0.7)):
                f = _hz(m - 12) * 2 ** (det / 12)
                w = (np.sin(2 * np.pi * f * tt) + .3 * np.sin(4 * np.pi * f * tt)) * env * .05
                mix[0, s:e] += w * (1 - pan); mix[1, s:e] += w * pan
        step = bar / 8
        for j in range(8):
            m = ch[[0, 1, 2, 1, 2, 1, 0, 2][j]] + 12
            s2 = int((ci * bar + j * step) * SR)
            if s2 >= n:
                break
            e2 = min(n, s2 + int(1.2 * SR))
            tt2 = np.arange(e2 - s2) / SR
            p = np.sin(2 * np.pi * _hz(m) * tt2) * np.exp(-tt2 * 4.5) * .035
            pan = .3 + .4 * ((j % 3) / 2)
            mix[0, s2:e2] += p * (1 - pan); mix[1, s2:e2] += p * pan
    mix *= np.clip(t / 2, 0, 1) * np.clip((seconds - t) / 3, 0, 1)
    mix /= max(1e-9, np.abs(mix).max())
    if out_wav:
        pcm = (mix.T * 32000 * .9).astype("<i2")
        with wave.open(out_wav, "wb") as w:
            w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
    return mix
