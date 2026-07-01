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

CYCLE_FRAMES = 36  # walking pace — ~1.5 seconds per stride at 24fps
CYCLES = 4          # more cycles to fill the same time

GROUP_A = ['FL', 'MR', 'RL']
GROUP_B = ['FR', 'ML', 'RR']

# Coxa-dominant gait — HORIZONTAL rowing, not vertical pumping
COXA_SWING = 14      # PRIMARY actuator — forward reach, backward pull
FEMUR_LIFT = 6       # SECONDARY — just enough to clear the ground
TIBIA_BEND = 4       # minimal — follows the femur
TARSUS_FLEX = 2      # minimal
TARSUS_TIPTOE = 65   # nearly vertical — standing on the thin edge

BODY_SWAY = 0.8      # minimal — controlled, stable
BODY_BOB = 1.0       # subtle — heavy but not bouncy

# POSTURE — constant leg arch. Spiders stand with legs arched UP,
# body hanging below. This is the base pose all animation layers on.
FEMUR_ARCH = -28     # steep arch — tent poles, body hangs below
TIBIA_DROP = 18      # steep drop back to ground — sharp knee bend

SWING_FRACTION = 0.50  # 50/50 — seamless alternation, no dead zone
OVERLAP = 2            # scaled down for faster cycle

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

    # Pedipalp and cephalothorax axes for menace behavior
    for name in ['cephalothorax', 'pedipalp_L_base', 'pedipalp_L_tip',
                  'pedipalp_R_base', 'pedipalp_R_tip']:
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
        # Some legs don't have a tarsus bone — tiptoe goes on tibia instead
        has_tarsus = f'leg_{leg}_tarsus' in arm.pose.bones
        tarsus = f'leg_{leg}_tarsus'

        bend_f = axes[femur]['bend']
        bend_t = axes[tibia]['bend']
        bend_ta = axes[tarsus]['bend']
        swing_c = axes[coxa]['swing']

        is_front = leg.startswith('F')
        is_rear = leg.startswith('R')

        # Front legs are EXPLORATORY — they reach further, lift higher, feel the space
        # Mid legs are WORKHORSES — steady, reliable
        # Rear legs are PUSHERS — compact, powerful, close to ground
        if is_front:
            lift_mult = 1.4     # front legs lift MORE — they're sensing
            swing_mult = 1.5    # front legs REACH further forward
        elif is_rear:
            lift_mult = 0.7     # rear legs stay low — they push
            swing_mult = 0.6    # rear legs barely swing — compact strokes
        else:
            lift_mult = 1.0
            swing_mult = 1.0

        swing_mid = swing_start + swing_len // 2

        # ROWING STROKE: reach forward → plant → pull backward
        # Coxa does the reaching and pulling. Femur just clears the ground.

        # === STANCE END — leg is BEHIND, having pulled backward ===
        set_axis_rot(arm, coxa, swing_start, swing_c, COXA_SWING * 0.5 * swing_mult)
        set_axis_rot(arm, femur, swing_start, bend_f, FEMUR_ARCH)
        set_axis_rot(arm, tibia, swing_start, bend_t, TIBIA_DROP)
        if has_tarsus:
            set_axis_rot(arm, tarsus, swing_start, bend_ta, TARSUS_TIPTOE)

        # === LIFT — coxa swings FORWARD, femur lifts just to clear ground ===
        lift = swing_start + int(swing_len * 0.25)
        set_axis_rot(arm, coxa, lift, swing_c, COXA_SWING * 0.1 * swing_mult)
        set_axis_rot(arm, femur, lift, bend_f, FEMUR_ARCH + (-FEMUR_LIFT * 0.7 * lift_mult))
        set_axis_rot(arm, tibia, lift + d, bend_t, TIBIA_DROP + (-TIBIA_BEND * 0.4 * lift_mult))
        if has_tarsus:
            set_axis_rot(arm, tarsus, lift + d2, bend_ta, TARSUS_TIPTOE)

        # === REACH — coxa fully FORWARD, leg extended ahead ===
        set_axis_rot(arm, coxa, swing_mid, swing_c, -COXA_SWING * 0.5 * swing_mult)
        set_axis_rot(arm, femur, swing_mid, bend_f, FEMUR_ARCH + (-FEMUR_LIFT * lift_mult))
        set_axis_rot(arm, tibia, swing_mid + d, bend_t, TIBIA_DROP + (-TIBIA_BEND * 0.5 * lift_mult))
        if has_tarsus:
            set_axis_rot(arm, tarsus, swing_mid + d2, bend_ta, TARSUS_TIPTOE)

        # === HOVER (front legs) — hold the reach ===
        if is_front:
            hover = min(swing_mid + max(int(swing_len * 0.15), 1), stance_start - 2)
            set_axis_rot(arm, coxa, hover, swing_c, -COXA_SWING * 0.45 * swing_mult)
            set_axis_rot(arm, femur, hover, bend_f, FEMUR_ARCH + (-FEMUR_LIFT * 0.5 * lift_mult))

        # === PLANT — foot touches down AHEAD of body ===
        set_axis_rot(arm, coxa, stance_start, swing_c, -COXA_SWING * 0.4 * swing_mult)
        set_axis_rot(arm, femur, stance_start, bend_f, FEMUR_ARCH)
        set_axis_rot(arm, tibia, min(stance_start + d, cycle_end - 1), bend_t, TIBIA_DROP)
        if has_tarsus:
            set_axis_rot(arm, tarsus, min(stance_start + d2, cycle_end - 1), bend_ta, TARSUS_TIPTOE)

        # === PULL — coxa drags backward, pulling body over planted foot ===
        mid_stance = stance_start + (cycle_end - stance_start) // 2
        set_axis_rot(arm, coxa, mid_stance, swing_c, 0)
        set_axis_rot(arm, femur, mid_stance, bend_f, FEMUR_ARCH)
        set_axis_rot(arm, tibia, mid_stance, bend_t, TIBIA_DROP)
        set_axis_rot(arm, tarsus, mid_stance, bend_ta, TARSUS_TIPTOE)

        # === PUSH FINISH — leg ends up BEHIND, ready for next swing ===
        set_axis_rot(arm, coxa, cycle_end, swing_c, COXA_SWING * 0.5 * swing_mult)
        set_axis_rot(arm, femur, cycle_end, bend_f, FEMUR_ARCH)
        set_axis_rot(arm, tibia, cycle_end, bend_t, TIBIA_DROP)
        if has_tarsus:
            set_axis_rot(arm, tarsus, cycle_end, bend_ta, TARSUS_TIPTOE)

    for cycle in range(CYCLES):
        base = cycle * CYCLE_FRAMES
        half = CYCLE_FRAMES // 2  # with 50% swing, half = swing_len exactly

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

        # Body — FORWARD TILT throughout (approaching, not standing)
        # The spider leans toward its prey. Always.
        q1 = base + CYCLE_FRAMES // 4
        q2 = base + CYCLE_FRAMES // 2
        q3 = base + 3 * CYCLE_FRAMES // 4
        q4 = base + CYCLE_FRAMES

        ceph_bend = axes['cephalothorax']['bend']
        FORWARD_LEAN = -3  # constant forward tilt — approaching

        bob1 = compose_rot(Vector((1,0,0)), BODY_BOB + FORWARD_LEAN, Vector((0,0,1)), BODY_SWAY)
        bob_rest = compose_rot(Vector((1,0,0)), FORWARD_LEAN, Vector((0,0,1)), 0)
        bob2 = compose_rot(Vector((1,0,0)), BODY_BOB + FORWARD_LEAN, Vector((0,0,1)), -BODY_SWAY)

        set_composed(arm, 'root', base, bob_rest)
        set_composed(arm, 'root', q1, bob1)
        set_composed(arm, 'root', q2, bob_rest)
        set_composed(arm, 'root', q3, bob2)
        set_composed(arm, 'root', q4, bob_rest)

    # PEDIPALPS — independent of gait cycle. Own rhythm.
    # Runs across the FULL animation, not per-cycle.
    palp_l_bend = axes.get('pedipalp_L_base', {}).get('bend', Vector((1,0,0)))
    palp_r_bend = axes.get('pedipalp_R_base', {}).get('bend', Vector((1,0,0)))
    palp_l_tip_bend = axes.get('pedipalp_L_tip', {}).get('bend', Vector((1,0,0)))
    palp_r_tip_bend = axes.get('pedipalp_R_tip', {}).get('bend', Vector((1,0,0)))

    PALP_TWITCH = 4
    twitch_period = 14  # own tempo, independent of gait

    for f in range(0, total_frames, twitch_period):
        phase = (f // twitch_period) % 2
        if phase == 0:
            set_axis_rot(arm, 'pedipalp_L_base', f, palp_l_bend, -PALP_TWITCH)
            set_axis_rot(arm, 'pedipalp_L_tip', f + twitch_period // 3, palp_l_tip_bend, -PALP_TWITCH * 0.5)
            set_identity(arm, 'pedipalp_R_base', f)
            set_identity(arm, 'pedipalp_R_tip', f)
        else:
            set_identity(arm, 'pedipalp_L_base', f)
            set_identity(arm, 'pedipalp_L_tip', f)
            set_axis_rot(arm, 'pedipalp_R_base', f, palp_r_bend, -PALP_TWITCH)
            set_axis_rot(arm, 'pedipalp_R_tip', f + twitch_period // 3, palp_r_tip_bend, -PALP_TWITCH * 0.5)

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
