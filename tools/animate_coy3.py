"""
COY v6 — solved against a REAL torso, with the pose gate first.

Fixes the two defects the 5-angle pose check exposed:
  1. Arm tunneled through the chest. Root cause was MY constraint: a
     penalty on elbow lateral offset ("coy elbows tuck") rewarded the
     elbow for moving medially — into the ribcage. Replaced with a
     TORSO CLEARANCE PROXY sampled from her actual chest geometry
     (height x angular sector -> max radius, built from torso-weighted
     verts, breasts included because they're chest-weighted). Arm
     sample points must stay outside it + margin. Poses that clip can
     no longer converge.
  2. Flat palm landed over the face (reads as shock/hiding, not coy).
     This rig has NO finger bones — the hand is a paddle — so the only
     coy-legible option is FINGERTIPS grazing the jaw from below, hand
     edge-on. Target is now the fingertip at the measured chin (lowest
     forward head vertex), with the wrist required to sit BELOW it.

Pipeline discipline: renders the 5-angle POSE CHECK by default (cheap
veto gate). Timeline grid needs --grid; full mp4 frames need --full.

Run:
  blender --background --python animate_coy3.py -- [--grid] [--full]
"""
import bpy
import sys
import json
import math
from mathutils import Vector, Quaternion, Euler

GLB = '/home/khaled/Kore/succubus_walk.glb'
OUT = r'C:\tmp'
FPS = 60
FRAMES = 132

argv = sys.argv
ARGS = argv[argv.index('--') + 1:] if '--' in argv else []

# ───────────────────── import + learn her joints ─────────────────────
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=GLB)
scene = bpy.context.scene
scene.render.fps = FPS
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
mesh = next(o for o in bpy.data.objects if o.type == 'MESH')

action = arm.animation_data.action
f0, f1 = (int(v) for v in action.frame_range)

def dominant_axis(bname):
    """The joint's true hinge, learned from her own working animation."""
    pb = arm.pose.bones[bname]
    data, best, ref = [], 0.0, None
    for f in range(f0, f1 + 1):
        scene.frame_set(f)
        q = pb.rotation_quaternion.copy()
        if q.w < 0:
            q = -q
        ang = math.degrees(2 * math.acos(max(-1.0, min(1.0, q.w))))
        ax = Vector((q.x, q.y, q.z))
        if ax.length > 1e-6:
            ax.normalize()
            data.append((ax, ang))
            if ang > best:
                best, ref = ang, ax
    acc = Vector((0, 0, 0))
    for ax, ang in data:
        if ax.dot(ref) < 0:
            ax = -ax
        acc += ax * ang
    acc.normalize()
    return acc, best

ELBOW_AXIS, elbow_max = dominant_axis('LeftForeArm')
print('LEARNED elbow axis %s (%.1f deg in walk)'
      % ([round(v, 2) for v in ELBOW_AXIS], elbow_max))

arm.animation_data_clear()
for pb in arm.pose.bones:
    pb.rotation_mode = 'QUATERNION'
    pb.rotation_quaternion = Quaternion()
    pb.location = (0, 0, 0)
scene.frame_set(1)
bpy.context.view_layer.update()

mw = arm.matrix_world

# ───────────────────── TORSO CLEARANCE PROXY ─────────────────────
# Sampled from rest geometry: torso-weighted verts -> (height along the
# spine axis, angular sector) -> max radial distance. The spine rotates
# only a few degrees in this emote, so the rest profile is valid.

TORSO_GROUPS = {'Spine', 'Spine01', 'Spine02', 'Hips'}
HEAD_GROUPS = {'Head'}
gi_torso = {mesh.vertex_groups[g].index for g in TORSO_GROUPS
            if g in mesh.vertex_groups}
gi_head = {mesh.vertex_groups[g].index for g in HEAD_GROUPS
           if g in mesh.vertex_groups}

spine_lo = mw @ arm.pose.bones['Spine02'].head      # base of torso axis
spine_hi = mw @ arm.pose.bones['neck'].head         # top of torso axis
axis = (spine_hi - spine_lo)
axis_len = axis.length
axis_n = axis.normalized()
# reference frame for angular sectors: forward (-Y-ish) and lateral
fwd = Vector((0, -1, 0)) - axis_n * Vector((0, -1, 0)).dot(axis_n)
fwd.normalize()
lat = axis_n.cross(fwd)

