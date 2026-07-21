"""
Keyframed first-person spell-cast animations for the cgtrader two-hand asset.

Run headless (Windows Blender, from WSL):
  "/mnt/c/Program Files/Blender Foundation/Blender 5.1/blender.exe" --background \
    "\\\\wsl.localhost\\Ubuntu/home/khaled/Kore/cgtrader_hand_wristed.blend" \
    --python "\\\\wsl.localhost\\Ubuntu/home/khaled/Kore/tools/animate_casts.py" \
    -- air_strike            # or water_strike / fire_strike / earth_strike / all

PORTED TO THE WRISTED RIG (2026-07-21): the canonical target is now
cgtrader_hand_wristed.blend (root 'Bone' split into forearm->hand, 2-DOF
wrist limits). The casts only reference finger bones (Bone.001-019) and
object transforms; 'hand'/'forearm' stay at rest, so deformation parity
with the canonical rig holds by construction (verified by pixel diff:
8/8 test stills mean diff <0.007/255). Still runs unchanged against the
pre-wrist cgtrader_hand.blend if ever needed.

Staging (camera, lights, mirror, matte, hand local axes) is lifted verbatim from
tools/render_hands_fp.py — that script settled the first-person frame. This one
authors MOTION: object-transform keyframes for gross arm movement (no elbow, the
forearm rides the wrist root) + pose-bone X-curl keyframes for hand shape.

Hand local axes (both hands, after the left's scale.x=-1 mirror):
  fingers +Z, palm -Y (toward camera at identity), forearm -Z,
  thumb inboard. Euler rotations are world XYZ (Rz @ Ry @ Rx).

TRUE FIRST PERSON: the camera must see the BACKS of the hands the whole time
(the player is behind their own hands), so every gather/hold pose lives on the
yaw-flipped branch (Z near +-180), same branch the release keys always used.
Thumbs land OUTBOARD there - correct for a vertical forearm seen from behind.
Useful orientations (right hand; left mirrors by negating Y/Z euler + X loc):
  (  0, 0, 172) knuckles to camera, fingers up, palm downrange (rest family)
  (  0, 0, 225) knife angled: palm inward+downrange, camera sees back-outboard
                quarter (seal / clasp - NOT 270: exactly edge-on reads palm-ish)
  (  0, 0, 180) palm-out downrange, fingers up       (release family)
  (-108,0,  10) cup: palm up tilted AWAY, fingers to the horizon (fire cup)
  (-180,0,  -8) fingers down, knuckles to camera     (earth slam)
Branch changes (gather Z~172 -> action Z~0/-180) are bridged with guide keys as
deliberate forearm supination/pronation rolls - that is what a wrist really does
(boxing chamber rolls palm-up; a scoop into a cup supinates ~160 deg).

Renders 12 evenly spaced frames per cast to C:\tmp\cast_<name>_NN.png plus a
manifest JSON (frame/time/phase per sample) for the montage script.
Flags after the cast names:
  --test  two sanity stills only (gather-hold + fling) -> C:\tmp\test_<name>_fNN.png
  --full  additionally render EVERY frame -> C:\tmp\<name>_0001.png... for
          ffmpeg: -framerate 60 -i <name>_%04d.png -> real-time MP4
"""
import bpy
import sys
import math
import json
from mathutils import Vector, Euler

# ───────────────────── staging (proven values from render_hands_fp.py) ─────

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
    'cup':   {'f': [35, 45, 30],  'thumb': [20, 25, 15]},
    'fist':  {'f': [80, 85, 60],  'thumb': [40, 50, 30]},
    # animation-specific shapes
    'blade': {'f': [8, 10, 6],    'thumb': [25, 30, 15]},   # flat knife hand
    'open':  {'f': [4, 8, 4],     'thumb': [10, 15, 8]},    # presenting palm
    'fling': {'f': [-12, -8, -2], 'thumb': [-12, -5, 0]},   # splayed release
    'knife_seal': {'f': [4, 6, 4], 'thumb': [55, 35, 15]},  # flat hand, thumb TUCKED
}

HAND_SCALE = 3.118
CAM_LOC, CAM_AIM, CAM_LENS = Vector((0.0, -8.2, 4.6)), Vector((0.0, 0.0, 3.3)), 36.0
RES_X, RES_Y = 960, 720
MATTE_COLOR, MATTE_ROUGH = (0.62, 0.55, 0.50, 1.0), 0.75
WORLD_COLOR = (0.12, 0.13, 0.16, 1.0)

