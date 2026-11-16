"""Perfect-fit sliced-object render. Usage:
python3 scene.py <out_dir> <angle_deg> <success 0|1> [res_scale] [samples] [frames] [seed] [style]
style: sphere | star | heart  (cross-section shape of the falling object)
"""
import sys, math, os, random
import bpy, bmesh
from mathutils import Vector, Matrix

out_dir = sys.argv[1]
angle = float(sys.argv[2])
success = sys.argv[3] == "1"
res_scale = float(sys.argv[4]) if len(sys.argv) > 4 else 0.5
samples = int(sys.argv[5]) if len(sys.argv) > 5 else 24
nframes = int(sys.argv[6]) if len(sys.argv) > 6 else 90
seed = int(sys.argv[7]) if len(sys.argv) > 7 else 1
palette = sys.argv[8] if len(sys.argv) > 8 else "oak"
NSLAB = int(sys.argv[9]) if len(sys.argv) > 9 else 9
frame_start = int(sys.argv[10]) if len(sys.argv) > 10 else 1
frame_end = int(sys.argv[11]) if len(sys.argv) > 11 else nframes
random.seed(seed)

bpy.ops.wm.read_factory_settings(use_empty=True)
scn = bpy.context.scene
scn.frame_start, scn.frame_end = 1, nframes
scn.render.fps = 30

R = 1.0            # sphere radius
GAP = 0.10        # gap between slabs
CLR = 0.012         # slot clearance
BLOCK = 2.9        # block width
BH = 2.3           # block height
POCKET = 2.0 + 0.02  # pocket depth (sphere sinks flush)

# ---------------- materials ----------------
PALETTES = {
    "oak":    [(0.20, 0.085, 0.030), (0.065, 0.024, 0.008), (0.48, 0.25, 0.10), (0.20, 0.09, 0.03)],
    "walnut": [(0.085, 0.040, 0.018), (0.025, 0.011, 0.005), (0.55, 0.33, 0.15), (0.26, 0.13, 0.05)],
    "maple":  [(0.50, 0.30, 0.13), (0.24, 0.12, 0.045), (0.12, 0.05, 0.02), (0.035, 0.014, 0.006)],
    "cherry": [(0.26, 0.07, 0.025), (0.09, 0.02, 0.008), (0.55, 0.32, 0.14), (0.25, 0.12, 0.045)],
}
pal = PALETTES[palette]

def wood_mat(name, c1, c2, scale, rough=0.45, ring=6.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree; n = nt.nodes; l = nt.links
    bsdf = n["Principled BSDF"]
    tc = n.new("ShaderNodeTexCoord")
    mp = n.new("ShaderNodeMapping")
    # stretch along Y so grain runs lengthwise
    mp.inputs["Scale"].default_value = (scale, scale * 0.12, scale)
    mp.inputs["Location"].default_value = (random.random() * 10, random.random() * 10, random.random() * 10)
    l.new(tc.outputs["Object"], mp.inputs["Vector"])
    # warp coordinates gently with low-freq noise
    warp = n.new("ShaderNodeTexNoise")
    warp.inputs["Scale"].default_value = 1.2
    warp.inputs["Detail"].default_value = 2
    l.new(mp.outputs["Vector"], warp.inputs["Vector"])
    vmix = n.new("ShaderNodeMix"); vmix.data_type = "VECTOR"
    vmix.inputs[0].default_value = 0.28
    l.new(mp.outputs["Vector"], vmix.inputs[4])
    l.new(warp.outputs["Color"], vmix.inputs[5])
    rings = n.new("ShaderNodeTexWave")
    rings.wave_type = "RINGS"; rings.rings_direction = "Y"
    rings.inputs["Scale"].default_value = ring
    rings.inputs["Distortion"].default_value = 3.0
    rings.inputs["Detail"].default_value = 3
    l.new(vmix.outputs[1], rings.inputs["Vector"])
    pores = n.new("ShaderNodeTexNoise")
    pores.inputs["Scale"].default_value = 60
    pores.inputs["Detail"].default_value = 4
    l.new(vmix.outputs[1], pores.inputs["Vector"])
    pr = n.new("ShaderNodeMath"); pr.operation = "POWER"
    pr.inputs[1].default_value = 2.2
    l.new(rings.outputs["Fac"], pr.inputs[0])
    mix = n.new("ShaderNodeMix"); mix.data_type = "FLOAT"
    mix.inputs[0].default_value = 0.22
    l.new(pr.outputs[0], mix.inputs[2])
    l.new(pores.outputs["Fac"], mix.inputs[3])
    ramp = n.new("ShaderNodeValToRGB")
    e0, e1 = ramp.color_ramp.elements
    e0.color = (*c1, 1); e1.color = (*c2, 1)
    e0.position = 0.15; e1.position = 0.75
    l.new(mix.outputs[0], ramp.inputs["Fac"])
    l.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = rough
    if "Coat Weight" in bsdf.inputs:
        bsdf.inputs["Coat Weight"].default_value = 0.25
        bsdf.inputs["Coat Roughness"].default_value = 0.25
    bump = n.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.08
    bump.inputs["Distance"].default_value = 0.02
    l.new(mix.outputs[0], bump.inputs["Height"])
    l.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return m

mat_block = wood_mat("block", pal[0], pal[1], 0.9, 0.5, 5.0)
mat_ball = wood_mat("ball", pal[2], pal[3], 1.1, 0.35, 7.0)

# ---------------- geometry helpers ----------------
def box_obj(name, x0, x1, y0, y1, z0, z1):
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co.x = x0 if v.co.x < 0 else x1
        v.co.y = y0 if v.co.y < 0 else y1
        v.co.z = z0 if v.co.z < 0 else z1
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    scn.collection.objects.link(ob)
    return ob

def apply_bool(target, cutter, op):
    md = target.modifiers.new("b", "BOOLEAN")
    md.operation = op
    md.object = cutter
    md.solver = "EXACT"
    bpy.context.view_layer.objects.active = target
    with bpy.context.temp_override(object=target, active_object=target):
        bpy.ops.object.modifier_apply(modifier=md.name)

def make_sphere(name):
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=96, v_segments=48, radius=R)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    scn.collection.objects.link(ob)
    return ob

