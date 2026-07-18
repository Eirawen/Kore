# Finer crease probe: per t-bin extents in X (width) and Y (thickness),
# armature space, for root-weighted verts. Wrist crease = X-width minimum
# between forearm cylinder and palm slab.
import bpy, numpy as np

arm = bpy.data.objects['Armature.001']
mesh = bpy.data.objects['Sphere.001']
rel = np.array(arm.matrix_world.inverted() @ mesh.matrix_world)
root = arm.data.bones['Bone']
h = np.array(root.head_local); t = np.array(root.tail_local)
axis = t - h; L = np.linalg.norm(axis); axis /= L
ridx = mesh.vertex_groups['Bone'].index

pts = []
for v in mesh.data.vertices:
    w = 0.0
    for g in v.groups:
        if g.group == ridx:
            w = g.weight
    if w <= 0.5:
        continue
    co = (rel @ np.array([v.co[0], v.co[1], v.co[2], 1.0]))[:3]
    ta = np.dot(co - h, axis) / L
    pts.append((ta, co[0], co[1], co[2]))
pts = np.array(pts)
print('t-bin    n   x_min   x_max  width_x   y_min   y_max  thick_y')
for lo in np.arange(0.20, 1.02, 0.02):
    hi = lo + 0.02
    m = pts[(pts[:, 0] >= lo) & (pts[:, 0] < hi)]
    if len(m):
        print('%5.2f %5d %7.3f %7.3f %8.3f %7.3f %7.3f %8.3f' % (
            lo, len(m), m[:, 1].min(), m[:, 1].max(), m[:, 1].max() - m[:, 1].min(),
            m[:, 2].min(), m[:, 2].max(), m[:, 2].max() - m[:, 2].min()))
print('\nroot length L =', L, ' (t*L = distance along bone from head)')
