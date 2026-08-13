"""THE FAMILY PORTRAIT — everything the analytical outflank has produced.

Nobody in this frame was posed by hand. The spider's joints came from
geodesic tracing, the succubus's wings from a graft and eight named
emotions, the elemental's whole presence from one float. Three creatures,
one render, zero trade skill.
"""
import bpy, math
from mathutils import Vector

for o in list(bpy.data.objects): bpy.data.objects.remove(o, do_unlink=True)
for c in list(bpy.data.collections): bpy.data.collections.remove(c)
sc=bpy.context.scene

def bbox(objs):
    lo=Vector((1e9,)*3); hi=Vector((-1e9,)*3)
    for o in objs:
        if o.type!='MESH': continue
        for c in o.bound_box:
            w=o.matrix_world @ Vector(c)
            lo=Vector((min(lo.x,w.x),min(lo.y,w.y),min(lo.z,w.z)))
            hi=Vector((max(hi.x,w.x),max(hi.y,w.y),max(hi.z,w.z)))
    return lo,hi

def bring(path, name, loc, scale, rotz=0.0):
    before=set(bpy.data.objects)
    if path.endswith('.glb'):
        bpy.ops.import_scene.gltf(filepath=path)
    else:
        with bpy.data.libraries.load(path) as (src, dst):
            dst.objects=[o for o in src.objects]
        for o in dst.objects:
            if o is not None: sc.collection.objects.link(o)
    new=[o for o in bpy.data.objects if o not in before]
    roots=[o for o in new if o.parent is None]
    for r in roots:
        r.location = Vector(loc); r.scale=(scale,)*3
        r.rotation_mode='XYZ'; r.rotation_euler=(r.rotation_euler.x, r.rotation_euler.y, rotz)
    print('  %-12s objects=%d roots=%d'%(name,len(new),len(roots)))
    return new

K=r'\\wsl.localhost\Ubuntu\home\khaled\Kore' + '\\'
# EYEBALLING THE COMPOSITION GAVE A BUILDING-SIZED SPIDER. So: measure every
# creature, normalise each to a target height, plant them on the floor, and
# space them. The analytical outflank, applied to a family photo.
CAST=[(K+'spider.glb','spider',0.62,-1.55,math.radians(28)),
      (K+'succubus_winged.blend','succubus',1.70, 0.05,math.radians(-8)),
      (K+'water_rigged.blend','elemental',1.95, 1.65,math.radians(14))]
for path,name,target_h,x,rz in CAST:
    objs=bring(path,name,(0,0,0),1.0,rz)
    lo,hi=bbox(objs)
    h=max(hi.z-lo.z,1e-6)
    k=target_h/h
    roots=[o for o in objs if o.parent is None]
    for r in roots:
        r.scale=(r.scale.x*k, r.scale.y*k, r.scale.z*k)
    bpy.context.view_layer.update()
    lo,hi=bbox(objs)                       # re-measure after scaling
    for r in roots:
        r.location.x += x - (lo.x+hi.x)*0.5
        r.location.y += 0.0
        r.location.z += -lo.z               # plant on the floor
    bpy.context.view_layer.update()
    lo,hi=bbox(objs)
    print('  %-10s h=%.2f  x=[%.2f..%.2f]  base_z=%.3f'%(name,hi.z-lo.z,lo.x,hi.x,lo.z))

# one shared material family so they read as a set
def tint(objs, rgb, rough, alpha=1.0):
    m=bpy.data.materials.new('t'); m.use_nodes=True
    b=m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value=(*rgb,1); b.inputs['Roughness'].default_value=rough
    if alpha<1.0:
        m.blend_method='BLEND'
        try: b.inputs['Alpha'].default_value=alpha
        except Exception: pass
    for o in objs:
        if o.type=='MESH':
            o.data.materials.clear(); o.data.materials.append(m)

allm=[o for o in bpy.data.objects if o.type=='MESH']
for o in allm:
    n=o.name.lower()
    if 'water' in n:      tint([o],(0.30,0.70,1.00),0.10,0.55)
    elif 'wing' in n:     tint([o],(0.72,0.30,0.42),0.42)
    elif 'spider' in n or 'mesh' in n: tint([o],(0.42,0.34,0.40),0.55)
    else:                 tint([o],(0.88,0.74,0.72),0.48)

try: sc.render.engine='BLENDER_EEVEE'
except TypeError: sc.render.engine='BLENDER_EEVEE_NEXT'
w=bpy.data.worlds.new('W'); w.use_nodes=True
w.node_tree.nodes['Background'].inputs['Color'].default_value=(.05,.06,.09,1); sc.world=w
ctr=Vector((0.05,0.0,0.95))
for nm,off,e,col in (('K',Vector((-1.1,-1.3,0.95)),3.6,(1,.96,.90)),
                     ('F',Vector(( 1.5,-0.8,0.30)),1.7,(.80,.88,1.0)),
                     ('R',Vector(( 0.0, 1.6,0.70)),2.2,(.86,.90,1.0))):
    d=bpy.data.lights.new(nm,'SUN'); d.energy=e; d.color=col
    ob=bpy.data.objects.new(nm,d); ob.location=ctr+off*4
    ob.rotation_euler=(ctr-ob.location).to_track_quat('-Z','Y').to_euler()
    sc.collection.objects.link(ob)
sc.render.resolution_x, sc.render.resolution_y = 1100, 620
cd=bpy.data.cameras.new('C'); cd.lens=52
cam=bpy.data.objects.new('C',cd); sc.collection.objects.link(cam); sc.camera=cam
cam.location=ctr+Vector((0.18,-1.0,0.20)).normalized()*6.4
cam.rotation_euler=(ctr-cam.location).to_track_quat('-Z','Y').to_euler()
sc.render.filepath=r'C:\tmp\family.png'
bpy.ops.render.render(write_still=True)
print('PORTRAIT RENDERED')
