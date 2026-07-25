"""
JUMP — with wing surgery, foot-planting IK, and a real ballistic arc.

Three pieces of engineering the coy emote didn't need:

1. WING SURGERY. Probe found the wings (one 330-vert island, +-0.48 wide at
   shoulder height) weighted to LeftArm/RightArm — Meshy's auto-rigger
   attached them to the nearest LIMB, so her wings got dragged around by
   her arms. Fixed: 2 new bones per wing parented to Spine, wing verts
   re-weighted to them exclusively. Now they ride the torso, can be posed,
   and (in-engine) can be driven by the spring-bone system for free.

2. FOOT-PLANTING IK. An FK rig + a lowering root = feet sinking through
   the floor. Solve (thigh, knee, ankle) per side so a chosen bone stays
   at a world target while the hips move. Ankle target for a flat-foot
   crouch; TOE target during toe-off, so the heel lifts and she rolls off
   the ball of the foot (this is what separates a jump from a levitation).

3. BALLISTIC ROOT. Flight height is computed, not eased: z(t) = z0 + v0*t
   - g*t^2/2, keyed every 2 frames. A symmetric bezier ease floats at the
   apex; real gravity gives fast-rise / hang / fast-fall for free.

Characterisation: her wings react LATE and don't help. She's a low-tier
demon in a bumfuck dungeon — the flap is vestigial, the arc is pure legs.

Run: blender --background --python animate_jump.py -- [--grid] [--full]
"""
import bpy
import sys
import json
import math
from mathutils import Vector, Quaternion, Euler

GLB = '/home/khaled/Kore/succubus_walk.glb'
OUT = r'C:\tmp'
FPS = 60
argv = sys.argv
ARGS = argv[argv.index('--') + 1:] if '--' in argv else []

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=GLB)
scene = bpy.context.scene
scene.render.fps = FPS
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
mesh = next(o for o in bpy.data.objects if o.type == 'MESH')

# ═══════════════ learn joint axes from her walk ═══════════════
action = arm.animation_data.action
f0, f1 = (int(v) for v in action.frame_range)

def dominant_axis(bname):
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
    return acc

AX = {b: dominant_axis(b) for b in
      ('LeftUpLeg', 'LeftLeg', 'LeftFoot', 'RightUpLeg', 'RightLeg',
       'RightFoot', 'LeftForeArm', 'RightForeArm', 'LeftArm', 'RightArm')}
print('LEARNED knee axis L=%s R=%s'
      % ([round(v, 2) for v in AX['LeftLeg']],
         [round(v, 2) for v in AX['RightLeg']]))

arm.animation_data_clear()
for pb in arm.pose.bones:
    pb.rotation_mode = 'QUATERNION'
    pb.rotation_quaternion = Quaternion()
    pb.location = (0, 0, 0)
scene.frame_set(1)
bpy.context.view_layer.update()
mw = arm.matrix_world
mwi = mw.inverted()

# ═══════════════ 1. WING SURGERY ═══════════════
import bmesh
bm = bmesh.new()
bm.from_mesh(mesh.data)
bm.verts.ensure_lookup_table()
seen, islands = set(), []
for v in bm.verts:
    if v.index in seen:
        continue
    stack, comp = [v], []
    seen.add(v.index)
    while stack:
        cur = stack.pop()
        comp.append(cur.index)
        for e in cur.link_edges:
            o = e.other_vert(cur)
            if o.index not in seen:
                seen.add(o.index)
                stack.append(o)
    islands.append(comp)
bm.free()

def wpos(i):
    return mesh.matrix_world @ mesh.data.vertices[i].co

wing_verts = None
for comp in islands:
    pts = [wpos(i) for i in comp]
    xs = [p.x for p in pts]
    zs = [p.z for p in pts]
    if (max(xs) - min(xs)) > 0.7 and min(zs) > 0.9 and len(comp) < 800:
        wing_verts = comp
        break
if wing_verts is None:
    raise RuntimeError('wing island not found')
