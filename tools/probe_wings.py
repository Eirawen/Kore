"""Probe the wing geometry + leg proportions.

Wings: which bone(s) are they weighted to, are they a separate island of
geometry, and where do they attach? That decides whether they can be
rigged (bones + reweight) or must be driven some other way.
Legs: segment lengths for the foot-planting IK the jump needs.
"""
import bpy
import math
from mathutils import Vector

GLB = '/home/khaled/Kore/succubus_walk.glb'

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=GLB)
scene = bpy.context.scene
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
mesh = next(o for o in bpy.data.objects if o.type == 'MESH')
if arm.animation_data:
    arm.animation_data_clear()
from mathutils import Quaternion
for pb in arm.pose.bones:
    pb.rotation_mode = 'QUATERNION'
    pb.rotation_quaternion = Quaternion()
    pb.location = (0, 0, 0)
bpy.context.view_layer.update()
mw = arm.matrix_world

print('MESH verts=%d groups=%d' % (len(mesh.data.vertices),
                                   len(mesh.vertex_groups)))

# ── connected components (islands) of the mesh ──
import bmesh
bm = bmesh.new()
bm.from_mesh(mesh.data)
bm.verts.ensure_lookup_table()
seen = set()
islands = []
for v in bm.verts:
    if v.index in seen:
        continue
    stack, comp = [v], []
    seen.add(v.index)
    while stack:
        cur = stack.pop()
        comp.append(cur.index)
        for e in cur.link_edges:
            o = e.other_vert(cur)
            if o.index not in seen:
                seen.add(o.index)
                stack.append(o)
    islands.append(comp)
islands.sort(key=len, reverse=True)
print('ISLANDS %d: sizes %s' % (len(islands), [len(i) for i in islands[:8]]))

gname = {g.index: g.name for g in mesh.vertex_groups}

def describe(idxs, label):
    pts = [mesh.matrix_world @ mesh.data.vertices[i].co for i in idxs]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    wsum = {}
    for i in idxs:
        for g in mesh.data.vertices[i].groups:
            if g.weight > 0.15:
                wsum[gname.get(g.group, '?')] = wsum.get(gname.get(g.group, '?'), 0) + g.weight
    top = sorted(wsum.items(), key=lambda x: -x[1])[:5]
    print('%s n=%d bbox_lo=%s hi=%s' % (label, len(idxs),
          [round(v, 3) for v in lo], [round(v, 3) for v in hi]))
    print('   weighted to: %s' % ', '.join('%s=%.0f' % t for t in top))
    return lo, hi

for k, comp in enumerate(islands[:6]):
    describe(comp, 'ISLAND%d' % k)

# ── candidate wing verts by geometry: high up, BEHIND the torso (+Y),
# and lateral. She faces -Y, so wings live at +Y.
shoulder_z = (mw @ arm.pose.bones['LeftShoulder'].head).z
spine_y = (mw @ arm.pose.bones['Spine'].head).y
cand = [v.index for v in mesh.data.vertices
        if (mesh.matrix_world @ v.co).z > shoulder_z - 0.25
        and (mesh.matrix_world @ v.co).y > spine_y + 0.02]
if cand:
    describe(cand, 'WING-CANDIDATES (above shoulder, behind spine)')

bm.free()

# ── leg proportions for foot-planting IK ──
def bp(n):
    return mw @ arm.pose.bones[n].head

for side in ('Left', 'Right'):
    hip = bp(side + 'UpLeg')
    knee = bp(side + 'Leg')
    ankle = bp(side + 'Foot')
    toe = bp(side + 'ToeBase')
    print('LEG[%s] thigh=%.3f shin=%.3f foot=%.3f  hip_z=%.3f ankle_z=%.3f toe_z=%.3f'
          % (side, (knee - hip).length, (ankle - knee).length,
             (toe - ankle).length, hip.z, ankle.z, toe.z))

# lowest vertex = the ground plane she stands on
zmin = min((mesh.matrix_world @ v.co).z for v in mesh.data.vertices)
print('GROUND lowest_vert_z=%.4f  hips_z=%.3f' % (zmin, bp('Hips').z))
