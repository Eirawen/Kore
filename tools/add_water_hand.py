"""Add a hand bone to the water elemental's arm.

Two bones cannot sell the moveset: a "snap" needs a wrist, and an arm
circling overhead reads through WHERE THE HAND POINTS. Extend the geodesic
arm trace one segment past arm1 to the true fingertip and hang a hand there.
"""
import bpy, heapq
from mathutils import Vector
bpy.ops.wm.open_mainfile(filepath=r'\\wsl.localhost\Ubuntu\home\khaled\Kore\water_rigged.blend')
ao=bpy.data.objects['WaterRig']; o=bpy.data.objects['WaterBody']
me=o.data; n=len(me.vertices)
adj=[[] for _ in range(n)]
for e in me.edges:
    a,b=e.vertices; adj[a].append(b); adj[b].append(a)
co=[v.co.copy() for v in me.vertices]
# the true extremity of the arm
tip=max(range(n),key=lambda j:(co[j].x**2+co[j].y**2)**0.5 if co[j].z>0.05 else -1)
print('fingertip=(%.3f,%.3f,%.3f)'%(co[tip].x,co[tip].y,co[tip].z))

arm1=ao.data.bones['arm1']
wrist=arm1.tail_local.copy()
tipv=co[tip]
handlen=(tipv-wrist).length
print('arm1 tail (wrist)=(%.3f,%.3f,%.3f)  ->  hand length %.3f'%(wrist.x,wrist.y,wrist.z,handlen))
if handlen < 0.02:
    # arm1 already reaches the tip: carve the last 35% of it into a hand
    a1h=arm1.head_local.copy()
    split=a1h.lerp(wrist,0.65)
    print('arm1 already reaches the tip; splitting at 65%% -> wrist=(%.3f,%.3f,%.3f)'%(split.x,split.y,split.z))
    newwrist, newtip = split, wrist
else:
    newwrist, newtip = wrist, tipv

bpy.context.view_layer.objects.active=ao
bpy.ops.object.mode_set(mode='EDIT')
eb=ao.data.edit_bones
e_arm1=eb['arm1']
if handlen < 0.02:
    e_arm1.tail = newwrist
hand=eb.new('arm_hand'); hand.head=newwrist; hand.tail=newtip
hand.parent=e_arm1; hand.use_connect=False
print('created arm_hand len=%.3f'%((newtip-newwrist).length))
bpy.ops.object.mode_set(mode='OBJECT')

# steal weights from arm1 for verts nearer the hand segment
vgA=o.vertex_groups.get('arm1'); vgH=o.vertex_groups.new(name='arm_hand')
hb=ao.data.bones['arm_hand']
def dseg(p,h,t):
    d=t-h; L2=d.length_squared
    tt=0.0 if L2<1e-12 else max(0.0,min(1.0,(p-h).dot(d)/L2))
    return (p-(h+d*tt)).length
moved=0
for v in me.vertices:
    w=0.0
    for g in v.groups:
        if g.group==vgA.index: w=g.weight
    if w<=1e-4: continue
    dh=dseg(v.co,hb.head_local,hb.tail_local)
    da=dseg(v.co,ao.data.bones['arm1'].head_local,ao.data.bones['arm1'].tail_local)
    if dh<da:
        share=min(1.0, da/max(dh+da,1e-6))
        vgH.add([v.index], w*share, 'REPLACE')
        vgA.add([v.index], w*(1-share), 'REPLACE')
        moved+=1
print('hand claimed weight from %d verts'%moved)
bpy.ops.wm.save_as_mainfile(filepath=r'\\wsl.localhost\Ubuntu\home\khaled\Kore\water_rigged.blend')
print('SAVED — arm is now arm0 -> arm1 -> arm_hand')
