import trimesh
import numpy as np

mesh = trimesh.load('/home/khaled/Kore/spider.glb', force='mesh')
verts = mesh.vertices

# glTF coordinate system: Y is up, X is left-right, Z is front-back
# From the images: spider faces negative Z (front legs at low Z, rear at high Z)
# Y is up/down (ground at low Y, top at high Y)

print("="*60)
print("SPIDER LANDMARK ANALYSIS")
print("="*60)

# === FOOT TIPS ===
# Foot tips are the lowest (most negative Y) vertices at the extremes
# They should be at the tips of the legs

# Get all vertices below Y = -0.2 (near ground level)
ground_verts_mask = verts[:, 1] < -0.2
ground_verts = verts[ground_verts_mask]
ground_indices = np.where(ground_verts_mask)[0]

print(f"\nVertices near ground (Y < -0.2): {len(ground_verts)}")

# Cluster ground vertices by XZ position to find distinct foot groups
from scipy.spatial import KDTree

# Project to XZ plane for clustering
ground_xz = ground_verts[:, [0, 2]]

# Find 6 foot clusters using farthest point sampling on XZ
def farthest_point_sample_2d(points, n):
    selected = [np.argmax(np.linalg.norm(points - points.mean(axis=0), axis=1))]
    for _ in range(n - 1):
        dists = np.min([np.linalg.norm(points - points[s], axis=1) for s in selected], axis=0)
        selected.append(np.argmax(dists))
    return selected

seeds = farthest_point_sample_2d(ground_xz, 6)

# Assign each ground vertex to nearest seed
from scipy.cluster.vq import kmeans2
centroids, labels = kmeans2(ground_xz, ground_xz[seeds], minit='matrix')

print("\n--- FOOT TIPS ---")
foot_tips = []
for i in range(6):
    cluster_mask = labels == i
    cluster_verts = ground_verts[cluster_mask]
    # The foot tip is the vertex farthest from the spider center in XZ
    center_xz = np.array([verts[:, 0].mean(), verts[:, 2].mean()])
    dists = np.linalg.norm(cluster_verts[:, [0, 2]] - center_xz, axis=1)
    tip_local_idx = np.argmax(dists)
    tip = cluster_verts[tip_local_idx]
    foot_tips.append(tip)

# Sort foot tips: front-to-back (by Z), then left-to-right (by X)
foot_tips = np.array(foot_tips)

# Determine front vs back: negative Z = front, positive Z = back
# Group into 3 pairs by Z value
z_order = np.argsort(foot_tips[:, 2])
front_pair = foot_tips[z_order[:2]]
mid_pair = foot_tips[z_order[2:4]]
rear_pair = foot_tips[z_order[4:]]

# Within each pair, sort by X (negative X = left, positive X = right)
# Khaled's indexing: front-left=0, front-right=1, mid-left=2, mid-right=3, back-left=4, back-right=5
def sort_pair_lr(pair):
    # More negative X = left
    if pair[0][0] < pair[1][0]:
        return pair[0], pair[1]  # left, right
    else:
        return pair[1], pair[0]

fl, fr = sort_pair_lr(front_pair)
ml, mr = sort_pair_lr(mid_pair)
rl, rr = sort_pair_lr(rear_pair)

ordered_feet = [fl, fr, ml, mr, rl, rr]
labels_feet = ["Front-Left (0)", "Front-Right (1)", "Mid-Left (2)", "Mid-Right (3)", "Rear-Left (4)", "Rear-Right (5)"]

for label, tip in zip(labels_feet, ordered_feet):
    print(f"  {label}: ({tip[0]:.4f}, {tip[1]:.4f}, {tip[2]:.4f})")

# === BODY CENTERS ===
# Use density to find the two body masses, split on Z axis
print("\n--- BODY CENTERS ---")

# High-density vertices = body
tree = KDTree(verts)
radius = 0.08
density = np.array([len(tree.query_ball_point(v, radius)) for v in verts])
body_mask = density > np.percentile(density, 75)
body_verts = verts[body_mask]

# Split body into front (cephalothorax) and back (abdomen) by Z
# First find the gap - the pedicel (narrow connection) should show as a density dip
z_values = body_verts[:, 2]
z_bins = np.linspace(z_values.min(), z_values.max(), 30)
z_hist, _ = np.histogram(z_values, bins=z_bins)

# Find the minimum in the histogram (the pedicel gap)
mid_region = z_hist[5:-5]  # avoid edges
gap_idx = np.argmin(mid_region) + 5
z_split = (z_bins[gap_idx] + z_bins[gap_idx + 1]) / 2

cephalo_verts = body_verts[body_verts[:, 2] < z_split]
abdomen_verts = body_verts[body_verts[:, 2] >= z_split]

