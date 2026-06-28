import trimesh
import numpy as np

mesh = trimesh.load('/home/khaled/Kore/spider.glb', force='mesh')
verts = mesh.vertices
center = verts.mean(axis=0)

print("="*60)
print("KORE'S LANDMARK PREDICTIONS")
print("="*60)

# Strategy: find foot tips by looking for the 6 vertices that are
# farthest from center in the XZ plane AND near ground level

# Ground level vertices
ground_mask = verts[:, 1] < -0.2  # Y < -0.2 in glTF = near ground
ground_verts = verts[ground_mask]
ground_indices = np.where(ground_mask)[0]

# Distance from center in XZ plane (horizontal spread)
center_xz = np.array([center[0], center[2]])
ground_xz_dist = np.linalg.norm(ground_verts[:, [0, 2]] - center_xz, axis=1)

# Farthest point sampling on ground vertices in XZ
def farthest_point_sample(points, dists_from_center, n):
    # Start with the farthest from center
    selected = [np.argmax(dists_from_center)]
    for _ in range(n - 1):
        min_dists = np.min([np.linalg.norm(points - points[s], axis=1) for s in selected], axis=0)
        selected.append(np.argmax(min_dists))
    return selected

seeds = farthest_point_sample(ground_verts[:, [0, 2]], ground_xz_dist, 6)
foot_tips_gltf = ground_verts[seeds]

# Sort into pairs by Z value
z_order = np.argsort(foot_tips_gltf[:, 2])
front_pair = foot_tips_gltf[z_order[:2]]
mid_pair = foot_tips_gltf[z_order[2:4]]
rear_pair = foot_tips_gltf[z_order[4:]]

def sort_lr(pair):
    if pair[0][0] < pair[1][0]:
        return pair[0], pair[1]
    return pair[1], pair[0]

fl, fr = sort_lr(front_pair)
ml, mr = sort_lr(mid_pair)
rl, rr = sort_lr(rear_pair)
ordered = [fl, fr, ml, mr, rl, rr]
names = ["Front-Left (0)", "Front-Right (1)", "Mid-Left (2)", "Mid-Right (3)", "Rear-Left (4)", "Rear-Right (5)"]

# Convert glTF to Blender: (X, Y, Z) -> (X, -Z, Y)
def to_blender(v):
    return (v[0], -v[2], v[1])

print("\nFOOT TIPS (Blender coords):")
for name, tip in zip(names, ordered):
    bx, by, bz = to_blender(tip)
    print(f"  {name}: X={bx:.4f}, Y={by:.4f}, Z={bz:.4f}")

# Body centers - find two dense masses
from scipy.spatial import KDTree
tree = KDTree(verts)
density = np.array([len(tree.query_ball_point(v, 0.08)) for v in verts])

# Body = high density, elevated (not ground), near center X
body_mask = (density > np.percentile(density, 70)) & (verts[:, 1] > -0.05) & (np.abs(verts[:, 0]) < 0.5)
body_verts = verts[body_mask]

# Split on Z to find cephalothorax (front, -Z) vs abdomen (back, +Z)
# Find the pedicel gap
z_vals = body_verts[:, 2]
z_bins = np.linspace(z_vals.min(), z_vals.max(), 40)
hist, _ = np.histogram(z_vals, bins=z_bins)

# Find minimum in middle region (pedicel)
search_start = len(hist) // 4
search_end = 3 * len(hist) // 4
gap_idx = search_start + np.argmin(hist[search_start:search_end])
z_split = (z_bins[gap_idx] + z_bins[gap_idx + 1]) / 2

cephalo = body_verts[body_verts[:, 2] < z_split]
abdomen = body_verts[body_verts[:, 2] >= z_split]

# For body center landmarks, Khaled would click the top-center
# So find the highest Y vertex near the centroid X/Z
def find_top_center(verts_subset):
    centroid_xz = verts_subset[:, [0, 2]].mean(axis=0)
    # Filter to near-center vertices
    near_center = np.linalg.norm(verts_subset[:, [0, 2]] - centroid_xz, axis=1) < 0.15
    if near_center.sum() == 0:
        near_center = np.ones(len(verts_subset), dtype=bool)
    candidates = verts_subset[near_center]
    top_idx = np.argmax(candidates[:, 1])
    return candidates[top_idx]

