"""Concept "funnel" (added 24/11 for variety, inspired by the "coin vortex / spiral wishing well" videos):
striped candy balls drop one after another into a gravity-well funnel, roll round and round faster and faster,
fall through the hole and stack into a glass tube that ends up exactly full, in rainbow order.
Several camera angles (wide -> top-down on the hypnotic spiral -> close-up on the tube -> wide).
python3 c_funnel.py <out_dir> [seed] [res] [samples]   env: N=10  BG
"""
import sys, os, math, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh
from mathutils import Vector, Quaternion
from common import *

out = sys.argv[1]
seed = int(sys.argv[2]) if len(sys.argv) > 2 else 1
res = float(sys.argv[3]) if len(sys.argv) > 3 else 0.4
spp = int(sys.argv[4]) if len(sys.argv) > 4 else 10
random.seed(seed)
N = int(os.environ.get("N", random.choice([9, 10, 10, 11])))
BG = os.environ.get("BG", pick_bg())

RB = 0.11
RI, RO = 0.21, 1.45
C = 0.40                                   # well depth constant: z(r) = ZTOP - C*(1/r - 1/RO)
BASE_T = 0.08
TUBE_BOT = BASE_T + 0.04
TUBE_IN = RB + 0.025
TUBE_H = N * 2 * RB + 0.07
ZHOLE = TUBE_BOT + TUBE_H + 0.22
ZTOP = ZHOLE + C * (1 / RI - 1 / RO)
R0 = RO - 0.16                              # where balls land on the funnel
SPIRAL = float(os.environ.get("SPIRAL", 2.7))   # seconds of spiralling per ball
STAG = int(os.environ.get("STAG", 13))          # frames between balls
LEAD = 10
DROP_H = 1.3
t_drop = math.sqrt(2 * DROP_H / (9.81 * 0.6))
nframes = LEAD + int(t_drop * FPS) + (N - 1) * STAG + int(SPIRAL * FPS) + 18 + 50
scn = reset(nframes, seed)
studio(BG)
scn.render.use_motion_blur = os.environ.get("MBLUR") == "1"   # off: blur across camera cuts makes black artefacts
scn.render.motion_blur_shutter = 0.45


def zf(r):
    return ZTOP - C * (1 / r - 1 / RO)


# ---- funnel (revolved gravity-well profile) ----
rs = [RI + (RO - RI) * (i / 60) ** 1.8 for i in range(61)] + [RO + 0.10]
SEG = 128


def build(bm):
    rings = []
    for i, r in enumerate(rs):
        z = zf(min(r, RO)) + (0.0 if r <= RO else 0.0)
        rings.append([bm.verts.new((r * math.cos(2 * math.pi * j / SEG), r * math.sin(2 * math.pi * j / SEG), z))
                      for j in range(SEG)])
    for i in range(len(rings) - 1):
        for j in range(SEG):
            bm.faces.new((rings[i][j], rings[i][(j + 1) % SEG], rings[i + 1][(j + 1) % SEG], rings[i + 1][j]))


fun = mesh_from_bm("funnel", build)
for p in fun.data.polygons:
    p.use_smooth = True
so = fun.modifiers.new("s", "SOLIDIFY"); so.thickness = 0.045; so.offset = -1
apply_mods(fun)
fstyle = random.choice(["white", "gold", "black", "candy"])
if fstyle == "gold":
    fm = metal("fun", (1.0, 0.74, 0.32), 0.16)
elif fstyle == "black":
    fm = plastic("fun", (0.07, 0.07, 0.09), rough=0.18, coat=0.8)
elif fstyle == "candy":
    fm = plastic("fun", random.choice([(0.98, 0.98, 0.98), (0.20, 0.55, 1.00), (1.0, 0.35, 0.65)]), rough=0.2, coat=0.8)
else:
    fm = plastic("fun", (0.97, 0.97, 0.96), rough=0.22, coat=0.6)
set_mat(fun, fm)
# neck below the hole
bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=RI + 0.03, depth=0.18, location=(0, 0, ZHOLE - 0.09), end_fill_type="NOTHING")
neck = bpy.context.active_object
so = neck.modifiers.new("s", "SOLIDIFY"); so.thickness = 0.03; apply_mods(neck)
for p in neck.data.polygons:
    p.use_smooth = True
set_mat(neck, fm)

# ---- stand: base disc + 3 legs ----
legm = metal("leg", (0.85, 0.86, 0.9), 0.2) if fstyle != "gold" else metal("leg", (1.0, 0.74, 0.32), 0.2)
bpy.ops.mesh.primitive_cylinder_add(vertices=96, radius=RO + 0.25, depth=BASE_T, location=(0, 0, BASE_T / 2))
base = bpy.context.active_object; bevel(base, 0.03, 3); smooth(base, 40)
set_mat(base, plastic("base", random.choice([(0.97, 0.97, 0.95), (0.12, 0.12, 0.14)]), rough=0.3, coat=0.5))
for k in range(3):
    a = math.pi / 2 + k * 2 * math.pi / 3
    h = ZTOP - BASE_T
    bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=0.035, depth=h,
                                        location=((RO + 0.06) * math.cos(a), (RO + 0.06) * math.sin(a), BASE_T + h / 2))
    leg = bpy.context.active_object; smooth(leg, 40); set_mat(leg, legm)

# ---- glass tube ----
def tube_b(bm):
    bmesh.ops.create_cone(bm, cap_ends=True, segments=64, radius1=TUBE_IN + 0.03, radius2=TUBE_IN + 0.03, depth=TUBE_H + 0.04)
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.normal.z > 0.5], context="FACES")


