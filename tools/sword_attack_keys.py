# KEY POSES for the three sword attacks on the wristed rig, gripped with
# KHALED'S retargeted grip (tools/retarget_grip.py). POSE-FIRST deliverable:
# stills only, no interpolation — Khaled approves poses before any motion pass.
#
# Weapon identity: Silverlight is a SIDE SWORD (cut-and-thrust).
#   light    — quick lunge, the validated in-line thrust model:
#              ready -> drive -> strike -> recover. Arm-led sagittal drive,
#              wrist near-neutral small flex (the corrected downrange sign
#              from thrust_keys.py).
#   heavy_lr — committed horizontal cut left->right: windup coiling across
#              the body, sweep THROUGH frame center at chest height,
#              follow-through past the body, brief recover. The mid-sweep
#              key is what gives the arc travel at the pose level.
#   heavy_rl — the same cut right->left (forehand coil on the sword side).
#
# Authoring is WORLD-SPACE (gotcha 28): each key = (fist world position,
# desired blade world dir, forearm-side hint, wrist flex/dev deltas, forearm
# pronation delta). Solved to object loc/euler at build time. The blade-dir
# solve is exact; the forearm hint only resolves the roll about the blade
# (the blade-forearm cone angle is fixed by Khaled's seat + the wrist).
# Pronation deltas ride ON TOP of the grip's +40.66 baseline and stay inside
# the +/-85 rig clamp; wrist deltas compose onto the grip swing and stay
# inside the 2-DOF limits.
#
#   blender --background cgtrader_hand_wristed.blend --python sword_attack_keys.py -- [attack ...]
import bpy, sys, math
from mathutils import Vector, Euler, Matrix, Quaternion

# retargeted-grip builder (which itself execs seat_grip's staging)
SRC = r'\\wsl.localhost\Ubuntu\home\khaled\Kore\tools\retarget_grip.py'
_code = open(SRC).read()
exec(_code[:_code.rfind('def main')])

