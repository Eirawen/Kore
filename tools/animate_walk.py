"""
Spider Walk Cycle v6 — Local Bone Axes
by Kore

The fix: instead of rotating all bones around global X/Y/Z,
query each bone's actual orientation and rotate around ITS axis.

A femur pointing northeast needs a different rotation vector to
"lift upward" than a femur pointing southwest. Global X lifts one
and twists the other. Local axes lift both correctly.

The bone's local Z axis (tail - head, normalized) is its length axis.
To "bend" a joint, we rotate around the axis PERPENDICULAR to the
bone's length and perpendicular to world-up. That's the bend axis.
"""

import bpy
import math
import mathutils
from mathutils import Vector, Euler

CYCLE_FRAMES = 48
CYCLES = 3

GROUP_A = ['FL', 'MR', 'RL']
GROUP_B = ['FR', 'ML', 'RR']

# Rotation amounts (degrees)
COXA_SWING = 8
FEMUR_LIFT = 14
TIBIA_BEND = 10
TARSUS_FLEX = 3

BODY_SWAY = 1.2
BODY_BOB = 1.0

def deg(d):
    return math.radians(d)

def find_armature():
    for obj in bpy.data.objects:
        if obj.type == 'ARMATURE' and 'SpiderRig' in obj.name:
            return obj
    return None

def get_bone_bend_axis(arm, bone_name):
    """
    Compute the axis a bone should rotate around to produce a natural bend.

    The bend axis is perpendicular to BOTH the bone's length AND world-up.
    This means rotating around it lifts/lowers the bone in the vertical plane
    containing the bone — exactly what a joint does.
    """
    if bone_name not in arm.pose.bones:
        return Vector((1, 0, 0))

    bone = arm.pose.bones[bone_name].bone
    # Bone direction in armature space
    bone_dir = (bone.tail_local - bone.head_local).normalized()

    # World up
    up = Vector((0, 0, 1))

    # Bend axis = perpendicular to bone direction AND up
    bend = bone_dir.cross(up)
    if bend.length < 0.001:
        # Bone is pointing straight up/down — use a fallback
        bend = bone_dir.cross(Vector((0, 1, 0)))
    bend.normalize()

    return bend

def get_bone_swing_axis(arm, bone_name):
    """
    The swing axis is world-up (Z). Swinging rotates the bone
    forward/backward in the horizontal plane — the coxa's job.
    """
    return Vector((0, 0, 1))

def set_rot_around_axis(arm, bone_name, frame, axis, angle_deg):
    """Rotate a bone around an arbitrary axis by angle_deg degrees."""
    if bone_name not in arm.pose.bones:
        return

    pb = arm.pose.bones[bone_name]
    pb.rotation_mode = 'QUATERNION'

    # Create rotation quaternion around the given axis
    angle_rad = math.radians(angle_deg)
    quat = mathutils.Quaternion(axis, angle_rad)

    pb.rotation_quaternion = quat
    pb.keyframe_insert(data_path='rotation_quaternion', frame=frame)

def set_identity(arm, bone_name, frame):
    """Set bone to rest rotation."""
    if bone_name not in arm.pose.bones:
        return
    pb = arm.pose.bones[bone_name]
    pb.rotation_mode = 'QUATERNION'
    pb.rotation_quaternion = mathutils.Quaternion()
    pb.keyframe_insert(data_path='rotation_quaternion', frame=frame)

def compose_rotations(axis1, angle1_deg, axis2, angle2_deg):
    """Combine two axis-angle rotations into one quaternion."""
    q1 = mathutils.Quaternion(axis1, math.radians(angle1_deg))
    q2 = mathutils.Quaternion(axis2, math.radians(angle2_deg))
    return q1 @ q2

def set_rot_composed(arm, bone_name, frame, quat):
    """Set bone rotation from a quaternion."""
    if bone_name not in arm.pose.bones:
        return
    pb = arm.pose.bones[bone_name]
    pb.rotation_mode = 'QUATERNION'
    pb.rotation_quaternion = quat
    pb.keyframe_insert(data_path='rotation_quaternion', frame=frame)

