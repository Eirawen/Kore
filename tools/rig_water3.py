"""Refine the arm into a bone chain, and decompose the hair island (isl1)
into individual ribbon strands via geodesic farthest-point tracing."""
import bpy, heapq
from mathutils import Vector
for o in list(bpy.data.objects): bpy.data.objects.remove(o, do_unlink=True)
bpy.ops.import_scene.gltf(filepath=r'\\wsl.localhost\Ubuntu\home\khaled\Kore\water_elemental.glb')
o=max([x for x in bpy.data.objects if x.type=='MESH'],key=lambda x:len(x.data.vertices))
bpy.context.view_layer.objects.active=o
bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.mesh.remove_doubles(threshold=1e-5); bpy.ops.object.mode_set(mode='OBJECT')
me=o.data; mw=o.matrix_world; n=len(me.vertices)
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
co=[mw@v.co for v in me.vertices]

def geo(src, allowed):
    d={j:1e9 for j in allowed}; d[src]=0.0; pq=[(0.0,src)]
    while pq:
        dd,u=heapq.heappop(pq)
        if dd>d[u]+1e-12: continue
        for v in adj[u]:
            if v not in d: continue
            nd=dd+(co[u]-co[v]).length
            if nd<d[v]-1e-12: d[v]=nd; heapq.heappush(pq,(nd,v))
    return d

# ---------- ARM chain (fine bands inside geodesic 0..0.52) ----------
B=set(isl[0])
tip=max(B,key=lambda j:(co[j].x**2+co[j].y**2)**0.5 if co[j].z>0.05 else -1)
d=geo(tip,B)
print('ARM CHAIN (fine bands):')
joints=[]
for k in range(7):
    g0=0.52*k/7; g1=0.52*(k+1)/7
    sel=[j for j in B if g0<=d[j]<g1]
    if len(sel)<3: continue
    c=sum((co[j] for j in sel),Vector())/len(sel)
    r=sum((co[j]-c).length for j in sel)/len(sel)
    joints.append(c)
    print('   g=%.3f n=%-4d (%+.3f,%+.3f,%+.3f) spread=%.3f'%(g0,len(sel),c.x,c.y,c.z,r))

# ---------- HAIR strands: repeated farthest-point extraction ----------
H=set(isl[1])
print('HAIR island: %d verts'%len(H))
# root = the highest hair vert (crown of the head)
crown=max(H,key=lambda j:co[j].z)
dh=geo(crown,H)
reach=[j for j in H if dh[j]<1e8]
print('  crown=(%.3f,%.3f,%.3f) reach=%d maxgeo=%.3f'
      %(co[crown].x,co[crown].y,co[crown].z,len(reach),max(dh[j] for j in reach)))
remaining=set(reach); strands=[]
for s in range(8):
    if not remaining: break
    far=max(remaining,key=lambda j:dh[j])
    if dh[far]<0.25: break
    # walk from far back toward the crown along steepest geodesic descent
    path=[far]; cur=far; guard=0
    while dh[cur]>1e-6 and guard<400:
        nxt=min((v for v in adj[cur] if v in dh), key=lambda v: dh[v], default=None)
        if nxt is None or dh[nxt]>=dh[cur]-1e-9: break
        path.append(nxt); cur=nxt; guard+=1
    # claim a tube of verts around this path
    claimed={j for j in remaining if any((co[j]-co[p]).length<0.045 for p in path[::3])}
    remaining-=claimed
    p0,p1=co[path[0]],co[path[-1]]
    print('  strand%d: len=%.3f pathv=%-3d claimed=%-4d tip=(%+.3f,%+.3f,%+.3f) root=(%+.3f,%+.3f,%+.3f)'
          %(s,dh[far],len(path),len(claimed),p0.x,p0.y,p0.z,p1.x,p1.y,p1.z))
    strands.append(path)
print('  strands found=%d, unclaimed hair verts=%d'%(len(strands),len(remaining)))
print('SHARDS: %d islands, %d verts'%(len(isl)-2,sum(len(g) for g in isl[2:])))