cephalo_top = find_top_center(cephalo)
abdomen_top = find_top_center(abdomen)

print(f"\nBODY CENTERS (Blender coords):")
bx, by, bz = to_blender(cephalo_top)
print(f"  Cephalothorax (top): X={bx:.4f}, Y={by:.4f}, Z={bz:.4f}")
bx, by, bz = to_blender(abdomen_top)
print(f"  Abdomen (top):       X={bx:.4f}, Y={by:.4f}, Z={bz:.4f}")

# Front appendages - fangs and pedipalps
# These are in front of the cephalothorax, not at ground level, near center X
print(f"\nFRONT APPENDAGES (Blender coords):")

# Get the most-negative-Z extent of the cephalothorax
cephalo_front_z = cephalo[:, 2].min()

# Find vertices beyond the cephalothorax front face
appendage_mask = (verts[:, 2] < cephalo_front_z + 0.05) & (np.abs(verts[:, 0]) < 0.4) & (verts[:, 1] > -0.2)
appendage_verts = verts[appendage_mask]

if len(appendage_verts) > 5:
    # Split left/right by X
    x_mid = appendage_verts[:, 0].mean()
    left_app = appendage_verts[appendage_verts[:, 0] < x_mid]
    right_app = appendage_verts[appendage_verts[:, 0] >= x_mid]

    # Tips are the most forward points (most negative Z)
    if len(left_app) > 0:
        left_tip = left_app[np.argmin(left_app[:, 2])]
        bx, by, bz = to_blender(left_tip)
        print(f"  Left fang/palp tip:  X={bx:.4f}, Y={by:.4f}, Z={bz:.4f}")
    if len(right_app) > 0:
        right_tip = right_app[np.argmin(right_app[:, 2])]
        bx, by, bz = to_blender(right_tip)
        print(f"  Right fang/palp tip: X={bx:.4f}, Y={by:.4f}, Z={bz:.4f}")

    # Are there two distinct pairs? (fangs vs pedipalps)
    # Check if there are two Z-depth layers
    z_vals_app = appendage_verts[:, 2]
    z_range = z_vals_app.max() - z_vals_app.min()
    print(f"\n  Appendage Z range: {z_range:.4f}")
    if z_range > 0.15:
        z_mid_app = (z_vals_app.min() + z_vals_app.max()) / 2
        outer_app = appendage_verts[z_vals_app < z_mid_app]  # more forward
        inner_app = appendage_verts[z_vals_app >= z_mid_app]  # closer to body

        if len(outer_app) > 2:
            left_outer = outer_app[outer_app[:, 0] < outer_app[:, 0].mean()]
            right_outer = outer_app[outer_app[:, 0] >= outer_app[:, 0].mean()]
            print(f"\n  Outer pair (fangs?):")
            if len(left_outer) > 0:
                tip = left_outer[np.argmin(left_outer[:, 2])]
                bx, by, bz = to_blender(tip)
                print(f"    Left:  X={bx:.4f}, Y={by:.4f}, Z={bz:.4f}")
            if len(right_outer) > 0:
                tip = right_outer[np.argmin(right_outer[:, 2])]
                bx, by, bz = to_blender(tip)
                print(f"    Right: X={bx:.4f}, Y={by:.4f}, Z={bz:.4f}")

        if len(inner_app) > 2:
            left_inner = inner_app[inner_app[:, 0] < inner_app[:, 0].mean()]
            right_inner = inner_app[inner_app[:, 0] >= inner_app[:, 0].mean()]
            print(f"\n  Inner pair (pedipalps?):")
            if len(left_inner) > 0:
                tip = left_inner[np.argmin(left_inner[:, 2])]
                bx, by, bz = to_blender(tip)
                print(f"    Left:  X={bx:.4f}, Y={by:.4f}, Z={bz:.4f}")
            if len(right_inner) > 0:
                tip = right_inner[np.argmin(right_inner[:, 2])]
                bx, by, bz = to_blender(tip)
                print(f"    Right: X={bx:.4f}, Y={by:.4f}, Z={bz:.4f}")

print("\n" + "="*60)
print("These are my blind predictions from mesh analysis alone.")
print("Now show me what you got, Khaled.")
print("="*60)
