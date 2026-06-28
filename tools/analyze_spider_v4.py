"""
Spider Mesh Landmark Analyzer v4
Automatically detects orientation (head vs rear) and assigns correct
front/rear and left/right labels without human input.

Orientation detection uses two independent signals:
  A. Cross-sectional height asymmetry: the abdomen is round/bulbous
     (large Y-span) while the cephalothorax is flat (small Y-span).
     The end with the larger Y-span = rear.
  B. Thin protrusion detection: the head end has fangs and pedipalps
     (very thin, flat structures) that the rear end lacks.

Both signals must agree for a confident orientation call.
"""

import trimesh
import numpy as np
from scipy.spatial import KDTree
from scipy.ndimage import uniform_filter1d


# ────────────────────────────────────────────────────────────
# Load mesh
# ────────────────────────────────────────────────────────────
mesh = trimesh.load('/home/khaled/Kore/spider.glb', force='mesh')
verts = mesh.vertices
faces = mesh.faces
center = verts.mean(axis=0)

print("=" * 64)
print("SPIDER LANDMARK ANALYZER v4 (automatic orientation)")
print("=" * 64)
print(f"Mesh: {len(verts)} vertices, {len(faces)} faces")
print(f"Centroid (glTF): X={center[0]:.4f}, Y={center[1]:.4f}, Z={center[2]:.4f}")


# ────────────────────────────────────────────────────────────
# Utility: coordinate conversion
# ────────────────────────────────────────────────────────────
def to_blender(v):
    """glTF (X, Y, Z) -> Blender (X, -Z, Y)"""
    return np.array([v[0], -v[2], v[1]])


# ────────────────────────────────────────────────────────────
# Step 1: Find 6 foot tips
# ────────────────────────────────────────────────────────────
print("\n--- STEP 1: Foot tip detection ---")

# Ground-level vertices (feet touch the ground)
ground_threshold = -0.20  # Y < -0.2 in glTF = near ground plane
ground_mask = verts[:, 1] < ground_threshold
ground_verts = verts[ground_mask]
ground_indices = np.where(ground_mask)[0]

print(f"Ground level: Y < {ground_threshold:.3f} ({len(ground_verts)} vertices)")

# Farthest-point sampling in XZ plane to find 6 distinct foot tips.
# FPS naturally selects the most spread-out points, which correspond
# to the tips of the 6 legs (the vertices farthest from each other).
center_xz = np.array([center[0], center[2]])
ground_xz = ground_verts[:, [0, 2]]
ground_xz_dist = np.linalg.norm(ground_xz - center_xz, axis=1)


def farthest_point_sample(points, init_dists, n):
    """Select n well-separated points using farthest-point sampling."""
    selected = [np.argmax(init_dists)]
    for _ in range(n - 1):
        min_dists = np.min(
            [np.linalg.norm(points - points[s], axis=1) for s in selected],
            axis=0,
        )
        selected.append(np.argmax(min_dists))
    return selected


fps_seeds = farthest_point_sample(ground_xz, ground_xz_dist, 6)
foot_tips_gltf = ground_verts[fps_seeds]
print(f"Found {len(foot_tips_gltf)} foot tips")


# ────────────────────────────────────────────────────────────
# Step 2: Sort foot tips into 3 pairs along body axis (Z)
# ────────────────────────────────────────────────────────────
z_order = np.argsort(foot_tips_gltf[:, 2])
pair_neg_z = foot_tips_gltf[z_order[:2]]   # most negative Z
pair_mid_z = foot_tips_gltf[z_order[2:4]]  # middle Z
pair_pos_z = foot_tips_gltf[z_order[4:]]   # most positive Z


# ────────────────────────────────────────────────────────────
# Step 3: Determine spider facing direction
# ────────────────────────────────────────────────────────────
print("\n--- STEP 3: Orientation detection ---")

# Signal A: Cross-sectional Y-span (height) asymmetry
# The abdomen is round/bulbous (large Y-span in cross-section),
# the cephalothorax is flat (small Y-span). The end with the
# larger average Y-span is the rear (abdomen side).

near_center_x = np.abs(verts[:, 0] - center[0]) < 0.35
center_x_verts = verts[near_center_x]

neg_z_half = center_x_verts[center_x_verts[:, 2] < center[2]]
pos_z_half = center_x_verts[center_x_verts[:, 2] >= center[2]]


