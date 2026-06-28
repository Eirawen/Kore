"""
Spider Threat Display Animation
by Kore

Something got too close. The spider rears up, spreads her fangs,
and raises her front legs to look as large as possible.

This is the arachnid equivalent of "back off."
"""

import bpy
import math

TOTAL_FRAMES = 80

# Threat display parameters
FRONT_LEG_RAISE = 30     # front legs go UP — look big
FRONT_COXA_SPREAD = 12   # front legs spread outward
BODY_REAR_BACK = 15      # cephalothorax tilts backward — exposing fangs
FANG_SPREAD = 18         # chelicerae open wide — showing weapons
PALP_FLARE = 15          # pedipalps spread outward
MID_LEG_BRACE = 5        # mid legs brace wider for stability
REAR_LEG_BRACE = 4       # rear legs brace backward
ABDOMEN_RAISE = 6        # abdomen lifts slightly

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

    print("Threat display animation...")

    # Key moments
    rest = 0
    notice = 10           # spider notices the threat
    rear_up = 25          # rearing back, legs starting to rise
    full_threat = 40      # maximum threat posture — HOLD
    hold_end = 55         # still holding
    shimmy_1 = 60         # aggressive shimmy — "I mean it"
    shimmy_2 = 65
    settle = 72           # begin to settle
    end = TOTAL_FRAMES    # back to rest (or hold if looping)

    # === REST ===
    all_bones = ['root', 'cephalothorax', 'abdomen',
                 'fang_L', 'fang_R',
                 'pedipalp_L_base', 'pedipalp_L_tip',
                 'pedipalp_R_base', 'pedipalp_R_tip']
    for leg in ['FL', 'FR', 'ML', 'MR', 'RL', 'RR']:
        all_bones.extend([f'leg_{leg}_coxa', f'leg_{leg}_femur',
                          f'leg_{leg}_tibia', f'leg_{leg}_tarsus'])

    for bone in all_bones:
        set_rot(arm, bone, rest, 0, 0, 0)

    # === NOTICE — slight startle ===
    set_rot(arm, 'cephalothorax', notice, rx=-BODY_REAR_BACK * 0.2)
    set_rot(arm, 'leg_FL_coxa', notice, ry=FRONT_COXA_SPREAD * 0.3)
    set_rot(arm, 'leg_FR_coxa', notice, ry=-FRONT_COXA_SPREAD * 0.3)

    # === REAR UP — the big move ===
    # Body tilts backward
    set_rot(arm, 'cephalothorax', rear_up, rx=-BODY_REAR_BACK * 0.7)
    set_rot(arm, 'abdomen', rear_up, rx=ABDOMEN_RAISE * 0.5)

    # Front legs rising
    set_rot(arm, 'leg_FL_coxa', rear_up, ry=FRONT_COXA_SPREAD * 0.7)
    set_rot(arm, 'leg_FL_femur', rear_up, rx=-FRONT_LEG_RAISE * 0.7)
    set_rot(arm, 'leg_FL_tibia', rear_up, rx=FRONT_LEG_RAISE * 0.3)
    set_rot(arm, 'leg_FR_coxa', rear_up, ry=-FRONT_COXA_SPREAD * 0.7)
    set_rot(arm, 'leg_FR_femur', rear_up, rx=-FRONT_LEG_RAISE * 0.7)
    set_rot(arm, 'leg_FR_tibia', rear_up, rx=FRONT_LEG_RAISE * 0.3)

    # Fangs starting to open
    set_rot(arm, 'fang_L', rear_up, rz=FANG_SPREAD * 0.5)
    set_rot(arm, 'fang_R', rear_up, rz=-FANG_SPREAD * 0.5)

    # === FULL THREAT — maximum intimidation ===
    # Body fully reared
    set_rot(arm, 'cephalothorax', full_threat, rx=-BODY_REAR_BACK)
    set_rot(arm, 'abdomen', full_threat, rx=ABDOMEN_RAISE)

    # Front legs fully raised and spread
    set_rot(arm, 'leg_FL_coxa', full_threat, ry=FRONT_COXA_SPREAD)
    set_rot(arm, 'leg_FL_femur', full_threat, rx=-FRONT_LEG_RAISE)
    set_rot(arm, 'leg_FL_tibia', full_threat, rx=FRONT_LEG_RAISE * 0.4)
    set_rot(arm, 'leg_FL_tarsus', full_threat, rx=-FRONT_LEG_RAISE * 0.2)
    set_rot(arm, 'leg_FR_coxa', full_threat, ry=-FRONT_COXA_SPREAD)
    set_rot(arm, 'leg_FR_femur', full_threat, rx=-FRONT_LEG_RAISE)
    set_rot(arm, 'leg_FR_tibia', full_threat, rx=FRONT_LEG_RAISE * 0.4)
    set_rot(arm, 'leg_FR_tarsus', full_threat, rx=-FRONT_LEG_RAISE * 0.2)

    # Fangs wide open
    set_rot(arm, 'fang_L', full_threat, rz=FANG_SPREAD)
    set_rot(arm, 'fang_R', full_threat, rz=-FANG_SPREAD)

    # Pedipalps flared
    set_rot(arm, 'pedipalp_L_base', full_threat, ry=PALP_FLARE, rx=-PALP_FLARE * 0.5)
    set_rot(arm, 'pedipalp_R_base', full_threat, ry=-PALP_FLARE, rx=-PALP_FLARE * 0.5)

    # Mid legs brace outward for stability
    set_rot(arm, 'leg_ML_coxa', full_threat, ry=MID_LEG_BRACE)
    set_rot(arm, 'leg_MR_coxa', full_threat, ry=-MID_LEG_BRACE)
    set_rot(arm, 'leg_ML_femur', full_threat, rx=-MID_LEG_BRACE)
    set_rot(arm, 'leg_MR_femur', full_threat, rx=-MID_LEG_BRACE)

    # Rear legs brace backward
    set_rot(arm, 'leg_RL_coxa', full_threat, ry=REAR_LEG_BRACE)
    set_rot(arm, 'leg_RR_coxa', full_threat, ry=-REAR_LEG_BRACE)

    # === HOLD — maintain threat posture ===
    # Copy full_threat pose
    set_rot(arm, 'cephalothorax', hold_end, rx=-BODY_REAR_BACK)
    set_rot(arm, 'abdomen', hold_end, rx=ABDOMEN_RAISE)
    set_rot(arm, 'leg_FL_coxa', hold_end, ry=FRONT_COXA_SPREAD)
    set_rot(arm, 'leg_FL_femur', hold_end, rx=-FRONT_LEG_RAISE)
    set_rot(arm, 'leg_FL_tibia', hold_end, rx=FRONT_LEG_RAISE * 0.4)
    set_rot(arm, 'leg_FL_tarsus', hold_end, rx=-FRONT_LEG_RAISE * 0.2)
    set_rot(arm, 'leg_FR_coxa', hold_end, ry=-FRONT_COXA_SPREAD)
    set_rot(arm, 'leg_FR_femur', hold_end, rx=-FRONT_LEG_RAISE)
    set_rot(arm, 'leg_FR_tibia', hold_end, rx=FRONT_LEG_RAISE * 0.4)
    set_rot(arm, 'leg_FR_tarsus', hold_end, rx=-FRONT_LEG_RAISE * 0.2)
    set_rot(arm, 'fang_L', hold_end, rz=FANG_SPREAD)
    set_rot(arm, 'fang_R', hold_end, rz=-FANG_SPREAD)
    set_rot(arm, 'pedipalp_L_base', hold_end, ry=PALP_FLARE, rx=-PALP_FLARE * 0.5)
    set_rot(arm, 'pedipalp_R_base', hold_end, ry=-PALP_FLARE, rx=-PALP_FLARE * 0.5)
    set_rot(arm, 'leg_ML_coxa', hold_end, ry=MID_LEG_BRACE)
    set_rot(arm, 'leg_MR_coxa', hold_end, ry=-MID_LEG_BRACE)
    set_rot(arm, 'leg_ML_femur', hold_end, rx=-MID_LEG_BRACE)
    set_rot(arm, 'leg_MR_femur', hold_end, rx=-MID_LEG_BRACE)
    set_rot(arm, 'leg_RL_coxa', hold_end, ry=REAR_LEG_BRACE)
    set_rot(arm, 'leg_RR_coxa', hold_end, ry=-REAR_LEG_BRACE)

    # === SHIMMY — aggressive shake, "I MEAN IT" ===
    set_rot(arm, 'cephalothorax', shimmy_1, rx=-BODY_REAR_BACK, rz=4)
    set_rot(arm, 'leg_FL_femur', shimmy_1, rx=-FRONT_LEG_RAISE * 1.1)
    set_rot(arm, 'leg_FR_femur', shimmy_1, rx=-FRONT_LEG_RAISE * 0.9)
    set_rot(arm, 'fang_L', shimmy_1, rz=FANG_SPREAD * 1.2)
    set_rot(arm, 'fang_R', shimmy_1, rz=-FANG_SPREAD * 0.8)

    set_rot(arm, 'cephalothorax', shimmy_2, rx=-BODY_REAR_BACK, rz=-4)
    set_rot(arm, 'leg_FL_femur', shimmy_2, rx=-FRONT_LEG_RAISE * 0.9)
    set_rot(arm, 'leg_FR_femur', shimmy_2, rx=-FRONT_LEG_RAISE * 1.1)
    set_rot(arm, 'fang_L', shimmy_2, rz=FANG_SPREAD * 0.8)
    set_rot(arm, 'fang_R', shimmy_2, rz=-FANG_SPREAD * 1.2)

    # === SETTLE — slowly lower back down ===
    set_rot(arm, 'cephalothorax', settle, rx=-BODY_REAR_BACK * 0.4)
    set_rot(arm, 'leg_FL_femur', settle, rx=-FRONT_LEG_RAISE * 0.4)
    set_rot(arm, 'leg_FR_femur', settle, rx=-FRONT_LEG_RAISE * 0.4)
    set_rot(arm, 'fang_L', settle, rz=FANG_SPREAD * 0.3)
    set_rot(arm, 'fang_R', settle, rz=-FANG_SPREAD * 0.3)

    # === END — back to rest ===
    for bone in all_bones:
        set_rot(arm, bone, end, 0, 0, 0)

    bpy.context.scene.frame_start = 0
    bpy.context.scene.frame_end = TOTAL_FRAMES
    bpy.context.scene.frame_current = 0

    if arm.animation_data and arm.animation_data.action:
        for fc in arm.animation_data.action.fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = 'BEZIER'
                kp.handle_left_type = 'AUTO_CLAMPED'
                kp.handle_right_type = 'AUTO_CLAMPED'

    print(f"Threat display: {TOTAL_FRAMES} frames. Press Space!")
    print("  Notice → Rear up → FULL THREAT → Shimmy → Settle")

try:
    animate()
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
