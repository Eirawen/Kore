# MOTION PASS for the three approved sword attacks (light lunge, heavy_lr,
# heavy_rl) on the wristed rig with Khaled's retargeted grip (thumb-tip
# amendment included via the baseline).
#
# Poses live in tools/sword_attack_keys.py (ATTACKS, world-space authored,
# amended per Khaled 2026-07-21). THIS file owns TIME:
#   - a TIMELINE per attack: (key_label, authored_frame); repeated labels =
#     held beats (anticipation HOLD before the snap)
#   - house retime pattern (animate_casts.py): (old->new) anchors, monotonic
#     piecewise-linear remap. Spacing pushed into gather/windup + HOLD; the
#     drive/sweep span stays FAST; recover eased long.
#   - Bezier AUTO_CLAMPED everywhere (no overshoot - fingers hyperextend)
#   - object eulers unwrapped key-to-key (mod-360 + the (x+180,180-y,z+180)
#     twin) so the wrist ROLLS instead of flipping (gotcha 28)
#   - wrist/pronation quats keyed per key, hemisphere-matched
#
# Targets: light ~0.8 s, heavies ~1.07 s @ 60 fps.
#
#   blender --background cgtrader_hand_wristed.blend --python animate_sword_attacks.py \
#       -- [light heavy_lr heavy_rl] [--full] [--samples N]
import bpy, sys, math, json
from mathutils import Vector, Euler, Matrix, Quaternion

# pose keys + solver + staging (execs retarget_grip -> seat_grip staging)
SRC = r'\\wsl.localhost\Ubuntu\home\khaled\Kore\tools\sword_attack_keys.py'
_code = open(SRC).read()
exec(_code[:_code.rfind('def main')])

FPS = 60

# ────────────────────────── time authoring ──────────────────────────
# (label, authored_frame); repeated label = held beat.
TIMELINES = {
    'light': [
        ('1_ready', 1), ('1b_gather', 9), ('1b_gather', 13),
        ('2_drive', 17), ('2b_mid', 19), ('3_strike', 21),
        ('3_strike', 26), ('4_recover', 39),
    ],
    'heavy_lr': [
        ('1_ready', 1), ('1b_coil', 6), ('2_windup', 10), ('2_windup', 14),
        ('2b_arc', 18), ('3_sweep', 21), ('4_through', 27),
        ('4_through', 31), ('5_recover', 44),
    ],
    'heavy_rl': [
        ('1_ready', 1), ('1b_coil', 6), ('2_windup', 10), ('2_windup', 14),
        ('2b_arc', 18), ('3_sweep', 21), ('4_through', 27),
        ('4_through', 31), ('5_recover', 44),
    ],
}
# retime anchors (old_frame -> new_frame), house pattern. Light: gather
# breathes (1->12), HOLD stretched (13->20), the 8-frame drive->strike snap
# is preserved 1:1 (21->28), impact registers (26->35), recover eased to 48.
# Heavies: coil breathes (10->16), windup HOLD telegraphs (14->26), the
# 13-frame sweep->through span maps to 12 (26->38, stays FAST), follow-
# through settles (31->46), recover eased to 64.
RETIME = {
    'light':    [(1, 1), (9, 12), (13, 20), (21, 28), (26, 35), (39, 48)],
    'heavy_lr': [(1, 1), (10, 16), (14, 26), (27, 38), (31, 46), (44, 64)],
    'heavy_rl': [(1, 1), (10, 16), (14, 26), (27, 38), (31, 46), (44, 64)],
}
TOTAL = {'light': 39, 'heavy_lr': 44, 'heavy_rl': 44}   # AUTHORED end frames
# (remapped through RETIME at build: light -> 48 f, heavies -> 64 f)

PHASES = {
    'light': [(1, 'ready'), (5, 'gather'), (13, 'HOLD'), (17, 'drive'),
              (21, 'strike'), (27, 'recover')],
    'heavy_lr': [(1, 'ready'), (4, 'windup'), (14, 'HOLD'), (15, 'sweep'),
                 (27, 'through'), (32, 'recover')],
    'heavy_rl': [(1, 'ready'), (4, 'windup'), (14, 'HOLD'), (15, 'sweep'),
                 (27, 'through'), (32, 'recover')],
}


def remap_frame(f, anchors):
    if f <= anchors[0][0]:
        return max(1, anchors[0][1] + (f - anchors[0][0]))
    for (o0, n0), (o1, n1) in zip(anchors, anchors[1:]):
        if f <= o1:
            t = (f - o0) / (o1 - o0)
            return int(round(n0 + t * (n1 - n0)))
    o0, n0 = anchors[-1]
    return int(round(n0 + (f - o0)))


# ────────────────────────── solve + unwrap ──────────────────────────

def solve_all_keys(right, sword, base_hand_q, base_roll, attack):
    """Solve each authored key once -> {label: (loc, euler_deg, fore_q,
    hand_q)}. Eulers raw here; unwrapped later in timeline order."""
    out = {}
    for key in ATTACKS[attack]:
        solve_key(right, sword, base_hand_q, base_roll, key)
        eul = right.rotation_euler
        out[key[0]] = (Vector(right.location),
                       [math.degrees(a) for a in eul],
                       right.pose.bones['forearm'].rotation_quaternion.copy(),
                       right.pose.bones['hand'].rotation_quaternion.copy())
    return out


def unwrap(prev, rot):
    """Euler-deg unwrap vs prev: mod-360 per channel + the flipped twin."""
    cands = [list(rot), [rot[0] + 180, 180 - rot[1], rot[2] + 180]]
    best, best_d = None, None
    for cand in cands:
        adj = []
        for i, a in enumerate(cand):
            if prev is not None:
                while a - prev[i] > 180:
                    a -= 360
                while a - prev[i] < -180:
                    a += 360
            adj.append(a)
        d = 0 if prev is None else sum(abs(a - p) for a, p in zip(adj, prev))
        if best is None or d < best_d:
            best, best_d = adj, d
    return best


