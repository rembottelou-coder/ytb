"""Concept "galton": bell-curve machine. Balls drop from a gold pipe, bounce left/right through a peg lattice
(scripted binomial random walk, so the bell curve always forms) and stack in bins.
python3 c_galton.py <out_dir> [seed] [res] [samples]   env: BG, NB
"""
import sys, os, math, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
from common import *

out = sys.argv[1]
seed = int(sys.argv[2]) if len(sys.argv) > 2 else 1
res = float(sys.argv[3]) if len(sys.argv) > 3 else 0.4
spp = int(sys.argv[4]) if len(sys.argv) > 4 else 10
random.seed(seed)
BG = os.environ.get("BG", random.choice(list(PASTELS)))
NB = int(os.environ.get("NB", 150))
LEAD = 12
ROWS = 10
DX, DY = 0.22, 0.18
R = 0.044
PEG_R = 0.025
W = 2.5
D = 0.15
TOP = 3.8                     # apex peg z
ROWT = 3                       # frames per row
REL = 1                        # frames between releases
bin_floor = 0.12
bin_top = TOP - ROWS * DY - 0.08
nframes = LEAD + NB * REL + 10 + ROWS * ROWT + 40 + 40
scn = reset(nframes, seed)
studio(BG, wall_y=1.2)

frame_m = plastic("frame", (0.15, 0.15, 0.17), rough=0.35, coat=0.3)
back = box("back", W + 0.3, 0.06, 4.9, (0, D / 2 + 0.03, 2.45))
set_mat(back, plastic("back", (0.97, 0.97, 0.97), rough=0.5, coat=0.0))
for x in (-(W / 2 + 0.06), W / 2 + 0.06):
    s = box("side", 0.12, D + 0.12, 4.9, (x, 0, 2.45)); set_mat(s, frame_m)
base = box("base", W + 0.36, D + 0.12, 0.12, (0, 0, 0.06)); set_mat(base, frame_m)
peg_m = metal("peg", (1.0, 0.75, 0.38), 0.2)
for r in range(ROWS):
    for k in range(-14, 15):
        x = (k - r / 2) * DX
        if abs(x) > W / 2 - 0.08:
            continue
        bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=PEG_R, depth=D, location=(x, 0, TOP - r * DY), rotation=(math.pi / 2, 0, 0))
        set_mat(bpy.context.active_object, peg_m)
for j in range(ROWS + 2):
    x = (j - ROWS / 2) * DX - DX / 2
    if abs(x) > W / 2:
        continue
    d = box("div", 0.02, D, bin_top - bin_floor, (x, 0, bin_floor + (bin_top - bin_floor) / 2)); set_mat(d, frame_m)
bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=0.07, depth=1.2, location=(0, 0, TOP + 0.75))
pipe = bpy.context.active_object; set_mat(pipe, peg_m); smooth(pipe, 40)

palette = random.sample(RAINBOW, 3)
mats = [plastic(f"b{i}", c, rough=0.2, coat=0.6) for i, c in enumerate(palette)]
counts = [0] * (ROWS + 1)
events = [[LEAD, "whoosh", 0.4]]
f = LEAD
for i in range(NB):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=8, radius=R, location=(0, 0, TOP + 0.6))
    b = bpy.context.active_object
    for p in b.data.polygons:
        p.use_smooth = True
    set_mat(b, mats[i % len(mats)])
    f0 = LEAD + i * REL
    zc = TOP + PEG_R + R
    key_loc(b, 1, (0, 0, TOP + 0.6)); key_loc(b, f0, (0, 0, TOP + 0.6))
    key_loc(b, f0 + 3, (0, 0, zc))
    f = f0 + 3
    x = 0.0
    rights = 0
    for r in range(ROWS):
        dirn = 1 if random.random() < 0.5 else -1
        rights += 1 if dirn > 0 else 0
        x1 = x + dirn * DX / 2
        z0 = TOP - r * DY + PEG_R + R
        z1 = TOP - (r + 1) * DY + PEG_R + R
        for k in range(1, ROWT + 1):
            t = k / ROWT
            z = z0 + (z1 - z0) * t * t + 0.05 * 4 * t * (1 - t)
            key_loc(b, f + k, (x + (x1 - x) * t, 0, z))
        f += ROWT
        x = x1
        if i % 9 == 0 and r in (0, 4, 8):
            events.append([f, "clink", 0.15])
    j = rights
    n = counts[j]; counts[j] += 1
    zf = bin_floor + R + (n // 2) * (2 * R * 0.93)
    xf = (j - ROWS / 2) * DX + (-1 if n % 2 == 0 else 1) * (R * 1.05)
    zr = TOP - ROWS * DY + PEG_R + R
    drop = max(zr - zf, 0.01)
    steps = max(2, int(math.sqrt(2 * drop / 9.81) * FPS))
    for k in range(1, steps + 1):
        t = k / steps
        key_loc(b, f + k, (x + (xf - x) * min(1, t * 3), 0, zr - drop * t * t))
    f += steps
    key_loc(b, f + 2, (xf, 0, zf + 0.01)); key_loc(b, f + 3, (xf, 0, zf))
    set_interp(b, "LINEAR")
    if i % 4 == 0:
        events.append([f, "click", 0.25 + 0.2 * random.random()])
events.append([f + 8, "ding", 1.0])
print("bins", counts)

camera((0.0, -8.6, 2.3), (0, 0, 2.2), lens=50)
caption = random.choice(["The bell curve machine", "Wait for the curve", "Satisfying physics", ""])
finish(out, events, nframes, res, spp, static_until=LEAD,
       meta={"concept": "galton", "bg": BG, "balls": NB, "caption": caption, "bins": counts})
