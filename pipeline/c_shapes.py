"""Concept "shapes": shape-sorter block; colourful pieces (square, circle, triangle, star, hexagon, heart)
fall, rotate into alignment and slide perfectly into their holes, ending flush.
python3 c_shapes.py <out_dir> [seed] [res] [samples]   env: BG, BLOCK=wood|marble|white
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
BG = os.environ.get("BG", pick_bg())
BLOCK = os.environ.get("BLOCK", random.choice(["wood", "white", "dark"]))

LEAD, INT = 15, 26
SHAPES = ["square", "circle", "triangle", "star", "hexagon", "heart"]
random.shuffle(SHAPES)
nframes = LEAD + len(SHAPES) * INT + 50
scn = reset(nframes, seed)
studio(BG)

R = 0.42           # nominal shape radius
DEPTH = 0.55
BW, BL, BH = 3.0, 4.3, 0.85
CLR = 0.03


def outline(kind, r):
    if kind == "square":
        return [(r * 0.86 * x, r * 0.86 * y) for x, y in [(-1, -1), (1, -1), (1, 1), (-1, 1)]]
    if kind == "circle":
        return [(r * math.cos(a), r * math.sin(a)) for a in [2 * math.pi * i / 64 for i in range(64)]]
    if kind == "triangle":
        return [(r * 1.15 * math.cos(a), r * 1.15 * math.sin(a) - r * 0.12) for a in [math.pi / 2 + 2 * math.pi * i / 3 for i in range(3)]]
    if kind == "hexagon":
        return [(r * math.cos(a), r * math.sin(a)) for a in [2 * math.pi * i / 6 for i in range(6)]]
    if kind == "star":
        pts = []
        for i in range(10):
            rr = r * 1.12 if i % 2 == 0 else r * 0.5
            a = math.pi / 2 + math.pi * i / 5
            pts.append((rr * math.cos(a), rr * math.sin(a)))
        return pts
    if kind == "heart":
        pts = []
        for i in range(64):
            t = 2 * math.pi * i / 64
            x = 16 * math.sin(t) ** 3
            y = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
            pts.append((x * r / 15.5, y * r / 15.5 + r * 0.1))
        return pts


def prism(name, pts, h, z0=0.0):
    def b(bm):
        vs = [bm.verts.new((x, y, z0)) for x, y in pts]
        f = bm.faces.new(vs)
        bmesh.ops.reverse_faces(bm, faces=[f]) if f.normal.z > 0 else None
        ext = bmesh.ops.extrude_face_region(bm, geom=[f])
        top = [e for e in ext["geom"] if isinstance(e, bmesh.types.BMVert)]
        bmesh.ops.translate(bm, verts=top, vec=(0, 0, h))
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return mesh_from_bm(name, b)


def grow(pts, d):
    """offset polygon outward approximately by d (scale from centroid by radial distance)."""
    out = []
    for x, y in pts:
        L = math.hypot(x, y) or 1
        out.append((x + d * x / L, y + d * y / L))
    return out


block = box("block", BW, BL, BH, (0, 0, BH / 2))
pos = [(-0.72, 1.35), (0.72, 1.35), (-0.72, 0.0), (0.72, 0.0), (-0.72, -1.35), (0.72, -1.35)]
for kind, (x, y) in zip(SHAPES, pos):
    c = prism("cut", grow(outline(kind, R), CLR), DEPTH + 1, BH - DEPTH)
    c.location = (x, y, 0)
    boolean(block, c)
bevel(block, 0.03, 3)
smooth(block, 30)
if BLOCK == "wood":
    m = plastic("block", (0.78, 0.58, 0.38), rough=0.55, coat=0.1)
elif BLOCK == "white":
    m = plastic("block", (0.95, 0.95, 0.94), rough=0.35, coat=0.2)
else:
    m = plastic("block", (0.17, 0.17, 0.19), rough=0.45, coat=0.2)
set_mat(block, m)

cols = RAINBOW[:]
random.shuffle(cols)
order = list(range(len(SHAPES)))
random.shuffle(order)
events = []
for n, k in enumerate(order):
    kind = SHAPES[k]; x, y = pos[k]
    p = prism(kind, outline(kind, R), DEPTH)
    bevel(p, 0.02, 2)
    smooth(p, 30)
    set_mat(p, plastic(f"p{k}", cols[n % len(cols)], rough=0.25, coat=0.5))
    f0 = LEAD + n * INT
    rest = BH - DEPTH
    above = BH + 0.5
    spin = random.choice([-1, 1]) * random.uniform(1.2, 2.5)
    tilt = random.uniform(-0.5, 0.5)
    p.location = (x, y, 6.0)
    key_rot(p, f0, (tilt, -tilt * 0.6, spin))
    fl = drop_keys(p, f0, 6.0, above, x=x, y=y, settle=False)
    # rotation eases to aligned exactly on arrival above the hole
    key_rot(p, fl, (0, 0, 0))
    glide = 10
    for g in range(1, glide + 1):
        t = g / glide
        e = 1 - (1 - t) ** 2
        key_loc(p, fl + g, (x, y, above + (rest - above) * e))
    land = fl + glide
    key_loc(p, land + 2, (x, y, rest + 0.01))
    key_loc(p, land + 4, (x, y, rest))
    key_rot(p, land + 4, (0, 0, 0))
    set_interp(p, "LINEAR")
    events.append([f0 + 3, "whoosh_short", 0.4])
    events.append([land, "thock", 0.8, n])
    events.append([land, "pluck", 0.6, 2 * n])            # rising melody, one note per piece
    events.append([land + 3, "pop", 0.45, n])              # tiny "suction" pop as it seats flush
last = max(e[0] for e in events)
events.append([last + 3, "chord", 1.0])
events.append([last + 5, "sparkle", 0.8])

camera((2.0, -6.6, 8.2), (0, 0.05, 0.3), lens=42)
caption = random.choice(["Every shape fits", "Shape sorter", "Perfect fit", "Wait for the last one"])
finish(out, events, nframes, res, spp, static_until=LEAD, meta={"concept": "shapes", "bg": BG, "block": BLOCK, "caption": caption})
