"""
Medial Axis Skeleton Extraction
by Kore

Mesh → Voxelize → Skeletonize → Branch extraction → Text description
No landmarks needed. No AI guessing. Computational geometry.
"""

import trimesh
import numpy as np
from skimage.morphology import skeletonize
from scipy import ndimage
from scipy.spatial import KDTree

MESH_PATH = '/home/khaled/Kore/spider.glb'
VOXEL_PITCH = 0.012  # resolution in meters — smaller = more detail, slower

print("=" * 60)
print("MEDIAL AXIS SKELETON EXTRACTION")
print("=" * 60)

# Step 1: Load mesh
print("\n[1] Loading mesh...")
mesh = trimesh.load(MESH_PATH, force='mesh')
print(f"    Vertices: {len(mesh.vertices)}, Faces: {len(mesh.faces)}")
print(f"    Bounds: {mesh.bounds[0]} to {mesh.bounds[1]}")

# Step 2: Voxelize
print(f"\n[2] Voxelizing at pitch={VOXEL_PITCH}m...")
voxels = mesh.voxelized(VOXEL_PITCH)
grid = voxels.matrix.astype(np.uint8)
print(f"    Grid shape: {grid.shape}")
print(f"    Filled voxels: {grid.sum()}")
print(f"    Fill ratio: {grid.sum() / grid.size:.4f}")

# Fill any internal holes for better skeletonization
grid_filled = ndimage.binary_fill_holes(grid).astype(np.uint8)
print(f"    After hole fill: {grid_filled.sum()} voxels")

# Step 3: Skeletonize
print("\n[3] Skeletonizing (3D thinning)...")
skeleton = skeletonize(grid_filled).astype(np.uint8)
skel_points_idx = np.argwhere(skeleton > 0)
print(f"    Skeleton voxels: {len(skel_points_idx)}")

# Convert voxel indices back to world coordinates
skel_points = skel_points_idx * VOXEL_PITCH + voxels.transform[:3, 3]
print(f"    Skeleton points world coords range:")
print(f"      X: {skel_points[:,0].min():.4f} to {skel_points[:,0].max():.4f}")
print(f"      Y: {skel_points[:,1].min():.4f} to {skel_points[:,1].max():.4f}")
print(f"      Z: {skel_points[:,2].min():.4f} to {skel_points[:,2].max():.4f}")

# Step 4: Find branch structure
print("\n[4] Analyzing branch structure...")

# Build adjacency: for each skeleton voxel, count neighbors (26-connectivity)
def count_neighbors_3d(skel):
    """Count 26-connected neighbors for each voxel."""
    kernel = np.ones((3, 3, 3), dtype=np.uint8)
    kernel[1, 1, 1] = 0
    neighbor_count = ndimage.convolve(skel, kernel, mode='constant', cval=0)
    return neighbor_count * skel  # only for skeleton voxels

neighbor_counts = count_neighbors_3d(skeleton)

# Classify points
endpoints = np.argwhere((skeleton > 0) & (neighbor_counts == 1))
branch_points = np.argwhere((skeleton > 0) & (neighbor_counts >= 3))
regular_points = np.argwhere((skeleton > 0) & (neighbor_counts == 2))

endpoints_world = endpoints * VOXEL_PITCH + voxels.transform[:3, 3]
branch_world = branch_points * VOXEL_PITCH + voxels.transform[:3, 3]

print(f"    Endpoints (tips): {len(endpoints)}")
print(f"    Branch points (junctions): {len(branch_points)}")
print(f"    Regular points (mid-segment): {len(regular_points)}")

# Step 5: Trace branches
print("\n[5] Tracing branches from endpoints...")

def trace_branch(skeleton, start_idx, neighbor_counts_grid):
    """Trace a branch from an endpoint until hitting a branch point or another endpoint."""
    path = [tuple(start_idx)]
    visited = {tuple(start_idx)}
    current = start_idx.copy()

    while True:
        # Find unvisited neighbors
        neighbors = []
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                for dz in [-1, 0, 1]:
                    if dx == 0 and dy == 0 and dz == 0:
                        continue
                    nx, ny, nz = current[0]+dx, current[1]+dy, current[2]+dz
                    if (0 <= nx < skeleton.shape[0] and
                        0 <= ny < skeleton.shape[1] and
                        0 <= nz < skeleton.shape[2] and
                        skeleton[nx, ny, nz] > 0 and
                        (nx, ny, nz) not in visited):
                        neighbors.append(np.array([nx, ny, nz]))

        if len(neighbors) == 0:
            break

        # Pick the first unvisited neighbor
        next_pt = neighbors[0]
        path.append(tuple(next_pt))
        visited.add(tuple(next_pt))

        # Stop if we hit a branch point or another endpoint
        nc = neighbor_counts_grid[next_pt[0], next_pt[1], next_pt[2]]
        if nc >= 3 or (nc == 1 and len(path) > 1):
            break

        current = next_pt

    return path