KEEP = {'Armature.001', 'Armature.003', 'Sphere.001', 'Sphere.002'}
RIGHT_ARM, RIGHT_MESH = 'Armature.001', 'Sphere.001'
LEFT_ARM,  LEFT_MESH  = 'Armature.003', 'Sphere.002'

# rest transforms (staging values, wrists dropped a touch for headroom).
# Yaw-flipped from the render_hands_fp.py staging: knuckles to camera.
R_REST_LOC, R_REST_ROT = (2.05, 0.0, -0.7), (14, 9, 172)
L_REST_LOC, L_REST_ROT = (-2.05, 0.0, -0.7), (14, -9, -172)

# Measured rig geometry (probed at runtime): the armature OBJECT ORIGIN sits at
# the forearm's lower stub. Along the hand's local +Z: wrist joint ≈ origin+3.1,
# curled-fist knuckles ≈ origin+4.0, middle fingertip ≈ origin+6.0. All loc
# values below are ORIGIN positions and account for that offset.


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


# CHIRALITY FIX (2026-07-17, verified by render + probe): the authored key
# data below was written for un-mirrored-right / mirrored-left, which put each
# thumb OUTBOARD — wrong chirality per side (Khaled caught it). The correct
# first-person view of the backs of your own hands has each thumb INBOARD.
# The fix is an in-place chirality flip applied uniformly at APPLICATION time:
# keep every location, negate the euler Y and Z, toggle the scale.x mirror
# (screen-right = mirrored mesh, screen-left = un-mirrored). Pose-bone X-curls
# are mirror-invariant and pass through untouched.
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


def key_pose(arm, frame, pose_name):
    """Apply a finger pose and keyframe every chain bone's X curl."""
    pose = POSES[pose_name]
    for finger, chain in CHAINS.items():
        angles = pose.get(finger, pose.get('f'))
        if finger == 'thumb':
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


def smooth_fcurves(arm):
    """Bezier + auto-clamped handles everywhere: eases without overshoot."""
    ad = arm.animation_data
    if not ad or not ad.action:
        return
    action = ad.action
    if hasattr(action, 'fcurves'):          # Blender <= 4.x
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


def clear_anim(arm):
    arm.animation_data_clear()
    clear_pose(arm)


# ───────────────────── timing / spacing pass ─────────────────────
# The casts were authored tight (~1.3s), so they read as a keyframe-to-
# keyframe sprint. Real casting has CONTRAST: a deliberate gather, a HELD
# beat on the seal (where the eye reads the orb forming), then a fast SNAP
# release. We get that by retiming — not re-posing. Each cast carries a
# 'retime' list of (old_frame -> new_frame) anchors; remap_frame does a
# monotonic piecewise-linear stretch between them. Spacing is pushed into
# the gather + hold; the pull->fling span is kept short so the release
# stays snappy. Applied once at import so frames/phases/tests stay in sync.
def remap_frame(f, anchors):
    if f <= anchors[0][0]:
        return max(1, anchors[0][1] + (f - anchors[0][0]))
    for (o0, n0), (o1, n1) in zip(anchors, anchors[1:]):
        if f <= o1:
            t = (f - o0) / (o1 - o0)
            return int(round(n0 + t * (n1 - n0)))
    o0, n0 = anchors[-1]
    return int(round(n0 + (f - o0)))


# ───────────────────── the four casts ─────────────────────
# Each entry: total frame count, per-hand key list, phase labels.
# Key tuple: (frame, (loc), (rot_deg), pose_name-or-None)

ANIMS = {}

