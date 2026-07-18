"""Probe Silverlight.glb: object structure, dimensions, pivot, blade axis.
Run: blender.exe --background --python probe_sword.py
"""
import bpy

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=r'C:\Users\kmessai\Downloads\Silverlight.glb')

for obj in bpy.data.objects:
    print('OBJ %-24s type=%-6s parent=%s' % (obj.name, obj.type,
          obj.parent.name if obj.parent else None))
    print('    loc=%s rot_quat=%s scale=%s' % (tuple(obj.location),
          tuple(obj.rotation_quaternion) if obj.rotation_mode == 'QUATERNION'
          else tuple(obj.rotation_euler), tuple(obj.scale)))
    if obj.type == 'MESH':
        me = obj.data
        xs = [v.co.x for v in me.vertices]
        ys = [v.co.y for v in me.vertices]
        zs = [v.co.z for v in me.vertices]
        print('    verts=%d local bbox x[%.3f %.3f] y[%.3f %.3f] z[%.3f %.3f]'
              % (len(me.vertices), min(xs), max(xs), min(ys), max(ys),
                 min(zs), max(zs)))
        bpy.context.view_layer.update()
        wb = [obj.matrix_world @ v.co for v in me.vertices]
        print('    world bbox x[%.3f %.3f] y[%.3f %.3f] z[%.3f %.3f]'
              % (min(v.x for v in wb), max(v.x for v in wb),
                 min(v.y for v in wb), max(v.y for v in wb),
                 min(v.z for v in wb), max(v.z for v in wb)))
        print('    materials:', [m.name if m else None for m in me.materials])

# cross-section profile along Z to find tip / guard / grip
me = bpy.data.objects['Mesh_0'].data
import collections
bins = collections.defaultdict(lambda: [0.0, 0.0, 0])
for v in me.vertices:
    b = round(v.co.z, 1)
    bins[b][0] = max(bins[b][0], abs(v.co.x))
    bins[b][1] = max(bins[b][1], abs(v.co.y))
    bins[b][2] += 1
for z in sorted(bins):
    mx, my, n = bins[z]
    print('PROF z=%5.1f  max|x|=%.3f max|y|=%.3f n=%d' % (z, mx, my, n))
