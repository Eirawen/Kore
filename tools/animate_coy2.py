"""
COY v4 — authored ON the imported withSkin rig, in its native pose space.

Method: import the GLB fresh (same scene as the verified walk render),
SAMPLE the walk action to learn each joint's working axes in importer pose
space, clear the action, then author the emote:
  - arm-to-chin: solver — single axis-angle on the upper arm (free axis,
    3 params) + elbow constrained to its LEARNED axis (1 param) + wrist
    (2 params). Single rotations in native space cannot candy-wrap.
  - torso/head/legs: small armature-space rotations (proven safe family).
  - acting beats: anticipate-away -> move (arm leads) -> overshoot ->
    settle (head lands last) -> living hold (breath/sway).

Run:
  blender --background --python animate_coy2.py -- [--full]
"""
import bpy
import sys
import json
import math
from mathutils import Vector, Quaternion, Euler

GLB = '/home/khaled/Kore/succubus_walk.glb'
OUT = r'C:\tmp'
FPS = 60
FRAMES = 132

# ───────── import fresh ─────────
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=GLB)
scene = bpy.context.scene
scene.render.fps = FPS
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')

# ───────── learn joint axes from the walk (native pose space) ─────────
action = arm.animation_data.action
f0, f1 = (int(v) for v in action.frame_range)

def sample_bone_quats(bname):
    qs = []
    pb = arm.pose.bones[bname]
    for f in range(f0, f1 + 1):
        scene.frame_set(f)
        qs.append(pb.rotation_quaternion.copy())
    return qs

def dominant_axis(quats):
    best_ang, ref = 0.0, None
    data = []
    for q in quats:
        if q.w < 0:
            q = -q
        ang = math.degrees(2 * math.acos(max(-1.0, min(1.0, q.w))))
        ax = Vector((q.x, q.y, q.z))
        if ax.length > 1e-6:
            ax.normalize()
            data.append((ax, ang))
            if ang > best_ang:
                best_ang, ref = ang, ax
    if ref is None:
        return Vector((1, 0, 0)), 0.0
    acc = Vector((0, 0, 0))
    for ax, ang in data:
        if ax.dot(ref) < 0:
            ax = -ax
        acc += ax * ang
    acc.normalize()
    return acc, best_ang

ELBOW_AXIS, elbow_max = dominant_axis(sample_bone_quats('LeftForeArm'))
ARM_AXIS_WALK, arm_max = dominant_axis(sample_bone_quats('LeftArm'))
print('LEARNED elbow axis %s (max %.1f deg in walk)' %
      ([round(v, 2) for v in ELBOW_AXIS], elbow_max))
print('LEARNED arm swing axis %s (max %.1f deg)' %
      ([round(v, 2) for v in ARM_AXIS_WALK], arm_max))

# elbow flexion SIGN: the walk's biggest elbow key defines "bending the
# right way"; positive angle about ELBOW_AXIS is that direction by
# construction (dominant_axis flips into the majority hemisphere).

# ───────── clear the action; she stands in bind pose ─────────
arm.animation_data_clear()
for pb in arm.pose.bones:
    pb.rotation_mode = 'QUATERNION'
    pb.rotation_quaternion = Quaternion()
    pb.location = (0, 0, 0)
scene.frame_set(1)

# ───────── staging (from the verified walk render, head-safe framing) ──
bpy.context.view_layer.update()
deps = bpy.context.evaluated_depsgraph_get()
lo = Vector((1e9,) * 3)
hi = Vector((-1e9,) * 3)
for o in bpy.data.objects:
    if o.type != 'MESH':
        continue
    eo = o.evaluated_get(deps)
    for corner in eo.bound_box:
        wc = eo.matrix_world @ Vector(corner)
        for i in range(3):
            lo[i] = min(lo[i], wc[i])
            hi[i] = max(hi[i], wc[i])
center = (lo + hi) / 2
size = max(hi - lo)
cam_data = bpy.data.cameras.new('Cam')
cam_data.lens = 50
cam = bpy.data.objects.new('Cam', cam_data)
cam.location = center + Vector((1.05, -1.35, 0.35)).normalized() * size * 1.55
cam.rotation_euler = (center + Vector((0, 0, size * 0.08)) - cam.location) \
    .to_track_quat('-Z', 'Y').to_euler()
scene.collection.objects.link(cam)
scene.camera = cam
for nm, off, e, col in (('K', Vector((-1, -1.2, 1.4)), 2.2, (1.0, 0.95, 0.9)),
                        ('F', Vector((1.3, -0.8, 0.4)), 0.7, (0.8, 0.85, 1.0))):
    d = bpy.data.lights.new(nm, 'SUN')
    d.energy, d.color = e, col
    d.angle = math.radians(8)
    o = bpy.data.objects.new(nm, d)
    o.location = center + off * size
    o.rotation_euler = (center - o.location).to_track_quat('-Z', 'Y').to_euler()
    scene.collection.objects.link(o)
w = bpy.data.worlds.new('W')
w.use_nodes = True
w.node_tree.nodes['Background'].inputs['Color'].default_value = (0.10, 0.09, 0.12, 1)
scene.world = w
try:
    scene.render.engine = 'BLENDER_EEVEE'
