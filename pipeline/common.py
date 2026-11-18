"""Shared helpers for SatisFit 3D concept scenes (Blender bpy, Cycles CPU).
A concept script builds its scene with these helpers, then calls finish(events, ...)
which writes events.json (for synced SFX) and renders frames f_####.jpg into out_dir.
"""
import os, sys, math, random, json, shutil
import bpy, bmesh
from mathutils import Vector, Euler

FPS = 30

PASTELS = {
    "peach":  ((0.95, 0.62, 0.48), (0.98, 0.80, 0.70)),
    "mint":   ((0.40, 0.80, 0.68), (0.72, 0.92, 0.84)),
    "lilac":  ((0.62, 0.52, 0.90), (0.84, 0.78, 0.97)),
    "sky":    ((0.40, 0.66, 0.95), (0.74, 0.86, 0.99)),
    "butter": ((0.98, 0.80, 0.35), (0.99, 0.92, 0.66)),
    "rose":   ((0.93, 0.48, 0.62), (0.98, 0.76, 0.84)),
    "sage":   ((0.55, 0.70, 0.52), (0.80, 0.88, 0.76)),
    "sand":   ((0.85, 0.72, 0.56), (0.95, 0.88, 0.78)),
}
# Saturated "candy" rainbow (feedback 18/11: more colours)
RAINBOW = [(1.00, 0.18, 0.33), (1.00, 0.48, 0.10), (1.00, 0.80, 0.08), (0.62, 0.90, 0.10), (0.10, 0.82, 0.45),
           (0.05, 0.80, 0.85), (0.12, 0.52, 1.00), (0.38, 0.30, 1.00), (0.70, 0.25, 1.00), (1.00, 0.25, 0.75)]
# Vivid backdrops (dark, light) – colourful but light enough that the candy objects still pop
VIVID = {
    "bubblegum": ((1.00, 0.45, 0.70), (1.00, 0.70, 0.85)),
    "electric":  ((0.25, 0.55, 1.00), (0.55, 0.78, 1.00)),
    "lime":      ((0.55, 0.88, 0.30), (0.80, 0.97, 0.55)),
    "sunny":     ((1.00, 0.78, 0.20), (1.00, 0.90, 0.50)),
    "violet":    ((0.55, 0.40, 1.00), (0.76, 0.66, 1.00)),
    "coral":     ((1.00, 0.50, 0.40), (1.00, 0.72, 0.62)),
    "aqua":      ((0.20, 0.85, 0.85), (0.55, 0.95, 0.92)),
}
PASTELS.update(VIVID)


def pick_bg():
    """Backdrop colour: mostly vivid, sometimes a classic pastel."""
    return random.choice(list(VIVID) * 3 + ["peach", "mint", "lilac", "sky", "rose"])


def srgb_to_lin(c):
    return tuple(((x + 0.055) / 1.055) ** 2.4 if x > 0.04045 else x / 12.92 for x in c)


def reset(nframes, seed=1):
    random.seed(seed)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scn = bpy.context.scene
    scn.frame_start, scn.frame_end = 1, nframes
    scn.render.fps = FPS
    return scn


def link(ob):
    bpy.context.scene.collection.objects.link(ob)
    return ob


def mesh_from_bm(name, build):
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    build(bm)
    bm.to_mesh(me)
    bm.free()
    return link(bpy.data.objects.new(name, me))


def smooth(ob, angle=35):
    with bpy.context.temp_override(object=ob, active_object=ob, selected_objects=[ob], selected_editable_objects=[ob]):
        bpy.ops.object.shade_smooth_by_angle(angle=math.radians(angle))


def bevel(ob, w=0.02, seg=3):
    b = ob.modifiers.new("bev", "BEVEL")
    b.width = w; b.segments = seg; b.limit_method = "ANGLE"; b.harden_normals = True
    return b


def apply_mods(ob):
    with bpy.context.temp_override(object=ob, active_object=ob, selected_objects=[ob], selected_editable_objects=[ob]):
        for m in list(ob.modifiers):
            bpy.ops.object.modifier_apply(modifier=m.name)


def boolean(target, cutter, op="DIFFERENCE", remove=True):
    md = target.modifiers.new("b", "BOOLEAN")
    md.operation = op; md.object = cutter; md.solver = "EXACT"
    with bpy.context.temp_override(object=target, active_object=target):
        bpy.ops.object.modifier_apply(modifier=md.name)
    if remove:
        bpy.data.objects.remove(cutter)


def box(name, sx, sy, sz, loc=(0, 0, 0)):
    def b(bm):
        bmesh.ops.create_cube(bm, size=1.0)
        for v in bm.verts:
            v.co.x *= sx; v.co.y *= sy; v.co.z *= sz
    ob = mesh_from_bm(name, b)
    ob.location = loc
    return ob


def set_mat(ob, m):
    ob.data.materials.clear()
    ob.data.materials.append(m)
    for p in ob.data.polygons:
        p.material_index = 0


