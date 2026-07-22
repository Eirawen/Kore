"""
RAILGUN — the electric spell line's introductory cast. Finger gun. Coin flick.

    "The premise of a 'level 1 electricity spell' is strange. If you're shocked
     by magical electricity, that's going to be rough as shit. So it's going to
     be Misaka's railgun." — Khaled, 2026-07-22

Design (see codex/casting-animation-design.md addendum):
  ELECTRICITY = AIM. Air is order, water is flow, fire is will, earth is labor;
  lightning is PRECISION. Asymmetric cooperation: the LEFT hand is logistics
  (flips the coin), the RIGHT hand is the barrel (finger gun tracking the arc).
  THE INVERSION: every other cast trembles during its hold — the railgun hold
  is DEAD STILL (sniper breath, coin hangtime). The tremble comes AFTER the
  shot: the buzz-out, residual current ringing in the hand. No forward fling —
  a railgun doesn't throw, it WITHSTANDS: wrist-extension recoil (first real
  use of the wristed rig's 'hand' bone in a cast).

Run headless (Windows Blender, from WSL):
  "/mnt/c/Program Files/Blender Foundation/Blender 5.1/blender.exe" --background \
    "\\\\wsl.localhost\\Ubuntu/home/khaled/Kore/cgtrader_hand_wristed.blend" \
    --python "\\\\wsl.localhost\\Ubuntu/home/khaled/Kore/tools/animate_railgun.py" \
    -- railgun_strike [--test|--full]

Staging + helpers lifted from tools/animate_casts.py (the proven FP frame).
Outputs cast_railgun_strike_NN.png + manifest to C:\tmp — montage via
  python3 tools/montage_casts.py railgun_strike
"""
import bpy
import sys
import math
import json
from mathutils import Vector, Euler, Quaternion

# ───────────────────── staging (verbatim from animate_casts.py) ─────────────

OUT_DIR = r'C:\tmp'
FPS = 60

CHAINS = {
    'thumb':  ['Bone.001', 'Bone.002', 'Bone.003'],
    'index':  ['Bone.004', 'Bone.017', 'Bone.018', 'Bone.019'],
    'middle': ['Bone.005', 'Bone.014', 'Bone.015', 'Bone.016'],
    'ring':   ['Bone.006', 'Bone.011', 'Bone.012', 'Bone.013'],
    'pinky':  ['Bone.007', 'Bone.008', 'Bone.009', 'Bone.010'],
}
METACARPAL_FRACTION = 0.15

POSES = {
    'idle':  {'f': [20, 30, 15],  'thumb': [15, 20, 10]},
    'open':  {'f': [4, 8, 4],     'thumb': [10, 15, 8]},
    'support_curl': {'f': [55, 60, 40], 'thumb': [30, 35, 20]},
    # RAILGUN shapes:
    # finger_gun — index a straight barrel, middle/ring/pinky curled to the
    # palm (fist-grade), thumb cocked UP like a hammer (low curl, no adduction
    # so it stands proud of the curled fingers).
    'finger_gun': {'index': [-6, -4, -2], 'middle': [88, 95, 68],
                   'ring': [90, 96, 70], 'pinky': [86, 88, 62],
                   'thumb': [4, 6, 3]},
    # coin_cock — loose curl, thumb tucked HARD under the index (spring
    # loaded, coin resting on the nail). thumb_rooty pulls it across the palm.
    'coin_cock': {'f': [55, 60, 40], 'thumb': [58, 48, 25], 'thumb_rooty': 22},
    # coin_flick — same curl, thumb SNAPPED straight (the launch).
    'coin_flick': {'f': [55, 60, 40], 'thumb': [-14, -8, 0]},
}
POSES['support_curl']['thumb_rooty'] = 14   # tuck the thumb horn across

# Gun-hand roll about the aim axis. The euler-guess approach sprawled the
# arm sideways (test f49) — the gun keys now use COMPUTED aim rotations:
# to_track_quat('Z','Y') points the fingers down the aim vector, then a
# post-roll about that vector sets which way the thumb faces. GUN_ROLL is
# picked empirically via --rolls (renders the aim frame at -90/0/+90).
GUN_ROLL = 90.0   # probed -90/0/+90: +90 = thumb-up knife profile, index barrel reads