tube = mesh_from_bm("tube", tube_b)
tube.location = (0, 0, TUBE_BOT - 0.04 + (TUBE_H + 0.04) / 2)
so = tube.modifiers.new("s", "SOLIDIFY"); so.thickness = 0.03; so.offset = -1
apply_mods(tube)
for p in tube.data.polygons:
    p.use_smooth = True
set_mat(tube, display_glass("tglass", gloss=0.35))
tube.visible_glossy = False; tube.visible_shadow = False

# ---- balls (candy colour + white stripe so the rolling is visible) ----
off = random.randrange(len(RAINBOW))
step_c = 1 if N <= 10 else 1
cols = [RAINBOW[(off + i * step_c) % len(RAINBOW)] for i in range(N)]
white = plastic("stripe", (0.98, 0.98, 0.97), rough=0.18, coat=0.9)
theta_in = random.uniform(0, 2 * math.pi)
events = []
balls = []
for k in range(N):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=RB, segments=32, ring_count=16, location=(0, 0, -5))
    b = bpy.context.active_object; b.name = f"ball{k}"
    for p in b.data.polygons:
        p.use_smooth = True
    b.data.materials.append(plastic(f"c{k}", cols[k], rough=0.16, coat=0.9))
    b.data.materials.append(white)
    for p in b.data.polygons:
        if abs(p.center.z) < RB * 0.17:
            p.material_index = 1
    b.rotation_mode = "QUATERNION"
    balls.append(b)

    # 1) drop in from above onto the funnel at R0
    x0, y0 = R0 * math.cos(theta_in), R0 * math.sin(theta_in)
    s0 = C / R0 ** 2
    zc0 = zf(R0) + RB / math.sqrt(1 + s0 * s0)
    f0 = LEAD + k * STAG
    key_loc(b, f0 - 1, (x0, y0, -5))           # parked below the floor before its turn
    b.hide_render = True; b.keyframe_insert("hide_render", frame=f0 - 1)
    b.hide_render = False; b.keyframe_insert("hide_render", frame=f0)
    fl = drop_keys(b, f0, zc0 + DROP_H, zc0, x=x0, y=y0, settle=False)
    events.append([fl, "pop", 0.55, k % 5])
    events.append([fl, "thock", 0.35, k % 4])

    # 2) spiral: r shrinks, angular speed grows (~ angular momentum), rolling rotation keyed every frame
    nf = int(SPIRAL * FPS)
    th = theta_in
    q = Quaternion((1, 0, 0, 0))
    prev = Vector((x0, y0, zc0))
    w0 = 2.3
    for i in range(1, nf + 1):
        u = i / nf
        r = RI + (R0 - RI) * (1 - u) ** 1.15
        w = min(24.0, w0 * (R0 / r) ** 1.5)
        th += w / FPS
        s = C / r ** 2
        nr = math.sqrt(1 + s * s)
        rc = r - RB * s / nr
        zc = zf(r) + RB / nr
        p = Vector((rc * math.cos(th), rc * math.sin(th), zc))
        d = p - prev
        if d.length > 1e-6:
            nrm = Vector((-s * math.cos(th), -s * math.sin(th), 1)).normalized()
            ax = nrm.cross(d.normalized())
            q = Quaternion(ax, d.length / RB) @ q
        b.location = p; b.keyframe_insert("location", frame=fl + i)
        b.rotation_quaternion = q; b.keyframe_insert("rotation_quaternion", frame=fl + i)
        prev = p
    f_hole = fl + nf
    events.append([f_hole - 4, "whoosh_short", 0.45])

    # 3) through the hole and down the tube onto the stack
    zl = TUBE_BOT + RB + k * 2 * RB
    key_loc(b, f_hole + 2, (0, 0, ZHOLE - 0.2))
    b.rotation_quaternion = q; b.keyframe_insert("rotation_quaternion", frame=f_hole + 2)
    fland = drop_keys(b, f_hole + 2, ZHOLE - 0.2, zl, x=0, y=0, bounce=0.025)
    events.append([fland, "clink", 0.75, k])
    events.append([fland, "pluck", 0.7, k])
    set_interp(b, "LINEAR")
last = max(e[0] for e in events if e[1] == "clink")
events.append([last + 5, "chord", 1.0])
events.append([last + 7, "sparkle", 0.9])
print("N", N, "nframes", nframes, "last landing", last, "funnel", fstyle, flush=True)

# ---- cameras ----
zmid = ZTOP * 0.52
s1 = int(nframes * 0.24); s2 = int(nframes * 0.50); s3 = int(nframes * 0.77)
side = random.choice([1, -1])
shots = [(1, (2.9 * side, -5.4, ZTOP + 4.0), (0, 0, ZTOP * 0.47), 36),
         (s1, (0.12 * side, -0.5, ZTOP + 4.2), (0, 0, ZHOLE), 30),
         (s2, (1.0 * side, -2.7, TUBE_BOT + TUBE_H * 0.55), (0, 0, TUBE_BOT + TUBE_H * 0.5), 42),
         (s3, (-2.9 * side, -5.6, ZTOP + 3.4), (0, 0, ZTOP * 0.45), 36)]
multi_camera(shots)
for f in (s1, s2, s3):
    events.append([f, "whoosh_short", 0.3])
caption = random.choice(["Round and round...", "Wait for the last one", "Perfect fit?", "So hypnotic"])
finish(out, events, nframes, res, spp, static_until=LEAD,
       meta={"concept": "funnel", "n": N, "bg": BG, "funnel": fstyle, "caption": caption})
