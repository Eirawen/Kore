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
    if isinstance(spec, tuple) and spec and spec[0] == 'quat':
        # pre-computed bone-local quaternion (look-at results)
        return Quaternion().slerp(spec[1], blend)
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

# ───────────────── generalized delta application ─────────────────
# THE fix for stale rest frames: express an ARMATURE-space rotation in a
# bone's own frame using its LIVE world matrix (posed parents included):
#     armature_rot = M0 @ pose      (M0 = parent_world @ rest_local)
#     want armature_rot = D @ M0    ->  pose = M0^-1 @ D @ M0
# matrix_local (used by local_quat) is the REST frame and goes stale the
# moment an ancestor moves; this does not.
def apply_delta(pb, D):
    pb.rotation_quaternion = Quaternion()
    bpy.context.view_layer.update()
    M0 = pb.matrix.to_quaternion()
    pb.rotation_quaternion = M0.inverted() @ D @ M0
    bpy.context.view_layer.update()

# Direction from her to the audience (the 3/4 hero angle).
AUDIENCE = Vector((0.9, -1.25, 0.28)).normalized()

def gaze_dir(yaw_deg, pitch_down_deg):
    """A desired facing built RELATIVE to the audience: yaw away/toward,
    then pitch down. Coy = yawed away early, yawed back + pitched down
    at the end (chin tucked, face still aimed at you)."""
    d = AUDIENCE.copy()
    d.rotate(Quaternion(Vector((0, 0, 1)), math.radians(yaw_deg)))
    horiz = Vector((d.x, d.y, 0)).normalized()
    p = math.radians(pitch_down_deg)
    return (horiz * math.cos(p) + Vector((0, 0, -1)) * math.sin(p)).normalized()

def head_fwd():
    return ((arm.pose.bones['headfront'].head
             - arm.pose.bones['Head'].head)).normalized()

def aim_head(desired, roll_deg, neck_share=0.38):
    """Look-at for the head: split the turn neck/head (a neck that shares
    the rotation reads as a curve, not a snapped-on head), then roll the
    head about its final forward for the coy tilt."""
    neck, hd = arm.pose.bones['neck'], arm.pose.bones['Head']
    neck.rotation_quaternion = Quaternion()
    hd.rotation_quaternion = Quaternion()
    bpy.context.view_layer.update()
    D = head_fwd().rotation_difference(desired)
    apply_delta(neck, Quaternion().slerp(D, neck_share))
    D2 = head_fwd().rotation_difference(desired)
    apply_delta(hd, D2)
    if abs(roll_deg) > 1e-6:
        f = head_fwd()
        cur = hd.rotation_quaternion.copy()
        pb_M0 = None
        hd.rotation_quaternion = Quaternion()
        bpy.context.view_layer.update()
        M0 = hd.matrix.to_quaternion()
        hd.rotation_quaternion = cur
        bpy.context.view_layer.update()
        roll = Quaternion(f, math.radians(roll_deg))
        hd.rotation_quaternion = M0.inverted() @ roll @ (M0 @ cur)
        bpy.context.view_layer.update()
    return (neck.rotation_quaternion.copy(), hd.rotation_quaternion.copy())

# ───────────────── COY BODY: contract, twist away, knees in ──────────
# Coy is approach-avoidance made structural: the torso turns AWAY from
# the audience while the face comes BACK. The body also gets smaller —
# shoulders up, spine curled, knees converged (uchimata).
KNEE_SIGN = 1.0        # verified numerically below

def body_pose(knee=1.0):
    return {
        # deeper curtsy + weight onto her right leg, hips swung out (S-curve)
        'HIPS_LOC':  (-3.2, 2.2, -9.5),
        'Hips':      [(Y, 4.0), (Z, -7)],            # sway + twist away
        # weight leg (right): softer, knee driven inward
        'RightUpLeg': [(X, -6), (Z, -9 * knee)],
        'RightLeg':  [(X, 15)],
        'RightFoot': [(X, -5), (Z, -10 * knee)],     # toe turned IN
        # free leg (left): more bend, knee crosses toward the midline
        'LeftUpLeg': [(X, -10), (Z, 13 * knee)],
        'LeftLeg':   [(X, 21)],
        'LeftFoot':  [(X, -7), (Z, 12 * knee)],      # toe turned IN
        # spine: forward curl (making herself small) + continued twist away
        'Spine02':   [(X, 5), (Y, -2), (Z, -5)],
        'Spine01':   [(X, 6), (Y, -2), (Z, -5)],
        'Spine':     [(X, 7), (Y, 2), (Z, -4)],
        # SHOULDER SQUEEZE: the left shoulder rises to meet the hand
        'LeftShoulder':  [(Y, 15)],
        'RightShoulder': [(Y, -9)],
    }

