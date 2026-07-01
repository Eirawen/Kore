"""
Automatic Rigging Pipeline — Multi-Resolution Medial Axis
by Kore

Coarse pass (0.012m): find topology — which branches are legs, how they connect
Fine pass (0.003m): refine centerlines — precise positions along each identified limb

Best of both: stable topology + sub-centimeter precision.
"""

import trimesh
import numpy as np
from skimage.morphology import skeletonize
from scipy import ndimage
from scipy.spatial import KDTree

MESH_PATH = '/home/khaled/Kore/spider.glb'
OUTPUT_PATH = '/home/khaled/Kore/tools/rig_spider_auto.py'
COARSE_PITCH = 0.012
FINE_PITCH = 0.003

KNOWN_FEET_BLENDER = [
    ('FL', np.array([0.699, -0.860, -0.301])),
    ('FR', np.array([-0.9136, -0.858, -0.302])),
    ('ML', np.array([0.850, -0.083, -0.314])),
    ('MR', np.array([-1.049, -0.085, -0.309])),
    ('RL', np.array([0.651, 0.859, -0.320])),
    ('RR', np.array([-0.869, 0.868, -0.322])),
]

# ============================================================
# HELPERS
# ============================================================

def to_blender(pt):
    return np.array([pt[0], -pt[2], pt[1]])

def from_blender(pt):
    """Blender Z-up to glTF Y-up."""
    return np.array([pt[0], pt[2], -pt[1]])

def center_refine(path_blender, mesh, iterations=4):
    """
    Refine a medial axis path to the true geometric center.

    For each point on the path:
    1. Find nearest mesh surface → that's "outward"
    2. Cast ray in opposite direction → find other side
    3. Midpoint = better center
    4. Repeat until converged

    Works on the ORIGINAL mesh geometry, not the voxelization.
    """
    # Work in glTF space (mesh's native coords)
    path_gltf = np.array([from_blender(p) for p in path_blender])

    for iteration in range(iterations):
        refined = []
        for pt in path_gltf:
            # Find closest point on mesh surface
            closest_pt, closest_dist, closest_face = trimesh.proximity.closest_point(mesh, [pt])
            closest_pt = closest_pt[0]

            if closest_dist[0] < 1e-8:
                refined.append(pt)
                continue

            # Direction from skeleton point to nearest surface = outward
            outward = closest_pt - pt
            outward_norm = np.linalg.norm(outward)
            if outward_norm < 1e-8:
                refined.append(pt)
                continue
            outward_dir = outward / outward_norm

            # Cast ray in OPPOSITE direction to find the other side
            inward_dir = -outward_dir
            ray_origin = pt + inward_dir * 0.001  # tiny offset to avoid self-intersection

            hits = mesh.ray.intersects_location(
                ray_origins=[ray_origin],
                ray_directions=[inward_dir]
            )

            if len(hits[0]) > 0:
                # Find the nearest hit in the inward direction
                hit_pts = hits[0]
                hit_dists = np.linalg.norm(hit_pts - pt, axis=1)
                nearest_hit = hit_pts[np.argmin(hit_dists)]

                # True center = midpoint between the two surface points
                center = (closest_pt + nearest_hit) / 2.0
                refined.append(center)
            else:
                # Ray didn't hit anything — try multiple directions
                found_center = False
                for alt_dir in [np.array([1,0,0]), np.array([0,1,0]), np.array([0,0,1]),
                                np.array([-1,0,0]), np.array([0,-1,0]), np.array([0,0,-1])]:
                    hits2 = mesh.ray.intersects_location(
                        ray_origins=[pt],
                        ray_directions=[alt_dir]
                    )
                    hits3 = mesh.ray.intersects_location(
                        ray_origins=[pt],
                        ray_directions=[-alt_dir]
                    )
                    if len(hits2[0]) > 0 and len(hits3[0]) > 0:
                        p1 = hits2[0][np.argmin(np.linalg.norm(hits2[0] - pt, axis=1))]
                        p2 = hits3[0][np.argmin(np.linalg.norm(hits3[0] - pt, axis=1))]
                        center = (p1 + p2) / 2.0
                        refined.append(center)
                        found_center = True
                        break
                if not found_center:
                    refined.append(pt)

        path_gltf = np.array(refined)

    return np.array([to_blender(p) for p in path_gltf])

