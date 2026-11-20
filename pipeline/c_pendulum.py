"""Concept "pendulum": rainbow pendulum wave - N balls with tuned periods drift into snakes, splits and swirls,
then line up again perfectly at the end. Each ball plays a marimba note at its right-hand turn-around.
python3 c_pendulum.py <out_dir> [seed] [res] [samples]   env: N=12  CYCLE=10 (s)  BG
"""
import sys, os, math, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh
from mathutils import Vector
from common import *

out = sys.argv[1]
seed = int(sys.argv[2]) if len(sys.argv) > 2 else 1
res = float(sys.argv[3]) if len(sys.argv) > 3 else 0.4
spp = int(sys.argv[4]) if len(sys.argv) > 4 else 10
random.seed(seed)
N = int(os.environ.get("N", random.choice([12, 13, 14])))
CYCLE = float(os.environ.get("CYCLE", random.choice([9.0, 10.0])))   # seconds until they all line up again
K = int(os.environ.get("K", 11))                                    # oscillations of the slowest ball per cycle
BG = os.environ.get("BG", pick_bg())
BALLMAT = os.environ.get("BALLS", random.choice(["candy", "candy", "chrome-rainbow"]))

LEAD = 18
TAIL = 40
nframes = int(LEAD + CYCLE * FPS + TAIL)
scn = reset(nframes, seed)
studio(BG)

TH0 = math.radians(24)          # release angle
L0 = 2.6                        # longest string
SPACING = 0.42
R = 0.19
BAR_Z = 3.35
ys = [i * SPACING for i in range(N)]
periods = [CYCLE / (K + i) for i in range(N)]
lengths = [L0 * (periods[i] / periods[0]) ** 2 for i in range(N)]

# frame: gold bar along y on two posts
gold = metal("gold", (1.0, 0.70, 0.28), 0.16)
y0, y1 = -0.45, ys[-1] + 0.45
bar = box("bar", 0.09, (y1 - y0), 0.09, (0, (y0 + y1) / 2, BAR_Z)); bevel(bar, 0.02, 3); set_mat(bar, gold)
for yy in (y0, y1):
    p = box("post", 0.09, 0.09, BAR_Z + 0.05, (0, yy, (BAR_Z + 0.05) / 2)); bevel(p, 0.02, 3); set_mat(p, gold)
    f = box("foot", 1.6, 0.22, 0.07, (0, yy, 0.035)); bevel(f, 0.02, 3); set_mat(f, gold)

stringm = plastic("string", (0.97, 0.97, 0.97), rough=0.5, coat=0.0)
pivots = []
balls = []
for i in range(N):
    piv = link(bpy.data.objects.new(f"piv{i}", None))
    piv.location = (0, ys[i], BAR_Z - 0.045)
    L = lengths[i]
    # V-shaped double string (keeps the swing in the x-z plane, like the real apparatus)
    for side in (-1, 1):
        top = Vector((0, side * 0.13, 0)); bot = Vector((0, 0, -L))
        d = bot - top
        def b(bm, d=d):
            bmesh.ops.create_cone(bm, cap_ends=False, segments=8, radius1=0.006, radius2=0.006, depth=d.length)
        s = mesh_from_bm(f"str{i}{side}", b)
        s.location = (top + bot) / 2
        s.rotation_euler = d.to_track_quat("Z", "Y").to_euler()
        set_mat(s, stringm)
        s.parent = piv
    def sb(bm):
        bmesh.ops.create_uvsphere(bm, u_segments=40, v_segments=24, radius=R)
    ball = mesh_from_bm(f"ball{i}", sb)
    for pgn in ball.data.polygons:
        pgn.use_smooth = True
    ball.location = (0, 0, -L - R * 0.9)
    ball.parent = piv
    c = RAINBOW[int(i / N * len(RAINBOW)) % len(RAINBOW)]
    if BALLMAT == "candy":
        set_mat(ball, plastic(f"b{i}", c, rough=0.18, coat=0.8))
    else:
        set_mat(ball, metal(f"b{i}", srgb_to_lin(c), 0.12))
    pivots.append(piv)
    balls.append(ball)

events = []
for i, piv in enumerate(pivots):
    T = periods[i] * FPS
    for f in range(1, nframes + 1):
        t = max(0, f - LEAD)
        th = TH0 * math.cos(2 * math.pi * t / T)
        piv.rotation_euler = (0, th, 0)
        piv.keyframe_insert("rotation_euler", frame=f)
    set_interp(piv, "LINEAR")
    # marimba note each time the ball turns around on the right (theta = +TH0), from release to the end
    k = 1
    while LEAD + k * T < nframes - 6:
        fr = int(round(LEAD + k * T))
        events.append([fr, "pluck", 0.22, i - 4, -0.7 + 1.4 * i / max(1, N - 1)])
        k += 1
# pattern accents: 1/2, 1/3, 2/3 cycle (2 or 3 groups) get a soft sparkle; the final line-up gets the big chord
for frac in (1 / 3, 1 / 2, 2 / 3):
    events.append([int(LEAD + frac * CYCLE * FPS), "sparkle", 0.6])
events.append([int(LEAD + CYCLE * FPS), "chord", 1.0])
events.append([LEAD, "whoosh_short", 0.5])

mid_y = ys[-1] / 2
camera((3.3, -2.9, 3.9), (-0.2, mid_y * 0.9, 1.5), lens=float(os.environ.get("LENS", 24)))
caption = random.choice(["Wait for them to line up...", "Watch the pattern", "Perfect timing", "Pendulum wave"])
finish(out, events, nframes, res, spp, static_until=LEAD,
       meta={"concept": "pendulum", "n": N, "cycle": CYCLE, "balls": BALLMAT, "bg": BG, "caption": caption,
             "root": 261.63})