wp = [wpos(i) for i in wing_verts]
print('WINGS island n=%d  x=[%.2f,%.2f] z=[%.2f,%.2f]'
      % (len(wing_verts), min(p.x for p in wp), max(p.x for p in wp),
         min(p.z for p in wp), max(p.z for p in wp)))

# per-side extents drive the bone placement (measured, not guessed)
spine_w = mw @ arm.pose.bones['Spine'].head
sides = {}
for sgn, name in ((1, 'L'), (-1, 'R')):
    pts = [(i, wpos(i)) for i in wing_verts if (wpos(i).x - spine_w.x) * sgn > 0.02]
    if not pts:
        continue
    xs = [p.x for _, p in pts]
    out = max(xs) if sgn > 0 else min(xs)
    inner = min(xs, key=abs)
    zt = max(p.z for _, p in pts)
    zb = min(p.z for _, p in pts)
    ym = sum(p.y for _, p in pts) / len(pts)
    sides[name] = dict(idx=[i for i, _ in pts], sgn=sgn, out=out,
                       inner=inner, ztop=zt, zbot=zb, ym=ym)
    print('WING[%s] n=%d inner_x=%.3f outer_x=%.3f z=[%.3f,%.3f] mid_y=%.3f'
          % (name, len(pts), inner, out, zb, zt, ym))

bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode='EDIT')
eb = arm.data.edit_bones
spine_eb = eb['Spine']
for name, s in sides.items():
    # root: shoulder-blade attachment -> mid-wing;  tip: mid -> outer edge
    root_w = Vector((s['inner'] + 0.02 * s['sgn'], s['ym'], s['ztop'] - 0.03))
    mid_w = Vector((s['inner'] + (s['out'] - s['inner']) * 0.5, s['ym'],
                    (s['ztop'] + s['zbot']) / 2 + 0.02))
    out_w = Vector((s['out'], s['ym'], s['zbot'] + 0.03))
    rb = eb.new('Wing%s_root' % name)
    rb.head, rb.tail = mwi @ root_w, mwi @ mid_w
    rb.parent, rb.use_connect = spine_eb, False
    tb = eb.new('Wing%s_tip' % name)
    tb.head, tb.tail = mwi @ mid_w, mwi @ out_w
    tb.parent, tb.use_connect = rb, True
    s['mid_w'], s['root_w'], s['out_w'] = mid_w, root_w, out_w
bpy.ops.object.mode_set(mode='OBJECT')
bpy.context.view_layer.update()

# re-weight: wing verts belong to the wing bones ALONE (this is the fix —
# they were being dragged around by LeftArm/RightArm)
for name in sides:
    for suffix in ('root', 'tip'):
        g = 'Wing%s_%s' % (name, suffix)
        if g not in mesh.vertex_groups:
            mesh.vertex_groups.new(name=g)
for name, s in sides.items():
    rg = mesh.vertex_groups['Wing%s_root' % name]
    tg = mesh.vertex_groups['Wing%s_tip' % name]
    span = abs(s['out'] - s['inner']) or 1.0
    for i in s['idx']:
        p = wpos(i)
        t = min(1.0, max(0.0, abs(p.x - s['inner']) / span))
        # smooth two-bone falloff along the wing
        w_tip = min(1.0, max(0.0, (t - 0.30) / 0.40))
        w_tip = w_tip * w_tip * (3 - 2 * w_tip)
        for vg in mesh.vertex_groups:
            try:
                vg.remove([i])
            except RuntimeError:
                pass
        rg.add([i], 1.0 - w_tip, 'REPLACE')
        tg.add([i], w_tip, 'REPLACE')
print('WINGS re-weighted to %d new bones (was LeftArm/RightArm)'
      % (2 * len(sides)))

for pb in arm.pose.bones:
    pb.rotation_mode = 'QUATERNION'
    pb.rotation_quaternion = Quaternion()
    pb.location = (0, 0, 0)
bpy.context.view_layer.update()

# ═══════════════ pose machinery ═══════════════
def local_quat(pb, axis_arm, deg):
    m = pb.bone.matrix_local.to_3x3().inverted()
    return Quaternion((m @ Vector(axis_arm)).normalized(), math.radians(deg))