HAND_SCALE = 3.118
CAM_LOC, CAM_AIM, CAM_LENS = Vector((0.0, -8.2, 4.6)), Vector((0.0, 0.0, 3.3)), 36.0
RES_X, RES_Y = 960, 720
MATTE_COLOR, MATTE_ROUGH = (0.62, 0.55, 0.50, 1.0), 0.75
COIN_COLOR, COIN_ROUGH = (0.55, 0.38, 0.16, 1.0), 0.45   # worn brass
WORLD_COLOR = (0.12, 0.13, 0.16, 1.0)

KEEP = {'Armature.001', 'Armature.003', 'Sphere.001', 'Sphere.002'}
RIGHT_ARM, RIGHT_MESH = 'Armature.001', 'Sphere.001'
LEFT_ARM,  LEFT_MESH  = 'Armature.003', 'Sphere.002'

R_REST_LOC, R_REST_ROT = (2.05, 0.0, -0.7), (14, 9, 172)
L_REST_LOC, L_REST_ROT = (-2.05, 0.0, -0.7), (14, -9, -172)


def look_at_rotation(loc, target):
    return (target - loc).to_track_quat('-Z', 'Y').to_euler()


def strip_scene():
    for obj in list(bpy.data.objects):
        if obj.name not in KEEP:
            bpy.data.objects.remove(obj, do_unlink=True)
    for _ in range(3):
        bpy.ops.outliner.orphans_purge(do_recursive=True)


def ensure_parented(mesh, arm):
    if mesh.parent != arm:
        mw = mesh.matrix_world.copy()
        mesh.parent = arm
        mesh.matrix_parent_inverse = arm.matrix_world.inverted()
        mesh.matrix_world = mw


def apply_matte(objs):
    mat = bpy.data.materials.new('FP_Matte')
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get('Principled BSDF')
    bsdf.inputs['Base Color'].default_value = MATTE_COLOR
    bsdf.inputs['Roughness'].default_value = MATTE_ROUGH
    for obj in objs:
        obj.data.materials.clear()
        obj.data.materials.append(mat)


def flip_chirality(rot_deg):
    return (rot_deg[0], -rot_deg[1], -rot_deg[2])


def stage_hands():
    right, left = bpy.data.objects[RIGHT_ARM], bpy.data.objects[LEFT_ARM]
    ensure_parented(bpy.data.objects[RIGHT_MESH], right)
    ensure_parented(bpy.data.objects[LEFT_MESH], left)
    for obj in (right, left):
        obj.rotation_mode = 'XYZ'
    right.location = R_REST_LOC
    right.scale = (-HAND_SCALE, HAND_SCALE, HAND_SCALE)
    right.rotation_euler = Euler(
        [math.radians(a) for a in flip_chirality(R_REST_ROT)], 'XYZ')
    left.location = L_REST_LOC
    left.scale = (HAND_SCALE,) * 3
    left.rotation_euler = Euler(
        [math.radians(a) for a in flip_chirality(L_REST_ROT)], 'XYZ')

    bpy.context.view_layer.update()
    for mesh_name in (RIGHT_MESH, LEFT_MESH):
        m = bpy.data.objects[mesh_name]
        if m.matrix_world.determinant() < 0:
            import bmesh
            bm = bmesh.new()
            bm.from_mesh(m.data)
            for f in bm.faces:
                f.normal_flip()
            bm.to_mesh(m.data)
            bm.free()
            m.data.update()


def make_coin():
    """The ammunition. A worn brass coin — in this economy, you shoot money."""
    bpy.ops.mesh.primitive_cylinder_add(radius=0.20, depth=0.045)
    coin = bpy.context.active_object
    coin.name = 'Railgun_Coin'
    mat = bpy.data.materials.new('Coin_Brass')
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get('Principled BSDF')
    bsdf.inputs['Base Color'].default_value = COIN_COLOR
    bsdf.inputs['Roughness'].default_value = COIN_ROUGH
    bsdf.inputs['Metallic'].default_value = 0.9
    coin.data.materials.append(mat)
    return coin