def animate():
    arm = find_armature()
    if not arm:
        print("ERROR: No SpiderRig found!")
        return

    bpy.context.view_layer.objects.active = arm
    if arm.mode != 'POSE':
        bpy.ops.object.mode_set(mode='POSE')

    if arm.animation_data and arm.animation_data.action:
        bpy.data.actions.remove(arm.animation_data.action)

    print("Walk cycle v6 — local bone axes")

    # Precompute bend and swing axes for each leg bone
    axes = {}
    for leg in GROUP_A + GROUP_B:
        for seg in ['coxa', 'femur', 'tibia', 'tarsus']:
            name = f'leg_{leg}_{seg}'
            axes[name] = {
                'bend': get_bone_bend_axis(arm, name),
                'swing': get_bone_swing_axis(arm, name),
            }
            if seg == 'coxa':
                print(f"  {name} bend axis: ({axes[name]['bend'].x:.2f}, {axes[name]['bend'].y:.2f}, {axes[name]['bend'].z:.2f})")

    total_frames = CYCLE_FRAMES * CYCLES
    half = CYCLE_FRAMES // 2

    def animate_leg(leg, swing_start, swing_mid, swing_end, stance_end):
        coxa = f'leg_{leg}_coxa'
        femur = f'leg_{leg}_femur'
        tibia = f'leg_{leg}_tibia'
        tarsus = f'leg_{leg}_tarsus'

        bend_c = axes[coxa]['bend']
        bend_f = axes[femur]['bend']
        bend_t = axes[tibia]['bend']
        bend_ta = axes[tarsus]['bend']
        swing_c = axes[coxa]['swing']

        # STANCE START — planted
        set_rot_around_axis(arm, coxa, swing_start, swing_c, COXA_SWING * 0.3)
        set_identity(arm, femur, swing_start)
        set_identity(arm, tibia, swing_start)
        set_identity(arm, tarsus, swing_start)

        # LIFT — femur bends upward around its local bend axis
        lift = swing_start + int((swing_mid - swing_start) * 0.5)
        set_identity(arm, coxa, lift)
        set_rot_around_axis(arm, femur, lift, bend_f, -FEMUR_LIFT * 0.6)
        set_rot_around_axis(arm, tibia, lift, bend_t, TIBIA_BEND * 0.4)
        set_rot_around_axis(arm, tarsus, lift, bend_ta, TARSUS_FLEX)

        # PEAK — max height
        set_rot_around_axis(arm, coxa, swing_mid, swing_c, -COXA_SWING * 0.5)
        set_rot_around_axis(arm, femur, swing_mid, bend_f, -FEMUR_LIFT)
        set_rot_around_axis(arm, tibia, swing_mid, bend_t, TIBIA_BEND)
        set_rot_around_axis(arm, tarsus, swing_mid, bend_ta, TARSUS_FLEX * 0.5)

        # PLANT — leg comes down
        set_rot_around_axis(arm, coxa, swing_end, swing_c, -COXA_SWING * 0.3)
        set_rot_around_axis(arm, femur, swing_end, bend_f, -FEMUR_LIFT * 0.1)
        set_rot_around_axis(arm, tibia, swing_end, bend_t, TIBIA_BEND * 0.1)
        set_identity(arm, tarsus, swing_end)

        # STANCE — push back
        set_rot_around_axis(arm, coxa, stance_end, swing_c, COXA_SWING * 0.3)
        set_identity(arm, femur, stance_end)
        set_identity(arm, tibia, stance_end)
        set_identity(arm, tarsus, stance_end)

    for cycle in range(CYCLES):
        base = cycle * CYCLE_FRAMES

        for leg in GROUP_A:
            animate_leg(leg,
                swing_start=base,
                swing_mid=base + half // 2,
                swing_end=base + half,
                stance_end=base + CYCLE_FRAMES)

        for leg in GROUP_B:
            animate_leg(leg,
                swing_start=base + half,
                swing_mid=base + half + half // 2,
                swing_end=base + CYCLE_FRAMES,
                stance_end=base + CYCLE_FRAMES + half)

        # Body sway
        q1 = base + half // 2
        q2 = base + half
        q3 = base + half + half // 2
        q4 = base + CYCLE_FRAMES

        set_identity(arm, 'root', base)
        bob_q1 = compose_rotations(Vector((1,0,0)), BODY_BOB, Vector((0,0,1)), BODY_SWAY)
        set_rot_composed(arm, 'root', q1, bob_q1)
        set_identity(arm, 'root', q2)
        bob_q3 = compose_rotations(Vector((1,0,0)), BODY_BOB, Vector((0,0,1)), -BODY_SWAY)
        set_rot_composed(arm, 'root', q3, bob_q3)
        set_identity(arm, 'root', q4)

    bpy.context.scene.frame_start = 0
    bpy.context.scene.frame_end = total_frames
    bpy.context.scene.frame_current = 0

    # Smooth interpolation
    if arm.animation_data and arm.animation_data.action:
        for fc in arm.animation_data.action.fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = 'BEZIER'
                kp.handle_left_type = 'AUTO_CLAMPED'
                kp.handle_right_type = 'AUTO_CLAMPED'

    print(f"Done: {total_frames} frames. Press Space!")

try:
    animate()
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