# (label, fist world pos, blade world dir, forearm-side hint,
#  flex deg, dev deg, pronation delta deg)
ATTACKS = {
    # AMENDMENT 2 (2026-07-21, Khaled): the strike must arrive PRONATED —
    # thumb inboard/LEFT from the player's view (natural right-hand thrust),
    # not thumb-right. PROBED (probe_strike_pronation.py): the forearm-roll
    # channel is a WORLD-POSE NO-OP under this solver — blade + hint pin the
    # assembly, and the forearm axis is invariant under its own roll — so the
    # pronation is authored as the ASSEMBLY SPIN: the forearm-side hint
    # rotated about the blade axis (drive -60 deg, strike -120 deg; the
    # wrist stays at the approved legal flex/dev). Elbow rides up-and-out
    # right — the classic high-line pronated stab.
    # AMENDMENT 3 (2026-07-21, Khaled): in-between keys for spatial guidance +
    # speed control (sparse keys read as teleports). 1b_gather = anticipation
    # pull-back before the launch; 2b_mid = mid-extension on the natural arc
    # (blade still climbing, pronation spin at -90 between drive's -60 and
    # strike's -120).
    'light': [
        ('1_ready',   (2.10, 0.35, 3.30), (0.06, -0.20, 0.98), (0.15, 0.30, 0.94), -14, 0, 0),
        ('1b_gather', (2.42, -0.45, 3.10), (0.16, -0.50, 0.85), (0.20, 0.26, 0.94), -20, 0, 0),
        ('2_drive',   (1.90, 1.70, 3.40), (0.02, 0.62, 0.78),  (-0.224, 0.731, 0.646), -5, 0, 5),
        ('2b_mid',    (1.78, 2.25, 3.32), (0.12, 0.94, 0.318), (-0.462, 0.879, -0.119), -2, -5, 8),
        ('3_strike',  (1.65, 2.70, 3.15), (0.18, 0.95, -0.25), (-0.442, 0.208, -0.857), 0, -10, 10),
        ('4_recover', (2.00, 1.10, 3.30), (0.05, 0.42, 0.90),  (0.05, 0.65, 0.75),  -9, 0, 0),
    ],
    # AMENDMENT 3 in-betweens (probed via animate_sword_attacks --probe):
    #   1b_coil — with only ready->windup keyed, the origin-centered rotation
    #     swings the offset fist on a huge detour (heavy_rl fist reached
    #     y=-2.3, BEHIND the camera plane). Pins the coil path in front of
    #     the chest on the natural up-and-across arc.
    #   2b_arc — mid-cut spatial guide between windup and sweep: fist pinned
    #     forward on the arc (kills the backswing bulge at sweep start),
    #     blade on the geodesic but tipped DOWN so the tip stays readable
    #     crossing frame center instead of vanishing into foreshortening.
    'heavy_lr': [
        ('1_ready',   (1.95, 0.45, 3.35), (0.05, 0.30, 0.95),  (0.40, 0.30, 0.85),  -8,  0,   0),
        ('1b_coil',   (0.70, 0.70, 3.85), (-0.54, 0.23, 0.80), (0.03, 0.43, 0.81),  -10, -4, -17),
        ('2_windup',  (-0.55, 0.85, 4.15), (-0.93, 0.08, 0.35), (-0.35, 0.55, 0.76), -12, -8, -35),
        ('2b_arc',    (-0.10, 1.80, 3.75), (-0.38, 0.86, -0.25), (-0.08, 0.65, 0.75), -6, -1, -22),
        ('3_sweep',   (0.45, 2.05, 3.30), (0.55, 0.80, -0.22), (0.20, 0.70, 0.70),   0,  6, -10),
        ('4_through', (2.75, 1.15, 3.10), (0.86, 0.48, -0.18), (0.75, 0.30, 0.60),   8,  8,  25),
        ('5_recover', (2.05, 0.50, 3.30), (0.18, 0.28, 0.94),  (0.40, 0.30, 0.86),  -6,  0,   0),
    ],
    'heavy_rl': [
        ('1_ready',   (1.95, 0.45, 3.35), (0.05, 0.30, 0.95),  (0.40, 0.30, 0.85),  -8,  0,   0),
        ('1b_coil',   (2.65, 0.75, 3.70), (0.55, 0.23, 0.80),  (0.45, 0.30, 0.83),  -10,  4,  17),
        ('2_windup',  (3.30, 0.80, 3.90), (0.90, 0.10, 0.42),  (0.50, 0.30, 0.81),  -12,  8,  35),
        ('2b_arc',    (2.15, 1.80, 3.65), (0.35, 0.88, -0.25), (0.30, 0.53, 0.73),  -6,  1,  22),
        ('3_sweep',   (0.90, 2.10, 3.30), (-0.55, 0.80, -0.20), (0.10, 0.75, 0.65),   0, -6,  10),
        ('4_through', (-1.35, 1.20, 3.10), (-0.85, 0.49, -0.19), (-0.55, 0.45, 0.70),  8, -8, -25),
        ('5_recover', (1.90, 0.55, 3.30), (0.10, 0.30, 0.95),  (0.35, 0.30, 0.89),  -6,  0,   0),
    ],
}
# FP camera aim x-offset per attack (thrust lives in the right lane; the
# cuts sweep through frame center)
FP_AIM_X = {'light': 1.9, 'heavy_lr': 0.8, 'heavy_rl': 0.8}
FP_LENS = {'light': 40, 'heavy_lr': 30, 'heavy_rl': 30}


def set_wrist(right, base_hand_q, flex, dev, roll_delta, base_roll):
    fore = right.pose.bones['forearm']
    hand = right.pose.bones['hand']
    fore.rotation_mode = hand.rotation_mode = 'QUATERNION'
    fore.rotation_quaternion = Quaternion((0, 1, 0),
                                          math.radians(base_roll + roll_delta))
    hand.rotation_quaternion = (base_hand_q @
                                Euler((math.radians(flex), 0,
                                       math.radians(dev)), 'XYZ').to_quaternion())
    bpy.context.view_layer.update()


