"""
First-person sword animations — Silverlight parented to the right hand.

Run headless (Windows Blender, from WSL):
  "/mnt/c/Program Files/Blender Foundation/Blender 5.1/blender.exe" --background \
    "\\\\wsl.localhost\\Ubuntu/home/khaled/Kore/cgtrader_hand.blend" \
    --python "\\\\wsl.localhost\\Ubuntu/home/khaled/Kore/tools/animate_sword.py" \
    -- sword_light            # or heavy/thrust/guard/parry/all, --grip

Staging (chirality-fixed 2026-07-17) is shared with tools/animate_casts.py:
authored data keeps the old sign convention; flip_chirality negates euler Y/Z
at application and the RIGHT hand is the mirrored mesh (scale.x = -3.118) so
each thumb lands INBOARD. Hand-local axes (mirrored right): thumb -X,
palm -Y, fingers/knuckles +Z, forearm -Z.

THE SWORD RIG: the cgtrader rig has no elbow — ALL gross motion is armature
OBJECT transforms, pose bones only curl fingers. So the sword is plain
object-parented to the right armature (rigid, BoneAttachment-style) and never
moves relative to the fist. Probed anatomy (tools/probe_sword.py): sword
local +Z = blade (tip at z 0.95), guard z -0.4..-0.7, grip -0.7..-0.9,
pommel -1.0. A fist's rod axis runs along hand-local X and the blade exits
the THUMB side (-X), so the sword gets a plain Ry(-90) — axis-aligned on
purpose: the parent's anisotropic mirror scale (-S, S, S) would SHEAR any
non-axis-aligned child rotation.

WORLD-SPACE KEY AUTHORING (new for the sword set): sword keys are authored as
(frame, fist_world_pos, forearm_dir, blade_dir, pose) — semantic intent — and
solved to origin-loc + authored-euler at build time:
  - forearm_dir f = wrist->knuckles direction (hand local +Z), world space
  - blade_dir b0 = where the blade should point; projected perpendicular to f
    because the hammer grip is rigid (blade is ALWAYS perpendicular to the
    metacarpals — a thrust can never be fully point-in-line on this rig)
  - palm lands on b x f automatically (right hand wrapping the hilt)
  - the armature ORIGIN sits at the forearm stub, fist center ~3.6 world
    units along f: origin = fist - 3.6*f  (the origin gotcha, pre-solved)
Eulers are unwrapped key-to-key (mod-360 + the (x+180, 180-y, z+180)
equivalent triple) so interpolation rolls the wrist instead of flipping.
"""
import bpy
import sys
import math
import json
from mathutils import Vector, Euler, Matrix

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
    'idle':       {'f': [20, 30, 15], 'thumb': [15, 20, 10]},
    # grips: fingers wrap the hilt, thumb locks over. Three tensions.
    'grip':       {'f': [75, 85, 58], 'thumb': [40, 50, 28]},
    'grip_loose': {'f': [55, 65, 40], 'thumb': [28, 35, 18]},
    'grip_tight': {'f': [80, 88, 60], 'thumb': [45, 55, 32]},
}

HAND_SCALE = 3.118
CAM_LOC, CAM_AIM, CAM_LENS = Vector((0.0, -8.2, 4.6)), Vector((0.0, 0.0, 3.3)), 36.0
RES_X, RES_Y = 960, 720
MATTE_COLOR, MATTE_ROUGH = (0.62, 0.55, 0.50, 1.0), 0.75
WORLD_COLOR = (0.12, 0.13, 0.16, 1.0)

KEEP = {'Armature.001', 'Armature.003', 'Sphere.001', 'Sphere.002'}
RIGHT_ARM, RIGHT_MESH = 'Armature.001', 'Sphere.001'
LEFT_ARM,  LEFT_MESH  = 'Armature.003', 'Sphere.002'

FIST_OFFSET = 3.6   # world units origin->fist-center along forearm dir

