"""
Spider Burrow Prowl — Slayer 2 Cave Spider
by Kore

Lives in the Burrow (underground warm dusty). Doesn't chase.
Waits for slayers to come to it. Poisons on hit.

Animation adjectives: deliberate, low, patient, predatory.

72-frame cycle (50% longer than walk). 65% stance, 35% swing.
Body low. Steps precise. Tarsus tips test the ground before
committing weight. The spider that owns the cave.

"Blue-collar fantasy. Not epic. Not heroic. People doing a shitty
dangerous job because the alternative is worse." — Design Journal
"""

import bpy
import math
import mathutils
from mathutils import Vector

CYCLE_FRAMES = 72  # slow prowl
CYCLES = 2

GROUP_A = ['FL', 'MR', 'RL']
GROUP_B = ['FR', 'ML', 'RR']

# Deliberate — smaller rotations, slower pace
COXA_SWING = 7       # short but readable steps
FEMUR_LIFT = 12      # low but visible lift
TIBIA_BEND = 9       # controlled
TARSUS_FLEX = 4      # claw flex
TARSUS_TIPTOE = 25   # en pointe — always on claw tips

BODY_SWAY = 0.8      # minimal — controlled, stable
BODY_BOB = 1.0       # subtle — heavy but not bouncy

SWING_FRACTION = 0.35  # 35% swing, 65% stance — more time planted
OVERLAP = 3            # more overlap — each joint waits longer

def find_armature():
    for obj in bpy.data.objects:
        if obj.type == 'ARMATURE' and 'SpiderRig' in obj.name:
            return obj
    return None

def get_bend_axis(arm, bone_name):
    if bone_name not in arm.pose.bones:
        return Vector((1, 0, 0))
    bone = arm.pose.bones[bone_name].bone
    mat = bone.matrix_local.to_3x3()
    up_local = mat.inverted() @ Vector((0, 0, 1))
    bone_y = Vector((0, 1, 0))
    bend = up_local.cross(bone_y)
    if bend.length < 0.001:
        up_local = mat.inverted() @ Vector((0, 1, 0))
        bend = up_local.cross(bone_y)
    bend.normalize()
    return bend

def get_swing_axis(arm, bone_name):
    if bone_name not in arm.pose.bones:
        return Vector((0, 0, 1))
    bone = arm.pose.bones[bone_name].bone
    mat = bone.matrix_local.to_3x3()
    swing = mat.inverted() @ Vector((0, 0, 1))
    swing.normalize()
    return swing

def set_axis_rot(arm, bone_name, frame, axis, angle_deg):
    if bone_name not in arm.pose.bones:
        return
    pb = arm.pose.bones[bone_name]
    pb.rotation_mode = 'QUATERNION'
    pb.rotation_quaternion = mathutils.Quaternion(axis, math.radians(angle_deg))
    pb.keyframe_insert(data_path='rotation_quaternion', frame=frame)

def set_identity(arm, bone_name, frame):
    if bone_name not in arm.pose.bones:
        return
    pb = arm.pose.bones[bone_name]
    pb.rotation_mode = 'QUATERNION'
    pb.rotation_quaternion = mathutils.Quaternion()
    pb.keyframe_insert(data_path='rotation_quaternion', frame=frame)

def compose_rot(axis1, angle1, axis2, angle2):
    q1 = mathutils.Quaternion(axis1, math.radians(angle1))
    q2 = mathutils.Quaternion(axis2, math.radians(angle2))
    return q1 @ q2