def setup_camera_lights_world():
    scene = bpy.context.scene
    cam_data = bpy.data.cameras.new('FP_Camera')
    cam_data.lens = CAM_LENS
    cam = bpy.data.objects.new('FP_Camera', cam_data)
    cam.location = CAM_LOC
    cam.rotation_euler = look_at_rotation(CAM_LOC, CAM_AIM)
    scene.collection.objects.link(cam)
    scene.camera = cam

    def add_sun(name, loc, energy, color=(1, 1, 1)):
        data = bpy.data.lights.new(name, 'SUN')
        data.energy, data.color = energy, color
        data.angle = math.radians(6)
        obj = bpy.data.objects.new(name, data)
        obj.location = loc
        obj.rotation_euler = look_at_rotation(Vector(loc), Vector((0, 0, 2.5)))
        scene.collection.objects.link(obj)

    add_sun('FP_Key',  (-6, -8, 10), 2.0, (1.0, 0.97, 0.92))
    add_sun('FP_Fill', (7, -6, 2),   0.8, (0.85, 0.90, 1.0))

    world = bpy.data.worlds.new('FP_World')
    world.use_nodes = True
    bg = world.node_tree.nodes.get('Background')
    bg.inputs['Color'].default_value = WORLD_COLOR
    bg.inputs['Strength'].default_value = 1.0
    scene.world = world

    try:
        scene.render.engine = 'BLENDER_EEVEE'
    except TypeError:
        scene.render.engine = 'BLENDER_EEVEE_NEXT'
    scene.render.resolution_x, scene.render.resolution_y = RES_X, RES_Y
    scene.render.image_settings.file_format = 'PNG'
    scene.render.fps = FPS


def clear_pose(arm):
    for pb in arm.pose.bones:
        pb.rotation_mode = 'XYZ'
        pb.rotation_euler = (0.0, 0.0, 0.0)
        pb.location = (0.0, 0.0, 0.0)
        pb.scale = (1.0, 1.0, 1.0)


# ───────────────────── keyframing helpers ─────────────────────

def key_obj(arm, frame, loc, rot_deg):
    arm.location = loc
    arm.rotation_euler = Euler(
        [math.radians(a) for a in flip_chirality(rot_deg)], 'XYZ')
    arm.keyframe_insert('location', frame=frame)
    arm.keyframe_insert('rotation_euler', frame=frame)


def aim_euler(aim_vec, roll_deg):
    """Applied-space euler pointing hand-local +Z (fingers) down aim_vec,
    rolled roll_deg about the aim axis. Bypasses the chirality flip —
    these are computed directly in the applied frame."""
    d = Vector(aim_vec).normalized()
    q = d.to_track_quat('Z', 'Y')
    q = Quaternion(d, math.radians(roll_deg)) @ q
    return q.to_euler('XYZ')


def key_obj_aim(arm, frame, loc, aim_vec, roll_deg):
    arm.location = loc
    arm.rotation_euler = aim_euler(aim_vec, roll_deg)
    arm.keyframe_insert('location', frame=frame)
    arm.keyframe_insert('rotation_euler', frame=frame)


def key_pose(arm, frame, pose_name):
    pose = POSES[pose_name]
    for finger, chain in CHAINS.items():
        angles = pose.get(finger, pose.get('f'))
        if finger == 'thumb':
            arm.pose.bones[chain[0]].rotation_euler.y = math.radians(
                pose.get('thumb_rooty', 0.0))
            phalanges = chain
        else:
            meta = arm.pose.bones[chain[0]]
            meta.rotation_euler.x = math.radians(angles[0] * METACARPAL_FRACTION)
            meta.keyframe_insert('rotation_euler', frame=frame)
            phalanges = chain[1:]
        for bone_name, deg in zip(phalanges, angles):
            pb = arm.pose.bones[bone_name]
            pb.rotation_euler.x = math.radians(deg)
            pb.keyframe_insert('rotation_euler', frame=frame)


