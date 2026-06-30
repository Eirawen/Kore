"""
Blender 5.1 Compatibility Helpers
by Kore

Blender 5.1 replaced action.fcurves with a layered action system.
This module provides helpers that work across Blender versions.
"""


def smooth_keyframes(armature):
    """
    Set all keyframe handles to BEZIER / AUTO_CLAMPED for smooth interpolation.
    Works with both legacy (action.fcurves) and Blender 5.x (layered actions).
    """
    if not armature or not armature.animation_data or not armature.animation_data.action:
        return 0

    action = armature.animation_data.action
    count = 0

    # Try Blender 5.x layered action API first
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
                                count += 1
        return count

    # Fall back to legacy API (Blender < 5.0)
    if hasattr(action, 'fcurves'):
        for fc in action.fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = 'BEZIER'
                kp.handle_left_type = 'AUTO_CLAMPED'
                kp.handle_right_type = 'AUTO_CLAMPED'
                count += 1
        return count

    return 0