except TypeError:
    scene.render.engine = 'BLENDER_EEVEE_NEXT'
scene.render.resolution_x, scene.render.resolution_y = 960, 720
scene.render.image_settings.file_format = 'PNG'
scene.frame_start, scene.frame_end = 1, FRAMES

# ───────── pose machinery ─────────

def local_quat(pb, axis_arm, deg):
    m = pb.bone.matrix_local.to_3x3().inverted()
    a = (m @ Vector(axis_arm)).normalized()
    return Quaternion(a, math.radians(deg))

def local_loc(pb, off):
    return pb.bone.matrix_local.to_3x3().inverted() @ Vector(off)

X, Y, Z = (1, 0, 0), (0, 1, 0), (0, 0, 1)

def spec_quat(pb, spec, blend=1.0):
    if isinstance(spec, tuple) and spec and spec[0] == 'axis':
        _, ax, deg = spec
        return Quaternion(Vector(ax).normalized(), math.radians(deg * blend))
    q = Quaternion()
    for axis, deg in spec:
        q = q @ local_quat(pb, axis, deg * blend)
    return q

def apply_pose(frame, pose, blend=1.0):
    for bone, spec in pose.items():
        if bone == 'HIPS_LOC':
            pb = arm.pose.bones['Hips']
            pb.location = local_loc(pb, Vector(spec) * blend)
            pb.keyframe_insert('location', frame=frame)
            continue
        pb = arm.pose.bones.get(bone)
        if pb is None:
            continue
        pb.rotation_quaternion = spec_quat(pb, spec, blend)
        pb.keyframe_insert('rotation_quaternion', frame=frame)

def key_rest(frame, bones):
    for bone in bones:
        if bone == 'HIPS_LOC':
            pb = arm.pose.bones['Hips']
            pb.location = (0, 0, 0)
            pb.keyframe_insert('location', frame=frame)
            continue
        pb = arm.pose.bones.get(bone)
        if pb is None:
            continue
        pb.rotation_quaternion = Quaternion()
        pb.keyframe_insert('rotation_quaternion', frame=frame)

# ───────── solve the arm (native space, learned elbow) ─────────
mw = arm.matrix_world

def arm_eval(p):
    """p = [ax, ay (axis direction angles), swing_deg, elbow_deg, wx, wz]"""
    for pb in arm.pose.bones:
        pb.rotation_quaternion = Quaternion()
        pb.location = (0, 0, 0)
    theta, phi = math.radians(p[0]), math.radians(p[1])
    axis = Vector((math.sin(theta) * math.cos(phi),
                   math.sin(theta) * math.sin(phi),
                   math.cos(theta)))
    arm.pose.bones['LeftArm'].rotation_quaternion = \
        Quaternion(axis, math.radians(p[2]))
    arm.pose.bones['LeftForeArm'].rotation_quaternion = \
        Quaternion(ELBOW_AXIS, math.radians(p[3]))
    arm.pose.bones['LeftHand'].rotation_quaternion = \
        Euler((math.radians(p[4]), 0, math.radians(p[5])), 'XYZ').to_quaternion()
    bpy.context.view_layer.update()
    headpos = mw @ arm.pose.bones['Head'].head
    front = ((mw @ arm.pose.bones['headfront'].head) - headpos).normalized()
    target = headpos + front * 0.075 + Vector((0.01, 0, -0.085))
    wrist = mw @ arm.pose.bones['LeftHand'].head
    elbow = mw @ arm.pose.bones['LeftForeArm'].head
    shoulder = mw @ arm.pose.bones['LeftArm'].head
    cost = (wrist - target).length
    if elbow.z > shoulder.z - 0.02:
        cost += (elbow.z - (shoulder.z - 0.02)) * 3.0
    if elbow.y > shoulder.y + 0.03:
        cost += (elbow.y - shoulder.y - 0.03) * 3.0
    flare = abs(elbow.x - shoulder.x)          # coy elbows tuck, not flare
    if flare > 0.10:
        cost += (flare - 0.10) * 2.0
    return cost

LIM = [(0, 180), (-180, 180), (0, 118), (0, 135), (-60, 45), (-45, 45)]
p = [90.0, 0.0, 55.0, 80.0, -25.0, 0.0]
step = 30.0
best = arm_eval(p)
for _ in range(16):
    improved = False
    for i in range(len(p)):
        for d in (step, -step):
            q = list(p)
            q[i] = max(LIM[i][0], min(LIM[i][1], q[i] + d))
            if q[i] == p[i]:
                continue
            c = arm_eval(q)
            if c < best - 1e-5:
                best, p, improved = c, q, True
    if not improved:
        step *= 0.5
        if step < 1.0:
            break
print('COYARM cost=%.4f axis=(t%.0f,p%.0f) swing=%.1f elbow=%.1f wrist=(%.0f,%.0f)'
      % (best, *p))

theta, phi = math.radians(p[0]), math.radians(p[1])
ARM_AXIS = (math.sin(theta) * math.cos(phi),
            math.sin(theta) * math.sin(phi), math.cos(theta))
