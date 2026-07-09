"""Auto-generated simple hand rig — one bone per finger."""
import bpy
from mathutils import Vector
import numpy as np

MESH_PATH = r'/home/khaled/Kore/slayerhands.glb'
BONES = [
  {
    "name": "L_wrist",
    "head": [
      -0.552,
      -0.03199999999999997,
      -0.42400000000000004
    ],
    "tail": [
      -0.5711999999999999,
      0.0012800000000000207,
      -0.0912
    ],
    "parent": None
  },
  {
    "name": "R_wrist",
    "head": [
      0.5199999999999999,
      -0.015999999999999986,
      -0.40800000000000003
    ],
    "tail": [
      0.55712,
      -0.016639999999999988,
      -0.07264000000000004
    ],
    "parent": None
  },
  {
    "name": "L_thumb_0",
    "head": [
      -0.5711999999999999,
      0.0012800000000000207,
      -0.0912
    ],
    "tail": [
      -0.3776,
      -0.031359999999999985,
      0.0744
    ],
    "parent": "L_wrist"
  },
  {
    "name": "L_thumb_1",
    "head": [
      -0.3776,
      -0.031359999999999985,
      0.0744
    ],
    "tail": [
      -0.18400000000000005,
      -0.064,
      0.24
    ],
    "parent": "L_thumb_0"
  },
  {
    "name": "L_index_0",
    "head": [
      -0.5711999999999999,
      0.0012800000000000207,
      -0.0912
    ],
    "tail": [
      -0.5411039999999999,
      0.011417600000000024,
      0.11577599999999999
    ],
    "parent": "L_wrist"
  },
  {
    "name": "L_index_1",
    "head": [
      -0.5411039999999999,
      0.011417600000000024,
      0.11577599999999999
    ],
    "tail": [
      -0.51648,
      0.019712000000000025,
      0.28512
    ],
    "parent": "L_index_0"
  },
  {
    "name": "L_index_2",
    "head": [
      -0.51648,
      0.019712000000000025,
      0.28512
    ],
    "tail": [
      -0.49824,
      0.02585600000000003,
      0.41056
    ],
    "parent": "L_index_1"
  },
  {
    "name": "L_index_3",
    "head": [
      -0.49824,
      0.02585600000000003,
      0.41056
    ],
    "tail": [
      -0.48000000000000004,
      0.03200000000000003,
      0.5359999999999999
    ],
    "parent": "L_index_2"
  },
  {
    "name": "L_middle_0",
    "head": [
      -0.5711999999999999,
      0.0012800000000000207,
      -0.0912
    ],
    "tail": [
      -0.6018239999999999,
      0.021977600000000017,
      0.11577599999999999
    ],
    "parent": "L_wrist"
  },
  {
    "name": "L_middle_1",
    "head": [
      -0.6018239999999999,
      0.021977600000000017,
      0.11577599999999999
    ],
    "tail": [
      -0.62688,
      0.038912000000000016,
      0.28512
    ],
    "parent": "L_middle_0"
  },
  {
    "name": "L_middle_2",
    "head": [
      -0.62688,
      0.038912000000000016,
      0.28512
    ],
    "tail": [
      -0.64544,
      0.051456000000000016,
      0.41056
    ],
    "parent": "L_middle_1"
  },
  {
    "name": "L_middle_3",
    "head": [
      -0.64544,
      0.051456000000000016,
      0.41056
    ],
    "tail": [
      -0.664,
      0.064,
      0.5359999999999999
    ],
    "parent": "L_middle_2"
  },
  {
    "name": "L_ring_0",
    "head": [
      -0.5711999999999999,
      0.0012800000000000207,
      -0.0912
    ],
    "tail": [
      -0.6361439999999999,
      0.040457600000000024,
      0.08673600000000004
    ],
    "parent": "L_wrist"
  },
  {
    "name": "L_ring_1",
    "head": [
      -0.6361439999999999,
      0.040457600000000024,
      0.08673600000000004
    ],
    "tail": [
      -0.68928,
      0.07251200000000002,
      0.23232000000000008
    ],
    "parent": "L_ring_0"
  },
  {
    "name": "L_ring_2",
    "head": [
      -0.68928,
      0.07251200000000002,
      0.23232000000000008
    ],
    "tail": [
      -0.72864,
      0.09625600000000002,
      0.34016000000000013
    ],
    "parent": "L_ring_1"
  },
  {
    "name": "L_ring_3",
    "head": [
      -0.72864,
      0.09625600000000002,
      0.34016000000000013
    ],
    "tail": [
      -0.768,
      0.12000000000000002,
      0.44800000000000006
    ],
    "parent": "L_ring_2"
  },
  {
    "name": "L_pinky_0",
    "head": [
      -0.5711999999999999,
      0.0012800000000000207,
      -0.0912
    ],
    "tail": [
      -0.681024,
      0.03517760000000002,
      0.03129600000000002
    ],
    "parent": "L_wrist"
  },
  {
    "name": "L_pinky_1",
    "head": [
      -0.681024,
      0.03517760000000002,
      0.03129600000000002
    ],
    "tail": [
      -0.77088,
      0.06291200000000001,
      0.13152
    ],
    "parent": "L_pinky_0"
  },
  {
    "name": "L_pinky_2",
    "head": [
      -0.77088,
      0.06291200000000001,
      0.13152
    ],
    "tail": [
      -0.83744,
      0.08345600000000002,
      0.20576000000000005
    ],
    "parent": "L_pinky_1"
  },
  {
    "name": "L_pinky_3",
    "head": [
      -0.83744,
      0.08345600000000002,
      0.20576000000000005
    ],
    "tail": [
      -0.904,
      0.10400000000000001,
      0.28
    ],
    "parent": "L_pinky_2"
  },
  {
    "name": "R_thumb_0",
    "head": [
      0.55712,
      -0.016639999999999988,
      -0.07264000000000004
    ],
    "tail": [
      0.37456,
      -0.02431999999999998,
      0.07967999999999997
    ],
    "parent": "R_wrist"
  },
  {
    "name": "R_thumb_1",
    "head": [
      0.37456,
      -0.02431999999999998,
      0.07967999999999997
    ],
    "tail": [
      0.19200000000000006,
      -0.03199999999999997,
      0.23199999999999998
    ],
    "parent": "R_thumb_0"
  },
  {
    "name": "R_index_0",
    "head": [
      0.55712,
      -0.016639999999999988,
      -0.07264000000000004
    ],
    "tail": [
      0.5395903999999999,
      -0.024348799999999986,
      0.13877119999999996
    ],
    "parent": "R_wrist"
  },
  {
    "name": "R_index_1",
    "head": [
      0.5395903999999999,
      -0.024348799999999986,
      0.13877119999999996
    ],
    "tail": [
      0.5252479999999999,
      -0.030655999999999982,
      0.31174399999999997
    ],
    "parent": "R_index_0"
  },
  {
    "name": "R_index_2",
    "head": [
      0.5252479999999999,
      -0.030655999999999982,
      0.31174399999999997
    ],
    "tail": [
      0.5146239999999999,
      -0.035327999999999984,
      0.43987199999999993
    ],
    "parent": "R_index_1"
  },
  {
    "name": "R_index_3",
    "head": [
      0.5146239999999999,
      -0.035327999999999984,
      0.43987199999999993
    ],
    "tail": [
      0.5039999999999999,
      -0.03999999999999998,
      0.568
    ],
    "parent": "R_index_2"
  },
  {
    "name": "R_middle_0",
    "head": [
      0.55712,
      -0.016639999999999988,
      -0.07264000000000004
    ],
    "tail": [
      0.5897504,
      -0.01906879999999999,
      0.13349119999999998
    ],
    "parent": "R_wrist"
  },
  {
    "name": "R_middle_1",
    "head": [
      0.5897504,
      -0.01906879999999999,
      0.13349119999999998
    ],
    "tail": [
      0.616448,
      -0.02105599999999999,
      0.3021439999999999
    ],
    "parent": "R_middle_0"
  },
  {
    "name": "R_middle_2",
    "head": [
      0.616448,
      -0.02105599999999999,
      0.3021439999999999
    ],
    "tail": [
      0.636224,
      -0.022527999999999992,
      0.42707199999999995
    ],
    "parent": "R_middle_1"
  },
  {
    "name": "R_middle_3",
    "head": [
      0.636224,
      -0.022527999999999992,
      0.42707199999999995
    ],
    "tail": [
      0.656,
      -0.023999999999999994,
      0.5519999999999999
    ],
    "parent": "R_middle_2"
  },
  {
    "name": "R_ring_0",
    "head": [
      0.55712,
      -0.016639999999999988,
      -0.07264000000000004
    ],
    "tail": [
      0.6346303999999999,
      -0.003228799999999985,
      0.10445120000000002
    ],
    "parent": "R_wrist"
  },
  {
    "name": "R_ring_1",
    "head": [
      0.6346303999999999,
      -0.003228799999999985,
      0.10445120000000002
    ],
    "tail": [
      0.6980479999999999,
      0.007744000000000018,
      0.249344
    ],
    "parent": "R_ring_0"
  },
  {
    "name": "R_ring_2",
    "head": [
      0.6980479999999999,
      0.007744000000000018,
      0.249344
    ],
    "tail": [
      0.7450239999999999,
      0.015872000000000018,
      0.3566720000000001
    ],
    "parent": "R_ring_1"
  },
  {
    "name": "R_ring_3",
    "head": [
      0.7450239999999999,
      0.015872000000000018,
      0.3566720000000001
    ],
    "tail": [
      0.7919999999999999,
      0.02400000000000002,
      0.4640000000000001
    ],
    "parent": "R_ring_2"
  },
  {
    "name": "R_pinky_0",
    "head": [
      0.55712,
      -0.016639999999999988,
      -0.07264000000000004
    ],
    "tail": [
      0.6768704,
      -0.016428799999999986,
      0.062211199999999967
    ],
    "parent": "R_wrist"
  },
  {
    "name": "R_pinky_1",
    "head": [
      0.6768704,
      -0.016428799999999986,
      0.062211199999999967
    ],
    "tail": [
      0.774848,
      -0.016255999999999986,
      0.17254399999999995
    ],
    "parent": "R_pinky_0"
  },
  {
    "name": "R_pinky_2",
    "head": [
      0.774848,
      -0.016255999999999986,
      0.17254399999999995
    ],
    "tail": [
      0.847424,
      -0.016127999999999986,
      0.254272
    ],
    "parent": "R_pinky_1"
  },
  {
    "name": "R_pinky_3",
    "head": [
      0.847424,
      -0.016127999999999986,
      0.254272
    ],
    "tail": [
      0.92,
      -0.015999999999999986,
      0.33599999999999997
    ],
    "parent": "R_pinky_2"
  }
]

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