SWORD_GLB = r'C:\Users\kmessai\Downloads\Silverlight.glb'
SWORD_SCALE = 2.8            # hand-local units; world grip radius ~0.27
# grip center (sword local z=-0.8) must land in the curled-finger VOID.
# Probed (tools/probe_fist_void.py): posed 'grip' knuckles z~1.45 y~-0.10,
# curled mid/distal joints y~-0.32 z~1.3-1.45 -> void center hand-local
# (0, -0.22, 1.37). Blade exits -X, so the sword origin sits 0.73*scale
# further along +X (0.73 not 0.8: seats the fist up under the guard).
SWORD_LOC = (-0.73 * SWORD_SCALE, -0.22, 1.37)
SWORD_ROT = (0, -90, 0)      # sword +Z (blade) -> hand -X (thumb side)


# ───────────────────────── helpers ─────────────────────────

def look_at_rotation(loc, target):
    return (target - loc).to_track_quat('-Z', 'Y').to_euler()


def flip_chirality(rot_deg):
    return (rot_deg[0], -rot_deg[1], -rot_deg[2])


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


def flip_normals_if_mirrored(obj):
    bpy.context.view_layer.update()
    if obj.matrix_world.determinant() < 0:
        import bmesh
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        for f in bm.faces:
            f.normal_flip()
        bm.to_mesh(obj.data)
        bm.free()
        obj.data.update()


def apply_matte(objs):
    mat = bpy.data.materials.new('FP_Matte')
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get('Principled BSDF')
    bsdf.inputs['Base Color'].default_value = MATTE_COLOR
    bsdf.inputs['Roughness'].default_value = MATTE_ROUGH
    for obj in objs:
        obj.data.materials.clear()
        obj.data.materials.append(mat)


R_REST_LOC, R_REST_ROT = (2.05, 0.0, -0.7), (14, 9, 172)
L_REST_LOC, L_REST_ROT = (-2.05, 0.0, -0.7), (14, -9, -172)


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
    for mesh_name in (RIGHT_MESH, LEFT_MESH):
        flip_normals_if_mirrored(bpy.data.objects[mesh_name])


def attach_sword():
    """Import Silverlight and rigid-parent it into the right fist."""
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=SWORD_GLB)
    new = [o for o in bpy.data.objects if o not in before]
    sword = [o for o in new if o.type == 'MESH'][0]
    sword.parent = None
    right = bpy.data.objects[RIGHT_ARM]
    sword.parent = right
    sword.matrix_parent_inverse.identity()
    sword.rotation_mode = 'XYZ'
    sword.location = SWORD_LOC
    sword.rotation_euler = Euler([math.radians(a) for a in SWORD_ROT], 'XYZ')
    sword.scale = (SWORD_SCALE,) * 3
    for o in new:
        if o is not sword and o.type != 'MESH':
            bpy.data.objects.remove(o, do_unlink=True)
    flip_normals_if_mirrored(sword)   # parent mirror flips winding
    return sword


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


def key_obj(arm, frame, loc, rot_deg):
    arm.location = loc
    arm.rotation_euler = Euler(
        [math.radians(a) for a in flip_chirality(rot_deg)], 'XYZ')
    arm.keyframe_insert('location', frame=frame)
    arm.keyframe_insert('rotation_euler', frame=frame)


def key_pose(arm, frame, pose_name):
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
    ad = arm.animation_data
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


def remap_frame(f, anchors):
    if f <= anchors[0][0]:
        return max(1, anchors[0][1] + (f - anchors[0][0]))
    for (o0, n0), (o1, n1) in zip(anchors, anchors[1:]):
        if f <= o1:
            t = (f - o0) / (o1 - o0)
            return int(round(n0 + t * (n1 - n0)))
    o0, n0 = anchors[-1]
    return int(round(n0 + (f - o0)))


# ─────────────── world-space key solver (right hand + sword) ───────────────

def _norm(v):
    v = Vector(v)
    v.normalize()
    return v


def solve_key(fist, fdir, bdir):
    """(fist_world, forearm_dir, blade_dir) -> (origin_loc, authored_euler)."""
    f = _norm(fdir)
    b = Vector(bdir) - Vector(bdir).dot(f) * f
    if b.length < 1e-4:
        raise ValueError('blade_dir parallel to forearm_dir: %s %s'
                         % (fdir, bdir))
    b.normalize()
    c2 = f.cross(b)                       # = -palm
    R = Matrix((( b.x, c2.x, f.x),
                ( b.y, c2.y, f.y),
                ( b.z, c2.z, f.z)))       # columns b, c2, f; det +1
    yp = math.degrees(math.asin(max(-1.0, min(1.0, -R[2][0]))))
    zp = math.degrees(math.atan2(R[1][0], R[0][0]))
    xp = math.degrees(math.atan2(R[2][1], R[2][2]))
    authored = (xp, -yp, -zp)
    origin = tuple(Vector(fist) - FIST_OFFSET * f)
    return origin, authored


