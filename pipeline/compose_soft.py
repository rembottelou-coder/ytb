"""Compose a "0% vs 100% SOFT" short. python3 compose_soft.py <short_dir> <title_word>
Clips: <short_dir>/clip1..N each with track.json (soft value inside). Outputs <short_dir>/final.mp4
"""
import sys, os, json, glob, subprocess, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

sd = sys.argv[1]
word = sys.argv[2] if len(sys.argv) > 2 else "SOFT"
W, H, FPS, SR = 1080, 1920, 30, 48000
FONT = "/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf"
f_big = ImageFont.truetype(FONT, 104)
rng = np.random.default_rng(int(os.environ.get("SEED", "5")))
clips = sorted(glob.glob(os.path.join(sd, "clip*")), key=lambda p: int(p.split("clip")[-1]))

def jolts(track, thr):
    fr = sorted(int(k) for k in track)
    c = np.array([track[str(f)][0] for f in fr])
    v = np.diff(c, axis=0)
    a = np.linalg.norm(np.diff(v, axis=0), axis=1)
    out, last = [], -10
    for i, m in enumerate(a):
        if m > thr and fr[i + 1] - last >= 3:
            out.append((fr[i + 1], float(min(1.0, m / (thr * 6)))))
            last = fr[i + 1]
    return out

# ---------------- sounds ----------------
def env(t, d): return np.exp(-d * t)
def clink(mag):
    t = np.arange(int(SR * 0.9)) / SR
    fs = np.array([2350, 3720, 5180, 6900]) * rng.uniform(0.95, 1.05)
    s = sum(a * np.sin(2 * np.pi * f * t) * env(t, d) for f, a, d in zip(fs, [1, .6, .4, .25], [7, 9, 12, 16]))
    s += rng.normal(0, 1, len(t)) * env(t, 400) * 0.4
    return s * 0.35 * (0.3 + 0.7 * mag)
def thud(mag):
    t = np.arange(int(SR * 0.4)) / SR
    s = np.sin(2 * np.pi * (110 - 40 * t) * t) * env(t, 18) + 0.4 * np.sin(2 * np.pi * 330 * t) * env(t, 40)
    s += rng.normal(0, 1, len(t)) * env(t, 150) * 0.3
    return s * (0.3 + 0.7 * mag)
def squish(mag, length=0.45):
    n = int(SR * length); t = np.arange(n) / SR
    # wet squelch: band-limited noise with a sweeping resonance + low "bloop"
    x = rng.normal(0, 1, n)
    y = np.zeros(n); y1 = y2 = 0.0
    for i in range(n):
        f = 900 - 650 * (i / n)
        w = 2 * np.pi * f / SR; rr = 0.985
        yy = x[i] + 2 * rr * np.cos(w) * y1 - rr * rr * y2
        y2, y1 = y1, yy; y[i] = yy
    y = y / (np.abs(y).max() + 1e-9)
    bloop = np.sin(2 * np.pi * np.cumsum(180 - 90 * t / length) / SR) * env(t, 9)
    e = np.minimum(1, t / 0.01) * env(t, 7)
    return (0.55 * y * e + 0.8 * bloop) * (0.35 + 0.65 * mag)
def whoosh(n):
    x = rng.normal(0, 1, n); y = np.zeros(n); acc = 0.0
    for i in range(n):
        acc += (0.02 + 0.2 * (i / n) ** 2) * (x[i] - acc); y[i] = acc
    return y * (np.arange(n) / n) ** 2 * 0.4
def pad(n):
    t = np.arange(n) / SR; s = np.zeros(n); seg = int(SR * 2)
    chords = [[261.63, 329.63, 392.0], [220.0, 261.63, 329.63], [174.61, 220.0, 261.63], [196.0, 246.94, 293.66]]
    for i in range(0, n, seg):
        tt = t[i:i + seg] - t[i]; m = len(tt)
        e = np.minimum(1, tt / 0.5) * np.minimum(1, (2 - tt) / 0.5)
        s[i:i + m] += sum(np.sin(2 * np.pi * f * tt) for f in chords[(i // seg) % 4]) * e
    return s * 0.025
def add(buf, snd, at):
    i = int(at * SR)
    if i < len(buf):
        j = min(len(buf), i + len(snd)); buf[i:j] += snd[: j - i]

def text_center(d, y, txt, font, fill):
    w = d.textlength(txt, font=font); d.text(((W - w) / 2, y), txt, font=font, fill=fill)

out_frames = os.path.join(sd, "comp"); os.makedirs(out_frames, exist_ok=True)
for f in glob.glob(os.path.join(out_frames, "*.jpg")): os.remove(f)
gi, events = 0, []
for ci, cdir in enumerate(clips):
    tr = json.load(open(os.path.join(cdir, "track.json")))
    soft = tr["soft"]; drop = tr["drop_start"]
    frames = sorted(glob.glob(os.path.join(cdir, "f_*.jpg")))
    t0 = gi / FPS
    events.append((t0 + drop / FPS, "whoosh", 1))
    js = jolts(tr["track"], 0.02 if soft == 0 else 0.012)
    for f, mag in js:
        if soft == 0:
            z = tr["track"][str(f)][0][2]
            events.append((t0 + f / FPS, "clink" if z > 2.6 else "thud", mag))
        else:
            events.append((t0 + f / FPS, "squish", mag * (0.6 + 0.4 * soft / 100)))
    for k, fp in enumerate(frames):
        im = Image.open(fp).convert("RGB").resize((W, H), Image.LANCZOS)
        im = im.filter(ImageFilter.UnsharpMask(radius=2, percent=50, threshold=2))
        d = ImageDraw.Draw(im)
        text_center(d, 150, f"{soft}% {word}", f_big, (25, 25, 28))
        im.save(os.path.join(out_frames, "c_%05d.jpg" % gi), quality=93); gi += 1

dur = gi / FPS
buf = np.zeros(int(SR * (dur + 1)))
buf += pad(len(buf))
for t, kind, mag in events:
    snd = {"clink": lambda: clink(mag), "thud": lambda: thud(mag), "squish": lambda: squish(mag),
           "whoosh": lambda: whoosh(int(SR * 0.45)) * 0.5}[kind]()
    add(buf, snd, t)
buf = buf[: int(SR * dur)]
buf = buf / (np.abs(buf).max() + 1e-9) * 0.85
fo = int(SR * 0.25); buf[-fo:] *= np.linspace(1, 0, fo)
with wave.open(os.path.join(sd, "audio.wav"), "wb") as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((buf * 32767).astype(np.int16).tobytes())
out = os.path.join(sd, "final.mp4")
subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-framerate", str(FPS), "-i", os.path.join(out_frames, "c_%05d.jpg"),
                "-i", os.path.join(sd, "audio.wav"), "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", out], check=True)
print("OK", out, round(dur, 2), "s", len(events), "events")
