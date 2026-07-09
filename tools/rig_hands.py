"""
Hand auto-rigging pipeline — medial axis → skeleton → weights → Blender script.

Same pipeline as the spider (auto_rig.py) adapted for hands:
- Two hands in one mesh (split by X coordinate)
- Five fingers per hand + wrist
- Joint detection tuned for finger proportions
- Proximity-based weights (rigid plates at finger segments, blend at knuckles)
"""

import trimesh
import numpy as np
from skimage.morphology import skeletonize
from scipy import ndimage
from scipy.spatial import KDTree
import json, os

MESH_PATH = '/home/khaled/Kore/slayerhands.glb'
OUTPUT_PATH = '/home/khaled/Kore/tools/rig_hands_blender.py'
PITCH = 0.008

# ═══════════════════════════════════════
# STEP 1: Voxelize + Skeletonize
# ═══════════════════════════════════════

print("Loading mesh...")
mesh = trimesh.load(MESH_PATH, force='mesh')
print(f"  {len(mesh.vertices)} verts, {len(mesh.faces)} faces")

print("Voxelizing...")
voxels = mesh.voxelized(PITCH)
grid = ndimage.binary_fill_holes(voxels.matrix).astype(np.uint8)
origin = voxels.transform[:3, 3]
print(f"  Grid: {grid.shape}")

print("Skeletonizing...")
skeleton = skeletonize(grid).astype(np.uint8)

kernel = np.ones((3,3,3), dtype=np.uint8); kernel[1,1,1] = 0
nc = ndimage.convolve(skeleton, kernel, mode='constant', cval=0) * skeleton
endpoints = np.argwhere((skeleton > 0) & (nc == 1))
print(f"  Endpoints: {len(endpoints)}")

def to_world(idx):
    return np.array(idx, dtype=float) * PITCH + origin

# ═══════════════════════════════════════
# STEP 2: Trace branches
# ═══════════════════════════════════════

def trace(skel, start, nc_grid):
    path = [tuple(start)]
    visited = {tuple(start)}
    current = start.copy()
    while True:
        neighbors = []
        for d in np.ndindex(3,3,3):
            d = np.array(d) - 1
            if np.all(d == 0): continue
            n = tuple(current + d)
            if (all(0 <= n[i] < skel.shape[i] for i in range(3))
                and skel[n] > 0 and n not in visited):
                neighbors.append(np.array(n))
        if not neighbors: break
        if len(path) > 1:
            dir_vec = current - np.array(path[-2])
            dots = [np.dot(nb - current, dir_vec) for nb in neighbors]
            nxt = neighbors[np.argmax(dots)]
        else:
            nxt = neighbors[0]
        path.append(tuple(nxt))
        visited.add(tuple(nxt))
        if nc_grid[nxt[0], nxt[1], nxt[2]] >= 3 or (nc_grid[nxt[0], nxt[1], nxt[2]] == 1 and len(path) > 1):
            break
        current = nxt
    return path

print("\nTracing branches...")
branches = []
for ep in endpoints:
    path = trace(skeleton, ep, nc)
    if len(path) < 3: continue
    path_world = np.array([to_world(p) for p in path])
    length = np.sum(np.linalg.norm(np.diff(path_world, axis=0), axis=1))
    branches.append({
        'tip': path_world[0],
        'root': path_world[-1],
        'length': length,
        'path': path_world,
    })

branches.sort(key=lambda b: b['length'], reverse=True)
print(f"  {len(branches)} branches found")

# ═══════════════════════════════════════
# STEP 3: Classify branches
# ═══════════════════════════════════════

print("\nClassifying branches...")

# Split into left hand (tip X < 0) and right hand (tip X > 0)
left_fingers = []
right_fingers = []
left_wrist = None
right_wrist = None

for b in branches:
    tip = b['tip']
    is_left = tip[0] < 0
    is_wrist = tip[1] < 0  # wrist endpoints are at negative Y

    if is_wrist:
        if is_left:
            left_wrist = b
        else:
            right_wrist = b
    else:
        if is_left:
            left_fingers.append(b)
        else:
            right_fingers.append(b)