def unwrap_eulers(keys):
    """Pick, per key, the euler representation closest to the previous key —
    mod 360 per channel plus the (x+180, 180-y, z+180) equivalent triple —
    so interpolation rolls the wrist instead of doing a 300-degree flip."""
    out = []
    prev = None
    for frame, loc, rot, pose in keys:
        cands = [rot, (rot[0] + 180, 180 - rot[1], rot[2] + 180)]
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
                best, best_d = tuple(adj), d
        out.append((frame, loc, best, pose))
        prev = best
    return out


# ───────────────────── the five sword animations ─────────────────────
# Right-hand keys: (frame, fist_world, forearm_dir, blade_dir, pose).
# All directions world-space; blade_dir gets projected perpendicular to
# forearm_dir (rigid hammer grip). Left hand idles.

READY = ((2.05, 1.3, 0.35), (-0.20, 0.90, 0.32), (-0.12, 0.25, 0.96))

ANIMS = {}

# SWORD LIGHT — loose grip, quick wrist-led diagonal slash, fast recovery.
ANIMS['sword_light'] = {
    'frames': 32,
    # eased cock, micro-hold, FAST slash-through, eased recovery
    'retime': [(1, 1), (8, 20), (12, 36), (17, 44), (22, 54), (32, 72)],
    'right': [
        (1,  *READY, 'grip'),
        (8,  (2.70, 0.7, 1.60), (-0.05, 0.85, 0.50), (0.45, 0.10, 0.90), 'grip_loose'),
        (12, (2.68, 0.7, 1.62), (-0.05, 0.85, 0.50), (0.45, 0.10, 0.90), 'grip_loose'),
        (17, (-0.40, 2.2, -0.30), (-0.45, 0.85, -0.25), (-0.75, 0.30, -0.60), 'grip'),
        (22, (-0.85, 1.9, -0.25), (-0.55, 0.78, -0.30), (-0.70, 0.20, -0.68), 'grip_loose'),
        (32, *READY, 'grip'),
    ],
    'phases': [(1, 'ready'), (3, 'cock'), (12, 'hold'), (14, 'slash'),
               (18, 'follow-through'), (23, 'recover')],
}

# SWORD HEAVY — big overhead wind-up, committed chop, slow heavy recovery.
ANIMS['sword_heavy'] = {
    'frames': 50,
    # slow deliberate wind-up, LONG apex hold (the breath), fast chop,
    # impact dig, ponderous recovery
    'retime': [(1, 1), (16, 36), (26, 74), (30, 82), (34, 90), (50, 128)],
    'right': [
        (1,  *READY, 'grip'),
        (8,  (2.20, 0.9, 1.70), (-0.10, 0.85, 0.53), (0.00, 0.15, 0.99), 'grip_tight'),
        (16, (1.30, 0.4, 3.10), (-0.15, 0.55, 0.82), (0.00, -0.92, 0.40), 'grip_tight'),
        (26, (1.28, 0.38, 3.15), (-0.15, 0.53, 0.83), (0.00, -0.93, 0.38), 'grip_tight'),
        (28, (1.20, 1.3, 2.60), (-0.12, 0.95, 0.28), (0.05, -0.28, 0.96), 'grip_tight'),  # guide: blade sweeping over
        (30, (1.15, 2.80, 0.35), (-0.10, 0.87, -0.48), (0.00, 0.60, -0.80), 'grip_tight'),
        (33, (1.18, 2.65, 0.15), (-0.10, 0.85, -0.52), (0.00, 0.57, -0.82), 'grip_tight'),
        (41, (1.60, 2.0, 0.10), (-0.15, 0.92, -0.36), (-0.05, 0.40, -0.90), 'grip'),
        (50, *READY, 'grip'),
    ],
    'phases': [(1, 'ready'), (4, 'lift'), (11, 'wind-up'), (26, 'apex hold'),
               (28, 'chop'), (32, 'impact'), (37, 'recover')],
}