def key_wrist(arm, frame, deg):
    """Wrist flexion/extension on the wristed rig's 'hand' bone.
    Negative = extension (knuckles snap back/up) = railgun recoil."""
    pb = arm.pose.bones.get('hand')
    if pb is None:
        return
    pb.rotation_euler.x = math.radians(deg)
    pb.keyframe_insert('rotation_euler', frame=frame)


def smooth_fcurves(obj):
    ad = obj.animation_data
    if not ad or not ad.action:
        return
    action = ad.action
    if hasattr(action, 'fcurves'):
        curve_sets = [action.fcurves]
    else:
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


def clear_anim(arm):
    arm.animation_data_clear()
    clear_pose(arm)


# ───────────────────── micro-life (buzz-out tremble) ─────────────────────

def _noise(a, b):
    v = math.sin(a * 12.9898 + b * 78.233) * 43758.5453
    return (v - math.floor(v)) * 2.0 - 1.0


def key_tremble(arm, f0, f1, pose_name, amp):
    pose = POSES[pose_name]
    f, j = f0 + 4, 0
    while f < f1 - 2:
        for fi, (finger, chain) in enumerate(CHAINS.items()):
            angles = pose.get(finger, pose.get('f'))
            if finger == 'thumb':
                arm.pose.bones[chain[0]].rotation_euler.y = math.radians(
                    pose.get('thumb_rooty', 0.0))
                phalanges = chain
            else:
                meta = arm.pose.bones[chain[0]]
                meta.rotation_euler.x = math.radians(
                    angles[0] * METACARPAL_FRACTION)
                meta.keyframe_insert('rotation_euler', frame=f)
                phalanges = chain[1:]
            for bi, (bone_name, deg) in enumerate(zip(phalanges, angles)):
                d = deg + amp * _noise(fi * 3.7 + bi * 1.3, j * 2.1)
                pb = arm.pose.bones[bone_name]
                pb.rotation_euler.x = math.radians(d)
                pb.keyframe_insert('rotation_euler', frame=f)
        j += 1
        f += 7 + int(round(2.0 * _noise(1.7, j * 5.3)))


# ───────────────────── retime ─────────────────────

def remap_frame(f, anchors):
    if f <= anchors[0][0]:
        return max(1, anchors[0][1] + (f - anchors[0][0]))
    for (o0, n0), (o1, n1) in zip(anchors, anchors[1:]):
        if f <= o1:
            t = (f - o0) / (o1 - o0)
            return int(round(n0 + t * (n1 - n0)))
    o0, n0 = anchors[-1]
    return int(round(n0 + (f - o0)))


# ───────────────────── RAILGUN ─────────────────────
# Authored 64 f. Rhythm: draw → FLICK → aim (DEAD-STILL hold = coin hangtime)
# → FIRE (1 f) → recoil snap (wrist extension) → long buzz-out settle.
# The coin arcs left-thumb → apex → falls across the muzzle line; the beam
# fires it at the fall. Coin scale-0 at fire (it IS the projectile now).

ANIMS = {}