BODY = body_pose(KNEE_SIGN)

# verify the knees actually CONVERGE (measure, don't guess the sign)
def knee_gap(knee):
    for pb in arm.pose.bones:
        pb.rotation_quaternion = Quaternion()
        pb.location = (0, 0, 0)
    set_pose(body_pose(knee))
    return abs((arm.pose.bones['LeftLeg'].head
                - arm.pose.bones['RightLeg'].head).x)

for pb in arm.pose.bones:
    pb.rotation_quaternion = Quaternion()
    pb.location = (0, 0, 0)
bpy.context.view_layer.update()
rest_gap = abs((arm.pose.bones['LeftLeg'].head
                - arm.pose.bones['RightLeg'].head).x)
gp, gn = knee_gap(1.0), knee_gap(-1.0)
KNEE_SIGN = 1.0 if gp < gn else -1.0
BODY = body_pose(KNEE_SIGN)
print('KNEES rest_gap=%.4f  (+)=%.4f  (-)=%.4f  -> sign %+.0f (converging)'
      % (rest_gap, gp, gn, KNEE_SIGN))

# ───────────────── measured hands ─────────────────
def hand_extent(side):
    gname = side + 'Hand'
    if gname not in mesh.vertex_groups:
        return 0.12
    gi = {mesh.vertex_groups[gname].index}
    for pb in arm.pose.bones:
        pb.rotation_quaternion = Quaternion()
        pb.location = (0, 0, 0)
    bpy.context.view_layer.update()
    wr = mw @ arm.pose.bones[gname].head
    pts = [mesh.matrix_world @ v.co for v in mesh.data.vertices
           if sum(g.weight for g in v.groups if g.group in gi) > 0.5]
    return (max((p - wr).length for p in pts) * 0.92) if pts else 0.12

HAND_L, HAND_R = hand_extent('Left'), hand_extent('Right')
ELBOW_AXIS_R, _ = None, None
print('MEASURED hand_L=%.3f hand_R=%.3f' % (HAND_L, HAND_R))