def plastic(name, rgb, rough=0.28, coat=0.3, srgb=True):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    c = srgb_to_lin(rgb) if srgb else rgb
    b.inputs["Base Color"].default_value = (*c, 1)
    b.inputs["Roughness"].default_value = rough
    if "Coat Weight" in b.inputs:
        b.inputs["Coat Weight"].default_value = coat
        b.inputs["Coat Roughness"].default_value = 0.15
    return m


def metal(name, rgb=(1.0, 0.72, 0.30), rough=0.18):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*rgb, 1)
    b.inputs["Metallic"].default_value = 1.0
    b.inputs["Roughness"].default_value = rough
    return m


def glass(name, tint=(0.95, 0.97, 1.0)):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*tint, 1)
    b.inputs["Roughness"].default_value = 0.02
    b.inputs["Transmission Weight"].default_value = 1.0
    b.inputs["IOR"].default_value = 1.45
    return m


def studio(color_key="peach", strength=1.0, wall_y=4.0, lights=True):
    """Coloured seamless cyclorama backdrop + soft lighting. Returns backdrop object."""
    dark, light = PASTELS[color_key] if color_key in PASTELS else (color_key, color_key)
    prof = []
    for i in range(0, 11):
        prof.append((-20 + i * (20 + wall_y) / 10, 0.0))
    R = 3.0
    for i in range(1, 13):
        a = (i / 12) * (math.pi / 2)
        prof.append((wall_y + R * math.sin(a), R - R * math.cos(a)))
    for i in range(1, 6):
        prof.append((wall_y + R, R + i * 4))

    def build(bm):
        rows = []
        for x in (-25, 25):
            rows.append([bm.verts.new((x, y, z)) for (y, z) in prof])
        for j in range(len(prof) - 1):
            bm.faces.new((rows[0][j], rows[0][j + 1], rows[1][j + 1], rows[1][j]))
    bd = mesh_from_bm("backdrop", build)
    for p in bd.data.polygons:
        p.use_smooth = True
    # with the "Standard" view transform the light tint blows out to cream: use the saturated tone
    bcol = dark if os.environ.get("VIEW", "Standard") == "Standard" else light
    m = plastic("backdrop", bcol, rough=0.9, coat=0.0)
    set_mat(bd, m)
    scn = bpy.context.scene
    world = bpy.data.worlds.new("w"); scn.world = world; world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (*srgb_to_lin(light), 1)
    bg.inputs["Strength"].default_value = 0.35 * strength
    if lights:
        area("key", (-4.5, -4.5, 7.5), 1300 * strength, 5.0)
        area("rim", (4.5, 2.5, 6.0), 600 * strength, 4.0)
        area("fill", (3.0, -7.0, 3.0), 380 * strength, 6.0)
    return bd