ANIMS['railgun_strike'] = {
    'frames': 64,
    # gather 1.4x, hold 16f -> 30f (real coin hangtime ~0.5s), fire->recoil
    # snap UNstretched, settle long for the buzz-out.
    'retime': [(1, 1), (24, 34), (40, 64), (43, 70), (64, 96)],
    'right': [
        (1,  (2.05, 0.0, -0.7),  (14, 9, 172),        'idle'),
        (8,  (2.25, -0.3, -1.0), (22, 9, 172),        'idle'),        # dip
        (16, (1.75, -0.1, -0.5), ('aim', (0.6, 0.55, 0.12)), 'finger_gun'),  # swinging onto line
        (24, (1.15, -0.2, -0.35), ('aim', (0.06, 0.95, 0.30)), 'finger_gun'),  # ON AIM
        (40, (1.15, -0.2, -0.35), ('aim', (0.06, 0.95, 0.30)), 'finger_gun'),  # DEAD-STILL hold
        (41, (1.15, -0.2, -0.35), ('aim', (0.06, 0.95, 0.30)), 'finger_gun'),  # FIRE
        (43, (1.28, -0.75, 0.1), ('aim', (0.06, 0.70, 0.70)), 'finger_gun'),   # recoil: muzzle kicks UP
        (48, (1.20, -0.45, -0.15), ('aim', (0.06, 0.88, 0.45)), 'finger_gun'), # recover
        (64, (1.16, -0.28, -0.30), ('aim', (0.06, 0.93, 0.34)), 'finger_gun'), # settle near aim
    ],
    'left': [
        (1,  (-2.05, 0.0, -0.7),  (14, -9, -172), 'idle'),
        (8,  (-2.25, -0.3, -1.0), (22, -9, -172), 'idle'),        # dip
        (16, (-1.35, 0.25, 0.9),  (30, -6, -168), 'coin_cock'),   # coin presented, thumb loaded
        (20, (-1.35, 0.28, 0.95), (36, -6, -166), 'coin_flick'),  # FLICK (thumb snap)
        (26, (-2.30, 0.2, -1.8),  (26, -9, -172), 'support_curl'),# eases away, sinking
        (40, (-2.55, 0.3, -3.0),  (34, -9, -172), 'support_curl'),# knuckle crest at frame edge
        (64, (-2.50, 0.3, -2.9),  (32, -9, -172), 'support_curl'),
    ],
    # wrist recoil keys (right hand only): (frame, degrees on 'hand' bone X)
    'wrist_right': [(24, 0), (41, 0), (43, -32), (48, -10), (64, 0)],
    # the coin: (frame, loc, scale, spinY_rad). One parabola up-and-downrange:
    # flick → apex → falls across the muzzle line just as the beam fires.
    'coin': [
        (14, (-0.92, 0.05, 1.15), 0.0, 0.0),          # pop-in hidden
        (16, (-0.92, 0.05, 1.18), 1.0, 0.0),          # on the thumb
        (20, (-0.86, 0.14, 1.35), 1.0, 1.2),          # leaving the flick
        (32, (0.40, 2.60, 3.90), 1.0, 7.5),           # apex, downrange, spinning
        (40, (1.45, 4.60, 1.95), 1.0, 12.6),          # falling across the muzzle line
        (41, (1.48, 4.75, 1.80), 0.0, 12.6),          # FIRED (it's the beam now)
    ],
    'phases': [(1, 'rest'), (4, 'draw'), (17, 'flick'), (24, 'aim — dead still'),
               (41, 'FIRE'), (43, 'recoil'), (49, 'buzz-out')],
}

# the buzz-out: tremble AFTER the shot (unique to railgun; holds stay clean)
TREMBLES = {
    'railgun_strike': [('right', 46, 62, 'finger_gun', 2.4)],
}

TEST_FRAMES = {
    'railgun_strike': [32, 43],   # mid-hold (aim + coin apex), recoil peak
}


def _apply_retime():
    for name, spec in ANIMS.items():
        anchors = spec.get('retime')
        if not anchors:
            continue
        for side in ('right', 'left'):
            spec[side] = [(remap_frame(fr, anchors), loc, rot, pose)
                          for (fr, loc, rot, pose) in spec[side]]
        spec['phases'] = [(remap_frame(fr, anchors), lab)
                          for fr, lab in spec['phases']]
        spec['wrist_right'] = [(remap_frame(fr, anchors), d)
                               for fr, d in spec.get('wrist_right', [])]
        spec['coin'] = [(remap_frame(fr, anchors), loc, s, spin)
                        for fr, loc, s, spin in spec.get('coin', [])]
        spec['frames'] = remap_frame(spec['frames'], anchors)
        if name in TEST_FRAMES:
            TEST_FRAMES[name] = [remap_frame(fr, anchors)
                                 for fr in TEST_FRAMES[name]]
        if name in TREMBLES:
            TREMBLES[name] = [(side, remap_frame(f0, anchors),
                               remap_frame(f1, anchors), pose, amp)
                              for side, f0, f1, pose, amp in TREMBLES[name]]


_apply_retime()


# ───────────────────── build + render ─────────────────────

COIN = None