NBIN, NSEC = 12, 12

def torso_coords(p):
    """world point -> (height bin fraction t, sector index, radius)"""
    d = p - spine_lo
    t = d.dot(axis_n) / axis_len
    radial = d - axis_n * (t * axis_len)
    r = radial.length
    ang = math.atan2(radial.dot(lat), radial.dot(fwd))
    sec = int(((ang + math.pi) / (2 * math.pi)) * NSEC) % NSEC
    return t, sec, r

profile = [[0.0] * NSEC for _ in range(NBIN)]
torso_v = 0
for v in mesh.data.vertices:
    w = sum(g.weight for g in v.groups if g.group in gi_torso)
    if w < 0.5:
        continue
    torso_v += 1
    t, sec, r = torso_coords(mesh.matrix_world @ v.co)
    if t < 0 or t >= 1:
        continue
    b = min(NBIN - 1, int(t * NBIN))
    if r > profile[b][sec]:
        profile[b][sec] = r

# fill empty cells from neighbours so lookups never read 0
for b in range(NBIN):
    for s in range(NSEC):
        if profile[b][s] > 0:
            continue
        vals = [profile[bb][ss % NSEC]
                for bb in (b - 1, b, b + 1) for ss in (s - 1, s, s + 1)
                if 0 <= bb < NBIN and profile[bb][ss % NSEC] > 0]
        profile[b][s] = max(vals) if vals else 0.06

maxr = max(max(row) for row in profile)
print('TORSO PROXY %d verts, axis_len=%.3f, max radius=%.3f'
      % (torso_v, axis_len, maxr))

def torso_penetration(p, margin=0.012):
    """How far inside the torso proxy this point is (0 = clear)."""
    t, sec, r = torso_coords(p)
    if t < -0.05 or t > 1.05:
        return 0.0
    b = min(NBIN - 1, max(0, int(t * NBIN)))
    lim = profile[b][sec] + margin
    return max(0.0, lim - r)

# ───────────────────── measured CHIN (lowest forward head vert) ──────
head_pts = []
for v in mesh.data.vertices:
    w = sum(g.weight for g in v.groups if g.group in gi_head)
    if w > 0.5:
        head_pts.append(mesh.matrix_world @ v.co)
if head_pts:
    zs = sorted(p.z for p in head_pts)
    z_cut = zs[int(len(zs) * 0.22)]           # lower fifth of the head
    low = [p for p in head_pts if p.z <= z_cut]
    CHIN = min(low, key=lambda p: p.y)        # most forward of those
else:
    CHIN = mw @ arm.pose.bones['Head'].head
print('CHIN measured at %s' % [round(v, 3) for v in CHIN])

# ───────────────────── pose machinery ─────────────────────

def local_quat(pb, axis_arm, deg):
    m = pb.bone.matrix_local.to_3x3().inverted()
    return Quaternion((m @ Vector(axis_arm)).normalized(), math.radians(deg))

def local_loc(pb, off):
    return pb.bone.matrix_local.to_3x3().inverted() @ Vector(off)

X, Y, Z = (1, 0, 0), (0, 1, 0), (0, 0, 1)

def spec_quat(pb, spec, blend=1.0):
    if isinstance(spec, tuple) and spec and spec[0] == 'axis':
        return Quaternion(Vector(spec[1]).normalized(),
                          math.radians(spec[2] * blend))
    q = Quaternion()
    for ax, deg in spec:
        q = q @ local_quat(pb, ax, deg * blend)
    return q

def set_pose(pose, blend=1.0):
    for bone, spec in pose.items():
        if bone == 'HIPS_LOC':
            pb = arm.pose.bones['Hips']
            pb.location = local_loc(pb, Vector(spec) * blend)
            continue
        pb = arm.pose.bones.get(bone)
        if pb is None:
            continue
        pb.rotation_quaternion = spec_quat(pb, spec, blend)
    bpy.context.view_layer.update()

