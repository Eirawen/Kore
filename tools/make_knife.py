"""
Placeholder throwing knife — "a cone on a stick" — exported as a clean,
standalone, game-ready GLB.

Run: blender.exe --background --python make_knife.py
Output: /home/khaled/Kore/assets/test_knife.glb  (via \\wsl.localhost UNC)

Conventions:
  - blade axis +Z, tip at z=+0.13
  - origin at the blade/handle junction (z=0), centered on the axis
  - real-world scale in meters: 26 cm total (13 cm cone blade, 12 cm
    handle + 1 cm pommel), blade base r=1.5 cm, handle r=1.0 cm
  - two materials: Knife_Steel (metallic) on the blade, Knife_Grip
    (dark leather-brown) on the handle/pommel
  - single mesh object 'TestKnife', no armature, no extra nodes
"""
import bpy
import math

OUT = r'\\wsl.localhost\Ubuntu\home\khaled\Kore\assets\test_knife.glb'

bpy.ops.wm.read_factory_settings(use_empty=True)

# blade: filled cone, base at z=0, tip at +0.13
bpy.ops.mesh.primitive_cone_add(vertices=24, radius1=0.015, radius2=0.0,
                                depth=0.13, location=(0, 0, 0.065))
blade = bpy.context.object
# handle: thin cylinder from z=-0.12 to 0
bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=0.010, depth=0.12,
                                    location=(0, 0, -0.06))
handle = bpy.context.object
# pommel: small cap sphere at the butt
bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=8, radius=0.013,
                                     location=(0, 0, -0.125))
pommel = bpy.context.object

steel = bpy.data.materials.new('Knife_Steel')
steel.use_nodes = True
b = steel.node_tree.nodes['Principled BSDF']
b.inputs['Base Color'].default_value = (0.75, 0.77, 0.80, 1.0)
b.inputs['Metallic'].default_value = 1.0
b.inputs['Roughness'].default_value = 0.35

grip = bpy.data.materials.new('Knife_Grip')
grip.use_nodes = True
b = grip.node_tree.nodes['Principled BSDF']
b.inputs['Base Color'].default_value = (0.16, 0.09, 0.05, 1.0)
b.inputs['Roughness'].default_value = 0.8

blade.data.materials.append(steel)
for o in (handle, pommel):
    o.data.materials.append(grip)

# join into one mesh, origin stays at the junction (world origin)
bpy.ops.object.select_all(action='DESELECT')
for o in (blade, handle, pommel):
    o.select_set(True)
bpy.context.view_layer.objects.active = blade
bpy.ops.object.join()
knife = bpy.context.object
knife.name = 'TestKnife'
bpy.ops.object.shade_smooth()
# origin at the blade/handle junction (world 0,0,0), no node translation
bpy.context.scene.cursor.location = (0.0, 0.0, 0.0)
bpy.ops.object.origin_set(type='ORIGIN_CURSOR')

bpy.ops.export_scene.gltf(filepath=OUT, export_format='GLB',
                          use_selection=True, export_yup=True)
print('exported', OUT)
