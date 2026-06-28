import trimesh
import numpy as np

mesh = trimesh.load('/home/khaled/Kore/spider.glb', force='mesh')

verts = mesh.vertices
print(f"Vertices: {len(verts)}")
print(f"Faces: {len(mesh.faces)}")

print(f"\nBounding box:")
print(f"  X: {verts[:,0].min():.4f} to {verts[:,0].max():.4f}")
print(f"  Y: {verts[:,1].min():.4f} to {verts[:,1].max():.4f}")
print(f"  Z: {verts[:,2].min():.4f} to {verts[:,2].max():.4f}")
print(f"  Center: {verts.mean(axis=0)}")

# Find extremities - vertices farthest from center of mass
center = verts.mean(axis=0)
distances = np.linalg.norm(verts - center, axis=1)

# Get the most extreme vertices
n_extreme = 50
extreme_indices = np.argsort(distances)[-n_extreme:]
print(f"\nTop {n_extreme} most extreme vertices (farthest from center):")
for i in extreme_indices[-20:]:
    v = verts[i]
    d = distances[i]
    print(f"  [{i}] ({v[0]:.4f}, {v[1]:.4f}, {v[2]:.4f}) dist={d:.4f}")

# Try to identify clusters of extremities (leg tips should cluster)
from collections import defaultdict

extreme_verts = verts[extreme_indices]

# Simple clustering: group extreme vertices that are close to each other
def cluster_points(points, threshold=0.05):
    clusters = []
    used = set()
    for i, p in enumerate(points):
        if i in used:
            continue
        cluster = [i]
        used.add(i)
        for j, q in enumerate(points):
            if j in used:
                continue
            if np.linalg.norm(p - q) < threshold:
                cluster.append(j)
                used.add(j)
        clusters.append(cluster)
    return clusters

clusters = cluster_points(extreme_verts, threshold=0.08)
print(f"\nExtremity clusters (threshold=0.08):")
for ci, cluster in enumerate(clusters):
    pts = extreme_verts[cluster]
    centroid = pts.mean(axis=0)
    print(f"  Cluster {ci}: {len(cluster)} points, centroid=({centroid[0]:.4f}, {centroid[1]:.4f}, {centroid[2]:.4f})")

# Now let's try to identify body segments by analyzing vertex density
# The body (cephalothorax + abdomen) should be dense clusters near the center
# Legs should be thin elongated structures radiating outward

# Find the densest region (body center)
from scipy.spatial import KDTree
tree = KDTree(verts)
# For each vertex, count neighbors within a radius
radius = 0.1
density = np.array([len(tree.query_ball_point(v, radius)) for v in verts])

densest_indices = np.argsort(density)[-20:]
print(f"\nDensest regions (likely body center):")
for i in densest_indices[-10:]:
    v = verts[i]
    print(f"  [{i}] ({v[0]:.4f}, {v[1]:.4f}, {v[2]:.4f}) neighbors={density[i]}")

# Try to find two body masses (cephalothorax and abdomen)
# They should be the two densest clusters along the Y axis (front-back)
dense_verts = verts[density > np.percentile(density, 80)]
print(f"\nDense vertex cloud (top 20% density): {len(dense_verts)} vertices")
print(f"  Y range: {dense_verts[:,1].min():.4f} to {dense_verts[:,1].max():.4f}")
print(f"  Y midpoint: {dense_verts[:,1].mean():.4f}")

# Split dense vertices into front and back by Y
y_mid = dense_verts[:,1].mean()
front_dense = dense_verts[dense_verts[:,1] > y_mid]
back_dense = dense_verts[dense_verts[:,1] <= y_mid]
if len(front_dense) > 0:
    print(f"\n  Front body mass center (cephalothorax?): ({front_dense.mean(axis=0)[0]:.4f}, {front_dense.mean(axis=0)[1]:.4f}, {front_dense.mean(axis=0)[2]:.4f})")
if len(back_dense) > 0:
    print(f"  Back body mass center (abdomen?): ({back_dense.mean(axis=0)[0]:.4f}, {back_dense.mean(axis=0)[1]:.4f}, {back_dense.mean(axis=0)[2]:.4f})")

# For leg tips: find the 6 most extreme points that are far from each other
# Use a greedy farthest-point sampling
def farthest_point_sample(points, n):
    selected = [np.argmax(np.linalg.norm(points - points.mean(axis=0), axis=1))]
    for _ in range(n - 1):
        dists = np.min([np.linalg.norm(points - points[s], axis=1) for s in selected], axis=0)
        selected.append(np.argmax(dists))
    return selected

# Get 10 most spread out extreme points (should capture 6 feet + 2 fangs + 2 feelers)
spread_indices = farthest_point_sample(verts, 12)
print(f"\n12 most spread out vertices (farthest point sampling):")
for idx, i in enumerate(spread_indices):
    v = verts[i]
    d = np.linalg.norm(v - center)
    print(f"  Point {idx}: [{i}] ({v[0]:.4f}, {v[1]:.4f}, {v[2]:.4f}) dist_from_center={d:.4f}")
