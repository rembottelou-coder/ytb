"""Concept "ring" (added 26/11, retention: combines the channel's two winning recipes — a note on every bounce
(xylo, 27k views) and suspense (fit "So close at 5°", 38k)): the viral "will it escape?" format.
A glossy ball bounces inside 4 concentric neon rings; each ring has a gap and rotates (alternating directions).
Every bounce plays the next note of a melody and recolours the ball; when the ball slips through a gap the ring pops.
Escape all rings -> big chord. The 2D physics is simulated here (seed search keeps a run with good pacing),
then keyframed and rendered in 3D.
python3 c_ring.py <out_dir> [seed] [res] [samples]   env: RINGS=4  BG  GAP=42
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
K = int(os.environ.get("RINGS", random.choice([4, 4, 5])))
GAP = math.radians(float(os.environ.get("GAP", 44)))
NIGHT = os.environ.get("BG", "") == "night" or (not os.environ.get("BG") and random.random() < 0.8)
BG = "night" if NIGHT else os.environ.get("BG", pick_bg())
RB = 0.15
MINOR = 0.055
R_OUT = 1.85
RADII = [R_OUT * (0.42 + 0.58 * k / (K - 1)) for k in range(K)]
OMEGA = [(1.25 - 0.13 * k) * (1 if k % 2 == 0 else -1) for k in range(K)]
G = 5.5
TMAX = 13.0
Z0 = R_OUT + 0.45          # ring centre height (above the cyclorama floor)
SUB = 8                     # physics substeps per frame


def wrap(a):
    return (a + math.pi) % (2 * math.pi) - math.pi


def simulate(rs):
    """returns per-frame ball positions, bounce frames, escape frames, ring phase offsets"""
    phase = [rs.uniform(-math.pi, math.pi) for _ in range(K)]
    ang = rs.uniform(0, 2 * math.pi)
    sp = rs.uniform(3.2, 4.2)
    x, z, vx, vz = 0.0, 0.25, sp * math.cos(ang), sp * math.sin(ang)
    k = 0
    pos, bounces, escapes = [], [], []
    dt = 1.0 / (FPS * SUB)
    nf = int(TMAX * FPS)
    for f in range(nf):
        for s in range(SUB):
            t = (f * SUB + s) * dt
            vz -= G * dt
            x += vx * dt; z += vz * dt
            if k < K:
                R = RADII[k]
                d = math.hypot(x, z)
                a = math.atan2(z, x)
                rel = wrap(a - (phase[k] + OMEGA[k] * t))
                in_gap = abs(rel) < GAP / 2 - math.asin(min(0.99, RB / R)) * 0.8
                if d + RB >= R - MINOR and not in_gap and d < R:
                    nx, nz = x / d, z / d
                    vn = vx * nx + vz * nz
                    if vn > 0:
                        vx -= 2 * vn * nx; vz -= 2 * vn * nz
                        spd = math.hypot(vx, vz)
                        boost = min(1.02, 8.5 / max(spd, 1e-6))
                        if spd < 3.4:
                            boost = 3.4 / spd
                        vx *= boost; vz *= boost
                        if not bounces or f - bounces[-1][0] >= 2:
                            bounces.append((f, k))
                    x, z = nx * (R - MINOR - RB), nz * (R - MINOR - RB)
                elif d - RB > R + MINOR:
                    escapes.append(f)
                    k += 1
        pos.append((x, z))
        if k >= K and f > escapes[-1] + 40:
            break
    return pos, bounces, escapes, phase


best = None
for attempt in range(400):
    rs = random.Random(seed * 1000 + attempt)
    pos, bounces, escapes, phase = simulate(rs)
    if len(escapes) < K:
        continue
    gaps = [b - a for a, b in zip([0] + escapes[:-1], escapes)]
    ok = escapes[0] > 1.3 * FPS and escapes[-1] < 11.0 * FPS and min(gaps[1:] or [99]) > 0.9 * FPS and len(bounces) >= 14
    if ok:
        best = (pos, bounces, escapes, phase, attempt)
        break
    if best is None or (len(escapes) == K and escapes[-1] < best[2][-1]):
        best = (pos, bounces, escapes, phase, attempt)
pos, bounces, escapes, phase, attempt = best
nframes = min(len(pos), escapes[-1] + 40)
print("ring sim attempt", attempt, "escapes", escapes, "bounces", len(bounces), "nframes", nframes, flush=True)

scn = reset(nframes, seed)
if NIGHT:
    studio((0.035, 0.035, 0.09), strength=0.6)
else:
    studio(BG)

# ---- rings with a gap (arc tubes), rotating about the camera axis (Y) ----
def arc_tube(name, R, r, a0, a1, nseg=160, nmin=16):
    def b(bm):
        rows = []
        n = max(8, int(nseg * (a1 - a0) / (2 * math.pi)))
        for i in range(n + 1):
            a = a0 + (a1 - a0) * i / n
            cx, cz = R * math.cos(a), R * math.sin(a)
            row = []
            for j in range(nmin):
                p = 2 * math.pi * j / nmin
                rr = R + r * math.cos(p)
                row.append(bm.verts.new((rr * math.cos(a), r * math.sin(p), rr * math.sin(a))))
            rows.append(row)
        for i in range(n):
            for j in range(nmin):
                bm.faces.new((rows[i][j], rows[i][(j + 1) % nmin], rows[i + 1][(j + 1) % nmin], rows[i + 1][j]))
        for end in (rows[0], rows[-1]):          # caps
            bm.faces.new(end if end is rows[-1] else list(reversed(end)))
    ob = mesh_from_bm(name, b)
    for p in ob.data.polygons:
        p.use_smooth = True
    return ob


def neon(name, rgb, strength):
    m = plastic(name, rgb, rough=0.18, coat=0.8)
    bsdf = m.node_tree.nodes["Principled BSDF"]
    if "Emission Color" in bsdf.inputs:
        bsdf.inputs["Emission Color"].default_value = (*srgb_to_lin(rgb), 1)
        bsdf.inputs["Emission Strength"].default_value = strength
    return m


off = random.randrange(len(RAINBOW))
ring_cols = [RAINBOW[(off + 2 * k) % len(RAINBOW)] for k in range(K)]
events = []
for k in range(K):
    # the gap is centred on angle 0 of the arc's local frame -> tube spans [GAP/2, 2pi - GAP/2]
    ring = arc_tube(f"ring{k}", RADII[k], MINOR, GAP / 2, 2 * math.pi - GAP / 2)
    set_mat(ring, neon(f"rn{k}", ring_cols[k], 2.2 if NIGHT else 0.6))
    # world angle of the gap centre = phase + omega*t ; rotation about -Y maps local +x angle a to world angle a
    ring.rotation_mode = "XYZ"
    ring.location = (0, 0, Z0)
    fe = escapes[k]
    for f in range(1, nframes + 1, 2):
        t = (f - 1) / FPS
        ring.rotation_euler = (0, -(phase[k] + OMEGA[k] * t), 0)
        ring.keyframe_insert("rotation_euler", frame=f)
    # pop when the ball escapes
    ring.scale = (1, 1, 1); ring.keyframe_insert("scale", frame=fe)
    ring.scale = (1.12, 1.12, 1.12); ring.keyframe_insert("scale", frame=fe + 3)
    ring.scale = (0.001, 0.001, 0.001); ring.keyframe_insert("scale", frame=fe + 8)
    set_interp(ring, "LINEAR")
    events.append([fe, "pop", 0.9, k + 2])
    events.append([fe, "sparkle", 0.55])
    events.append([fe + 1, "whoosh_short", 0.4])

# ---- ball: recolours on every bounce; short comet trail of shrinking copies ----
bm_ = plastic("ballm", RAINBOW[off], rough=0.12, coat=1.0)
bsdf = bm_.node_tree.nodes["Principled BSDF"]
bpy.ops.mesh.primitive_uv_sphere_add(radius=RB, segments=40, ring_count=20, location=(0, 0, 0))
ball = bpy.context.active_object; ball.name = "ball"
for p in ball.data.polygons:
    p.use_smooth = True
set_mat(ball, bm_)
if "Emission Color" in bsdf.inputs:
    bsdf.inputs["Emission Strength"].default_value = 0.35 if NIGHT else 0.0
trail = []
for j in range(1, 7):
    tr = bpy.data.objects.new(f"trail{j}", ball.data); link(tr)
    s = 0.86 ** j
    tr.scale = (s, s, s)
    trail.append(tr)
for f in range(1, nframes + 1):
    x, z = pos[f - 1]
    ball.location = (x, 0, z + Z0); ball.keyframe_insert("location", frame=f)
    for j, tr in enumerate(trail, start=1):
        px, pz = pos[max(0, f - 1 - j)]
        tr.location = (px, 0.02 * j, pz + Z0); tr.keyframe_insert("location", frame=f)


def key_col(rgb, f):
    c = (*srgb_to_lin(rgb), 1)
    bsdf.inputs["Base Color"].default_value = c
    bsdf.inputs["Base Color"].keyframe_insert("default_value", frame=f)
    if "Emission Color" in bsdf.inputs:
        bsdf.inputs["Emission Color"].default_value = c
        bsdf.inputs["Emission Color"].keyframe_insert("default_value", frame=f)


key_col(RAINBOW[off], 1)
# melody: rising pentatonic run that climbs a little higher with every ring escaped
MEL = [0, 2, 4, 5, 7, 4, 5, 7, 9, 7, 9, 11]
for i, (f, k) in enumerate(bounces):
    if f >= nframes:
        break
    key_col(RAINBOW[(off + i + 1) % len(RAINBOW)], f)
    events.append([f, "pluck", 0.75, MEL[i % len(MEL)] % 12 + min(k, 2), 0.8 * pos[f - 1][0] / R_OUT])
    events.append([f, "clink", 0.42, k, 0.8 * pos[f - 1][0] / R_OUT])
for mt in [bm_]:
    if mt.node_tree.animation_data and mt.node_tree.animation_data.action:
        pass
events.append([escapes[-1] + 3, "chord", 1.0])
events.append([escapes[-1] + 5, "sparkle", 1.0])

# ---- cameras: front -> slight 3/4 closer -> front ----
s1 = int(nframes * 0.42); s2 = int(nframes * 0.72)
side = random.choice([1, -1])
multi_camera([(1, (0, -12.5, Z0 + 0.6), (0, 0, Z0), 61),
              (s1, (3.2 * side, -10.4, Z0 + 2.0), (0, 0, Z0), 62),
              (s2, (0, -12.5, Z0 + 0.6), (0, 0, Z0), 61)], push=1.05)
for f0 in (s1, s2):
    events.append([f0, "whoosh_short", 0.25])
caption = random.choice(["Will it escape?", "Every bounce is a note", "Wait for it..."])
finish(out, events, nframes, res, spp, static_until=1,
       meta={"concept": "ring", "rings": K, "bg": BG, "bounces": len(bounces), "caption": caption})
