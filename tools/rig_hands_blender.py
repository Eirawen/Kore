"""Auto-generated simple hand rig — one bone per finger."""
import bpy
from mathutils import Vector
import numpy as np

MESH_PATH = r'\\wsl.localhost\Ubuntu\home\khaled\Kore\slayerhands.glb'
BONES = [
  {
    "name": "L_wrist",
    "head": [
      -0.536,
      -0.03199999999999997,
      -0.40800000000000003
    ],
    "tail": [
      -0.56288,
      0.0019200000000000224,
      -0.07776
    ],
    "parent": None
  },
  {
    "name": "R_wrist",
    "head": [
      0.5279999999999999,
      -0.023999999999999994,
      -0.392
    ],
    "tail": [
      0.56256,
      -0.02143999999999999,
      -0.06240000000000001
    ],
    "parent": None
  },
  {
    "name": "L_thumb_0",
    "head": [
      -0.56288,
      0.0019200000000000224,
      -0.07776
    ],
    "tail": [
      -0.37344000000000005,
      -0.031039999999999988,
      0.08112
    ],
    "parent": "L_wrist"
  },
  {
    "name": "L_thumb_1",
    "head": [
      -0.37344000000000005,
      -0.031039999999999988,
      0.08112
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
      -0.56288,
      0.0019200000000000224,
      -0.07776
    ],
    "tail": [
      -0.5408096,
      0.011846400000000024,
      0.1379808
    ],
    "parent": "L_wrist"
  },
  {
    "name": "L_index_1",
    "head": [
      -0.5408096,
      0.011846400000000024,
      0.1379808
    ],
    "tail": [
      -0.5227520000000001,
      0.019968000000000024,
      0.31449599999999994
    ],
    "parent": "L_index_0"
  },
  {
    "name": "L_index_2",
    "head": [
      -0.5227520000000001,
      0.019968000000000024,
      0.31449599999999994
    ],
    "tail": [
      -0.509376,
      0.025984000000000028,
      0.4452479999999999
    ],
    "parent": "L_index_1"
  },
  {
    "name": "L_index_3",
    "head": [
      -0.509376,
      0.025984000000000028,
      0.4452479999999999
    ],
    "tail": [
      -0.49600000000000005,
      0.03200000000000003,
      0.576
    ],
    "parent": "L_index_2"
  },
  {
    "name": "L_middle_0",
    "head": [
      -0.56288,
      0.0019200000000000224,
      -0.07776
    ],
    "tail": [
      -0.5962496,
      0.02504640000000002,
      0.12742079999999997
    ],
    "parent": "L_wrist"
  },
  {
    "name": "L_middle_1",
    "head": [
      -0.5962496,
      0.02504640000000002,
      0.12742079999999997
    ],
    "tail": [
      -0.623552,
      0.04396800000000002,
      0.2952959999999999
    ],
    "parent": "L_middle_0"
  },
  {
    "name": "L_middle_2",
    "head": [
      -0.623552,
      0.04396800000000002,
      0.2952959999999999
    ],
    "tail": [
      -0.643776,
      0.05798400000000002,
      0.4196479999999999
    ],
    "parent": "L_middle_1"
  },
  {
    "name": "L_middle_3",
    "head": [
      -0.643776,
      0.05798400000000002,
      0.4196479999999999
    ],
    "tail": [
      -0.664,
      0.07200000000000001,
      0.5439999999999999
    ],
    "parent": "L_middle_2"
  },
  {
    "name": "L_ring_0",
    "head": [
      -0.56288,
      0.0019200000000000224,
      -0.07776
    ],
    "tail": [
      -0.6305696000000001,
      0.04088640000000003,
      0.09574080000000001
    ],
    "parent": "L_wrist"
  },
  {
    "name": "L_ring_1",
    "head": [
      -0.6305696000000001,
      0.04088640000000003,
      0.09574080000000001
    ],
    "tail": [
      -0.685952,
      0.07276800000000001,
      0.23769600000000002
    ],
    "parent": "L_ring_0"
  },
  {
    "name": "L_ring_2",
    "head": [
      -0.685952,
      0.07276800000000001,
      0.23769600000000002
    ],
    "tail": [
      -0.7269760000000001,
      0.09638400000000003,
      0.34284800000000004
    ],
    "parent": "L_ring_1"
  },
  {
    "name": "L_ring_3",
    "head": [
      -0.7269760000000001,
      0.09638400000000003,
      0.34284800000000004
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
      -0.56288,
      0.0019200000000000224,
      -0.07776
    ],
    "tail": [
      -0.6754496000000001,
      0.035606400000000024,
      0.04030080000000001
    ],
    "parent": "L_wrist"
  },
  {
    "name": "L_pinky_1",
    "head": [
      -0.6754496000000001,
      0.035606400000000024,
      0.04030080000000001
    ],
    "tail": [
      -0.767552,
      0.06316800000000002,
      0.13689600000000002
    ],
    "parent": "L_pinky_0"
  },
  {
    "name": "L_pinky_2",
    "head": [
      -0.767552,
      0.06316800000000002,
      0.13689600000000002
    ],
    "tail": [
      -0.8357760000000001,
      0.08358400000000002,
      0.20844800000000002
    ],
    "parent": "L_pinky_1"
  },
  {
    "name": "L_pinky_3",
    "head": [
      -0.8357760000000001,
      0.08358400000000002,
      0.20844800000000002
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
      0.56256,
      -0.02143999999999999,
      -0.06240000000000001
    ],
    "tail": [
      0.37728,
      -0.02671999999999998,
      0.08479999999999999
    ],
    "parent": "R_wrist"
  },
  {
    "name": "R_thumb_1",
    "head": [
      0.37728,
      -0.02671999999999998,
      0.08479999999999999
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
      0.56256,
      -0.02143999999999999,
      -0.06240000000000001
    ],
    "tail": [
      0.5432351999999999,
      -0.027564799999999987,
      0.14563199999999998
    ],
    "parent": "R_wrist"
  },
  {
    "name": "R_index_1",
    "head": [
      0.5432351999999999,
      -0.027564799999999987,
      0.14563199999999998
    ],
    "tail": [
      0.5274239999999999,
      -0.03257599999999998,
      0.31583999999999995
    ],
    "parent": "R_index_0"
  },
  {
    "name": "R_index_2",
    "head": [
      0.5274239999999999,
      -0.03257599999999998,
      0.31583999999999995
    ],
    "tail": [
      0.515712,
      -0.03628799999999999,
      0.44192
    ],
    "parent": "R_index_1"
  },
  {
    "name": "R_index_3",
    "head": [
      0.515712,
      -0.03628799999999999,
      0.44192
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
      0.56256,
      -0.02143999999999999,
      -0.06240000000000001
    ],
    "tail": [
      0.5933952,
      -0.02228479999999999,
      0.14035199999999998
    ],
    "parent": "R_wrist"
  },
  {
    "name": "R_middle_1",
    "head": [
      0.5933952,
      -0.02228479999999999,
      0.14035199999999998
    ],
    "tail": [
      0.618624,
      -0.022975999999999993,
      0.30623999999999996
    ],
    "parent": "R_middle_0"
  },
  {
    "name": "R_middle_2",
    "head": [
      0.618624,
      -0.022975999999999993,
      0.30623999999999996
    ],
    "tail": [
      0.637312,
      -0.02348799999999999,
      0.42911999999999995
    ],
    "parent": "R_middle_1"
  },
  {
    "name": "R_middle_3",
    "head": [
      0.637312,
      -0.02348799999999999,
      0.42911999999999995
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
      0.56256,
      -0.02143999999999999,
      -0.06240000000000001
    ],
    "tail": [
      0.6382751999999999,
      -0.003804799999999983,
      0.10867200000000002
    ],
    "parent": "R_wrist"
  },
  {
    "name": "R_ring_1",
    "head": [
      0.6382751999999999,
      -0.003804799999999983,
      0.10867200000000002
    ],
    "tail": [
      0.700224,
      0.010624000000000019,
      0.24864000000000003
    ],
    "parent": "R_ring_0"
  },
  {
    "name": "R_ring_2",
    "head": [
      0.700224,
      0.010624000000000019,
      0.24864000000000003
    ],
    "tail": [
      0.7461119999999999,
      0.021312000000000022,
      0.3523200000000001
    ],
    "parent": "R_ring_1"
  },
  {
    "name": "R_ring_3",
    "head": [
      0.7461119999999999,
      0.021312000000000022,
      0.3523200000000001
    ],
    "tail": [
      0.7919999999999999,
      0.03200000000000003,
      0.45600000000000007
    ],
    "parent": "R_ring_2"
  },
  {
    "name": "R_pinky_0",
    "head": [
      0.56256,
      -0.02143999999999999,
      -0.06240000000000001
    ],
    "tail": [
      0.6831552,
      -0.02228479999999999,
      0.074352
    ],
    "parent": "R_wrist"
  },
  {
    "name": "R_pinky_1",
    "head": [
      0.6831552,
      -0.02228479999999999,
      0.074352
    ],
    "tail": [
      0.781824,
      -0.022975999999999993,
      0.18623999999999996
    ],
    "parent": "R_pinky_0"
  },
  {
    "name": "R_pinky_2",
    "head": [
      0.781824,
      -0.022975999999999993,
      0.18623999999999996
    ],
    "tail": [
      0.8549120000000001,
      -0.02348799999999999,
      0.26912
    ],
    "parent": "R_pinky_1"
  },
  {
    "name": "R_pinky_3",
    "head": [
      0.8549120000000001,
      -0.02348799999999999,
      0.26912
    ],
    "tail": [
      0.928,
      -0.023999999999999994,
      0.352
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

# ── Palm-priority two-layer weights ──
# Diagnosis of the old failure: the finger bone chains ALL start at the palm
# center, and each finger's first bone (finger_0 = the metacarpal) runs right
# through the palm flesh. So a palm vertex near the thumb base was closest to
# L_thumb_0 and got grabbed by the thumb — the reported bug. The short wrist
# bone could never win that contest.
#
# Fix (the spider's body-priority trick, adapted): fold the metacarpal bones
# (finger_0) into the PALM territory. The finger groups then contain only the
# phalanges (finger_1..n), which live past the MCP knuckle. The palm/finger
# boundary therefore lands cleanly on the knuckle line, and the palm keeps
# priority on ties.
#   Layer 1: is this vertex palm territory (wrist + metacarpals) or a finger?
#   Layer 2: palm verts -> the wrist bone; finger verts -> nearest phalanx.
print("Assigning weights (palm-priority two-layer)...")
verts = np.array([np.array(v.co) for v in mesh_obj.data.vertices])

def seg_dist(p, head, tail):
    """Distance from point p to a bone segment [head, tail]."""
    seg = tail - head
    L2 = float(np.dot(seg, seg))
    if L2 < 1e-12:
        return float(np.linalg.norm(p - head))
    t = np.clip(np.dot(p - head, seg) / L2, 0.0, 1.0)
    proj = head + t * seg
    return float(np.linalg.norm(p - proj))

# Sort bones: palm territory (wrist + finger_0 metacarpals) vs finger phalanges
palm_segs = {'L': [], 'R': []}
finger_segs = {}   # (side, finger) -> [(name, head, tail), ...] for idx >= 1
for bd in BONES:
    name = bd['name']
    head = np.array(bd['head']); tail = np.array(bd['tail'])
    side = name[0]  # 'L' or 'R'
    parts = name.split('_')
    if not parts[-1].isdigit():
        palm_segs[side].append((name, head, tail))   # wrist -> palm territory
        continue
    idx = int(parts[-1])
    finger = parts[1]
    if idx == 0:
        # metacarpal -> palm territory (folds the boundary onto the knuckle line)
        palm_segs[side].append((name, head, tail))
    else:
        key = (side, finger)
        if key not in finger_segs:
            finger_segs[key] = []
        finger_segs[key].append((name, head, tail))

# Create all vertex groups
for bd in BONES:
    if bd['name'] not in mesh_obj.vertex_groups:
        mesh_obj.vertex_groups.new(name=bd['name'])

n_palm = 0; n_finger = 0
for vi, v in enumerate(verts):
    side = 'L' if v[0] < 0.0 else 'R'   # gate by hand — no cross-hand bleed
    wrist_name = side + '_wrist'

    # Layer 1a: distance to palm territory (this side's wrist + metacarpals)
    d_palm = float('inf')
    for nm, h, t in palm_segs[side]:
        d = seg_dist(v, h, t)
        if d < d_palm:
            d_palm = d

    # Layer 1b: nearest finger phalanx (this side only)
    d_finger = float('inf')
    best_bone = None
    for (s, finger), segs in finger_segs.items():
        if s != side:
            continue
        for nm, h, t in segs:
            d = seg_dist(v, h, t)
            if d < d_finger:
                d_finger = d
                best_bone = nm

    # Decision — palm wins ties (priority), fingers must be strictly closer
    if best_bone is not None and d_finger < d_palm:
        target = best_bone           # Layer 2: nearest phalanx
        n_finger += 1
    else:
        target = wrist_name          # Layer 2: palm verts belong to the wrist
        n_palm += 1

    mesh_obj.vertex_groups[target].add([vi], 1.0, 'REPLACE')

print("Done — palm-priority weights. palm verts:", n_palm, "finger verts:", n_finger)

bpy.ops.wm.save_as_mainfile(filepath=r'C:\Users\kmessai\Downloads\slayerhands_rigged.blend')
bpy.ops.export_scene.gltf(filepath=r'C:\Users\kmessai\Downloads\slayerhands_rigged.glb', export_format='GLB', export_skins=True)
print("Exported to Downloads")
