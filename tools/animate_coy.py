"""
COY — the succubus's first emote. First full-humanoid character animation
in Crescent.

Hand to chin, slight crouch, weight on the left leg, head tilted into the
hand. Acting beats: anticipation-away -> move (wrist leads) -> overshoot ->
settle (head lands AFTER the hand: overlapping action) -> living hold
(breath, sway — the hold is the breath).

Rig: Mixamo-style, 24 bones, armature scale 0.01 (cm), faces -Y.
All rotations are authored as ARMATURE-SPACE axis+angle and converted to
bone-local quaternions via matrix_local (gotcha #8 — never guess local
axes). Hips location offsets likewise converted.

Run:
  "/mnt/c/Program Files/Blender Foundation/Blender 5.1/blender.exe" \
    --background "\\\\wsl.localhost\\Ubuntu/home/khaled/Kore/succubus_rigged.blend" \
    --python "\\\\wsl.localhost\\Ubuntu/home/khaled/Kore/tools/animate_coy.py" -- [--full]

Outputs C:\tmp\coy_NN.png + manifest (grid), --full renders every frame.
"""
import bpy
import sys
import math
import json
from mathutils import Vector, Quaternion, Euler

OUT = r'C:\tmp'
FPS = 60
FRAMES = 132

ARM = 'Armature'

# ───────────────────────── staging ─────────────────────────

