"""Concept "xylo": rainbow xylophone staircase - candy balls bounce down a zigzag of xylophone bars, every hit plays
the bar's marimba note (balls are staggered so their melodies overlap in harmony), the bar wobbles, and each ball
ends in its slot of a gold tray -> final chord.
python3 c_xylo.py <out_dir> [seed] [res] [samples]   env: BARS=8  BALLS=5  HOP=15 (frames)  BG
"""
import sys, os, math, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh
from common import *

out = sys.argv[1]
seed = int(sys.argv[2]) if len(sys.argv) > 2 else 1
res = float(sys.argv[3]) if len(sys.argv) > 3 else 0.4
spp = int(sys.argv[4]) if len(sys.argv) > 4 else 10
random.seed(seed)
NB = int(os.environ.get("BARS", random.choice([7, 8, 8])))
NBALL = int(os.environ.get("BALLS", random.choice([4, 5, 5, 6])))
HOP = int(os.environ.get("HOP", random.choice([14, 15, 16])))
STAG = int(os.environ.get("STAG", HOP + HOP // 2))   # 1.5 hops apart -> off-beat notes, balls on alternate sides
BG = os.environ.get("BG", pick_bg())
BARMAT = os.environ.get("BARMAT", random.choice(["candy", "candy", "metal"]))
G = 9.81 * 0.8
R = 0.15
DX = 0.52                      # bar centre offset left / right
DZ = 0.40
TOPZ = 0.95 + (NB - 1) * DZ
LEAD = 14
TAIL = 40

bar_x = [(-1) ** i * DX for i in range(NB)]
bar_z = [TOPZ - i * DZ for i in range(NB)]           # top surface of each bar
bar_len = [1.25 - 0.55 * i / max(1, NB - 1) for i in range(NB)]   # shorter bar = higher note
TH = 0.11

# tray slots on the floor, centred under the staircase
TRAY_Z = 0.07
slot_x = [(k - (NBALL - 1) / 2) * 0.34 for k in range(NBALL)]

t_first = 0.55                 # seconds of the first drop onto bar 0
f_first = int(round(t_first * FPS))
last_ball_land = LEAD + (NBALL - 1) * STAG + f_first + (NB - 1) * HOP + int(HOP * 1.6)
nframes = last_ball_land + TAIL
scn = reset(nframes, seed)
studio(BG)

# ---- bars + gold towers ----
gold = metal("gold", (1.0, 0.70, 0.28), 0.16)
bars = []
for i in range(NB):
    c = RAINBOW[int(i / NB * 9) % len(RAINBOW)]
    ob = box(f"bar{i}", 0.44, bar_len[i], TH, (bar_x[i], 0, bar_z[i] - TH / 2))
    bevel(ob, 0.025, 3)
    if BARMAT == "candy":
        set_mat(ob, plastic(f"bm{i}", c, rough=0.2, coat=0.8))
    else:
        set_mat(ob, metal(f"bm{i}", srgb_to_lin(c), 0.14))
    bars.append(ob)
    # gold pins from the bar ends out to the tower poles
    PY = 0.72
    for s in (1,):            # cantilevered from the back poles only (clean front view)
        y0 = s * bar_len[i] / 2; y1 = s * PY
        pin = box(f"pin{i}{s}", 0.05, abs(y1 - y0) + 0.04, 0.05, (bar_x[i], (y0 + y1) / 2, bar_z[i] - TH / 2))
        set_mat(pin, gold)
for side in (-1, 1):
    for s in (1,):
        hgt = TOPZ + 0.25
        def cb(bm, hgt=hgt):
            bmesh.ops.create_cone(bm, cap_ends=True, segments=20, radius1=0.035, radius2=0.035, depth=hgt)
        p = mesh_from_bm("pole", cb)
        p.location = (side * DX, s * 0.72, hgt / 2)
        for pg in p.data.polygons:
            pg.use_smooth = True
        set_mat(p, gold)
        def kb(bm):
            bmesh.ops.create_uvsphere(bm, u_segments=20, v_segments=12, radius=0.08)
        k = mesh_from_bm("knob", kb); k.location = (side * DX, s * 0.72, hgt + 0.02)
        for pg in k.data.polygons:
            pg.use_smooth = True
        set_mat(k, gold)

# gold tray with one dimple per ball
tray_w = (NBALL - 1) * 0.34 + 0.5
tray = box("tray", tray_w, 0.42, 0.08, (0, 0, 0.04 - 0.02)); bevel(tray, 0.03, 3); set_mat(tray, gold)
lip_m = plastic("lip", (1.0, 1.0, 1.0), rough=0.25, coat=0.6)
for s in (-1, 1):
    lip = box("lip", tray_w, 0.05, 0.08, (0, s * 0.2, 0.08)); bevel(lip, 0.02, 3); set_mat(lip, gold)

# ---- balls ----
def sb(bm):
    bmesh.ops.create_uvsphere(bm, u_segments=36, v_segments=20, radius=R)
balls = []
events = []
bar_hits = [[] for _ in range(NB)]
for k in range(NBALL):
    ob = mesh_from_bm(f"ball{k}", sb)
    for pg in ob.data.polygons:
        pg.use_smooth = True
    c = RAINBOW[(k * 2 + 1) % len(RAINBOW)] if NBALL <= 5 else RAINBOW[int(k / NBALL * 10) % 10]
    set_mat(ob, plastic(f"ball{k}", c, rough=0.15, coat=0.9))
    f0 = LEAD + k * STAG
    zc0 = bar_z[0] + R          # ball centre when resting on bar 0
    zstart = zc0 + 0.5 * G * t_first ** 2
    # hidden high above the frame before its release
    key_loc(ob, 1, (bar_x[0], 0, zstart + 3.0))
    key_loc(ob, f0 - 1, (bar_x[0], 0, zstart + 3.0))
    for f in range(f0, f0 + f_first + 1):
        t = (f - f0) / FPS
        key_loc(ob, f, (bar_x[0], 0, max(zc0, zstart - 0.5 * G * t * t)))
    fh = f0 + f_first
    hits = [(fh, 0)]
    pos = (bar_x[0], 0.0, zc0)
    # hops bar i -> bar i+1, then a longer hop into the tray slot
    targets = [(bar_x[i], 0.0, bar_z[i] + R, HOP) for i in range(1, NB)] + [(slot_x[k], 0.0, TRAY_Z + R, int(HOP * 1.6))]
    for j, (tx, ty, tz, dur) in enumerate(targets):
        T = dur / FPS
        vz = (tz - pos[2] + 0.5 * G * T * T) / T
        for df in range(1, dur + 1):
            t = df / FPS
            a = df / dur
            key_loc(ob, fh + df, (pos[0] + (tx - pos[0]) * a, pos[1] + (ty - pos[1]) * a, pos[2] + vz * t - 0.5 * G * t * t))
        # spin a little while flying
        fh += dur
        pos = (tx, ty, tz)
        if j < NB - 1:
            hits.append((fh, j + 1))
    # settle in the slot: two tiny bounces
    key_loc(ob, fh + 4, (pos[0], 0, pos[2] + 0.06)); key_loc(ob, fh + 8, pos)
    key_loc(ob, fh + 10, (pos[0], 0, pos[2] + 0.015)); key_loc(ob, fh + 12, pos)
    key_loc(ob, nframes, pos)
    set_interp(ob, "LINEAR")
    pan_of = lambda x: max(-0.8, min(0.8, x / DX * 0.6))
    for (f, i) in hits:
        events.append([f, "pluck", 0.30, i, pan_of(bar_x[i])])
        events.append([f, "clink", 0.18, i, pan_of(bar_x[i])])
        bar_hits[i].append(f)
    events.append([fh, "thock", 0.55, k, pan_of(slot_x[k])])
    events.append([fh, "pop", 0.35, None, pan_of(slot_x[k])])
    balls.append(ob)

# bar wobble: a damped tilt after each hit
for i, ob in enumerate(bars):
    rot = {}
    for f in bar_hits[i]:
        for df in range(0, 18):
            a = math.radians(3.0) * math.exp(-df / 5.0) * math.sin(df * 1.3)
            rot[f + df] = rot.get(f + df, 0) + a
    key_rot(ob, 1, (0, 0, 0))
    for f in sorted(rot):
        key_rot(ob, f, (0, rot[f] * (-1) ** i, 0))
        if f + 1 not in rot:
            key_rot(ob, f + 1, (0, 0, 0))
    set_interp(ob, "LINEAR")

events.append([last_ball_land + 2, "chord", 1.0])
events.append([last_ball_land + 4, "sparkle", 0.8])
events.append([LEAD, "whoosh_short", 0.45])

midz = TOPZ / 2 + 0.25
camera((0.9, -4.8, midz + 1.9), (0, 0.15, midz - 0.3), lens=float(os.environ.get("LENS", 33)))
caption = random.choice(["Listen to the melody...", "Every bar plays a note", "Wait for the last ball",
                         "Xylophone stairs"])
finish(out, events, nframes, res, spp, static_until=LEAD,
       meta={"concept": "xylo", "bars": NB, "balls": NBALL, "hop": HOP, "barmat": BARMAT, "bg": BG,
             "caption": caption, "root": 261.63})
