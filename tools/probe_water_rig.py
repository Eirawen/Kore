import bpy
bpy.ops.wm.open_mainfile(filepath=r'\\wsl.localhost\Ubuntu\home\khaled\Kore\water_rigged.blend')
ao=bpy.data.objects['WaterRig']
print('BONES: %d'%len(ao.data.bones))
for b in ao.data.bones:
    p=b.parent.name if b.parent else '-'
    L=(b.tail_local-b.head_local).length
    print('  %-8s parent=%-8s head=(%+.3f,%+.3f,%+.3f) len=%.3f'
          %(b.name,p,b.head_local.x,b.head_local.y,b.head_local.z,L))
