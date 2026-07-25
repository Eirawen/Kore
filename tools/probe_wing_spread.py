"""Test Khaled's hypothesis: am I SWINGING the wing (rigid plank tipping
from vertical to horizontal) instead of EXTENDING it (joints unfolding,
arm sweeping out)? Measure candidate strategies, and report the per-side
island structure that an anatomical rig would use."""
import bpy, bmesh, json, math
from mathutils import Vector, Quaternion

bpy.ops.wm.open_mainfile(
    filepath=r'\\wsl.localhost\Ubuntu\home\khaled\Kore\succubus_winged.blend')
scene = bpy.context.scene
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
WL, WR = bpy.data.objects['WingsL'], bpy.data.objects['WingsR']
body = next(o for o in bpy.data.objects
            if o.type == 'MESH' and not o.name.startswith('Wings'))
mw = arm.matrix_world
OUT = r'C:\tmp'

# ── island structure of ONE wing: what an anatomical rig would rig ──
bm = bmesh.new(); bm.from_mesh(WL.data); bm.verts.ensure_lookup_table()
seen, isl = set(), []
for v in bm.verts:
    if v.index in seen: continue
    st, comp = [v], []; seen.add(v.index)
    while st:
        c = st.pop(); comp.append(c.index)
        for e in c.link_edges:
            o = e.other_vert(c)
            if o.index not in seen: seen.add(o.index); st.append(o)
    isl.append(comp)
bm.free()
isl.sort(key=len, reverse=True)
print('WINGL ISLANDS %d' % len(isl))
for k, comp in enumerate(isl[:10]):
    p = [WL.matrix_world @ WL.data.vertices[i].co for i in comp]
    lo = Vector((min(q.x for q in p), min(q.y for q in p), min(q.z for q in p)))
    hi = Vector((max(q.x for q in p), max(q.y for q in p), max(q.z for q in p)))
    ext = hi - lo
    thin = min(ext) / (max(ext) + 1e-9)
    kind = 'MEMBRANE' if thin > 0.25 and len(comp) > 200 else 'SPAR/CLAW'
    print('  isl%-2d n=%-5d ext=%s thin=%.2f  %s  (x %.2f..%.2f, z %.2f..%.2f)'
          % (k, len(comp), [round(v, 3) for v in ext], thin, kind,
             lo.x, hi.x, lo.z, hi.z))

NAMES = {'L': ['WingL_root', 'WingL_mid', 'WingL_tip'],
         'R': ['WingR_root', 'WingR_mid', 'WingR_tip']}

def clear():
    for nms in NAMES.values():
        for nm in nms:
            pb = arm.pose.bones[nm]
            pb.rotation_mode = 'QUATERNION'
            pb.rotation_quaternion = Quaternion()
    bpy.context.view_layer.update()

def local_quat(pb, ax, deg):
    m = pb.bone.matrix_local.to_3x3().inverted()
    return Quaternion((m @ Vector(ax)).normalized(), math.radians(deg))

def aim_bone(pb, want_world):
    """point the bone's axis along want_world (live-matrix conjugation)"""
    R = mw.to_3x3(); Ri = R.inverted()
    pb.rotation_quaternion = Quaternion()
    bpy.context.view_layer.update()
    cur = (Ri @ ((mw @ pb.tail) - (mw @ pb.head))).normalized()
    des = (Ri @ Vector(want_world)).normalized()
    M0 = pb.matrix.to_quaternion()
    pb.rotation_quaternion = M0.inverted() @ cur.rotation_difference(des) @ M0
    bpy.context.view_layer.update()

def measure():
    deps = bpy.context.evaluated_depsgraph_get()
    pts = []
    for o in (WL, WR):
        eo = o.evaluated_get(deps)
        pts += [eo.matrix_world @ v.co for v in eo.data.vertices]
    return (max(p.x for p in pts) - min(p.x for p in pts),
            max(p.z for p in pts), max(p.z for p in pts) - min(p.z for p in pts))

# ── strategy A: current — same-sign +Y on all three (the "plank swing")
def strat_swing(deg=40):
    clear()
    for side, sgn in (('L', 1), ('R', -1)):
        for nm, k in zip(NAMES[side], (1.0, 0.62, 0.30)):
            pb = arm.pose.bones[nm]
            pb.rotation_quaternion = local_quat(pb, (0, 1, 0), deg * k * sgn)
    bpy.context.view_layer.update()