def local_loc(pb, off):
    return pb.bone.matrix_local.to_3x3().inverted() @ Vector(off)

X, Y, Z = (1, 0, 0), (0, 1, 0), (0, 0, 1)

def spec_quat(pb, spec, blend=1.0):
    if isinstance(spec, tuple) and spec and spec[0] == 'quat':
        return Quaternion().slerp(spec[1], blend)
    if isinstance(spec, tuple) and spec and spec[0] == 'axis':
        return Quaternion(Vector(spec[1]).normalized(),
                          math.radians(spec[2] * blend))
    q = Quaternion()
    for item in spec:
        if len(item) == 3 and item[0] == 'L':
            # bone-LOCAL axis (the learned hinges live in this space)
            q = q @ Quaternion(Vector(item[1]).normalized(),
                               math.radians(item[2] * blend))
        else:
            ax, deg = item
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

# ═══════════════ 2. FOOT-PLANTING IK ═══════════════
# The hips move; the contact bone must not. Solve 3 scalars per leg about
# the LEARNED joint axes (thigh flex, knee flex, ankle flex).
STANCE = {}
for side in ('Left', 'Right'):
    STANCE[side] = {b: (mw @ arm.pose.bones[side + b].head)
                    for b in ('UpLeg', 'Leg', 'Foot', 'ToeBase')}
HIPS_REST = mw @ arm.pose.bones['Hips'].head
print('STANCE hips_z=%.3f  L_ankle_z=%.3f L_toe_z=%.3f'
      % (HIPS_REST.z, STANCE['Left']['Foot'].z, STANCE['Left']['ToeBase'].z))

# ── EXACT analytic leg IK. Coordinate descent kept finding local minima
# (5 DOF -> 2cm sink, 7 DOF -> 8cm sink: more freedom, worse basin). A leg
# is a TWO-BONE CHAIN, so the knee is law-of-cosines and each bone can be
# aimed exactly. Zero residual by construction, no search.
def aim_bone(pb, desired_world_dir):
    """Rotate pb so its axis points along desired_world_dir. Uses the
    bone's LIVE matrix (posed parents included) via pose = M0^-1 D M0 —
    the same conjugation that killed the stale-rest-frame bugs."""
    R = mw.to_3x3()
    Ri = R.inverted()
    pb.rotation_quaternion = Quaternion()
    bpy.context.view_layer.update()
    cur = (Ri @ ((mw @ pb.tail) - (mw @ pb.head))).normalized()
    des = (Ri @ Vector(desired_world_dir)).normalized()
    D = cur.rotation_difference(des)
    M0 = pb.matrix.to_quaternion()
    pb.rotation_quaternion = M0.inverted() @ D @ M0
    bpy.context.view_layer.update()

FOOT_LEN = {s: (STANCE[s]['ToeBase'] - STANCE[s]['Foot']).length
            for s in ('Left', 'Right')}
THIGH = {s: (STANCE[s]['Leg'] - STANCE[s]['UpLeg']).length
         for s in ('Left', 'Right')}
SHIN = {s: (STANCE[s]['Foot'] - STANCE[s]['Leg']).length
        for s in ('Left', 'Right')}