# slab bounds along X
width = 2 * R
slab_t = (width - GAP * (NSLAB - 1)) / NSLAB
bounds = []
x = -R
for i in range(NSLAB):
    bounds.append((x, x + slab_t))
    x += slab_t + GAP

# ---- block with pocket ----
block = box_obj("Block", -BLOCK / 2, BLOCK / 2, -BLOCK / 2, BLOCK / 2, 0, BH)
for (x0, x1) in bounds:
    xm = 0 if x0 < 0 < x1 else min(abs(x0), abs(x1))
    h = math.sqrt(max(R * R - xm * xm, 0.0001))
    cut = box_obj("cut", x0 - CLR, x1 + CLR, -h - CLR, h + CLR, BH - POCKET, BH + 1)
    apply_bool(block, cut, "DIFFERENCE")
    bpy.data.objects.remove(cut)
# bevel the outer edges a bit
bv = block.modifiers.new("bev", "BEVEL")
bv.width = 0.025
bv.segments = 2
bv.limit_method = "ANGLE"
block.data.materials.clear(); block.data.materials.append(mat_block)
for p_ in block.data.polygons: p_.material_index = 0

# ---- slabs ----
slabs = []
for i, (x0, x1) in enumerate(bounds):
    s = make_sphere(f"slab{i}")
    c = box_obj("c", x0, x1, -2, 2, -2, 2)
    apply_bool(s, c, "INTERSECT")
    bpy.data.objects.remove(c)
    for p in s.data.polygons:
        p.use_smooth = True
    s.data.materials.clear(); s.data.materials.append(mat_ball)
    for p_ in s.data.polygons: p_.material_index = 0
    sb = s.modifiers.new("bev", "BEVEL"); sb.width = 0.012; sb.segments = 2; sb.limit_method = "ANGLE"; sb.harden_normals = True
    with bpy.context.temp_override(object=s, active_object=s, selected_objects=[s], selected_editable_objects=[s]):
        bpy.ops.object.shade_smooth_by_angle(angle=math.radians(35))
    slabs.append(s)

# group parent for rotation / fall
pivot = bpy.data.objects.new("pivot", None)
scn.collection.objects.link(pivot)
for s in slabs:
    s.parent = pivot

rest_z = BH - POCKET + R           # sphere center when sunk
start_z = rest_z + 4.2
pivot.rotation_euler = (0, 0, math.radians(angle))

g = 9.81 * 0.55  # slightly slowed gravity for drama (scene units)
drop_start = 18     # frames hold before release
fps = 30