if len(cephalo_verts) > 0:
    cephalo_center = cephalo_verts.mean(axis=0)
    # Get topmost point of cephalothorax for "top center" landmark
    cephalo_top_idx = np.argmax(cephalo_verts[:, 1])
    cephalo_top = cephalo_verts[cephalo_top_idx]
    print(f"  Cephalothorax center: ({cephalo_center[0]:.4f}, {cephalo_center[1]:.4f}, {cephalo_center[2]:.4f})")
    print(f"  Cephalothorax top:    ({cephalo_top[0]:.4f}, {cephalo_top[1]:.4f}, {cephalo_top[2]:.4f})")

if len(abdomen_verts) > 0:
    abdomen_center = abdomen_verts.mean(axis=0)
    abdomen_top_idx = np.argmax(abdomen_verts[:, 1])
    abdomen_top = abdomen_verts[abdomen_top_idx]
    print(f"  Abdomen center:       ({abdomen_center[0]:.4f}, {abdomen_center[1]:.4f}, {abdomen_center[2]:.4f})")
    print(f"  Abdomen top:          ({abdomen_top[0]:.4f}, {abdomen_top[1]:.4f}, {abdomen_top[2]:.4f})")

print(f"  Z split point (pedicel): {z_split:.4f}")

# === FRONT APPENDAGES (fangs/pedipalps) ===
print("\n--- FRONT APPENDAGES ---")

# Front appendages should be:
# - In front of the cephalothorax (most negative Z)
# - Not at ground level (they stick forward, not down)
# - Near center X
# - There should be a left and right pair

# Find vertices that are far forward (low Z) but not feet
front_mask = (verts[:, 2] < -0.4) & (verts[:, 1] > -0.15) & (np.abs(verts[:, 0]) < 0.5)
front_verts = verts[front_mask]
front_indices = np.where(front_mask)[0]

if len(front_verts) > 0:
    print(f"  Front appendage candidates: {len(front_verts)} vertices")

    # Split into left (negative X) and right (positive X)
    # Use X relative to center
    x_center = front_verts[:, 0].mean()

    left_front = front_verts[front_verts[:, 0] < x_center]
    right_front = front_verts[front_verts[:, 0] >= x_center]

    if len(left_front) > 0:
        # Tip = most negative Z
        left_tip_idx = np.argmin(left_front[:, 2])
        left_tip = left_front[left_tip_idx]
        print(f"  Left appendage tip:  ({left_tip[0]:.4f}, {left_tip[1]:.4f}, {left_tip[2]:.4f})")

    if len(right_front) > 0:
        right_tip_idx = np.argmin(right_front[:, 2])
        right_tip = right_front[right_tip_idx]
        print(f"  Right appendage tip: ({right_tip[0]:.4f}, {right_tip[1]:.4f}, {right_tip[2]:.4f})")
else:
    # Broaden search
    front_mask2 = (verts[:, 2] < -0.3) & (verts[:, 1] > -0.1) & (np.abs(verts[:, 0]) < 0.4)
    front_verts2 = verts[front_mask2]
    print(f"  Broadened search: {len(front_verts2)} vertices")
    if len(front_verts2) > 0:
        # Just get the most forward points
        forward_order = np.argsort(front_verts2[:, 2])
        for idx in forward_order[:10]:
            v = front_verts2[idx]
            print(f"    ({v[0]:.4f}, {v[1]:.4f}, {v[2]:.4f})")

# === COORDINATE SYSTEM NOTE ===
print("\n--- COORDINATE SYSTEM ---")
print(f"  glTF/GLB coords (Y-up)")
print(f"  Spider faces: -Z direction")
print(f"  Left side: -X")
print(f"  Right side: +X")
print(f"  Ground plane: Y ≈ -0.3")
print(f"  Body top: Y ≈ 0.17")

# === BUT KHALED IS IN BLENDER ===
# Blender uses Z-up. glTF export converts:
# Blender X -> glTF X
# Blender Y -> glTF -Z
# Blender Z -> glTF Y
print("\n--- BLENDER COORDINATE CONVERSION ---")
print("  Blender uses Z-up. glTF uses Y-up.")
print("  Conversion: Blender (X, Y, Z) -> glTF (X, Z, -Y)")
print("  Reverse:    glTF (X, Y, Z) -> Blender (X, -Z, Y)")

print("\n--- MY PREDICTIONS IN BLENDER COORDS ---")
print("  (Converting glTF -> Blender: X stays, Y = -glTF_Z, Z = glTF_Y)")

def gltf_to_blender(x, y, z):
    return (x, -z, y)

print("\n  FOOT TIPS:")
for label, tip in zip(labels_feet, ordered_feet):
    bx, by, bz = gltf_to_blender(tip[0], tip[1], tip[2])
    print(f"    {label}: Blender ({bx:.4f}, {by:.4f}, {bz:.4f})")

print("\n  BODY CENTERS (top surface):")
bx, by, bz = gltf_to_blender(cephalo_top[0], cephalo_top[1], cephalo_top[2])
print(f"    Cephalothorax top: Blender ({bx:.4f}, {by:.4f}, {bz:.4f})")
bx, by, bz = gltf_to_blender(abdomen_top[0], abdomen_top[1], abdomen_top[2])
print(f"    Abdomen top: Blender ({bx:.4f}, {by:.4f}, {bz:.4f})")
