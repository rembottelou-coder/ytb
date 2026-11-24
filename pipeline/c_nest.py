"""Concept "nest": hollow shapes (squares / hexagons / circles) drop one into another, perfect fit, tops end flush.
python3 c_nest.py <out_dir> [seed] [res] [samples]
env: SHAPE=4|6|64  N=6  BG=peach
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
SEG = int(os.environ.get("SHAPE", random.choice([4, 4, 6, 64])))
N = int(os.environ.get("N", random.choice([5, 6, 7])))
BG = os.environ.get("BG", pick_bg())

LEAD = 15
STEP = 30         # frames between drops
nframes = LEAD + N * STEP + 45
scn = reset(nframes, seed)
studio(BG)

WALL, BOT, CLR = 0.09, 0.09, 0.018
H0 = 0.55 + N * BOT          # outer box height so the smallest is still a visible cup
A0 = 1.35                    # outer apothem of the largest
cosn = math.cos(math.pi / SEG)

def prism(name, apo, h, z0):
    r = apo / cosn
    def b(bm):
        bmesh.ops.create_cone(bm, cap_ends=True, segments=SEG, radius1=r, radius2=r, depth=h)
    ob = mesh_from_bm(name, b)
    for v in ob.data.vertices:
        v.co.z += h / 2
    ob.location.z = z0
    if SEG == 4:
        ob.rotation_euler.z = math.pi / 4
    return ob

cols = RAINBOW[:]
if random.random() < 0.5:
    cols.reverse()
start = random.randint(0, 7)
boxes = []
apo, h = A0, H0
for i in range(N):
    outer = prism(f"box{i}", apo, h, 0)
    inner = prism("cut", apo - WALL, h + 1, BOT)
    boolean(outer, inner)
    bevel(outer, 0.012, 2)
    smooth(outer, 40)
    set_mat(outer, plastic(f"m{i}", cols[(start + i) % len(cols)], rough=0.32))
    boxes.append((outer, apo, h))
    apo = apo - WALL - CLR
    h = h - BOT

events = []
# box 0 sits on the floor from the start
for i, (ob, apo, h) in enumerate(boxes):
    rest_z = i * BOT
    if i == 0:
        ob.location.z = 0
        continue
    f0 = LEAD + (i - 1) * STEP
    z_top = 7.5
    rim = H0 + 0.05          # where it enters the outer cup (all tops flush at H0)
    # free fall to just above the rim
    fl = drop_keys(ob, f0, z_top, rim - h + 0.0 + 0.6, settle=False)
    # air-cushion glide: slow ease into place
    glide = 14
    key_loc(ob, fl, (0, 0, rim - h + 0.6))
    for k in range(1, glide + 1):
        t = k / glide
        e = 1 - (1 - t) ** 2.2
        key_loc(ob, fl + k, (0, 0, (rim - h + 0.6) + (rest_z - (rim - h + 0.6)) * e))
    land = fl + glide
    key_loc(ob, land + 2, (0, 0, rest_z + 0.012))
    key_loc(ob, land + 4, (0, 0, rest_z))
    set_interp(ob, "LINEAR")
    events.append([fl, "whoosh_short", 0.5])
    events.append([land, "thock", 0.5 + 0.5 * i / N, i])   # 4th field = pitch step
    events.append([land, "pluck", 0.55 + 0.3 * i / N, i])  # rising melody on every landing (18/11 feedback)
    events.append([land + 1, "pop", 0.35, i])
_end = events[-1][0] + 3
events.append([_end, "chord", 1.0])
events.append([_end + 2, "sparkle", 0.8])

cam_h = 7.6
camera((3.7, -5.6, 6.6), (0, 0, 0.75), lens=44)
caption = random.choice(["Perfect fit?", "Wait for the last one", "So satisfying", "Will it fit?"])
finish(out, events, nframes, res, spp, static_until=LEAD,
       meta={"concept": "nest", "shape": SEG, "n": N, "bg": BG, "caption": caption})
