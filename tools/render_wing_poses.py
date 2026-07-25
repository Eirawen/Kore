"""Contact sheet of the whole wing pose library, with measured span/height
per pose so the emotional read has numbers under it."""
import bpy, sys, json, math
sys.path.append('/home/khaled/Kore/tools')
from mathutils import Vector, Quaternion
from wing_poses import WING_POSES, apply_wing_pose

bpy.ops.wm.open_mainfile(
    filepath=r'\\wsl.localhost\Ubuntu\home\khaled\Kore\succubus_winged.blend')
scene = bpy.context.scene
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
WL, WR = bpy.data.objects['WingsL'], bpy.data.objects['WingsR']
OUT = r'C:\tmp'

def measure():
    deps = bpy.context.evaluated_depsgraph_get()
    pts = []
    for o in (WL, WR):
        eo = o.evaluated_get(deps)
        pts += [eo.matrix_world @ v.co for v in eo.data.vertices]
    return (max(p.x for p in pts) - min(p.x for p in pts),
            max(p.z for p in pts) - min(p.z for p in pts),
            max(p.y for p in pts) - min(p.y for p in pts))

center = Vector((0, 0, 1.12)); size = 2.2
for nm, off, e, col in (('K', Vector((-1, -1.2, 1.3)), 2.5, (1, .96, .92)),
                        ('F', Vector((1.3, -.9, .4)), 1.0, (.82, .87, 1)),
                        ('B', Vector((0, 1.3, .6)), 0.7, (.9, .9, 1))):
    d = bpy.data.lights.new(nm, 'SUN'); d.energy, d.color = e, col
    o = bpy.data.objects.new(nm, d); o.location = center + off * size
    o.rotation_euler = (center - o.location).to_track_quat('-Z', 'Y').to_euler()
    scene.collection.objects.link(o)
w = bpy.data.worlds.new('W'); w.use_nodes = True
w.node_tree.nodes['Background'].inputs['Color'].default_value = (.11, .10, .13, 1)
scene.world = w
try: scene.render.engine = 'BLENDER_EEVEE'
except TypeError: scene.render.engine = 'BLENDER_EEVEE_NEXT'
scene.render.resolution_x, scene.render.resolution_y = 400, 500
cd = bpy.data.cameras.new('C'); cd.lens = 42
cam = bpy.data.objects.new('C', cd); scene.collection.objects.link(cam)
scene.camera = cam

man, i = [], 0
for name, spec in WING_POSES.items():
    apply_wing_pose(arm, name)
    sp, hz, dy = measure()
    print('POSE %-8s span=%.3f height=%.3f depth=%.3f  | %s'
          % (name, sp, hz, dy, spec['reads']))
    for dv, vl in (((0, -1, 0.06), 'front'), ((0.75, -1.0, 0.14), '3/4')):
        cam.location = center + Vector(dv).normalized() * size * 1.62
        cam.rotation_euler = (center - cam.location).to_track_quat('-Z', 'Y').to_euler()
        i += 1
        scene.render.filepath = OUT + '\\wpose_%02d.png' % i
        bpy.ops.render.render(write_still=True)
        man.append({'index': i, 'pose': name, 'view': vl,
                    'reads': spec['reads'], 'span': round(sp, 3),
                    'height': round(hz, 3)})
with open(OUT + '\\wpose_manifest.json', 'w') as fh:
    json.dump({'samples': man}, fh)
print('RENDERED %d' % i)