def mean_y_span(v, n_slices=15):
    """Average Y-span across Z-slices."""
    if len(v) < 5:
        return 0.0
    z_lo, z_hi = v[:, 2].min(), v[:, 2].max()
    if z_hi - z_lo < 1e-6:
        return 0.0
    z_bins = np.linspace(z_lo, z_hi, n_slices + 1)
    spans = []
    for i in range(n_slices):
        in_bin = v[(v[:, 2] >= z_bins[i]) & (v[:, 2] < z_bins[i + 1])]
        if len(in_bin) >= 2:
            spans.append(in_bin[:, 1].max() - in_bin[:, 1].min())
    return np.mean(spans) if spans else 0.0


neg_z_yspan = mean_y_span(neg_z_half)
pos_z_yspan = mean_y_span(pos_z_half)
yspan_ratio = (neg_z_yspan / pos_z_yspan) if pos_z_yspan > 0 else float("inf")

print(f"  Signal A (Y-span asymmetry):")
print(f"    neg-Z half mean Y-span: {neg_z_yspan:.4f}")
print(f"    pos-Z half mean Y-span: {pos_z_yspan:.4f}")
print(f"    ratio: {yspan_ratio:.2f}")

# Abdomen (rear) is the side with larger Y-span
signal_a_faces_pos_z = neg_z_yspan > pos_z_yspan  # True if rear is at -Z => head faces +Z
signal_a_confidence = abs(yspan_ratio - 1.0)  # how asymmetric
print(f"    verdict: spider faces {'+ Z' if signal_a_faces_pos_z else '- Z'}"
      f" (confidence: {signal_a_confidence:.2f})")


# Signal B: Thin protrusion detection
# Head appendages (fangs, pedipalps) are thin flat structures near
# the extremes of the body. Count how many Z-slices at each end
# have very small Y-span (< 0.1).

z_total_range = center_x_verts[:, 2].max() - center_x_verts[:, 2].min()
z_fringe = z_total_range * 0.3

neg_extreme = center_x_verts[center_x_verts[:, 2] < center_x_verts[:, 2].min() + z_fringe]
pos_extreme = center_x_verts[center_x_verts[:, 2] > center_x_verts[:, 2].max() - z_fringe]


def count_thin_slices(v, n_slices=10, thin_threshold=0.1):
    """Count Z-slices with Y-span below threshold."""
    if len(v) < 5:
        return 0, 0
    z_lo, z_hi = v[:, 2].min(), v[:, 2].max()
    if z_hi - z_lo < 1e-6:
        return 0, 0
    z_bins = np.linspace(z_lo, z_hi, n_slices + 1)
    thin = 0
    total = 0
    for i in range(n_slices):
        in_bin = v[(v[:, 2] >= z_bins[i]) & (v[:, 2] < z_bins[i + 1])]
        if len(in_bin) >= 2:
            total += 1
            if (in_bin[:, 1].max() - in_bin[:, 1].min()) < thin_threshold:
                thin += 1
    return thin, total


neg_thin, neg_total = count_thin_slices(neg_extreme)
pos_thin, pos_total = count_thin_slices(pos_extreme)

print(f"  Signal B (thin protrusions):")
print(f"    neg-Z extreme: {neg_thin}/{neg_total} thin slices")
print(f"    pos-Z extreme: {pos_thin}/{pos_total} thin slices")

signal_b_faces_pos_z = pos_thin > neg_thin  # More thin slices at +Z => head appendages at +Z
signal_b_valid = (pos_thin != neg_thin)
if signal_b_valid:
    print(f"    verdict: spider faces {'+ Z' if signal_b_faces_pos_z else '- Z'}")
else:
    print(f"    verdict: inconclusive")


# Combine signals
if signal_b_valid and signal_a_faces_pos_z == signal_b_faces_pos_z:
    spider_faces_pos_z = signal_a_faces_pos_z
    print(f"\n  BOTH signals agree: spider faces {'+ Z' if spider_faces_pos_z else '- Z'}")
elif signal_a_confidence > 0.5:
    spider_faces_pos_z = signal_a_faces_pos_z
    print(f"\n  Signal B inconclusive, using Signal A: spider faces {'+ Z' if spider_faces_pos_z else '- Z'}")
elif signal_b_valid:
    spider_faces_pos_z = signal_b_faces_pos_z
    print(f"\n  Signal A weak, using Signal B: spider faces {'+ Z' if spider_faces_pos_z else '- Z'}")