def solve_leg(side, hips_off_cm, contact='Foot', target=None,
              extra_body=None, iters=0):
    U, L, F = side + 'UpLeg', side + 'Leg', side + 'Foot'
    T = side + 'ToeBase'
    a, b = THIGH[side], SHIN[side]
    toe_t = STANCE[side]['ToeBase']

    for pb in arm.pose.bones:
        pb.rotation_quaternion = Quaternion()
        pb.location = (0, 0, 0)
    if extra_body:
        set_pose(extra_body)
    hb = arm.pose.bones['Hips']
    hb.location = local_loc(hb, Vector((0, 0, hips_off_cm)))
    bpy.context.view_layer.update()

    H = mw @ arm.pose.bones[U].head
    if contact == 'ToeBase':
        # heel LIFTS: park the ankle one foot-length up-and-behind the
        # planted toe, which IS plantar flexion
        ank_t = toe_t + FOOT_LEN[side] * Vector((0, 0.32, 1)).normalized()
    else:
        ank_t = STANCE[side]['Foot'] if target is None else target

    to_a = ank_t - H
    d = to_a.length
    d = max(abs(a - b) + 1e-4, min(a + b - 1e-4, d))
    along = to_a.normalized()
    cos_al = max(-1.0, min(1.0, (a * a + d * d - b * b) / (2 * a * d)))
    al = math.acos(cos_al)
    pole = Vector((0, -1, 0))                     # she faces -Y: knee leads
    perp = pole - along * pole.dot(along)
    if perp.length < 1e-5:
        perp = Vector((0, 0, 1)) - along * along.z
    perp.normalize()
    knee_t = H + a * (math.cos(al) * along + math.sin(al) * perp)

    aim_bone(arm.pose.bones[U], knee_t - H)
    knee_now = mw @ arm.pose.bones[L].head
    aim_bone(arm.pose.bones[L], ank_t - knee_now)
    ank_now = mw @ arm.pose.bones[F].head
    aim_bone(arm.pose.bones[F], toe_t - ank_now)

    got = mw @ arm.pose.bones[side + contact].head
    tgt = toe_t if contact == 'ToeBase' else ank_t
    dist = (got - tgt).length
    return ({U: ('quat', arm.pose.bones[U].rotation_quaternion.copy()),
             L: ('quat', arm.pose.bones[L].rotation_quaternion.copy()),
             F: ('quat', arm.pose.bones[F].rotation_quaternion.copy())}, dist)


# ═══════════════ 3. BALLISTIC ARC ═══════════════
G = 9.81
JUMP_H = 0.34                     # metres of hip rise
TAKEOFF_F, LAND_F = 40, 74        # ground-contact frames
V0 = math.sqrt(2 * G * JUMP_H)
T_UP = V0 / G
print('BALLISTIC h=%.2fm v0=%.2fm/s t_apex=%.3fs (%.1f frames) '
      'flight=%d frames' % (JUMP_H, V0, T_UP, T_UP * FPS, LAND_F - TAKEOFF_F))

TAKEOFF_OFF = 7.0                 # cm: extended + on the toes
LAND_OFF = 3.0

def ballistic_cm(f):
    """Root height offset (cm) at frame f during flight."""
    t = (f - TAKEOFF_F) / FPS
    z = V0 * t - 0.5 * G * t * t          # metres above takeoff
    return TAKEOFF_OFF + z * 100.0

# ═══════════════ the poses ═══════════════
STAND = {}