# SWORD THRUST — blade leads downrange, driven from the shoulder, quick
# retract. The rigid hammer grip cannot go point-in-line, so this is the
# committed saber stab: blade ~35 deg up, fist driven hard forward along it.
ANIMS['sword_thrust'] = {
    'frames': 32,
    # deliberate chamber, gather beat, DRIVE snap, eased retract
    'retime': [(1, 1), (9, 22), (13, 40), (17, 46), (22, 56), (32, 74)],
    'right': [
        (1,  *READY, 'grip'),
        (9,  (2.45, -0.5, 0.15), (-0.18, 0.95, 0.25), (-0.05, 0.30, 0.95), 'grip_tight'),
        (13, (2.50, -0.55, 0.15), (-0.18, 0.95, 0.25), (-0.05, 0.30, 0.95), 'grip_tight'),
        (17, (1.35, 3.7, -0.15), (-0.12, 0.97, 0.10), (0.00, 0.62, 0.78), 'grip_tight'),
        (22, (2.00, 1.0, 0.10), (-0.18, 0.94, 0.20), (0.00, 0.40, 0.90), 'grip'),
        (32, *READY, 'grip'),
    ],
    'phases': [(1, 'ready'), (4, 'chamber'), (13, 'gather'), (15, 'drive'),
               (19, 'retract'), (26, 'ready')],
}

# SWORD GUARD — blade raised across the body, HELD, subtle breathing.
GUARD = ((1.30, 1.6, 0.90), (-0.30, 0.88, 0.35), (-0.45, 0.15, 0.88))
ANIMS['sword_guard'] = {
    'frames': 56,
    'retime': [(1, 1), (10, 20), (56, 88)],
    'right': [
        (1,  *READY, 'grip'),
        (10, *GUARD, 'grip_tight'),
        (22, (1.28, 1.65, 0.95), (-0.30, 0.88, 0.36), (-0.44, 0.16, 0.88), 'grip_tight'),
        (34, (1.33, 1.55, 0.86), (-0.31, 0.88, 0.34), (-0.46, 0.14, 0.87), 'grip_tight'),
        (46, (1.29, 1.62, 0.92), (-0.30, 0.88, 0.35), (-0.45, 0.15, 0.88), 'grip_tight'),
        (56, *GUARD, 'grip_tight'),
    ],
    'phases': [(1, 'ready'), (3, 'raise'), (11, 'guard hold (breathing)')],
}

# SWORD PARRY — THE one. Forte against foible: a small efficient beat. The
# fist snaps inboard-forward so the FORTE (the strong third of the blade,
# right above the guard) crosses the incoming line and meets their FOIBLE;
# the wrist rotates the blade into opposition and turns their steel aside
# laterally. The tip stays UP and threat-forward the whole time — no
# flailing block — and it ends with the point canted at the opponent,
# poised to riposte.
ANIMS['sword_parry'] = {
    'frames': 38,
    # micro-read, SNAP beat, catch-and-turn, settle into the riposte-poise
    'retime': [(1, 1), (7, 16), (11, 24), (14, 31), (24, 48), (38, 72)],
    'right': [
        (1,  (2.20, 1.1, 0.40), (-0.18, 0.91, 0.30), (-0.08, 0.24, 0.97), 'grip'),
        (7,  (2.32, 0.95, 0.45), (-0.16, 0.92, 0.28), (-0.06, 0.26, 0.96), 'grip'),
        (11, (0.80, 1.9, 0.90), (-0.40, 0.85, 0.33), (-0.30, 0.22, 0.93), 'grip_tight'),
        (14, (0.55, 2.1, 1.00), (-0.45, 0.83, 0.33), (-0.42, 0.30, 0.86), 'grip_tight'),
        (24, (1.55, 1.9, 0.30), (-0.20, 0.97, -0.10), (0.00, 0.55, 0.83), 'grip'),
        (38, (1.57, 1.88, 0.28), (-0.20, 0.97, -0.10), (0.00, 0.55, 0.83), 'grip'),
    ],
    'phases': [(1, 'ready'), (3, 'read'), (8, 'beat (forte)'),
               (12, 'turn aside'), (15, 'riposte-poised')],
}


