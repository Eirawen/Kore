"""
Spider Threat Display v2 — Bone-Local Axes + Animation Principles
by Kore

Fixes from v1:
  1. Bone-local axes — front legs lift UP, not sideways
  2. Anticipation frame — compress before exploding upward
  3. Body rear-back actually visible
  4. Snappy settle — drops suddenly, not gliding
  5. Bigger fang spread
  6. Overlapping action — legs don't all arrive at the same time
"""

import bpy
import math
import mathutils
from mathutils import Vector

TOTAL_FRAMES = 90

FRONT_LEG_RAISE = 35
FRONT_COXA_SPREAD = 10
BODY_REAR_BACK = 20
FANG_SPREAD = 22
PALP_FLARE = 18
MID_LEG_BRACE = 6
REAR_LEG_BRACE = 5
ABDOMEN_RAISE = 8

def deg(d):
    return math.radians(d)

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

def set_combined(arm, bone_name, frame, axis1, angle1, axis2, angle2):
    if bone_name not in arm.pose.bones:
        return
    pb = arm.pose.bones[bone_name]
    pb.rotation_mode = 'QUATERNION'
    q1 = mathutils.Quaternion(axis1, math.radians(angle1))
    q2 = mathutils.Quaternion(axis2, math.radians(angle2))
    pb.rotation_quaternion = q1 @ q2
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

    print("Threat display v2 — bone-local axes + animation principles")

    # Precompute axes
    axes = {}
    all_leg_bones = []
    for leg in ['FL', 'FR', 'ML', 'MR', 'RL', 'RR']:
        for seg in ['coxa', 'femur', 'tibia', 'tarsus']:
            name = f'leg_{leg}_{seg}'
            axes[name] = {
                'bend': get_bend_axis(arm, name),
                'swing': get_swing_axis(arm, name),
            }
            all_leg_bones.append(name)

    for name in ['cephalothorax', 'abdomen', 'root',
                  'fang_L', 'fang_R',
                  'pedipalp_L_base', 'pedipalp_L_tip',
                  'pedipalp_R_base', 'pedipalp_R_tip']:
        axes[name] = {
            'bend': get_bend_axis(arm, name),
            'swing': get_swing_axis(arm, name),
        }

    # Timeline
    rest = 0
    anticipate = 8        # COMPRESS — hunker down before exploding up
    notice = 14           # start of rear-up
    rear_up = 28          # front legs rising fast
    full_threat = 42      # maximum intimidation — HOLD
    hold_end = 56         # still holding
    shimmy_1 = 60
    shimmy_2 = 66
    snap_down = 72        # SNAP — sudden drop, not gentle settle
    rest_end = TOTAL_FRAMES

    # Collect all bone names for rest keyframes
    all_bones = all_leg_bones + ['cephalothorax', 'abdomen', 'root',
        'fang_L', 'fang_R', 'pedipalp_L_base', 'pedipalp_L_tip',
        'pedipalp_R_base', 'pedipalp_R_tip']

    # === REST ===
    for bone in all_bones:
        set_identity(arm, bone, rest)

    # === ANTICIPATION — compress downward before the explosion ===
    # Legs bend slightly inward, body drops
    bend_ceph = axes['cephalothorax']['bend']
    set_axis_rot(arm, 'cephalothorax', anticipate, bend_ceph, 4)  # slight duck
    for leg in ['FL', 'FR']:
        bend_f = axes[f'leg_{leg}_femur']['bend']
        set_axis_rot(arm, f'leg_{leg}_femur', anticipate, bend_f, 5)  # compress down

    # === NOTICE — start the rear-up ===
    set_axis_rot(arm, 'cephalothorax', notice, bend_ceph, -BODY_REAR_BACK * 0.3)
    for leg in ['FL', 'FR']:
        bend_f = axes[f'leg_{leg}_femur']['bend']
        set_axis_rot(arm, f'leg_{leg}_femur', notice, bend_f, -FRONT_LEG_RAISE * 0.2)

    # === REAR UP — the big move ===
    set_axis_rot(arm, 'cephalothorax', rear_up, bend_ceph, -BODY_REAR_BACK * 0.7)
    bend_abd = axes['abdomen']['bend']
    set_axis_rot(arm, 'abdomen', rear_up, bend_abd, -ABDOMEN_RAISE * 0.5)

    # Front legs rising — overlapping: FL arrives 2 frames before FR
    for i, leg in enumerate(['FL', 'FR']):
        offset = i * 2  # FR is 2 frames behind FL
        bend_c = axes[f'leg_{leg}_coxa']['bend']
        swing_c = axes[f'leg_{leg}_coxa']['swing']
        bend_f = axes[f'leg_{leg}_femur']['bend']
        bend_t = axes[f'leg_{leg}_tibia']['bend']

        set_axis_rot(arm, f'leg_{leg}_coxa', rear_up + offset, swing_c, FRONT_COXA_SPREAD * 0.7 * (1 if leg.endswith('L') else -1))
        set_axis_rot(arm, f'leg_{leg}_femur', rear_up + offset, bend_f, -FRONT_LEG_RAISE * 0.7)
        set_axis_rot(arm, f'leg_{leg}_tibia', rear_up + offset, bend_t, -FRONT_LEG_RAISE * 0.3)

    # Fangs opening
    bend_fl = axes['fang_L']['bend']
    bend_fr = axes['fang_R']['bend']
    swing_fl = axes['fang_L']['swing']
    swing_fr = axes['fang_R']['swing']
    set_axis_rot(arm, 'fang_L', rear_up, swing_fl, FANG_SPREAD * 0.5)
    set_axis_rot(arm, 'fang_R', rear_up, swing_fr, -FANG_SPREAD * 0.5)

    # === FULL THREAT — maximum intimidation ===
    set_axis_rot(arm, 'cephalothorax', full_threat, bend_ceph, -BODY_REAR_BACK)
    set_axis_rot(arm, 'abdomen', full_threat, bend_abd, -ABDOMEN_RAISE)

    for i, leg in enumerate(['FL', 'FR']):
        offset = i * 2
        swing_c = axes[f'leg_{leg}_coxa']['swing']
        bend_f = axes[f'leg_{leg}_femur']['bend']
        bend_t = axes[f'leg_{leg}_tibia']['bend']

        side = 1 if leg.endswith('L') else -1
        set_axis_rot(arm, f'leg_{leg}_coxa', full_threat + offset, swing_c, FRONT_COXA_SPREAD * side)
        set_axis_rot(arm, f'leg_{leg}_femur', full_threat + offset, bend_f, -FRONT_LEG_RAISE)
        set_axis_rot(arm, f'leg_{leg}_tibia', full_threat + offset, bend_t, -FRONT_LEG_RAISE * 0.4)

    # Fangs wide
    set_axis_rot(arm, 'fang_L', full_threat, swing_fl, FANG_SPREAD)
    set_axis_rot(arm, 'fang_R', full_threat, swing_fr, -FANG_SPREAD)

    # Pedipalps flare
    bend_pl = axes['pedipalp_L_base']['bend']
    bend_pr = axes['pedipalp_R_base']['bend']
    swing_pl = axes['pedipalp_L_base']['swing']
    swing_pr = axes['pedipalp_R_base']['swing']
    set_combined(arm, 'pedipalp_L_base', full_threat, bend_pl, -PALP_FLARE * 0.5, swing_pl, PALP_FLARE)
    set_combined(arm, 'pedipalp_R_base', full_threat, bend_pr, -PALP_FLARE * 0.5, swing_pr, -PALP_FLARE)

    # Mid legs brace
    for leg in ['ML', 'MR']:
        swing_c = axes[f'leg_{leg}_coxa']['swing']
        bend_f = axes[f'leg_{leg}_femur']['bend']
        side = 1 if leg.endswith('L') else -1
        set_axis_rot(arm, f'leg_{leg}_coxa', full_threat, swing_c, MID_LEG_BRACE * side)
        set_axis_rot(arm, f'leg_{leg}_femur', full_threat, bend_f, -MID_LEG_BRACE)

    # Rear legs brace
    for leg in ['RL', 'RR']:
        swing_c = axes[f'leg_{leg}_coxa']['swing']
        side = 1 if leg.endswith('L') else -1
        set_axis_rot(arm, f'leg_{leg}_coxa', full_threat, swing_c, REAR_LEG_BRACE * side)

    # === HOLD — copy full threat ===
    set_axis_rot(arm, 'cephalothorax', hold_end, bend_ceph, -BODY_REAR_BACK)
    set_axis_rot(arm, 'abdomen', hold_end, bend_abd, -ABDOMEN_RAISE)
    for leg in ['FL', 'FR']:
        swing_c = axes[f'leg_{leg}_coxa']['swing']
        bend_f = axes[f'leg_{leg}_femur']['bend']
        bend_t = axes[f'leg_{leg}_tibia']['bend']
        side = 1 if leg.endswith('L') else -1
        set_axis_rot(arm, f'leg_{leg}_coxa', hold_end, swing_c, FRONT_COXA_SPREAD * side)
        set_axis_rot(arm, f'leg_{leg}_femur', hold_end, bend_f, -FRONT_LEG_RAISE)
        set_axis_rot(arm, f'leg_{leg}_tibia', hold_end, bend_t, -FRONT_LEG_RAISE * 0.4)
    set_axis_rot(arm, 'fang_L', hold_end, swing_fl, FANG_SPREAD)
    set_axis_rot(arm, 'fang_R', hold_end, swing_fr, -FANG_SPREAD)
    set_combined(arm, 'pedipalp_L_base', hold_end, bend_pl, -PALP_FLARE * 0.5, swing_pl, PALP_FLARE)
    set_combined(arm, 'pedipalp_R_base', hold_end, bend_pr, -PALP_FLARE * 0.5, swing_pr, -PALP_FLARE)
    for leg in ['ML', 'MR']:
        swing_c = axes[f'leg_{leg}_coxa']['swing']
        bend_f = axes[f'leg_{leg}_femur']['bend']
        side = 1 if leg.endswith('L') else -1
        set_axis_rot(arm, f'leg_{leg}_coxa', hold_end, swing_c, MID_LEG_BRACE * side)
        set_axis_rot(arm, f'leg_{leg}_femur', hold_end, bend_f, -MID_LEG_BRACE)
    for leg in ['RL', 'RR']:
        swing_c = axes[f'leg_{leg}_coxa']['swing']
        side = 1 if leg.endswith('L') else -1
        set_axis_rot(arm, f'leg_{leg}_coxa', hold_end, swing_c, REAR_LEG_BRACE * side)

    # === SHIMMY — aggressive asymmetric shake ===
    set_axis_rot(arm, 'cephalothorax', shimmy_1, bend_ceph, -BODY_REAR_BACK)
    bend_fl_fem = axes['leg_FL_femur']['bend']
    bend_fr_fem = axes['leg_FR_femur']['bend']
    set_axis_rot(arm, 'leg_FL_femur', shimmy_1, bend_fl_fem, -FRONT_LEG_RAISE * 1.15)
    set_axis_rot(arm, 'leg_FR_femur', shimmy_1, bend_fr_fem, -FRONT_LEG_RAISE * 0.85)
    set_axis_rot(arm, 'fang_L', shimmy_1, swing_fl, FANG_SPREAD * 1.2)
    set_axis_rot(arm, 'fang_R', shimmy_1, swing_fr, -FANG_SPREAD * 0.8)

    set_axis_rot(arm, 'cephalothorax', shimmy_2, bend_ceph, -BODY_REAR_BACK)
    set_axis_rot(arm, 'leg_FL_femur', shimmy_2, bend_fl_fem, -FRONT_LEG_RAISE * 0.85)
    set_axis_rot(arm, 'leg_FR_femur', shimmy_2, bend_fr_fem, -FRONT_LEG_RAISE * 1.15)
    set_axis_rot(arm, 'fang_L', shimmy_2, swing_fl, FANG_SPREAD * 0.8)
    set_axis_rot(arm, 'fang_R', shimmy_2, swing_fr, -FANG_SPREAD * 1.2)

    # === SNAP DOWN — sudden drop, not gentle ===
    # Only 4 frames from shimmy to snap — fast!
    for bone in all_bones:
        set_identity(arm, bone, snap_down)

    # Tiny overshoot — legs go slightly PAST rest then settle
    for leg in ['FL', 'FR']:
        bend_f = axes[f'leg_{leg}_femur']['bend']
        set_axis_rot(arm, f'leg_{leg}_femur', snap_down + 3, bend_f, 4)  # overshoot down

    # === FINAL REST ===
    for bone in all_bones:
        set_identity(arm, bone, rest_end)

    bpy.context.scene.frame_start = 0
    bpy.context.scene.frame_end = TOTAL_FRAMES
    bpy.context.scene.frame_current = 0

    # Bezier for the buildup, but LINEAR for the snap-down (fast drop)
    if arm.animation_data and arm.animation_data.action:
        try:
            for layer in arm.animation_data.action.layers:
                for strip in layer.strips:
                    for cb in strip.channelbags:
                        for fc in cb.fcurves:
                            for kp in fc.keyframe_points:
                                if kp.co[0] >= snap_down - 2:
                                    kp.interpolation = 'LINEAR'
                                else:
                                    kp.interpolation = 'BEZIER'
                                    kp.handle_left_type = 'AUTO_CLAMPED'
                                    kp.handle_right_type = 'AUTO_CLAMPED'
        except:
            pass

    print(f"Threat display v2: {TOTAL_FRAMES} frames")
    print("  Anticipation → Rear up → FULL THREAT → Shimmy → SNAP down → Rest")

try:
    animate()
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
