import bpy, sys
import math
from mathutils import Vector
exec(open('/home/khaled/Kore/tools/render_water_clips.py').read().split('N=8')[0])
# MARKER at her destination so front/back is unambiguous in the render
bpy.ops.mesh.primitive_cone_add(radius1=0.12, depth=0.5, location=(0,-2.9,0))
mk=bpy.context.active_object; mk.rotation_euler=(math.radians(-90),0,0) if False else (0,0,0)
mm=bpy.data.materials.new('mk'); mm.use_nodes=True
mm.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(1,0.35,0.1,1)
mk.data.materials.append(mm)
FR=[0,12,24,40,56,70,82,95]
for i,fr in enumerate(FR):
    sc.frame_set(fr)
    tgt=Vector((0,-1.3,0))          # STATIC camera framing the whole run
    cam.location=tgt+Vector((0.9,-0.15,0.30)).normalized()*4.6
    cam.rotation_euler=(tgt-cam.location).to_track_quat('-Z','Y').to_euler()
    sc.render.filepath=r'C:\tmp\clip_%02d.png'%i
    bpy.ops.render.render(write_still=True)
print('RENDERED marked %d  (orange cone = her DESTINATION)'%len(FR))
