"""VORTEX DRIVER test. One parameter `water` (0..1) compiles into the whole
look: swirl phase, helical twist, centrifugal flare, gravity droop, and
column height. Proves the 'gushing vortex -> sad stream' read before it
becomes a shader uniform.

Physics story: spin vs gravity. High water -> centrifugal force throws the
strands out horizontal. Low water -> gravity wins and they hang."""
import bpy, math
from mathutils import Vector
for o in list(bpy.data.objects): bpy.data.objects.remove(o, do_unlink=True)
bpy.ops.import_scene.gltf(filepath=r'\\wsl.localhost\Ubuntu\home\khaled\Kore\water_elemental.glb')
o=max([x for x in bpy.data.objects if x.type=='MESH'],key=lambda x:len(x.data.vertices))
bpy.context.view_layer.objects.active=o
bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.mesh.remove_doubles(threshold=1e-5); bpy.ops.object.mode_set(mode='OBJECT')
bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
me=o.data
rest=[v.co.copy() for v in me.vertices]
zs=[c.z for c in rest]; Z0,Z1=min(zs),max(zs)
# strand factor: how far a vert is from the core column -> the vortex eye
# doesn't swirl, the outflung water does.
CORE_R=0.085; EDGE_R=0.26
def strand(c):
    r=math.hypot(c.x,c.y)
    return max(0.0,min(1.0,(r-CORE_R)/(EDGE_R-CORE_R)))

SPIN=2.30      # rad of phase at full water
TWIST=3.10     # helical: extra rotation per unit height
FLARE=0.55     # centrifugal outward push
DROOP=0.42     # gravity sag when the spin dies
SQUAT=0.30     # column loses height as it empties

def apply(water, t):
    for i,c in enumerate(rest):
        s=strand(c)
        r=math.hypot(c.x,c.y); th=math.atan2(c.y,c.x)
        h=(c.z-Z0)/(Z1-Z0)
        # swirl: phase + helix, both scaled by water and by strandness
        th += (SPIN*t + TWIST*h) * water * s
        # centrifugal flare vs gravity droop
        rr = r * (1.0 + FLARE*water*s)
        zz = c.z - DROOP*(1.0-water)*s*(0.35+0.65*h)
        # the whole column squats as she empties
        zz = Z0 + (zz-Z0)*(1.0 - SQUAT*(1.0-water))
        me.vertices[i].co = Vector((rr*math.cos(th), rr*math.sin(th), zz))
    me.update()

def measure():
    co=[v.co for v in me.vertices]
    zz=[c.z for c in co]; rr=[math.hypot(c.x,c.y) for c in co]
    return max(zz)-min(zz), sum(rr)/len(rr), max(rr)

sc=bpy.context.scene
try: sc.render.engine='BLENDER_EEVEE'
except TypeError: sc.render.engine='BLENDER_EEVEE_NEXT'
w=bpy.data.worlds.new('W'); w.use_nodes=True
w.node_tree.nodes['Background'].inputs['Color'].default_value=(.07,.09,.13,1); sc.world=w
mat=bpy.data.materials.new('aqua'); mat.use_nodes=True
bs=mat.node_tree.nodes['Principled BSDF']
bs.inputs['Base Color'].default_value=(0.32,0.70,1.0,1); bs.inputs['Roughness'].default_value=0.12
me.materials.clear(); me.materials.append(mat)
ctr=Vector((0,0,0))
for nm,off,e in (('K',Vector((-1,-1.2,1.0)),3.4),('F',Vector((1.3,-.9,.3)),1.6),('B',Vector((0,1.4,.6)),1.3)):
    d=bpy.data.lights.new(nm,'SUN'); d.energy=e
    ob=bpy.data.objects.new(nm,d); ob.location=ctr+off*2
    ob.rotation_euler=(ctr-ob.location).to_track_quat('-Z','Y').to_euler(); sc.collection.objects.link(ob)
sc.render.resolution_x,sc.render.resolution_y=360,520
cd=bpy.data.cameras.new('C'); cd.lens=45
cam=bpy.data.objects.new('C',cd); sc.collection.objects.link(cam); sc.camera=cam
cam.location=ctr+Vector((0.25,-1,0.05)).normalized()*1.85
cam.rotation_euler=(ctr-cam.location).to_track_quat('-Z','Y').to_euler()
print('WATER LEVEL -> silhouette:')
for i,wl in enumerate((1.0,0.65,0.35,0.12)):
    apply(wl, 0.0)
    h,rm,rx=measure()
    print('  water=%.2f  height=%.3f  mean_radius=%.3f  max_radius=%.3f'%(wl,h,rm,rx))
    sc.render.filepath=r'C:\tmp\vtx_%d.png'%i
    bpy.ops.render.render(write_still=True)
print('RENDERED 4')