CROUCH_BODY = {
    'Spine02': [(X, 8)], 'Spine01': [(X, 10)], 'Spine': [(X, 9)],
    'LeftShoulder': [(Y, -6)], 'RightShoulder': [(Y, 6)],
    'LeftArm': ('axis', tuple(AX['LeftArm']), -34),
    'RightArm': ('axis', tuple(AX['RightArm']), -34),
    'LeftForeArm': ('axis', tuple(AX['LeftForeArm']), 26),
    'RightForeArm': ('axis', tuple(AX['RightForeArm']), 26),
    'neck': [(X, -4)], 'Head': [(X, -7)],
    'WingL_root': [(Y, -26)], 'WingR_root': [(Y, 26)],
    'WingL_tip': [(Y, -34)], 'WingR_tip': [(Y, 34)],
}
# the FLAP: swept hard down. Fires after she's already left the ground, so
# it visibly contributes nothing — a vestigial demon's wings.
FLAP_DOWN = {
    'WingL_root': [(Y, -62)], 'WingR_root': [(Y, 62)],
    'WingL_tip': [(Y, -78)], 'WingR_tip': [(Y, 78)],
}
LAUNCH_BODY = {
    'Spine02': [(X, -4)], 'Spine01': [(X, -5)], 'Spine': [(X, -6)],
    'LeftShoulder': [(Y, 7)], 'RightShoulder': [(Y, -7)],
    'LeftArm': [('L', tuple(AX['LeftArm']), 78), (Y, -14)],
    'RightArm': [('L', tuple(AX['RightArm']), 78), (Y, 14)],
    'LeftForeArm': ('axis', tuple(AX['LeftForeArm']), 8),
    'RightForeArm': ('axis', tuple(AX['RightForeArm']), 8),
    'neck': [(X, -6)], 'Head': [(X, -10)],
}
AIR_BODY = dict(LAUNCH_BODY)
AIR_BODY.update({
    'Spine02': [(X, 2)], 'Spine01': [(X, 3)], 'Spine': [(X, 2)],
    # wings FLARE at apex — and it does not help. Vestigial by design.
    'WingL_root': [(Y, 46)], 'WingR_root': [(Y, -46)],
    'WingL_tip': [(Y, 40)], 'WingR_tip': [(Y, -40)],
})
ABSORB_BODY = {
    'Spine02': [(X, 12)], 'Spine01': [(X, 14)], 'Spine': [(X, 12)],
    'LeftShoulder': [(Y, -4)], 'RightShoulder': [(Y, 4)],
    'LeftArm': ('axis', tuple(AX['LeftArm']), -20),
    'RightArm': ('axis', tuple(AX['RightArm']), -20),
    'LeftForeArm': ('axis', tuple(AX['LeftForeArm']), 42),
    'RightForeArm': ('axis', tuple(AX['RightForeArm']), 42),
    'neck': [(X, 6)], 'Head': [(X, 8)],
    'WingL_root': [(Y, -22)], 'WingR_root': [(Y, 22)],
    'WingL_tip': [(Y, -28)], 'WingR_tip': [(Y, 28)],
}

# solve the planted phases
print('solving planted legs...')
LEGS = {}
LEGS['stand'] = ({}, 0.0)
for tag, off, contact, body in (
        ('crouch', -19.0, 'Foot', CROUCH_BODY),
        ('midlaunch', -6.0, 'ToeBase', LAUNCH_BODY),
        ('contact', LAND_OFF, 'ToeBase', ABSORB_BODY),
        ('absorb', -18.0, 'Foot', ABSORB_BODY)):
    pose = {}
    worst = 0.0
    for side in ('Left', 'Right'):
        p, c = solve_leg(side, off, contact, None, body)
        pose.update(p)
        worst = max(worst, c)
    LEGS[tag] = (pose, worst)
    print('  IK[%-9s] hips%+6.1fcm contact=%-8s foot_error=%.4fm %s'
          % (tag, off, contact, worst,
             'PLANTED' if worst < 0.015 else 'SLIPPING'))

# airborne legs: free — a tuck, then reaching for the ground
TUCK = {
    'LeftUpLeg': ('axis', tuple(AX['LeftUpLeg']), 34),
    'RightUpLeg': ('axis', tuple(AX['RightUpLeg']), 30),
    'LeftLeg': ('axis', tuple(AX['LeftLeg']), 46),
    'RightLeg': ('axis', tuple(AX['RightLeg']), 42),
    'LeftFoot': ('axis', tuple(AX['LeftFoot']), -26),
    'RightFoot': ('axis', tuple(AX['RightFoot']), -26),
}
REACH = {
    'LeftUpLeg': ('axis', tuple(AX['LeftUpLeg']), 10),
    'RightUpLeg': ('axis', tuple(AX['RightUpLeg']), 8),
    'LeftLeg': ('axis', tuple(AX['LeftLeg']), 12),
    'RightLeg': ('axis', tuple(AX['RightLeg']), 10),
    'LeftFoot': ('axis', tuple(AX['LeftFoot']), -18),
    'RightFoot': ('axis', tuple(AX['RightFoot']), -18),
}
EXTEND = {
    'LeftUpLeg': ('axis', tuple(AX['LeftUpLeg']), -6),
    'RightUpLeg': ('axis', tuple(AX['RightUpLeg']), -6),
    'LeftLeg': ('axis', tuple(AX['LeftLeg']), 2),
    'RightLeg': ('axis', tuple(AX['RightLeg']), 2),
    'LeftFoot': ('axis', tuple(AX['LeftFoot']), -34),   # pointed toes
    'RightFoot': ('axis', tuple(AX['RightFoot']), -34),
}

