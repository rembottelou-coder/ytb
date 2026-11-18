"""Concept "cloth": a silky / metallic cloth falls in slow motion and wraps a glossy object on a pedestal.
python3 c_cloth.py <out_dir> [seed] [res] [samples]   env: OBJ=sphere|cube|torus|cone  CLOTH=rainbow|silk|gold|silver  BG
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
OBJ = os.environ.get("OBJ", random.choice(["sphere", "sphere", "cube", "torus", "cone"]))
CL = os.environ.get("CLOTH", random.choice(["rainbow", "rainbow", "rainbow", "silk", "silk", "gold"]))
BG = os.environ.get("BG", pick_bg())
LEAD = 12
nframes = 225
scn = reset(nframes, seed)
studio(BG)

# pedestal
bpy.ops.mesh.primitive_cylinder_add(vertices=96, radius=1.25, depth=0.9, location=(0, 0, 0.45))
ped = bpy.context.active_object; bevel(ped, 0.03, 3); smooth(ped, 30)
set_mat(ped, plastic("ped", (0.96, 0.96, 0.95), rough=0.3, coat=0.3))

col = random.choice(RAINBOW)
mobj = plastic("obj", col, rough=0.18, coat=0.8)
top = 0.9
if OBJ == "sphere":
    bpy.ops.mesh.primitive_uv_sphere_add(segments=96, ring_count=48, radius=0.75, location=(0, 0, top + 0.75))
elif OBJ == "cube":
    bpy.ops.mesh.primitive_cube_add(size=1.2, location=(0, 0, top + 0.6), rotation=(0, 0, math.radians(30)))
elif OBJ == "torus":
    bpy.ops.mesh.primitive_torus_add(major_radius=0.6, minor_radius=0.25, major_segments=96, minor_segments=32,
                                     location=(0, 0, top + 0.6), rotation=(math.radians(70), 0, math.radians(20)))
else:
    bpy.ops.mesh.primitive_cone_add(vertices=96, radius1=0.7, radius2=0.0, depth=1.5, location=(0, 0, top + 0.75))
obj = bpy.context.active_object
if OBJ == "cube":
    bevel(obj, 0.08, 4)
smooth(obj, 30)
set_mat(obj, mobj)
cm = obj.modifiers.new("col", "COLLISION"); obj.collision.thickness_outer = 0.012; obj.collision.cloth_friction = 8
cp = ped.modifiers.new("col", "COLLISION"); ped.collision.thickness_outer = 0.012
floor = box("floorcol", 30, 30, 0.1, (0, 0, -0.05)); floor.hide_render = True
floor.modifiers.new("col", "COLLISION")

# cloth
bpy.ops.mesh.primitive_grid_add(x_subdivisions=90, y_subdivisions=90, size=3.6, location=(0, 0, 3.3),
                                rotation=(math.radians(random.uniform(-8, 8)), math.radians(random.uniform(-8, 8)), math.radians(random.uniform(0, 90))))
cloth = bpy.context.active_object
for p in cloth.data.polygons:
    p.use_smooth = True
c = cloth.modifiers.new("cloth", "CLOTH")
s = c.settings
s.quality = 6; s.mass = 0.15; s.air_damping = 1.5
s.tension_stiffness = 12; s.compression_stiffness = 12; s.shear_stiffness = 5; s.bending_stiffness = 0.05
s.time_scale = 0.42
c.collision_settings.distance_min = 0.008
c.collision_settings.use_self_collision = True
c.collision_settings.self_distance_min = 0.006
c.point_cache.frame_start, c.point_cache.frame_end = 1, nframes
scn.gravity = (0, 0, 0); scn.keyframe_insert("gravity", frame=LEAD)
scn.gravity = (0, 0, -9.81); scn.keyframe_insert("gravity", frame=LEAD + 1)
sol = cloth.modifiers.new("sol", "SOLIDIFY"); sol.thickness = 0.008
sub = cloth.modifiers.new("sub", "SUBSURF"); sub.levels = 1; sub.render_levels = 1
if CL == "gold":
    mc = metal("clothm", (1.0, 0.75, 0.38), 0.22)
elif CL == "silver":
    mc = metal("clothm", (0.92, 0.92, 0.95), 0.18)
else:
    mc = bpy.data.materials.new("silk"); mc.use_nodes = True
    nt = mc.node_tree; b = nt.nodes["Principled BSDF"]
    if CL == "rainbow":
        # vivid rainbow gradient across the cloth (UV based), slightly diagonal
        tc = nt.nodes.new("ShaderNodeTexCoord"); sep = nt.nodes.new("ShaderNodeSeparateXYZ")
        mix = nt.nodes.new("ShaderNodeMath"); mix.operation = "MULTIPLY_ADD"; mix.inputs[1].default_value = 0.35
        ramp = nt.nodes.new("ShaderNodeValToRGB")
        cols = RAINBOW[:] if random.random() < 0.5 else RAINBOW[::-1]
        el = ramp.color_ramp.elements
        while len(el) < len(cols):
            el.new(0.5)
        for i, c in enumerate(cols):
            el[i].position = i / (len(cols) - 1) * 0.74
            el[i].color = (*srgb_to_lin(c), 1)
        nt.links.new(tc.outputs["UV"], sep.inputs[0])
        nt.links.new(sep.outputs["X"], mix.inputs[0]); nt.links.new(sep.outputs["Y"], mix.inputs[2])
        nt.links.new(mix.outputs[0], ramp.inputs["Fac"]); nt.links.new(ramp.outputs["Color"], b.inputs["Base Color"])
        b.inputs["Roughness"].default_value = 0.3
    else:
        sc = random.choice([(1.0, 0.12, 0.40), (0.10, 0.45, 1.0), (0.05, 0.80, 0.50), (0.60, 0.20, 1.0), (1.0, 0.45, 0.05)])
        b.inputs["Base Color"].default_value = (*srgb_to_lin(sc), 1)
        b.inputs["Roughness"].default_value = 0.35
    if "Sheen Weight" in b.inputs:
        b.inputs["Sheen Weight"].default_value = 0.25 if CL == "rainbow" else 0.8
    b.inputs["Specular IOR Level"].default_value = 0.8
set_mat(cloth, mc)

# simulate and find first contact / settle for SFX
events = [[LEAD, "swish", 0.8]]
prev_min = None
contact = None
zs_prev = None
for f in range(1, nframes + 1):
    scn.frame_set(f)
    if f in (LEAD + 40, LEAD + 80):
        events.append([f, "swish", 0.5])
    if contact is None and f > LEAD:
        dg = bpy.context.evaluated_depsgraph_get()
        ev = cloth.evaluated_get(dg)
        me = ev.to_mesh()
        mz = min((ev.matrix_world @ v.co).z for i_, v in enumerate(me.vertices) if i_ % 37 == 0)
        ev.to_mesh_clear()
        top_obj = obj.location.z + obj.dimensions.z / 2
        if mz < top_obj + 0.02:
            contact = f
if contact:
    events.append([contact, "thud", 0.5])
    events.append([contact, "pop", 0.6, 0])
    events.append([contact + 2, "sparkle", 0.7])
    # soft rising marimba arpeggio while the cloth drapes, panned left -> right
    for k in range(8):
        events.append([contact + 6 + k * 7, "pluck", 0.55, k, -0.7 + 1.4 * k / 7])
end = min(nframes - 30, (contact or 60) + 70)
events.append([end, "chord", 0.9])

camera((0.0, -9.0, 4.4), (0, 0, 1.6), lens=60)
caption = random.choice(["So smooth", "Silky satisfying", "Wait for it...", "Rainbow drape" if CL == "rainbow" else "So silky"])
finish(out, events, nframes, res, spp, static_until=LEAD,
       meta={"concept": "cloth", "obj": OBJ, "cloth": CL, "bg": BG, "caption": caption, "root": 220.0})
