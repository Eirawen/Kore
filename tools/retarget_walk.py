"""Retarget the Meshy walk GLB onto the surgery blend's rig.

glTF animation channels are node-local ABSOLUTE quaternions; Blender pose
quats are DELTAS on rest. Formula per bone per key:
    pose_quat = rest_gltf^-1 (x) channel_quat
Hips also gets its translation channel (parent-space cm -> bone-local via
matrix_local, same conversion as everywhere else).

Renders 8 frames across one walk cycle -> C:\tmp\walkcheck_NN.png
"""
import bpy
import json
import struct
import numpy as np
from mathutils import Vector, Quaternion

GLB = '/home/khaled/Kore/succubus_walk.glb'
OUT = r'C:\tmp'
ARM = 'Armature'
FPS = 60

# ── parse GLB ──
with open(GLB, 'rb') as f:
    data = f.read()
jlen, _ = struct.unpack('<II', data[12:20])
gltf = json.loads(data[20:20 + jlen])
boff = 20 + jlen
blen, _ = struct.unpack('<II', data[boff:boff + 8])
bin_chunk = data[boff + 8:boff + 8 + blen]

def read_accessor(idx):
    acc = gltf['accessors'][idx]
    bv = gltf['bufferViews'][acc['bufferView']]
    start = bv.get('byteOffset', 0) + acc.get('byteOffset', 0)
    ncomp = {'SCALAR': 1, 'VEC3': 3, 'VEC4': 4}[acc['type']]
    arr = np.frombuffer(bin_chunk, dtype=np.float32,
                        count=acc['count'] * ncomp, offset=start)
    return arr.reshape(acc['count'], ncomp)

nodes = gltf['nodes']
name_of = {i: n.get('name', f'n{i}') for i, n in enumerate(nodes)}
rest_r = {i: n.get('rotation', [0, 0, 0, 1]) for i, n in enumerate(nodes)}
rest_t = {i: n.get('translation', [0, 0, 0]) for i, n in enumerate(nodes)}
anim = gltf['animations'][0]

# ── staging (same as animate_coy) ──
scene = bpy.context.scene
ico = bpy.data.objects.get('Icosphere')
if ico:
    ico.hide_render = True
cam = bpy.data.objects.get('Camera')
cam.location = Vector((2.9, -3.6, 1.6))
target = Vector((0.0, -0.1, 0.95))
cam.rotation_euler = (target - cam.location).to_track_quat('-Z', 'Y').to_euler()
cam.data.lens = 50
scene.camera = cam
import math
for nm, loc, e, col in (('WKey', (-3, -5, 4), 2.2, (1.0, 0.95, 0.9)),
                        ('WFill', (4, -3, 1.5), 0.7, (0.8, 0.85, 1.0))):
    d = bpy.data.lights.new(nm, 'SUN')
    d.energy, d.color = e, col
    d.angle = math.radians(8)
    o = bpy.data.objects.new(nm, d)
    o.location = loc
    o.rotation_euler = (Vector((0, 0, 1.0)) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
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

# ── retarget ──
arm = bpy.data.objects[ARM]
arm.animation_data_clear()
for pb in arm.pose.bones:
    pb.rotation_mode = 'QUATERNION'
    pb.rotation_quaternion = Quaternion()
    pb.location = (0, 0, 0)

max_t = 0.0
for ch in anim['channels']:
    node = ch['target']['node']
    bname = name_of[node]
    pb = arm.pose.bones.get(bname)
    if pb is None:
        continue
    samp = anim['samplers'][ch['sampler']]
    times = read_accessor(samp['input'])[:, 0]
    vals = read_accessor(samp['output'])
    max_t = max(max_t, float(times[-1]))
    path = ch['target']['path']
    if path == 'rotation':
        rq = rest_r[node]
        rest = Quaternion((rq[3], rq[0], rq[1], rq[2]))
        rinv = rest.inverted()
        for t, v in zip(times, vals):
            q = Quaternion((v[3], v[0], v[1], v[2]))
            pb.rotation_quaternion = rinv @ q
            pb.keyframe_insert('rotation_quaternion', frame=1 + t * FPS)
    elif path == 'translation' and bname == 'Hips':
        rt = Vector(rest_t[node])
        m = pb.bone.matrix_local.to_3x3().inverted()
        for t, v in zip(times, vals):
            # glTF Y-up parent space -> blender armature space: the importer
            # bakes the up-axis into the armature object; hips parent chain
            # (char1/Armature) carries it. Convert via the same rest frame.
            delta = Vector((v[0], v[1], v[2])) - rt
            pb.location = m @ delta
            pb.keyframe_insert('location', frame=1 + t * FPS)

scene.frame_start = 1
scene.frame_end = int(1 + max_t * FPS)
print('retargeted, cycle length %.2fs -> frames 1..%d' % (max_t, scene.frame_end))

# ── render 8 frames across the cycle ──
manifest = []
n = scene.frame_end
frames = [max(1, round(1 + (n - 1) * i / 7)) for i in range(8)]
for i, f in enumerate(sorted(set(frames))):
    scene.frame_set(f)
    path = OUT + '\\walkcheck_%02d.png' % (i + 1)
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    manifest.append({'index': i + 1, 'frame': f, 'time': round((f - 1) / FPS, 3)})
    print('rendered', path)
with open(OUT + '\\walkcheck_manifest.json', 'w') as fh:
    json.dump({'samples': manifest}, fh)