if success:
    # analytical free fall into pocket with tiny settle bounce
    dist = start_z - rest_z
    t_fall = math.sqrt(2 * dist / g)
    f_end = drop_start + t_fall * fps
    pivot.location = (0, 0, start_z)
    pivot.keyframe_insert("location", frame=1)
    pivot.keyframe_insert("location", frame=drop_start)
    f = drop_start
    while f < f_end:
        t = (f - drop_start) / fps
        pivot.location = (0, 0, start_z - 0.5 * g * t * t)
        pivot.keyframe_insert("location", frame=f)
        f += 1
    pivot.location = (0, 0, rest_z)
    pivot.keyframe_insert("location", frame=math.ceil(f_end))
    # a little woody "thunk" settle
    pivot.location = (0, 0, rest_z + 0.035)
    pivot.keyframe_insert("location", frame=math.ceil(f_end) + 3)
    pivot.location = (0, 0, rest_z)
    pivot.keyframe_insert("location", frame=math.ceil(f_end) + 6)
    for fc in pivot.animation_data.action.fcurves if hasattr(pivot.animation_data.action, "fcurves") else []:
        for kp in fc.keyframe_points:
            kp.interpolation = "LINEAR"
else:
    # rigid body simulation: slabs fall together, hit the block and tumble
    pivot.location = (0, 0, start_z)
    bpy.context.view_layer.update()
    mats = [s.matrix_world.copy() for s in slabs]
    for s, mw in zip(slabs, mats):
        s.parent = None
        s.matrix_world = mw
    bpy.ops.rigidbody.world_add()
    rw = scn.rigidbody_world
    rw.point_cache.frame_start = 1
    rw.point_cache.frame_end = nframes
    rw.substeps_per_frame = 20
    rw.solver_iterations = 30
    rw.time_scale = 0.75
    for s in slabs:
        bpy.context.view_layer.objects.active = s
        s.select_set(True)
        with bpy.context.temp_override(object=s, active_object=s, selected_objects=[s]):
            bpy.ops.rigidbody.object_add(type="ACTIVE")
        s.rigid_body.collision_shape = "CONVEX_HULL"
        s.rigid_body.mass = 0.4
        s.rigid_body.friction = 0.6
        s.rigid_body.restitution = 0.25
        s.rigid_body.use_margin = True
        s.rigid_body.collision_margin = 0.002
        s.rigid_body.kinematic = True
        s.keyframe_insert('rigid_body.kinematic', frame=drop_start)
        s.rigid_body.kinematic = False
        s.keyframe_insert('rigid_body.kinematic', frame=drop_start + 1)
        s.select_set(False)
    with bpy.context.temp_override(object=block, active_object=block, selected_objects=[block]):
        bpy.ops.rigidbody.object_add(type="PASSIVE")
    block.rigid_body.collision_shape = "MESH"
    block.rigid_body.mesh_source = "BASE"
    block.rigid_body.friction = 0.7
    block.rigid_body.restitution = 0.2
    block.rigid_body.use_margin = True
    block.rigid_body.collision_margin = 0.002
    floor = box_obj("floor", -20, 20, -20, 20, -0.2, 0)
    with bpy.context.temp_override(object=floor, active_object=floor, selected_objects=[floor]):
        bpy.ops.rigidbody.object_add(type="PASSIVE")
    floor.rigid_body.collision_shape = "BOX"
    floor.hide_render = True
    # bake
    with bpy.context.temp_override(scene=scn, point_cache=rw.point_cache):
        bpy.ops.ptcache.bake(bake=True)

# ---------------- floor (visible, shadow catcher-ish dark) ----------------
gnd = box_obj("ground", -30, 30, -30, 30, -0.05, 0)
gm = bpy.data.materials.new("ground")
gm.use_nodes = True
gb = gm.node_tree.nodes["Principled BSDF"]
gb.inputs["Base Color"].default_value = (0.035, 0.035, 0.04, 1)
gb.inputs["Roughness"].default_value = 0.35
gnd.data.materials.append(gm)

# ---------------- world / lights / camera ----------------
world = bpy.data.worlds.new("w")
scn.world = world
world.use_nodes = True
bg = world.node_tree.nodes["Background"]
bg.inputs["Color"].default_value = (0.02, 0.02, 0.025, 1)
bg.inputs["Strength"].default_value = 1.0

def area(name, loc, energy, size, color=(1, 1, 1)):
    ld = bpy.data.lights.new(name, "AREA")
    ld.energy = energy
    ld.size = size
    ld.color = color
    ob = bpy.data.objects.new(name, ld)
    ob.location = loc
    scn.collection.objects.link(ob)
    d = Vector((0, 0, 1.2)) - Vector(loc)
    ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    return ob