# ───────────────── generic arm solver (either side) ─────────────────
def solve_arm(side, target, hand_len, elbow_axis, fingers_up=None,
              wrist_below=None, seeds=None, w_clear=6.0, label=''):
    A, F, H = side + 'Arm', side + 'ForeArm', side + 'Hand'
    lat = 1.0 if side == 'Left' else -1.0

    def ev(p, report=False):
        for pb in arm.pose.bones:
            pb.rotation_quaternion = Quaternion()
            pb.location = (0, 0, 0)
        set_pose(BODY)
        th, ph = math.radians(p[0]), math.radians(p[1])
        ax = Vector((math.sin(th) * math.cos(ph), math.sin(th) * math.sin(ph),
                     math.cos(th)))
        arm.pose.bones[A].rotation_quaternion = Quaternion(ax, math.radians(p[2]))
        arm.pose.bones[F].rotation_quaternion = Quaternion(elbow_axis,
                                                           math.radians(p[3]))
        arm.pose.bones[H].rotation_quaternion = Euler(
            (math.radians(p[4]), 0, math.radians(p[5])), 'XYZ').to_quaternion()
        bpy.context.view_layer.update()
        sh = mw @ arm.pose.bones[A].head
        el = mw @ arm.pose.bones[F].head
        wr = mw @ arm.pose.bones[H].head
        hb = arm.pose.bones[H]
        hd = ((mw @ hb.tail) - wr)
        hd = hd.normalized() if hd.length > 1e-6 else Vector((0, 0, 1))
        tip = wr + hd * hand_len
        cost = (tip - target).length
        if fingers_up is not None:
            # BAND, not a floor: a floor lets the solver stand the paddle
            # straight up into a wall over her mouth. Coy wants the hand
            # angled up-and-inward ALONG the jaw.
            lo_b, hi_b = fingers_up
            if hd.z < lo_b:
                cost += (lo_b - hd.z) * 0.45
            elif hd.z > hi_b:
                cost += (hd.z - hi_b) * 0.45
        if wrist_below is not None and wr.z > wrist_below:
            cost += (wr.z - wrist_below) * 2.5
        pen = 0.0
        for a, b in ((sh, el), (el, wr)):
            for i in range(1, 9):
                pen += torso_penetration(a.lerp(b, i / 9.0))
        pen += torso_penetration(wr) + torso_penetration(tip, margin=0.0)
        cost += pen * w_clear
        if el.z > sh.z - 0.04:
            cost += (el.z - (sh.z - 0.04)) * 2.0
        if el.y > sh.y + 0.03:
            cost += (el.y - sh.y - 0.03) * 2.0
        if report:
            print('ARM[%s] tip_err=%.4f pen=%.4f fingers_z=%.2f'
                  % (label or side, (tip - target).length, pen, hd.z))
        return cost

    LIMS = [(0, 180), (-180, 180), (0, 140), (0, 135), (-70, 60), (-70, 70)]
    seeds = seeds or [[90, 0, 55, 80, -20, 0], [60, 40 * lat, 70, 100, -30, 20],
                      [120, -30 * lat, 60, 110, -10, -20],
                      [90, 90 * lat, 80, 90, -40, 30]]
    bp, bc = None, 1e9
    for seed in seeds:
        p = [float(v) for v in seed]
        step, c = 24.0, ev(p)
        for _ in range(18):
            improved = False
            for i in range(len(p)):
                for d in (step, -step):
                    q = list(p)
                    q[i] = max(LIMS[i][0], min(LIMS[i][1], q[i] + d))
                    if q[i] == p[i]:
                        continue
                    cc = ev(q)
                    if cc < c - 1e-5:
                        c, p, improved = cc, q, True
            if not improved:
                step *= 0.5
                if step < 0.75:
                    break
        if c < bc:
            bc, bp = c, p
    ev(bp, report=True)
    th, ph = math.radians(bp[0]), math.radians(bp[1])
    axis = (math.sin(th) * math.cos(ph), math.sin(th) * math.sin(ph),
            math.cos(th))
    return {A: ('axis', axis, bp[2]),
            F: ('axis', tuple(elbow_axis), bp[3]),
            H: [(X, bp[4]), (Z, bp[5])]}, bp

ELBOW_R, _r = dominant_axis('RightForeArm')

# LEFT hand -> the jaw/cheek (fingers up along the face)
JAW = CHIN + Vector((0.034, 0.020, -0.026))   # jawline, below the mouth
left_pose, lp = solve_arm('Left', JAW, HAND_L, ELBOW_AXIS,
                          fingers_up=(0.42, 0.66), wrist_below=JAW.z - 0.040,
                          label='Left->jaw')

# RIGHT hand -> across the waist to her opposite (left) hip: the closed,
# contained silhouette. Idle arms kill a pose; give it a job.
for pb in arm.pose.bones:
    pb.rotation_quaternion = Quaternion()
    pb.location = (0, 0, 0)
set_pose(BODY)
hip_pt = (mw @ arm.pose.bones['LeftUpLeg'].head) + Vector((0.035, -0.055, 0.02))
right_pose, rp = solve_arm('Right', hip_pt, HAND_R, ELBOW_R,
                           seeds=[[80, -30, 45, 55, 0, 0], [95, -60, 60, 70, -10, 10],
                                  [70, -10, 35, 45, 10, -10]],
                           label='Right->hip')

# ───────────────── compose the landed COY pose ─────────────────
for pb in arm.pose.bones:
    pb.rotation_quaternion = Quaternion()
    pb.location = (0, 0, 0)