def apply_pose(frame, pose, blend=1.0):
    for bone, spec in pose.items():
        if bone == 'HIPS_LOC':
            pb = arm.pose.bones['Hips']
            pb.location = local_loc(pb, Vector(spec) * blend)
            pb.keyframe_insert('location', frame=frame)
            continue
        pb = arm.pose.bones.get(bone)
        if pb is None:
            continue
        pb.rotation_quaternion = spec_quat(pb, spec, blend)
        pb.keyframe_insert('rotation_quaternion', frame=frame)

def key_rest(frame, bones):
    for bone in bones:
        if bone == 'HIPS_LOC':
            pb = arm.pose.bones['Hips']
            pb.location = (0, 0, 0)
            pb.keyframe_insert('location', frame=frame)
            continue
        pb = arm.pose.bones.get(bone)
        if pb is None:
            continue
        pb.rotation_quaternion = Quaternion()
        pb.keyframe_insert('rotation_quaternion', frame=frame)

# ───────────────── body pose (the part that already read well) ───────
BODY = {
    'HIPS_LOC':  (-2.4, 1.8, -8.0),
    'Hips':      [(Y, 2.5)],
    'RightUpLeg': [(X, -5)],
    'RightLeg':  [(X, 12)],
    'RightFoot': [(X, -4)],
    'LeftUpLeg': [(X, -8), (Z, 5)],
    'LeftLeg':   [(X, 17)],
    'LeftFoot':  [(X, -6)],
    'Spine02':   [(X, 3), (Y, -1.5)],
    'Spine01':   [(X, 4), (Y, -1.5)],
    'Spine':     [(X, 5), (Y, 2)],
    'LeftShoulder':  [(Y, 10)],
    'RightShoulder': [(Y, -7)],
    'RightArm':     [(X, -4), (Z, -5)],
    'RightForeArm': [(X, -10)],
    'neck':      [(X, 6), (Y, 6)],
    'Head':      [(X, 9), (Y, 10), (Z, 7)],
}

# ───────────────── measured hand extent ─────────────────
# Guessing this was the sin. The paddle's real length decides whether a
# chin touch is even geometrically reachable on this rig.
gi_hand = {mesh.vertex_groups['LeftHand'].index} if 'LeftHand' in mesh.vertex_groups else set()
wrist_rest = mw @ arm.pose.bones['LeftHand'].head
hand_pts = [mesh.matrix_world @ v.co for v in mesh.data.vertices
            if sum(g.weight for g in v.groups if g.group in gi_hand) > 0.5]
HAND_LEN = (max((p - wrist_rest).length for p in hand_pts) * 0.92
            if hand_pts else 0.095)
FOREARM_LEN = ((mw @ arm.pose.bones['LeftHand'].head)
               - (mw @ arm.pose.bones['LeftForeArm'].head)).length
print('MEASURED hand_len=%.3f forearm_len=%.3f elbow_reach=%.3f (%d hand verts)'
      % (HAND_LEN, FOREARM_LEN, FOREARM_LEN + HAND_LEN, len(hand_pts)))

# ───────────────── solve the acting arm ─────────────────

