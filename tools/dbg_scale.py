import bpy
from mathutils import Quaternion
bpy.ops.wm.open_mainfile(filepath=r'\\wsl.localhost\Ubuntu\home\khaled\Kore\water_rigged.blend')
ao=bpy.data.objects['WaterRig']
a=bpy.data.actions.new('dbg')
ao.animation_data_create(); ao.animation_data.action=a
print('mode before:', ao.mode)
for f,s in ((0,1.0),(10,0.3),(20,1.0)):
    ao.scale=(1.0,2.0,s)
    ao.location=(0,0,-0.5*(1-s))
    r1=ao.keyframe_insert('scale', frame=f)
    r2=ao.keyframe_insert('location', frame=f)
    print('f=%d scale_key=%s loc_key=%s  ao.scale=%s'%(f,r1,r2,tuple(round(v,2) for v in ao.scale)))
try: fcs=list(a.fcurves)
except Exception: fcs=[fc for l in a.layers for st in l.strips for cb in st.channelbags for fc in cb.fcurves]
print('fcurves:', [(fc.data_path,fc.array_index,len(fc.keyframe_points)) for fc in fcs])
