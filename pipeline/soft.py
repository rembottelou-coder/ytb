"""Concept 2: "0% vs 100% SOFT" — a ball drops onto a gold cone on a marble pedestal.
python3 soft.py <out_dir> <softness 0..100> [res_scale] [samples] [frames] [seed] [obstacle]
obstacle: cone | pipe | spikes
Writes frames f_####.jpg and track.json (centroid + min-z of the ball per frame).
"""
import sys, os, math, random, json, shutil
import bpy, bmesh
from mathutils import Vector

out_dir = sys.argv[1]
soft = int(sys.argv[2])
res_scale = float(sys.argv[3]) if len(sys.argv) > 3 else 0.4
samples = int(sys.argv[4]) if len(sys.argv) > 4 else 10
nframes = int(sys.argv[5]) if len(sys.argv) > 5 else 96
seed = int(sys.argv[6]) if len(sys.argv) > 6 else 1
obstacle = sys.argv[7] if len(sys.argv) > 7 else "cone"
ball_col = os.environ.get("BALL", "marble")  # marble | gold | pink | mint
random.seed(seed)
os.makedirs(out_dir, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
scn = bpy.context.scene
scn.frame_start, scn.frame_end = 1, nframes
scn.render.fps = 30
DROP = 14

# ---------------- materials ----------------
def marble(name, base=(0.92, 0.92, 0.91), vein=(0.42, 0.43, 0.46), scale=1.4):
    m = bpy.data.materials.new(name); m.use_nodes = True
    n, l = m.node_tree.nodes, m.node_tree.links
    b = n["Principled BSDF"]
    tc = n.new("ShaderNodeTexCoord")
    nz = n.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = scale; nz.inputs["Detail"].default_value = 12
    nz.inputs["Roughness"].default_value = 0.6
    l.new(tc.outputs["Object"], nz.inputs["Vector"])
    wv = n.new("ShaderNodeTexWave"); wv.inputs["Scale"].default_value = 0.9; wv.inputs["Distortion"].default_value = 9
    wv.inputs["Detail"].default_value = 6
    l.new(nz.outputs["Color"], wv.inputs["Vector"])
    ramp = n.new("ShaderNodeValToRGB")
    e0, e1 = ramp.color_ramp.elements
    e0.position, e0.color = 0.0, (*vein, 1)
    e1.position, e1.color = 0.08, (*base, 1)
    l.new(wv.outputs["Fac"], ramp.inputs["Fac"])
    l.new(ramp.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.12
    return m

def metal(name, col=(1.0, 0.72, 0.30), rough=0.16):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*col, 1)
    b.inputs["Metallic"].default_value = 1.0
    b.inputs["Roughness"].default_value = rough
    return m

def glossy(name, col):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*col, 1)
    b.inputs["Roughness"].default_value = 0.25
    if "Coat Weight" in b.inputs:
        b.inputs["Coat Weight"].default_value = 0.6
    if "Subsurface Weight" in b.inputs:
        b.inputs["Subsurface Weight"].default_value = 0.15
    return m

M_MARBLE = marble("marble")
M_MARBLE2 = marble("marble2", scale=2.2)
M_GOLD = metal("gold")
BALLS = {"marble": marble("ballm", scale=2.0), "gold": M_GOLD,
         "pink": glossy("pink", (0.9, 0.35, 0.45)), "mint": glossy("mint", (0.35, 0.8, 0.65)),
         "silver": metal("silver", (0.9, 0.9, 0.92), 0.12)}
M_BALL = BALLS[ball_col]

def link(ob):
    scn.collection.objects.link(ob); return ob

def mesh_obj(name, build):
    me = bpy.data.meshes.new(name); bm = bmesh.new(); build(bm); bm.to_mesh(me); bm.free()
    return link(bpy.data.objects.new(name, me))

def smooth(ob):
    for p in ob.data.polygons: p.use_smooth = True

# ---------------- scene ----------------
PED_R, PED_H = 1.55, 1.3
ped = mesh_obj("ped", lambda bm: bmesh.ops.create_cone(bm, cap_ends=True, segments=96, radius1=PED_R, radius2=PED_R, depth=PED_H))
ped.location.z = PED_H / 2
smooth(ped)
bv = ped.modifiers.new("bev", "BEVEL"); bv.width = 0.03; bv.segments = 3; bv.limit_method = "ANGLE"
ped.data.materials.append(M_MARBLE)
ring = mesh_obj("ring", lambda bm: None)
bpy.data.objects.remove(ring)
bpy.ops.mesh.primitive_torus_add(major_radius=PED_R + 0.01, minor_radius=0.045, major_segments=96, minor_segments=16, location=(0, 0, PED_H - 0.08))
ring = bpy.context.active_object; smooth(ring); ring.data.materials.append(M_GOLD)
bpy.ops.mesh.primitive_torus_add(major_radius=PED_R + 0.01, minor_radius=0.045, major_segments=96, minor_segments=16, location=(0, 0, 0.12))
ring2 = bpy.context.active_object; smooth(ring2); ring2.data.materials.append(M_GOLD)

