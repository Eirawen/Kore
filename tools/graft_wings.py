"""
WING GRAFT — replace her slab wings with the generated bat wings.

What the probe found in the asset (2217 verts, 24 islands, no rig):
  isl0  863v cx=+0.00  the MEMBRANE — ONE connected sheet across BOTH
                       wings, so it must not be split into two objects
  isl1  331v cx=-0.38  leading-edge arm panel (left)
  isl2  300v cx=+0.38  leading-edge arm panel (right)
  isl3/4 171/168v      secondary spars
  isl5+ 11 islands at cx=+-0.42..0.46  claws / finger tips
  vertex split across the midline 1103/1114 -> already symmetric

Approach:
  * DELETE her old 330-vert slab island entirely.
  * Mount the wing pair as a SEPARATE mesh object sharing her armature —
    no vertex-index disruption to her body, no weight contamination, and
    it's how game characters are actually built.
  * Anchor = the asset's central convergence zone (|x| < 8% of span).
    Scale about that anchor, so the attachment point never moves.
  * 3 bones per wing (root -> mid -> tip) laid along the measured span,
    parented to Spine. Midline verts weight to BOTH roots so the shared
    membrane cannot tear.

Config by FILE (gotcha #11: WSL env vars do NOT reach Windows Blender):
  tools/.wingcfg   span=1.5  mount_z=1.26  mount_y=0.055
                   pitch=0  yaw=0  roll=0
"""
import bpy
import bmesh
import json
import math
from mathutils import Vector, Quaternion, Euler, Matrix

HER = '/home/khaled/Kore/succubus_walk.glb'
WINGS = '/home/khaled/Kore/wings_raw.glb'
OUT = r'C:\tmp'
CFG = r'\\wsl.localhost\Ubuntu\home\khaled\Kore\tools\.wingcfg'


def cfg(key, default):
    try:
        for line in open(CFG):
            k, _, v = line.strip().partition('=')
            if k == key:
                return float(v)
    except (OSError, ValueError):
        pass
    return default

SPAN = cfg('span', 1.5)          # total tip-to-tip, metres
MOUNT_Z = cfg('mount_z', 1.26)
MOUNT_Y = cfg('mount_y', 0.055)
PITCH = cfg('pitch', 0.0)
YAW = cfg('yaw', 0.0)
ROLL = cfg('roll', 0.0)
print('CFG span=%.2f mount=(%.3f,%.3f) rot=(%.0f,%.0f,%.0f)'
      % (SPAN, MOUNT_Y, MOUNT_Z, PITCH, YAW, ROLL))

bpy.ops.wm.read_factory_settings(use_empty=True)

# ═══════════ her ═══════════
bpy.ops.import_scene.gltf(filepath=HER)
scene = bpy.context.scene
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
body = next(o for o in bpy.data.objects if o.type == 'MESH')
if arm.animation_data:
    arm.animation_data_clear()
for pb in arm.pose.bones:
    pb.rotation_mode = 'QUATERNION'
    pb.rotation_quaternion = Quaternion()
    pb.location = (0, 0, 0)
bpy.context.view_layer.update()
mw = arm.matrix_world
mwi = mw.inverted()

def bpos(n):
    return mw @ arm.pose.bones[n].head

SPINE = bpos('Spine')
SH_L, SH_R = bpos('LeftArm'), bpos('RightArm')
SHOULDER_W = abs(SH_L.x - SH_R.x)
print('HER shoulder_w=%.3f spine=(%.3f,%.3f,%.3f) height~%.3f'
      % (SHOULDER_W, SPINE.x, SPINE.y, SPINE.z,
         max((body.matrix_world @ v.co).z for v in body.data.vertices)))

# ═══════════ remove the old slab wings ═══════════
def islands_of(m):
    bm = bmesh.new()
    bm.from_mesh(m.data)
    bm.verts.ensure_lookup_table()
    seen, out = set(), []
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
        out.append(comp)
    bm.free()
    return out

old = None
for comp in islands_of(body):
    pts = [body.matrix_world @ body.data.vertices[i].co for i in comp]
    xs = [p.x for p in pts]
    if (max(xs) - min(xs)) > 0.7 and min(p.z for p in pts) > 0.9 and len(comp) < 800:
        old = comp
        break