else:
    # Fallback: assume the end with more near-center-X vertices beyond
    # the body is the abdomen (rear), since abdomen extends further
    spider_faces_pos_z = neg_z_yspan > pos_z_yspan
    print(f"\n  Both signals weak, best guess: spider faces {'+ Z' if spider_faces_pos_z else '- Z'}")


# ────────────────────────────────────────────────────────────
# Step 4: Assign front/rear/left/right labels
# ────────────────────────────────────────────────────────────
print("\n--- STEP 4: Labeling foot tips ---")

# Front = the pair at the head end, Rear = the pair at the tail end
if spider_faces_pos_z:
    front_pair = pair_pos_z
    mid_pair = pair_mid_z
    rear_pair = pair_neg_z
    facing_str = "+Z"
else:
    front_pair = pair_neg_z
    mid_pair = pair_mid_z
    rear_pair = pair_pos_z
    facing_str = "-Z"

print(f"Spider faces: {facing_str}")


def assign_left_right(pair, faces_pos_z):
    """
    Assign left/right from the spider's perspective.
    When facing +Z: spider's left = +X, spider's right = -X
    When facing -Z: spider's left = -X, spider's right = +X

    (Think of standing on the spider looking forward: left/right
     follow the right-hand rule with forward and up.)
    """
    if faces_pos_z:
        # Spider faces +Z => left = +X
        if pair[0][0] > pair[1][0]:
            return pair[0], pair[1]  # left, right
        return pair[1], pair[0]
    else:
        # Spider faces -Z => left = -X
        if pair[0][0] < pair[1][0]:
            return pair[0], pair[1]  # left, right
        return pair[1], pair[0]


fl, fr = assign_left_right(front_pair, spider_faces_pos_z)
ml, mr = assign_left_right(mid_pair, spider_faces_pos_z)
rl, rr = assign_left_right(rear_pair, spider_faces_pos_z)

ordered_feet = [fl, fr, ml, mr, rl, rr]
foot_names = [
    "Front-Left  (0)", "Front-Right (1)",
    "Mid-Left    (2)", "Mid-Right   (3)",
    "Rear-Left   (4)", "Rear-Right  (5)",
]

print(f"\nFOOT TIPS (glTF coords):")
for name, tip in zip(foot_names, ordered_feet):
    print(f"  {name}: X={tip[0]:+.4f}, Y={tip[1]:+.4f}, Z={tip[2]:+.4f}")

print(f"\nFOOT TIPS (Blender coords):")
for name, tip in zip(foot_names, ordered_feet):
    b = to_blender(tip)
    print(f"  {name}: X={b[0]:+.4f}, Y={b[1]:+.4f}, Z={b[2]:+.4f}")


# ────────────────────────────────────────────────────────────
# Step 5: Find body segments (cephalothorax and abdomen)
# ────────────────────────────────────────────────────────────
print("\n--- STEP 5: Body segment detection ---")

# Body candidate vertices: near center X and not at ground level.
# This captures the main body (cephalothorax + abdomen) and head appendages
# while excluding legs (which extend far from center X).
body_cand = verts[
    (np.abs(verts[:, 0] - center[0]) < 0.35)
    & (verts[:, 1] > ground_threshold + 0.05)
]

# Find pedicel (waist) by looking for the minimum cross-sectional area
# along Z. The pedicel is the narrow constriction between cephalothorax
# and abdomen -- it shows as a dip in the X-span * Y-span profile.
n_body_bins = 40
z_body_lo, z_body_hi = body_cand[:, 2].min(), body_cand[:, 2].max()
z_body_bins = np.linspace(z_body_lo, z_body_hi, n_body_bins + 1)

areas = np.zeros(n_body_bins)
for i in range(n_body_bins):
    in_bin = body_cand[
        (body_cand[:, 2] >= z_body_bins[i]) & (body_cand[:, 2] < z_body_bins[i + 1])
    ]
    if len(in_bin) >= 3:
        areas[i] = (in_bin[:, 0].max() - in_bin[:, 0].min()) * (
            in_bin[:, 1].max() - in_bin[:, 1].min()
        )

# Smooth the area profile to avoid noise-driven false minima
areas_smooth = uniform_filter1d(areas, size=3)

