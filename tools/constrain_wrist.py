# Constrain the wristed rig to REAL wrist anatomy (Khaled's rapier reference):
#
#   hand (wrist) bone — 2-DOF ONLY:
#     X: flexion/extension  ±70°   (+X = palmar flexion, probed in seat_grip)
#     Z: radial/ulnar dev.  +20° radial (toward thumb = -X side) / -35°... no:
#        +Z moves the fingertips TOWARD the thumb (radial), so Z in [-35, +20].
#     Y: AXIAL TWIST = 0. The wrist does not twist; twist is forearm
#        pronation/supination. This is the DOF that produced the reverse grip
#        and the broken-looking wrist. Killed.
#   forearm bone — pronation/supination channel ONLY:
#     Y (roll about its own long axis): ±85°.  X = Z = 0 (gross arm motion is
#     object-level, not forearm-bone-level).
#
# Applied to BOTH armatures (identical local data), saved into
# cgtrader_hand_wristed.blend BEFORE any scene staging, so the file stays
# clean. Rest pose is inside every limit -> rest unchanged.
#
# Then (no further save) stages the grip scene and PROVES the constraints:
#   - numeric: a commanded 90° axial twist moves the middle fingertip ~0
#   - numeric: a commanded 120° flexion lands exactly on the 70° clamp
#   - render:  twist-attempt still == grip still (reverse grip impossible)
#
#   blender --background cgtrader_hand_wristed.blend --python constrain_wrist.py --
import bpy, math
from mathutils import Vector, Quaternion

ARMS = ['Armature.001', 'Armature.003']
DEG = math.radians

HAND_LIMITS = dict(x=(-70, 70), y=(0, 0), z=(-35, 20))
FORE_LIMITS = dict(x=(0, 0), y=(-85, 85), z=(0, 0))


def limit_rotation(pb, limits, name):
    for c in list(pb.constraints):
        if c.name == name:
            pb.constraints.remove(c)
    c = pb.constraints.new('LIMIT_ROTATION')
    c.name = name
    c.owner_space = 'LOCAL'
    c.use_limit_x = c.use_limit_y = c.use_limit_z = True
    c.min_x, c.max_x = DEG(limits['x'][0]), DEG(limits['x'][1])
    c.min_y, c.max_y = DEG(limits['y'][0]), DEG(limits['y'][1])
    c.min_z, c.max_z = DEG(limits['z'][0]), DEG(limits['z'][1])
    return c


def constrain(arm):
    limit_rotation(arm.pose.bones['hand'], HAND_LIMITS, 'anatomy_2dof')
    limit_rotation(arm.pose.bones['forearm'], FORE_LIMITS, 'anatomy_pronation')
    print('constrained %s: hand x%s y%s z%s | forearm y%s' % (
        arm.name, HAND_LIMITS['x'], HAND_LIMITS['y'], HAND_LIMITS['z'],
        FORE_LIMITS['y']))


for name in ARMS:
    constrain(bpy.data.objects[name])
bpy.ops.wm.save_mainfile()
print('SAVED', bpy.data.filepath)

# ---------------------------------------------------------------- proof ----
# reuse seat_grip's staging (constants + defs only, main() stripped)
SRC = r'\\wsl.localhost\Ubuntu\home\khaled\Kore\tools\seat_grip.py'
code = open(SRC).read()
exec(code[:code.rfind('def main')])

right, left = bpy.data.objects[RIGHT_ARM], bpy.data.objects[LEFT_ARM]
strip_scene(); stage_hands()
apply_matte([bpy.data.objects[RIGHT_MESH], bpy.data.objects[LEFT_MESH]])
cam = setup_world()
apply_pose(right, POSE_RAPIER); apply_pose(left, POSE_RAPIER)
bpy.context.view_layer.update()
sword = import_sword(right)
left.location = (-HAND_X - 0.5, -0.9, -1.2)
fist = right.matrix_world @ FIST_VOID

pb = right.pose.bones['hand']
tip_bone = CHAINS['middle'][-1]


def tip_after(q):
    pb.rotation_quaternion = q
    bpy.context.view_layer.update()
    deps = bpy.context.evaluated_depsgraph_get()
    return Vector(right.evaluated_get(deps).pose.bones[tip_bone].tail)


base = tip_after(Quaternion())
twist = tip_after(Quaternion((0, 1, 0), DEG(90)))       # forbidden axial twist
print('PROOF twist90 tip residual %.4f (0 = twist fully blocked)'
      % (twist - base).length)
over = tip_after(Quaternion((1, 0, 0), DEG(120)))       # beyond flexion ROM
at70 = tip_after(Quaternion((1, 0, 0), DEG(70)))
print('PROOF flex120 vs flex70 residual %.4f (0 = clamped at 70)'
      % (over - at70).length)
dev_over = tip_after(Quaternion((0, 0, 1), DEG(60)))    # beyond radial ROM
dev_at20 = tip_after(Quaternion((0, 0, 1), DEG(20)))
print('PROOF dev60 vs dev20 residual %.4f (0 = clamped at 20)'
      % (dev_over - dev_at20).length)

# render the twist attempt: must look exactly like the natural grip
pb.rotation_quaternion = Quaternion((0, 1, 0), DEG(90))
bpy.context.view_layer.update()
render('twistproof_fp', cam, fist + Vector((0.2, -4.6, 1.6)),
       fist + Vector((0, 0.6, 0.4)))
pb.rotation_quaternion = Quaternion()