set_pose(BODY)
set_pose(left_pose)
set_pose(right_pose)
# THE coy gaze: yawed BACK toward the audience, chin tucked, head rolled
# toward the raised shoulder.
NECK_COY, HEAD_COY = aim_head(gaze_dir(-3, 15), roll_deg=-17)
f_coy = head_fwd()
print('GAZE coy fwd=%s  (audience dot=%.2f, down=%.2f)'
      % ([round(v, 2) for v in f_coy], f_coy.dot(AUDIENCE), -f_coy.z))

COY = dict(BODY)
COY.update(left_pose)
COY.update(right_pose)
COY['neck'] = ('quat', NECK_COY)
COY['Head'] = ('quat', HEAD_COY)

# the shy FLINCH: face turned away, chin down a little
for pb in arm.pose.bones:
    pb.rotation_quaternion = Quaternion()
    pb.location = (0, 0, 0)
NECK_AWAY, HEAD_AWAY = aim_head(gaze_dir(-62, 12), roll_deg=4)
f_away = head_fwd()
print('GAZE away fwd=%s (audience dot=%.2f)'
      % ([round(v, 2) for v in f_away], f_away.dot(AUDIENCE)))

FLINCH = {
    'neck': ('quat', NECK_AWAY),
    'Head': ('quat', HEAD_AWAY),
    'Spine': [(X, -1), (Z, -3)],
    'LeftShoulder': [(Y, 8)],
    'RightShoulder': [(Y, -5)],
    'HIPS_LOC': (0, 0, 0.8),
}

OVER = {}
for b, sp in COY.items():
    if b == 'HIPS_LOC':
        OVER[b] = (sp[0] * 1.10, sp[1], sp[2] * 1.12)
    elif isinstance(sp, tuple) and sp[0] == 'axis':
        OVER[b] = ('axis', sp[1], sp[2] * 1.05)
    elif isinstance(sp, tuple) and sp[0] == 'quat':
        OVER[b] = sp
    else:
        OVER[b] = [(a, d * 1.10) for a, d in sp]


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

HERO = (0.9, -1.25, 0.28)
VIEWS = [
    ((0, -1, 0.06), 'upper', 1.9, 'FRONT (upper)'),
    ((1, -0.05, 0.06), 'upper', 1.9, 'HER LEFT — arm side'),
    ((-1, -0.05, 0.06), 'upper', 1.9, 'HER RIGHT'),
    ((0.35, -0.5, 1.0), 'upper', 2.0, 'TOP-DOWN 45'),
    (HERO, 'full', 1.5, 'HERO 3/4 (full)'),
]
scene.render.resolution_x, scene.render.resolution_y = 620, 720
man = []
for i, (dv, fr, mu, label) in enumerate(VIEWS):
    shoot(dv, fr, mu, OUT + '\\coy5chk_%02d.png' % (i + 1))
    man.append({'index': i + 1, 'label': label})
with open(OUT + '\\coy5chk_manifest.json', 'w') as fh:
    json.dump({'samples': man}, fh)
print('GATE rendered')

# ════════════════ COMPONENT TRACKS ════════════════
# Khaled's methodology: ask what EACH body part should be doing at each
# step, and backwards-induct from the end state. Every component gets its
# OWN clock. Keying whole-body poses on shared frames is what made the
# hesitation symmetric (she hesitated to touch her face AND her thigh on
# the same frame) and made the hold a single-sine puppet wiggle.
FRAMES = 200

COMP = {
    'head':      ['neck', 'Head'],
    'chest':     ['Spine', 'Spine01', 'Spine02'],
    'pelvis':    ['Hips', 'HIPS_LOC'],
    'legs':      ['LeftUpLeg', 'LeftLeg', 'RightUpLeg', 'RightLeg'],
    'feet':      ['LeftFoot', 'RightFoot'],
    'larm':      ['LeftArm', 'LeftForeArm', 'LeftHand'],
    'lshoulder': ['LeftShoulder'],
    'rarm':      ['RightShoulder', 'RightArm', 'RightForeArm', 'RightHand'],
}

