"""
VELOCITY CHECK — catch dead frames and jolts NUMERICALLY, no vision cost.

Khaled's note on v10 ("she PAUSES, then her hand goes in with a JOLT") is
detectable as pure arithmetic: sample a bone's world position every frame,
differentiate, and look for (a) near-zero speed inside a move = a dead
frame that reads as a paused game, and (b) acceleration spikes = jolts.
Also reports whether two components OVERLAP in time or run sequentially.

Run:
  blender --background --python animate_coy6.py -- --velcheck
(or standalone: it re-runs the authoring script's logic via import)
"""
import bpy
import sys
import math
from mathutils import Vector


def report(arm, scene, bones, f0, f1, label, quiet_thresh=0.06):
    """Per-frame speed profile for a set of bones (world space)."""
    prev = None
    speeds = []
    for f in range(f0, f1 + 1):
        scene.frame_set(f)
        p = sum(((arm.matrix_world @ arm.pose.bones[b].head)
                 for b in bones), Vector((0, 0, 0))) / len(bones)
        if prev is not None:
            speeds.append((f, (p - prev).length))
        prev = p
    if not speeds:
        return
    peak = max(s for _, s in speeds)
    if peak < 1e-9:
        print('VEL[%s] static' % label)
        return
    norm = [(f, s / peak) for f, s in speeds]
    # dead frames: near-zero speed INSIDE the active span only. A frozen
    # hand during the settled hold is the intent, not a defect — only a
    # stall in the middle of a move reads as a paused game.
    act = [f for f, s in norm if s >= quiet_thresh]
    a0, a1 = (act[0], act[-1]) if act else (0, -1)
    run, worst_run = 0, 0
    for f, s in norm:
        if not (a0 <= f <= a1):
            continue
        if s < quiet_thresh:
            run += 1
            worst_run = max(worst_run, run)
        else:
            run = 0
    # jolts: frame-to-frame acceleration spikes
    acc = [(norm[i][0], abs(norm[i][1] - norm[i - 1][1]))
           for i in range(1, len(norm))]
    jolt_f, jolt_v = max(acc, key=lambda x: x[1])
    active = act
    print('VEL[%-10s] active f%d-%d  peak=%.4f  mid-move_dead_run=%df  '
          'max_accel=%.3f @f%d %s'
          % (label, active[0] if active else -1, active[-1] if active else -1,
             peak, worst_run, jolt_v, jolt_f,
             'JOLT' if jolt_v > 0.22 else 'smooth'))
    return (active[0], active[-1]) if active else None