# AIR STRIKE — order from chaos. 78 f @ 60fps = 1.3 s
# Rest -> dip -> rise into the HORIZONTAL monkey sandwich (right hand below,
# palm up; left hand directly above, palm down; fingers of both pointing
# downrange; a clear vertical gap between the palms where the orb spins) ->
# hold -> bottom hand pronates 90° to palm-out while the top hand peels
# up-and-away -> forward fling -> settle.
# Bottom hand rise + release reuse fire's validated supination/pronation rolls.
ANIMS['air_strike'] = {
    'frames': 78,
    # gather 1.8x slower, seal HELD 0.33s -> 0.8s, release stays a ~0.1s snap
    'retime': [(1, 1), (30, 52), (50, 100), (64, 118), (78, 140)],
    'right': [
        (1,  (2.05, 0.0, -0.7),  (14, 9, 172),    'idle'),
        (10, (2.30, -0.4, -1.0), (22, 9, 172),    'idle'),   # anticipation dip
        (20, (2.30, -0.5, -0.4), (-35, 5, 95),    'cup'),    # supinating scoop guide
        (30, (0.45, -0.6, 0.10), (-76, 0, 12),    'knife_seal'),  # sandwich bottom, palm up, centered
        (50, (0.45, -0.6, 0.15), (-76, 0, 12),    'knife_seal'),  # hold (orb beat)
        (56, (0.70, -0.8, -0.10), (-70, 0, 12),   'knife_seal'),  # slight pull anticipation
        (59, (1.60, 1.2, 0.2),   (-45, 0, -110),  'open'),   # pronating mid-swing
        (64, (1.05, 4.4, -0.5),  (-32, 0, -180),  'fling'),  # release downrange
        (70, (1.15, 3.9, -0.8),  (-27, 0, -180),  'fling'),  # recoil
        (78, (1.20, 3.7, -0.9),  (-26, 0, -180),  'open'),   # settle
    ],
    'left': [
        (1,  (-2.05, 0.0, -0.7), (14, -9, -172),  'idle'),
        (10, (-2.30, -0.4, -1.0), (22, -9, -172), 'idle'),
        (20, (-1.80, -0.5, 1.0), (45, -4, -188),  'knife_seal'),  # pitching forward on the way up
        (30, (-0.55, -0.6, 2.80), (78, 0, -184),  'knife_seal'),  # sandwich top, palm down, gap above
        (50, (-0.55, -0.6, 2.85), (78, 0, -184),  'knife_seal'),  # hold
        (58, (-2.20, -0.6, 3.0), (58, 0, -215),   'knife_seal'),  # peels back-outboard
        (66, (-3.60, -0.3, 2.5), (40, 0, -228),   'open'),   # clear of the throw
        (78, (-3.70, -0.1, 2.3), (35, 0, -224),   'open'),   # settle low-outboard
    ],
    'phases': [(1, 'rest'), (4, 'anticipate'), (14, 'rise'), (30, 'seal'),
               (51, 'peel + rotate'), (59, 'fling'), (66, 'follow-through')],
}

# WATER STRIKE — flow given direction. 78 f = 1.3 s
# Rest -> dip -> wide outward sweep up -> near-prayer clasp with a gap
# (orb forms) -> both palms rotate out -> unified forward fling -> settle.
ANIMS['water_strike'] = {
    'frames': 78,
    # sweep+clasp gather slowed, clasp HELD longer, unified fling stays snappy
    'retime': [(1, 1), (28, 52), (48, 100), (62, 116), (78, 138)],
    'right': [
        (1,  (2.05, 0.0, -0.7),  (14, 9, 172),    'idle'),
        (8,  (2.40, -0.3, -1.1), (22, 9, 172),    'idle'),   # dip
        (18, (3.10, 0.8, 0.2),   (15, 5, 195),    'open'),   # outward arc
        (28, (1.05, 2.6, -1.0),  (8, -10, 225),   'blade'),  # clasp (wrist z~1.6)
        (48, (1.05, 2.6, -0.9),  (8, -10, 225),   'blade'),  # hold, orb
        (55, (1.00, 2.0, -1.3),  (-20, 0, 180),   'open'),   # palms out + pull
        (62, (0.90, 4.8, -0.6),  (-42, 0, 180),   'fling'),  # release
        (68, (0.95, 4.3, -0.9),  (-32, 0, 180),   'fling'),
        (78, (1.10, 3.9, -1.1),  (-28, 0, 180),   'open'),
    ],
    'left': [
        (1,  (-2.05, 0.0, -0.7), (14, -9, -172),  'idle'),
        (8,  (-2.40, -0.3, -1.1), (22, -9, -172), 'idle'),
        (18, (-3.10, 0.8, 0.2),  (15, -5, -195),  'open'),
        (28, (-1.05, 2.6, -1.0), (8, 10, -225),   'blade'),
        (48, (-1.05, 2.6, -0.9), (8, 10, -225),   'blade'),
        (55, (-1.00, 2.0, -1.3), (-20, 0, -180),  'open'),
        (62, (-0.90, 4.8, -0.6), (-42, 0, -180),  'fling'),
        (68, (-0.95, 4.3, -0.9), (-32, 0, -180),  'fling'),
        (78, (-1.10, 3.9, -1.1), (-28, 0, -180),  'open'),
    ],
    'phases': [(1, 'rest'), (4, 'anticipate'), (12, 'sweep up'), (28, 'clasp'),
               (49, 'palms out'), (57, 'fling'), (64, 'follow-through')],
}