def stage():
    scene = bpy.context.scene
    # hide the leftover icosphere (it sits at the origin, inside her)
    ico = bpy.data.objects.get('Icosphere')
    if ico:
        ico.hide_render = True
        ico.hide_viewport = True

    # camera: keep his position family, re-aim at her upper body, closer
    cam = bpy.data.objects.get('Camera')
    cam.location = Vector((2.6, -3.4, 1.85))
    target = Vector((0.0, -0.1, 1.05))
    cam.rotation_euler = (target - cam.location).to_track_quat('-Z', 'Y').to_euler()
    cam.data.lens = 55
    scene.camera = cam

    # lighting: keep his light, add a cool fill + a dim world
    def sun(name, loc, energy, color):
        data = bpy.data.lights.new(name, 'SUN')
        data.energy, data.color = energy, color
        data.angle = math.radians(8)
        o = bpy.data.objects.new(name, data)
        o.location = loc
        o.rotation_euler = (Vector((0, 0, 1.2)) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
        scene.collection.objects.link(o)
    sun('CoyKey', (-3, -5, 4), 2.2, (1.0, 0.95, 0.9))
    sun('CoyFill', (4, -3, 1.5), 0.7, (0.8, 0.85, 1.0))

    world = bpy.data.worlds.new('CoyWorld')
    world.use_nodes = True
    bg = world.node_tree.nodes.get('Background')
    bg.inputs['Color'].default_value = (0.10, 0.09, 0.12, 1.0)
    bg.inputs['Strength'].default_value = 1.0
    scene.world = world

    try:
        scene.render.engine = 'BLENDER_EEVEE'
    except TypeError:
        scene.render.engine = 'BLENDER_EEVEE_NEXT'
    scene.render.resolution_x, scene.render.resolution_y = 960, 720
    scene.render.image_settings.file_format = 'PNG'
    scene.render.fps = FPS
    scene.frame_start, scene.frame_end = 1, FRAMES


# ─────────────────── armature-space pose machinery ───────────────────

def local_quat(pb, axis_arm, deg):
    """Armature-space axis+angle -> this bone's local quaternion delta."""
    m = pb.bone.matrix_local.to_3x3().inverted()
    axis_local = (m @ Vector(axis_arm)).normalized()
    return Quaternion(axis_local, math.radians(deg))

def compose(pb, rots):
    """Compose multiple (axis, deg) armature-space rotations into one
    local quaternion (applied in listed order)."""
    q = Quaternion()
    for axis, deg in rots:
        q = q @ local_quat(pb, axis, deg)
    return q

def local_loc(pb, offset_arm):
    """Armature-space offset (cm) -> bone-local location vector."""
    m = pb.bone.matrix_local.to_3x3().inverted()
    return m @ Vector(offset_arm)


X, Y, Z = (1, 0, 0), (0, 1, 0), (0, 0, 1)
# She faces -Y. So: pitch-forward = rotate about +X? (test empirically);
# lateral lean = about Y; twist = about Z.

# ─────────────────── THE POSES (armature-space) ───────────────────
# Each pose: bone -> list of (axis, degrees). 'HIPS_LOC' -> (x, y, z) cm.
# Signs verified by render iteration — this is the authored first pass.

REST = {}

# anticipation: a breath of looking away (head RIGHT = away from camera,
# body a hair taller) — so the coy tilt toward camera lands as an arrival
ANTICIPATE = {
    'Head':      [(Z, -9), (X, -3)],
    'neck':      [(Z, -4)],
    'Spine':     [(X, -2)],
    'HIPS_LOC':  (0, 0, 1.0),
}

# the landed coy pose — MIRRORED: left hand to chin, weight on RIGHT leg,
# head tilts LEFT (+X, toward the camera at +X,-Y)
COY = {
    # slight curtsy-crouch: hips settle down and a touch back, shifted
    # onto her RIGHT leg (-X); pelvis rolls gently, spine counters
    'HIPS_LOC':  (-2.2, 1.5, -6.0),
    'Hips':      [(Y, 2.5)],
    # weight leg (right): soft
    'RightUpLeg': [(X, -5)],
    'RightLeg':  [(X, 9)],
    'RightFoot': [(X, -4)],
    # free leg (left): softer knee, eased in (shy)
    'LeftUpLeg': [(X, -8), (Z, 5)],
    'LeftLeg':   [(X, 14)],
    'LeftFoot':  [(X, -6)],
    # spine: counter the pelvis roll (stay upright), shy hunch forward,
    # gentle curve toward the hand side (+X)
    'Spine02':   [(X, 3), (Y, -1.5)],
    'Spine01':   [(X, 4), (Y, -1.5)],
    'Spine':     [(X, 5), (Y, 2)],
    # shoulders: the shrug
    'LeftShoulder':  [(Y, 10)],
    'RightShoulder': [(Y, -7)],
    # LEFT arm: hand to chin — SOLVED numerically (coordinate descent,
    # wrist landed 6.5mm from the chin target). Armature-space params;
    # the render is the anatomical judge.
    'LeftArm':      [(X, -110), (Y, 118), (Z, 42)],
    'LeftForeArm':  [(X, -180), (Z, 128)],
    'LeftHand':     [(X, -25), (Z, 10)],
    # right arm: soft at her side
    'RightArm':     [(X, -4), (Z, -5)],
    'RightForeArm': [(X, -10)],
    # head: tilts down and INTO the hand side (+X = toward camera)
    'neck':      [(X, 6), (Y, 6)],
    'Head':      [(X, 9), (Y, 10), (Z, 7)],
}

OVER = {}
for b, rots in COY.items():
    if b == 'HIPS_LOC':
        OVER[b] = (COY[b][0] * 1.12, COY[b][1], COY[b][2] * 1.14)
    else:
        OVER[b] = [(ax, d * 1.15) for ax, d in rots]

# ─────────────────── keyframing ───────────────────

def apply_pose(arm, frame, pose, blend=1.0):
    for pb in arm.pose.bones:
        pb.rotation_mode = 'QUATERNION'
    for bone, spec in pose.items():
        if bone == 'HIPS_LOC':
            pb = arm.pose.bones['Hips']
            off = Vector(spec) * blend
            pb.location = local_loc(pb, off)
            pb.keyframe_insert('location', frame=frame)
            continue
        pb = arm.pose.bones.get(bone)
        if pb is None:
            continue
        if isinstance(spec, tuple) and spec and spec[0] == 'local_euler':
            e = spec[1]
            q = Euler([math.radians(v * blend) for v in e], 'XYZ').to_quaternion()
        elif isinstance(spec, tuple) and spec and spec[0] == 'hinge':
            q = Quaternion(Vector(spec[1]).normalized(),
                           math.radians(spec[2] * blend))
        else:
            q = Quaternion()
            for axis, deg in spec:
                q = q @ local_quat(pb, axis, deg * blend)
        pb.rotation_quaternion = q
        pb.keyframe_insert('rotation_quaternion', frame=frame)

def key_rest(arm, frame, bones):
    """Key listed bones at rest (identity) on this frame."""
    for bone in bones:
        if bone == 'HIPS_LOC':
            pb = arm.pose.bones['Hips']
            pb.location = (0, 0, 0)
            pb.keyframe_insert('location', frame=frame)
            continue
        pb = arm.pose.bones.get(bone)
        if pb is None:
            continue
        pb.rotation_mode = 'QUATERNION'
        pb.rotation_quaternion = Quaternion()
        pb.keyframe_insert('rotation_quaternion', frame=frame)

def smooth(arm):
    ad = arm.animation_data
    if not ad or not ad.action:
        return
    action = ad.action
    curve_sets = ([action.fcurves] if hasattr(action, 'fcurves')
                  else [cb.fcurves for L in action.layers for s in L.strips
                        for cb in s.channelbags])
    for fcurves in curve_sets:
        for fc in fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = 'BEZIER'
                kp.handle_left_type = 'AUTO_CLAMPED'
                kp.handle_right_type = 'AUTO_CLAMPED'


def load_solved_arm():
    import os
    path = '/mnt/c/tmp/coy_arm_solved.json' if os.path.exists('/mnt/c/tmp/coy_arm_solved.json') else None
    if path is None:
        path = r'C:\tmp\coy_arm_solved.json'
        try:
            open(path).close()
        except OSError:
            return
    with open(path) as fh:
        sol = json.load(fh)
    COY['LeftArm'] = ('local_euler', tuple(sol['upper']))
    COY['LeftForeArm'] = ('hinge', tuple(sol['hinge_axis']), sol['elbow_deg'])
    COY['LeftHand'] = ('local_euler', tuple(sol['wrist']))
    OVER['LeftArm'] = ('local_euler', tuple(v * 1.1 for v in sol['upper']))
    OVER['LeftForeArm'] = ('hinge', tuple(sol['hinge_axis']), sol['elbow_deg'] * 1.08)
    OVER['LeftHand'] = ('local_euler', tuple(v * 1.1 for v in sol['wrist']))
    print('loaded solved arm:', sol)


def build():
    arm = bpy.data.objects[ARM]
    load_solved_arm()
    arm.animation_data_clear()          # clear 'Armature|clip0|baselayer'
    for pb in arm.pose.bones:
        pb.rotation_mode = 'QUATERNION'
        pb.rotation_quaternion = Quaternion()
        pb.location = (0, 0, 0)

    all_bones = list(COY.keys()) + ['Head', 'neck']

    # f1: rest
    key_rest(arm, 1, all_bones)
    # f14: anticipation (only its bones move; others hold rest)
    apply_pose(arm, 14, ANTICIPATE)
    # hand bones stay rest through the anticipation
    key_rest(arm, 14, [b for b in COY if b not in ANTICIPATE])
    # f30: mid-move — the body commits (60% of the way), wrist leading:
    # the arm is AHEAD of the torso schedule
    apply_pose(arm, 30, {k: v for k, v in COY.items()
                         if k not in ('Head', 'neck')}, blend=0.6)
    apply_pose(arm, 30, {'RightArm': COY['RightArm'],
                         'RightForeArm': COY['RightForeArm']}, blend=0.85)
    # f44: overshoot (hand past chin, crouch bottoms)
    apply_pose(arm, 44, OVER)
    # f54: settle body; head still traveling
    apply_pose(arm, 54, {k: v for k, v in COY.items()
                         if k not in ('Head', 'neck')})
    # f60: head LANDS last (overlapping action)
    apply_pose(arm, 60, {'Head': COY['Head'], 'neck': COY['neck']})

    # f60-132: LIVING HOLD — breath in the spine, slow sway in the hips,
    # micro-tilt in the head. Deterministic phases, re-keyed sparsely.
    import math as _m
    for i, f in enumerate(range(72, FRAMES + 1, 12)):
        t = (f - 60) / 60.0
        sway = _m.sin(t * _m.pi * 0.8) * 1.2
        breath = _m.sin(t * _m.pi * 1.6) * 0.8
        tilt = _m.sin(t * _m.pi * 0.5 + 0.7) * 1.5
        hold = dict(COY)
        hold = {k: list(v) if isinstance(v, list) else v for k, v in COY.items()}
        hold['Hips'] = COY['Hips'] + [(Y, sway)]
        hold['Spine01'] = COY['Spine01'] + [(X, breath)]
        hold['Spine'] = COY['Spine'] + [(X, breath * 0.7)]
        hold['Head'] = COY['Head'] + [(Y, -tilt), (X, breath * 0.5)]
        apply_pose(arm, f, hold)

    smooth(arm)


PHASES = [(1, 'rest'), (8, 'anticipate (look away)'), (18, 'the move'),
          (40, 'overshoot'), (50, 'settle'), (60, 'coy — living hold')]

def phase_of(f):
    lab = ''
    for start, l in PHASES:
        if f >= start:
            lab = l
    return lab


def render_grid(samples=12):
    scene = bpy.context.scene
    frames = sorted({max(1, min(FRAMES, round(1 + (FRAMES - 1) * i / (samples - 1))))
                     for i in range(samples)})
    manifest = []
    for i, f in enumerate(frames):
        scene.frame_set(f)
        path = OUT + '\\coy_%02d.png' % (i + 1)
        scene.render.filepath = path
        bpy.ops.render.render(write_still=True)
        manifest.append({'index': i + 1, 'frame': f,
                         'time': round((f - 1) / FPS, 3), 'phase': phase_of(f)})
        print('rendered', path)
    with open(OUT + '\\coy_manifest.json', 'w') as fh:
        json.dump({'name': 'coy', 'frames': FRAMES, 'fps': FPS,
                   'samples': manifest}, fh, indent=1)


def render_full():
    scene = bpy.context.scene
    scene.render.filepath = OUT + '\\coy_'
    bpy.ops.render.render(animation=True)


def probe_reach():
    """Numeric hand-to-chin check: apply COY variants, print distances.
    Chin ~ head bone head + forward offset (headfront gives the face dir)."""
    arm = bpy.data.objects[ARM]
    arm.animation_data_clear()
    for pb in arm.pose.bones:
        pb.rotation_mode = 'QUATERNION'

    variants = {
        'authored': (COY['LeftArm'], COY['LeftForeArm']),
        'higher':   ([(X, -62), (Z, 40), (Y, 20)], [(X, -105), (Z, 32)]),
        'tighter':  ([(X, -55), (Z, 48), (Y, 26)], [(X, -112), (Z, 40)]),
        'inward':   ([(X, -58), (Z, 42), (Y, 30)], [(X, -108), (Z, 48)]),
    }
    for name, (armR, foreR) in variants.items():
        for pb in arm.pose.bones:
            pb.rotation_quaternion = Quaternion()
            pb.location = (0, 0, 0)
        pose = dict(COY)
        pose['LeftArm'] = armR
        pose['LeftForeArm'] = foreR
        apply_pose(arm, 1, pose)
        bpy.context.view_layer.update()
        mw = arm.matrix_world
        # NOTE: this rig's bone TAILS are pathological (FBX surgery
        # artifacts — Hips tail 5m out). HEADS are sane. Measure the
        # WRIST (LeftHand.head); contact target ~0.10m wrist-to-chin.
        hand = mw @ arm.pose.bones['LeftHand'].head
        headb = arm.pose.bones['Head']
        headpos = mw @ headb.head
        frontb = arm.pose.bones['headfront']
        front = ((mw @ frontb.head) - headpos).normalized()
        chin = headpos + front * 0.075 + Vector((0, 0, -0.035))
        print('PROBE %s dist=%.3f hand=(%.2f,%.2f,%.2f) chin=(%.2f,%.2f,%.2f)'
              % (name, (hand - chin).length, *hand, *chin))


def solve_arm():
    """Coordinate-descent IK: hill-climb (LeftArm XYZ, LeftForeArm XZ)
    to put the WRIST at the chin target, elbow hanging naturally."""
    arm = bpy.data.objects[ARM]
    arm.animation_data_clear()
    for pb in arm.pose.bones:
        pb.rotation_mode = 'QUATERNION'
    mw = arm.matrix_world

    def evaluate(p):
        for pbb in arm.pose.bones:
            pbb.rotation_quaternion = Quaternion()
            pbb.location = (0, 0, 0)
        pose = dict(COY)
        pose['LeftArm'] = [(X, p[0]), (Y, p[1]), (Z, p[2])]
        pose['LeftForeArm'] = [(X, p[3]), (Z, p[4])]
        apply_pose(arm, 1, pose)
        bpy.context.view_layer.update()
        headb = arm.pose.bones['Head']
        headpos = mw @ headb.head
        front = ((mw @ arm.pose.bones['headfront'].head) - headpos).normalized()
        target = headpos + front * 0.05 + Vector((0.015, 0, -0.055))
        wrist = mw @ arm.pose.bones['LeftHand'].head
        elbow = mw @ arm.pose.bones['LeftForeArm'].head
        shoulder = mw @ arm.pose.bones['LeftArm'].head
        cost = (wrist - target).length
        if elbow.z > shoulder.z:          # chicken-wing: elbow above shoulder
            cost += (elbow.z - shoulder.z) * 2.0
        if elbow.y > shoulder.y + 0.02:   # elbow swung behind the back
            cost += (elbow.y - shoulder.y) * 2.0
        return cost, wrist, target

    # Human ROM clamps — impossible poses must be UNSEARCHABLE (same
    # philosophy as the FP wrist constraints). Elbow flexion caps ~135.
    LIMITS = [(-120, 10), (-20, 120), (-10, 80), (-135, 0), (-10, 90)]
    p = [-58.0, 30.0, 42.0, -108.0, 48.0]
    step = 16.0
    best, _, _ = evaluate(p)
    for round_ in range(12):
        improved = False
        for i in range(len(p)):
            for delta in (step, -step):
                q = list(p)
                q[i] = max(LIMITS[i][0], min(LIMITS[i][1], q[i] + delta))
                if q[i] == p[i]:
                    continue
                c, _, _ = evaluate(q)
                if c < best - 1e-5:
                    best, p, improved = c, q, True
        if not improved:
            step *= 0.5
            if step < 0.5:
                break
    c, wrist, target = evaluate(p)
    print('SOLVED cost=%.4f params=[%.1f, %.1f, %.1f, %.1f, %.1f]' % (c, *p))
    print('SOLVED wrist=(%.3f,%.3f,%.3f) target=(%.3f,%.3f,%.3f)'
          % (*wrist, *target))


# Elbow hinge LEARNED from the Meshy walk data (single-axis 0.98):
ELBOW_HINGE_L = (-0.73, 0.09, 0.68)

def solve_arm2():
    """Pose-LOCAL coordinate descent: upper arm free (local euler),
    elbow constrained to its LEARNED hinge, wrist gentle. The elbow is
    anatomically correct BY CONSTRUCTION now."""
    arm = bpy.data.objects[ARM]
    arm.animation_data_clear()
    for pb in arm.pose.bones:
        pb.rotation_mode = 'QUATERNION'
    mw = arm.matrix_world

    def evaluate(p):
        for pbb in arm.pose.bones:
            pbb.rotation_quaternion = Quaternion()
            pbb.location = (0, 0, 0)
        pose = dict(COY)
        pose['LeftArm'] = ('local_euler', (p[0], p[1], p[2]))
        pose['LeftForeArm'] = ('hinge', ELBOW_HINGE_L, p[3])
        pose['LeftHand'] = ('local_euler', (p[4], 0, p[5]))
        apply_pose(arm, 1, pose)
        bpy.context.view_layer.update()
        headb = arm.pose.bones['Head']
        headpos = mw @ headb.head
        front = ((mw @ arm.pose.bones['headfront'].head) - headpos).normalized()
        target = headpos + front * 0.05 + Vector((0.015, 0, -0.055))
        wrist = mw @ arm.pose.bones['LeftHand'].head
        elbow = mw @ arm.pose.bones['LeftForeArm'].head
        shoulder = mw @ arm.pose.bones['LeftArm'].head
        cost = (wrist - target).length
        if elbow.z > shoulder.z - 0.03:
            cost += (elbow.z - (shoulder.z - 0.03)) * 3.0
        if elbow.y > shoulder.y + 0.02:
            cost += (elbow.y - shoulder.y) * 3.0
        return cost, wrist, target

    LIMITS = [(-90, 90), (-90, 90), (-90, 90), (-135, 135), (-45, 45), (-45, 45)]
    p = [0.0, 0.0, 0.0, 60.0, 0.0, 0.0]
    step = 24.0
    best, _, _ = evaluate(p)
    for round_ in range(14):
        improved = False
        for i in range(len(p)):
            for delta in (step, -step):
                q = list(p)
                q[i] = max(LIMITS[i][0], min(LIMITS[i][1], q[i] + delta))
                if q[i] == p[i]:
                    continue
                c, _, _ = evaluate(q)
                if c < best - 1e-5:
                    best, p, improved = c, q, True
        if not improved:
            step *= 0.5
            if step < 1.0:
                break
    c, wrist, target = evaluate(p)
    print('SOLVED2 cost=%.4f upper=(%.1f,%.1f,%.1f) elbow=%.1f wrist=(%.1f,%.1f)'
          % (c, p[0], p[1], p[2], p[3], p[4], p[5]))
    with open(r'C:\tmp\coy_arm_solved.json', 'w') as fh:
        json.dump({'upper': [p[0], p[1], p[2]],
                   'hinge_axis': list(ELBOW_HINGE_L),
                   'elbow_deg': p[3],
                   'wrist': [p[4], 0, p[5]],
                   'cost': c}, fh)
    print('SOLVED2 written to C:\\tmp\\coy_arm_solved.json')


def main():
    argv = sys.argv
    args = argv[argv.index('--') + 1:] if '--' in argv else []
    if '--solve2' in args:
        solve_arm2()
        return
    if '--solve' in args:
        solve_arm()
        return
    if '--probe' in args:
        probe_reach()
        return
    stage()
    build()
    render_grid()
    if '--full' in args:
        render_full()

main()
