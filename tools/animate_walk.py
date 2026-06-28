"""
Spider Walk Cycle v2 — Fixed Biomechanics
by Kore

Fixes from v1 (diagnosed via Khaled's temporal grid):
- Feet now LIFT: femur does the heavy lifting, not tarsus
- Local bone rotations instead of global X for all bones
- Bigger angles — v1 was too subtle to see
- Tarsus barely moves — it's the foot, not the actuator

The lift comes from the FEMUR rotating upward.
The tibia and tarsus follow through parent-child hierarchy.
Like lifting your hand by rotating your shoulder, not your wrist.
"""

import bpy
import math

CYCLE_FRAMES = 48
CYCLES = 3

GROUP_A = ['FL', 'MR', 'RL']
GROUP_B = ['FR', 'ML', 'RR']

# v2: bigger rotations, femur does the lifting
COXA_SWING = 12     # forward/back swing (was 8)
FEMUR_LIFT = 25     # THIS is what lifts the foot off the ground (was 12)
TIBIA_BEND = 15     # tibia bends during swing (was 10)
TARSUS_FLEX = 3     # minimal — foot tip, not actuator (was 6)

BODY_SWAY = 2
BODY_BOB = 1.5

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

def animate_leg_swing(arm, leg, base_frame, swing_start, swing_mid, swing_end, stance_end):
    """Animate one leg's full swing-stance cycle."""
    coxa = f'leg_{leg}_coxa'
    femur = f'leg_{leg}_femur'
    tibia = f'leg_{leg}_tibia'
    tarsus = f'leg_{leg}_tarsus'

    side = 1 if leg.endswith('L') else -1

    # Determine which axis to swing on based on leg position
    # Front legs swing more in Y (forward), mid legs more in Z (lateral), rear legs more in Y (backward)
    is_front = leg.startswith('F')
    is_rear = leg.startswith('R')
    is_mid = leg.startswith('M')

    # === STANCE START (leg is planted, pushing back) ===
    set_rot(arm, coxa, swing_start, rx=COXA_SWING * 0.3 * side)
    set_rot(arm, femur, swing_start, rx=0)
    set_rot(arm, tibia, swing_start, rx=0)
    set_rot(arm, tarsus, swing_start, rx=0)

    # === SWING: LIFT OFF ===
    # Femur lifts the entire leg — this is what gets feet off the ground
    lift_frame = swing_start + int((swing_mid - swing_start) * 0.4)
    set_rot(arm, coxa, lift_frame, rx=0)
    set_rot(arm, femur, lift_frame, rx=-FEMUR_LIFT * 0.7)
    set_rot(arm, tibia, lift_frame, rx=TIBIA_BEND * 0.5)
    set_rot(arm, tarsus, lift_frame, rx=TARSUS_FLEX)

    # === SWING: PEAK (max height, reaching forward) ===
    set_rot(arm, coxa, swing_mid, rx=-COXA_SWING * side)
    set_rot(arm, femur, swing_mid, rx=-FEMUR_LIFT)
    set_rot(arm, tibia, swing_mid, rx=TIBIA_BEND)
    set_rot(arm, tarsus, swing_mid, rx=TARSUS_FLEX * 0.5)

    # === SWING: PLANT (leg comes down, reaches forward) ===
    set_rot(arm, coxa, swing_end, rx=-COXA_SWING * 0.5 * side)
    set_rot(arm, femur, swing_end, rx=-FEMUR_LIFT * 0.1)
    set_rot(arm, tibia, swing_end, rx=TIBIA_BEND * 0.1)
    set_rot(arm, tarsus, swing_end, rx=-TARSUS_FLEX * 0.3)

    # === STANCE: planted, slowly pushing backward ===
    set_rot(arm, coxa, stance_end, rx=COXA_SWING * 0.3 * side)
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

    print("Animating spider walk cycle v2...")
    print(f"  Femur lift: {FEMUR_LIFT}° (this lifts the feet)")
    print(f"  Coxa swing: {COXA_SWING}°")
    print(f"  Tarsus flex: {TARSUS_FLEX}° (minimal — not the actuator)")

    total_frames = CYCLE_FRAMES * CYCLES
    half = CYCLE_FRAMES // 2

    for cycle in range(CYCLES):
        base = cycle * CYCLE_FRAMES

        # Group A swings first half, stance second half
        for leg in GROUP_A:
            animate_leg_swing(arm, leg,
                base_frame=base,
                swing_start=base,
                swing_mid=base + half // 2,
                swing_end=base + half,
                stance_end=base + CYCLE_FRAMES)

        # Group B: stance first half, swings second half
        for leg in GROUP_B:
            animate_leg_swing(arm, leg,
                base_frame=base,
                swing_start=base + half,
                swing_mid=base + half + half // 2,
                swing_end=base + CYCLE_FRAMES,
                stance_end=base + CYCLE_FRAMES + half)

        # Body sway — shift toward planted legs
        f_q1 = base + half // 2
        f_q2 = base + half
        f_q3 = base + half + half // 2
        f_q4 = base + CYCLE_FRAMES

        set_rot(arm, 'root', base, rx=0, ry=0, rz=0)
        set_rot(arm, 'root', f_q1, rx=BODY_BOB, ry=0, rz=BODY_SWAY)
        set_rot(arm, 'root', f_q2, rx=0, ry=0, rz=0)
        set_rot(arm, 'root', f_q3, rx=BODY_BOB, ry=0, rz=-BODY_SWAY)
        set_rot(arm, 'root', f_q4, rx=0, ry=0, rz=0)

    bpy.context.scene.frame_start = 0
    bpy.context.scene.frame_end = total_frames
    bpy.context.scene.frame_current = 0

    # Set interpolation to smooth
    if arm.animation_data and arm.animation_data.action:
        for fc in arm.animation_data.action.fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = 'BEZIER'
                kp.handle_left_type = 'AUTO_CLAMPED'
                kp.handle_right_type = 'AUTO_CLAMPED'

    print(f"\nWalk cycle v2 created: {total_frames} frames")
    print("Press Space to play!")

try:
    animate()
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