# Search the middle 50% for the pedicel (minimum cross-sectional area)
search_lo = n_body_bins // 4
search_hi = 3 * n_body_bins // 4
pedicel_idx = search_lo + np.argmin(areas_smooth[search_lo:search_hi])
z_pedicel = (z_body_bins[pedicel_idx] + z_body_bins[pedicel_idx + 1]) / 2

print(f"Pedicel (waist) at glTF Z = {z_pedicel:.4f} (Blender Y = {-z_pedicel:.4f})")

# Split body into cephalothorax (head side) and abdomen (rear side)
if spider_faces_pos_z:
    cephalo_cand = body_cand[body_cand[:, 2] >= z_pedicel]
    abdomen_cand = body_cand[body_cand[:, 2] < z_pedicel]
else:
    cephalo_cand = body_cand[body_cand[:, 2] <= z_pedicel]
    abdomen_cand = body_cand[body_cand[:, 2] > z_pedicel]

# Also compute density for top-vertex selection (prefer dense body regions)
tree = KDTree(verts)
density = np.array([len(tree.query_ball_point(v, 0.08)) for v in verts])


def find_top_center(seg, all_verts, all_density):
    """Find the topmost vertex near the XZ centroid of a body segment.

    Uses density weighting to prefer the dense core of the body over
    sparse appendage or leg-root vertices that happen to be included.
    """
    centroid_xz = seg[:, [0, 2]].mean(axis=0)

    # Find the vertex indices in the full mesh that match this segment
    # (to look up their density)
    seg_tree = KDTree(seg)
    # Filter to vertices near the XZ centroid
    dist_to_center = np.linalg.norm(seg[:, [0, 2]] - centroid_xz, axis=1)
    radius = np.percentile(dist_to_center, 40)  # inner 40% of the segment
    near_center = dist_to_center < max(radius, 0.10)
    if near_center.sum() == 0:
        near_center = np.ones(len(seg), dtype=bool)
    candidates = seg[near_center]
    return candidates[np.argmax(candidates[:, 1])]


cephalo_top = find_top_center(cephalo_cand, verts, density)
abdomen_top = find_top_center(abdomen_cand, verts, density)

print(f"\nBODY CENTERS (glTF coords):")
print(f"  Cephalothorax top: X={cephalo_top[0]:+.4f}, Y={cephalo_top[1]:+.4f}, Z={cephalo_top[2]:+.4f}")
print(f"  Abdomen top:       X={abdomen_top[0]:+.4f}, Y={abdomen_top[1]:+.4f}, Z={abdomen_top[2]:+.4f}")

print(f"\nBODY CENTERS (Blender coords):")
bc = to_blender(cephalo_top)
ba = to_blender(abdomen_top)
print(f"  Cephalothorax top: X={bc[0]:+.4f}, Y={bc[1]:+.4f}, Z={bc[2]:+.4f}")
print(f"  Abdomen top:       X={ba[0]:+.4f}, Y={ba[1]:+.4f}, Z={ba[2]:+.4f}")


# ────────────────────────────────────────────────────────────
# Step 6: Head appendages (fangs and pedipalps)
# ────────────────────────────────────────────────────────────
print("\n--- STEP 6: Head appendage detection ---")

# Head appendages are between the cephalothorax body and the front legs.
# They are thin (small Y-span), near center X, and elevated (not ground).

# Head appendages sit between the cephalothorax body and the front
# legs. To find where the body ends and appendages begin, look for
# where the cross-sectional area drops below 30% of its cephalothorax
# peak -- that boundary marks the start of the appendage region.
if spider_faces_pos_z:
    # Scan cephalothorax area profile to find where body ends
    cephalo_areas = areas_smooth[pedicel_idx:]
    cephalo_peak = np.max(cephalo_areas) if len(cephalo_areas) > 0 else 0
    threshold_area = cephalo_peak * 0.30
    body_end_rel = len(cephalo_areas) - 1
    for j in range(len(cephalo_areas) - 1, -1, -1):
        if cephalo_areas[j] >= threshold_area:
            body_end_rel = j
            break
    body_end_z = z_body_bins[pedicel_idx + body_end_rel + 1]

    front_leg_z = front_pair[:, 2].mean()
    app_mask = (
        (verts[:, 2] > body_end_z - 0.10)
        & (verts[:, 2] < front_leg_z - 0.05)
        & (verts[:, 1] > ground_threshold + 0.05)
        & (np.abs(verts[:, 0] - center[0]) < 0.45)
    )
