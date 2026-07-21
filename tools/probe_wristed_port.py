# Quick probe of cgtrader_hand_wristed.blend before porting casts/knife:
#   - object inventory (name, type, parent, hide_render)
#   - bone lists per armature (root chain + finger roots)
#   - pose-bone constraints (the 2-DOF wrist limits)
#   - mesh parenting matrices (unified spaces expected)
import bpy

print('=== OBJECTS ===')
for o in bpy.data.objects:
    print('%-16s %-8s parent=%-14s hide_render=%s' %
          (o.name, o.type, o.parent.name if o.parent else '-', o.hide_render))

for an in ('Armature.001', 'Armature.003'):
    arm = bpy.data.objects.get(an)
    if not arm:
        print('MISSING', an)
        continue
    print('=== %s bones ===' % an)
    for b in arm.data.bones:
        print('  %-10s parent=%-10s use_connect=%s' %
              (b.name, b.parent.name if b.parent else '-', b.use_connect))
    for pb in arm.pose.bones:
        for c in pb.constraints:
            print('  CONSTRAINT %s on %s (%s) influence=%.2f' %
                  (c.name, pb.name, c.type, c.influence))

for mn in ('Sphere.001', 'Sphere.002'):
    m = bpy.data.objects.get(mn)
    if m:
        print('=== %s ===' % mn)
        print('  parent:', m.parent.name if m.parent else '-')
        print('  matrix_basis identity:', m.matrix_basis ==
              m.matrix_basis.Identity(4))
        print('  vgroups:', sorted(vg.name for vg in m.vertex_groups)[:8], '...')