def left_idle(frames):
    mid = max(2, frames // 2)
    return [
        (1,      (-2.05, 0.0, -0.7),   (14, -9, -172),  'idle'),
        (mid,    (-2.10, -0.05, -0.75), (15, -9, -171), 'idle'),
        (frames, (-2.05, 0.0, -0.7),   (14, -9, -172),  'idle'),
    ]


def _bake():
    """Solve world-space right keys to (loc, euler), unwrap, retime."""
    for name, spec in ANIMS.items():
        solved = []
        for frame, fist, fdir, bdir, pose in spec['right']:
            loc, rot = solve_key(fist, fdir, bdir)
            solved.append((frame, loc, rot, pose))
        spec['right'] = unwrap_eulers(solved)
        spec['left'] = left_idle(spec['frames'])
        anchors = spec.get('retime')
        if not anchors:
            continue
        for side in ('right', 'left'):
            spec[side] = [(remap_frame(fr, anchors), loc, rot, pose)
                          for (fr, loc, rot, pose) in spec[side]]
        spec['phases'] = [(remap_frame(fr, anchors), lab)
                          for fr, lab in spec['phases']]
        spec['frames'] = remap_frame(spec['frames'], anchors)


_bake()


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
        path = OUT_DIR + '\\sword_%s_%02d.png' % (name, i + 1)
        scene.render.filepath = path
        bpy.ops.render.render(write_still=True)
        manifest.append({'index': i + 1, 'frame': f,
                         'time': round((f - 1) / FPS, 3),
                         'phase': phase_of(name, f)})
        print('rendered', path)
    with open(OUT_DIR + '\\sword_%s_manifest.json' % name, 'w') as fh:
        json.dump({'name': name, 'frames': n, 'fps': FPS,
                   'samples': manifest}, fh, indent=1)


def render_full(name):
    """Every frame at authored fps to <name>_%04d.png (ffmpeg -> mp4)."""
    build_animation(name)
    scene = bpy.context.scene
    scene.render.filepath = OUT_DIR + '\\%s_' % name
    bpy.ops.render.render(animation=True)
    print('rendered full sequence for', name)


def render_grip_still():
    """Static grip verification: ready stance, wide + close."""
    right = bpy.data.objects[RIGHT_ARM]
    left = bpy.data.objects[LEFT_ARM]
    clear_anim(right)
    clear_anim(left)
    loc, rot = solve_key(*READY)
    key_obj(right, 1, loc, rot)
    key_pose(right, 1, 'grip')
    key_obj(left, 1, (-2.05, 0.0, -0.7), (14, -9, -172))
    key_pose(left, 1, 'idle')
    scene = bpy.context.scene
    scene.frame_set(1)
    scene.render.filepath = OUT_DIR + '\\sword_grip_still.png'
    bpy.ops.render.render(write_still=True)
    print('rendered', scene.render.filepath)
    cam = scene.camera
    fist = Vector(READY[0])
    cam.location = fist + Vector((-1.2, -4.2, 1.4))
    cam.rotation_euler = look_at_rotation(cam.location, fist)
    scene.render.filepath = OUT_DIR + '\\sword_grip_close.png'
    bpy.ops.render.render(write_still=True)
    print('rendered', scene.render.filepath)
    cam.location = CAM_LOC
    cam.rotation_euler = look_at_rotation(CAM_LOC, CAM_AIM)


def main():
    argv = sys.argv
    args = argv[argv.index('--') + 1:] if '--' in argv else []
    grip = '--grip' in args
    full = '--full' in args
    args = [a for a in args if not a.startswith('--')]
    names = list(ANIMS) if (not args or args == ['all']) else args

    strip_scene()
    stage_hands()
    apply_matte([bpy.data.objects[RIGHT_MESH], bpy.data.objects[LEFT_MESH]])
    setup_camera_lights_world()
    attach_sword()
    if grip:
        render_grip_still()
        return
    for name in names:
        if full:
            render_full(name)
        else:
            render_animation(name)


if __name__ == '__main__':
    main()
