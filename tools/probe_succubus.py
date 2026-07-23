"""Probe the succubus rig: armatures, bone hierarchy, rest orientations,
meshes, dimensions, actions. Run headless; prints a compact report."""
import bpy
import json
from mathutils import Vector

print("PROBE_START")

report = {'objects': [], 'armatures': {}, 'actions': [a.name for a in bpy.data.actions]}

for obj in bpy.data.objects:
    entry = {'name': obj.name, 'type': obj.type,
             'loc': [round(v, 3) for v in obj.location],
             'scale': [round(v, 3) for v in obj.scale],
             'parent': obj.parent.name if obj.parent else None}
    if obj.type == 'MESH':
        entry['verts'] = len(obj.data.vertices)
        entry['dims'] = [round(v, 3) for v in obj.dimensions]
        mods = [(m.type, getattr(m, 'object', None).name if getattr(m, 'object', None) else '')
                for m in obj.modifiers]
        entry['modifiers'] = mods
        entry['vgroups'] = len(obj.vertex_groups)
    report['objects'].append(entry)

for obj in bpy.data.objects:
    if obj.type != 'ARMATURE':
        continue
    arm = obj.data
    bones = {}
    for b in arm.bones:
        bones[b.name] = {
            'parent': b.parent.name if b.parent else None,
            'head': [round(v, 3) for v in b.head_local],
            'tail': [round(v, 3) for v in b.tail_local],
            'connected': b.use_connect,
        }
    report['armatures'][obj.name] = {
        'bone_count': len(arm.bones),
        'bones': bones,
    }

print(json.dumps(report, indent=1))
print("PROBE_END")
