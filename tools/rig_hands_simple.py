"""
Simple hand rig — one bone per finger, palm to tip.
No medial axis tracing. Just endpoints + palm center → straight bones.
Get the bones INSIDE the mesh first. Add joints later.
"""
import trimesh
import numpy as np
from skimage.morphology import skeletonize
from scipy import ndimage
import json

MESH_PATH = '/home/khaled/Kore/slayerhands.glb'
OUTPUT_PATH = '/home/khaled/Kore/tools/rig_hands_blender.py'

mesh = trimesh.load(MESH_PATH, force='mesh')
pitch = 0.008
voxels = mesh.voxelized(pitch)
grid = ndimage.binary_fill_holes(voxels.matrix).astype(np.uint8)
origin = voxels.transform[:3, 3]
skeleton = skeletonize(grid).astype(np.uint8)
kernel = np.ones((3,3,3), dtype=np.uint8); kernel[1,1,1] = 0
nc = ndimage.convolve(skeleton, kernel, mode='constant', cval=0) * skeleton
endpoints = np.argwhere((skeleton > 0) & (nc == 1))

def to_world(idx): return np.array(idx, dtype=float) * pitch + origin
def to_blender(p): return [float(p[0]), float(-p[2]), float(p[1])]

ep_world = np.array([to_world(e) for e in endpoints])

# Classify endpoints
fingertips = ep_world[ep_world[:, 1] > 0]
wrists = ep_world[ep_world[:, 1] < 0]

left_tips = fingertips[fingertips[:, 0] < 0]
right_tips = fingertips[fingertips[:, 0] > 0]
left_wrist = wrists[wrists[:, 0] < 0].mean(axis=0)
right_wrist = wrists[wrists[:, 0] > 0].mean(axis=0)

# Thumb is INNERMOST (closest to X=0), pinky is OUTERMOST
left_tips = left_tips[left_tips[:, 0].argsort()[::-1]]  # least negative = thumb
right_tips = right_tips[right_tips[:, 0].argsort()]       # least positive = thumb

finger_names = ['thumb', 'index', 'middle', 'ring', 'pinky']

# Palm = 40% toward tips, 60% toward wrist
left_palm = np.mean(left_tips[:5], axis=0) * 0.4 + left_wrist * 0.6
right_palm = np.mean(right_tips[:5], axis=0) * 0.4 + right_wrist * 0.6

# Build bones
bones = []

# Wrist bones
bones.append({
    'name': 'L_wrist',
    'head': to_blender(left_wrist),
    'tail': to_blender(left_palm),
    'parent': None
})
bones.append({
    'name': 'R_wrist',
    'head': to_blender(right_wrist),
    'tail': to_blender(right_palm),
    'parent': None
})

# Finger bones — subdivided at anatomical knuckle ratios
# Thumb: 2 segments (1 knuckle at 50%)
# Other fingers: 3 segments (MCP at 33%, PIP at 60%, DIP at 80%)
FINGER_SPLITS = {
    'thumb': [0.5],              # one knuckle
    'index': [0.33, 0.60, 0.80],  # MCP, PIP, DIP
    'middle': [0.33, 0.60, 0.80],
    'ring':  [0.33, 0.60, 0.80],
    'pinky': [0.33, 0.60, 0.80],
}

def subdivide_finger(palm, tip, splits, name_prefix, parent_name):
    """Create a chain of bones from palm to tip, split at the given ratios."""
    result = []
    palm = np.array(palm)
    tip = np.array(tip)

    # All points: palm, splits, tip
    points = [palm]
    for t in splits:
        points.append(palm + (tip - palm) * t)
    points.append(tip)

    # Create bones between consecutive points
    current_parent = parent_name
    for bi in range(len(points) - 1):
        bone_name = f'{name_prefix}_{bi}'
        result.append({
            'name': bone_name,
            'head': to_blender(points[bi]),
            'tail': to_blender(points[bi + 1]),
            'parent': current_parent,
        })
        current_parent = bone_name
    return result

for i, tip in enumerate(left_tips[:5]):
    name = finger_names[i] if i < 5 else f'extra_{i}'
    splits = FINGER_SPLITS.get(name, [0.33, 0.60, 0.80])
    bones.extend(subdivide_finger(left_palm, tip, splits, f'L_{name}', 'L_wrist'))

for i, tip in enumerate(right_tips[:5]):
    name = finger_names[i] if i < 5 else f'extra_{i}'
    splits = FINGER_SPLITS.get(name, [0.33, 0.60, 0.80])
    bones.extend(subdivide_finger(right_palm, tip, splits, f'R_{name}', 'R_wrist'))

print(f"{len(bones)} bones: 2 wrists + {len(left_tips[:5])} left + {len(right_tips[:5])} right fingers")

# Generate Blender script
bones_str = json.dumps(bones, indent=2).replace(': null', ': None')

script = f'''"""Auto-generated simple hand rig — one bone per finger."""
import bpy
from mathutils import Vector
import numpy as np

MESH_PATH = r'{MESH_PATH}'
BONES = {bones_str}

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

bone_map = {{}}
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

bpy.ops.wm.save_as_mainfile(filepath=r'C:\\tmp\\slayerhands_rigged.blend')
bpy.ops.export_scene.gltf(filepath=r'C:\\tmp\\slayerhands_rigged.glb', export_format='GLB', export_skins=True)
print("Exported")
'''

with open(OUTPUT_PATH, 'w') as f:
    f.write(script)

print(f"Written to {OUTPUT_PATH}")