def probe_obj_dirs(right, sword):
    """Blade dir + fist void in OBJECT-LOCAL (armature) space, current wrist."""
    deps = bpy.context.evaluated_depsgraph_get()
    Msw = sword.evaluated_get(deps).matrix_world
    M3 = right.matrix_world.to_3x3()
    b_world = (Msw.to_3x3() @ Vector((0, 0, 1))).normalized()
    b_obj = (M3.inverted() @ b_world).normalized()
    return b_obj


def solve_key(right, sword, base_hand_q, base_roll, key):
    label, fist_w, d_blade, d_hint, flex, dev, roll_d = key
    set_wrist(right, base_hand_q, flex, dev, roll_d, base_roll)
    b_obj = probe_obj_dirs(right, sword)
    S = Matrix.Diagonal((-HAND_SCALE, HAND_SCALE, HAND_SCALE))
    s1 = (S @ b_obj).normalized()
    a_obj = Vector((0, 0.045, 0.999))                 # forearm rest axis
    s2 = (S @ a_obj) - (S @ a_obj).dot(s1) * s1
    s2.normalize()
    s3 = s1.cross(s2)
    t1 = Vector(d_blade).normalized()
    t2 = Vector(d_hint) - Vector(d_hint).dot(t1) * t1
    t2.normalize()
    t3 = t1.cross(t2)

    def frame(a, b, c):
        m = Matrix.Identity(3)
        for i in range(3):
            m[i][0], m[i][1], m[i][2] = a[i], b[i], c[i]
        return m
    R = frame(t1, t2, t3) @ frame(s1, s2, s3).inverted()
    right.rotation_euler = R.to_euler('XYZ')
    right.location = Vector(fist_w) - R @ S @ FIST_VOID
    bpy.context.view_layer.update()
    # honesty probe: where did the blade & arm actually land
    b_land = (right.matrix_world.to_3x3() @ b_obj).normalized()
    arm_land = (right.matrix_world.to_3x3() @ a_obj).normalized()
    print('KEY %-10s blade_err %.2fdeg  arm dir (%.2f,%.2f,%.2f)  '
          'blade-arm angle %.1fdeg' % (
              label, math.degrees(b_land.angle(Vector(d_blade).normalized())),
              *arm_land, math.degrees(b_land.angle(arm_land))))


def render(cam, name, loc, aim, lens):
    cam.data.lens = lens
    cam.location = Vector(loc)
    cam.rotation_euler = look_at(Vector(loc), Vector(aim))
    bpy.context.scene.render.filepath = OUT_DIR + '\\sk_%s.png' % name
    bpy.ops.render.render(write_still=True)
    print('rendered', name)


def main():
    argv = sys.argv
    args = argv[argv.index('--') + 1:] if '--' in argv else []
    names = args or list(ATTACKS)

    right, left, sword, report = build_retargeted_grip()
    cam = setup_world()
    base_hand_q = right.pose.bones['hand'].rotation_quaternion.copy()
    base_roll = report['forearm_roll_deg']

    # baseline probe: blade vs forearm cone angle with Khaled's seat
    b0 = probe_obj_dirs(right, sword)
    print('BASELINE blade dir (obj) (%.3f,%.3f,%.3f)  off forearm axis %.1fdeg'
          % (*b0, math.degrees(b0.angle(Vector((0, 0.045, 0.999))))))

    for attack in names:
        keys = ATTACKS[attack]
        mid = sum((Vector(k[1]) for k in keys), Vector()) / len(keys)
        fp_loc = Vector((0.0, -8.2, 4.9))
        fp_aim = Vector((FP_AIM_X[attack], 1.5, 3.35))
        sd_loc = mid + Vector((11.5, 0.4, 0.9))
        sd_aim = mid + Vector((0, 0.2, 0.1))
        left_mesh = bpy.data.objects[LEFT_MESH]
        for key in keys:
            solve_key(right, sword, base_hand_q, base_roll, key)
            render(cam, '%s_%s_fp' % (attack, key[0]), fp_loc, fp_aim,
                   FP_LENS[attack])
            # side views: hide the parked left hand (it floats mid-frame from
            # this vantage and clutters the pose read); FP keeps it
            left_mesh.hide_render = True
            render(cam, '%s_%s_side' % (attack, key[0]), sd_loc, sd_aim, 28)
            left_mesh.hide_render = False


main()