def arm_eval(p, report=False):
    """p = [theta, phi, swing, elbow, wrist_x, wrist_z]"""
    for pb in arm.pose.bones:
        pb.rotation_quaternion = Quaternion()
        pb.location = (0, 0, 0)
    set_pose(BODY)
    th, ph = math.radians(p[0]), math.radians(p[1])
    ax = Vector((math.sin(th) * math.cos(ph), math.sin(th) * math.sin(ph),
                 math.cos(th)))
    arm.pose.bones['LeftArm'].rotation_quaternion = \
        Quaternion(ax, math.radians(p[2]))
    arm.pose.bones['LeftForeArm'].rotation_quaternion = \
        Quaternion(ELBOW_AXIS, math.radians(p[3]))
    arm.pose.bones['LeftHand'].rotation_quaternion = \
        Euler((math.radians(p[4]), 0, math.radians(p[5])), 'XYZ').to_quaternion()
    bpy.context.view_layer.update()

    sh = mw @ arm.pose.bones['LeftArm'].head
    el = mw @ arm.pose.bones['LeftForeArm'].head
    wr = mw @ arm.pose.bones['LeftHand'].head
    hb = arm.pose.bones['LeftHand']
    hand_dir = ((mw @ hb.tail) - wr)
    hand_dir = hand_dir.normalized() if hand_dir.length > 1e-6 else Vector((0, 0, 1))
    tip = wr + hand_dir * HAND_LEN

    # FINGERTIP grazes the JAW CORNER — slightly to her left of and below
    # the chin point. On a fingerless paddle this is the honest read of
    # "hand to chin" (a dead-centre chin poke needs an index finger).
    JAW = CHIN + Vector((0.022, 0.012, -0.012))
    cost = (tip - JAW).length * 1.0

    # the wrist stays below the jaw (fingers arrive from underneath) but
    # not absurdly low — the paddle only spans HAND_LEN
    if wr.z > JAW.z - 0.045:
        cost += (wr.z - (JAW.z - 0.045)) * 2.5

    # FINGERS POINT UP along the jaw, not across the mouth. This single
    # term is what separates "coy" from "covering her face" when the rig
    # has no fingers to curl.
    if hand_dir.z < 0.55:
        cost += (0.55 - hand_dir.z) * 0.35

    # the elbow drifts down toward the ribs (relaxed, not chicken-winged) —
    # gentle weight so it never beats reach or clearance
    if el.z > sh.z - 0.10:
        cost += (el.z - (sh.z - 0.10)) * 0.5

    # TORSO CLEARANCE: sample the upper arm and forearm; nothing may be
    # inside her chest. This is the term that was missing.
    pen = 0.0
    for a, b in ((sh, el), (el, wr)):
        for i in range(1, 9):
            pen += torso_penetration(a.lerp(b, i / 9.0))
    pen += torso_penetration(wr) + torso_penetration(tip, margin=0.0)
    cost += pen * 6.0

    # elbow hangs below the shoulder (no chicken wing) and not behind the back
    if el.z > sh.z - 0.04:
        cost += (el.z - (sh.z - 0.04)) * 2.0
    if el.y > sh.y + 0.03:
        cost += (el.y - sh.y - 0.03) * 2.0

    if report:
        print('ARMREPORT tip_err=%.4f pen=%.4f fingers_up=%.2f wrist_z=%.3f '
              'jaw_z=%.3f elbow_drop=%.3f'
              % ((tip - JAW).length, pen, hand_dir.z, wr.z, JAW.z, sh.z - el.z))
    return cost

LIM = [(0, 180), (-180, 180), (0, 140), (0, 135), (-70, 60), (-70, 70)]

def solve():
    best_p, best_c = None, 1e9
    # multi-start: the search surface has local minima (that's how the
    # chest-tunnel solution won last time)
    for seed in ([90, 0, 55, 80, -20, 0], [60, 40, 70, 100, -30, 20],
                 [120, -30, 60, 110, -10, -20], [90, 90, 80, 90, -40, 30]):
        p = [float(v) for v in seed]
        step = 24.0
        c = arm_eval(p)
        for _ in range(18):
            improved = False
            for i in range(len(p)):
                for d in (step, -step):
                    q = list(p)
                    q[i] = max(LIM[i][0], min(LIM[i][1], q[i] + d))
                    if q[i] == p[i]:
                        continue
                    cc = arm_eval(q)
                    if cc < c - 1e-5:
                        c, p, improved = cc, q, True
            if not improved:
                step *= 0.5
                if step < 0.75:
                    break
        if c < best_c:
            best_c, best_p = c, p
    return best_p, best_c

P, C = solve()
arm_eval(P, report=True)
print('SOLVED3 cost=%.4f theta=%.0f phi=%.0f swing=%.1f elbow=%.1f wrist=(%.0f,%.0f)'
      % (C, *P))

th, ph = math.radians(P[0]), math.radians(P[1])
ARM_AXIS = (math.sin(th) * math.cos(ph), math.sin(th) * math.sin(ph),
            math.cos(th))