area("key", (4.5, -4.0, 7.5), 1400, 4.0, (1.0, 0.93, 0.85))
area("fill", (-6, -3, 3.5), 300, 5.0, (0.8, 0.88, 1.0))
area("rim", (-2.5, 6.5, 6.0), 900, 3.0, (1.0, 0.85, 0.7))

cam_d = bpy.data.cameras.new("cam")
cam_d.lens = 45
cam = bpy.data.objects.new("cam", cam_d)
scn.collection.objects.link(cam)
scn.camera = cam
cam.location = (4.6, -6.4, 10.2)
tgt = Vector((0, 0, 3.2))
cam.rotation_euler = (tgt - cam.location).to_track_quat("-Z", "Y").to_euler()
cam_d.dof.use_dof = False

# ---------------- render settings ----------------
r = scn.render
r.engine = "CYCLES"
scn.cycles.device = "CPU"
scn.cycles.samples = samples
scn.cycles.use_denoising = True
scn.cycles.denoiser = "OPENIMAGEDENOISE"
scn.cycles.max_bounces = 4
scn.cycles.diffuse_bounces = 2
scn.cycles.glossy_bounces = 2
scn.cycles.transmission_bounces = 0
scn.cycles.use_adaptive_sampling = True
scn.cycles.adaptive_threshold = 0.04
r.use_persistent_data = True
scn.cycles.texture_limit_render = "1024"
r.resolution_x = 1080
r.resolution_y = 1920
r.resolution_percentage = int(res_scale * 100)
r.use_motion_blur = os.environ.get("MB","0")=="1"
r.motion_blur_shutter = 0.4
scn.view_settings.view_transform = "AgX"
scn.view_settings.look = "AgX - Punchy"
r.image_settings.file_format = "JPEG"
r.image_settings.quality = 92
r.filepath = os.path.join(out_dir, "f_")
scn.frame_start = frame_start
scn.frame_end = frame_end
scn.frame_step = int(os.environ.get("STEP", "1"))
import json
track = {}
for f in range(1, nframes + 1):
    scn.frame_set(f)
    track[f] = [list(o.matrix_world.translation) for o in slabs]
json.dump({"track": track, "success": success, "drop_start": drop_start}, open(os.path.join(out_dir, "track.json"), "w"))
scn.frame_set(1)
for o in scn.objects: print("MAT", o.name, [s.material.name if s.material else None for s in o.material_slots])
if os.environ.get("NORENDER"): sys.exit()
HERO = os.environ.get("HERO")
if HERO:
    # still hero image: sphere entering the slots, transparent background w/ shadow catcher
    rx, ry = [int(v) for v in os.environ.get("HERO_RES", "1000x1000").split("x")]
    r.resolution_x, r.resolution_y, r.resolution_percentage = rx, ry, 100
    r.film_transparent = True
    gnd.is_shadow_catcher = True
    r.use_motion_blur = False
    if pivot.animation_data: pivot.animation_data_clear()
    pivot.location = (0, 0, rest_z + float(os.environ.get("HERO_Z", "1.15")))
    pivot.rotation_euler = (0, 0, 0)
    cam.location = Vector([float(v) for v in os.environ.get("HERO_CAM", "4.2,-5.6,6.4").split(",")])
    tgt = Vector((0, 0, float(os.environ.get("HERO_TGT", "2.55"))))
    cam.rotation_euler = (tgt - cam.location).to_track_quat("-Z", "Y").to_euler()
    cam_d.lens = float(os.environ.get("HERO_LENS", "42"))
    scn.cycles.samples = samples
    r.image_settings.file_format = "PNG"
    r.image_settings.color_mode = "RGBA"
    r.filepath = os.path.join(out_dir, "hero.png")
    scn.frame_set(1)
    bpy.ops.render.render(write_still=True)
    sys.exit()
import shutil
# static lead-in: render first frame once, copy for the hold
fs = frame_start
if frame_start <= drop_start - 1 and not os.environ.get("NOSKIP"):
    scn.frame_set(frame_start)
    r.filepath = os.path.join(out_dir, "f_%04d.jpg" % frame_start)
    bpy.ops.render.render(write_still=True)
    for f in range(frame_start + 1, drop_start):
        shutil.copy(r.filepath, os.path.join(out_dir, "f_%04d.jpg" % f))
    fs = drop_start
    r.filepath = os.path.join(out_dir, "f_")
scn.frame_start = fs
bpy.ops.render.render(animation=True)
print("DONE")
