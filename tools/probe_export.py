"""Probe cgtrader_hand.blend structure ahead of the GLB export spike.
Lists objects, parents, scales, armature bones, modifiers, constraints.
"""
import bpy
import json

out = []
for obj in bpy.data.objects:
    rec = {
        'name': obj.name, 'type': obj.type,
        'parent': obj.parent.name if obj.parent else None,
        'parent_type': obj.parent_type if obj.parent else None,
        'parent_bone': obj.parent_bone if obj.parent else '',
        'loc': [round(v, 3) for v in obj.location],
        'scale': [round(v, 3) for v in obj.scale],
        'hide_render': obj.hide_render,
        'modifiers': [(m.type, getattr(m, 'object', None).name
                       if getattr(m, 'object', None) else None)
                      for m in getattr(obj, 'modifiers', [])],
        'constraints': [c.type for c in obj.constraints],
    }
    if obj.type == 'ARMATURE':
        rec['bones'] = [(b.name, b.parent.name if b.parent else None)
                        for b in obj.data.bones]
        rec['bone_constraints'] = {
            pb.name: [c.type for c in pb.constraints]
            for pb in obj.pose.bones if pb.constraints}
    if obj.type == 'MESH':
        rec['verts'] = len(obj.data.vertices)
        rec['vgroups'] = len(obj.vertex_groups)
    out.append(rec)

print('PROBE_JSON_START')
print(json.dumps(out, indent=1))
print('PROBE_JSON_END')