def key_comp(frame, comp, pose, blend=1.0, extra=None):
    """Key ONLY this component's bones. pose=None means rest."""
    for b in COMP[comp]:
        if pose is None:
            spec = None
        else:
            spec = pose.get(b)
        if b == 'HIPS_LOC':
            pb = arm.pose.bones['Hips']
            off = Vector(spec) * blend if spec else Vector((0, 0, 0))
            pb.location = local_loc(pb, off)
            pb.keyframe_insert('location', frame=frame)
            continue
        pb = arm.pose.bones.get(b)
        if pb is None:
            continue
        if spec is None:
            pb.rotation_quaternion = Quaternion()
        else:
            if extra and b in extra:
                if isinstance(spec, list):
                    spec = spec + extra[b]
            pb.rotation_quaternion = spec_quat(pb, spec, blend)
        pb.keyframe_insert('rotation_quaternion', frame=frame)

for pb in arm.pose.bones:
    pb.rotation_quaternion = Quaternion()
    pb.location = (0, 0, 0)
arm.animation_data_clear()

# everything starts at rest
for c in COMP:
    key_comp(1, c, None)

# ── HEAD: first to move, last to settle. The bookend. ───────────────
# A flinch is a REFLEX — 9 frames. Then it waits (she's not ready to look
# at you) while the arms do their work. The look back is the slowest
# thing in the piece because hesitation is the whole emotion.
key_comp(10, 'head', FLINCH)
key_comp(84, 'head', FLINCH)              # holds away through the arm work
key_comp(126, 'head', COY)                # ...then the slow return (42f)

# ── CHEST: follows the head into the turn, LAGGING 6 frames (you turn
# away with your body a beat after your face). Breath is the only true
# oscillation in the body, and it HOLDS during the hesitation.
key_comp(16, 'chest', COY, 0.5)
key_comp(34, 'chest', COY, 1.0)
BR = lambda a: {'Spine01': [(X, a)], 'Spine': [(X, a * 0.7)],
                'Spine02': [(X, a * 0.5)]}
for f, a in ((44, 0.9), (56, -0.5)):
    key_comp(f, 'chest', COY, 1.0, extra=BR(a))
key_comp(64, 'chest', COY, 1.0, extra=BR(-0.7))   # breath HELD through
key_comp(76, 'chest', COY, 1.0, extra=BR(-0.7))   # the hesitation
key_comp(92, 'chest', COY, 1.0, extra=BR(1.5))    # the exhale, after landing
key_comp(110, 'chest', COY, 1.0, extra=BR(0.2))

# ── PELVIS + LEGS + FEET: the postural layer. Slow, early, finished
# before anything interesting happens. Nobody watches a weight shift.
key_comp(18, 'pelvis', COY, 0.35)
key_comp(52, 'pelvis', COY, 1.0)
key_comp(20, 'legs', COY, 0.3)
key_comp(56, 'legs', COY, 1.0)
key_comp(22, 'feet', COY, 0.3)
key_comp(58, 'feet', COY, 1.0)

# ── RIGHT ARM: the PROTECTIVE arm. Automatic, pre-decision, so it moves
# early and NEVER hesitates. Already settled before the other arm has
# decided anything. (This asymmetry in TIME is the fix.)
key_comp(12, 'rarm', COY, 0.25)
key_comp(30, 'rarm', COY, 0.8)
key_comp(46, 'rarm', COY, 1.0)

# ── LEFT ARM: the SELF-CONSCIOUS one. Late start, owns the hesitation
# alone, arrives last of the limbs, then goes COMPLETELY STILL —
# that stillness is the embarrassment.
key_comp(32, 'larm', COY, 0.30)
key_comp(56, 'larm', COY, 0.84)
key_comp(70, 'larm', COY, 0.87)           # ── THE STALL: she almost doesn't
key_comp(82, 'larm', OVER, 1.0)           # commits, slight overshoot
key_comp(92, 'larm', COY, 1.0)            # settles at the jaw, and stops

# ── LEFT SHOULDER: arrives AFTER the hand and creeps up to meet it.
# Overlapping action inside one limb — the bashful squeeze lands late.
key_comp(40, 'lshoulder', COY, 0.25)
key_comp(88, 'lshoulder', COY, 0.55)
key_comp(112, 'lshoulder', COY, 1.0)

