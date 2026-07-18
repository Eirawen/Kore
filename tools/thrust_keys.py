# THRUST key poses on the wristed rig — POSE-FIRST deliverable.
#
# Builds on seat_grip.py (in-line rapier seat, rapier grip pose) and the
# 2-DOF wrist constraints (constrain_wrist.py). The corrected biomechanics:
#   ready  — arm up (forearm near vertical), blade up, wrist EXTENDED (the
#            big wrist angle lives here: the point cocks back over the
#            shoulder line, a coiled spring)
#   drive  — arm pitching downrange, wrist releasing toward neutral
#   strike — arm extended downrange, wrist ~neutral (+ a few degrees of
#            flexion to level the point at the target)
# The reach is mostly ARM pitch + forward extension; the wrist is small and
# only ever flexion/extension — the constraints make anything else
# impossible.
#
# Pitch sign: the staged forearm is armature +Z ~ world up at euler X ~ 0;
# rotating X NEGATIVE tips it toward world +Y = downrange (into the FP
# screen). pose_thrust.py's positive pitch pointed the blade at the player.
#
# Renders each key from the fixed FP (player) camera and a fixed side
# camera -> C:\tmp\tk_<key>_<view>.png. Montage with montage_thrust.py.
#
#   blender --background cgtrader_hand_wristed.blend --python thrust_keys.py --
import bpy, math
from mathutils import Vector, Euler, Quaternion

SRC = r'\\wsl.localhost\Ubuntu\home\khaled\Kore\tools\seat_grip.py'
_code = open(SRC).read()
exec(_code[:_code.rfind('def main')])

# (label, object-location, arm-pitch deg DOWNRANGE, wrist flex deg
#  [+ = palmar flexion, - = extension])
KEYS = [
    ('1_ready',   (2.05, -0.20,  0.10),  0.0, -24.0),
    ('2_drive',   (1.80,  0.55, -0.10), 34.0,  -8.0),
    ('3_strike',  (1.55,  1.55, -0.22), 62.0,   6.0),
    ('4_recover', (1.95,  0.35, -0.05), 22.0, -12.0),
]


def set_key(right, loc, pitch, flex):
    right.location = loc
    right.rotation_euler = Euler((math.radians(TILT_BACK - pitch),
                                  math.radians(TIP_INWARD),
                                  math.radians(-ROLL_INWARD)), 'XYZ')
    pb = right.pose.bones['hand']
    pb.rotation_mode = 'QUATERNION'
    pb.rotation_quaternion = Quaternion((1, 0, 0), math.radians(flex))
    bpy.context.view_layer.update()


def main():
    right, left = bpy.data.objects[RIGHT_ARM], bpy.data.objects[LEFT_ARM]
    assert 'hand' in right.data.bones, 'need the WRISTED rig'
    strip_scene(); stage_hands()
    apply_matte([bpy.data.objects[RIGHT_MESH], bpy.data.objects[LEFT_MESH]])
    cam = setup_world()
    apply_pose(right, POSE_RAPIER)
    apply_pose(left, POSE_RAPIER)
    bpy.context.view_layer.update()
    sword = import_sword(right)
    seat_sword(right, sword, SWORD_RZ)
    # left hand low guard, out of the lane but in frame (FP realism)
    left.location = (-HAND_X - 0.4, -0.35, -0.75)

    # fist path (world) for framing
    fists = []
    for label, loc, pitch, flex in KEYS:
        set_key(right, loc, pitch, flex)
        fists.append(right.matrix_world @ FIST_VOID)
    mid = sum(fists, Vector()) / len(fists)
    print('FISTS', [tuple(round(v, 2) for v in f) for f in fists])

    # FP camera = player eye: behind/above the hands, looking downrange,
    # framed tight on the right-hand lane.
    fp_loc = Vector((0.0, -8.2, 4.9))
    fp_aim = Vector((2.3, 1.5, 3.3))
    # side camera: outside the right hand, sees the up->forward sagittal arc
    sd_loc = mid + Vector((11.5, 0.4, 0.9))
    sd_aim = mid + Vector((0, 0.2, 0.3))

    for label, loc, pitch, flex in KEYS:
        set_key(right, loc, pitch, flex)
        cam.data.lens = 44
        render('%s_fp' % label, cam, fp_loc, fp_aim)
        cam.data.lens = 30
        render('%s_side' % label, cam, sd_loc, sd_aim)


# retarget seat_grip's render() output names for this script
def render(name, cam, loc, target):
    cam.location = loc
    cam.rotation_euler = look_at(Vector(loc), Vector(target))
    bpy.context.scene.render.filepath = OUT_DIR + '\\tk_%s.png' % name
    bpy.ops.render.render(write_still=True)
    print('rendered', name)


main()