COY = dict(BODY)
COY['LeftArm'] = ('axis', ARM_AXIS, P[2])
COY['LeftForeArm'] = ('axis', tuple(ELBOW_AXIS), P[3])
COY['LeftHand'] = [(X, P[4]), (Z, P[5])]

ANTICIPATE = {
    'Head':      [(Z, -8), (X, -3)],
    'neck':      [(Z, -4)],
    'Spine':     [(X, -2)],
    'HIPS_LOC':  (0, 0, 1.0),
}

OVER = {}
for b, sp in COY.items():
    if b == 'HIPS_LOC':
        OVER[b] = (sp[0] * 1.12, sp[1], sp[2] * 1.14)
    elif isinstance(sp, tuple) and sp[0] == 'axis':
        OVER[b] = ('axis', sp[1], sp[2] * 1.06)
    else:
        OVER[b] = [(a, d * 1.12) for a, d in sp]

# ───────────────────── staging ─────────────────────
for pb in arm.pose.bones:
    pb.rotation_quaternion = Quaternion()
    pb.location = (0, 0, 0)
set_pose(COY)
deps = bpy.context.evaluated_depsgraph_get()
lo, hi = Vector((1e9,) * 3), Vector((-1e9,) * 3)
for o in bpy.data.objects:
    if o.type != 'MESH':
        continue
    eo = o.evaluated_get(deps)
    for c in eo.bound_box:
        wc = eo.matrix_world @ Vector(c)
        for i in range(3):
            lo[i], hi[i] = min(lo[i], wc[i]), max(hi[i], wc[i])
full_center, full_size = (lo + hi) / 2, max(hi - lo)
upper_center = ((mw @ arm.pose.bones['Spine'].head)
                + (mw @ arm.pose.bones['Head'].head)) / 2
upper_size = full_size * 0.42

for nm, off, e, col in (('K', Vector((-1, -1.2, 1.4)), 2.4, (1.0, 0.96, 0.92)),
                        ('F', Vector((1.3, -0.9, 0.4)), 0.9, (0.82, 0.87, 1.0)),
                        ('R', Vector((0.2, 1.3, 0.7)), 0.6, (0.9, 0.9, 1.0))):
    d = bpy.data.lights.new(nm, 'SUN')
    d.energy, d.color, d.angle = e, col, math.radians(9)
    o = bpy.data.objects.new(nm, d)
    o.location = full_center + off * full_size
    o.rotation_euler = (full_center - o.location).to_track_quat('-Z', 'Y').to_euler()
    scene.collection.objects.link(o)
w = bpy.data.worlds.new('W')
w.use_nodes = True
w.node_tree.nodes['Background'].inputs['Color'].default_value = (0.11, 0.10, 0.13, 1)
scene.world = w
try:
    scene.render.engine = 'BLENDER_EEVEE'
except TypeError:
    scene.render.engine = 'BLENDER_EEVEE_NEXT'
scene.render.image_settings.file_format = 'PNG'
cam_data = bpy.data.cameras.new('C')
cam_data.lens = 55
cam = bpy.data.objects.new('C', cam_data)
scene.collection.objects.link(cam)
scene.camera = cam

def shoot(dirv, framing, mult, path):
    target = upper_center if framing == 'upper' else full_center
    size = upper_size if framing == 'upper' else full_size
    cam.location = target + Vector(dirv).normalized() * size * mult
    cam.rotation_euler = (target - cam.location).to_track_quat('-Z', 'Y').to_euler()
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)

VIEWS = [
    ((0, -1, 0.06), 'upper', 1.9, 'FRONT (upper)'),
    ((1, -0.05, 0.06), 'upper', 1.9, 'HER LEFT — arm side'),
    ((-1, -0.05, 0.06), 'upper', 1.9, 'HER RIGHT'),
    ((0.35, -0.5, 1.0), 'upper', 2.0, 'TOP-DOWN 45'),
    ((0.9, -1.25, 0.28), 'full', 1.55, 'FULL BODY 3/4'),
]

