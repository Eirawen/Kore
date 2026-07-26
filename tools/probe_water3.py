import bpy, math
from mathutils import Vector
for o in list(bpy.data.objects): bpy.data.objects.remove(o, do_unlink=True)
bpy.ops.import_scene.gltf(filepath=r'\\wsl.localhost\Ubuntu\home\khaled\Kore\water_elemental.glb')
o = max([x for x in bpy.data.objects if x.type=='MESH'], key=lambda x: len(x.data.vertices))
bpy.context.view_layer.objects.active=o
bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.mesh.remove_doubles(threshold=1e-5); bpy.ops.object.mode_set(mode='OBJECT')
me=o.data; mw=o.matrix_world
n=len(me.vertices); par=list(range(n))
def find(a):
    while par[a]!=a: par[a]=par[par[a]]; a=par[a]
    return a
for e in me.edges:
    a,b=find(e.vertices[0]),find(e.vertices[1])
    if a!=b: par[a]=b
g={}
for i in range(n): g.setdefault(find(i),[]).append(i)
isl=sorted(g.values(),key=len,reverse=True)
co=[mw@v.co for v in me.vertices]
vi={}
for i,grp in enumerate(isl):
    for j in grp: vi[j]=i

# --- where is the ARM? the extremity furthest from the vertical axis, up high
best=max(range(n), key=lambda j: (co[j].x**2+co[j].y**2)**0.5 if co[j].z>0.05 else -1)
p=co[best]
print('ARM TIP  vert=%d  pos=(%.3f,%.3f,%.3f)  radius=%.3f  ISLAND=isl%d'
      % (best,p.x,p.y,p.z,(p.x**2+p.y**2)**0.5, vi[best]))
# highest point (head/hair top)
hi=max(range(n), key=lambda j: co[j].z); p=co[hi]
print('TOP      pos=(%.3f,%.3f,%.3f) ISLAND=isl%d' % (p.x,p.y,p.z, vi[hi]))
# lowest (base)
lo=min(range(n), key=lambda j: co[j].z); p=co[lo]
print('BOTTOM   pos=(%.3f,%.3f,%.3f) ISLAND=isl%d' % (p.x,p.y,p.z, vi[lo]))
# radius profile of isl0 by height -> where is the body column vs the flare
b0=isl[0]
print('isl0 RADIUS PROFILE (body column vs base flare):')
for k in range(10):
    z0=-0.5+k*0.1; z1=z0+0.1
    sel=[co[j] for j in b0 if z0<=co[j].z<z1]
    if sel:
        r=[ (c.x**2+c.y**2)**0.5 for c in sel]
        print('   z=[%+.2f..%+.2f] n=%-4d  r_mean=%.3f r_max=%.3f' % (z0,z1,len(sel),sum(r)/len(r),max(r)))

# colour by island tier and render
mats=[]
for name,rgb in (('BODY',(0.15,0.55,1,1)),('HAIR',(1,0.25,0.6,1)),('SHARD',(1,0.85,0.2,1))):
    m=bpy.data.materials.new(name); m.use_nodes=True
    m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=rgb
    mats.append(m); me.materials.append(m)
for poly in me.polygons:
    i=vi[poly.vertices[0]]
    poly.material_index = 0 if i==0 else (1 if i==1 else 2)
sc=bpy.context.scene
try: sc.render.engine='BLENDER_EEVEE'
except TypeError: sc.render.engine='BLENDER_EEVEE_NEXT'
w=bpy.data.worlds.new('W'); w.use_nodes=True
w.node_tree.nodes['Background'].inputs['Color'].default_value=(.1,.1,.12,1); sc.world=w
for nm,off,e in (('K',Vector((-1,-1.2,1.1)),3.0),('F',Vector((1.3,-.9,.3)),1.4),('B',Vector((0,1.4,.5)),1.0)):
    d=bpy.data.lights.new(nm,'SUN'); d.energy=e
    ob=bpy.data.objects.new(nm,d); ob.location=Vector((0,0,0))+off*2
    ob.rotation_euler=(Vector((0,0,0))-ob.location).to_track_quat('-Z','Y').to_euler()
    sc.collection.objects.link(ob)
sc.render.resolution_x, sc.render.resolution_y = 460,620
cd=bpy.data.cameras.new('C'); cd.lens=45
cam=bpy.data.objects.new('C',cd); sc.collection.objects.link(cam); sc.camera=cam
for i,(dv,lbl) in enumerate((((0,-1,0.05),'front'),((0.9,-0.7,0.10),'3q'),((1,0,0.05),'side'))):
    cam.location=Vector(dv).normalized()*1.75
    cam.rotation_euler=(Vector((0,0,0))-cam.location).to_track_quat('-Z','Y').to_euler()
    sc.render.filepath=r'C:\tmp\water_%d.png'%i
    bpy.ops.render.render(write_still=True)
print('RENDERED 3')
