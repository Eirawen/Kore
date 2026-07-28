"""Check shading + subdivide her for liquid-grade surface. Reports whether
normals were flat (which alone would explain a faceted read)."""
import bpy
for o in list(bpy.data.objects): bpy.data.objects.remove(o, do_unlink=True)
bpy.ops.import_scene.gltf(filepath=r'\\wsl.localhost\Ubuntu\home\khaled\Kore\water_elemental.glb')
o=max([x for x in bpy.data.objects if x.type=='MESH'],key=lambda x:len(x.data.vertices))
bpy.context.view_layer.objects.active=o
me=o.data
flat=sum(1 for p in me.polygons if not p.use_smooth)
print('SHADING: %d/%d polys FLAT (%.0f%%)' % (flat, len(me.polygons), 100*flat/max(len(me.polygons),1)))
print('verts before: %d  faces: %d' % (len(me.vertices), len(me.polygons)))
bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.mesh.remove_doubles(threshold=1e-5); bpy.ops.object.mode_set(mode='OBJECT')
# smooth shading first — this alone may be the whole "faceted" read
bpy.ops.object.shade_smooth()
# simple subdivision: more verts, same silhouette (Catmull-Clark would
# round off the ribbon edges that give her character)
m=o.modifiers.new('Subsurf','SUBSURF'); m.subdivision_type='SIMPLE'; m.levels=m.render_levels=2
bpy.ops.object.modifier_apply(modifier='Subsurf')
print('verts after : %d  faces: %d' % (len(o.data.vertices), len(o.data.polygons)))
bpy.ops.object.select_all(action='DESELECT'); o.select_set(True)
bpy.ops.export_scene.gltf(
    filepath=r'\\wsl.localhost\Ubuntu\home\khaled\Kore\water_elemental_sub.glb',
    export_format='GLB', use_selection=True, export_apply=True)
print('EXPORTED water_elemental_sub.glb')