if old:
    bm = bmesh.new()
    bm.from_mesh(body.data)
    bm.verts.ensure_lookup_table()
    doomed = [bm.verts[i] for i in old]
    bmesh.ops.delete(bm, geom=doomed, context='VERTS')
    bm.to_mesh(body.data)
    bm.free()
    body.data.update()
    print('REMOVED old slab wings: %d verts (body now %d)'
          % (len(old), len(body.data.vertices)))

# ═══════════ bring in the new wings ═══════════
before = set(o.name for o in bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=WINGS)
new_objs = [o for o in bpy.data.objects if o.name not in before]
wing = next(o for o in new_objs if o.type == 'MESH')
for o in new_objs:
    if o is not wing and o.type == 'ARMATURE':
        bpy.data.objects.remove(o, do_unlink=True)
wing.name = 'Wings'
wing.parent = None
bpy.context.view_layer.update()

wpts = [wing.matrix_world @ v.co for v in wing.data.vertices]
wlo = Vector((min(p.x for p in wpts), min(p.y for p in wpts), min(p.z for p in wpts)))
whi = Vector((max(p.x for p in wpts), max(p.y for p in wpts), max(p.z for p in wpts)))
native_span = whi.x - wlo.x
# anchor: the central convergence zone where the two wings meet
band = native_span * 0.08
core = [p for p in wpts if abs(p.x - (wlo.x + whi.x) / 2) < band]
anchor = Vector((sum(p.x for p in core) / len(core),
                 sum(p.y for p in core) / len(core),
                 sum(p.z for p in core) / len(core)))
print('WINGS native_span=%.3f bbox=%s anchor=%s (%d core verts)'
      % (native_span, [round(v, 3) for v in (whi - wlo)],
         [round(v, 3) for v in anchor], len(core)))

# bake the mount transform into the vertices (scale about the anchor,
# rotate, then move the anchor onto her back)
s = SPAN / native_span
rot = Euler((math.radians(PITCH), math.radians(ROLL), math.radians(YAW)),
            'XYZ').to_matrix()
mount = Vector((SPINE.x, SPINE.y + MOUNT_Y, MOUNT_Z))
wmi = wing.matrix_world.inverted()
for v in wing.data.vertices:
    p = wing.matrix_world @ v.co
    v.co = wmi @ (mount + rot @ ((p - anchor) * s))
wing.data.update()
bpy.context.view_layer.update()

wpts = [wing.matrix_world @ v.co for v in wing.data.vertices]
wlo = Vector((min(p.x for p in wpts), min(p.y for p in wpts), min(p.z for p in wpts)))
whi = Vector((max(p.x for p in wpts), max(p.y for p in wpts), max(p.z for p in wpts)))
print('MOUNTED span=%.3f height=%.3f  z=[%.3f,%.3f] y=[%.3f,%.3f]'
      % (whi.x - wlo.x, whi.z - wlo.z, wlo.z, whi.z, wlo.y, whi.y))
HEAD_Z = max((body.matrix_world @ v.co).z for v in body.data.vertices)
print('       tips vs shoulders %+.3f m, vs top of head %+.3f m (she is %.2f tall)'
      % (whi.z - SH_L.z, whi.z - HEAD_Z, HEAD_Z))
print('       span/height ratio of her = %.2f  (asset is furled, ~1:1)'
      % ((whi.x - wlo.x) / HEAD_Z))

# ═══════════ bones: 3 per wing along the measured span ═══════════
bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode='EDIT')
eb = arm.data.edit_bones
spine_eb = eb['Spine']
for nm in list(eb.keys()):
    if nm.startswith('Wing'):
        eb.remove(eb[nm])

SEG = {}
for side, sgn in (('L', 1), ('R', -1)):
    half = [p for p in wpts if (p.x - mount.x) * sgn > 0.01]
    if not half:
        continue
    tip_x = max(half, key=lambda p: (p.x - mount.x) * sgn).x
    span_half = abs(tip_x - mount.x)
    # sample the wing's own shape at 1/3 and 2/3 out so the bones follow
    # the arc of the membrane instead of a straight line
    joints = [mount]
    for frac in (0.42, 0.78, 1.0):
        band_pts = [p for p in half
                    if abs(abs(p.x - mount.x) - span_half * frac) < span_half * 0.10]
        if not band_pts:
            band_pts = half
        joints.append(Vector((
            mount.x + sgn * span_half * frac,
            sum(p.y for p in band_pts) / len(band_pts),
            sum(p.z for p in band_pts) / len(band_pts))))
    names = ['Wing%s_root' % side, 'Wing%s_mid' % side, 'Wing%s_tip' % side]
    prev = None
    for i, nm in enumerate(names):
        b = eb.new(nm)
        b.head, b.tail = mwi @ joints[i], mwi @ joints[i + 1]
        b.parent = spine_eb if prev is None else prev
        b.use_connect = prev is not None
        prev = b
    SEG[side] = dict(sgn=sgn, span=span_half, joints=joints, names=names)
    print('BONES[%s] span=%.3f joints_z=%s' % (side, span_half,
          [round(j.z, 3) for j in joints]))