# FIRE STRIKE — will made manifest. 54 f = 0.9 s. One hand.
# Rest -> present cupped palm-up, fingers to the horizon -> beat (flicker)
# -> pull back -> palm-out forward fling -> settle. Left hand never wakes.
ANIMS['fire_strike'] = {
    'frames': 54,
    # deliberate present+cup, LONG flicker beat (the will gathering), snap fling
    'retime': [(1, 1), (16, 40), (34, 88), (47, 104), (54, 116)],
    'right': [
        (1,  (2.05, 0.0, -0.7),  (14, 9, 172),   'idle'),
        (6,  (2.20, -0.2, -0.95), (22, 9, 172),  'idle'),    # dip
        (11, (1.80, 0.15, 0.0),  (-45, 5, 90),   'cup'),     # scoop: supinating roll
        (16, (1.40, 0.5, 1.0),   (-108, 0, 10),  'cup'),     # palm up tilted away, cupped
        (34, (1.40, 0.55, 1.05), (-108, 0, 10),  'cup'),     # flicker beat
        (40, (1.70, -0.2, 0.3),  (-94, 0, 10),   'cup'),     # anticipation pull
        (42, (1.35, 1.8, -0.1),  (-45, 0, -110), 'open'),    # pronating mid-swing
        (47, (1.05, 4.4, -0.5),  (-32, 0, -180), 'fling'),   # release
        (51, (1.15, 3.9, -0.8),  (-27, 0, -180), 'fling'),
        (54, (1.20, 3.7, -0.9),  (-26, 0, -180), 'open'),
    ],
    'left': [
        (1,  (-2.05, 0.0, -0.7),  (14, -9, -172), 'idle'),
        (11, (-2.45, 0.3, -1.9),  (28, -9, -172), 'cup'),   # sinks low, loose support curl
        (16, (-2.55, 0.4, -2.2),  (30, -9, -172), 'cup'),   # mostly out of frame
        (40, (-2.55, 0.4, -2.2),  (30, -9, -172), 'cup'),   # stays low through the fling
        (54, (-2.45, 0.3, -1.9),  (28, -9, -172), 'cup'),
    ],
    'phases': [(1, 'rest'), (7, 'present'), (17, 'flicker beat'),
               (35, 'anticipate'), (41, 'fling'), (48, 'follow-through')],
}

# EARTH STRIKE — labor. 66 f = 1.1 s. Fists, asymmetric.
# Clench -> left winds high -> LEFT slams DOWN (kicks the earth up) ->
# right chambers -> RIGHT punches FORWARD (propels it). No palm fling.
ANIMS['earth_strike'] = {
    'frames': 66,
    # slow clench+wind-up, SLAM stays fast, earth hangs kicked-up (held beat),
    # then a snappy forward PUNCH -> settle
    'retime': [(1, 1), (8, 18), (19, 52), (24, 58), (34, 84), (42, 96), (66, 124)],
    'right': [
        (1,  (2.05, 0.0, -0.7),  (14, 9, 172),   'idle'),
        (8,  (2.10, -0.1, -0.75), (16, 9, 172),  'fist'),    # clench
        (24, (2.15, -0.2, -0.55), (18, 9, 172),  'fist'),    # waits, slight lift
        (29, (2.35, -0.85, -0.5), (-15, 0, 91),  'fist'),    # rolling into chamber
        (34, (2.50, -1.5, -0.4), (-48, -12, 10), 'fist'),    # chamber back (palm-up roll)
        (42, (1.20, 2.6, -1.0),  (-58, -4, 6),   'fist'),    # PUNCH forward
        (48, (1.45, 2.0, -1.05), (-50, -6, 7),   'fist'),    # recoil
        (66, (1.70, 1.5, -1.1),  (-42, -7, 8),   'fist'),    # settle
    ],
    'left': [
        (1,  (-2.05, 0.0, -0.7), (14, -9, -172), 'idle'),
        (8,  (-2.10, -0.1, -0.75), (16, -9, -172), 'fist'),  # clench
        (12, (-2.00, 0.25, 0.3), (0, 0, -120),   'fist'),    # wind-up roll begins
        (16, (-1.90, 0.6, 1.4),  (-10, 3, -60),  'fist'),    # wind-up rise, still rolling
        (19, (-1.95, 0.4, 1.9),  (-40, 7, -8),   'fist'),    # overshoot up, roll done
        (24, (-1.55, 1.7, 4.0),  (-180, 5, -8),  'fist'),    # SLAM down (fist z~-0.3)
        (30, (-1.55, 1.7, 4.15), (-175, 5, -8),  'fist'),    # impact bounce
        (66, (-1.60, 1.6, 4.20), (-174, 5, -8),  'fist'),    # holds low
    ],
    'phases': [(1, 'rest'), (4, 'clench'), (12, 'wind-up'), (20, 'slam down'),
               (27, 'chamber'), (38, 'punch fwd'), (45, 'follow-through')],
}