# ════════════════ THE HOLD ════════════════
# Each component on its OWN clock, and fidgets are EVENTS (a decision she
# makes once) not oscillations. Only breath oscillates. Head and both
# hands are STILL — a coy person freezes.
key_comp(150, 'chest', COY, 1.0, extra=BR(-0.6))
key_comp(178, 'chest', COY, 1.0, extra=BR(0.8))
key_comp(200, 'chest', COY, 1.0, extra=BR(-0.2))

# the shy WEIGHT SHIFT: one discrete event, legs + pelvis + free foot
# only. It resolves and stays resolved.
SHIFT_P = {'Hips': COY['Hips'] + [(Y, 1.5)], 'HIPS_LOC': (COY['HIPS_LOC'][0] + 0.5,
           COY['HIPS_LOC'][1], COY['HIPS_LOC'][2] + 0.6)}
SHIFT_L = {'LeftUpLeg': COY['LeftUpLeg'] + [(X, -2.5)],
           'LeftLeg': COY['LeftLeg'] + [(X, 3.0)],
           'RightUpLeg': COY['RightUpLeg'], 'RightLeg': COY['RightLeg']}
SHIFT_F = {'LeftFoot': COY['LeftFoot'] + [(Z, 7)],   # the toe pivots
           'RightFoot': COY['RightFoot']}
key_comp(146, 'pelvis', COY, 1.0)
key_comp(160, 'pelvis', SHIFT_P, 1.0)
key_comp(200, 'pelvis', SHIFT_P, 1.0)
key_comp(148, 'legs', COY, 1.0)
key_comp(162, 'legs', SHIFT_L, 1.0)
key_comp(200, 'legs', SHIFT_L, 1.0)
key_comp(150, 'feet', COY, 1.0)
key_comp(166, 'feet', SHIFT_F, 1.0)
key_comp(200, 'feet', SHIFT_F, 1.0)

# head: micro-drift only, its own slow clock, amplitude barely there
key_comp(158, 'head', COY, 1.0, extra={'neck': [(Z, -0.6)]})
key_comp(192, 'head', COY, 1.0, extra={'neck': [(Z, 0.4)]})
# arms: nothing. They hold. (No keys = no motion.)
key_comp(200, 'larm', COY, 1.0)
key_comp(200, 'lshoulder', COY, 1.0)
key_comp(200, 'rarm', COY, 1.0)

ad = arm.animation_data
if ad and ad.action:
    a = ad.action
    cs = ([a.fcurves] if hasattr(a, 'fcurves')
          else [cb.fcurves for L in a.layers for s in L.strips
                for cb in s.channelbags])
    n = 0
    for fcs in cs:
        for fc in fcs:
            for kp in fc.keyframe_points:
                kp.interpolation = 'BEZIER'
                kp.handle_left_type = 'AUTO_CLAMPED'
                kp.handle_right_type = 'AUTO_CLAMPED'
                n += 1
    print('SMOOTHED %d keyframes' % n)
scene.frame_start, scene.frame_end = 1, FRAMES

if '--grid' in ARGS:
    scene.render.resolution_x, scene.render.resolution_y = 470, 550
    frames = sorted({max(1, min(FRAMES, round(1 + (FRAMES - 1) * i / 11)))
                     for i in range(12)})
    gm = []
    for i, f in enumerate(frames):
        scene.frame_set(f)
        shoot(HERO, 'full', 1.5, OUT + '\\coy5grid_%02d.png' % (i + 1))
        gm.append({'index': i + 1, 'frame': f, 'time': round((f - 1) / FPS, 3)})
    with open(OUT + '\\coy5grid_manifest.json', 'w') as fh:
        json.dump({'samples': gm}, fh)
    print('GRID rendered')

if '--full' in ARGS:
    scene.render.resolution_x, scene.render.resolution_y = 720, 760
    cam.location = full_center + Vector(HERO).normalized() * full_size * 1.5
    cam.rotation_euler = (full_center - cam.location).to_track_quat('-Z', 'Y').to_euler()
    scene.render.filepath = OUT + '\\coy5full_'
    bpy.ops.render.render(animation=True)
