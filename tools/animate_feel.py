"""
Spider Pedipalp Feeling Animation
by Kore

The spider probes the air with its pedipalps — sensing, tasting,
searching. Alternating left and right, with subtle fang twitches
and a curious forward lean.

This is an idle/sensing animation, not locomotion.
"""

import bpy
import math

CYCLE_FRAMES = 60
CYCLES = 2

PALP_REACH = 15       # pedipalp base reaches forward
PALP_CURL = 20        # pedipalp tip curls inward (touching/feeling)
FANG_TWITCH = 8       # chelicerae open slightly during probing
BODY_LEAN = 3         # body leans forward when interested
HEAD_TILT = 4         # subtle head movement

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

    print("Pedipalp feeling animation...")
    total_frames = CYCLE_FRAMES * CYCLES

    for cycle in range(CYCLES):
        b = cycle * CYCLE_FRAMES

        # Key moments
        rest = b
        left_reach = b + int(CYCLE_FRAMES * 0.15)
        left_feel = b + int(CYCLE_FRAMES * 0.3)
        left_retract = b + int(CYCLE_FRAMES * 0.45)
        mid = b + int(CYCLE_FRAMES * 0.5)
        right_reach = b + int(CYCLE_FRAMES * 0.65)
        right_feel = b + int(CYCLE_FRAMES * 0.8)
        right_retract = b + int(CYCLE_FRAMES * 0.9)
        end = b + CYCLE_FRAMES

        # === LEFT PEDIPALP: reach, feel, retract ===
        # Rest
        set_rot(arm, 'pedipalp_L_base', rest, rx=0, ry=0)
        set_rot(arm, 'pedipalp_L_tip', rest, rx=0, ry=0)

        # Reach forward
        set_rot(arm, 'pedipalp_L_base', left_reach, rx=-PALP_REACH, ry=3)
        set_rot(arm, 'pedipalp_L_tip', left_reach, rx=-PALP_REACH * 0.5)

        # Feel/probe — tip curls inward
        set_rot(arm, 'pedipalp_L_base', left_feel, rx=-PALP_REACH * 0.8, ry=5)
        set_rot(arm, 'pedipalp_L_tip', left_feel, rx=PALP_CURL)

        # Retract
        set_rot(arm, 'pedipalp_L_base', left_retract, rx=-PALP_REACH * 0.3)
        set_rot(arm, 'pedipalp_L_tip', left_retract, rx=PALP_CURL * 0.3)

        # Back to rest
        set_rot(arm, 'pedipalp_L_base', mid, rx=0)
        set_rot(arm, 'pedipalp_L_tip', mid, rx=0)

        # === RIGHT PEDIPALP: reach, feel, retract (offset by half cycle) ===
        set_rot(arm, 'pedipalp_R_base', rest, rx=0)
        set_rot(arm, 'pedipalp_R_tip', rest, rx=0)

        # Slight anticipatory twitch while left is probing
        set_rot(arm, 'pedipalp_R_base', left_feel, rx=-PALP_REACH * 0.2)
        set_rot(arm, 'pedipalp_R_tip', left_feel, rx=0)

        # Reach
        set_rot(arm, 'pedipalp_R_base', right_reach, rx=-PALP_REACH, ry=-3)
        set_rot(arm, 'pedipalp_R_tip', right_reach, rx=-PALP_REACH * 0.5)

        # Feel
        set_rot(arm, 'pedipalp_R_base', right_feel, rx=-PALP_REACH * 0.8, ry=-5)
        set_rot(arm, 'pedipalp_R_tip', right_feel, rx=PALP_CURL)

        # Retract
        set_rot(arm, 'pedipalp_R_base', right_retract, rx=-PALP_REACH * 0.3)
        set_rot(arm, 'pedipalp_R_tip', right_retract, rx=PALP_CURL * 0.3)

        # Rest
        set_rot(arm, 'pedipalp_R_base', end, rx=0)
        set_rot(arm, 'pedipalp_R_tip', end, rx=0)

        # === FANGS: twitch open during probing ===
        set_rot(arm, 'fang_L', rest, rz=0)
        set_rot(arm, 'fang_R', rest, rz=0)

        # Open slightly when left palp feels
        set_rot(arm, 'fang_L', left_feel, rz=FANG_TWITCH)
        set_rot(arm, 'fang_R', left_feel, rz=-FANG_TWITCH)

        # Close
        set_rot(arm, 'fang_L', mid, rz=0)
        set_rot(arm, 'fang_R', mid, rz=0)

        # Open when right palp feels
        set_rot(arm, 'fang_L', right_feel, rz=FANG_TWITCH * 0.7)
        set_rot(arm, 'fang_R', right_feel, rz=-FANG_TWITCH * 0.7)

        # Close
        set_rot(arm, 'fang_L', end, rz=0)
        set_rot(arm, 'fang_R', end, rz=0)

        # === BODY: lean forward when probing, slight sway ===
        set_rot(arm, 'cephalothorax', rest, rx=0, rz=0)
        set_rot(arm, 'cephalothorax', left_feel, rx=-BODY_LEAN, rz=HEAD_TILT)
        set_rot(arm, 'cephalothorax', mid, rx=0, rz=0)
        set_rot(arm, 'cephalothorax', right_feel, rx=-BODY_LEAN, rz=-HEAD_TILT)
        set_rot(arm, 'cephalothorax', end, rx=0, rz=0)

    bpy.context.scene.frame_start = 0
    bpy.context.scene.frame_end = total_frames
    bpy.context.scene.frame_current = 0

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
