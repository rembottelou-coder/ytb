"""Compose a short from rendered clips: upscale, overlay text, synthesize SFX, encode.
python3 compose.py <short_dir> <label> <val1> <val2> ... (one value per clip; last = success)
e.g. compose.py shorts/s01 "Angle" "32°" "12°" "0°"
"""
import sys, os, json, glob, subprocess, math, random
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

sd = sys.argv[1]
label = sys.argv[2]
vals = sys.argv[3:]
W, H = 1080, 1920
FPS = 30
SR = 48000
FONT = "/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf"
f_big = ImageFont.truetype(FONT, 92)
f_mark = ImageFont.truetype(FONT, 120)
f_small = ImageFont.truetype(FONT, 46)
rng = np.random.default_rng(int(os.environ.get("SEED", "3")))

clips = sorted(glob.glob(os.path.join(sd, "clip*")), key=lambda p: int(p.split("clip")[-1]))
assert len(clips) == len(vals), (clips, vals)

def impacts(track, success):
    fr = sorted(int(k) for k in track)
    z = np.array([[p[2] for p in track[str(f)]] for f in fr])  # frames x slabs
    if success:
        # frame where centre reaches rest (velocity ~0 after falling)
        zc = z.mean(1)
        v = np.diff(zc)
        idx = int(np.argmax((v[:-1] < -0.05) & (np.abs(v[1:]) < 0.02))) + 1
        return [(fr[idx] , 1.0)]
    v = np.diff(z, axis=0)
    a = np.diff(v, axis=0)  # positive = upward jolt
    ev = []
    for i in range(a.shape[0]):
        m = a[i].clip(min=0)
        strong = m[m > 0.025]
        if len(strong):
            ev.append((fr[i + 1], float(min(1.0, strong.sum() * 2.5)), len(strong)))
    out = []
    last = -10
    for f, mag, n in ev:
        if f - last >= 2:
            out.append((f, mag))
            last = f
    return out

# ---------------- audio synthesis ----------------
def knock(mag, pitch=1.0, dur=0.35):
    t = np.arange(int(SR * dur)) / SR
    freqs = np.array([190, 410, 830, 1560]) * pitch * rng.uniform(0.92, 1.08, 4)
    decays = np.array([28, 40, 60, 90])
    amps = np.array([1.0, 0.6, 0.35, 0.15])
    s = sum(a * np.sin(2 * np.pi * f * t + rng.uniform(0, 6)) * np.exp(-d * t) for f, d, a in zip(freqs, decays, amps))
    noise = rng.normal(0, 1, len(t)) * np.exp(-180 * t) * 0.6
    s = s + noise
    return s * mag

def thock():
    t = np.arange(int(SR * 0.6)) / SR
    s = 1.2 * np.sin(2 * np.pi * 95 * t) * np.exp(-14 * t) + 0.7 * np.sin(2 * np.pi * 240 * t) * np.exp(-22 * t)
    s += 0.4 * np.sin(2 * np.pi * 520 * t) * np.exp(-35 * t)
    s += rng.normal(0, 1, len(t)) * np.exp(-120 * t) * 0.5
    return s

def chime():
    t = np.arange(int(SR * 1.6)) / SR
    s = np.zeros_like(t)
    for f, a, d in [(1046.5, 0.5, 3.0), (1568, 0.35, 3.5), (2093, 0.2, 4.5), (1318.5, 0.3, 3.2)]:
        s += a * np.sin(2 * np.pi * f * t) * np.exp(-d * t)
    att = np.minimum(1, t / 0.004)
    return s * att * 0.45

def fail_tone():
    t = np.arange(int(SR * 0.35)) / SR
    f = 160 - 60 * t / 0.35
    ph = 2 * np.pi * np.cumsum(f) / SR
    s = (np.sin(ph) + 0.3 * np.sign(np.sin(ph))) * np.exp(-6 * t) * 0.25
    return s

def whoosh(n):
    x = rng.normal(0, 1, n)
    # simple one-pole lowpass with rising cutoff
    y = np.zeros(n)
    acc = 0.0
    for i in range(n):
        alpha = 0.02 + 0.25 * (i / n) ** 2
        acc += alpha * (x[i] - acc)
        y[i] = acc
    env = (np.arange(n) / n) ** 2
    return y * env * 0.5

