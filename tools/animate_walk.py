"""
Spider Walk Cycle v3 — Gentle for 3k mesh
by Kore

Tuned for low-poly: small rotations that don't tear the mesh.
Proves the pipeline without requiring production geometry.
"""

import bpy
import math

CYCLE_FRAMES = 48
CYCLES = 3

GROUP_A = ['FL', 'MR', 'RL']
GROUP_B = ['FR', 'ML', 'RR']

# v5: sweet spot — visible motion without deformation artifacts
COXA_SWING = 8
FEMUR_LIFT = 13
TIBIA_BEND = 9
TARSUS_FLEX = 2

BODY_SWAY = 1.2
BODY_BOB = 1.0

def deg(d):
    return math.radians(d)

def find_armature():
    for obj in bpy.data.objects:
        if obj.type == 'ARMATURE' and 'SpiderRig' in obj.name:
            return obj
    return None

def set_rot(arm, bone_name, frame, rx=0, ry=0, rz=0):
    if bone_name not in arm.pose.bones:
        return
    pb = arm.pose.bones[bone_name]
    pb.rotation_mode = 'XYZ'
    pb.rotation_euler = (deg(rx), deg(ry), deg(rz))
    pb.keyframe_insert(data_path='rotation_euler', frame=frame)

def animate_leg(arm, leg, swing_start, swing_mid, swing_end, stance_end):
    coxa = f'leg_{leg}_coxa'
    femur = f'leg_{leg}_femur'
    tibia = f'leg_{leg}_tibia'
    tarsus = f'leg_{leg}_tarsus'

    side = 1 if leg.endswith('L') else -1

    # STANCE START — leg planted, slightly behind
    set_rot(arm, coxa, swing_start, ry=COXA_SWING * 0.3 * side)
    set_rot(arm, femur, swing_start, rx=0)
    set_rot(arm, tibia, swing_start, rx=0)
    set_rot(arm, tarsus, swing_start, rx=0)

    # LIFT — femur pulls leg up
    lift = swing_start + int((swing_mid - swing_start) * 0.5)
    set_rot(arm, coxa, lift, ry=0)
    set_rot(arm, femur, lift, rx=-FEMUR_LIFT * 0.6)
    set_rot(arm, tibia, lift, rx=TIBIA_BEND * 0.4)
    set_rot(arm, tarsus, lift, rx=TARSUS_FLEX)

    # PEAK — max height, reaching forward
    set_rot(arm, coxa, swing_mid, ry=-COXA_SWING * 0.5 * side)
    set_rot(arm, femur, swing_mid, rx=-FEMUR_LIFT)
    set_rot(arm, tibia, swing_mid, rx=TIBIA_BEND)
    set_rot(arm, tarsus, swing_mid, rx=TARSUS_FLEX * 0.5)

    # PLANT — leg comes down
    set_rot(arm, coxa, swing_end, ry=-COXA_SWING * 0.3 * side)
    set_rot(arm, femur, swing_end, rx=-FEMUR_LIFT * 0.1)
    set_rot(arm, tibia, swing_end, rx=TIBIA_BEND * 0.1)
    set_rot(arm, tarsus, swing_end, rx=0)

    # STANCE — planted, pushes back
    set_rot(arm, coxa, stance_end, ry=COXA_SWING * 0.3 * side)
    set_rot(arm, femur, stance_end, rx=0)
    set_rot(arm, tibia, stance_end, rx=0)
    set_rot(arm, tarsus, stance_end, rx=0)

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

    print("Walk cycle v3 — gentle for 3k mesh")
    total_frames = CYCLE_FRAMES * CYCLES
    half = CYCLE_FRAMES // 2

    for cycle in range(CYCLES):
        base = cycle * CYCLE_FRAMES

        for leg in GROUP_A:
            animate_leg(arm, leg,
                swing_start=base,
                swing_mid=base + half // 2,
                swing_end=base + half,
                stance_end=base + CYCLE_FRAMES)

        for leg in GROUP_B:
            animate_leg(arm, leg,
                swing_start=base + half,
                swing_mid=base + half + half // 2,
                swing_end=base + CYCLE_FRAMES,
                stance_end=base + CYCLE_FRAMES + half)

        # Body sway
        q1 = base + half // 2
        q2 = base + half
        q3 = base + half + half // 2
        q4 = base + CYCLE_FRAMES

        set_rot(arm, 'root', base, rx=0, rz=0)
        set_rot(arm, 'root', q1, rx=BODY_BOB, rz=BODY_SWAY)
        set_rot(arm, 'root', q2, rx=0, rz=0)
        set_rot(arm, 'root', q3, rx=BODY_BOB, rz=-BODY_SWAY)
        set_rot(arm, 'root', q4, rx=0, rz=0)

    bpy.context.scene.frame_start = 0
    bpy.context.scene.frame_end = total_frames
    bpy.context.scene.frame_current = 0

    if arm.animation_data and arm.animation_data.action:
        for fc in arm.animation_data.action.fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = 'BEZIER'
                kp.handle_left_type = 'AUTO_CLAMPED'
                kp.handle_right_type = 'AUTO_CLAMPED'

    print(f"Done: {total_frames} frames. Press Space to play!")

try:
    animate()
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
