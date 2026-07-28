import bpy, sys
from mathutils import Vector
exec(open('/home/khaled/Kore/tools/render_water_clips.py').read().split('N=8')[0])
FR=[0,6,12,18,24,34,48,70]
for i,fr in enumerate(FR):
    sc.frame_set(fr)
    tgt=Vector((ao.location.x, ao.location.y, 0.0))
    cam.location=tgt+Vector((0.85,-0.6,0.22)).normalized()*DIST
    cam.rotation_euler=(tgt-cam.location).to_track_quat('-Z','Y').to_euler()
    sc.render.filepath=r'C:\tmp\clip_%02d.png'%i
    bpy.ops.render.render(write_still=True)
print('RENDERED early %d'%len(FR))