def pad(n):
    t = np.arange(n) / SR
    chords = [[220.0, 277.18, 329.63], [196.0, 246.94, 293.66], [174.61, 220.0, 261.63], [196.0, 246.94, 329.63]]
    seg = int(SR * 2.0)
    s = np.zeros(n)
    for i in range(0, n, seg):
        ch = chords[(i // seg) % len(chords)]
        tt = t[i:i + seg] - t[i]
        env = np.minimum(1, tt / 0.6) * np.minimum(1, (2.0 - tt) / 0.6)
        part = sum(np.sin(2 * np.pi * f * tt) + 0.3 * np.sin(2 * np.pi * 2 * f * tt) for f in ch)
        s[i:i + seg] += part[: len(s[i:i + seg])] * env[: len(s[i:i + seg])]
    return s * 0.03

def add(buf, snd, at):
    i = int(at * SR)
    if i >= len(buf):
        return
    j = min(len(buf), i + len(snd))
    buf[i:j] += snd[: j - i]

# ---------------- frames ----------------
def text_center(d, y, txt, font, fill, stroke=0):
    w = d.textlength(txt, font=font)
    d.text(((W - w) / 2, y), txt, font=font, fill=fill, stroke_width=stroke, stroke_fill=(0, 0, 0))

def draw_x(d, cx, cy, s, col):
    d.line([(cx - s, cy - s), (cx + s, cy + s)], fill=col, width=16)
    d.line([(cx - s, cy + s), (cx + s, cy - s)], fill=col, width=16)

def draw_check(d, cx, cy, s, col):
    d.line([(cx - s, cy), (cx - s * 0.3, cy + s * 0.7), (cx + s, cy - s * 0.8)], fill=col, width=18, joint="curve")

out_frames = os.path.join(sd, "comp")
os.makedirs(out_frames, exist_ok=True)
for f in glob.glob(os.path.join(out_frames, "*.jpg")):
    os.remove(f)

gi = 0
events = []  # (time, kind, mag)
n_total = len(clips)
for ci, (cdir, val) in enumerate(zip(clips, vals)):
    tr = json.load(open(os.path.join(cdir, "track.json")))
    success = tr["success"]
    drop = tr["drop_start"]
    imps = impacts(tr["track"], success)
    first_imp = imps[0][0] if imps else drop + 20
    frames = sorted(glob.glob(os.path.join(cdir, "f_*.jpg")))
    # trim: fail clips end ~1.2s after first impact; success holds ~1.4s after landing
    end_f = min(len(frames), first_imp + (36 if not success else 46))
    t0 = gi / FPS
    events.append((t0 + drop / FPS, "release", 1))
    for f, mag in imps:
        if f <= end_f:
            events.append((t0 + f / FPS, "thock" if success else "knock", mag))
    if success:
        events.append((t0 + (first_imp + 4) / FPS, "chime", 1))
    else:
        events.append((t0 + (first_imp + 8) / FPS, "fail", 1))
    for k in range(end_f):
        fnum = k + 1
        im = Image.open(frames[k]).convert("RGB").resize((W, H), Image.LANCZOS)
        im = im.filter(ImageFilter.UnsharpMask(radius=2, percent=60, threshold=2))
        # top darkening band for legibility
        d = ImageDraw.Draw(im)
        text_center(d, 112, f"{label} {val}", f_big, (255, 255, 255))
        # attempt dots
        for j in range(n_total):
            cx = W / 2 + (j - (n_total - 1) / 2) * 44
            col = (255, 255, 255) if j == ci else (110, 110, 110)
            d.ellipse([cx - 9, 82 - 9, cx + 9, 82 + 9], fill=col)
        if not success and fnum >= first_imp + 6:
            draw_x(d, W / 2, 330, 46, (235, 60, 50))
        if success and fnum >= first_imp + 2:
            draw_check(d, W / 2, 330, 52, (70, 220, 110))
            text_center(d, 410, "PERFECT FIT", f_small, (70, 220, 110))
        im.save(os.path.join(out_frames, "c_%05d.jpg" % gi), quality=93)
        gi += 1

dur = gi / FPS
buf = np.zeros(int(SR * (dur + 0.5)))
buf += pad(len(buf))
for t, kind, mag in events:
    if kind == "knock":
        add(buf, knock(0.25 + 0.75 * mag, pitch=rng.uniform(0.85, 1.25)), t)
    elif kind == "thock":
        add(buf, thock(), t)
    elif kind == "chime":
        add(buf, chime(), t)
    elif kind == "fail":
        add(buf, fail_tone(), t)
    elif kind == "release":
        add(buf, whoosh(int(SR * 0.5)) * 0.6, t + 0.05)
buf = buf[: int(SR * dur)]
buf = buf / (np.abs(buf).max() + 1e-9) * 0.85
# fade out
fo = int(SR * 0.25)
buf[-fo:] *= np.linspace(1, 0, fo)
import wave
with wave.open(os.path.join(sd, "audio.wav"), "wb") as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((buf * 32767).astype(np.int16).tobytes())

out = os.path.join(sd, "final.mp4")
subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-framerate", str(FPS), "-i", os.path.join(out_frames, "c_%05d.jpg"),
                "-i", os.path.join(sd, "audio.wav"), "-c:v", "libx264", "-preset", "medium", "-crf", "20",
                "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", out], check=True)
print("OK", out, round(dur, 2), "s", events[:3])