# ── strategy B: UNFOLD — aim each bone along one outward direction, so
# the arc STRAIGHTENS and the span grows from the chain's own length
def strat_unfold(out_y=0.18, out_z=0.10):
    clear()
    for side, sgn in (('L', 1), ('R', -1)):
        d = Vector((sgn, out_y, out_z)).normalized()
        for nm in NAMES[side]:
            aim_bone(arm.pose.bones[nm], d)

# ── strategy C: SWEEP — rotate about the vertical axis so the arm swings
# outward in the HORIZONTAL plane (protraction), no tipping
def strat_sweep(deg=45):
    clear()
    for side, sgn in (('L', 1), ('R', -1)):
        for nm, k in zip(NAMES[side], (1.0, 0.62, 0.30)):
            pb = arm.pose.bones[nm]
            pb.rotation_quaternion = local_quat(pb, (0, 0, 1), -deg * k * sgn)
    bpy.context.view_layer.update()

# ── strategy D: UNFOLD then a little elevation — extension first, THEN
# set the wing's angle. This is what a real wing does in that order.
def strat_combo():
    strat_unfold(0.20, 0.06)
    for side, sgn in (('L', 1), ('R', -1)):
        pb = arm.pose.bones[NAMES[side][0]]
        q = pb.rotation_quaternion.copy()
        pb.rotation_quaternion = q @ local_quat(pb, (0, 1, 0), 16 * sgn)
    bpy.context.view_layer.update()

clear(); base = measure()
print('BASE furled  span=%.3f top_z=%.3f height=%.3f' % base)
CASES = [('A swing +Y40 (current)', strat_swing),
         ('B unfold (aim outward)', strat_unfold),
         ('C sweep about vertical', strat_sweep),
         ('D unfold + elevate', strat_combo)]
res = []
for label, fn in CASES:
    fn()
    m = measure()
    res.append((label, m))
    print('%-26s span=%.3f (%+.3f vs furled) top_z=%.3f height=%.3f'
          % (label, m[0], m[0] - base[0], m[1], m[2]))

# ── render them for the eye ──
center = Vector((0, 0, 1.12)); size = 2.1
for nm, off, e, col in (('K', Vector((-1, -1.2, 1.3)), 2.5, (1, .96, .92)),
                        ('F', Vector((1.3, -.9, .4)), 1.0, (.82, .87, 1))):
    d = bpy.data.lights.new(nm, 'SUN'); d.energy, d.color = e, col
    o = bpy.data.objects.new(nm, d); o.location = center + off * size
    o.rotation_euler = (center - o.location).to_track_quat('-Z', 'Y').to_euler()
    scene.collection.objects.link(o)
w = bpy.data.worlds.new('W'); w.use_nodes = True
w.node_tree.nodes['Background'].inputs['Color'].default_value = (.11, .10, .13, 1)
scene.world = w
try: scene.render.engine = 'BLENDER_EEVEE'
except TypeError: scene.render.engine = 'BLENDER_EEVEE_NEXT'
scene.render.resolution_x, scene.render.resolution_y = 520, 620
cd = bpy.data.cameras.new('C'); cd.lens = 44
cam = bpy.data.objects.new('C', cd); scene.collection.objects.link(cam)
scene.camera = cam
man = []
shots = [('FURLED', None)] + CASES
i = 0
for label, fn in shots:
    for vi, (dv, vlabel) in enumerate((((0, -1, 0.06), 'front'),
                                       ((0.35, -0.55, 0.75), 'top'))):
        if fn is None: clear()
        else: fn()
        cam.location = center + Vector(dv).normalized() * size * 1.6
        cam.rotation_euler = (center - cam.location).to_track_quat('-Z', 'Y').to_euler()
        i += 1
        scene.render.filepath = OUT + '\\wspread_%02d.png' % i
        bpy.ops.render.render(write_still=True)
        man.append({'index': i, 'label': '%s / %s' % (label, vlabel)})
with open(OUT + '\\wspread_manifest.json', 'w') as fh:
    json.dump({'samples': man}, fh)
print('RENDERED %d' % i)
