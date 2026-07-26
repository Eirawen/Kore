"""Water elemental rig v1 — probe the medial structure of the body island
and lay out the column + arm chain. Measurement pass: report joints before
creating anything, so the anatomy is confirmed numerically first."""
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
gg={}
for i in range(n): gg.setdefault(find(i),[]).append(i)
isl=sorted(gg.values(),key=len,reverse=True)
co=[mw@v.co for v in me.vertices]
body=isl[0]

# --- COLUMN: centroid per height slice = the medial axis of the trunk.
# Exclude the arm by rejecting verts beyond a radius gate per slice.
print('COLUMN (medial centroids, arm excluded):')
col=[]
for k in range(20):
    z0=-0.5+k*0.05; z1=z0+0.05
    sel=[co[j] for j in body if z0<=co[j].z<z1]
    if len(sel)<4: continue
    c0=Vector((sum(p.x for p in sel)/len(sel), sum(p.y for p in sel)/len(sel),0))
    r=sorted((Vector((p.x,p.y,0))-c0).length for p in sel)
    gate=r[int(len(r)*0.75)]*1.35          # drop the outlier arm verts
    keep=[p for p in sel if (Vector((p.x,p.y,0))-c0).length<=gate]
    c=sum(keep,Vector())/len(keep)
    col.append((c, len(keep), gate))
    print('  z=%+.3f  n=%-4d ctr=(%+.3f,%+.3f)  r75=%.3f' % (c.z,len(keep),c.x,c.y,gate))

# --- ARM: verts beyond the column gate, above the waist
print('ARM branch (verts outside the column gate, z>0.10):')
arm=[]
for j in body:
    p=co[j]
    if p.z<0.10: continue
    near=min(col,key=lambda t:abs(t[0].z-p.z))
    if (Vector((p.x,p.y,0))-Vector((near[0].x,near[0].y,0))).length > near[2]:
        arm.append(p)
if arm:
    ctr=sum(arm,Vector())/len(arm)
    far=max(arm,key=lambda p:(p-ctr).length)
    root=min(arm,key=lambda p:(Vector((p.x,p.y,0))).length)
    print('  n=%d  centroid=(%.3f,%.3f,%.3f)' % (len(arm),ctr.x,ctr.y,ctr.z))
    print('  shoulder-ish=(%.3f,%.3f,%.3f)  tip=(%.3f,%.3f,%.3f)  len=%.3f'
          % (root.x,root.y,root.z, far.x,far.y,far.z, (far-root).length))
    # sample the arm centerline along its own long axis
    ax=(far-root).normalized()
    print('  arm centerline samples:')
    for t in (0.0,0.25,0.5,0.75,1.0):
        tgt=root+(far-root)*t
        near=[p for p in arm if abs((p-root).dot(ax)-(far-root).length*t)<0.05]
        if near:
            c=sum(near,Vector())/len(near)
            print('     t=%.2f n=%-3d ctr=(%+.3f,%+.3f,%+.3f)'%(t,len(near),c.x,c.y,c.z))
print('ISL1 (hair mass) extent: v=%d'%len(isl[1]))
h=[co[j] for j in isl[1]]
print('  z=[%.2f..%.2f] x=[%.2f..%.2f] y=[%.2f..%.2f]'
      %(min(p.z for p in h),max(p.z for p in h),min(p.x for p in h),max(p.x for p in h),
        min(p.y for p in h),max(p.y for p in h)))
