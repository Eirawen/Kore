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
# json.dumps emits `null` for None; Python needs `None`. Convert every
# standalone null token (word-boundary regex handles nested/array cases too).
import re
bones_str = re.sub(r'\bnull\b', 'None', json.dumps(bones, indent=2))

# Blender runs on Windows and cannot resolve a bare /home/... Linux path,
# so hand it the UNC path into the WSL filesystem.
WIN_MESH_PATH = '\\\\wsl.localhost\\Ubuntu' + MESH_PATH.replace('/', '\\')

script = f'''"""Auto-generated simple hand rig — one bone per finger."""
import bpy
from mathutils import Vector
import numpy as np

MESH_PATH = r'{WIN_MESH_PATH}'
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
    \"\"\"Distance from point p to a bone segment [head, tail].\"\"\"
    seg = tail - head
    L2 = float(np.dot(seg, seg))
    if L2 < 1e-12:
        return float(np.linalg.norm(p - head))
    t = np.clip(np.dot(p - head, seg) / L2, 0.0, 1.0)
    proj = head + t * seg
    return float(np.linalg.norm(p - proj))

# Sort bones: palm territory (wrist + finger_0 metacarpals) vs finger phalanges
palm_segs = {{'L': [], 'R': []}}
finger_segs = {{}}   # (side, finger) -> [(name, head, tail), ...] for idx >= 1
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

bpy.ops.wm.save_as_mainfile(filepath=r'C:\\Users\\kmessai\\Downloads\\slayerhands_rigged.blend')
bpy.ops.export_scene.gltf(filepath=r'C:\\Users\\kmessai\\Downloads\\slayerhands_rigged.glb', export_format='GLB', export_skins=True)
print("Exported to Downloads")
'''

with open(OUTPUT_PATH, 'w') as f:
    f.write(script)

print(f"Written to {OUTPUT_PATH}")