def voxelize_and_skeletonize(mesh, pitch):
    voxels = mesh.voxelized(pitch)
    grid = ndimage.binary_fill_holes(voxels.matrix).astype(np.uint8)
    origin = voxels.transform[:3, 3]
    skeleton = skeletonize(grid).astype(np.uint8)

    kernel = np.ones((3, 3, 3), dtype=np.uint8)
    kernel[1, 1, 1] = 0
    nc = ndimage.convolve(skeleton, kernel, mode='constant', cval=0) * skeleton

    endpoints = np.argwhere((skeleton > 0) & (nc == 1))
    return skeleton, nc, endpoints, origin, voxels

def trace_branch(skel, start, nc_grid):
    path = [tuple(start)]
    visited = {tuple(start)}
    current = start.copy()
    while True:
        neighbors = []
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                for dz in [-1, 0, 1]:
                    if dx == 0 and dy == 0 and dz == 0:
                        continue
                    n = (current[0]+dx, current[1]+dy, current[2]+dz)
                    if (0 <= n[0] < skel.shape[0] and
                        0 <= n[1] < skel.shape[1] and
                        0 <= n[2] < skel.shape[2] and
                        skel[n[0], n[1], n[2]] > 0 and
                        n not in visited):
                        neighbors.append(np.array(n))
        if not neighbors:
            break
        next_pt = neighbors[0]
        path.append(tuple(next_pt))
        visited.add(tuple(next_pt))
        if nc_grid[next_pt[0], next_pt[1], next_pt[2]] >= 3 or \
           (nc_grid[next_pt[0], next_pt[1], next_pt[2]] == 1 and len(path) > 1):
            break
        current = next_pt
    return path

def extract_branches(skeleton, nc, endpoints, origin, pitch):
    branches = []
    for ep in endpoints:
        path_voxels = trace_branch(skeleton, ep, nc)
        if len(path_voxels) < 3:
            continue
        path_world = np.array(path_voxels) * pitch + origin
        path_blender = np.array([to_blender(p) for p in path_world])
        length = np.sum(np.linalg.norm(np.diff(path_blender, axis=0), axis=1))
        branches.append({'path': path_blender, 'length': length})
    branches.sort(key=lambda b: b['length'], reverse=True)
    return branches

def match_legs(branches, known_feet, threshold=0.15):
    legs = {}
    other = []
    for branch in branches:
        start = branch['path'][0]
        matched = False
        for label, foot_pos in known_feet:
            if label not in legs and np.linalg.norm(start - foot_pos) < threshold:
                legs[label] = branch
                matched = True
                break
        if not matched:
            other.append(branch)
    return legs, other