# ───────────────────── build + render ─────────────────────

def build_animation(name):
    spec = ANIMS[name]
    for arm_name, side in ((RIGHT_ARM, 'right'), (LEFT_ARM, 'left')):
        arm = bpy.data.objects[arm_name]
        clear_anim(arm)
        for frame, loc, rot, pose in spec[side]:
            key_obj(arm, frame, loc, rot)
            if pose:
                key_pose(arm, frame, pose)
        smooth_fcurves(arm)
    scene = bpy.context.scene
    scene.frame_start, scene.frame_end = 1, spec['frames']


def phase_of(name, frame):
    label = ''
    for start, lab in ANIMS[name]['phases']:
        if frame >= start:
            label = lab
    return label


# gather-hold + fling sanity-check frames per cast (for --test)
TEST_FRAMES = {
    'air_strike':   [40, 64],
    'water_strike': [38, 62],
    'fire_strike':  [25, 47],
    'earth_strike': [20, 42],
}


def _apply_retime():
    """Bake each cast's 'retime' anchors into its keys, total, phases, and
    test frames — once, at import — so every downstream reader sees the new
    timing consistently."""
    for name, spec in ANIMS.items():
        anchors = spec.get('retime')
        if not anchors:
            continue
        for side in ('right', 'left'):
            spec[side] = [(remap_frame(fr, anchors), loc, rot, pose)
                          for (fr, loc, rot, pose) in spec[side]]
        spec['phases'] = [(remap_frame(fr, anchors), lab)
                          for fr, lab in spec['phases']]
        spec['frames'] = remap_frame(spec['frames'], anchors)
        if name in TEST_FRAMES:
            TEST_FRAMES[name] = [remap_frame(fr, anchors)
                                 for fr in TEST_FRAMES[name]]


_apply_retime()


def render_animation(name, samples=12):
    """12 evenly spaced stills + manifest (for the montage grids)."""
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
    """Two sanity stills: one gather-hold frame, one fling frame."""
    build_animation(name)
    scene = bpy.context.scene
    for f in TEST_FRAMES[name]:
        scene.frame_set(f)
        path = OUT_DIR + '\\test_%s_f%02d.png' % (name, f)
        scene.render.filepath = path
        bpy.ops.render.render(write_still=True)
        print('rendered', path)


def render_full(name):
    """Every frame at authored fps to <name>_%04d.png (ffmpeg -> mp4)."""
    build_animation(name)
    scene = bpy.context.scene
    scene.render.filepath = OUT_DIR + '\\%s_' % name
    bpy.ops.render.render(animation=True)
    print('rendered full sequence for', name)


def main():
    argv = sys.argv
    args = argv[argv.index('--') + 1:] if '--' in argv else []
    test = '--test' in args
    full = '--full' in args
    args = [a for a in args if not a.startswith('--')]
    names = list(ANIMS) if (not args or args == ['all']) else args

    strip_scene()
    stage_hands()
    apply_matte([bpy.data.objects[RIGHT_MESH], bpy.data.objects[LEFT_MESH]])
    setup_camera_lights_world()
    for name in names:
        if test:
            render_test(name)
        else:
            render_animation(name)
            if full:
                render_full(name)


main()
