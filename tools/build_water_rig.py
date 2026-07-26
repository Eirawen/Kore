"""Water elemental rig v1. Column + arm + hair-mass chain, weighted by
geodesic/height bands. She is mostly shader; the skeleton is small and
purposeful: sway, gesture, and a spring cascade for gliding locomotion."""
import bpy, heapq, math
from mathutils import Vector
for o in list(bpy.data.objects): bpy.data.objects.remove(o, do_unlink=True)
bpy.ops.import_scene.gltf(filepath=r'\\wsl.localhost\Ubuntu\home\khaled\Kore\water_elemental.glb')
o=max([x for x in bpy.data.objects if x.type=='MESH'],key=lambda x:len(x.data.vertices))
o.name='WaterBody'
bpy.context.view_layer.objects.active=o
bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.mesh.remove_doubles(threshold=1e-5); bpy.ops.object.mode_set(mode='OBJECT')
bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)  # GOTCHA #1
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
SHARD=set(); [SHARD.update(g) for g in isl[2:]]

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
dArm=geo(tip,BODY); ARM_G=0.40                      # boundary from the spread analysis
armset={j for j in BODY if dArm[j]<ARM_G}
trunk=BODY-armset
crown=max(HAIR,key=lambda j:co[j].z); dHair=geo(crown,HAIR)

# ---- column joints: centroid per height band of the TRUNK ----
zs=[co[j].z for j in trunk]; z0,z1=min(zs),max(zs)
NCOL=7; colpts=[]
for k in range(NCOL+1):
    zz=z0+(z1-z0)*k/NCOL
    sel=[co[j] for j in trunk if abs(co[j].z-zz)<(z1-z0)/NCOL*0.6]
    c=(sum(sel,Vector())/len(sel)) if sel else Vector((0,0,zz))
    colpts.append(Vector((c.x,c.y,zz)))
# ---- arm joints from geodesic bands (tip -> shoulder), reversed to body->tip
armpts=[]
for k in range(6,-1,-1):
    g0,g1=ARM_G*k/7,ARM_G*(k+1)/7
    sel=[co[j] for j in armset if g0<=dArm[j]<g1]
    if len(sel)>=3: armpts.append(sum(sel,Vector())/len(sel))
armpts=[armpts[0],armpts[len(armpts)//2],armpts[-1]] if len(armpts)>=3 else armpts
# ---- hair chain from geodesic bands ----
mxh=max(dHair[j] for j in HAIR); NH=5; hairpts=[]
for k in range(NH+1):
    g=mxh*k/NH
    sel=[co[j] for j in HAIR if abs(dHair[j]-g)<mxh/NH*0.6]
    if sel: hairpts.append(sum(sel,Vector())/len(sel))

arm=bpy.data.armatures.new('WaterRig')
ao=bpy.data.objects.new('WaterRig',arm); bpy.context.collection.objects.link(ao)
bpy.context.view_layer.objects.active=ao; bpy.ops.object.mode_set(mode='EDIT')
def mk(name,h,t,parent=None):
    b=arm.edit_bones.new(name); b.head=h; b.tail=t
    if parent: b.parent=parent; b.use_connect=False
    return b
COL=[]
for i in range(len(colpts)-1):
    COL.append(mk('col%d'%i,colpts[i],colpts[i+1],COL[-1] if COL else None))
print('COLUMN bones:')
for i,b in enumerate(COL): print('   col%d head=(%+.3f,%+.3f,%+.3f) len=%.3f'%(i,b.head.x,b.head.y,b.head.z,(b.tail-b.head).length))
# attach arm to the column bone nearest the shoulder height
sh=armpts[0]
host=min(range(len(COL)),key=lambda i:abs((COL[i].head.z+COL[i].tail.z)/2-sh.z))
ARM=[]
for i in range(len(armpts)-1):
    ARM.append(mk('arm%d'%i,armpts[i],armpts[i+1],ARM[-1] if ARM else COL[host]))
print('ARM bones (host col%d):'%host)
for i,b in enumerate(ARM): print('   arm%d head=(%+.3f,%+.3f,%+.3f) len=%.3f'%(i,b.head.x,b.head.y,b.head.z,(b.tail-b.head).length))
HAIRB=[]
for i in range(len(hairpts)-1):
    HAIRB.append(mk('hair%d'%i,hairpts[i],hairpts[i+1],HAIRB[-1] if HAIRB else COL[-1]))
print('HAIR bones:')
for i,b in enumerate(HAIRB): print('   hair%d head=(%+.3f,%+.3f,%+.3f) len=%.3f'%(i,b.head.x,b.head.y,b.head.z,(b.tail-b.head).length))
bpy.ops.object.mode_set(mode='OBJECT')

# ---------- WEIGHTS ----------
for b in list(COL)+list(ARM)+list(HAIRB):
    pass
names=['col%d'%i for i in range(len(COL))]+['arm%d'%i for i in range(len(ARM))]+['hair%d'%i for i in range(len(HAIRB))]
vg={nm:o.vertex_groups.new(name=nm) for nm in names}
def seg_t(p,h,t):
    d=t-h; L2=d.length_squared
    return 0.0 if L2<1e-12 else max(0.0,min(1.0,(p-h).dot(d)/L2))
bones=[(nm,arm.bones[nm].head_local,arm.bones[nm].tail_local) for nm in names]
def assign(idx, cand):
    p=co[idx]; best=[]
    for nm in cand:
        h,t=arm.bones[nm].head_local,arm.bones[nm].tail_local
        tt=seg_t(p,h,t); d=(p-(h+(t-h)*tt)).length
        best.append((d,nm))
    best.sort()
    d0,n0=best[0]
    if len(best)>1 and best[1][0]<d0*1.6:      # smooth blend between two nearest
        d1,n1=best[1]; w0=d1/(d0+d1); vg[n0].add([idx],w0,'REPLACE'); vg[n1].add([idx],1-w0,'REPLACE')
    else: vg[n0].add([idx],1.0,'REPLACE')
colnames=['col%d'%i for i in range(len(COL))]
armnames=['arm%d'%i for i in range(len(ARM))]
hairnames=['hair%d'%i for i in range(len(HAIRB))]
for j in trunk: assign(j,colnames)
for j in armset: assign(j,armnames+[colnames[host]])
for j in HAIR: assign(j,hairnames)
for j in SHARD: assign(j,names)          # shards ride the nearest bone
o.parent=ao
m=o.modifiers.new('Armature','ARMATURE'); m.object=ao
tot=sum(len(g) for g in isl)
print('WEIGHTS: trunk=%d arm=%d hair=%d shards=%d  (total %d/%d)'%(len(trunk),len(armset),len(HAIR),len(SHARD),len(trunk)+len(armset)+len(HAIR)+len(SHARD),tot))
print('BONES TOTAL: %d'%len(names))
bpy.ops.wm.save_as_mainfile(filepath=r'\\wsl.localhost\Ubuntu\home\khaled\Kore\water_rigged.blend')
print('SAVED water_rigged.blend')