def find_joints(path, n_joints=5):
    from scipy.ndimage import uniform_filter1d

    if len(path) < 10:
        indices = np.linspace(0, len(path)-1, min(n_joints, len(path)), dtype=int)
        return path[indices]

    smoothed = np.copy(path).astype(float)
    for axis in range(3):
        smoothed[:, axis] = uniform_filter1d(smoothed[:, axis], size=max(5, len(path)//20))

    dirs = np.diff(smoothed, axis=0)
    norms = np.linalg.norm(dirs, axis=1, keepdims=True)
    norms[norms == 0] = 1
    dirs = dirs / norms

    dots = np.sum(dirs[:-1] * dirs[1:], axis=1)
    dots = np.clip(dots, -1, 1)
    angles = np.arccos(dots)

    if len(angles) > 5:
        angles_smooth = uniform_filter1d(angles, size=max(5, len(angles)//15))
    else:
        angles_smooth = angles

    n_internal = n_joints - 1
    min_separation = len(angles_smooth) // (n_internal + 2)
    joint_indices = []

    angles_copy = angles_smooth.copy()
    for _ in range(n_internal):
        if angles_copy.max() < 0.01:
            break
        peak_idx = np.argmax(angles_copy)
        joint_indices.append(peak_idx + 1)
        lo = max(0, peak_idx - min_separation)
        hi = min(len(angles_copy), peak_idx + min_separation + 1)
        angles_copy[lo:hi] = 0

    joint_indices.sort()
    all_indices = [0] + joint_indices + [len(path) - 1]

    # Merge tiny segments
    total_length = np.sum(np.linalg.norm(np.diff(path, axis=0), axis=1))
    min_seg = max(total_length / (n_joints * 3), 0.03)

    filtered = [all_indices[0]]
    for i in range(1, len(all_indices) - 1):
        if np.linalg.norm(path[all_indices[i]] - path[filtered[-1]]) >= min_seg:
            filtered.append(all_indices[i])
    end_pos = path[all_indices[-1]]
    if len(filtered) > 1 and np.linalg.norm(end_pos - path[filtered[-1]]) < min_seg:
        filtered.pop()
    filtered.append(all_indices[-1])

    return path[filtered]


# ============================================================
# COARSE PASS — topology
# ============================================================

print("=" * 60)
print("COARSE PASS (topology)")
print("=" * 60)

mesh = trimesh.load(MESH_PATH, force='mesh')

print(f"[1] Voxelizing at {COARSE_PITCH}m...")
skel_c, nc_c, ep_c, origin_c, vox_c = voxelize_and_skeletonize(mesh, COARSE_PITCH)
branches_c = extract_branches(skel_c, nc_c, ep_c, origin_c, COARSE_PITCH)
print(f"    Branches: {len(branches_c)}, Endpoints: {len(ep_c)}")

legs_c, other_c = match_legs(branches_c, KNOWN_FEET_BLENDER)
print(f"    Legs matched: {list(legs_c.keys())}")

# Classify non-leg branches
if len(other_c) >= 3:
    for b in other_c:
        tip = b['path'][0]
        min_dist = min(np.linalg.norm(tip - b2['path'][0]) for b2 in other_c if b2 is not b)
        b['_isolation'] = min_dist
    abdomen_branch = max(other_c, key=lambda b: b['_isolation'])
else:
    abdomen_branch = other_c[0] if other_c else None

leg_ends = np.array([b['path'][-1] for b in legs_c.values()])
body_center_coarse = leg_ends.mean(axis=0)

print(f"    Body center: ({body_center_coarse[0]:.3f}, {body_center_coarse[1]:.3f}, {body_center_coarse[2]:.3f})")
if abdomen_branch:
    print(f"    Abdomen: ({abdomen_branch['path'][0][0]:.3f}, {abdomen_branch['path'][0][1]:.3f}, {abdomen_branch['path'][0][2]:.3f})")

avg_leg_len = np.mean([b['length'] for b in legs_c.values()])
remaining = [b for b in other_c if b is not abdomen_branch]
pedipalps = [b for b in remaining if b['length'] > avg_leg_len * 0.2]
fangs = [b for b in remaining if avg_leg_len * 0.04 < b['length'] <= avg_leg_len * 0.2]

print(f"    Pedipalps: {len(pedipalps)}, Fangs: {len(fangs)}")

# ============================================================
# FINE PASS — precision refinement
# ============================================================

print(f"\n{'=' * 60}")
print("FINE PASS (precision)")
print("=" * 60)

print(f"[2] Voxelizing at {FINE_PITCH}m...")
skel_f, nc_f, ep_f, origin_f, vox_f = voxelize_and_skeletonize(mesh, FINE_PITCH)
fine_skel_points = np.argwhere(skel_f > 0) * FINE_PITCH + origin_f
fine_skel_blender = np.array([to_blender(p) for p in fine_skel_points])
fine_tree = KDTree(fine_skel_blender)
print(f"    Fine skeleton points: {len(fine_skel_blender)}")

def refine_path(coarse_path, fine_tree, fine_points):
    """Snap each coarse path point to the nearest fine skeleton point."""
    refined = []
    for pt in coarse_path:
        dist, idx = fine_tree.query(pt)
        refined.append(fine_points[idx])
    return np.array(refined)

def resample_path_fine(coarse_path, fine_tree, fine_points, n_samples=None):
    """Resample the path using fine skeleton points between coarse waypoints."""
    if n_samples is None:
        n_samples = max(len(coarse_path) * 3, 20)

    # For each pair of consecutive coarse points, find fine skeleton points
    # that lie near the line between them
    full_path = []
    for i in range(len(coarse_path) - 1):
        start = coarse_path[i]
        end = coarse_path[i + 1]
        seg_vec = end - start
        seg_len = np.linalg.norm(seg_vec)
        if seg_len < 1e-6:
            full_path.append(start)
            continue

        seg_dir = seg_vec / seg_len

        # Find fine points near this segment
        mid = (start + end) / 2
        radius = seg_len * 0.7
        nearby_idx = fine_tree.query_ball_point(mid, radius)
        if not nearby_idx:
            full_path.append(start)
            continue

        nearby = fine_points[nearby_idx]

        # Project onto segment axis, keep points within segment bounds and close to axis
        projections = np.dot(nearby - start, seg_dir)
        lateral_dist = np.linalg.norm(nearby - start - np.outer(projections, seg_dir), axis=1)

        mask = (projections >= -0.02) & (projections <= seg_len + 0.02) & (lateral_dist < seg_len * 0.3)
        segment_points = nearby[mask]
        segment_proj = projections[mask]

        if len(segment_points) < 2:
            full_path.append(start)
            continue

        # Sort by projection along segment
        order = np.argsort(segment_proj)
        segment_points = segment_points[order]

        # Subsample to avoid too many points
        if len(segment_points) > 10:
            indices = np.linspace(0, len(segment_points)-1, 10, dtype=int)
            segment_points = segment_points[indices]

        full_path.extend(segment_points[:-1].tolist())

    full_path.append(coarse_path[-1].tolist())
    return np.array(full_path)

# Refine each leg path
print("[3] Refining leg paths...")
legs_refined = {}
for label, branch in legs_c.items():
    coarse_path = branch['path']
    refined_path = resample_path_fine(coarse_path, fine_tree, fine_skel_blender)
    legs_refined[label] = refined_path
    print(f"    Leg {label}: {len(coarse_path)} coarse → {len(refined_path)} refined points")

# CENTER REFINEMENT — push paths to true geometric center
print("\n[3.5] Center refinement (surface averaging)...")
for label, path in legs_refined.items():
    centered = center_refine(path, mesh, iterations=4)
    legs_refined[label] = centered
    # Measure improvement
    orig_dists = trimesh.proximity.closest_point(mesh, np.array([from_blender(p) for p in path]))[1]
    new_dists = trimesh.proximity.closest_point(mesh, np.array([from_blender(p) for p in centered]))[1]
    print(f"    Leg {label}: avg surface dist {orig_dists.mean():.4f}m → {new_dists.mean():.4f}m")

# Find joints on refined + centered paths
print("\n[4] Detecting joints on centered paths...")
leg_joints = {}
for label, path in legs_refined.items():
    joints = find_joints(path, n_joints=5)
    # Don't force subdivisions — let the mesh dictate joint count
    # Mid legs with 4 joints get tiptoe from tibia rotation instead
    leg_joints[label] = joints
    print(f"    Leg {label}: {len(joints)} joints")
    for i, j in enumerate(joints):
        print(f"      Joint {i}: ({j[0]:.4f}, {j[1]:.4f}, {j[2]:.4f})")

# Refine body center from refined leg endpoints
body_center = np.mean([path[-1] for path in legs_refined.values()], axis=0)
print(f"\n    Body center (refined): ({body_center[0]:.3f}, {body_center[1]:.3f}, {body_center[2]:.3f})")

# Refine abdomen and appendage paths
if abdomen_branch:
    abdomen_tip = refine_path(abdomen_branch['path'][[0]], fine_tree, fine_skel_blender)[0]
pedipalps_refined = []
for palp in pedipalps:
    pedipalps_refined.append(refine_path(palp['path'], fine_tree, fine_skel_blender))
fangs_refined = []
for fang in fangs:
    fangs_refined.append(refine_path(fang['path'], fine_tree, fine_skel_blender))

# ============================================================
# GENERATE BLENDER SCRIPT
# ============================================================

print(f"\n{'=' * 60}")
print("GENERATING BLENDER SCRIPT")
print("=" * 60)

def fmt(v):
    return f"({v[0]:.6f}, {v[1]:.6f}, {v[2]:.6f})"

lines = []
lines.append('"""')
lines.append('Auto-generated Spider Rig — Multi-Resolution Medial Axis')
lines.append('by Kore — coarse topology + fine precision')
lines.append('"""')
lines.append('')
lines.append('import bpy')
lines.append('import mathutils')
lines.append('from mathutils import Vector')
lines.append('')
lines.append('def find_mesh():')
lines.append('    for obj in bpy.data.objects:')
lines.append('        if obj.type == "MESH" and "Mesh" in obj.name:')
lines.append('            return obj')
lines.append('    for obj in bpy.data.objects:')
lines.append('        if obj.type == "MESH":')
lines.append('            return obj')
lines.append('    return None')
lines.append('')
lines.append('def add_bone(arm, name, head, tail, parent=None, connect=False):')
lines.append('    bone = arm.data.edit_bones.new(name)')
lines.append('    bone.head = Vector(head)')
lines.append('    bone.tail = Vector(tail)')
lines.append('    if parent and parent in arm.data.edit_bones:')
lines.append('        bone.parent = arm.data.edit_bones[parent]')
lines.append('        bone.use_connect = connect')
lines.append('    return bone')
lines.append('')
lines.append('def build():')
lines.append('    mesh = find_mesh()')
lines.append('    if not mesh:')
lines.append('        print("No mesh found!")')
lines.append('        return')
lines.append('')
lines.append('    # Clean up old rigs')
lines.append('    for obj in list(bpy.data.objects):')
lines.append('        if "SpiderRig" in obj.name:')
lines.append('            bpy.data.objects.remove(obj, do_unlink=True)')
lines.append('    for arm in list(bpy.data.armatures):')
lines.append('        if "SpiderArmature" in arm.name:')
lines.append('            bpy.data.armatures.remove(arm)')
lines.append('')
lines.append('    # Clear parent and APPLY ALL TRANSFORMS')
lines.append('    # This bakes location+rotation into vertices so everything is in world space')
lines.append('    mesh.select_set(True)')
lines.append('    bpy.context.view_layer.objects.active = mesh')
lines.append('    bpy.ops.object.parent_clear(type="CLEAR_KEEP_TRANSFORM")')
lines.append('    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)')
lines.append('    bpy.ops.object.select_all(action="DESELECT")')
lines.append('    print(f"Mesh after apply: loc={mesh.location}, rot={mesh.rotation_euler}")')
lines.append('')
lines.append('    # After transform_apply, mesh.location should be (0,0,0)')
lines.append('    # Create armature at origin — same space as mesh vertices now')
lines.append('    bpy.ops.object.armature_add(enter_editmode=True, location=(0, 0, 0))')
lines.append('    arm = bpy.context.object')
lines.append('    arm.name = "SpiderRig"')
lines.append('    arm.data.name = "SpiderArmature"')
lines.append('    default = arm.data.edit_bones.get("Bone")')
lines.append('    if default:')
lines.append('        arm.data.edit_bones.remove(default)')
lines.append('')

# Body bones
bc = body_center
lines.append(f'    add_bone(arm, "root", {fmt(bc)}, ({bc[0]:.6f}, {bc[1]:.6f}, {bc[2] + 0.08:.6f}))')
lines.append(f'    add_bone(arm, "cephalothorax", {fmt(bc)}, ({bc[0]:.6f}, {bc[1]:.6f}, {bc[2] + 0.12:.6f}), "root")')

if abdomen_branch:
    abd = abdomen_tip
    abd_dir = abd - bc
    abd_dir_n = abd_dir / max(np.linalg.norm(abd_dir), 1e-6)
    abd_start = bc + abd_dir_n * 0.1
    lines.append(f'    add_bone(arm, "abdomen", {fmt(abd_start)}, {fmt(abd)}, "root")')
lines.append('')

# Leg bones
bone_names_all = []
for label in ['FL', 'FR', 'ML', 'MR', 'RL', 'RR']:
    if label not in leg_joints:
        continue
    joints = leg_joints[label][::-1]  # REVERSE: body→foot, not foot→body
    lines.append(f'    # Leg {label}')
    seg_names = ['coxa', 'femur', 'tibia', 'tarsus', 'seg4', 'seg5']
    bone_names_in_leg = []
    for i in range(len(joints) - 1):
        bone_name = f'leg_{label}_{seg_names[min(i, len(seg_names)-1)]}'
        parent = 'cephalothorax' if i == 0 else bone_names_in_leg[-1]
        connect = i > 0
        lines.append(f'    add_bone(arm, "{bone_name}", {fmt(joints[i])}, {fmt(joints[i+1])}, "{parent}", {connect})')
        bone_names_in_leg.append(bone_name)
        bone_names_all.append(bone_name)
    lines.append('')

# Pedipalps
for pi, path in enumerate(pedipalps_refined):
    side = 'L' if pi == 0 else 'R'
    tip, base = path[0], path[-1]
    mid = path[len(path)//2]
    lines.append(f'    add_bone(arm, "pedipalp_{side}_base", {fmt(base)}, {fmt(mid)}, "cephalothorax")')
    lines.append(f'    add_bone(arm, "pedipalp_{side}_tip", {fmt(mid)}, {fmt(tip)}, "pedipalp_{side}_base", True)')
    lines.append('')

# Fangs
for fi, path in enumerate(fangs_refined):
    side = 'L' if fi == 0 else 'R'
    tip, base = path[0], path[-1]
    lines.append(f'    add_bone(arm, "fang_{side}", {fmt(base)}, {fmt(tip)}, "cephalothorax")')
    lines.append('')

# ================================================================
# TWO-LAYER WEIGHT ASSIGNMENT
#
# Layer 1: BRANCH SEGMENTATION — which body part does each vertex belong to?
#   Uses medial axis branch paths (not bone proximity).
#   Each vertex → closest branch centerline → that's its body part.
#   At branch junctions: blend between body and leg (articular membrane).
#
# Layer 2: RIGID PLATE WEIGHTING — within the assigned body part, which bone?
#   Standard chitin physics: rigid plates + linear blend at joints.
#
# This replaces the broken body-priority heuristic with actual
# anatomical segmentation from the medial axis data.
# ================================================================

# Embed branch paths for segmentation (subsampled to 15 points each)
branch_paths = {}
for label, path in legs_refined.items():
    indices = np.linspace(0, len(path)-1, min(15, len(path)), dtype=int)
    sampled = path[indices]
    branch_paths[f'leg_{label}'] = sampled.tolist()

# Body path: use body center as a single point expanded to a sphere
branch_paths['body'] = [body_center.tolist()]

# Abdomen path
if abdomen_branch:
    abd_path = abdomen_branch['path']
    indices = np.linspace(0, len(abd_path)-1, min(8, len(abd_path)), dtype=int)
    branch_paths['abdomen'] = abd_path[indices].tolist()

# Pedipalp/fang paths
for pi, path in enumerate(pedipalps_refined):
    side = 'L' if pi == 0 else 'R'
    indices = np.linspace(0, len(path)-1, min(6, len(path)), dtype=int)
    branch_paths[f'pedipalp_{side}'] = path[indices].tolist()
for fi, path in enumerate(fangs_refined):
    side = 'L' if fi == 0 else 'R'
    branch_paths[f'fang_{side}'] = path[min(0, len(path)-1):].tolist()

import json
lines.append('    bpy.ops.object.mode_set(mode="OBJECT")')
lines.append('    bpy.ops.object.select_all(action="DESELECT")')
lines.append('    mesh.select_set(True)')
lines.append('    arm.select_set(True)')
lines.append('    bpy.context.view_layer.objects.active = arm')
lines.append('    bpy.ops.object.parent_set(type="ARMATURE_NAME")')
lines.append('')
lines.append('    print("Computing two-layer weights...")')
lines.append('    print("  Layer 1: Branch segmentation (medial axis paths)")')
lines.append('    print("  Layer 2: Rigid plate + joint blend (chitin physics)")')
lines.append('    bpy.context.view_layer.objects.active = mesh')
lines.append('')
lines.append(f'    BRANCH_PATHS = {json.dumps({k: [[round(c,4) for c in p] for p in v] for k, v in branch_paths.items()})}')
lines.append('')
lines.append('    JOINT_BLEND_WIDTH = 0.025')
lines.append('    BRANCH_BLEND_WIDTH = 0.04  # blend zone at leg-body junction')
lines.append('')
lines.append('    def dist_to_path(p, path_points):')
lines.append('        """Minimum distance from point p to a polyline path."""')
lines.append('        min_d = float("inf")')
lines.append('        for i in range(len(path_points)):')
lines.append('            pt = Vector(path_points[i])')
lines.append('            d = (p - pt).length')
lines.append('            if d < min_d:')
lines.append('                min_d = d')
lines.append('        # Also check segments between consecutive points')
lines.append('        for i in range(len(path_points) - 1):')
lines.append('            a = Vector(path_points[i])')
lines.append('            b = Vector(path_points[i+1])')
lines.append('            ab = b - a')
lines.append('            ab_sq = ab.dot(ab)')
lines.append('            if ab_sq < 1e-10:')
lines.append('                continue')
lines.append('            t = max(0, min(1, (p - a).dot(ab) / ab_sq))')
lines.append('            closest = a + ab * t')
lines.append('            d = (p - closest).length')
lines.append('            if d < min_d:')
lines.append('                min_d = d')
lines.append('        return min_d')
lines.append('')
lines.append('    def project_onto_bone(p, a, b):')
lines.append('        ab = b - a')
lines.append('        ab_sq = ab.dot(ab)')
lines.append('        if ab_sq < 1e-10:')
lines.append('            return (p - a).length, 0.5')
lines.append('        t = max(0, min(1, (p - a).dot(ab) / ab_sq))')
lines.append('        closest = a + ab * t')
lines.append('        return (p - closest).length, t')
lines.append('')
lines.append('    # Build bone chain data')
lines.append('    bone_data = []')
lines.append('    bone_chains = {}')
lines.append('    for bone in arm.data.bones:')
lines.append('        h = arm.matrix_world @ bone.head_local')
lines.append('        t = arm.matrix_world @ bone.tail_local')
lines.append('        name = bone.name')
lines.append('        if name.startswith("leg_"):')
lines.append('            group = "_".join(name.split("_")[:2])')
lines.append('        elif "pedipalp" in name:')
lines.append('            group = "pedipalp_" + name.split("_")[1]')
lines.append('        elif "fang" in name:')
lines.append('            group = "fang_" + name.split("_")[1]')
lines.append('        else:')
lines.append('            group = "body"')
lines.append('        if group not in bone_chains:')
lines.append('            bone_chains[group] = []')
lines.append('        chain_idx = len(bone_chains[group])')
lines.append('        bone_chains[group].append(name)')
lines.append('        bone_data.append((name, h, t, group, chain_idx))')
lines.append('')
lines.append('    mesh_world = mesh.matrix_world')
lines.append('    for v in mesh.data.vertices:')
lines.append('        v_world = mesh_world @ v.co')
lines.append('')
lines.append('        # === LAYER 1: Branch segmentation ===')
lines.append('        # Find closest branch path for this vertex')
lines.append('        branch_dists = {}')
lines.append('        for branch_name, path_pts in BRANCH_PATHS.items():')
lines.append('            branch_dists[branch_name] = dist_to_path(v_world, path_pts)')
lines.append('')
lines.append('        sorted_branches = sorted(branch_dists.items(), key=lambda x: x[1])')
lines.append('        best_branch = sorted_branches[0][0]')
lines.append('        best_branch_dist = sorted_branches[0][1]')
lines.append('')
lines.append('        # Map branch name to bone group')
lines.append('        if best_branch == "body":')
lines.append('            assigned_group = "body"')
lines.append('        elif best_branch == "abdomen":')
lines.append('            assigned_group = "body"  # abdomen is a body bone')
lines.append('        else:')
lines.append('            assigned_group = best_branch')
lines.append('')
lines.append('        # Check for branch junction blend (leg meets body)')
lines.append('        branch_blend = None')
lines.append('        if len(sorted_branches) > 1:')
lines.append('            second_branch = sorted_branches[1][0]')
lines.append('            second_dist = sorted_branches[1][1]')
lines.append('            gap = second_dist - best_branch_dist')
lines.append('            if gap < BRANCH_BLEND_WIDTH:')
lines.append('                # At junction — check if it is a leg-body boundary')
lines.append('                is_leg_body = (best_branch.startswith("leg_") and second_branch in ("body", "abdomen")) or \\')
lines.append('                              (second_branch.startswith("leg_") and best_branch in ("body", "abdomen"))')
lines.append('                if is_leg_body:')
lines.append('                    blend_factor = gap / BRANCH_BLEND_WIDTH  # 0=at junction, 1=at edge')
lines.append('                    branch_blend = (best_branch, second_branch, blend_factor)')
lines.append('')
lines.append('        # === LAYER 2: Within-branch bone weighting ===')
lines.append('        if assigned_group not in bone_chains:')
lines.append('            assigned_group = "body"')
lines.append('')
lines.append('        # Find closest bone WITHIN the assigned group')
lines.append('        best_dist = float("inf")')
lines.append('        best_bone = None')
lines.append('        best_t = 0')
lines.append('        best_cidx = 0')
lines.append('        for bname, bh, bt, bgroup, cidx in bone_data:')
lines.append('            if bgroup != assigned_group:')
lines.append('                continue')
lines.append('            d, t = project_onto_bone(v_world, bh, bt)')
lines.append('            if d < best_dist:')
lines.append('                best_dist = d')
lines.append('                best_bone = bname')
lines.append('                best_t = t')
lines.append('                best_cidx = cidx')
lines.append('')
lines.append('        if best_bone is None:')
lines.append('            # Fallback: closest bone of any group')
lines.append('            for bname, bh, bt, bgroup, cidx in bone_data:')
lines.append('                d, t = project_onto_bone(v_world, bh, bt)')
lines.append('                if d < best_dist:')
lines.append('                    best_dist = d')
lines.append('                    best_bone = bname')
lines.append('                    best_t = t')
lines.append('                    best_cidx = cidx')
lines.append('                    assigned_group = bgroup')
lines.append('')
lines.append('        chain = bone_chains.get(assigned_group, [best_bone])')
lines.append('        bone_head = bone_tail = None')
lines.append('        for bname, bh, bt, bg, ci in bone_data:')
lines.append('            if bname == best_bone:')
lines.append('                bone_head, bone_tail = bh, bt')
lines.append('                break')
lines.append('        bone_length = (bone_tail - bone_head).length if bone_head and bone_tail else 0.1')
lines.append('        blend_t = min(JOINT_BLEND_WIDTH / max(bone_length, 0.01), 0.4)')
lines.append('')
lines.append('        weights = {}')
lines.append('')
lines.append('        # Joint blend within the bone chain')
lines.append('        if best_t < blend_t and best_cidx > 0:')
lines.append('            prev_bone = chain[best_cidx - 1]')
lines.append('            factor = best_t / blend_t')
lines.append('            weights[best_bone] = factor')
lines.append('            weights[prev_bone] = 1.0 - factor')
lines.append('        elif best_t > (1.0 - blend_t) and best_cidx < len(chain) - 1:')
lines.append('            next_bone = chain[best_cidx + 1]')
lines.append('            factor = (1.0 - best_t) / blend_t')
lines.append('            weights[best_bone] = factor')
lines.append('            weights[next_bone] = 1.0 - factor')
lines.append('        else:')
lines.append('            weights[best_bone] = 1.0')
lines.append('')
lines.append('        # Apply branch junction blend (leg ↔ body)')
lines.append('        if branch_blend:')
lines.append('            _, _, bf = branch_blend')
lines.append('            # bf=0 at junction (50/50), bf=1 at edge (100% assigned branch)')
lines.append('            body_weight = (1.0 - bf) * 0.5')
lines.append('            leg_weight = 1.0 - body_weight')
lines.append('            body_bone_name = "cephalothorax"')
lines.append('            adjusted = {}')
lines.append('            for bname, w in weights.items():')
lines.append('                adjusted[bname] = w * leg_weight')
lines.append('            adjusted[body_bone_name] = adjusted.get(body_bone_name, 0) + body_weight')
lines.append('            weights = adjusted')
lines.append('')
lines.append('        for bname, w in weights.items():')
lines.append('            if w < 0.001:')
lines.append('                continue')
lines.append('            if bname not in mesh.vertex_groups:')
lines.append('                mesh.vertex_groups.new(name=bname)')
lines.append('            mesh.vertex_groups[bname].add([v.index], w, "REPLACE")')
lines.append('')
lines.append('    print("=" * 50)')
lines.append('    print("RIGGING COMPLETE")')
lines.append('    print("  Two-layer weights: branch segmentation + rigid plates")')
lines.append('    print(f"  Bones: {len(arm.data.bones)}")')
lines.append('    print("=" * 50)')
lines.append('')
lines.append('try:')
lines.append('    build()')
lines.append('except Exception as e:')
lines.append('    print(f"Error: {e}")')
lines.append('    import traceback')
lines.append('    traceback.print_exc()')

with open(OUTPUT_PATH, 'w') as f:
    f.write('\n'.join(lines))

import shutil
shutil.copy(OUTPUT_PATH, '/mnt/c/Users/kmessai/Downloads/rig_spider_auto.py')

print(f"\nBlender script written to {OUTPUT_PATH}")
print(f"Copied to Downloads/rig_spider_auto.py")