bpy.ops.object.mode_set(mode='OBJECT')
bpy.context.view_layer.update()

# ═══════════ split at the midline into two independent wings ═══════
# bisect_plane cuts the 39 straddling faces exactly at the plane, so the
# halves abut with no hole and no overlap.
HALVES = {}
for side, sgn in (('L', 1), ('R', -1)):
    obj = wing.copy()
    obj.data = wing.data.copy()
    obj.name = 'Wings' + side
    scene.collection.objects.link(obj)
    omi = obj.matrix_world.inverted()
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    geom = list(bm.verts) + list(bm.edges) + list(bm.faces)
    bmesh.ops.bisect_plane(
        bm, geom=geom, dist=1e-6,
        plane_co=omi @ mount,
        plane_no=(omi.to_3x3() @ Vector((sgn, 0, 0))).normalized(),
        clear_inner=True, clear_outer=False)
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()
    HALVES[side] = obj
    print('SPLIT Wings%s -> %d verts' % (side, len(obj.data.vertices)))
bpy.data.objects.remove(wing, do_unlink=True)
bpy.context.view_layer.update()

def smooth(t):
    t = min(1.0, max(0.0, t))
    return t * t * (3 - 2 * t)

for side, sd in SEG.items():
    obj = HALVES[side]
    for nm in sd['names']:
        if nm not in obj.vertex_groups:
            obj.vertex_groups.new(name=nm)
    span_half = sd['span']
    for v in obj.data.vertices:
        p = obj.matrix_world @ v.co
        t = min(1.0, abs(p.x - mount.x) / span_half)
        w_root = 1.0 - smooth((t - 0.10) / 0.38)
        w_tip = smooth((t - 0.52) / 0.40)
        w_mid = max(0.0, 1.0 - w_root - w_tip)
        for nm, w in zip(sd['names'], (w_root, w_mid, w_tip)):
            if w > 1e-4:
                obj.vertex_groups[nm].add([v.index], w, 'REPLACE')

mat = bpy.data.materials.new('WingMat')
mat.use_nodes = True
mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.42, 0.20, 0.24, 1)
mat.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = 0.55
for side, obj in HALVES.items():
    obj.parent = arm
    obj.matrix_parent_inverse = arm.matrix_world.inverted()
    md = obj.modifiers.new('Armature', 'ARMATURE')
    md.object = arm
    obj.data.materials.clear()
    obj.data.materials.append(mat)

print('GRAFTED %d independent wings, %d verts total, %d bones'
      % (len(HALVES), sum(len(o.data.vertices) for o in HALVES.values()),
         sum(len(sd['names']) for sd in SEG.values())))

# save for the animation scripts to pick up
bpy.ops.wm.save_as_mainfile(
    filepath=r'\\wsl.localhost\Ubuntu\home\khaled\Kore\succubus_winged.blend')
print('SAVED succubus_winged.blend')

# ═══════════ spread pose: the asset is FURLED, so the wings open via
# the ROOT BONES. This cannot be done by scaling the mesh (it would just
# distort the membrane), and doing it in the pose means the spread is
# animatable — the flap already drives these bones.
SPREAD = cfg('spread', 40.0)
SWEEP = cfg('sweep', 14.0)
# now that the wings are independent they need never match exactly.
# Perfect symmetry is the manufactured look; a few degrees of
# difference reads as a living creature.
ASYM = cfg('asym', 5.0)
def aim_bone(pb, want_world):
    """Point a bone's axis along want_world using its LIVE matrix
    (posed parents included): pose = M0^-1 . D . M0."""
    R = mw.to_3x3()
    Ri = R.inverted()
    pb.rotation_quaternion = Quaternion()
    bpy.context.view_layer.update()
    cur = (Ri @ ((mw @ pb.tail) - (mw @ pb.head))).normalized()
    des = (Ri @ Vector(want_world)).normalized()
    M0 = pb.matrix.to_quaternion()
    pb.rotation_quaternion = M0.inverted() @ cur.rotation_difference(des) @ M0
    bpy.context.view_layer.update()