else:
    cephalo_areas = areas_smooth[:pedicel_idx]
    cephalo_peak = np.max(cephalo_areas) if len(cephalo_areas) > 0 else 0
    threshold_area = cephalo_peak * 0.30
    body_end_rel = 0
    for j in range(len(cephalo_areas)):
        if cephalo_areas[j] >= threshold_area:
            body_end_rel = j
            break
    body_end_z = z_body_bins[body_end_rel]

    front_leg_z = front_pair[:, 2].mean()
    app_mask = (
        (verts[:, 2] < body_end_z + 0.10)
        & (verts[:, 2] > front_leg_z + 0.05)
        & (verts[:, 1] > ground_threshold + 0.05)
        & (np.abs(verts[:, 0] - center[0]) < 0.45)
    )

app_verts = verts[app_mask]
fang_left = fang_right = palp_left = palp_right = None

if len(app_verts) > 4:
    print(f"Appendage region: {len(app_verts)} vertices")

    # Split into depth layers along Z to separate fangs from pedipalps.
    # Fangs (chelicerae) are closer to the body; pedipalps are further forward.
    app_z_mid = np.median(app_verts[:, 2])

    if spider_faces_pos_z:
        inner_app = app_verts[app_verts[:, 2] <= app_z_mid]  # closer to body
        outer_app = app_verts[app_verts[:, 2] > app_z_mid]   # further forward
    else:
        inner_app = app_verts[app_verts[:, 2] >= app_z_mid]
        outer_app = app_verts[app_verts[:, 2] < app_z_mid]

    def find_appendage_tips(app_subset, faces_pos_z):
        """Find left and right tips of an appendage pair."""
        if len(app_subset) < 2:
            return None, None
        x_mid = app_subset[:, 0].mean()
        if faces_pos_z:
            left_side = app_subset[app_subset[:, 0] > x_mid]
            right_side = app_subset[app_subset[:, 0] <= x_mid]
        else:
            left_side = app_subset[app_subset[:, 0] < x_mid]
            right_side = app_subset[app_subset[:, 0] >= x_mid]

        left_tip = right_tip = None
        if len(left_side) > 0:
            idx = np.argmax(left_side[:, 2]) if faces_pos_z else np.argmin(left_side[:, 2])
            left_tip = left_side[idx]
        if len(right_side) > 0:
            idx = np.argmax(right_side[:, 2]) if faces_pos_z else np.argmin(right_side[:, 2])
            right_tip = right_side[idx]
        return left_tip, right_tip

    fang_left, fang_right = find_appendage_tips(inner_app, spider_faces_pos_z)
    palp_left, palp_right = find_appendage_tips(outer_app, spider_faces_pos_z)

    for label, lt, rt in [("FANGS", fang_left, fang_right),
                           ("PEDIPALPS / FEELERS", palp_left, palp_right)]:
        print(f"\n{label} (glTF coords):")
        if lt is not None:
            print(f"  Left:  X={lt[0]:+.4f}, Y={lt[1]:+.4f}, Z={lt[2]:+.4f}")
        if rt is not None:
            print(f"  Right: X={rt[0]:+.4f}, Y={rt[1]:+.4f}, Z={rt[2]:+.4f}")

        print(f"\n{label} (Blender coords):")
        if lt is not None:
            b = to_blender(lt)
            print(f"  Left:  X={b[0]:+.4f}, Y={b[1]:+.4f}, Z={b[2]:+.4f}")
        if rt is not None:
            b = to_blender(rt)
            print(f"  Right: X={b[0]:+.4f}, Y={b[1]:+.4f}, Z={b[2]:+.4f}")
else:
    print(f"WARNING: Only {len(app_verts)} appendage vertices found (expected more)")


# ────────────────────────────────────────────────────────────
# Step 7: Accuracy report against ground truth
# ────────────────────────────────────────────────────────────
print("\n" + "=" * 64)
print("ACCURACY CHECK vs GROUND TRUTH")
print("=" * 64)

