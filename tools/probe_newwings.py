"""Probe the generated wing asset: objects, islands, orientation, scale.
Everything the graft needs to be measured rather than guessed."""
import bpy
import bmesh
import math
from mathutils import Vector

GLB = '/home/khaled/Kore/wings_raw.glb'

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=GLB)

meshes = [o for o in bpy.data.objects if o.type == 'MESH']
arms = [o for o in bpy.data.objects if o.type == 'ARMATURE']
print('OBJECTS meshes=%d armatures=%d' % (len(meshes), len(arms)))
for o in bpy.data.objects:
    print('  %-28s %-9s loc=%s scale=%s'
          % (o.name[:28], o.type, [round(v, 3) for v in o.location],
             [round(v, 3) for v in o.scale]))

for m in meshes:
    print('MESH %s verts=%d polys=%d mats=%d groups=%d'
          % (m.name, len(m.data.vertices), len(m.data.polygons),
             len(m.data.materials), len(m.vertex_groups)))
    pts = [m.matrix_world @ v.co for v in m.data.vertices]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    print('  bbox lo=%s hi=%s  size=%s'
          % ([round(v, 3) for v in lo], [round(v, 3) for v in hi],
             [round(v, 3) for v in (hi - lo)]))
    for mat in m.data.materials:
        print('  material: %s' % (mat.name if mat else 'None'))

    # islands (the coloured components)
    bm = bmesh.new()
    bm.from_mesh(m.data)
    bm.verts.ensure_lookup_table()
    seen, islands = set(), []
    for v in bm.verts:
        if v.index in seen:
            continue
        stack, comp = [v], []
        seen.add(v.index)
        while stack:
            cur = stack.pop()
            comp.append(cur.index)
            for e in cur.link_edges:
                o2 = e.other_vert(cur)
                if o2.index not in seen:
                    seen.add(o2.index)
                    stack.append(o2)
        islands.append(comp)
    bm.free()
    islands.sort(key=len, reverse=True)
    print('  ISLANDS %d' % len(islands))
    for k, comp in enumerate(islands[:16]):
        cp = [m.matrix_world @ m.data.vertices[i].co for i in comp]
        clo = Vector((min(p.x for p in cp), min(p.y for p in cp), min(p.z for p in cp)))
        chi = Vector((max(p.x for p in cp), max(p.y for p in cp), max(p.z for p in cp)))
        ext = chi - clo
        # longest axis tells spar vs membrane
        axis = 'XYZ'[max(range(3), key=lambda i: ext[i])]
        thin = min(ext) / (max(ext) + 1e-9)
        print('    isl%-2d n=%-5d size=%s long=%s thin=%.3f cx=%+.3f'
              % (k, len(comp), [round(v, 3) for v in ext], axis, thin,
                 (clo.x + chi.x) / 2))

# orientation sanity: where is the mass relative to the origin
allpts = [m.matrix_world @ v.co for m in meshes for v in m.data.vertices]
cx = sum(p.x for p in allpts) / len(allpts)
cy = sum(p.y for p in allpts) / len(allpts)
cz = sum(p.z for p in allpts) / len(allpts)
print('CENTROID (%.3f, %.3f, %.3f)' % (cx, cy, cz))
left = [p for p in allpts if p.x > cx]
right = [p for p in allpts if p.x <= cx]
print('SPLIT by x: %d / %d  (a symmetric PAIR should be near-even)'
      % (len(left), len(right)))
