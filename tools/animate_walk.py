"""
Spider Walk Cycle v7 — Bone-Local Space
by Kore

v6 had the right idea (compute per-bone bend axes) but the wrong
coordinate space. rotation_quaternion is interpreted in BONE-LOCAL
space, but v6 computed the axes in ARMATURE space. Result: each bone
rotated around a seemingly random axis — partially twisting, partially
swinging — and the combined rotations of femur+tibia+tarsus cancelled
each other out. The feet LOOKED planted because the net vertical
displacement was near zero.

The fix: compute bend axes directly in bone-local space.
  - Bone local Y = bone direction (head to tail)
  - up_local = armature Z (0,0,1) transformed to bone-local
  - bend_axis = up_local.cross(bone_Y)  (sign: negative angle = lift)
"""

import bpy
import math
import mathutils
from mathutils import Vector, Euler

CYCLE_FRAMES = 48
CYCLES = 3

GROUP_A = ['FL', 'MR', 'RL']
GROUP_B = ['FR', 'ML', 'RR']

# Rotation amounts (degrees) — correct axes mean we need less rotation
COXA_SWING = 8
FEMUR_LIFT = 15
TIBIA_BEND = 12
TARSUS_FLEX = 4

BODY_SWAY = 1.5
BODY_BOB = 1.8  # visible but not bouncy

def deg(d):
    return math.radians(d)

def find_armature():
    for obj in bpy.data.objects:
        if obj.type == 'ARMATURE' and 'SpiderRig' in obj.name:
            return obj
    return None

def get_bone_bend_axis(arm, bone_name):
    """
    Compute the axis a bone should rotate around to produce a natural bend,
    in BONE-LOCAL space (which is what rotation_quaternion expects).

    In bone-local space:
      Y axis = bone direction (head to tail)
      up_local = armature (0,0,1) transformed to bone-local

    The bend axis = up_local.cross(bone_Y).
    Sign convention: NEGATIVE angle = lift (rotate tail toward +Z in armature space).
    """
    if bone_name not in arm.pose.bones:
        return Vector((1, 0, 0))

    bone = arm.pose.bones[bone_name].bone

    # Transform armature-space "up" to bone-local space
    mat = bone.matrix_local.to_3x3()
    up_local = mat.inverted() @ Vector((0, 0, 1))

    # Bone direction in local space is always (0, 1, 0)
    bone_y = Vector((0, 1, 0))

    # Bend axis perpendicular to bone direction and up, in bone-local space
    # Cross order chosen so negative angle = lift
    bend = up_local.cross(bone_y)
    if bend.length < 0.001:
        # Bone is vertical — fall back to armature Y as "up"
        up_local = mat.inverted() @ Vector((0, 1, 0))
        bend = up_local.cross(bone_y)
    bend.normalize()

    return bend

