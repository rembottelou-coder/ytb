"""Procedural 'satisfying' sound effects (48 kHz mono numpy arrays)."""
import numpy as np

SR = 48000
_rng = np.random.default_rng(7)


def seed(s):
    global _rng
    _rng = np.random.default_rng(s)


def _t(d):
    return np.arange(int(SR * d)) / SR


def _env(t, d):
    return np.exp(-d * t)


def _reson(x, f, q=0.985):
    """2-pole resonator over signal x at frequency f (scalar or array)."""
    y = np.zeros_like(x); y1 = y2 = 0.0
    f = np.broadcast_to(np.asarray(f, float), x.shape)
    c = 2 * q * np.cos(2 * np.pi * f / SR)
    for i in range(len(x)):
        yy = x[i] + c[i] * y1 - q * q * y2
        y2, y1 = y1, yy; y[i] = yy
    return y / (np.abs(y).max() + 1e-9)


def knock(mag=1.0, pitch=1.0):          # wood
    t = _t(0.35)
    fs = np.array([190, 410, 830, 1560]) * pitch * _rng.uniform(0.93, 1.07, 4)
    s = sum(a * np.sin(2 * np.pi * f * t) * _env(t, d) for f, a, d in zip(fs, [1, .6, .35, .15], [28, 40, 60, 90]))
    s += _rng.normal(0, 1, len(t)) * _env(t, 180) * 0.5
    return s * mag


def thock(mag=1.0, pitch=1.0):         # deep satisfying plastic/wood landing
    t = _t(0.5)
    s = 1.1 * np.sin(2 * np.pi * 120 * pitch * t) * _env(t, 16) + 0.6 * np.sin(2 * np.pi * 300 * pitch * t) * _env(t, 25)
    s += 0.35 * np.sin(2 * np.pi * 640 * pitch * t) * _env(t, 40)
    s += _rng.normal(0, 1, len(t)) * _env(t, 140) * 0.45
    return s * mag


def clack(mag=1.0, pitch=1.0):         # dice / hard plastic
    t = _t(0.18)
    fs = np.array([1800, 2900, 4300]) * pitch * _rng.uniform(0.9, 1.1, 3)
    s = sum(a * np.sin(2 * np.pi * f * t) * _env(t, d) for f, a, d in zip(fs, [1, .7, .4], [55, 70, 90]))
    s += _rng.normal(0, 1, len(t)) * _env(t, 350) * 0.8
    return s * 0.6 * mag


def click(mag=1.0, pitch=1.0):         # domino tick
    t = _t(0.08)
    s = np.sin(2 * np.pi * 2600 * pitch * t) * _env(t, 120) + _rng.normal(0, 1, len(t)) * _env(t, 600) * 0.7
    s += 0.5 * np.sin(2 * np.pi * 900 * pitch * t) * _env(t, 90)
    return s * 0.55 * mag


def clink(mag=1.0, pitch=1.0):         # metal / glass marble
    t = _t(0.8)
    fs = np.array([2350, 3720, 5180]) * pitch * _rng.uniform(0.96, 1.04)
    s = sum(a * np.sin(2 * np.pi * f * t) * _env(t, d) for f, a, d in zip(fs, [1, .55, .3], [8, 11, 15]))
    s += _rng.normal(0, 1, len(t)) * _env(t, 450) * 0.3
    return s * 0.3 * mag


def thud(mag=1.0, pitch=1.0):
    t = _t(0.35)
    s = np.sin(2 * np.pi * (100 * pitch - 40 * t) * t) * _env(t, 18) + 0.3 * np.sin(2 * np.pi * 280 * t) * _env(t, 40)
    s += _rng.normal(0, 1, len(t)) * _env(t, 150) * 0.3
    return s * mag


def squish(mag=1.0, pitch=1.0, length=0.45):
    t = _t(length); n = len(t)
    y = _reson(_rng.normal(0, 1, n), (900 - 650 * t / length) * pitch)
    bloop = np.sin(2 * np.pi * np.cumsum(180 * pitch - 90 * t / length) / SR) * _env(t, 9)
    e = np.minimum(1, t / 0.01) * _env(t, 7)
    return (0.55 * y * e + 0.8 * bloop) * mag


def whoosh(mag=1.0, length=0.45):
    n = int(SR * length); x = _rng.normal(0, 1, n); y = np.zeros(n); acc = 0.0
    for i in range(n):
        acc += (0.02 + 0.22 * (i / n) ** 2) * (x[i] - acc); y[i] = acc
    return y * (np.arange(n) / n) ** 2 * 0.5 * mag


def swish(mag=1.0, length=0.8):         # cloth
    n = int(SR * length); t = np.arange(n) / SR
    y = _reson(_rng.normal(0, 1, n), 1200 + 800 * np.sin(np.pi * t / length), q=0.9)
    e = np.sin(np.pi * t / length) ** 2
    return y * e * 0.25 * mag


def ding(mag=1.0, pitch=1.0):
    t = _t(1.6); s = np.zeros_like(t)
    for f, a, d in [(1046.5, .5, 3.0), (1568, .35, 3.5), (2093, .2, 4.5), (1318.5, .3, 3.2)]:
        s += a * np.sin(2 * np.pi * f * pitch * t) * _env(t, d)
    return s * np.minimum(1, t / 0.004) * 0.45 * mag


def pluck(mag=1.0, step=0):            # pentatonic marimba note, step = scale degree
    scale = [0, 2, 4, 7, 9]
    semi = scale[step % 5] + 12 * (step // 5)
    f = 523.25 * 2 ** (semi / 12)
    t = _t(0.7)
    s = np.sin(2 * np.pi * f * t) * _env(t, 7) + 0.25 * np.sin(2 * np.pi * 4 * f * t) * _env(t, 18)
    return s * 0.35 * mag


def pad(n, root=261.63):
    t = np.arange(n) / SR; s = np.zeros(n); seg = int(SR * 2)
    ratios = [[1, 1.26, 1.5], [0.84, 1.0, 1.26], [0.667, 0.84, 1.0], [0.75, 0.944, 1.122]]
    for i in range(0, n, seg):
        tt = t[i:i + seg] - t[i]; m = len(tt)
        e = np.minimum(1, tt / 0.5) * np.minimum(1, (2 - tt) / 0.5)
        s[i:i + m] += sum(np.sin(2 * np.pi * root * r * tt) for r in ratios[(i // seg) % 4]) * e
    return s * 0.022


SOUNDS = {"knock": knock, "thock": thock, "clack": clack, "click": click, "clink": clink, "thud": thud,
          "squish": squish, "ding": ding}
