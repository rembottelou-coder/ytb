"""Compose a single-clip concept short: frames + events.json -> final.mp4 with synced SFX.
python3 compose_generic.py <clip_dir> [caption]
events.json: {"events": [[frame, kind, mag, (opt) pitch_step], ...], "nframes":.., "meta": {"caption":..}}
kinds: knock thock clack click clink thud squish ding whoosh whoosh_short swish pluck pop sparkle chord
event = [frame, kind, mag, (opt) step, (opt) pan -1..1]; output is stereo with reverb
"""
import sys, os, json, glob, subprocess, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
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
# ---- retention (26/11, Studio data: Shorts that open on a frozen frame get swiped by ~75 % of viewers) ----
# 1) hook: drop the frozen lead-in copies and start a few frames before the first sound/action;
# 2) tail: stop ~1.2 s after the last event (finale) instead of lingering;
# 3) loop: crossfade the last frames into the first one so the Shorts player loops seamlessly (rewatches).
if os.environ.get("TRIM", "1") == "1" and not ev.get("meta", {}).get("no_trim") and ev["events"]:
    first_b = open(frames[0], "rb").read()
    nstatic = 1
    while nstatic < len(frames) and os.path.getsize(frames[nstatic]) == len(first_b) and open(frames[nstatic], "rb").read() == first_b:
        nstatic += 1
    evf = sorted(int(e[0]) for e in ev["events"])
    s0 = max(nstatic - 1, evf[0] - 1 - int(os.environ.get("HOOK_PRE", 8)), 0)
    s0 = min(s0, max(0, len(frames) - 60))
    e1 = min(len(frames), evf[-1] - 1 + int(os.environ.get("TAIL", 36)))
    frames = frames[s0:e1]
    ev["events"] = [[e[0] - s0] + list(e[1:]) for e in ev["events"] if e[0] - s0 >= 1]
    print("trim", s0, "->", s0 + len(frames), "static", nstatic, flush=True)
LOOPF = int(os.environ.get("LOOPF", 8))
comp = os.path.join(cd, "comp"); os.makedirs(comp, exist_ok=True)
for f in glob.glob(os.path.join(comp, "*.jpg")):
    os.remove(f)
for i, fp in enumerate(frames):
    im = Image.open(fp).convert("RGB").resize((W, H), Image.LANCZOS)
    im = im.filter(ImageFilter.UnsharpMask(radius=2, percent=50, threshold=2))
    im = ImageEnhance.Color(im).enhance(float(os.environ.get("SAT", 1.18)))      # extra colour pop
    if caption:
        d = ImageDraw.Draw(im)
        tw = d.textlength(caption, font=font)
        d.text(((W - tw) / 2, 150), caption, font=font, fill=(255, 255, 255), stroke_width=6, stroke_fill=(30, 30, 35))
    if i == 0:
        first_im = im.copy()
    elif LOOPF and i >= len(frames) - LOOPF:
        im = Image.blend(im, first_im, (i - (len(frames) - LOOPF) + 1) / (LOOPF + 1))
    im.save(os.path.join(comp, "c_%05d.jpg" % i), quality=93)

n = len(frames)
dur = n / FPS
buf = np.zeros((2, int(SR * (dur + 1))))          # stereo: headphone-friendly ASMR panning
pad = sfx.pad(buf.shape[1], root=float(ev.get("meta", {}).get("root", 261.63)))
buf[0] += pad; buf[1] += pad
counts = {}
prng = np.random.default_rng(len(ev["events"]) * 31 + ev["nframes"])
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
    elif kind == "sparkle":
        s = sfx.sparkle(mag)
    elif kind == "pluck":
        s = sfx.pluck(mag, int(step or 0))
    else:
        pitch = 1.0 if step is None else 2 ** (int(step) * 2 / 12)   # rising whole tones per step
        s = sfx.SOUNDS[kind](mag, pitch)
    # pan: explicit 5th field in [-1,1], else gentle random; final chord / pads stay centred
    pan = float(e[4]) if len(e) > 4 else (0.0 if kind in ("chord", "ding", "whoosh", "swish") else prng.uniform(-0.55, 0.55))
    gl, gr = np.sqrt((1 - pan) / 2) * 1.414, np.sqrt((1 + pan) / 2) * 1.414
    i0 = int(t * SR); j = min(buf.shape[1], i0 + len(s))
    buf[0, i0:j] += gl * s[: j - i0]; buf[1, i0:j] += gr * s[: j - i0]
buf[0] = sfx.reverb(buf[0], seed_=11); buf[1] = sfx.reverb(buf[1], seed_=12)
buf = buf[:, : int(SR * dur)]
buf = np.tanh(1.6 * buf / (np.abs(buf).max() + 1e-9)) / np.tanh(1.6) * 0.9   # soft-clip: louder, punchier
fo = int(SR * 0.3); buf[:, -fo:] *= np.linspace(1, 0, fo)
with wave.open(os.path.join(cd, "audio.wav"), "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((buf.T * 32767).astype(np.int16).tobytes())
out = os.path.join(cd, "final.mp4")
subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-framerate", str(FPS), "-i", os.path.join(comp, "c_%05d.jpg"),
                "-i", os.path.join(cd, "audio.wav"), "-c:v", "libx264", "-preset", "medium", "-crf", "20",
                "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", out], check=True)
print("OK", out, round(dur, 2), "s", counts)