def smooth_fcurves(arm):
    ad = arm.animation_data
    if not ad or not ad.action:
        return
    action = ad.action
    if hasattr(action, 'fcurves'):
        curve_sets = [action.fcurves]
    else:                                   # Blender 5.x layered actions
        curve_sets = [cb.fcurves
                      for layer in action.layers
                      for strip in layer.strips
                      for cb in strip.channelbags]
    for fcurves in curve_sets:
        for fc in fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = 'BEZIER'
                kp.handle_left_type = 'AUTO_CLAMPED'
                kp.handle_right_type = 'AUTO_CLAMPED'


def build_animation(right, sword, base_hand_q, base_roll, attack):
    right.animation_data_clear()
    solved = solve_all_keys(right, sword, base_hand_q, base_roll, attack)
    anchors = RETIME[attack]
    fore = right.pose.bones['forearm']
    hand = right.pose.bones['hand']
    prev_eul, prev_fq, prev_hq = None, None, None
    for label, af in TIMELINES[attack]:
        frame = remap_frame(af, anchors)
        loc, rot, fq, hq = solved[label]
        rot = unwrap(prev_eul, rot)
        prev_eul = rot
        fq, hq = fq.copy(), hq.copy()
        if prev_fq is not None and prev_fq.dot(fq) < 0:
            fq.negate()
        if prev_hq is not None and prev_hq.dot(hq) < 0:
            hq.negate()
        prev_fq, prev_hq = fq, hq
        right.location = loc
        right.rotation_euler = Euler([math.radians(a) for a in rot], 'XYZ')
        right.keyframe_insert('location', frame=frame)
        right.keyframe_insert('rotation_euler', frame=frame)
        fore.rotation_quaternion = fq
        hand.rotation_quaternion = hq
        fore.keyframe_insert('rotation_quaternion', frame=frame)
        hand.keyframe_insert('rotation_quaternion', frame=frame)
    smooth_fcurves(right)
    scene = bpy.context.scene
    scene.frame_start = 1
    scene.frame_end = remap_frame(TOTAL[attack], anchors)
    scene.render.fps = FPS
    return scene.frame_end


def phase_of(attack, frame, anchors):
    label = ''
    for start, lab in PHASES[attack]:
        if frame >= remap_frame(start, anchors):
            label = lab
    return label


def aim_camera(cam, attack):
    fp_loc = Vector((0.0, -8.2, 4.9))
    fp_aim = Vector((FP_AIM_X[attack], 1.5, 3.35))
    cam.data.lens = FP_LENS[attack]
    cam.location = fp_loc
    cam.rotation_euler = look_at(fp_loc, fp_aim)


def render_samples(attack, total, samples):
    scene = bpy.context.scene
    frames = sorted({max(1, min(total, round(1 + (total - 1) * i /
                                            (samples - 1))))
                     for i in range(samples)})
    manifest = []
    for i, f in enumerate(frames):
        scene.frame_set(f)
        path = OUT_DIR + '\\swm_%s_%02d.png' % (attack, i + 1)
        scene.render.filepath = path
        bpy.ops.render.render(write_still=True)
        manifest.append({'index': i + 1, 'frame': f,
                         'time': round((f - 1) / FPS, 3),
                         'phase': phase_of(attack, f, RETIME[attack])})
        print('rendered', path)
    with open(OUT_DIR + '\\swm_%s_manifest.json' % attack, 'w') as fh:
        json.dump({'name': attack, 'frames': total, 'fps': FPS,
                   'samples': manifest}, fh, indent=1)


def probe_curves(right, sword, attack, total):
    """Numeric arc check (no render): per-frame blade world dir + fist pos.
    Corner-cutting shows as the blade dir leaving the windup->sweep geodesic
    (e.g. an early wrong-side x swing) or the fist chord going flat."""
    scene = bpy.context.scene
    for f in range(1, total + 1):
        scene.frame_set(f)
        deps = bpy.context.evaluated_depsgraph_get()
        b = (sword.evaluated_get(deps).matrix_world.to_3x3() @
             Vector((0, 0, 1))).normalized()
        fist = right.evaluated_get(deps).matrix_world @ FIST_VOID
        print('PROBE %s f%02d blade (%+.2f,%+.2f,%+.2f) fist (%+.2f,%+.2f,%+.2f)'
              % (attack, f, *b, *fist))


def render_full(attack):
    scene = bpy.context.scene
    scene.render.filepath = OUT_DIR + '\\sword_%s_' % attack
    bpy.ops.render.render(animation=True)
    print('rendered full sequence for', attack)


def main():
    argv = sys.argv
    args = argv[argv.index('--') + 1:] if '--' in argv else []
    full = '--full' in args
    probe = '--probe' in args
    samples = 12
    if '--samples' in args:
        samples = int(args[args.index('--samples') + 1])
    names = [a for a in args if not a.startswith('--') and not a.isdigit()]
    names = names or list(ATTACKS)

    right, left, sword, report = build_retargeted_grip()
    cam = setup_world()
    base_hand_q = right.pose.bones['hand'].rotation_quaternion.copy()
    base_roll = report['forearm_roll_deg']

    for attack in names:
        total = build_animation(right, sword, base_hand_q, base_roll, attack)
        print('ATTACK %s  frames %d  (%.2f s)' % (attack, total,
                                                  (total - 1) / FPS))
        if probe:
            probe_curves(right, sword, attack, total)
            continue
        aim_camera(cam, attack)
        render_samples(attack, total, samples)
        if full:
            render_full(attack)


main()
