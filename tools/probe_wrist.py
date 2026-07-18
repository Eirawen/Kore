# Probe the hand blend before wrist surgery:
#  - object transforms (are mesh/armature spaces aligned?)
#  - bone hierarchy of BOTH armatures
#  - width profile of root-weighted verts along stub->knuckle axis, in ARMATURE
#    space (verts transformed by relative matrix), to locate the wrist crease.
import bpy, numpy as np

PAIRS = [('Armature.001', 'Sphere.001', 'RIGHT'),
         ('Armature.003', 'Sphere.002', 'LEFT')]

def show_xform(o):
    print('  %-14s parent=%s' % (o.name, o.parent.name if o.parent else '-'))
    print('    matrix_basis loc %s rot(euler deg) %s scale %s' % (
        tuple(round(v, 4) for v in o.matrix_basis.to_translation()),
        tuple(round(np.degrees(v), 2) for v in o.matrix_basis.to_euler()),
        tuple(round(v, 4) for v in o.matrix_basis.to_scale())))
    print('    matrix_world loc %s rot(euler deg) %s scale %s' % (
        tuple(round(v, 4) for v in o.matrix_world.to_translation()),
        tuple(round(np.degrees(v), 2) for v in o.matrix_world.to_euler()),
        tuple(round(v, 4) for v in o.matrix_world.to_scale())))

for ARM, MESH, TAG in PAIRS:
    arm = bpy.data.objects.get(ARM)
    mesh = bpy.data.objects.get(MESH)
    print('\n########## %s hand: %s / %s ##########' % (TAG, ARM, MESH))
    if not arm or not mesh:
        print('  MISSING'); continue
    show_xform(arm); show_xform(mesh)
    print('  mesh data users:', mesh.data.users, 'name:', mesh.data.name)
    print('  armature data users:', arm.data.users, 'name:', arm.data.name)
    mods = [(m.type, getattr(m, 'object', None) and m.object.name) for m in mesh.modifiers]
    print('  mesh modifiers:', mods)

    print('  ----- bones -----')
    for b in arm.data.bones:
        p = b.parent.name if b.parent else '-'
        print('  %-10s p=%-10s head %s tail %s' % (
            b.name, p,
            tuple(round(v, 4) for v in b.head_local),
            tuple(round(v, 4) for v in b.tail_local)))

    # verts -> armature space
    rel = arm.matrix_world.inverted() @ mesh.matrix_world
    roots = [b for b in arm.data.bones if not b.parent]
    root = roots[0]
    h = np.array(root.head_local); t = np.array(root.tail_local)
    axis = t - h; L = np.linalg.norm(axis); axis /= L
    vg = mesh.vertex_groups.get(root.name)
    if vg is None:
        print('  no root vertex group named', root.name)
        continue
    ridx = vg.index
    rows = []  # (t_along, radial_dist, weight)
    rel_np = np.array(rel)
    for v in mesh.data.vertices:
        w = 0.0
        for g in v.groups:
            if g.group == ridx:
                w = g.weight
        if w <= 0.01:
            continue
        co = rel_np @ np.array([v.co[0], v.co[1], v.co[2], 1.0])
        d = co[:3] - h
        ta = np.dot(d, axis) / L
        rad = np.linalg.norm(d - np.dot(d, axis) * axis)
        rows.append((ta, rad, w))
    rows = np.array(rows)
    print('  %d verts with root weight >0.01' % len(rows))
    print('  weight stats: min %.3f max %.3f  frac(w>0.9)=%.2f' % (
        rows[:, 2].min(), rows[:, 2].max(), (rows[:, 2] > 0.9).mean()))
    print('  width profile along stub(0)->knuckle(1), verts w>0.5:')
    sel = rows[rows[:, 2] > 0.5]
    print('   t-bin   n    rad_mean rad_max  (radii in armature units)')
    for lo in np.arange(-0.1, 1.15, 0.05):
        hi = lo + 0.05
        m = sel[(sel[:, 0] >= lo) & (sel[:, 0] < hi)]
        if len(m):
            print('   %5.2f %4d   %7.4f %7.4f' % (lo, len(m), m[:, 1].mean(), m[:, 1].max()))
    # where do OTHER groups (fingers) start to take weight from root?
    print('  root-weight falloff: mean root weight per t-bin (all w>0.01):')
    for lo in np.arange(0.5, 1.15, 0.05):
        hi = lo + 0.05
        m = rows[(rows[:, 0] >= lo) & (rows[:, 0] < hi)]
        if len(m):
            print('   %5.2f %4d   w_mean %.3f' % (lo, len(m), m[:, 2].mean()))
