# PROBE (amendment 2): which forearm-roll delta lands the light-lunge strike
# with the thumb facing screen-LEFT (pronated right-hand thrust, Khaled's
# correction)? Sweeps candidate roll deltas on the 3_strike key, prints the
# world thumb direction (screen-left = -X from the FP camera), renders FP
# stills for the eyeball check (gotcha 26: never trust chirality reasoning).
#
#   blender --background cgtrader_hand_wristed.blend --python probe_strike_pronation.py --
import bpy, sys, math
from mathutils import Vector

SRC = r'\\wsl.localhost\Ubuntu\home\khaled\Kore\tools\sword_attack_keys.py'
_code = open(SRC).read()
exec(_code[:_code.rfind('def main')])


def thumb_probe(right):
    bpy.context.view_layer.update()
    deps = bpy.context.evaluated_depsgraph_get()
    ev = right.evaluated_get(deps)
    M = right.matrix_world
    base = M @ Vector(ev.pose.bones['Bone.001'].head)
    tip = M @ Vector(ev.pose.bones['Bone.003'].tail)
    d = (tip - base).normalized()
    return d, base


right, left, sword, report = build_retargeted_grip()
cam = setup_world()
base_hand_q = right.pose.bones['hand'].rotation_quaternion.copy()
base_roll = report['forearm_roll_deg']

label, fist_w, d_blade, d_hint, flex, dev, _ = ATTACKS['light'][2]  # 3_strike
fp_loc = Vector((0.0, -8.2, 4.9))
fp_aim = Vector((FP_AIM_X['light'], 1.5, 3.35))

# FINDING (first sweep): roll_d is a WORLD-POSE NO-OP under this solver —
# blade + forearm-hint are both pinned, and the forearm axis is invariant
# under rotation about itself, so the assembly spin about the blade is fully
# determined by (d_blade, d_hint). Thumb dir was identical at every roll_d.
# The real knob: rotate the HINT about the blade axis (spins fist + elbow
# together), plus wrist flex/dev (shifts the forearm-in-hand azimuth, i.e.
# thumb-vs-elbow). Sweep both.
from mathutils import Matrix, Quaternion

b_hat = Vector(d_blade).normalized()
for theta in (0, 60, 90, 120, 150, -60, -90, -120, -150):
    Rt = Quaternion(b_hat, math.radians(theta))
    hint = tuple(Rt @ Vector(d_hint))
    key = (label, fist_w, d_blade, hint, flex, dev, 0)
    solve_key(right, sword, base_hand_q, base_roll, key)
    d, base = thumb_probe(right)
    print('THETA %+4d  thumb dir (%+.2f,%+.2f,%+.2f)  hint (%+.2f,%+.2f,%+.2f)'
          % (theta, *d, *hint))
    render(cam, 'probe_th_%s' % str(theta).replace('-', 'm'),
           fp_loc, fp_aim, FP_LENS['light'])

# wrist contribution at the best-looking thetas
for theta, fx, dv in ((-75, 30, -30), (-90, 30, -30), (-105, 30, -30),
                      (-90, 45, -35), (-105, 45, -35), (-120, 20, -20)):
    Rt = Quaternion(b_hat, math.radians(theta))
    hint = tuple(Rt @ Vector(d_hint))
    key = (label, fist_w, d_blade, hint, fx, dv, 0)
    solve_key(right, sword, base_hand_q, base_roll, key)
    d, base = thumb_probe(right)
    print('THETA %+4d flex %+3d dev %+3d  thumb dir (%+.2f,%+.2f,%+.2f)'
          % (theta, fx, dv, *d))
    render(cam, 'probe_th_%s_f%s_d%s' % (str(theta).replace('-', 'm'),
                                         str(fx).replace('-', 'm'),
                                         str(dv).replace('-', 'm')),
           fp_loc, fp_aim, FP_LENS['light'])