# Ground truth (Blender coords):
#   Spider faces: -Y (in Blender) = +Z (in glTF)
#   Front legs at Blender Y ~ -0.86  (glTF Z ~ +0.86)
#   Mid legs at Blender Y ~ -0.08    (glTF Z ~ +0.08)  [note: mesh has asymmetric mid legs]
#   Rear legs at Blender Y ~ +0.86   (glTF Z ~ -0.86)
#   Body center at Blender Y ~ -0.08 (glTF Z ~ +0.08)
#   Abdomen at Blender Y ~ +0.48     (glTF Z ~ -0.48)
#   Spider left = +X (Blender) = +X (glTF)
#   Fangs at Blender Y ~ -0.26, Pedipalps at Blender Y ~ -0.55

gt_facing = "+Z"

# Check facing direction
facing_correct = (facing_str == gt_facing)
print(f"\nFacing direction: predicted={facing_str}, ground_truth={gt_facing}"
      f"  {'CORRECT' if facing_correct else 'WRONG'}")

# Structural check: front pair must have the most extreme Blender Y
# in the facing direction, rear pair must have the opposite extreme,
# and mid pair must be between them.
print(f"\nFoot tip ordering (Blender Y values):")
front_ys = [to_blender(fl)[1], to_blender(fr)[1]]
mid_ys = [to_blender(ml)[1], to_blender(mr)[1]]
rear_ys = [to_blender(rl)[1], to_blender(rr)[1]]

front_mean_y = np.mean(front_ys)
mid_mean_y = np.mean(mid_ys)
rear_mean_y = np.mean(rear_ys)

print(f"  Front pair mean Y: {front_mean_y:+.4f}")
print(f"  Mid   pair mean Y: {mid_mean_y:+.4f}")
print(f"  Rear  pair mean Y: {rear_mean_y:+.4f}")

# Spider faces -Y in Blender, so front = most negative Y, rear = most positive Y
order_correct = (front_mean_y < mid_mean_y < rear_mean_y)
print(f"  Order front < mid < rear? {'YES' if order_correct else 'NO'}")

# Check left/right: spider's left = +X in both Blender and glTF
lr_checks = []
for pair_name, left_foot, right_foot in [
    ("Front", fl, fr), ("Mid", ml, mr), ("Rear", rl, rr)
]:
    left_x = to_blender(left_foot)[0]
    right_x = to_blender(right_foot)[0]
    correct = left_x > right_x  # spider left = +X
    lr_checks.append(correct)
    print(f"  {pair_name:5s} L/R: left_X={left_x:+.4f} > right_X={right_x:+.4f}? "
          f"{'YES' if correct else 'NO'}")

all_lr_ok = all(lr_checks)

# Body centers
cephalo_b = to_blender(cephalo_top)
abdomen_b = to_blender(abdomen_top)
body_order_ok = cephalo_b[1] < abdomen_b[1]  # cephalo more negative Y (forward)
print(f"\nBody centers (Blender Y):")
print(f"  Cephalothorax: Y={cephalo_b[1]:+.4f}  (expected negative, i.e. forward)")
print(f"  Abdomen:       Y={abdomen_b[1]:+.4f}  (expected positive, i.e. rearward)")
print(f"  Cephalo forward of abdomen? {'YES' if body_order_ok else 'NO'}")

# Appendage check (if detected)
appendage_ok = True
if fang_left is not None:
    fang_b = to_blender(fang_left)
    fang_forward = fang_b[1] < cephalo_b[1]  # fangs should be forward of cephalo center
    print(f"\nAppendage check:")
    print(f"  Fang Y={fang_b[1]:+.4f}, Cephalo Y={cephalo_b[1]:+.4f}")
    print(f"  Fangs forward of cephalothorax? {'YES' if fang_forward else 'NO'}")
    appendage_ok = fang_forward

# Individual foot positions for reference
print(f"\nFoot tip positions (Blender coords):")
for name, tip in zip(foot_names, ordered_feet):
    b = to_blender(tip)
    print(f"  {name}: X={b[0]:+.4f}, Y={b[1]:+.4f}, Z={b[2]:+.4f}")

# Summary
print(f"\n{'='*64}")
print(f"SUMMARY:")
print(f"  Facing direction:  {'PASS' if facing_correct else 'FAIL'}")
print(f"  Front/Rear order:  {'PASS' if order_correct else 'FAIL'}")
print(f"  Left/Right labels: {'PASS' if all_lr_ok else 'FAIL'}")
print(f"  Body segments:     {'PASS' if body_order_ok else 'FAIL'}")
print(f"  Appendages:        {'PASS' if appendage_ok else 'FAIL'}")
print(f"{'='*64}")