bpy.ops.import_scene.gltf(filepath=MESH_PATH)
mesh_obj = None
for obj in bpy.context.scene.objects:
    if obj.type == 'MESH':
        mesh_obj = obj
        break

bpy.context.view_layer.objects.active = mesh_obj
mesh_obj.select_set(True)
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

bpy.ops.object.armature_add(location=(0, 0, 0))
armature = bpy.context.object
armature.name = 'HandArmature'
bpy.ops.object.mode_set(mode='EDIT')

for b in armature.data.edit_bones:
    armature.data.edit_bones.remove(b)

bone_map = {}
for bd in BONES:
    bone = armature.data.edit_bones.new(bd['name'])
    bone.head = Vector(bd['head'])
    bone.tail = Vector(bd['tail'])
    bone_map[bd['name']] = bone

for bd in BONES:
    if bd['parent'] and bd['parent'] in bone_map:
        bone_map[bd['name']].parent = bone_map[bd['parent']]

bpy.ops.object.mode_set(mode='OBJECT')

mesh_obj.select_set(True)
armature.select_set(True)
bpy.context.view_layer.objects.active = armature
bpy.ops.object.parent_set(type='ARMATURE_NAME')

# Weight painting — each vertex to nearest bone
print("Assigning weights...")
verts = np.array([v.co for v in mesh_obj.data.vertices])

bone_data = []
for bd in BONES:
    head = np.array(bd['head'])
    tail = np.array(bd['tail'])
    bone_data.append((bd['name'], head, tail))

for bd in BONES:
    if bd['name'] not in mesh_obj.vertex_groups:
        mesh_obj.vertex_groups.new(name=bd['name'])

for vi, v in enumerate(verts):
    best_bone = None
    best_dist = float('inf')
    for bname, head, tail in bone_data:
        seg = tail - head
        seg_len = np.linalg.norm(seg)
        if seg_len < 1e-6:
            dist = np.linalg.norm(v - head)
        else:
            t = np.clip(np.dot(v - head, seg) / (seg_len * seg_len), 0, 1)
            proj = head + t * seg
            dist = np.linalg.norm(v - proj)
        if dist < best_dist:
            best_dist = dist
            best_bone = bname
    if best_bone:
        mesh_obj.vertex_groups[best_bone].add([vi], 1.0, 'REPLACE')

print("Done")

bpy.ops.wm.save_as_mainfile(filepath=r'C:\tmp\slayerhands_rigged.blend')
bpy.ops.export_scene.gltf(filepath=r'C:\tmp\slayerhands_rigged.glb', export_format='GLB', export_skins=True)
print("Exported")
