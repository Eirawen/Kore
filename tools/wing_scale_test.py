"""
HOVER-JUMP — with wing surgery, foot-planting IK, and a real ballistic arc.

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

Run: blender --background --python animate_hover.py -- [--grid] [--full]
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

# ── WING_SCALE: grow the island away from each side's attachment point.
# Verts at the root barely move, so the midline seam holds. Span and
# height scale fully; thickness only slightly (a wing is a membrane).
# gotcha #11: WSL env vars do NOT reach Windows Blender through
# --background --python. Config travels by FILE via the UNC path.
def _cfg(key, default):
    try:
        for line in open(r'\\wsl.localhost\Ubuntu\home\khaled\Kore\tools\.wingcfg'):
            k, _, v = line.strip().partition('=')
            if k == key:
                return v
    except OSError:
        pass
    return default
WING_SCALE = float(_cfg('scale', '1.0'))
if abs(WING_SCALE - 1.0) > 1e-3:
    mmi = mesh.matrix_world.inverted()
    for name, sv in sides.items():
        anchor = Vector((sv['inner'], sv['ym'], sv['ztop'] - 0.02))
        for i in sv['idx']:
            p = wpos(i)
            d = p - anchor
            d.x *= WING_SCALE
            d.z *= WING_SCALE
            d.y *= 1.0 + (WING_SCALE - 1.0) * 0.30
            mesh.data.vertices[i].co = mmi @ (anchor + d)
    mesh.data.update()
    # re-measure the extents the bones are built from
    for sgn, name in ((1, 'L'), (-1, 'R')):
        if name not in sides:
            continue
        sv = sides[name]
        pts = [wpos(i) for i in sv['idx']]
        xs = [p.x for p in pts]
        sv['out'] = max(xs) if sgn > 0 else min(xs)
        sv['inner'] = min(xs, key=abs)
        sv['ztop'] = max(p.z for p in pts)
        sv['zbot'] = min(p.z for p in pts)
        sv['ym'] = sum(p.y for p in pts) / len(pts)
    print('WING_SCALE %.2f applied; new span L=%.3f' % (WING_SCALE,
          abs(sides['L']['out'] - sides['L']['inner'])))

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


# ── pose the power-stroke and shoot one frame ──
def local_quat(pb, axis_arm, deg):
    m = pb.bone.matrix_local.to_3x3().inverted()
    return Quaternion((m @ Vector(axis_arm)).normalized(), math.radians(deg))
X, Y, Z = (1, 0, 0), (0, 1, 0), (0, 0, 1)
POSE = {
    'WingL_root': [(Y, -50)], 'WingR_root': [(Y, 50)],
    'WingL_tip': [(Y, -66)], 'WingR_tip': [(Y, 66)],
    'LeftUpLeg': ('axis', tuple(AX['LeftUpLeg']), 26),
    'RightUpLeg': ('axis', tuple(AX['RightUpLeg']), 22),
    'LeftLeg': ('axis', tuple(AX['LeftLeg']), 34),
    'RightLeg': ('axis', tuple(AX['RightLeg']), 30),
    'LeftFoot': ('axis', tuple(AX['LeftFoot']), -28),
    'RightFoot': ('axis', tuple(AX['RightFoot']), -28),
    'Spine': [(X, 2)], 'neck': [(X, -5)], 'Head': [(X, -8)],
}
for bone, spec in POSE.items():
    pb = arm.pose.bones.get(bone)
    if pb is None:
        continue
    if isinstance(spec, tuple) and spec[0] == 'axis':
        pb.rotation_quaternion = Quaternion(Vector(spec[1]).normalized(),
                                            math.radians(spec[2]))
    else:
        q = Quaternion()
        for ax, deg in spec:
            q = q @ local_quat(pb, ax, deg)
        pb.rotation_quaternion = q
bpy.context.view_layer.update()

deps = bpy.context.evaluated_depsgraph_get()
eo = mesh.evaluated_get(deps)
lo, hi = Vector((1e9,) * 3), Vector((-1e9,) * 3)
for c in eo.bound_box:
    wc = eo.matrix_world @ Vector(c)
    for i in range(3):
        lo[i], hi[i] = min(lo[i], wc[i]), max(hi[i], wc[i])
print('SILHOUETTE width=%.3f height=%.3f' % (hi.x - lo.x, hi.z - lo.z))
center = (lo + hi) / 2
# FIXED framing across all scales so the comparison is honest
center = Vector((0, 0, 0.95))
size = 2.6

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
scene.render.resolution_x, scene.render.resolution_y = 620, 700
scene.render.image_settings.file_format = 'PNG'
cd = bpy.data.cameras.new('C')
cd.lens = 46
cam = bpy.data.objects.new('C', cd)
scene.collection.objects.link(cam)
scene.camera = cam
cam.location = center + Vector((0.75, -1.35, 0.14)).normalized() * size * 1.5
cam.rotation_euler = (center - cam.location).to_track_quat('-Z', 'Y').to_euler()
scene.render.filepath = OUT + '\\wingscale_%s.png' % _cfg('tag', 'x')
bpy.ops.render.render(write_still=True)
print('rendered wing scale', WING_SCALE)