# Sort fingers by X position (thumb is most outward, pinky most inward)
# Left hand: thumb is most negative X
left_fingers.sort(key=lambda b: b['tip'][0])
# Right hand: thumb is most positive X
right_fingers.sort(key=lambda b: b['tip'][0], reverse=True)

# Label them
finger_names = ['thumb', 'index', 'middle', 'ring', 'pinky']

print(f"  Left hand: {len(left_fingers)} fingers" + (" + wrist" if left_wrist else ""))
for i, f in enumerate(left_fingers):
    name = finger_names[i] if i < 5 else f'extra_{i}'
    f['name'] = f'L_{name}'
    print(f"    {f['name']}: length={f['length']:.3f}, tip=({f['tip'][0]:.3f}, {f['tip'][1]:.3f}, {f['tip'][2]:.3f})")

print(f"  Right hand: {len(right_fingers)} fingers" + (" + wrist" if right_wrist else ""))
for i, f in enumerate(right_fingers):
    name = finger_names[i] if i < 5 else f'extra_{i}'
    f['name'] = f'R_{name}'
    print(f"    {f['name']}: length={f['length']:.3f}, tip=({f['tip'][0]:.3f}, {f['tip'][1]:.3f}, {f['tip'][2]:.3f})")

if left_wrist:
    left_wrist['name'] = 'L_wrist'
    print(f"  L_wrist: length={left_wrist['length']:.3f}")
if right_wrist:
    right_wrist['name'] = 'R_wrist'
    print(f"  R_wrist: length={right_wrist['length']:.3f}")

# ═══════════════════════════════════════
# STEP 4: Joint detection along each finger
# ═══════════════════════════════════════

print("\nDetecting joints...")

