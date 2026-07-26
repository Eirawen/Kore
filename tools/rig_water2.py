"""Geodesic arm trace: BFS along mesh edges from the true extremity inward.
Centroid per geodesic band = the arm's real centerline (spider-leg method)."""
import bpy, math
from collections import deque
from mathutils import Vector
for o in list(bpy.data.objects): bpy.data.objects.remove(o, do_unlink=True)
bpy.ops.import_scene.gltf(filepath=r'\\wsl.localhost\Ubuntu\home\khaled\Kore\water_elemental.glb')
o=max([x for x in bpy.data.objects if x.type=='MESH'],key=lambda x:len(x.data.vertices))
bpy.context.view_layer.objects.active=o
bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.mesh.remove_doubles(threshold=1e-5); bpy.ops.object.mode_set(mode='OBJECT')
me=o.data; mw=o.matrix_world
n=len(me.vertices); par=list(range(n))
def find(a):
    while par[a]!=a: par[a]=par[par[a]]; a=par[a]
    return a
adj=[[] for _ in range(n)]
for e in me.edges:
    a,b=e.vertices; adj[a].append(b); adj[b].append(a)
    x,y=find(a),find(b)
    if x!=y: par[x]=y
gg={}
for i in range(n): gg.setdefault(find(i),[]).append(i)
isl=sorted(gg.values(),key=len,reverse=True)
co=[mw@v.co for v in me.vertices]
bodyset=set(isl[0])

# true extremity of the body island: furthest from the vertical axis, upper half
tip=max(bodyset,key=lambda j:(co[j].x**2+co[j].y**2)**0.5 if co[j].z>0.05 else -1)
print('TIP vert=%d pos=(%.3f,%.3f,%.3f)'%(tip,co[tip].x,co[tip].y,co[tip].z))

# geodesic distance along edges from the tip, within the body island
INF=1e9; dist=[INF]*n; dist[tip]=0.0
import heapq
pq=[(0.0,tip)]
while pq:
    d,u=heapq.heappop(pq)
    if d>dist[u]+1e-12: continue
    for v in adj[u]:
        if v not in bodyset: continue
        nd=d+(co[u]-co[v]).length
        if nd<dist[v]-1e-12:
            dist[v]=nd; heapq.heappush(pq,(nd,v))
reach=[j for j in bodyset if dist[j]<INF]
mx=max(dist[j] for j in reach)
print('geodesic reach: %d verts, max dist %.3f'%(len(reach),mx))
print('CENTERLINE by geodesic band:')
NB=12
pts=[]
for k in range(NB):
    d0=mx*k/NB; d1=mx*(k+1)/NB
    sel=[j for j in reach if d0<=dist[j]<d1]
    if len(sel)<3: continue
    c=sum((co[j] for j in sel),Vector())/len(sel)
    r=sum((co[j]-c).length for j in sel)/len(sel)
    pts.append((d0,c,len(sel),r))
    print('  g=[%.2f..%.2f] n=%-4d ctr=(%+.3f,%+.3f,%+.3f) spread=%.3f'
          %(d0,d1,len(sel),c.x,c.y,c.z,r))
# where does the spread blow up? that's where the arm joins the body
print('ARM/BODY BOUNDARY: first band where spread > 2x the running min:')
mn=1e9
for d0,c,cnt,r in pts:
    mn=min(mn,r)
    if r>mn*2.0:
        print('  -> at geodesic %.3f, ctr=(%+.3f,%+.3f,%+.3f) spread=%.3f (min was %.3f)'
              %(d0,c.x,c.y,c.z,r,mn)); break
