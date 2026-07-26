import bpy, sys
from mathutils import Vector
for o in list(bpy.data.objects): bpy.data.objects.remove(o, do_unlink=True)
bpy.ops.import_scene.gltf(filepath=r'\\wsl.localhost\Ubuntu\home\khaled\Kore\water_elemental.glb')
ms = [o for o in bpy.data.objects if o.type == 'MESH']
print('OBJECTS: %d mesh' % len(ms))
for o in ms:
    me = o.data
    print('  %-28s verts=%-6d faces=%-6d mats=%s' % (o.name, len(me.vertices), len(me.polygons), [m.name if m else None for m in me.materials]))

o = max(ms, key=lambda x: len(x.data.vertices))
me = o.data
mw = o.matrix_world
co = [mw @ v.co for v in me.vertices]
mn = Vector((min(c.x for c in co), min(c.y for c in co), min(c.z for c in co)))
mx = Vector((max(c.x for c in co), max(c.y for c in co), max(c.z for c in co)))
print('BBOX  x=%.3f y=%.3f z=%.3f  (min %.3f %.3f %.3f)' % (mx.x-mn.x, mx.y-mn.y, mx.z-mn.z, mn.x, mn.y, mn.z))

# connected islands via union-find on edges
n = len(me.vertices)
par = list(range(n))
def find(a):
    while par[a] != a:
        par[a] = par[par[a]]; a = par[a]
    return a
for e in me.edges:
    a, b = find(e.vertices[0]), find(e.vertices[1])
    if a != b: par[a] = b
groups = {}
for i in range(n): groups.setdefault(find(i), []).append(i)
isl = sorted(groups.values(), key=len, reverse=True)
print('ISLANDS: %d total' % len(isl))
tot = 0
for i, g in enumerate(isl[:16]):
    pts = [co[j] for j in g]
    bx = (max(p.x for p in pts)-min(p.x for p in pts),
          max(p.y for p in pts)-min(p.y for p in pts),
          max(p.z for p in pts)-min(p.z for p in pts))
    zc = (min(p.z for p in pts), max(p.z for p in pts))
    # aspect: is it a long thin strip (ribbon) or a blob?
    dims = sorted(bx, reverse=True)
    aspect = dims[0] / max(dims[1], 1e-6)
    print('  isl%-2d v=%-5d bbox=(%.2f,%.2f,%.2f) z=[%.2f..%.2f] aspect=%.1f %s'
          % (i, len(g), bx[0], bx[1], bx[2], zc[0], zc[1], aspect,
             'RIBBON' if aspect > 2.5 and len(g) < 400 else ''))
    tot += len(g)
print('  (top16 = %d of %d verts)' % (tot, n))
small = [g for g in isl if len(g) < 400]
print('SMALL ISLANDS (<400v): %d, totalling %d verts' % (len(small), sum(len(g) for g in small)))