top = PED_H
obst = []
if obstacle == "cone":
    bpy.ops.mesh.primitive_cone_add(vertices=64, radius1=0.42, radius2=0.0, depth=1.25, location=(0, 0, top + 0.625))
    c = bpy.context.active_object; smooth(c); c.data.materials.append(M_GOLD); obst.append(c)
elif obstacle == "pipe":
    bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=0.16, depth=1.4, location=(0, 0, top + 0.7))
    c = bpy.context.active_object; smooth(c); c.data.materials.append(M_GOLD); obst.append(c)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.2, location=(0, 0, top + 1.4))
    c2 = bpy.context.active_object; smooth(c2); c2.data.materials.append(M_GOLD); obst.append(c2)
elif obstacle == "spikes":
    for i, (x, y) in enumerate([(0, 0), (0.55, 0.3), (-0.55, 0.3), (0.0, -0.6)]):
        bpy.ops.mesh.primitive_cone_add(vertices=48, radius1=0.2, radius2=0.0, depth=0.9 if i == 0 else 0.6, location=(x, y, top + (0.45 if i == 0 else 0.3)))
        c = bpy.context.active_object; smooth(c); c.data.materials.append(M_GOLD); obst.append(c)

floor = mesh_obj("floor", lambda bm: bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=30))
fm = bpy.data.materials.new("floor"); fm.use_nodes = True
fb = fm.node_tree.nodes["Principled BSDF"]; fb.inputs["Base Color"].default_value = (0.80, 0.80, 0.82, 1); fb.inputs["Roughness"].default_value = 1.0
floor.data.materials.append(fm)

# ball
R = 0.62
bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=4 if soft > 0 else 5, radius=R, location=(0.06 + random.uniform(-0.03, 0.03), 0.02, top + 2.9))
ball = bpy.context.active_object; smooth(ball); ball.data.materials.append(M_BALL)

if soft == 0:
    bpy.ops.rigidbody.world_add()
    rw = scn.rigidbody_world
    rw.point_cache.frame_start, rw.point_cache.frame_end = 1, nframes
    rw.substeps_per_frame = 20; rw.solver_iterations = 20
    def rb(ob, typ, shape, fr=0.5, rest=0.5, mass=1.0):
        with bpy.context.temp_override(object=ob, active_object=ob, selected_objects=[ob]):
            bpy.ops.rigidbody.object_add(type=typ)
        ob.rigid_body.collision_shape = shape; ob.rigid_body.friction = fr; ob.rigid_body.restitution = rest
        ob.rigid_body.mass = mass
        return ob
    rb(ball, "ACTIVE", "SPHERE", 0.4, 0.75)
    ball.rigid_body.kinematic = True; ball.keyframe_insert("rigid_body.kinematic", frame=DROP)
    ball.rigid_body.kinematic = False; ball.keyframe_insert("rigid_body.kinematic", frame=DROP + 1)
    for o in obst: rb(o, "PASSIVE", "MESH", 0.4, 0.8)
    rb(ped, "PASSIVE", "MESH", 0.5, 0.5)
    rb(floor, "PASSIVE", "BOX", 0.6, 0.4)
    with bpy.context.temp_override(scene=scn, point_cache=rw.point_cache):
        bpy.ops.ptcache.bake(bake=True)
else:
    k = soft / 100.0
    cl = ball.modifiers.new("cloth", "CLOTH")
    s = cl.settings
    s.quality = 8
    s.mass = 0.3
    s.air_damping = 1.0
    s.tension_stiffness = 60 * (1 - k) + 3
    s.compression_stiffness = 60 * (1 - k) + 3
    s.shear_stiffness = 20 * (1 - k) + 2
    s.bending_stiffness = 8 * (1 - k) ** 2 + 0.05
    s.tension_damping = 5; s.compression_damping = 5; s.bending_damping = 0.5
    s.use_pressure = True
    s.uniform_pressure_force = 14 * (1 - k) + 2.5
    s.pressure_factor = 1.0
    s.fluid_density = 0
    s.use_internal_springs = False
    cl.collision_settings.use_self_collision = False
    cl.collision_settings.distance_min = 0.012
    cl.collision_settings.collision_quality = 4
    cl.point_cache.frame_start, cl.point_cache.frame_end = 1, nframes
    # hold the ball still until DROP with a pinned vertex group animated off? simpler: gravity starts at DROP
    scn.gravity = (0, 0, 0)
    scn.keyframe_insert("gravity", frame=DROP)
    scn.gravity = (0, 0, -9.81)
    scn.keyframe_insert("gravity", frame=DROP + 1)
    for o in obst + [ped, floor]:
        cm = o.modifiers.new("col", "COLLISION")
        o.collision.thickness_outer = 0.015
        o.collision.cloth_friction = 6 if o in obst else 4
        o.collision.damping = 0.3
    sub = ball.modifiers.new("sub", "SUBSURF"); sub.levels = 1; sub.render_levels = 1

