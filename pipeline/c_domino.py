"""Concept "domino": rainbow domino chain (spiral / S-curve / heart path) falls in a chain reaction (rigid bodies).
python3 c_domino.py <out_dir> [seed] [res] [samples]   env: PATH=spiral|wave|circle  BG
"""
import sys, os, math, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
from mathutils import Vector
from common import *

out = sys.argv[1]
seed = int(sys.argv[2]) if len(sys.argv) > 2 else 1
res = float(sys.argv[3]) if len(sys.argv) > 3 else 0.4
spp = int(sys.argv[4]) if len(sys.argv) > 4 else 10
random.seed(seed)
SHAPE = os.environ.get("PATHSHAPE", random.choice(["spiral", "spiral", "wave"]))
BG = os.environ.get("BG", pick_bg())
LEAD = 15
scn = reset(400, seed)
studio(BG)

DH, DW, DT = 0.36, 0.18, 0.045
SP = DH * 0.52


def path_points():
    pts = []
    if SHAPE == "spiral":
        a, b = 0.30, 0.095
        th = 2.2
        while True:
            r = a + b * th
            if r > 1.95:
                break
            pts.append((r * math.cos(th), r * math.sin(th)))
            th += SP / r
        pts.reverse()  # start outside, spiral inward
    elif SHAPE == "wave":
        y = -2.3
        while y < 2.6:
            pts.append((1.2 * math.sin(y * 1.6), y))
            dx = 1.2 * 1.6 * math.cos(y * 1.6)
            y += SP / math.sqrt(1 + dx * dx)
    else:  # double circle
        for R0, sgn in ((1.6, 1), (0.95, -1)):
            n = int(2 * math.pi * R0 / SP)
            for i in range(n):
                th = sgn * 2 * math.pi * i / n - math.pi / 2
                pts.append((R0 * math.cos(th), R0 * math.sin(th) + (0 if R0 > 1 else 0)))
    return pts


pts = path_points()
N = len(pts)
nframes = int(os.environ.get("NF", LEAD + N * 2.4 + 55))
scn.frame_end = nframes
doms = []
cols = RAINBOW
for i, (x, y) in enumerate(pts):
    nx, ny = pts[min(i + 1, N - 1)] if i < N - 1 else (2 * x - pts[i - 1][0], 2 * y - pts[i - 1][1])
    ang = math.atan2(ny - y, nx - x)
    d = box(f"dom{i}", DT, DW, DH, (x, y, DH / 2))
    d.rotation_euler = (0, 0, ang)
    bevel(d, 0.008, 2)
    c = cols[int(i / N * len(cols) * 2) % len(cols)]
    set_mat(d, plastic(f"dm{i % 16}", c, rough=0.25, coat=0.5) if i < 16 else bpy.data.materials.get(f"dm{i % 16}"))
    rigid(d, "ACTIVE", "BOX", mass=0.2, fr=0.55, rest=0.05, margin=0.001)
    doms.append(d)
# give each a unique colour material keyed by gradient
mats = {}
for i, d in enumerate(doms):
    t = i / max(1, N - 1) * (len(cols) - 1)
    a, b = cols[int(t)], cols[min(len(cols) - 1, int(t) + 1)]
    f = t - int(t)
    c = tuple(a[k] * (1 - f) + b[k] * f for k in range(3))
    key = tuple(round(v, 2) for v in c)
    if key not in mats:
        mats[key] = plastic(f"g{len(mats)}", c, rough=0.25, coat=0.5)
    set_mat(d, mats[key])

floor = box("floorcol", 40, 40, 0.2, (0, 0, -0.1))
floor.hide_render = True
rigid(floor, "PASSIVE", "BOX", fr=0.6, rest=0.0)

# first domino gets a nudge: animated kinematic pusher
pusher = box("pusher", 0.08, 0.08, 0.08, (0, 0, 0))
pusher.hide_render = True
x0, y0 = pts[0]; x1, y1 = pts[1]
dx, dy = (x1 - x0), (y1 - y0); L = math.hypot(dx, dy); dx /= L; dy /= L
start = (x0 - dx * 0.25, y0 - dy * 0.25, DH * 0.85)
endp = (x0 + dx * 0.05, y0 + dy * 0.05, DH * 0.85)
rigid(pusher, "ACTIVE", "BOX", mass=5)
pusher.rigid_body.kinematic = True
key_loc(pusher, 1, start); key_loc(pusher, LEAD, start); key_loc(pusher, LEAD + 6, endp); key_loc(pusher, LEAD + 12, (endp[0], endp[1], 3))
set_interp(pusher, "LINEAR")
bake_rigid(nframes, substeps=30, iters=30)

# events: click when each domino passes ~35 deg tilt
events = []
fell = [None] * N
for f in range(1, nframes + 1):
    scn.frame_set(f)
    for i, d in enumerate(doms):
        if fell[i] is None:
            up = d.matrix_world.to_3x3() @ Vector((0, 0, 1))
            if up.z < math.cos(math.radians(35)):
                fell[i] = f
done = [f for f in fell if f]
for i, f in enumerate(fell):
    if f:
        events.append([f, "click", 0.5 + 0.3 * random.random()])
        if i % 6 == 0:
            events.append([f, "pluck", 0.45, i // 6])
last = max(done) if done else nframes - 30
events.append([last + 4, "chord", 0.9])
print("fallen", len(done), "of", N, "last", last)

camera((0.0, -3.4, 9.0), (0, 0.05, 0.0), lens=44)
caption = random.choice(["Wait for it...", "Rainbow chain reaction", "Domino effect", ""])
finish(out, events, nframes, res, spp, static_until=LEAD,
       meta={"concept": "domino", "path": SHAPE, "n": N, "fallen": len(done), "last": last, "bg": BG, "caption": caption})
