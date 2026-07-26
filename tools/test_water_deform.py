"""Deformation test: pose the column, arm, and hair; measure mesh coherence
(neighbour-distance distortion) and render a strip."""
import bpy, math
from mathutils import Vector, Quaternion
bpy.ops.wm.open_mainfile(filepath=r'\\wsl.localhost\Ubuntu\home\khaled\Kore\water_rigged.blend')
sc=bpy.context.scene
ao=bpy.data.objects['WaterRig']; o=bpy.data.objects['WaterBody']
me=o.data
# baseline neighbour distances
nb=[]
for e in me.edges: nb.append((e.vertices[0],e.vertices[1],(me.vertices[e.vertices[0]].co-me.vertices[e.vertices[1]].co).length))
def distortion():
    deps=bpy.context.evaluated_depsgraph_get(); ev=o.evaluated_get(deps); m=ev.to_mesh()
    worst=0.0; bad=0
    for a,b,L0 in nb:
        if L0<1e-6: continue
        L=(m.vertices[a].co-m.vertices[b].co).length
        r=max(L/L0, L0/max(L,1e-9))
        if r>worst: worst=r
        if r>2.0: bad+=1
    ev.to_mesh_clear(); return worst,bad
def clear():
    for pb in ao.pose.bones: pb.rotation_mode='QUATERNION'; pb.rotation_quaternion=Quaternion()
    bpy.context.view_layer.update()
def rot(name,axis,deg):
    pb=ao.pose.bones[name]; pb.rotation_mode='QUATERNION'
    m=pb.bone.matrix_local.to_3x3().inverted()
    a=(m@Vector(axis)).normalized()
    pb.rotation_quaternion=pb.rotation_quaternion@Quaternion(a,math.radians(deg))
    bpy.context.view_layer.update()
NC=len([b for b in ao.pose.bones if b.name.startswith('col')])
NA=len([b for b in ao.pose.bones if b.name.startswith('arm')])
NH=len([b for b in ao.pose.bones if b.name.startswith('hair')])
SWAY=[('col%d'%i,(0,1,0),d) for i,d in zip(range(2,NC),(7,9,10,8,6,5))]
ARMP=[('arm%d'%i,(0,1,0),-40+10*i) for i in range(NA)]
HAIRP=[('hair%d'%i,(1,0,0),10+6*i) for i in range(NH)]
poses={}
clear(); poses['rest']=distortion()
clear()
for bn,ax,dg in SWAY: rot(bn,ax,dg)
poses['sway']=distortion()
clear()
for bn,ax,dg in ARMP: rot(bn,ax,dg)
poses['arm_raise']=distortion()
clear()
for bn,ax,dg in HAIRP: rot(bn,ax,dg)
poses['hair_swing']=distortion()
for k,(w,b) in poses.items(): print('POSE %-11s worst_edge_ratio=%.2f  edges_over_2x=%d'%(k,w,b))

# render strip
try: sc.render.engine='BLENDER_EEVEE'
except TypeError: sc.render.engine='BLENDER_EEVEE_NEXT'
w=bpy.data.worlds.new('W'); w.use_nodes=True
w.node_tree.nodes['Background'].inputs['Color'].default_value=(.09,.10,.13,1); sc.world=w
mat=bpy.data.materials.new('aqua'); mat.use_nodes=True
bs=mat.node_tree.nodes['Principled BSDF']
bs.inputs['Base Color'].default_value=(0.35,0.72,1.0,1)
bs.inputs['Roughness'].default_value=0.15
me.materials.clear(); me.materials.append(mat)
ctr=Vector((0,0,0))
for nm,off,e in (('K',Vector((-1,-1.2,1.0)),3.2),('F',Vector((1.3,-.9,.3)),1.5),('B',Vector((0,1.4,.6)),1.2)):
    d=bpy.data.lights.new(nm,'SUN'); d.energy=e
    ob=bpy.data.objects.new(nm,d); ob.location=ctr+off*2
    ob.rotation_euler=(ctr-ob.location).to_track_quat('-Z','Y').to_euler(); sc.collection.objects.link(ob)
sc.render.resolution_x,sc.render.resolution_y=380,540
cd=bpy.data.cameras.new('C'); cd.lens=45
cam=bpy.data.objects.new('C',cd); sc.collection.objects.link(cam); sc.camera=cam
cam.location=ctr+Vector((0.35,-1,0.06)).normalized()*1.8
cam.rotation_euler=(ctr-cam.location).to_track_quat('-Z','Y').to_euler()
seq=[('rest',None),('sway',SWAY),('arm_raise',ARMP),('hair_swing',HAIRP)]
for i,(nm,ops) in enumerate(seq):
    clear()
    if ops:
        for bn,ax,dg in ops: rot(bn,ax,dg)
    sc.render.filepath=r'C:\tmp\wdef_%d.png'%i
    bpy.ops.render.render(write_still=True)
print('RENDERED %d'%len(seq))
