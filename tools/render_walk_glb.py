"""Import the Meshy withSkin walk GLB into a FRESH scene and render its
own animation on its own skin — zero retargeting, zero surgery variables.
The ground-truth 'this is how it's supposed to look' grid.

Run:
  blender --background --python render_walk_glb.py
"""
import bpy
import json
import math
from mathutils import Vector

GLB = '/home/khaled/Kore/succubus_walk.glb'
OUT = r'C:\tmp'
FPS = 60

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=GLB)
scene = bpy.context.scene
scene.render.fps = FPS

# find the imported armature + action
armature = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
action = armature.animation_data.action if armature.animation_data else None
if action:
    f0, f1 = action.frame_range
else:  # importer may put action elsewhere
    acts = list(bpy.data.actions)
    action = acts[0]
    f0, f1 = action.frame_range
scene.frame_start, scene.frame_end = int(f0), int(max(f1, f0 + 1))
print('action:', action.name, 'frames', f0, f1)

# animated bounding box (sample mid-clip) for adaptive framing
scene.frame_set(int((f0 + f1) / 2))
deps = bpy.context.evaluated_depsgraph_get()
lo = Vector((1e9, 1e9, 1e9))
hi = Vector((-1e9, -1e9, -1e9))
for o in bpy.data.objects:
    if o.type != 'MESH':
        continue
    eo = o.evaluated_get(deps)
    for corner in eo.bound_box:
        wc = eo.matrix_world @ Vector(corner)
        lo.x, lo.y, lo.z = min(lo.x, wc.x), min(lo.y, wc.y), min(lo.z, wc.z)
        hi.x, hi.y, hi.z = max(hi.x, wc.x), max(hi.y, wc.y), max(hi.z, wc.z)
center = (lo + hi) / 2
size = max(hi - lo)
print('bbox center', [round(v, 2) for v in center], 'size', round(size, 2))

cam_data = bpy.data.cameras.new('Cam')
cam_data.lens = 50
cam = bpy.data.objects.new('Cam', cam_data)
cam.location = center + Vector((1.1, -1.3, 0.25)).normalized() * size * 1.7
cam.rotation_euler = (center - cam.location).to_track_quat('-Z', 'Y').to_euler()
scene.collection.objects.link(cam)
scene.camera = cam

for nm, off, e, col in (('K', Vector((-1, -1.2, 1.4)), 2.2, (1.0, 0.95, 0.9)),
                        ('F', Vector((1.3, -0.8, 0.4)), 0.7, (0.8, 0.85, 1.0))):
    d = bpy.data.lights.new(nm, 'SUN')
    d.energy, d.color = e, col
    d.angle = math.radians(8)
    o = bpy.data.objects.new(nm, d)
    o.location = center + off * size
    o.rotation_euler = (center - o.location).to_track_quat('-Z', 'Y').to_euler()
    scene.collection.objects.link(o)

w = bpy.data.worlds.new('W')
w.use_nodes = True
w.node_tree.nodes['Background'].inputs['Color'].default_value = (0.10, 0.09, 0.12, 1)
scene.world = w

try:
    scene.render.engine = 'BLENDER_EEVEE'
except TypeError:
    scene.render.engine = 'BLENDER_EEVEE_NEXT'
scene.render.resolution_x, scene.render.resolution_y = 960, 720
scene.render.image_settings.file_format = 'PNG'

n0, n1 = scene.frame_start, scene.frame_end
frames = sorted({round(n0 + (n1 - n0) * i / 11) for i in range(12)})
manifest = []
for i, f in enumerate(frames):
    scene.frame_set(f)
    path = OUT + '\\meshywalk_%02d.png' % (i + 1)
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    manifest.append({'index': i + 1, 'frame': f,
                     'time': round((f - n0) / FPS, 3)})
    print('rendered', path)
with open(OUT + '\\meshywalk_manifest.json', 'w') as fh:
    json.dump({'samples': manifest}, fh)