def set_composed(arm, bone_name, frame, quat):
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

    print("Burrow prowl — deliberate, low, patient")

    axes = {}
    for leg in GROUP_A + GROUP_B:
        for seg in ['coxa', 'femur', 'tibia', 'tarsus']:
            name = f'leg_{leg}_{seg}'
            axes[name] = {
                'bend': get_bend_axis(arm, name),
                'swing': get_swing_axis(arm, name),
            }

    total_frames = CYCLE_FRAMES * CYCLES
    swing_len = int(CYCLE_FRAMES * SWING_FRACTION)
    d = OVERLAP
    d2 = OVERLAP * 2

    def animate_leg(leg, swing_start, stance_start, cycle_end):
        coxa = f'leg_{leg}_coxa'
        femur = f'leg_{leg}_femur'
        tibia = f'leg_{leg}_tibia'
        tarsus = f'leg_{leg}_tarsus'

        bend_f = axes[femur]['bend']
        bend_t = axes[tibia]['bend']
        bend_ta = axes[tarsus]['bend']
        swing_c = axes[coxa]['swing']

        is_front = leg.startswith('F')
        is_rear = leg.startswith('R')
        lift_mult = 1.15 if is_front else (0.85 if is_rear else 1.0)
        swing_mult = 1.2 if is_front else (0.7 if is_rear else 1.0)

        swing_mid = swing_start + swing_len // 2

        # === STANCE — planted, tiptoe, coxa pushing back ===
        set_axis_rot(arm, coxa, swing_start, swing_c, COXA_SWING * 0.3)
        set_identity(arm, femur, swing_start)
        set_identity(arm, tibia, swing_start)
        set_axis_rot(arm, tarsus, swing_start, bend_ta, TARSUS_TIPTOE)

        # === LIFT — slow, controlled ===
        lift = swing_start + int(swing_len * 0.3)
        set_identity(arm, coxa, lift)
        set_axis_rot(arm, femur, lift, bend_f, -FEMUR_LIFT * 0.5 * lift_mult)
        set_axis_rot(arm, tibia, lift + d, bend_t, -TIBIA_BEND * 0.3 * lift_mult)
        set_axis_rot(arm, tarsus, lift + d2, bend_ta, -TARSUS_FLEX * 3)  # dramatic curl up

        # === PEAK — low, not dramatic ===
        set_axis_rot(arm, coxa, swing_mid, swing_c, -COXA_SWING * 0.4 * swing_mult)
        set_axis_rot(arm, femur, swing_mid, bend_f, -FEMUR_LIFT * lift_mult)
        set_axis_rot(arm, tibia, swing_mid + d, bend_t, -TIBIA_BEND * 0.6 * lift_mult)
        set_axis_rot(arm, tarsus, swing_mid + d2, bend_ta, -TARSUS_FLEX)

        # === PLANT — careful placement ===
        set_axis_rot(arm, coxa, stance_start, swing_c, -COXA_SWING * 0.15 * swing_mult)
        set_axis_rot(arm, femur, stance_start, bend_f, -FEMUR_LIFT * 0.03)
        set_axis_rot(arm, tibia, min(stance_start + d, cycle_end - 1), bend_t, TIBIA_BEND * 0.02)
        set_axis_rot(arm, tarsus, min(stance_start + d2, cycle_end - 1), bend_ta, TARSUS_TIPTOE)

        # === SETTLE ===
        settle = min(stance_start + 4, cycle_end - 3)
        set_axis_rot(arm, coxa, settle, swing_c, -COXA_SWING * 0.05 * swing_mult)
        set_identity(arm, femur, settle)
        set_identity(arm, tibia, settle)

        # === STANCE — slow push back ===
        set_axis_rot(arm, coxa, cycle_end, swing_c, COXA_SWING * 0.35)
        set_identity(arm, femur, cycle_end)
        set_identity(arm, tibia, cycle_end)
        set_axis_rot(arm, tarsus, cycle_end, bend_ta, TARSUS_TIPTOE)

    for cycle in range(CYCLES):
        base = cycle * CYCLE_FRAMES
        half = CYCLE_FRAMES // 2

        for leg in GROUP_A:
            animate_leg(leg,
                swing_start=base,
                stance_start=base + swing_len,
                cycle_end=base + CYCLE_FRAMES)

        for leg in GROUP_B:
            animate_leg(leg,
                swing_start=base + half,
                stance_start=base + half + swing_len,
                cycle_end=base + CYCLE_FRAMES + half)

        # Body — minimal, controlled
        q1 = base + CYCLE_FRAMES // 4
        q2 = base + CYCLE_FRAMES // 2
        q3 = base + 3 * CYCLE_FRAMES // 4
        q4 = base + CYCLE_FRAMES

        set_identity(arm, 'root', base)
        bob1 = compose_rot(Vector((1,0,0)), BODY_BOB, Vector((0,0,1)), BODY_SWAY)
        set_composed(arm, 'root', q1, bob1)
        set_identity(arm, 'root', q2)
        bob2 = compose_rot(Vector((1,0,0)), BODY_BOB, Vector((0,0,1)), -BODY_SWAY)
        set_composed(arm, 'root', q3, bob2)
        set_identity(arm, 'root', q4)

    bpy.context.scene.frame_start = 0
    bpy.context.scene.frame_end = total_frames
    bpy.context.scene.frame_current = 0

    if arm.animation_data and arm.animation_data.action:
        try:
            for layer in arm.animation_data.action.layers:
                for strip in layer.strips:
                    for cb in strip.channelbags:
                        for fc in cb.fcurves:
                            for kp in fc.keyframe_points:
                                kp.interpolation = 'BEZIER'
                                kp.handle_left_type = 'AUTO_CLAMPED'
                                kp.handle_right_type = 'AUTO_CLAMPED'
        except:
            pass

    print(f"Burrow prowl: {total_frames} frames ({CYCLES} cycles @ {CYCLE_FRAMES}f)")
    print(f"  She owns this cave.")

try:
    animate()
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
