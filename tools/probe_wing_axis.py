"""Which armature axis OPENS the wings? Probe, don't guess (same method
as the railgun's GUN_ROLL). Renders each axis/sign and reports the
resulting SPAN — the correct axis is the one that makes span go UP."""
import bpy, json, math
from mathutils import Vector, Quaternion

bpy.ops.wm.open_mainfile(
    filepath=r'\\wsl.localhost\Ubuntu\home\khaled\Kore\succubus_winged.blend')
scene = bpy.context.scene
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
wing = bpy.data.objects['Wings']
body = next(o for o in bpy.data.objects
            if o.type == 'MESH' and o.name != 'Wings')
mw = arm.matrix_world
OUT = r'C:\tmp'

def local_quat(pb, axis_arm, deg):
    m = pb.bone.matrix_local.to_3x3().inverted()
    return Quaternion((m @ Vector(axis_arm)).normalized(), math.radians(deg))

NAMES = {'L': ['WingL_root', 'WingL_mid', 'WingL_tip'],
         'R': ['WingR_root', 'WingR_mid', 'WingR_tip']}
FALLOFF = (1.0, 0.6, 0.3)

def apply(axis, deg):
    for side, sgn in (('L', 1), ('R', -1)):
        for nm, k in zip(NAMES[side], FALLOFF):
            pb = arm.pose.bones[nm]
            pb.rotation_mode = 'QUATERNION'
            pb.rotation_quaternion = local_quat(pb, axis, deg * k * sgn)
    bpy.context.view_layer.update()

def measure():
    deps = bpy.context.evaluated_depsgraph_get()
    eo = wing.evaluated_get(deps)
    pts = [eo.matrix_world @ v.co for v in eo.data.vertices]
    return (max(p.x for p in pts) - min(p.x for p in pts),
            max(p.z for p in pts), max(p.y for p in pts) - min(p.y for p in pts))

apply((0, 0, 1), 0)
base = measure()
print('BASE span=%.3f top_z=%.3f depth=%.3f' % base)

CANDS = [((1, 0, 0), 40, 'X+40'), ((1, 0, 0), -40, 'X-40'),
         ((0, 1, 0), 40, 'Y+40'), ((0, 1, 0), -40, 'Y-40'),
         ((0, 0, 1), 40, 'Z+40'), ((0, 0, 1), -40, 'Z-40')]
res = []
for axis, deg, label in CANDS:
    apply(axis, deg)
    sp, tz, dp = measure()
    res.append((label, sp, tz, dp))
    print('AXIS %-6s span=%.3f (%+.3f) top_z=%.3f depth=%.3f'
          % (label, sp, sp - base[0], tz, dp))

best = max(res, key=lambda r: r[1])
print('BEST opener: %s (span %.3f -> %.3f)' % (best[0], base[0], best[1]))

# render the winner plus base for the eye to confirm
lights = []
center = Vector((0, 0, 1.15)); size = 2.0
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
scene.render.resolution_x, scene.render.resolution_y = 560, 660
cd = bpy.data.cameras.new('C'); cd.lens = 46
cam = bpy.data.objects.new('C', cd); scene.collection.objects.link(cam)
scene.camera = cam
man = []
shots = [((0, 0, 1), 0, 'FURLED (base)')]
for axis, deg, label in CANDS:
    if label == best[0]:
        shots.append((axis, deg, 'SPREAD ' + label))
        shots.append((axis, deg * 1.7, 'SPREAD %s x1.7' % label))
for i, (axis, deg, label) in enumerate(shots):
    apply(axis, deg)
    cam.location = center + Vector((0.5, -1.3, 0.10)).normalized() * size * 1.6
    cam.rotation_euler = (center - cam.location).to_track_quat('-Z', 'Y').to_euler()
    scene.render.filepath = OUT + '\\waxis_%02d.png' % (i + 1)
    bpy.ops.render.render(write_still=True)
    man.append({'index': i + 1, 'label': label})
with open(OUT + '\\waxis_manifest.json', 'w') as fh:
    json.dump({'samples': man}, fh)
print('PROBE rendered %d' % len(man))