# ---------------- light / camera / world ----------------
world = bpy.data.worlds.new("w"); scn.world = world; world.use_nodes = True
bg = world.node_tree.nodes["Background"]; bg.inputs["Color"].default_value = (0.86, 0.86, 0.88, 1); bg.inputs["Strength"].default_value = 0.75

def area(name, loc, energy, size, tgt=(0, 0, 1.6)):
    ld = bpy.data.lights.new(name, "AREA"); ld.energy = energy; ld.size = size; ld.shape = "RECTANGLE"; ld.size_y = size * 0.4
    ob = link(bpy.data.objects.new(name, ld)); ob.location = loc
    ob.rotation_euler = (Vector(tgt) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
area("key", (-4.5, -3.5, 7.0), 1600, 5.0)
area("rim", (4.5, 3.0, 5.0), 900, 4.0)
area("front", (1.0, -7.5, 3.0), 500, 6.0)

cam_d = bpy.data.cameras.new("cam"); cam_d.lens = 58
cam = link(bpy.data.objects.new("cam", cam_d)); scn.camera = cam
cam.location = (0.0, -9.6, 5.2)
tgt = Vector((0, 0, 2.2))
cam.rotation_euler = (tgt - cam.location).to_track_quat("-Z", "Y").to_euler()

# ---------------- simulate + track ----------------
deps = bpy.context.evaluated_depsgraph_get()
track = {}
for f in range(1, nframes + 1):
    scn.frame_set(f)
    deps = bpy.context.evaluated_depsgraph_get()
    ev = ball.evaluated_get(deps)
    if soft == 0:
        c = ev.matrix_world.translation
        track[f] = [[c.x, c.y, c.z]]
    else:
        me = ev.to_mesh()
        mw = ev.matrix_world
        zs = [(mw @ v.co) for v in me.vertices]
        cx = sum(p.x for p in zs) / len(zs); cy = sum(p.y for p in zs) / len(zs); cz = sum(p.z for p in zs) / len(zs)
        mz = min(p.z for p in zs)
        track[f] = [[cx, cy, cz], [cx, cy, mz]]
        ev.to_mesh_clear()
json.dump({"track": track, "success": soft == 100, "drop_start": DROP, "soft": soft}, open(os.path.join(out_dir, "track.json"), "w"))

# ---------------- render ----------------
r = scn.render
r.engine = "CYCLES"; scn.cycles.device = "CPU"
scn.cycles.samples = samples; scn.cycles.use_denoising = True; scn.cycles.denoiser = "OPENIMAGEDENOISE"
scn.cycles.use_adaptive_sampling = True; scn.cycles.adaptive_threshold = 0.04
scn.cycles.max_bounces = 4; scn.cycles.glossy_bounces = 3; scn.cycles.diffuse_bounces = 2; scn.cycles.transmission_bounces = 0
r.use_persistent_data = True
r.resolution_x, r.resolution_y, r.resolution_percentage = 1080, 1920, int(res_scale * 100)
scn.view_settings.view_transform = "AgX"; scn.view_settings.look = "AgX - Medium High Contrast"
r.image_settings.file_format = "JPEG"; r.image_settings.quality = 92
if os.environ.get("NORENDER"):
    sys.exit()
fs = int(os.environ.get("FSTART", 1)); fe = int(os.environ.get("FEND", nframes))
scn.frame_set(fs)
r.filepath = os.path.join(out_dir, "f_%04d.jpg" % fs)
bpy.ops.render.render(write_still=True)
if fs == 1:
    for f in range(2, DROP):
        shutil.copy(r.filepath, os.path.join(out_dir, "f_%04d.jpg" % f))
    fs = DROP
scn.frame_start, scn.frame_end = fs, fe
scn.frame_step = int(os.environ.get("STEP", "1"))
r.filepath = os.path.join(out_dir, "f_")
bpy.ops.render.render(animation=True)
print("DONE")
