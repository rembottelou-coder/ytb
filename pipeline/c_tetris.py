"""Concept "tetris" (added 26/11 for variety, from the RUNBOOK idea list "Tetris pieces filling a box"):
glossy candy tetrominoes glide in from above, rotate and drop into an upright board until it is filled
PERFECTLY (no gap), then every row flashes from bottom to top with rising notes and a final chord.
Several camera angles (3/4 wide -> low close-up -> front -> wide).
python3 c_tetris.py <out_dir> [seed] [res] [samples]   env: COLS=6 ROWS=8 BG
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
COLS = int(os.environ.get("COLS", random.choice([6, 6, 8])))
ROWS = int(os.environ.get("ROWS", 8 if COLS == 6 else 7))
if (COLS * ROWS) % 4:
    ROWS += 1
BG = os.environ.get("BG", pick_bg())

# ---------- tiling of the board by tetrominoes, with a drop-valid order ----------
BASE = {"I": [(0, 0), (1, 0), (2, 0), (3, 0)], "O": [(0, 0), (1, 0), (0, 1), (1, 1)],
        "T": [(0, 0), (1, 0), (2, 0), (1, 1)], "S": [(0, 0), (1, 0), (1, 1), (2, 1)],
        "Z": [(1, 0), (2, 0), (0, 1), (1, 1)], "L": [(0, 0), (1, 0), (2, 0), (2, 1)],
        "J": [(0, 0), (1, 0), (2, 0), (0, 1)]}


def norm(cells):
    mx = min(c[0] for c in cells); my = min(c[1] for c in cells)
    return tuple(sorted(((x - mx, y - my) for x, y in cells), key=lambda c: (c[1], c[0])))


ORIENTS = []
for k, cells in BASE.items():
    seen = set(); cur = cells
    for r in range(4):
        n = norm(cur)
        if n not in seen:
            seen.add(n); ORIENTS.append((k, n, r))
        cur = [(-y, x) for x, y in cur]


def tile(rng):
    grid = [[None] * COLS for _ in range(ROWS)]
    pieces = []

    def first_empty():
        for y in range(ROWS):
            for x in range(COLS):
                if grid[y][x] is None:
                    return x, y
        return None

    def rec(depth=0):
        fe = first_empty()
        if fe is None:
            return True
        ex, ey = fe
        opts = ORIENTS[:]
        rng.shuffle(opts)
        # mild preference for variety: avoid the same letter as the previous piece
        if pieces:
            opts.sort(key=lambda o: o[0] == pieces[-1][0])
        for kind, cells, r in opts:
            ax, ay = cells[0]
            pl = [(ex + x - ax, ey + y - ay) for x, y in cells]
            if all(0 <= x < COLS and 0 <= y < ROWS and grid[y][x] is None for x, y in pl):
                for x, y in pl:
                    grid[y][x] = len(pieces)
                pieces.append((kind, pl, r))
                if rec(depth + 1):
                    return True
                pieces.pop()
                for x, y in pl:
                    grid[y][x] = None
        return False

    if not rec():
        return None
    # drop order: a piece can fall straight down once everything below it (in its columns) is placed
    placed = set(); order = []
    while len(order) < len(pieces):
        ok = []
        for i, (kind, pl, r) in enumerate(pieces):
            if i in placed:
                continue
            cells = set(pl); good = True
            for x, y in pl:
                for yy in range(ROWS):
                    if (x, yy) in cells:
                        continue
                    j = grid[yy][x]
                    if yy < y and j not in placed:
                        good = False
                    if yy > y and j in placed:
                        good = False
            if good:
                ok.append(i)
        if not ok:
            return None
        ok.sort(key=lambda i: (min(c[1] for c in pieces[i][1]), rng.random()))
        order.append(ok[0]); placed.add(ok[0])
    return [pieces[i] for i in order]


rng = random.Random(seed)
seq = None
for _ in range(400):
    seq = tile(rng)
    if seq and len({p[0] for p in seq}) >= 5:
        break
assert seq, "no tiling"
NP = len(seq)

# ---------- scene ----------
S = 0.30                    # cell size
GAP = 0.012
LEAD = 10
STAG = int(os.environ.get("STAG", 12))
GLIDE = 9                   # frames of sideways glide + rotation above the board
nfill = LEAD + (NP - 1) * STAG + GLIDE + 22
FLASH0 = nfill + 6
ROWSTEP = 4
nframes = FLASH0 + ROWS * ROWSTEP + 62
scn = reset(nframes, seed)
studio(BG)
scn.render.use_motion_blur = False        # blur across camera cuts makes black artefacts
BW, BH = COLS * S, ROWS * S
X0 = -BW / 2
Z0 = 0.18                                   # board floor height (top of the base)

# board: base, two side posts, back panel, thin glass front
style = random.choice(["white", "black", "gold"])
if style == "gold":
    fm = metal("frame", (1.0, 0.74, 0.32), 0.16)
elif style == "black":
    fm = plastic("frame", (0.07, 0.07, 0.09), rough=0.18, coat=0.8)
else:
    fm = plastic("frame", (0.97, 0.97, 0.96), rough=0.22, coat=0.6)
base = box("base", BW + 0.5, S + 0.5, Z0, (0, 0, Z0 / 2)); bevel(base, 0.03, 3); set_mat(base, fm)
for sx in (-1, 1):
    p = box("post", 0.12, S + 0.16, BH + 0.25, (sx * (BW / 2 + 0.06), 0, Z0 + (BH + 0.25) / 2))
    bevel(p, 0.03, 3); set_mat(p, fm)
back = box("back", BW, 0.05, BH + 0.25, (0, S / 2 + 0.04, Z0 + (BH + 0.25) / 2))
set_mat(back, plastic("backp", (0.10, 0.10, 0.14) if style != "black" else (0.95, 0.95, 0.97), rough=0.35, coat=0.4))
front = box("front", BW, 0.02, BH + 0.25, (0, -S / 2 - 0.03, Z0 + (BH + 0.25) / 2))
set_mat(front, display_glass("fglass", gloss=0.25))
front.visible_glossy = False; front.visible_shadow = False

# candy colours per letter (like the classic game, but saturated rainbow)
off = random.randrange(len(RAINBOW))
letters = list(BASE)
random.shuffle(letters)
LCOL = {k: RAINBOW[(off + 1 + i * 10 // 7) % len(RAINBOW)] for i, k in enumerate(letters)}


def cube_mesh():
    me = bpy.data.meshes.new("cell")
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=S - GAP); bm.to_mesh(me); bm.free()
    return me


events = []
row_mats = {y: [] for y in range(ROWS)}
top = Z0 + BH
for k, (kind, cells, r) in enumerate(seq):
    cx = sum(x for x, y in cells) / 4; cy = sum(y for x, y in cells) / 4
    tx = X0 + (cx + 0.5) * S; tz = Z0 + (cy + 0.5) * S
    piv = link(bpy.data.objects.new(f"p{k}", None))
    for x, y in cells:
        c = link(bpy.data.objects.new(f"p{k}_{x}_{y}", cube_mesh()))
        bev = c.modifiers.new("bev", "BEVEL"); bev.width = 0.035; bev.segments = 3
        for pp in c.data.polygons:
            pp.use_smooth = True
        m = plastic(f"m{k}_{x}_{y}", LCOL[kind], rough=0.15, coat=0.9)
        c.data.materials.append(m)
        row_mats[y].append(m)
        c.parent = piv
        c.location = ((x - cx) * S, 0, (y - cy) * S)
    # glide in from one side above the board while turning a quarter/half turn, then free fall
    f0 = LEAD + k * STAG
    zs = top + 0.85 + 0.1 * (k % 2)
    sx = tx + random.choice([-1, 1]) * random.uniform(0.35, 0.8)
    turns = random.choice([1, 1, 2, -1])
    piv.location = (sx, 0, zs + 1.6); piv.keyframe_insert("location", frame=f0 - 2)
    piv.hide_render = True; piv.keyframe_insert("hide_render", frame=f0 - 2)
    for c in piv.children:
        c.hide_render = True; c.keyframe_insert("hide_render", frame=f0 - 2)
        c.hide_render = False; c.keyframe_insert("hide_render", frame=f0 - 1)
    piv.hide_render = False; piv.keyframe_insert("hide_render", frame=f0 - 1)
    for i in range(GLIDE + 1):
        u = i / GLIDE; e = 1 - (1 - u) ** 3
        piv.location = (sx + (tx - sx) * e, 0, zs + 1.6 * (1 - u) ** 2)
        piv.keyframe_insert("location", frame=f0 + i)
        piv.rotation_euler = (0, turns * math.pi / 2 * (1 - e), 0)
        piv.keyframe_insert("rotation_euler", frame=f0 + i)
    events.append([f0 + 2, "whoosh_short", 0.25, None, (tx / (BW / 2)) * 0.6])
    fl = drop_keys(piv, f0 + GLIDE, zs, tz, x=tx, y=0, bounce=0.02)
    set_interp(piv, "LINEAR")
    pan = max(-0.8, min(0.8, tx / (BW / 2) * 0.7))
    events.append([fl, "thock", 0.75, k % 4, pan])
    events.append([fl, "pluck", 0.6, int(cy) + (k % 3), pan])
    if k == NP - 1:
        events.append([fl + 1, "pop", 0.6, 2, pan])

# rows flash bottom -> top (the board is perfectly full)
for y in range(ROWS):
    f = FLASH0 + y * ROWSTEP
    for m in row_mats[y]:
        b = m.node_tree.nodes["Principled BSDF"]
        es = b.inputs["Emission Strength"]
        b.inputs["Emission Color"].default_value = (1, 1, 1, 1)
        for ff, v in ((f - 1, 0.0), (f + 2, 1.6), (f + 9, 0.0)):
            es.default_value = v; es.keyframe_insert("default_value", frame=ff)
    events.append([f, "ding" if y == ROWS - 1 else "pluck", 0.5 if y == ROWS - 1 else 0.65, y, 0.0])
events.append([FLASH0 + ROWS * ROWSTEP + 4, "chord", 1.0])
events.append([FLASH0 + ROWS * ROWSTEP + 6, "sparkle", 0.9])
events = [[e[0], e[1], e[2]] + ([e[3]] if len(e) > 3 and e[3] is not None else ([0] if len(e) > 4 else []))
          + ([e[4]] if len(e) > 4 else []) for e in events]
print("tetris", COLS, "x", ROWS, NP, "pieces", "".join(p[0] for p in seq), "nframes", nframes, flush=True)

# ---------- cameras ----------
zc = Z0 + BH / 2
side = random.choice([1, -1])
s1 = int(nfill * 0.30); s2 = int(nfill * 0.62); s3 = nfill + 2
shots = [(1, (2.1 * side, -4.7, zc + 2.0), (0, 0, zc + 0.3), 40),
         (s1, (0.9 * side, -2.4, Z0 + 0.35), (0, 0, Z0 + BH * 0.55), 30),
         (s2, (-0.6 * side, -3.6, top + 2.6), (0, 0, zc), 34),
         (s3, (0.0, -5.3, zc + 0.5), (0, 0, zc + 0.12), 44)]
multi_camera(shots)
for f in (s1, s2, s3):
    events.append([f, "whoosh_short", 0.3])
caption = random.choice(["Perfect fit?", "Not a single gap", "Wait for the last piece", "Oddly perfect"])
finish(out, events, nframes, res, spp, static_until=LEAD,
       meta={"concept": "tetris", "cols": COLS, "rows": ROWS, "n": NP, "bg": BG, "frame": style, "caption": caption})
