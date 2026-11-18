"""Concept "dice": colourful dice drop one by one, tumbling, and snap perfectly into a grid tray.
python3 c_dice.py <out_dir> [seed] [res] [samples]
env: GRID=3|4  BG=<pastel>  FACES=six|random|count
"""
import sys, os, math, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh
from mathutils import Euler
from common import *

out = sys.argv[1]
seed = int(sys.argv[2]) if len(sys.argv) > 2 else 1
res = float(sys.argv[3]) if len(sys.argv) > 3 else 0.4
spp = int(sys.argv[4]) if len(sys.argv) > 4 else 10
random.seed(seed)
G = int(os.environ.get("GRID", random.choice([3, 4, 4])))
BG = os.environ.get("BG", pick_bg())
FACES = os.environ.get("FACES", random.choice(["six", "random", "count"]))

S = 0.5            # die size
GAP = 0.12         # wall between slots
CLR = 0.025
INT = 11 if G == 4 else 14   # frames between drops
LEAD = 15
nframes = LEAD + G * G * INT + 50
scn = reset(nframes, seed)
studio(BG)

# ---- die prototype mesh (pips cut with black material) ----
die = box("die", S, S, S)
bevel(die, 0.06, 4)
apply_mods(die)
m_pip = plastic("pip", (0.05, 0.05, 0.06), rough=0.4, coat=0.0)
m_body = plastic("body", (1, 1, 1), rough=0.3)
die.data.materials.append(m_body)
die.data.materials.append(m_pip)
P = S * 0.27
layouts = {1: [(0, 0)], 2: [(-1, -1), (1, 1)], 3: [(-1, -1), (0, 0), (1, 1)], 4: [(-1, -1), (-1, 1), (1, -1), (1, 1)],
           5: [(-1, -1), (-1, 1), (0, 0), (1, -1), (1, 1)], 6: [(-1, -1), (-1, 0), (-1, 1), (1, -1), (1, 0), (1, 1)]}
# face normals: 1:+z 6:-z 2:+x 5:-x 3:+y 4:-y  (opposite faces sum to 7)
faces = {1: ((0, 0, 1), 0, 1), 6: ((0, 0, -1), 0, 1), 2: ((1, 0, 0), 1, 2), 5: ((-1, 0, 0), 1, 2), 3: ((0, 1, 0), 0, 2), 4: ((0, -1, 0), 0, 2)}
cutters = []
for num, (nrm, a1, a2) in faces.items():
    for (u, v) in layouts[num]:
        c = [0.0, 0.0, 0.0]
        ax = [i for i in range(3) if nrm[i] != 0][0]
        c[ax] = nrm[ax] * S / 2
        others = [i for i in range(3) if i != ax]
        c[others[0]] = u * P; c[others[1]] = v * P
        bpy.ops.mesh.primitive_uv_sphere_add(radius=S * 0.075, segments=16, ring_count=8, location=c)
        cutters.append(bpy.context.active_object)
cut = cutters[0]
with bpy.context.temp_override(active_object=cut, selected_editable_objects=cutters, selected_objects=cutters):
    bpy.ops.object.join()
cut.data.materials.append(m_pip)
md = die.modifiers.new("b", "BOOLEAN"); md.operation = "DIFFERENCE"; md.object = cut; md.solver = "EXACT"
md.material_mode = "TRANSFER"
with bpy.context.temp_override(object=die, active_object=die):
    bpy.ops.object.modifier_apply(modifier=md.name)
bpy.data.objects.remove(cut)
for p in die.data.polygons:
    p.use_smooth = True
smooth(die, 40)
die.hide_render = True; die.location = (0, 0, -10)

# rotation that puts face `num` on top
TOP = {1: (0, 0, 0), 6: (math.pi, 0, 0), 2: (0, -math.pi / 2, 0), 5: (0, math.pi / 2, 0), 3: (math.pi / 2, 0, 0), 4: (-math.pi / 2, 0, 0)}

# ---- tray ----
TW = G * (S + 2 * CLR) + (G + 1) * GAP
TH = S * 0.75
tray = box("tray", TW, TW, TH, (0, 0, TH / 2))
for i in range(G):
    for j in range(G):
        x = -TW / 2 + GAP + (S + 2 * CLR) / 2 + i * (S + 2 * CLR + GAP)
        y = -TW / 2 + GAP + (S + 2 * CLR) / 2 + j * (S + 2 * CLR + GAP)
        c = box("c", S + 2 * CLR, S + 2 * CLR, TH, (x, y, TH / 2 + 0.12))
        boolean(tray, c)
bevel(tray, 0.03, 3)
smooth(tray, 40)
tray_col = random.choice([(0.18, 0.16, 0.15), (0.95, 0.95, 0.93), (0.25, 0.35, 0.55)])
set_mat(tray, plastic("tray", tray_col, rough=0.5, coat=0.1))

cols = RAINBOW[:]
random.shuffle(cols)
slots = [(i, j) for j in range(G - 1, -1, -1) for i in range(G)]      # back row first
events = []
for k, (i, j) in enumerate(slots):
    x = -TW / 2 + GAP + (S + 2 * CLR) / 2 + i * (S + 2 * CLR + GAP)
    y = -TW / 2 + GAP + (S + 2 * CLR) / 2 + j * (S + 2 * CLR + GAP)
    d = bpy.data.objects.new(f"d{k}", die.data)
    link(d)
    d.material_slots[0].link = "OBJECT"
    d.material_slots[0].material = plastic(f"dc{k}", cols[k % len(cols)], rough=0.25, coat=0.5)
    if FACES == "six":
        num = 6
    elif FACES == "count":
        num = (k % 6) + 1
    else:
        num = random.randint(1, 6)
    final = Euler(TOP[num])
    spins = [random.choice([-2, -1, 1, 2]) * math.pi / 2 for _ in range(3)]
    start_rot = (final.x + spins[0] + 0.3, final.y + spins[1] - 0.2, final.z + spins[2])
    f0 = LEAD + k * INT
    zr = 0.12 + S / 2
    d.location = (x, y, 6.5)
    key_rot(d, f0, start_rot)
    fl = drop_keys(d, f0, 6.5, zr, x=x, y=y, bounce=0.03)
    key_rot(d, fl, tuple(final))
    key_rot(d, fl + 6, tuple(final))
    set_interp(d, "LINEAR")
    events.append([fl, "clack", 0.8, k % 5])
    events.append([fl, "pluck", 0.7, k])
last = max(e[0] for e in events)
events.append([last + 6, "chord", 1.0])
events.append([last + 8, "sparkle", 0.8])

camera((2.4, -4.4, 6.2), (0, 0.1, 0.25), lens=48 if G == 4 else 56)
caption = {"six": "Only sixes", "count": "1, 2, 3, 4, 5, 6...", "random": random.choice(["Perfect fit", "Fill the tray"])}[FACES]
finish(out, events, nframes, res, spp, static_until=LEAD, meta={"concept": "dice", "grid": G, "bg": BG, "faces": FACES, "caption": caption})
