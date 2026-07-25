"""Is the membrane genuinely fused across the midline, or only bridged?
Measures the actual topology at x=0 so the split decision is data, not
my assertion."""
import bpy, bmesh, math
from mathutils import Vector

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath='/home/khaled/Kore/wings_raw.glb')
m = next(o for o in bpy.data.objects if o.type == 'MESH')
bm = bmesh.new(); bm.from_mesh(m.data)
bm.verts.ensure_lookup_table(); bm.faces.ensure_lookup_table()

xs = [v.co.x for v in bm.verts]
cx = (min(xs) + max(xs)) / 2
span = max(xs) - min(xs)
print('MIDLINE cx=%.4f span=%.3f' % (cx, span))

# how much geometry actually crosses the midline?
straddle = [f for f in bm.faces
            if any(v.co.x < cx for v in f.verts) and any(v.co.x > cx for v in f.verts)]
cross_e = [e for e in bm.edges
           if (e.verts[0].co.x - cx) * (e.verts[1].co.x - cx) < 0]
print('STRADDLE faces=%d of %d (%.1f%%)  edges crossing=%d of %d'
      % (len(straddle), len(bm.faces), 100.0 * len(straddle) / len(bm.faces),
         len(cross_e), len(bm.edges)))

# density profile near the centre: a PINCH shows as a dip
print('DENSITY (verts per 2%% slice of span, centre outward):')
row = []
for k in range(-6, 7):
    lo = cx + span * (k * 0.02 - 0.01)
    hi = cx + span * (k * 0.02 + 0.01)
    n = sum(1 for v in bm.verts if lo <= v.co.x < hi)
    row.append('%+.0f%%:%d' % (k * 2, n))
print('  ' + '  '.join(row))

# the z-extent of the straddling band tells us how TALL the bridge is
if straddle:
    zz = [v.co.z for f in straddle for v in f.verts]
    yy = [v.co.y for f in straddle for v in f.verts]
    print('BRIDGE z=[%.3f,%.3f] (%.3f tall)  y=[%.3f,%.3f]'
          % (min(zz), max(zz), max(zz) - min(zz), min(yy), max(yy)))
    print('       bridge height is %.1f%% of the asset height'
          % (100.0 * (max(zz) - min(zz)) / (max(v.co.z for v in bm.verts)
                                            - min(v.co.z for v in bm.verts))))

# is there an existing edge loop AT the midline to cut along cleanly?
onmid = [v for v in bm.verts if abs(v.co.x - cx) < span * 0.004]
print('ON-MIDLINE verts (within 0.4%% of span) = %d' % len(onmid))
bm.free()
