# Read-only introspection of the hand rig — can we add a wrist bone?
# Dumps: bone hierarchy (head/tail/parent) + vertex-group weight distribution
# for the RIGHT hand, and locates where a wrist split would fall.
import bpy, numpy as np

ARM, MESH = 'Armature.001', 'Sphere.001'
arm = bpy.data.objects[ARM]
mesh = bpy.data.objects[MESH]

print('\n===== BONES (%s) =====' % ARM)
print('%-12s %-8s %-30s %-30s' % ('bone', 'parent', 'head(x,y,z)', 'tail(x,y,z)'))
for b in arm.data.bones:
    p = b.parent.name if b.parent else '-'
    h = tuple(round(v, 3) for v in b.head_local)
    t = tuple(round(v, 3) for v in b.tail_local)
    print('%-12s %-8s %-30s %-30s' % (b.name, p, h, t))

# Which bones are the root / which are children (finger roots)
roots = [b.name for b in arm.data.bones if not b.parent]
print('\nROOT bone(s):', roots)
print('children of root:', [b.name for b in arm.data.bones if b.parent and b.parent.name in roots])

# ---- vertex group weight distribution ----
print('\n===== VERTEX GROUPS (%s), %d verts total =====' % (MESH, len(mesh.data.vertices)))
vg_names = {vg.index: vg.name for vg in mesh.vertex_groups}
counts = {n: 0 for n in vg_names.values()}
for v in mesh.data.vertices:
    for g in v.groups:
        if g.weight > 0.1:
            counts[vg_names[g.group]] += 1
for n, c in sorted(counts.items(), key=lambda kv: -kv[1]):
    print('  %-12s %5d verts (w>0.1)' % (n, c))

# ---- geometry of the root-weighted verts (forearm+palm): where's the wrist? ----
# Use the root bone's axis (head->tail) as the "along-hand" coordinate.
root = arm.data.bones[roots[0]]
axis = np.array(root.tail_local) - np.array(root.head_local)
L = np.linalg.norm(axis); axis = axis / L
root_idx = mesh.vertex_groups[roots[0]].index if roots[0] in mesh.vertex_groups else None
print('\n===== ROOT bone "%s": head->tail length %.3f (this spans forearm..knuckles) =====' % (roots[0], L))
if root_idx is not None:
    ts = []
    for v in mesh.data.vertices:
        for g in v.groups:
            if g.group == root_idx and g.weight > 0.3:
                d = np.dot(np.array(v.co) - np.array(root.head_local), axis)
                ts.append(d / L)  # 0 at head(stub), 1 at tail(knuckles)
    if ts:
        ts = np.array(ts)
        print('  %d verts strongly on root. Their position along stub(0)->knuckle(1):' % len(ts))
        print('   min %.2f  25%% %.2f  median %.2f  75%% %.2f  max %.2f'
              % (ts.min(), np.percentile(ts, 25), np.median(ts),
                 np.percentile(ts, 75), ts.max()))
        print('  => a WRIST split near t~0.45-0.6 would separate forearm(<t) from hand(>t).')
else:
    print('  (no vertex group named for the root bone — forearm may ride a different group)')
print('\n===== finger-root bone heads (the knuckle line ~ where the hand begins) =====')
for b in arm.data.bones:
    if b.parent and b.parent.name in roots:
        d = np.dot(np.array(b.head_local) - np.array(root.head_local), axis) / L
        print('  %-12s head at t=%.2f along stub->knuckle' % (b.name, d))