ARM_SWING, ELBOW_DEG, WR_X, WR_Z = p[2], p[3], p[4], p[5]

# ───────── the poses ─────────
ANTICIPATE = {
    'Head':      [(Z, -8), (X, -3)],
    'neck':      [(Z, -4)],
    'Spine':     [(X, -2)],
    'HIPS_LOC':  (0, 0, 1.0),
}

COY = {
    'HIPS_LOC':  (-2.4, 1.8, -8.0),
    'Hips':      [(Y, 2.5)],
    'RightUpLeg': [(X, -5)],
    'RightLeg':  [(X, 12)],
    'RightFoot': [(X, -4)],
    'LeftUpLeg': [(X, -8), (Z, 5)],
    'LeftLeg':   [(X, 17)],
    'LeftFoot':  [(X, -6)],
    'Spine02':   [(X, 3), (Y, -1.5)],
    'Spine01':   [(X, 4), (Y, -1.5)],
    'Spine':     [(X, 5), (Y, 2)],
    'LeftShoulder':  [(Y, 10)],
    'RightShoulder': [(Y, -7)],
    'LeftArm':      ('axis', ARM_AXIS, ARM_SWING),
    'LeftForeArm':  ('axis', tuple(ELBOW_AXIS), ELBOW_DEG),
    'LeftHand':     [(X, WR_X), (Z, WR_Z)],
    'RightArm':     [(X, -4), (Z, -5)],
    'RightForeArm': [(X, -10)],
    'neck':      [(X, 6), (Y, 6)],
    'Head':      [(X, 9), (Y, 10), (Z, 7)],
}

OVER = {}
for b, rots in COY.items():
    if b == 'HIPS_LOC':
        OVER[b] = (COY[b][0] * 1.12, COY[b][1], COY[b][2] * 1.14)
    elif isinstance(rots, tuple) and rots[0] == 'axis':
        OVER[b] = ('axis', rots[1], rots[2] * 1.08)
    else:
        OVER[b] = [(ax, d * 1.15) for ax, d in rots]

# ───────── build the animation ─────────
for pb in arm.pose.bones:
    pb.rotation_mode = 'QUATERNION'

all_bones = list(COY.keys())
key_rest(1, all_bones)
apply_pose(14, ANTICIPATE)
key_rest(14, [b for b in COY if b not in ANTICIPATE])
apply_pose(30, {k: v for k, v in COY.items() if k not in ('Head', 'neck')}, 0.6)
apply_pose(30, {'LeftArm': COY['LeftArm'],
                'LeftForeArm': COY['LeftForeArm']}, 0.85)
apply_pose(44, OVER)
apply_pose(54, {k: v for k, v in COY.items() if k not in ('Head', 'neck')})
apply_pose(60, {'Head': COY['Head'], 'neck': COY['neck']})

for f in range(72, FRAMES + 1, 12):
    t = (f - 60) / 60.0
    sway = math.sin(t * math.pi * 0.8) * 1.2
    breath = math.sin(t * math.pi * 1.6) * 0.8
    tilt = math.sin(t * math.pi * 0.5 + 0.7) * 1.5
    hold = dict(COY)
    hold['Hips'] = COY['Hips'] + [(Y, sway)]
    hold['Spine01'] = COY['Spine01'] + [(X, breath)]
    hold['Spine'] = COY['Spine'] + [(X, breath * 0.7)]
    hold['Head'] = COY['Head'] + [(Y, tilt), (X, breath * 0.5)]
    apply_pose(f, hold)

# smooth
ad = arm.animation_data
if ad and ad.action:
    a = ad.action
    curve_sets = ([a.fcurves] if hasattr(a, 'fcurves')
                  else [cb.fcurves for L in a.layers for s in L.strips
                        for cb in s.channelbags])
    for fcs in curve_sets:
        for fc in fcs:
            for kp in fc.keyframe_points:
                kp.interpolation = 'BEZIER'
                kp.handle_left_type = 'AUTO_CLAMPED'
                kp.handle_right_type = 'AUTO_CLAMPED'

PHASES = [(1, 'rest'), (8, 'anticipate (look away)'), (18, 'the move'),
          (40, 'overshoot'), (50, 'settle'), (60, 'coy — living hold')]

def phase_of(f):
    lab = ''
    for s0, l in PHASES:
        if f >= s0:
            lab = l
    return lab

argv = sys.argv
args = argv[argv.index('--') + 1:] if '--' in argv else []
frames = sorted({max(1, min(FRAMES, round(1 + (FRAMES - 1) * i / 11)))
                 for i in range(12)})
manifest = []
for i, f in enumerate(frames):
    scene.frame_set(f)
    path = OUT + '\\coy2_%02d.png' % (i + 1)
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    manifest.append({'index': i + 1, 'frame': f,
                     'time': round((f - 1) / FPS, 3), 'phase': phase_of(f)})
    print('rendered', path)
with open(OUT + '\\coy2_manifest.json', 'w') as fh:
    json.dump({'samples': manifest}, fh)
if '--full' in args:
    scene.render.filepath = OUT + '\\coy2full_'
    bpy.ops.render.render(animation=True)
