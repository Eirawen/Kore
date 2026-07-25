"""
POSE CHECK — the structured-looking gate. Renders ONE pose from four
diagnostic angles into a labeled strip, so depth ambiguity can't hide
interpenetration. This is the cheap veto before any motion/mp4 spend.

Views: FRONT (-Y), HER-LEFT (+X, the acting-arm side), HER-RIGHT (-X),
TOP-DOWN-45. Upper-body framing (the torso/arm/head zone where the
failures live) plus one full-body front.

Run:
  blender --background --python pose_check.py
"""
import bpy
import json
import math
from mathutils import Vector, Quaternion, Euler

GLB = '/home/khaled/Kore/succubus_walk.glb'
OUT = r'C:\tmp'

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=GLB)
scene = bpy.context.scene
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')

# ── learn the elbow axis from her own walk (as in animate_coy2) ──
action = arm.animation_data.action
f0, f1 = (int(v) for v in action.frame_range)

def dominant_axis(bname):
    pb = arm.pose.bones[bname]
    data, best_ang, ref = [], 0.0, None
    for f in range(f0, f1 + 1):
        scene.frame_set(f)
        q = pb.rotation_quaternion.copy()
        if q.w < 0:
            q = -q
        ang = math.degrees(2 * math.acos(max(-1.0, min(1.0, q.w))))
        ax = Vector((q.x, q.y, q.z))
        if ax.length > 1e-6:
            ax.normalize()
            data.append((ax, ang))
            if ang > best_ang:
                best_ang, ref = ang, ax
    acc = Vector((0, 0, 0))
    for ax, ang in data:
        if ax.dot(ref) < 0:
            ax = -ax
        acc += ax * ang
    acc.normalize()
    return acc

ELBOW_AXIS = dominant_axis('LeftForeArm')

arm.animation_data_clear()
for pb in arm.pose.bones:
    pb.rotation_mode = 'QUATERNION'
    pb.rotation_quaternion = Quaternion()
    pb.location = (0, 0, 0)
scene.frame_set(1)

# ── pose machinery ──
def local_quat(pb, axis_arm, deg):
    m = pb.bone.matrix_local.to_3x3().inverted()
    return Quaternion((m @ Vector(axis_arm)).normalized(), math.radians(deg))

X, Y, Z = (1, 0, 0), (0, 1, 0), (0, 0, 1)

def apply(pose):
    for bone, spec in pose.items():
        if bone == 'HIPS_LOC':
            pb = arm.pose.bones['Hips']
            pb.location = pb.bone.matrix_local.to_3x3().inverted() @ Vector(spec)
            continue
        pb = arm.pose.bones.get(bone)
        if pb is None:
            continue
        if isinstance(spec, tuple) and spec and spec[0] == 'axis':
            pb.rotation_quaternion = Quaternion(
                Vector(spec[1]).normalized(), math.radians(spec[2]))
        else:
            q = Quaternion()
            for ax, deg in spec:
                q = q @ local_quat(pb, ax, deg)
            pb.rotation_quaternion = q
    bpy.context.view_layer.update()

# ── THE CURRENT (v5) LANDED COY POSE — solved params baked in ──
# solver output: axis theta=0,phi=0 -> (0,0,1); swing 70; elbow 135; wrist (-25,0)
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
    'LeftArm':      ('axis', (0, 0, 1), 70.0),
    'LeftForeArm':  ('axis', tuple(ELBOW_AXIS), 135.0),
    'LeftHand':     [(X, -25), (Z, 0)],
    'RightArm':     [(X, -4), (Z, -5)],
    'RightForeArm': [(X, -10)],
    'neck':      [(X, 6), (Y, 6)],
    'Head':      [(X, 9), (Y, 10), (Z, 7)],
}
apply(COY)

# ── measure the body for framing ──
deps = bpy.context.evaluated_depsgraph_get()
lo, hi = Vector((1e9,) * 3), Vector((-1e9,) * 3)
for o in bpy.data.objects:
    if o.type != 'MESH':
        continue
    eo = o.evaluated_get(deps)
    for c in eo.bound_box:
        wc = eo.matrix_world @ Vector(c)
        for i in range(3):
            lo[i], hi[i] = min(lo[i], wc[i]), max(hi[i], wc[i])
full_center = (lo + hi) / 2
full_size = max(hi - lo)
mw = arm.matrix_world
chest = mw @ arm.pose.bones['Spine'].head
head = mw @ arm.pose.bones['Head'].head
upper_center = (chest + head) / 2
upper_size = full_size * 0.42

print('MEASURE full_size=%.2f chest=%s head=%s'
      % (full_size, [round(v, 3) for v in chest], [round(v, 3) for v in head]))

# ── lights + world ──
for nm, off, e, col in (('K', Vector((-1, -1.2, 1.4)), 2.4, (1.0, 0.96, 0.92)),
                        ('F', Vector((1.3, -0.9, 0.4)), 0.9, (0.82, 0.87, 1.0)),
                        ('R', Vector((0.2, 1.3, 0.7)), 0.6, (0.9, 0.9, 1.0))):
    d = bpy.data.lights.new(nm, 'SUN')
    d.energy, d.color, d.angle = e, col, math.radians(9)
    o = bpy.data.objects.new(nm, d)
    o.location = full_center + off * full_size
    o.rotation_euler = (full_center - o.location).to_track_quat('-Z', 'Y').to_euler()
    scene.collection.objects.link(o)
w = bpy.data.worlds.new('W')
w.use_nodes = True
w.node_tree.nodes['Background'].inputs['Color'].default_value = (0.11, 0.10, 0.13, 1)
scene.world = w
try:
    scene.render.engine = 'BLENDER_EEVEE'
except TypeError:
    scene.render.engine = 'BLENDER_EEVEE_NEXT'
scene.render.resolution_x, scene.render.resolution_y = 620, 720
scene.render.image_settings.file_format = 'PNG'

cam_data = bpy.data.cameras.new('C')
cam_data.lens = 55
cam = bpy.data.objects.new('C', cam_data)
scene.collection.objects.link(cam)
scene.camera = cam

# dir vector, target, distance-multiplier, label
VIEWS = [
    ((0, -1, 0.06), 'upper', 1.9, 'FRONT (upper body)'),
    ((1, -0.05, 0.06), 'upper', 1.9, 'HER LEFT SIDE — arm side'),
    ((-1, -0.05, 0.06), 'upper', 1.9, 'HER RIGHT SIDE'),
    ((0.35, -0.5, 1.0), 'upper', 2.0, 'TOP-DOWN 45'),
    ((0.9, -1.25, 0.28), 'full', 1.55, 'FULL BODY 3/4'),
]

manifest = []
for i, (dirv, framing, mult, label) in enumerate(VIEWS):
    target = upper_center if framing == 'upper' else full_center
    size = upper_size if framing == 'upper' else full_size
    cam.location = target + Vector(dirv).normalized() * size * mult
    cam.rotation_euler = (target - cam.location).to_track_quat('-Z', 'Y').to_euler()
    path = OUT + '\\posechk_%02d.png' % (i + 1)
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    manifest.append({'index': i + 1, 'label': label})
    print('rendered', path, label)

with open(OUT + '\\posechk_manifest.json', 'w') as fh:
    json.dump({'samples': manifest}, fh)
