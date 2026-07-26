"""Water elemental rig v2. Fixes v1's tearing:
  (a) hair chain from Z-BANDS (monotonic down by construction, not geodesic
      centroids which zigzag at max distance)
  (b) WEIGHT DIFFUSION over the mesh graph -> continuity across every seam,
      which is what killed the arm/trunk cliff and the hair rip."""
import bpy, heapq, math
from mathutils import Vector
for o in list(bpy.data.objects): bpy.data.objects.remove(o, do_unlink=True)
bpy.ops.import_scene.gltf(filepath=r'\\wsl.localhost\Ubuntu\home\khaled\Kore\water_elemental.glb')
o=max([x for x in bpy.data.objects if x.type=='MESH'],key=lambda x:len(x.data.vertices)); o.name='WaterBody'
bpy.context.view_layer.objects.active=o
bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.mesh.remove_doubles(threshold=1e-5); bpy.ops.object.mode_set(mode='OBJECT')
bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
me=o.data; n=len(me.vertices)
par=list(range(n)); adj=[[] for _ in range(n)]
def find(a):
    while par[a]!=a: par[a]=par[par[a]]; a=par[a]
    return a
for e in me.edges:
    a,b=e.vertices; adj[a].append(b); adj[b].append(a)
    x,y=find(a),find(b)
    if x!=y: par[x]=y
gg={}
for i in range(n): gg.setdefault(find(i),[]).append(i)
isl=sorted(gg.values(),key=len,reverse=True)
co=[v.co.copy() for v in me.vertices]
BODY,HAIR=set(isl[0]),set(isl[1])
def geo(src,allowed):
    d={j:1e9 for j in allowed}; d[src]=0.0; pq=[(0.0,src)]
    while pq:
        dd,u=heapq.heappop(pq)
        if dd>d[u]+1e-12: continue
        for v in adj[u]:
            if v not in d: continue
            nd=dd+(co[u]-co[v]).length
            if nd<d[v]-1e-12: d[v]=nd; heapq.heappush(pq,(nd,v))
    return d
tip=max(BODY,key=lambda j:(co[j].x**2+co[j].y**2)**0.5 if co[j].z>0.05 else -1)
dArm=geo(tip,BODY); ARM_G=0.40
armset={j for j in BODY if dArm[j]<ARM_G}; trunk=BODY-armset

zs=[co[j].z for j in trunk]; z0,z1=min(zs),max(zs); NCOL=7
colpts=[]
for k in range(NCOL+1):
    zz=z0+(z1-z0)*k/NCOL
    sel=[co[j] for j in trunk if abs(co[j].z-zz)<(z1-z0)/NCOL*0.6]
    c=(sum(sel,Vector())/len(sel)) if sel else Vector((0,0,zz))
    colpts.append(Vector((c.x,c.y,zz)))
armpts=[]
for k in range(6,-1,-1):
    g0,g1=ARM_G*k/7,ARM_G*(k+1)/7
    sel=[co[j] for j in armset if g0<=dArm[j]<g1]
    if len(sel)>=3: armpts.append(sum(sel,Vector())/len(sel))
armpts=[armpts[0],armpts[len(armpts)//2],armpts[-1]]
# --- HAIR: z-bands, top to bottom. Monotonic by construction. ---
hz=[co[j].z for j in HAIR]; hz0,hz1=min(hz),max(hz); NH=4
hairpts=[]
for k in range(NH+1):
    zz=hz1-(hz1-hz0)*k/NH
    sel=[co[j] for j in HAIR if abs(co[j].z-zz)<(hz1-hz0)/NH*0.7]
    c=(sum(sel,Vector())/len(sel)) if sel else Vector((0,0,zz))
    hairpts.append(Vector((c.x,c.y,zz)))
arm=bpy.data.armatures.new('WaterRig')
ao=bpy.data.objects.new('WaterRig',arm); bpy.context.collection.objects.link(ao)
bpy.context.view_layer.objects.active=ao; bpy.ops.object.mode_set(mode='EDIT')
def mk(nm,h,t,p=None):
    b=arm.edit_bones.new(nm); b.head=h; b.tail=t
    if p: b.parent=p; b.use_connect=False
    return b
COL=[mk('col0',colpts[0],colpts[1])]
for i in range(1,NCOL): COL.append(mk('col%d'%i,colpts[i],colpts[i+1],COL[-1]))
host=min(range(NCOL),key=lambda i:abs((COL[i].head.z+COL[i].tail.z)/2-armpts[0].z))
ARM=[mk('arm0',armpts[0],armpts[1],COL[host])]
for i in range(1,len(armpts)-1): ARM.append(mk('arm%d'%i,armpts[i],armpts[i+1],ARM[-1]))
HB=[mk('hair0',hairpts[0],hairpts[1],COL[-1])]
for i in range(1,NH): HB.append(mk('hair%d'%i,hairpts[i],hairpts[i+1],HB[-1]))
print('HAIR chain (z-bands):')
for i,b in enumerate(HB): print('   hair%d (%+.3f,%+.3f,%+.3f) -> z %+.3f  len=%.3f'%(i,b.head.x,b.head.y,b.head.z,b.tail.z,(b.tail-b.head).length))
bpy.ops.object.mode_set(mode='OBJECT')
names=['col%d'%i for i in range(NCOL)]+['arm%d'%i for i in range(len(ARM))]+['hair%d'%i for i in range(NH)]
BN={nm:(arm.bones[nm].head_local,arm.bones[nm].tail_local) for nm in names}
def dseg(p,h,t):
    d=t-h; L2=d.length_squared
    tt=0.0 if L2<1e-12 else max(0.0,min(1.0,(p-h).dot(d)/L2))
    return (p-(h+d*tt)).length
# --- initial weights: inverse-distance over the K nearest bones (SOFT) ---
K=3; W=[dict() for _ in range(n)]
for j in range(n):
    p=co[j]
    ds=sorted(((dseg(p,*BN[nm]),nm) for nm in names))[:K]
    tot=0.0; tmp={}
    for d,nm in ds:
        w=1.0/max(d,1e-4)**2; tmp[nm]=w; tot+=w
    for nm in tmp: W[j][nm]=tmp[nm]/tot
# --- WEIGHT DIFFUSION: average against neighbours -> seam continuity ---
for it in range(12):
    NW=[]
    for j in range(n):
        acc=dict(W[j])
        for nm in acc: acc[nm]*=0.45
        nb=adj[j]
        if nb:
            f=0.55/len(nb)
            for v in nb:
                for nm,w in W[v].items(): acc[nm]=acc.get(nm,0.0)+w*f
        s=sum(acc.values())
        NW.append({k:v/s for k,v in acc.items() if v/s>0.004})
    W=NW
vg={nm:o.vertex_groups.new(name=nm) for nm in names}
for j in range(n):
    s=sum(W[j].values())
    for nm,w in W[j].items(): vg[nm].add([j],w/s,'REPLACE')
o.parent=ao
m=o.modifiers.new('Armature','ARMATURE'); m.object=ao
avg=sum(len(w) for w in W)/n
print('WEIGHTS: %d verts, avg %.2f bones/vert (diffused 12x)'%(n,avg))
bpy.ops.wm.save_as_mainfile(filepath=r'\\wsl.localhost\Ubuntu\home\khaled\Kore\water_rigged.blend')
print('SAVED')
