# Clean up Khaled's hand-posed grip and render it for comparison.
# Loads his saved sandbox; relaxes the over-curled thumb TIP (Bone.003 was
# ~170deg, folded double) to a natural flexion. Renders 3 matte views.
# (The wrist-twist -> forearm redistribution is invisible here and is done when
#  we retarget onto the constrained rig for animation, where it actually bites.)
import bpy, math
from mathutils import Vector, Quaternion

RIGHT = 'Armature.001'
arm = bpy.data.objects[RIGHT]

# --- relax the thumb tip to a natural ~40deg curl ---
arm.pose.bones['Bone.003'].rotation_mode = 'QUATERNION'
arm.pose.bones['Bone.003'].rotation_quaternion = Quaternion((1, 0, 0), math.radians(40))
bpy.context.view_layer.update()

scene = bpy.context.scene
scene.render.image_settings.file_format = 'PNG'
scene.render.resolution_x = scene.render.resolution_y = 900


def look_at(loc, t):
    return (t - loc).to_track_quat('-Z', 'Y').to_euler()


def add_cam(name, loc, aim, lens=55):
    c = bpy.data.cameras.new(name); c.lens = lens
    o = bpy.data.objects.new(name, c); scene.collection.objects.link(o)
    o.location = Vector(loc); o.rotation_euler = look_at(Vector(loc), Vector(aim))
    return o


# aim at the ACTUAL POSED hand: read the deformed (evaluated) vertices, not the
# rest-pose bounding box. This is where the fingers really are after posing.
mesh = bpy.data.objects['Sphere.001']
deps = bpy.context.evaluated_depsgraph_get()
ev = mesh.evaluated_get(deps)
me = ev.to_mesh()
vs = [ev.matrix_world @ v.co for v in me.vertices]
center = sum(vs, Vector()) / len(vs)
radius = max((v - center).length for v in vs)
ev.to_mesh_clear()
print('posed hand center:', tuple(round(v, 2) for v in center), 'radius', round(radius, 2))

D = radius * 2.6
a = add_cam('CamA', center + Vector((-0.3, -1.0, 0.15)).normalized() * D, center, 50)
b = add_cam('CamB', center + Vector((-0.9, -0.6, 0.1)).normalized() * D, center, 50)
c = add_cam('CamC', center + Vector((0.8, -0.6, 0.1)).normalized() * D, center, 50)

shots = [('fp', a), ('close', b), ('side', c)]
for nm, c in shots:
    if c is None:
        continue
    scene.camera = c
    scene.render.filepath = r'C:\tmp\khaled_grip_%s.png' % nm
    bpy.ops.render.render(write_still=True)
    print('rendered', nm)