def find_joints(path, n_joints=3, min_seg_frac=0.12):
    """Find joint positions along a path using curvature analysis."""
    if len(path) < 10:
        # Too short for proper analysis — evenly space joints
        indices = np.linspace(0, len(path)-1, n_joints+1, dtype=int)[1:]
        return path[indices]

    # Compute curvature as direction change
    tangents = np.diff(path, axis=0)
    tangents = tangents / (np.linalg.norm(tangents, axis=1, keepdims=True) + 1e-8)

    curvature = np.zeros(len(path))
    for i in range(1, len(tangents)):
        curvature[i] = 1 - np.dot(tangents[i], tangents[i-1])

    # Smooth curvature
    from scipy.ndimage import uniform_filter1d
    curvature_smooth = uniform_filter1d(curvature, size=max(3, len(path)//10))

    # Find peaks
    total_length = np.sum(np.linalg.norm(np.diff(path, axis=0), axis=1))
    min_seg = total_length * min_seg_frac

    # Cumulative arc length
    arc = np.zeros(len(path))
    for i in range(1, len(path)):
        arc[i] = arc[i-1] + np.linalg.norm(path[i] - path[i-1])

    joints = []
    for i in range(5, len(curvature_smooth) - 5):
        if curvature_smooth[i] > curvature_smooth[i-1] and curvature_smooth[i] > curvature_smooth[i+1]:
            # Check minimum segment distance from previous joints and endpoints
            too_close = False
            for j_arc in [0] + [arc[j] for j in joints] + [arc[-1]]:
                if abs(arc[i] - j_arc) < min_seg:
                    too_close = True
                    break
            if not too_close:
                joints.append(i)

    # If we found too many, keep the strongest
    if len(joints) > n_joints:
        joint_curvatures = [(j, curvature_smooth[j]) for j in joints]
        joint_curvatures.sort(key=lambda x: x[1], reverse=True)
        joints = sorted([j for j, _ in joint_curvatures[:n_joints]])

    # If we found too few, subdivide evenly
    while len(joints) < n_joints:
        # Find longest segment and split it
        all_points = [0] + joints + [len(path)-1]
        max_gap = 0
        max_idx = 0
        for i in range(len(all_points) - 1):
            gap = arc[all_points[i+1]] - arc[all_points[i]]
            if gap > max_gap:
                max_gap = gap
                max_idx = i
        # Insert midpoint
        mid_arc = (arc[all_points[max_idx]] + arc[all_points[max_idx+1]]) / 2
        mid_idx = np.argmin(np.abs(arc - mid_arc))
        joints.append(mid_idx)
        joints.sort()

    return path[joints]

all_finger_branches = left_fingers + right_fingers
for fb in all_finger_branches:
    path = fb['path']
    # Fingers have 3 joints (DIP, PIP, MCP) — but for the wraps,
    # 2 joints might be enough (knuckle + mid-finger)
    n_joints = 2 if 'thumb' in fb['name'] else 3
    joints = find_joints(path, n_joints=n_joints)
    fb['joints'] = joints
    print(f"  {fb['name']}: {len(joints)} joints detected")

# ═══════════════════════════════════════
# STEP 5: Center refinement (push bones to mesh center)
# ═══════════════════════════════════════

print("\nRefining bone centers...")
mesh_tree = KDTree(mesh.vertices)

def refine_center(point, mesh, mesh_tree, iterations=3):
    """Push a point toward the true center of the mesh cross-section."""
    pt = point.copy()
    for _ in range(iterations):
        dist, idx = mesh_tree.query(pt)
        nearest = mesh.vertices[idx]
        # Ray from nearest surface point through the current center
        direction = pt - nearest
        direction = direction / (np.linalg.norm(direction) + 1e-8)
        # Find opposite surface point
        hits = mesh.ray.intersects_location(
            ray_origins=[pt],
            ray_directions=[direction]
        )
        if len(hits[0]) > 0:
            opposite = hits[0][0]
            pt = (nearest + opposite) / 2
    return pt

for fb in all_finger_branches:
    refined_joints = []
    for j in fb['joints']:
        refined = refine_center(j, mesh, mesh_tree)
        refined_joints.append(refined)
    fb['joints'] = np.array(refined_joints)
    # Also refine tip and root
    fb['tip_refined'] = refine_center(fb['tip'], mesh, mesh_tree)
    fb['root_refined'] = refine_center(fb['root'], mesh, mesh_tree)

print("  Done")

# ═══════════════════════════════════════
# STEP 6: Generate Blender script
# ═══════════════════════════════════════

print("\nGenerating Blender script...")

# Build bone data
all_bones = []

# For each hand, create a root bone at the wrist
for side, fingers, wrist in [('L', left_fingers, left_wrist), ('R', right_fingers, right_wrist)]:
    # Hand root at the center of the palm (average of finger roots)
    if fingers:
        palm_center = np.mean([f['root'] for f in fingers], axis=0)
    else:
        continue

    wrist_pos = wrist['tip'] if wrist else palm_center - np.array([0, 0.15, 0])

    all_bones.append({
        'name': f'{side}_hand_root',
        'head': wrist_pos.tolist(),
        'tail': palm_center.tolist(),
        'parent': None,
    })

    for fb in fingers:
        # Build bone chain: root → joints → tip
        chain_points = [fb['root_refined']]
        for j in fb['joints']:
            chain_points.append(j)
        chain_points.append(fb['tip_refined'])

        # REVERSE chain: palm→fingertip, not fingertip→palm (gotcha #2)
        chain_points = chain_points[::-1]

        parent_name = f'{side}_hand_root'
        for bi in range(len(chain_points) - 1):
            bone_name = f"{fb['name']}_{bi}"
            all_bones.append({
                'name': bone_name,
                'head': chain_points[bi].tolist(),
                'tail': chain_points[bi+1].tolist(),
                'parent': parent_name,
            })
            parent_name = bone_name

# Convert all bone positions from trimesh/glTF space to Blender space
# glTF is Y-up, Blender is Z-up. After transform_apply:
# blender = (x, -z, y)
def to_blender(pos):
    return [pos[0], -pos[2], pos[1]]

for b in all_bones:
    b['head'] = to_blender(b['head'])
    b['tail'] = to_blender(b['tail'])

print(f"  {len(all_bones)} bones total (converted to Blender coords)")

# Branch paths for weight assignment (converted to Blender coords)
branch_paths = {}
for fb in all_finger_branches:
    branch_paths[fb['name']] = [[p[0], -p[2], p[1]] for p in fb['path'].tolist()]
if left_wrist:
    branch_paths['L_wrist'] = [[p[0], -p[2], p[1]] for p in left_wrist['path'].tolist()]
if right_wrist:
    branch_paths['R_wrist'] = [[p[0], -p[2], p[1]] for p in right_wrist['path'].tolist()]

# Write Blender script
script = f'''"""
Auto-generated hand rig script for Blender.
Run: blender --background --python {OUTPUT_PATH}
"""
import bpy
import json
from mathutils import Vector

MESH_PATH = r'{MESH_PATH}'
BONES = {json.dumps(all_bones, indent=2).replace(': null', ': None')}
BRANCH_PATHS = {json.dumps(branch_paths)}

# ── Clear scene ──
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

# ── Import mesh ──
bpy.ops.import_scene.gltf(filepath=MESH_PATH)
mesh_obj = None
for obj in bpy.context.scene.objects:
    if obj.type == 'MESH':
        mesh_obj = obj
        break

if not mesh_obj:
    raise RuntimeError("No mesh found in GLB")

# Apply transforms
bpy.context.view_layer.objects.active = mesh_obj
mesh_obj.select_set(True)
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

print(f"Mesh: {{len(mesh_obj.data.vertices)}} verts")

# ── Create armature ──
bpy.ops.object.armature_add(location=(0, 0, 0))
armature = bpy.context.object
armature.name = 'HandArmature'

bpy.ops.object.mode_set(mode='EDIT')

# Remove default bone
for b in armature.data.edit_bones:
    armature.data.edit_bones.remove(b)

# Create bones
bone_map = {{}}
for bd in BONES:
    bone = armature.data.edit_bones.new(bd['name'])
    bone.head = Vector(bd['head'])
    bone.tail = Vector(bd['tail'])
    bone_map[bd['name']] = bone

# Set parents
for bd in BONES:
    if bd['parent'] and bd['parent'] in bone_map:
        bone_map[bd['name']].parent = bone_map[bd['parent']]

bpy.ops.object.mode_set(mode='OBJECT')

# ── Parent mesh to armature ──
mesh_obj.select_set(True)
armature.select_set(True)
bpy.context.view_layer.objects.active = armature
bpy.ops.object.parent_set(type='ARMATURE_NAME')

# ── Weight painting: proximity to branch paths ──
print("Assigning weights...")

import numpy as np

verts = np.array([v.co for v in mesh_obj.data.vertices])

# For each bone, find the closest point on its segment (head→tail)
# and assign weight based on proximity
bone_data = []
for bd in BONES:
    head = np.array(bd['head'])
    tail = np.array(bd['tail'])
    bone_data.append((bd['name'], head, tail))

# Create vertex groups
for bd in BONES:
    if bd['name'] not in mesh_obj.vertex_groups:
        mesh_obj.vertex_groups.new(name=bd['name'])

# For each vertex, find closest bone and assign
for vi, v in enumerate(verts):
    best_bone = None
    best_dist = float('inf')

    for bname, head, tail in bone_data:
        # Point-to-segment distance
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
        vg = mesh_obj.vertex_groups[best_bone]
        vg.add([vi], 1.0, 'REPLACE')

print("Weights assigned")

# ── Save ──
output = r'C:\\tmp\\slayerhands_rigged.blend'
bpy.ops.wm.save_as_mainfile(filepath=output)
print(f"Saved to {{output}}")

# Also export as GLB
glb_output = r'C:\\tmp\\slayerhands_rigged.glb'
bpy.ops.export_scene.gltf(
    filepath=glb_output,
    export_format='GLB',
    export_skins=True,
)
print(f"Exported GLB to {{glb_output}}")
'''

with open(OUTPUT_PATH, 'w') as f:
    f.write(script)

print(f"\nBlender script written to {OUTPUT_PATH}")
print(f"Run: blender --background --python {OUTPUT_PATH}")