def build_animation(name):
    global COIN
    spec = ANIMS[name]
    for arm_name, side in ((RIGHT_ARM, 'right'), (LEFT_ARM, 'left')):
        arm = bpy.data.objects[arm_name]
        clear_anim(arm)
        for frame, loc, rot, pose in spec[side]:
            if isinstance(rot[0], str) and rot[0] == 'aim':
                key_obj_aim(arm, frame, loc, rot[1], GUN_ROLL)
            else:
                key_obj(arm, frame, loc, rot)
            if pose:
                key_pose(arm, frame, pose)
        if side == 'right':
            for frame, deg in spec.get('wrist_right', []):
                key_wrist(arm, frame, deg)
        for tside, f0, f1, tpose, amp in TREMBLES.get(name, []):
            if tside == side:
                key_tremble(arm, f0, f1, tpose, amp)
        smooth_fcurves(arm)
    if spec.get('coin'):
        if COIN is None:
            COIN = make_coin()
        COIN.animation_data_clear()
        for frame, loc, s, spin in spec['coin']:
            COIN.location = loc
            COIN.scale = (s, s, s)
            COIN.rotation_euler = (math.radians(80), spin, 0.0)
            COIN.keyframe_insert('location', frame=frame)
            COIN.keyframe_insert('scale', frame=frame)
            COIN.keyframe_insert('rotation_euler', frame=frame)
        smooth_fcurves(COIN)
    scene = bpy.context.scene
    scene.frame_start, scene.frame_end = 1, spec['frames']


def phase_of(name, frame):
    label = ''
    for start, lab in ANIMS[name]['phases']:
        if frame >= start:
            label = lab
    return label


def render_animation(name, samples=12):
    build_animation(name)
    spec = ANIMS[name]
    n = spec['frames']
    frames = sorted({max(1, min(n, round(1 + (n - 1) * i / (samples - 1))))
                     for i in range(samples)})
    scene = bpy.context.scene
    manifest = []
    for i, f in enumerate(frames):
        scene.frame_set(f)
        path = OUT_DIR + '\\cast_%s_%02d.png' % (name, i + 1)
        scene.render.filepath = path
        bpy.ops.render.render(write_still=True)
        manifest.append({'index': i + 1, 'frame': f,
                         'time': round((f - 1) / FPS, 3),
                         'phase': phase_of(name, f)})
        print('rendered', path)
    with open(OUT_DIR + '\\cast_%s_manifest.json' % name, 'w') as fh:
        json.dump({'name': name, 'frames': n, 'fps': FPS,
                   'samples': manifest}, fh, indent=1)


def render_test(name):
    build_animation(name)
    scene = bpy.context.scene
    for f in TEST_FRAMES[name]:
        scene.frame_set(f)
        path = OUT_DIR + '\\test_%s_f%02d.png' % (name, f)
        scene.render.filepath = path
        bpy.ops.render.render(write_still=True)
        print('rendered', path)


def render_full(name):
    build_animation(name)
    scene = bpy.context.scene
    scene.render.filepath = OUT_DIR + '\\%s_' % name
    bpy.ops.render.render(animation=True)
    print('rendered full sequence for', name)


def render_rolls(name):
    """Empirical GUN_ROLL probe: the aim frame at three rolls."""
    global GUN_ROLL
    scene = bpy.context.scene
    aim_frame = TEST_FRAMES[name][0]
    for roll in (-90.0, 0.0, 90.0):
        GUN_ROLL = roll
        build_animation(name)
        scene.frame_set(aim_frame)
        path = OUT_DIR + '\\test_roll_%s.png' % str(int(roll)).replace('-', 'm')
        scene.render.filepath = path
        bpy.ops.render.render(write_still=True)
        print('rendered', path)


def main():
    argv = sys.argv
    args = argv[argv.index('--') + 1:] if '--' in argv else []
    test = '--test' in args
    full = '--full' in args
    rolls = '--rolls' in args
    args = [a for a in args if not a.startswith('--')]
    names = list(ANIMS) if (not args or args == ['all']) else args

    strip_scene()
    stage_hands()
    apply_matte([bpy.data.objects[RIGHT_MESH], bpy.data.objects[LEFT_MESH]])
    setup_camera_lights_world()
    for name in names:
        if rolls:
            render_rolls(name)
        elif test:
            render_test(name)
        else:
            render_animation(name)
            if full:
                render_full(name)


main()