# ═══════════════ component tracks ═══════════════
COMP = {
    'root':  ['HIPS_LOC'],
    'legs':  ['LeftUpLeg', 'LeftLeg', 'LeftFoot',
              'RightUpLeg', 'RightLeg', 'RightFoot'],
    'toes':  ['LeftToeBase', 'RightToeBase'],
    'spine': ['Spine', 'Spine01', 'Spine02'],
    'arms':  ['LeftShoulder', 'LeftArm', 'LeftForeArm',
              'RightShoulder', 'RightArm', 'RightForeArm'],
    'head':  ['neck', 'Head'],
    'wings': ['WingL_root', 'WingL_tip', 'WingR_root', 'WingR_tip'],
}

def key_comp(frame, comp, pose, blend=1.0):
    for b in COMP[comp]:
        spec = pose.get(b) if pose else None
        if b == 'HIPS_LOC':
            pb = arm.pose.bones['Hips']
            pb.location = local_loc(pb, Vector(spec) * blend) if spec \
                else Vector((0, 0, 0))
            pb.keyframe_insert('location', frame=frame)
            continue
        pb = arm.pose.bones.get(b)
        if pb is None:
            continue
        pb.rotation_quaternion = spec_quat(pb, spec, blend) if spec \
            else Quaternion()
        pb.keyframe_insert('rotation_quaternion', frame=frame)

for pb in arm.pose.bones:
    pb.rotation_quaternion = Quaternion()
    pb.location = (0, 0, 0)
arm.animation_data_clear()

FRAMES = 150
for c in COMP:
    key_comp(1, c, None)

R = lambda z: {'HIPS_LOC': (0, 0, z)}

# ── ROOT: computed, not felt. Ballistic between takeoff and landing. ──
key_comp(8, 'root', R(0))
key_comp(30, 'root', R(-19))          # loaded crouch
# the root MUST pass through the exact height each IK plant was solved at,
# or the foot is planted for a pose she is not in
key_comp(TAKEOFF_F - 4, 'root', R(-6))
key_comp(TAKEOFF_F, 'root', R(TAKEOFF_OFF))
for f in range(TAKEOFF_F + 2, LAND_F, 2):
    key_comp(f, 'root', R(ballistic_cm(f)))
key_comp(LAND_F, 'root', R(LAND_OFF))
key_comp(LAND_F + 12, 'root', R(-18))  # absorb
key_comp(LAND_F + 34, 'root', R(-2))
key_comp(LAND_F + 52, 'root', R(0))

# ── ARMS lead: they swing back BEFORE the legs finish loading, and swing
# UP before the feet leave (real jumps borrow ~10% of height from arm
# swing — the arms are AHEAD of the legs).
key_comp(10, 'arms', STAND)
key_comp(26, 'arms', CROUCH_BODY)      # back-swing arrives early
key_comp(TAKEOFF_F - 4, 'arms', LAUNCH_BODY)   # up BEFORE takeoff
key_comp(52, 'arms', AIR_BODY)
key_comp(LAND_F, 'arms', AIR_BODY)
key_comp(LAND_F + 10, 'arms', ABSORB_BODY)
key_comp(LAND_F + 40, 'arms', STAND)

# ── LEGS: the engine. IK-solved while planted, free while airborne. ──
key_comp(10, 'legs', LEGS['stand'][0])
key_comp(30, 'legs', LEGS['crouch'][0])
key_comp(TAKEOFF_F - 4, 'legs', LEGS['midlaunch'][0])
key_comp(TAKEOFF_F, 'legs', EXTEND)               # snapped straight
key_comp(TAKEOFF_F + 10, 'legs', TUCK)            # tuck after leaving
key_comp(56, 'legs', TUCK)
key_comp(LAND_F - 6, 'legs', REACH)               # reaching for the floor
key_comp(LAND_F, 'legs', LEGS['contact'][0])
key_comp(LAND_F + 12, 'legs', LEGS['absorb'][0])
key_comp(LAND_F + 40, 'legs', LEGS['stand'][0])

