"""Compose a single-clip concept short: frames + events.json -> final.mp4 with synced SFX.
python3 compose_generic.py <clip_dir> [caption]
events.json: {"events": [[frame, kind, mag, (opt) pitch_step], ...], "nframes":.., "meta": {"caption":..}}
kinds: knock thock clack click clink thud squish ding whoosh whoosh_short swish pluck
"""
import sys, os, json, glob, subprocess, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sfx

cd = sys.argv[1]
ev = json.load(open(os.path.join(cd, "events.json")))
caption = sys.argv[2] if len(sys.argv) > 2 else ev.get("meta", {}).get("caption", "")
W, H, FPS, SR = 1080, 1920, 30, sfx.SR
FONT = "/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf"
font = ImageFont.truetype(FONT, 88)
# shrink long captions so they keep a safe margin on each side (Shorts UI crops the edges)
_fs = 88
while _fs > 48 and ImageDraw.Draw(Image.new("RGB", (8, 8))).textlength(caption, font=font) > W - 160:
    _fs -= 4
    font = ImageFont.truetype(FONT, _fs)
sfx.seed(len(caption) + ev["nframes"])

frames = sorted(glob.glob(os.path.join(cd, "f_*.jpg")))
comp = os.path.join(cd, "comp"); os.makedirs(comp, exist_ok=True)
for f in glob.glob(os.path.join(comp, "*.jpg")):
    os.remove(f)
for i, fp in enumerate(frames):
    im = Image.open(fp).convert("RGB").resize((W, H), Image.LANCZOS)
    im = im.filter(ImageFilter.UnsharpMask(radius=2, percent=50, threshold=2))
    if caption:
        d = ImageDraw.Draw(im)
        tw = d.textlength(caption, font=font)
        d.text(((W - tw) / 2, 150), caption, font=font, fill=(255, 255, 255), stroke_width=6, stroke_fill=(30, 30, 35))
    im.save(os.path.join(comp, "c_%05d.jpg" % i), quality=93)

n = len(frames)
dur = n / FPS
buf = np.zeros(int(SR * (dur + 1)))
buf += sfx.pad(len(buf), root=float(ev.get("meta", {}).get("root", 261.63)))
counts = {}
for e in ev["events"]:
    f, kind, mag = e[0], e[1], float(e[2])
    step = e[3] if len(e) > 3 else None
    t = f / FPS
    if t >= dur:
        continue
    counts[kind] = counts.get(kind, 0) + 1
    if kind == "whoosh":
        s = sfx.whoosh(mag)
    elif kind == "whoosh_short":
        s = sfx.whoosh(mag * 0.6, 0.3)
    elif kind == "swish":
        s = sfx.swish(mag)
    elif kind == "pluck":
        s = sfx.pluck(mag, int(step or 0))
    else:
        pitch = 1.0 if step is None else 2 ** (int(step) * 2 / 12)   # rising whole tones per step
        s = sfx.SOUNDS[kind](mag, pitch)
    i0 = int(t * SR); j = min(len(buf), i0 + len(s)); buf[i0:j] += s[: j - i0]
buf = buf[: int(SR * dur)]
buf = buf / (np.abs(buf).max() + 1e-9) * 0.85
fo = int(SR * 0.3); buf[-fo:] *= np.linspace(1, 0, fo)
with wave.open(os.path.join(cd, "audio.wav"), "wb") as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((buf * 32767).astype(np.int16).tobytes())
out = os.path.join(cd, "final.mp4")
subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-framerate", str(FPS), "-i", os.path.join(comp, "c_%05d.jpg"),
                "-i", os.path.join(cd, "audio.wav"), "-c:v", "libx264", "-preset", "medium", "-crf", "20",
                "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", out], check=True)
print("OK", out, round(dur, 2), "s", counts)