branches = []
for ep in endpoints:
    branch = trace_branch(skeleton, ep, neighbor_counts)
    if len(branch) >= 3:  # skip tiny stubs
        branch_world_coords = np.array(branch) * VOXEL_PITCH + voxels.transform[:3, 3]
        length = np.sum(np.linalg.norm(np.diff(branch_world_coords, axis=0), axis=1))
        branches.append({
            'start': branch_world_coords[0],
            'end': branch_world_coords[-1],
            'path': branch_world_coords,
            'length': length,
            'n_points': len(branch),
        })

# Sort branches by length
branches.sort(key=lambda b: b['length'], reverse=True)

print(f"    Found {len(branches)} branches")
print()

# Step 6: Convert to Blender coordinates and describe
# glTF (Y-up): mesh coords → Blender (Z-up): X stays, Y = -Z_gltf, Z = Y_gltf
# BUT: the mesh vertices Khaled read were already in Blender space
# Let's check by comparing skeleton endpoints to known foot positions

KNOWN_FEET = [
    (0.699, -0.860, -0.301),       # FL
    (-0.9136, -0.858, -0.302),     # FR
    (0.850, -0.083, -0.314),       # ML
    (-1.049, -0.085, -0.309),      # MR
    (0.651, 0.859, -0.320),        # RL
    (-0.869, 0.868, -0.322),       # RR
]

def to_blender(pt):
    """Convert glTF Y-up to Blender Z-up."""
    return np.array([pt[0], -pt[2], pt[1]])

print("=" * 60)
print("BRANCH DESCRIPTIONS (in glTF coords)")
print("=" * 60)

for i, branch in enumerate(branches[:20]):
    start_b = to_blender(branch['start'])
    end_b = to_blender(branch['end'])

    # Check if either end is near a known foot
    foot_match = ""
    for fi, foot in enumerate(KNOWN_FEET):
        foot_arr = np.array(foot)
        if np.linalg.norm(start_b - foot_arr) < 0.1:
            foot_match = f" ← FOOT {fi}"
        elif np.linalg.norm(end_b - foot_arr) < 0.1:
            foot_match = f" ← FOOT {fi} (at end)"

    print(f"\nBranch {i}: length={branch['length']:.3f}m, {branch['n_points']} points{foot_match}")
    print(f"  Start (Blender): ({start_b[0]:.3f}, {start_b[1]:.3f}, {start_b[2]:.3f})")
    print(f"  End   (Blender): ({end_b[0]:.3f}, {end_b[1]:.3f}, {end_b[2]:.3f})")

    # Sample points along the branch for the text description
    path_blender = np.array([to_blender(p) for p in branch['path']])
    n_samples = min(5, len(path_blender))
    indices = np.linspace(0, len(path_blender)-1, n_samples, dtype=int)
    print(f"  Path samples (Blender coords):")
    for si in indices:
        p = path_blender[si]
        pct = si / max(len(path_blender)-1, 1) * 100
        print(f"    {pct:5.1f}%: ({p[0]:.3f}, {p[1]:.3f}, {p[2]:.3f})")

# Also output the raw skeleton points for visualization
print(f"\n\n{'='*60}")
print(f"SKELETON SUMMARY")
print(f"{'='*60}")
print(f"Total skeleton points: {len(skel_points_idx)}")
print(f"Endpoints: {len(endpoints)}")
print(f"Branch points: {len(branch_points)}")
print(f"Branches traced: {len(branches)}")
print(f"Longest branch: {branches[0]['length']:.3f}m" if branches else "No branches")

# Save skeleton points for potential visualization
np.save('/home/khaled/Kore/spider_skeleton_points.npy', skel_points)
print(f"\nSkeleton points saved to spider_skeleton_points.npy")