# ── TOES: last to leave, first to touch. This is the jump's signature. ──
TOE_OFF = {'LeftToeBase': [(X, 42)], 'RightToeBase': [(X, 42)]}
TOE_POINT = {'LeftToeBase': [(X, -14)], 'RightToeBase': [(X, -14)]}
TOE_STRIKE = {'LeftToeBase': [(X, 26)], 'RightToeBase': [(X, 26)]}
key_comp(30, 'toes', None)
key_comp(TAKEOFF_F, 'toes', TOE_OFF)              # push-off
key_comp(TAKEOFF_F + 8, 'toes', TOE_POINT)        # relax, pointed
key_comp(LAND_F - 4, 'toes', TOE_STRIKE)          # reaching, ball-first
key_comp(LAND_F + 6, 'toes', None)                # heel comes down
key_comp(LAND_F + 40, 'toes', None)

# ── SPINE: folds to load, extends through launch, folds again to absorb ─
key_comp(12, 'spine', STAND)
key_comp(30, 'spine', CROUCH_BODY)
key_comp(TAKEOFF_F + 2, 'spine', LAUNCH_BODY)     # extension trails the arms
key_comp(54, 'spine', AIR_BODY)
key_comp(LAND_F + 6, 'spine', ABSORB_BODY)        # fold on impact
key_comp(LAND_F + 44, 'spine', STAND)

# ── HEAD: leads UP on launch (you look where you're going), and is the
# LAST thing to settle after landing.
key_comp(14, 'head', STAND)
key_comp(28, 'head', CROUCH_BODY)
key_comp(TAKEOFF_F - 6, 'head', LAUNCH_BODY)      # looks up first
key_comp(56, 'head', AIR_BODY)
key_comp(LAND_F + 8, 'head', ABSORB_BODY)
key_comp(LAND_F + 50, 'head', STAND)              # settles last

# ── WINGS: react LATE and don't help. She can't fly; the arc is legs.
key_comp(20, 'wings', STAND)
key_comp(34, 'wings', CROUCH_BODY)                # drawn in, loading
key_comp(TAKEOFF_F + 4, 'wings', CROUCH_BODY)     # LATE — still folded at liftoff
key_comp(TAKEOFF_F + 13, 'wings', FLAP_DOWN)      # the flap, far too late to help
key_comp(60, 'wings', AIR_BODY)                   # flare/glide at apex
key_comp(LAND_F + 4, 'wings', AIR_BODY)
key_comp(LAND_F + 14, 'wings', ABSORB_BODY)       # fold on impact
key_comp(LAND_F + 46, 'wings', STAND)

ad = arm.animation_data
if ad and ad.action:
    a = ad.action
    cs = ([a.fcurves] if hasattr(a, 'fcurves')
          else [cb.fcurves for L in a.layers for s in L.strips
                for cb in s.channelbags])
    nc = nm_ = 0
    for fcs in cs:
        for fc in fcs:
            kps = fc.keyframe_points
            last = len(kps) - 1
            # the ballistic root must stay LINEAR-ish in velocity, so its
            # pass-through keys get AUTO (bezier eases would flatten the
            # arc at every sample and re-introduce apex float)
            for i, kp in enumerate(kps):
                kp.interpolation = 'BEZIER'
                if i == 0 or i == last:
                    kp.handle_left_type = kp.handle_right_type = 'AUTO_CLAMPED'
                    nc += 1
                else:
                    kp.handle_left_type = kp.handle_right_type = 'AUTO'
                    nm_ += 1
    print('HANDLES %d clamped, %d smooth' % (nc, nm_))
scene.frame_start, scene.frame_end = 1, FRAMES

