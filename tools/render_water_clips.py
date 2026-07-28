import bpy, sys
from mathutils import Vector
bpy.ops.wm.open_mainfile(filepath=r'\\wsl.localhost\Ubuntu\home\khaled\Kore\water_rigged.blend')
sc=bpy.context.scene
ao=bpy.data.objects['WaterRig']; o=bpy.data.objects['WaterBody']
clip=sys.argv[-1]
act=bpy.data.actions[clip]
ao.animation_data_create(); ao.animation_data.action=act
f0,f1=int(act.frame_range[0]),int(act.frame_range[1])
try: sc.render.engine='BLENDER_EEVEE'
except TypeError: sc.render.engine='BLENDER_EEVEE_NEXT'
w=bpy.data.worlds.new('W'); w.use_nodes=True
w.node_tree.nodes['Background'].inputs['Color'].default_value=(.07,.09,.13,1); sc.world=w
m=bpy.data.materials.new('aq'); m.use_nodes=True
bs=m.node_tree.nodes['Principled BSDF']
bs.inputs['Base Color'].default_value=(0.32,0.70,1.0,1); bs.inputs['Roughness'].default_value=0.12
o.data.materials.clear(); o.data.materials.append(m)
# per-clip framing; camera TRACKS her so travelling clips stay judgeable
DIST={'waveform':2.0,'react_scoop':1.7,'atk_wave_rise':1.9}.get(clip,1.9)
ctr=Vector((0,0,0))
for nm,off,e in (('K',Vector((-1,-1.2,1.0)),3.4),('F',Vector((1.3,-.9,.3)),1.6),('B',Vector((0,1.4,.6)),1.3)):
    d=bpy.data.lights.new(nm,'SUN'); d.energy=e
    ob=bpy.data.objects.new(nm,d); ob.location=ctr+off*3
    ob.rotation_euler=(ctr-ob.location).to_track_quat('-Z','Y').to_euler(); sc.collection.objects.link(ob)
sc.render.resolution_x,sc.render.resolution_y=300,400
cd=bpy.data.cameras.new('C'); cd.lens=40
cam=bpy.data.objects.new('C',cd); sc.collection.objects.link(cam); sc.camera=cam
N=8
for i in range(N):
    sc.frame_set(int(f0+(f1-f0)*i/(N-1)))
    tgt=Vector((ao.location.x, ao.location.y, 0.0))
    cam.location=tgt+Vector((0.85,-0.6,0.22)).normalized()*DIST
    cam.rotation_euler=(tgt-cam.location).to_track_quat('-Z','Y').to_euler()
    sc.render.filepath=r'C:\tmp\clip_%02d.png'%i
    bpy.ops.render.render(write_still=True)
print('RENDERED %s %d frames'%(clip,N))