def get_bone_swing_axis(arm, bone_name):
    """
    The swing axis is world-up (Z) transformed to bone-local space.
    Swinging rotates the bone forward/backward in the horizontal plane.
    """
    if bone_name not in arm.pose.bones:
        return Vector((0, 0, 1))

    bone = arm.pose.bones[bone_name].bone
    mat = bone.matrix_local.to_3x3()
    swing = mat.inverted() @ Vector((0, 0, 1))
    swing.normalize()
    return swing

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

    print("Walk cycle v7 — bone-local space")

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

    OVERLAP_DELAY = 2

    def animate_leg(leg, swing_start, swing_mid, swing_end, stance_end):
        # Front legs reach more, rear legs push more
        is_front = leg.startswith('F')
        is_rear = leg.startswith('R')
        lift_mult = 1.2 if is_front else (0.8 if is_rear else 1.0)
        swing_mult = 1.3 if is_front else (0.7 if is_rear else 1.0)
        coxa = f'leg_{leg}_coxa'
        femur = f'leg_{leg}_femur'
        tibia = f'leg_{leg}_tibia'
        tarsus = f'leg_{leg}_tarsus'

        bend_c = axes[coxa]['bend']
        bend_f = axes[femur]['bend']
        bend_t = axes[tibia]['bend']
        bend_ta = axes[tarsus]['bend']
        swing_c = axes[coxa]['swing']

        # Tibia and tarsus FOLLOW the femur by a few frames (overlapping action)
        d = OVERLAP_DELAY
        d2 = OVERLAP_DELAY * 2

        # STANCE START — planted, tarsus angled down (tiptoe — spiders walk on claw tips)
        set_rot_around_axis(arm, coxa, swing_start, swing_c, COXA_SWING * 0.3)
        set_identity(arm, femur, swing_start)
        set_identity(arm, tibia, swing_start)
        set_rot_around_axis(arm, tarsus, swing_start, bend_ta, 5)  # tiptoe angle

        # LIFT — femur initiates, tibia follows, tarsus curls UP to clear ground
        lift = swing_start + int((swing_mid - swing_start) * 0.5)
        set_identity(arm, coxa, lift)
        set_rot_around_axis(arm, femur, lift, bend_f, -FEMUR_LIFT * 0.6 * lift_mult)
        set_rot_around_axis(arm, tibia, lift + d, bend_t, -TIBIA_BEND * 0.4 * lift_mult)
        set_rot_around_axis(arm, tarsus, lift + d2, bend_ta, -TARSUS_FLEX * 1.5)  # curl up

        # PEAK — femur peaks first, tibia catches up
        set_rot_around_axis(arm, coxa, swing_mid, swing_c, -COXA_SWING * 0.5 * swing_mult)
        set_rot_around_axis(arm, femur, swing_mid, bend_f, -FEMUR_LIFT * lift_mult)
        set_rot_around_axis(arm, tibia, swing_mid + d, bend_t, -TIBIA_BEND * 0.7 * lift_mult)
        set_rot_around_axis(arm, tarsus, swing_mid + d2, bend_ta, -TARSUS_FLEX * 0.5)

        # PLANT — leg reaches ground, tarsus returns to tiptoe
        set_rot_around_axis(arm, coxa, swing_end, swing_c, -COXA_SWING * 0.2 * swing_mult)
        set_rot_around_axis(arm, femur, swing_end, bend_f, -FEMUR_LIFT * 0.05)
        set_rot_around_axis(arm, tibia, min(swing_end + d, stance_end - 1), bend_t, TIBIA_BEND * 0.05)
        set_rot_around_axis(arm, tarsus, min(swing_end + d2, stance_end - 1), bend_ta, 5)  # back to tiptoe

        # SETTLE — brief moment of absorption after plant (2 frames)
        settle = min(swing_end + 3, stance_end - 2)
        set_rot_around_axis(arm, coxa, settle, swing_c, -COXA_SWING * 0.1 * swing_mult)
        set_identity(arm, femur, settle)
        set_identity(arm, tibia, settle)

        # STANCE — push back, coxa drifts backward, tarsus stays tiptoe
        set_rot_around_axis(arm, coxa, stance_end, swing_c, COXA_SWING * 0.4)
        set_identity(arm, femur, stance_end)
        set_identity(arm, tibia, stance_end)
        set_rot_around_axis(arm, tarsus, stance_end, bend_ta, 5)  # tiptoe maintained

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

        # Body sway — axes in root bone's local space
        q1 = base + half // 2
        q2 = base + half
        q3 = base + half + half // 2
        q4 = base + CYCLE_FRAMES

        root_bone = arm.pose.bones['root'].bone
        root_mat = root_bone.matrix_local.to_3x3()
        bob_axis = root_mat.inverted() @ Vector((1, 0, 0))   # pitch axis in root-local
        sway_axis = root_mat.inverted() @ Vector((0, 0, 1))   # yaw axis in root-local

        set_identity(arm, 'root', base)
        bob_q1 = compose_rotations(bob_axis, BODY_BOB, sway_axis, BODY_SWAY)
        set_rot_composed(arm, 'root', q1, bob_q1)
        set_identity(arm, 'root', q2)
        bob_q3 = compose_rotations(bob_axis, BODY_BOB, sway_axis, -BODY_SWAY)
        set_rot_composed(arm, 'root', q3, bob_q3)
        set_identity(arm, 'root', q4)

    bpy.context.scene.frame_start = 0
    bpy.context.scene.frame_end = total_frames
    bpy.context.scene.frame_current = 0

    # Smooth interpolation (Blender 5.1 layered action API + legacy fallback)
    if arm.animation_data and arm.animation_data.action:
        action = arm.animation_data.action
        smoothed = 0
        if hasattr(action, 'layers'):
            for layer in action.layers:
                for strip in layer.strips:
                    if hasattr(strip, 'channelbags'):
                        for cb in strip.channelbags:
                            for fc in cb.fcurves:
                                for kp in fc.keyframe_points:
                                    kp.interpolation = 'BEZIER'
                                    kp.handle_left_type = 'AUTO_CLAMPED'
                                    kp.handle_right_type = 'AUTO_CLAMPED'
                                    smoothed += 1
        elif hasattr(action, 'fcurves'):
            for fc in action.fcurves:
                for kp in fc.keyframe_points:
                    kp.interpolation = 'BEZIER'
                    kp.handle_left_type = 'AUTO_CLAMPED'
                    kp.handle_right_type = 'AUTO_CLAMPED'
                    smoothed += 1
        print(f"  Smoothed {smoothed} keyframe handles.")

    print(f"Done: {total_frames} frames. Press Space!")

try:
    animate()
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