# ── POSE GATE (default): 5 angles of the landed pose ──
scene.render.resolution_x, scene.render.resolution_y = 620, 720
man = []
for i, (dv, fr, mu, label) in enumerate(VIEWS):
    shoot(dv, fr, mu, OUT + '\\coy3chk_%02d.png' % (i + 1))
    man.append({'index': i + 1, 'label': label})
    print('rendered gate', label)
with open(OUT + '\\coy3chk_manifest.json', 'w') as fh:
    json.dump({'samples': man}, fh)

# ───────────────── author the motion (only if asked) ─────────────────
if '--grid' in ARGS or '--full' in ARGS:
    for pb in arm.pose.bones:
        pb.rotation_quaternion = Quaternion()
        pb.location = (0, 0, 0)
    arm.animation_data_clear()
    allb = list(COY.keys())
    key_rest(1, allb)
    apply_pose(14, ANTICIPATE)
    key_rest(14, [b for b in COY if b not in ANTICIPATE])
    apply_pose(30, {k: v for k, v in COY.items()
                    if k not in ('Head', 'neck')}, 0.6)
    apply_pose(30, {'LeftArm': COY['LeftArm'],
                    'LeftForeArm': COY['LeftForeArm']}, 0.85)
    apply_pose(44, OVER)
    apply_pose(54, {k: v for k, v in COY.items() if k not in ('Head', 'neck')})
    apply_pose(60, {'Head': COY['Head'], 'neck': COY['neck']})
    for f in range(72, FRAMES + 1, 12):
        t = (f - 60) / 60.0
        sway = math.sin(t * math.pi * 0.8) * 1.2
        breath = math.sin(t * math.pi * 1.6) * 0.8
        tilt = math.sin(t * math.pi * 0.5 + 0.7) * 1.5
        hold = dict(COY)
        hold['Hips'] = COY['Hips'] + [(Y, sway)]
        hold['Spine01'] = COY['Spine01'] + [(X, breath)]
        hold['Spine'] = COY['Spine'] + [(X, breath * 0.7)]
        hold['Head'] = COY['Head'] + [(Y, tilt), (X, breath * 0.5)]
        apply_pose(f, hold)
    ad = arm.animation_data
    if ad and ad.action:
        a = ad.action
        cs = ([a.fcurves] if hasattr(a, 'fcurves')
              else [cb.fcurves for L in a.layers for s in L.strips
                    for cb in s.channelbags])
        for fcs in cs:
            for fc in fcs:
                for kp in fc.keyframe_points:
                    kp.interpolation = 'BEZIER'
                    kp.handle_left_type = 'AUTO_CLAMPED'
                    kp.handle_right_type = 'AUTO_CLAMPED'
    scene.frame_start, scene.frame_end = 1, FRAMES

    PHASES = [(1, 'rest'), (8, 'anticipate'), (18, 'the move'),
              (40, 'overshoot'), (50, 'settle'), (60, 'coy — living hold')]

    def phase_of(f):
        lab = ''
        for s0, l in PHASES:
            if f >= s0:
                lab = l
        return lab

    if '--grid' in ARGS:
        scene.render.resolution_x, scene.render.resolution_y = 620, 720
        frames = sorted({max(1, min(FRAMES, round(1 + (FRAMES - 1) * i / 11)))
                         for i in range(12)})
        gm = []
        for i, f in enumerate(frames):
            scene.frame_set(f)
            shoot((0.9, -1.25, 0.28), 'full', 1.55,
                  OUT + '\\coy3grid_%02d.png' % (i + 1))
            gm.append({'index': i + 1, 'frame': f,
                       'time': round((f - 1) / FPS, 3), 'phase': phase_of(f)})
            print('rendered grid', f)
        with open(OUT + '\\coy3grid_manifest.json', 'w') as fh:
            json.dump({'samples': gm}, fh)

    if '--full' in ARGS:
        scene.render.resolution_x, scene.render.resolution_y = 720, 720
        target, size = full_center, full_size
        cam.location = target + Vector((0.9, -1.25, 0.28)).normalized() * size * 1.55
        cam.rotation_euler = (target - cam.location).to_track_quat('-Z', 'Y').to_euler()
        scene.render.filepath = OUT + '\\coy3full_'
        bpy.ops.render.render(animation=True)