def area(name, loc, energy, size, tgt=(0, 0, 1.0)):
    ld = bpy.data.lights.new(name, "AREA")
    ld.energy = energy; ld.size = size; ld.shape = "RECTANGLE"; ld.size_y = size * 0.5
    ob = link(bpy.data.objects.new(name, ld))
    ob.location = loc
    ob.rotation_euler = (Vector(tgt) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    return ob


def camera(loc, tgt, lens=50, push=None):
    """push: slow push-in factor over the clip (lens * push at the last frame) – keeps the frame alive."""
    cd = bpy.data.cameras.new("cam"); cd.lens = lens
    push = float(os.environ.get("PUSH", 1.06)) if push is None else push
    if push != 1.0:
        scn = bpy.context.scene
        cd.keyframe_insert("lens", frame=1)
        cd.lens = lens * push; cd.keyframe_insert("lens", frame=scn.frame_end); cd.lens = lens
        for fc in (cd.animation_data.action.fcurves if hasattr(cd.animation_data.action, "fcurves") else []):
            for kp in fc.keyframe_points:
                kp.interpolation = "SINE"
    cam = link(bpy.data.objects.new("cam", cd))
    cam.location = loc
    cam.rotation_euler = (Vector(tgt) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.camera = cam
    return cam


def key_loc(ob, frame, loc, interp="LINEAR"):
    ob.location = loc
    ob.keyframe_insert("location", frame=frame)


def key_rot(ob, frame, rot):
    ob.rotation_euler = rot
    ob.keyframe_insert("rotation_euler", frame=frame)


def set_interp(ob, interp="LINEAR"):
    ad = ob.animation_data
    if not ad or not ad.action:
        return
    act = ad.action
    curves = []
    if hasattr(act, "fcurves"):
        curves = list(act.fcurves)
    else:  # Blender 5 layered actions
        for layer in act.layers:
            for strip in layer.strips:
                for cb in strip.channelbags:
                    curves += list(cb.fcurves)
    for fc in curves:
        for kp in fc.keyframe_points:
            kp.interpolation = interp


def drop_keys(ob, f0, z0, z1, g=9.81 * 0.6, x=None, y=None, bounce=0.04, settle=True):
    """Keyframe a free fall of ob from z0 (at frame f0) to z1, with a tiny settle bounce.
    Returns the landing frame."""
    dist = z0 - z1
    t_fall = math.sqrt(2 * max(dist, 1e-4) / g)
    f_land = f0 + t_fall * FPS
    lx = ob.location.x if x is None else x
    ly = ob.location.y if y is None else y
    key_loc(ob, f0, (lx, ly, z0))
    f = f0 + 1
    while f < f_land:
        t = (f - f0) / FPS
        key_loc(ob, f, (lx, ly, z0 - 0.5 * g * t * t))
        f += 1
    fl = math.ceil(f_land)
    key_loc(ob, fl, (lx, ly, z1))
    if settle and bounce > 0:
        key_loc(ob, fl + 3, (lx, ly, z1 + bounce))
        key_loc(ob, fl + 6, (lx, ly, z1))
    return fl


def render_settings(res_scale=0.4, samples=10):
    scn = bpy.context.scene
    r = scn.render
    r.engine = "CYCLES"; scn.cycles.device = "CPU"
    scn.cycles.samples = samples; scn.cycles.use_denoising = True; scn.cycles.denoiser = "OPENIMAGEDENOISE"
    scn.cycles.use_adaptive_sampling = True; scn.cycles.adaptive_threshold = 0.04
    scn.cycles.max_bounces = 5; scn.cycles.glossy_bounces = 3; scn.cycles.diffuse_bounces = 2
    scn.cycles.transmission_bounces = 4
    r.use_persistent_data = True
    r.resolution_x, r.resolution_y, r.resolution_percentage = 1080, 1920, int(res_scale * 100)
    # feedback 18/11: vivid colours. AgX desaturates bright saturated plastics, "Standard" keeps the candy colours.
    vt = os.environ.get("VIEW", "Standard")
    scn.view_settings.view_transform = vt
    scn.view_settings.exposure = float(os.environ.get("EXPOSURE", -0.5 if vt == "Standard" else 0.0))
    try:
        scn.view_settings.look = os.environ.get("LOOK", "Medium High Contrast" if vt == "Standard" else "AgX - Punchy")
    except Exception:
        pass
    r.image_settings.file_format = "JPEG"; r.image_settings.quality = 92


def bake_rigid(nframes, substeps=20, iters=20, time_scale=1.0):
    scn = bpy.context.scene
    rw = scn.rigidbody_world
    rw.point_cache.frame_start, rw.point_cache.frame_end = 1, nframes
    rw.substeps_per_frame = substeps; rw.solver_iterations = iters; rw.time_scale = time_scale
    with bpy.context.temp_override(scene=scn, point_cache=rw.point_cache):
        bpy.ops.ptcache.bake(bake=True)


def rigid(ob, typ="ACTIVE", shape="CONVEX_HULL", mass=1.0, fr=0.5, rest=0.3, margin=0.002):
    if bpy.context.scene.rigidbody_world is None:
        bpy.ops.rigidbody.world_add()
    with bpy.context.temp_override(object=ob, active_object=ob, selected_objects=[ob]):
        bpy.ops.rigidbody.object_add(type=typ)
    rb = ob.rigid_body
    rb.collision_shape = shape; rb.mass = mass; rb.friction = fr; rb.restitution = rest
    rb.use_margin = True; rb.collision_margin = margin
    return rb


def impacts_from_motion(objs, nframes, thr=0.03, min_gap=2, kind="clack"):
    """Step the scene and detect per-object velocity jolts -> events. Call after baking."""
    scn = bpy.context.scene
    prev = {}
    pv = {}
    events = []
    last = {}
    for f in range(1, nframes + 1):
        scn.frame_set(f)
        for ob in objs:
            p = ob.matrix_world.translation.copy()
            r = ob.matrix_world.to_euler()
            if ob.name in prev:
                v = p - prev[ob.name]
                if ob.name in pv:
                    a = (v - pv[ob.name]).length
                    if a > thr and f - last.get(ob.name, -99) >= min_gap:
                        events.append([f, kind, min(1.0, a / (thr * 5))])
                        last[ob.name] = f
                pv[ob.name] = v
            prev[ob.name] = p
    return events


def finish(out_dir, events, nframes, res_scale=0.4, samples=10, static_until=1, meta=None):
    """Write events.json and render frames. Frames 1..static_until-1 are copies of frame 1."""
    os.makedirs(out_dir, exist_ok=True)
    json.dump({"events": sorted(events), "nframes": nframes, "fps": FPS, "meta": meta or {}},
              open(os.path.join(out_dir, "events.json"), "w"))
    render_settings(res_scale, samples)
    if os.environ.get("NORENDER"):
        return
    scn = bpy.context.scene
    r = scn.render
    fs = int(os.environ.get("FSTART", 1)); fe = int(os.environ.get("FEND", nframes))
    if fs == 1 and static_until > 2:
        scn.frame_set(1)
        r.filepath = os.path.join(out_dir, "f_0001.jpg")
        bpy.ops.render.render(write_still=True)
        for f in range(2, static_until):
            shutil.copy(r.filepath, os.path.join(out_dir, "f_%04d.jpg" % f))
        fs = static_until
    scn.frame_start, scn.frame_end = fs, fe
    scn.frame_step = int(os.environ.get("STEP", "1"))
    r.filepath = os.path.join(out_dir, "f_")
    bpy.ops.render.render(animation=True)
    print("DONE")
