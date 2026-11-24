"""Concept "boxfill" (added 24/11, user idea: "les boules sous différents angles qui rentrent dans une boîte"):
a rain of candy balls pours into a glass box / hexagon / jar and fills it in rainbow layers. Real rigid-body
physics, shown from several camera angles (wide -> top-down into the box -> low close-up on the layers -> wide).
Sound: dense soft clacks on every landing + a pluck melody that rises with the fill level, chord + sparkle finale.
python3 c_boxfill.py <out_dir> [seed] [res] [samples]   env: SHAPE=box|hex|jar  MODE=bands|mixed  BG  POUR=4.5
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
SHAPE = os.environ.get("SHAPE", random.choice(["box", "box", "hex", "jar"]))
MODE = os.environ.get("MODE", random.choice(["bands", "bands", "mixed"]))
BG = os.environ.get("BG", pick_bg())
POUR = float(os.environ.get("POUR", 4.5))       # seconds of pouring

K = {"box": 4, "hex": 6, "jar": 40}[SHAPE]
AP = 0.70 if SHAPE == "box" else 0.74           # inner apothem
RC = AP / math.cos(math.pi / K)                  # inner circumradius
HB = 1.15                                        # inner height
WT = 0.05                                        # wall thickness
BASE = 0.22                                      # pedestal height (inner floor at BASE + WT)
FLOOR = BASE + WT
RB = 0.105
DAMP = 0.8
VT = 9.81 / -math.log(1 - DAMP)                  # bullet terminal velocity with this damping
TAU = 1 / -math.log(1 - DAMP)

area_in = 0.5 * K * RC * RC * math.sin(2 * math.pi / K)
N = int(0.57 * area_in * HB * 0.86 / (4 / 3 * math.pi * RB ** 3))
N = min(N, 230)
T0 = 0.2
nframes = int((T0 + POUR) * FPS) + 75
scn = reset(nframes, seed)
studio(BG)
scn.gravity = (0, 0, -9.81)

# ---- pedestal + glass vessel ----
ang0 = math.pi / K if K == 4 else 0.0
ped_col = random.choice([(0.97, 0.97, 0.95), (0.12, 0.12, 0.14), (0.98, 0.82, 0.30)])


def prism(name, r_out, h, z0, top_open=True):
    def b(bm):
        bmesh.ops.create_cone(bm, cap_ends=True, segments=K, radius1=r_out, radius2=r_out, depth=h)
        if top_open:
            bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.normal.z > 0.5], context="FACES")
    ob = mesh_from_bm(name, b)
    ob.location = (0, 0, z0 + h / 2)
    ob.rotation_euler = (0, 0, ang0)
    return ob


ped = prism("ped", (AP + WT + 0.12) / math.cos(math.pi / K), BASE, 0.0, top_open=False)
bevel(ped, 0.04, 4)
if K > 12:
    smooth(ped, 40)
set_mat(ped, metal("ped", ped_col, 0.25) if ped_col[2] < 0.5 and ped_col[0] > 0.9 else plastic("ped", ped_col, rough=0.35, coat=0.4))

r_out = (AP + WT) / math.cos(math.pi / K)
vessel = prism("vessel", r_out, HB + WT, BASE)
so = vessel.modifiers.new("s", "SOLIDIFY"); so.thickness = WT; so.offset = -1
bv = vessel.modifiers.new("b", "BEVEL"); bv.width = 0.015; bv.segments = 2; bv.limit_method = "ANGLE"
apply_mods(vessel)
for p in vessel.data.polygons:
    p.use_smooth = K > 12
if K <= 12:
    smooth(vessel, 40)
set_mat(vessel, display_glass("vglass", gloss=0.35))
vessel.visible_glossy = False
vessel.visible_shadow = False

# collision: floor + K thin wall slabs (hidden), robust for bullet
coll = []
fl = box("cfloor", 4, 4, 0.2, (0, 0, FLOOR - 0.1)); coll.append(fl)
for k in range(K):
    a = ang0 + (k + 0.5) * 2 * math.pi / K if K == 4 else (k + 0.5) * 2 * math.pi / K
    # wall centred at apothem distance along the face normal
    a = math.atan2(math.sin(a), math.cos(a))
    side = 2 * RC * math.sin(math.pi / K) + 0.08
    w = box(f"cw{k}", 0.12, side, HB + 3.0, (0, 0, 0))
    w.location = ((AP + 0.06) * math.cos(a), (AP + 0.06) * math.sin(a), FLOOR + (HB + 3.0) / 2 - 0.05)
    w.rotation_euler = (0, 0, a)
    coll.append(w)
for c in coll:
    c.hide_render = True; c.hide_viewport = False
    rigid(c, "PASSIVE", "BOX", fr=0.4, rest=0.25, margin=0.004)

# ---- balls: columns inside the vessel, free fall at terminal velocity, arrivals spread over POUR seconds ----
pts = []
step = 0.29
lim = AP - RB - 0.06
g = -lim
while g <= lim + 1e-6:
    h = -lim
    while h <= lim + 1e-6:
        if K == 4 or math.hypot(g, h) <= lim:
            pts.append((g, h))
        h += step
    g += step
random.shuffle(pts)
top = FLOOR + HB + 0.5
nb = 7 if MODE == "bands" else 0
off = random.randrange(len(RAINBOW))
band_cols = [RAINBOW[(off + i) % len(RAINBOW)] for i in range(7)]
mats = [plastic(f"b{i}", c, rough=0.16, coat=0.9) for i, c in enumerate(RAINBOW)]
band_mats = [plastic(f"bb{i}", c, rough=0.16, coat=0.9) for i, c in enumerate(band_cols)]
balls = []
col_last = {}
for k in range(N):
    t_arr = T0 + POUR * (k / max(1, N - 1)) ** 0.92
    # pick a column whose previous ball is far enough above (no mid-air collisions)
    best = None
    for tries in range(len(pts)):
        c = pts[(k + tries) % len(pts)]
        if t_arr - col_last.get(c, -9) > 0.12:
            best = c; break
    best = best or pts[k % len(pts)]
    col_last[best] = t_arr
    x = best[0] + random.uniform(-0.035, 0.035); y = best[1] + random.uniform(-0.035, 0.035)
    z = top + VT * (t_arr - TAU * (1 - math.exp(-t_arr / TAU)))   # exact damped fall from rest
    bpy.ops.mesh.primitive_uv_sphere_add(radius=RB, segments=20, ring_count=12, location=(x, y, z))
    b = bpy.context.active_object; b.name = f"ball{k}"
    for p in b.data.polygons:
        p.use_smooth = True
    if MODE == "bands":
        set_mat(b, band_mats[min(6, int(7 * k / N))])
    else:
        set_mat(b, mats[k % len(mats)])
    rb = rigid(b, "ACTIVE", "SPHERE", mass=0.05, fr=0.35, rest=0.35, margin=0.002)
    rb.linear_damping = DAMP; rb.angular_damping = 0.4
    balls.append(b)
print("N", N, "shape", SHAPE, "mode", MODE, "VT", round(VT, 2), flush=True)
bake_rigid(nframes, substeps=20, iters=20)

# ---- events from the baked motion: first landing of each ball ----
events = []
prev = {}
pv = {}
landed = {}
topz = []
for f in range(1, nframes + 1):
    scn.frame_set(f)
    for b in balls:
        p = b.matrix_world.translation.copy()
        if b.name in prev:
            v = p - prev[b.name]
            if b.name in pv and b.name not in landed and p.z < FLOOR + HB + 0.3:
                if (v - pv[b.name]).length > 0.06:
                    landed[b.name] = f
            pv[b.name] = v
        prev[b.name] = p
order = sorted(landed.items(), key=lambda kv: kv[1])
last_f = order[-1][1] if order else nframes - 60
for i, (name, f) in enumerate(order):
    frac = i / max(1, len(order) - 1)
    events.append([f, "clack", random.uniform(0.22, 0.42), random.randint(0, 3)])
    if i % 9 == 0:
        events.append([f, "pluck", 0.55 + 0.25 * frac, int(frac * 12)])
    elif i % 9 == 4 and random.random() < 0.5:
        events.append([f, "pop", 0.3, random.randint(0, 4)])
fin = min(nframes - 30, last_f + 10)
events.append([fin, "chord", 1.0]); events.append([fin + 2, "sparkle", 0.9])
scn.frame_set(nframes)
maxz = max(b.matrix_world.translation.z for b in balls)
inside = sum(1 for b in balls if b.matrix_world.translation.z < FLOOR + HB and
             math.hypot(b.matrix_world.translation.x, b.matrix_world.translation.y) < RC + 0.05)
print("landed", len(order), "inside_end", inside, "/", N, "maxz", round(maxz, 2), "rim", round(FLOOR + HB, 2), flush=True)

# ---- cameras: wide -> top-down -> low close-up -> wide (other side) ----
cz = FLOOR + HB * 0.45
s1 = int(nframes * 0.27); s2 = int(nframes * 0.52); s3 = int(nframes * 0.76)
side = random.choice([1, -1])
shots = [(1, (2.5 * side, -4.7, 3.5), (0, 0, cz), 44),
         (s1, (0.25 * side, -1.05, FLOOR + HB + 3.3), (0, 0.12, FLOOR), 28),
         (s2, (0.9 * side, -2.5, FLOOR + 0.55), (0, 0, FLOOR + 0.5), 46),
         (s3, (-2.4 * side, -4.9, 3.1), (0, 0, cz), 44)]
multi_camera(shots)
for f0 in (s1, s2, s3):
    events.append([f0, "whoosh_short", 0.35])
caption = random.choice(["Fill it up!", "Rainbow ball rain", "Watch it fill...", "Every angle"]) if MODE == "bands" else \
    random.choice(["Fill it up!", "Candy ball rain", "Watch it fill..."])
finish(out, events, nframes, res, spp, static_until=1,
       meta={"concept": "boxfill", "shape": SHAPE, "mode": MODE, "n": N, "bg": BG, "caption": caption,
             "inside": inside})