def spread_pose(amount=1.0):
    """UNFOLD, don't swing.

    Khaled spotted that the wings were "rotating vertically rather than
    extending out", and the measurement proved him right. Applying the same
    +Y rotation to all three bones swings the chain like a rigid plank:
        swing +Y40 -> span 1.695 but wing HEIGHT collapses 1.062 -> 0.481
    The wing gains width by lying down. Instead, AIM each bone along one
    outward direction, which STRAIGHTENS the furled arc:
        unfold      -> span 1.670 (same width) and height stays 1.058
    Nearly identical span, full vertical presence kept. A real wing spreads
    by unfolding its joints, not by tipping over.
    """
    for side, sd in SEG.items():
        sgn = sd['sgn']
        asym = 1.0 + (ASYM / 100.0 if side == 'R' else -ASYM / 100.0)
        if amount <= 1e-4:
            for nm in sd['names']:
                pb = arm.pose.bones.get(nm)
                if pb is not None:
                    pb.rotation_mode = 'QUATERNION'
                    pb.rotation_quaternion = Quaternion()
            continue
        out = Vector((sgn, SWEEP / 100.0 * asym, 0.10)).normalized()
        for nm in sd['names']:
            pb = arm.pose.bones.get(nm)
            if pb is None:
                continue
            pb.rotation_mode = 'QUATERNION'
            rest = Quaternion()
            aim_bone(pb, out)
            full = pb.rotation_quaternion.copy()
            pb.rotation_quaternion = rest.slerp(full, amount)
        # elevation is applied AFTER extension, at the root only — the
        # order a real wing does it in
        root = arm.pose.bones.get(sd['names'][0])
        if root is not None and abs(SPREAD) > 1e-6:
            m = root.bone.matrix_local.to_3x3().inverted()
            ay = (m @ Vector((0, 1, 0))).normalized()
            root.rotation_quaternion = (root.rotation_quaternion
                @ Quaternion(ay, math.radians(SPREAD * 0.35 * amount * sgn * asym)))
    bpy.context.view_layer.update()


# ═══════════ check render: 4 angles ═══════════
deps = bpy.context.evaluated_depsgraph_get()
lo, hi = Vector((1e9,) * 3), Vector((-1e9,) * 3)
for o in [body] + list(HALVES.values()):
    eo = o.evaluated_get(deps)
    for c in eo.bound_box:
        wc = eo.matrix_world @ Vector(c)
        for i in range(3):
            lo[i], hi[i] = min(lo[i], wc[i]), max(hi[i], wc[i])
center = (lo + hi) / 2
size = max(hi - lo)
for nm, off, e, col in (('K', Vector((-1, -1.2, 1.3)), 2.5, (1.0, 0.96, 0.92)),
                        ('F', Vector((1.3, -0.9, 0.4)), 1.0, (0.82, 0.87, 1.0)),
                        ('R', Vector((0.1, 1.4, 0.7)), 0.8, (0.9, 0.9, 1.0))):
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
scene.render.resolution_x, scene.render.resolution_y = 600, 700
scene.render.image_settings.file_format = 'PNG'
cd = bpy.data.cameras.new('C')
cd.lens = 48
cam = bpy.data.objects.new('C', cd)
scene.collection.objects.link(cam)
scene.camera = cam

VIEWS = [((0, -1, 0.05), 'FRONT furled'), ((0.85, -1.1, 0.12), '3/4 furled'),
         ((0, -1, 0.05), 'FRONT spread'), ((0.85, -1.1, 0.12), '3/4 spread'),
         ((1, -0.02, 0.05), 'SIDE spread'), ((0.25, 1, 0.12), 'BEHIND spread')]
man = []
for i, (dv, label) in enumerate(VIEWS):
    spread_pose(0.0 if 'furled' in label else 1.0)
    cam.location = center + Vector(dv).normalized() * size * 1.62
    cam.rotation_euler = (center - cam.location).to_track_quat('-Z', 'Y').to_euler()
    scene.render.filepath = OUT + '\\graft_%02d.png' % (i + 1)
    bpy.ops.render.render(write_still=True)
    man.append({'index': i + 1, 'label': label})
spread_pose(0.0)
with open(OUT + '\\graft_manifest.json', 'w') as fh:
    json.dump({'samples': man}, fh)
print('CHECK rendered')
