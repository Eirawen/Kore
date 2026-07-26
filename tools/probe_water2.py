import bpy, bmesh
from mathutils import Vector
for o in list(bpy.data.objects): bpy.data.objects.remove(o, do_unlink=True)
bpy.ops.import_scene.gltf(filepath=r'\\wsl.localhost\Ubuntu\home\khaled\Kore\water_elemental.glb')
o = max([x for x in bpy.data.objects if x.type=='MESH'], key=lambda x: len(x.data.vertices))
bpy.context.view_layer.objects.active = o

def islands(me, mw):
    n = len(me.vertices); par = list(range(n))
    def find(a):
        while par[a]!=a: par[a]=par[par[a]]; a=par[a]
        return a
    for e in me.edges:
        a,b = find(e.vertices[0]), find(e.vertices[1])
        if a!=b: par[a]=b
    g={}
    for i in range(n): g.setdefault(find(i),[]).append(i)
    return sorted(g.values(), key=len, reverse=True)

print('BEFORE merge: verts=%d islands=%d' % (len(o.data.vertices), len(islands(o.data, o.matrix_world))))
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.mesh.remove_doubles(threshold=1e-5)
bpy.ops.object.mode_set(mode='OBJECT')
isl = islands(o.data, o.matrix_world)
print('AFTER  merge: verts=%d islands=%d' % (len(o.data.vertices), len(isl)))

mw = o.matrix_world
co = [mw @ v.co for v in o.data.vertices]
print('--- top islands after merge ---')
for i,g in enumerate(isl[:14]):
    pts=[co[j] for j in g]
    bx=(max(p.x for p in pts)-min(p.x for p in pts),
        max(p.y for p in pts)-min(p.y for p in pts),
        max(p.z for p in pts)-min(p.z for p in pts))
    d=sorted(bx,reverse=True); asp=d[0]/max(d[1],1e-6)
    ctr=sum(pts,Vector())/len(pts)
    print('  isl%-2d v=%-5d %5.1f%%  bbox=(%.2f,%.2f,%.2f) z=[%.2f..%.2f] ctr=(%.2f,%.2f,%.2f) aspect=%.1f%s'
          % (i,len(g),100*len(g)/len(o.data.vertices),bx[0],bx[1],bx[2],
             min(p.z for p in pts),max(p.z for p in pts),ctr.x,ctr.y,ctr.z,asp,
             '  <-- RIBBON' if asp>2.5 else ''))
big=[g for g in isl if len(g)>=200]; mid=[g for g in isl if 40<=len(g)<200]; sml=[g for g in isl if len(g)<40]
print('TIERS: big(>=200v)=%d [%dv]  mid(40-199)=%d [%dv]  small(<40)=%d [%dv]'
      % (len(big),sum(len(g) for g in big),len(mid),sum(len(g) for g in mid),len(sml),sum(len(g) for g in sml)))