# ═══════════════ audit: does she actually leave the ground, and do her
# feet stay planted while they should? ═══════════════
print('--- ground truth audit ---')
prev = None
for f in (1, 30, TAKEOFF_F - 4, TAKEOFF_F, 48, 56, 64, LAND_F, LAND_F + 12,
          LAND_F + 40, FRAMES):
    scene.frame_set(f)
    lo = min((mesh.matrix_world @ (mesh.evaluated_get(
        bpy.context.evaluated_depsgraph_get()).data.vertices[v.index].co))
        .z for v in mesh.data.vertices)
    hips = (mw @ arm.pose.bones['Hips'].head).z
    lt = (mw @ arm.pose.bones['LeftToeBase'].head).z
    print('  f%-3d hips=%.3f lowest_vert=%+.4f left_toe=%.4f' % (f, hips, lo, lt))

# ═══════════════ render ═══════════════
scene.frame_set(1)
bpy.context.view_layer.update()
deps = bpy.context.evaluated_depsgraph_get()
lo_b, hi_b = Vector((1e9,) * 3), Vector((-1e9,) * 3)
eo = mesh.evaluated_get(deps)
for c in eo.bound_box:
    wc = eo.matrix_world @ Vector(c)
    for i in range(3):
        lo_b[i], hi_b[i] = min(lo_b[i], wc[i]), max(hi_b[i], wc[i])
# frame for the WHOLE jump: extra headroom above, floor at the bottom
center = Vector(((lo_b.x + hi_b.x) / 2, (lo_b.y + hi_b.y) / 2,
                 (lo_b.z + hi_b.z) / 2 + 0.22))
size = max(hi_b - lo_b) * 1.30

ground = bpy.data.meshes.new('gp')
import bmesh as _bm
_b = _bm.new()
_bm.ops.create_grid(_b, x_segments=1, y_segments=1, size=6)
_b.to_mesh(ground)
_b.free()
gobj = bpy.data.objects.new('Ground', ground)
scene.collection.objects.link(gobj)
gmat = bpy.data.materials.new('gm')
gmat.use_nodes = True
gmat.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.16, 0.15, 0.18, 1)
ground.materials.append(gmat)

for nm, off, e, col in (('K', Vector((-1, -1.2, 1.4)), 2.4, (1.0, 0.96, 0.92)),
                        ('F', Vector((1.3, -0.9, 0.4)), 0.9, (0.82, 0.87, 1.0)),
                        ('R', Vector((0.2, 1.3, 0.7)), 0.6, (0.9, 0.9, 1.0))):
    d = bpy.data.lights.new(nm, 'SUN')
    d.energy, d.color, d.angle = e, col, math.radians(9)
    o = bpy.data.objects.new(nm, d)
    o.location = center + off * size
    o.rotation_euler = (center - o.location).to_track_quat('-Z', 'Y').to_euler()
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
cam_data.lens = 50
cam = bpy.data.objects.new('C', cam_data)
scene.collection.objects.link(cam)
scene.camera = cam
HERO = Vector((0.85, -1.3, 0.16)).normalized()
cam.location = center + HERO * size * 1.75
cam.rotation_euler = (center - cam.location).to_track_quat('-Z', 'Y').to_euler()

if '--grid' in ARGS:
    scene.render.resolution_x, scene.render.resolution_y = 430, 560
    fr = sorted({max(1, min(FRAMES, round(1 + (FRAMES - 1) * i / 11)))
                 for i in range(12)})
    gm = []
    for i, f in enumerate(fr):
        scene.frame_set(f)
        scene.render.filepath = OUT + '\\jump_%02d.png' % (i + 1)
        bpy.ops.render.render(write_still=True)
        gm.append({'index': i + 1, 'frame': f, 'time': round((f - 1) / FPS, 3)})
    with open(OUT + '\\jump_manifest.json', 'w') as fh:
        json.dump({'samples': gm}, fh)
    print('GRID rendered')

if '--full' in ARGS:
    scene.render.resolution_x, scene.render.resolution_y = 640, 760
    scene.render.filepath = OUT + '\\jumpfull_'
    bpy.ops.render.render(animation=True)
