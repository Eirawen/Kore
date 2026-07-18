"""
Chirality probe: stage the FP rest pose exactly as animate_casts.py does,
render one still, and print the world-space thumb/pinky/finger directions of
both hands so we can say definitively which way each thumb points.

Run:
  blender.exe --background cgtrader_hand.blend --python probe_chirality.py
Output: C:\tmp\chirality_rest.png + console vectors.
"""
import bpy
import math
from mathutils import Vector, Euler

HAND_SCALE = 3.118
KEEP = {'Armature.001', 'Armature.003', 'Sphere.001', 'Sphere.002'}
RIGHT_ARM, RIGHT_MESH = 'Armature.001', 'Sphere.001'
LEFT_ARM,  LEFT_MESH  = 'Armature.003', 'Sphere.002'
R_REST_LOC, R_REST_ROT = (2.05, 0.0, -0.7), (14, 9, 172)
L_REST_LOC, L_REST_ROT = (-2.05, 0.0, -0.7), (14, -9, -172)

CHAINS = {
    'thumb':  ['Bone.001', 'Bone.002', 'Bone.003'],
    'index':  ['Bone.004', 'Bone.017', 'Bone.018', 'Bone.019'],
    'pinky':  ['Bone.007', 'Bone.008', 'Bone.009', 'Bone.010'],
}


def look_at_rotation(loc, target):
    return (target - loc).to_track_quat('-Z', 'Y').to_euler()


def main():
    for obj in list(bpy.data.objects):
        if obj.name not in KEEP:
            bpy.data.objects.remove(obj, do_unlink=True)

    right, left = bpy.data.objects[RIGHT_ARM], bpy.data.objects[LEFT_ARM]
    for obj in (right, left):
        obj.rotation_mode = 'XYZ'
    # chirality-fixed staging: keep loc, negate euler Y/Z, toggle mirror
    def flip(rot):
        return (rot[0], -rot[1], -rot[2])
    right.location = R_REST_LOC
    right.scale = (-HAND_SCALE, HAND_SCALE, HAND_SCALE)
    right.rotation_euler = Euler([math.radians(a) for a in flip(R_REST_ROT)], 'XYZ')
    left.location = L_REST_LOC
    left.scale = (HAND_SCALE,) * 3
    left.rotation_euler = Euler([math.radians(a) for a in flip(L_REST_ROT)], 'XYZ')

    bpy.context.view_layer.update()
    for mesh_name in (RIGHT_MESH, LEFT_MESH):
        m = bpy.data.objects[mesh_name]
        if m.matrix_world.determinant() < 0:
            import bmesh
            bm = bmesh.new()
            bm.from_mesh(m.data)
            for f in bm.faces:
                f.normal_flip()
            bm.to_mesh(m.data)
            bm.free()
            m.data.update()

    # neutral pose
    for arm in (right, left):
        for pb in arm.pose.bones:
            pb.rotation_mode = 'XYZ'
            pb.rotation_euler = (0, 0, 0)
            pb.location = (0, 0, 0)

    bpy.context.view_layer.update()

    # ── probe: print world positions of key bones for each hand ──
    for label, arm in (('RIGHT-SLOT (screen +X, unmirrored)', right),
                       ('LEFT-SLOT (screen -X, mirrored)', left)):
        print('==== %s ====' % label)
        mw = arm.matrix_world
        for finger, chain in CHAINS.items():
            head = mw @ arm.pose.bones[chain[0]].head
            tip = mw @ arm.pose.bones[chain[-1]].tail
            print('  %-6s base=(%6.2f,%6.2f,%6.2f) tip=(%6.2f,%6.2f,%6.2f)'
                  % (finger, head.x, head.y, head.z, tip.x, tip.y, tip.z))
        # wrist root bone(s)
        roots = [b for b in arm.pose.bones if b.parent is None]
        for r in roots:
            h = mw @ r.head
            t = mw @ r.tail
            print('  root %-10s head=(%6.2f,%6.2f,%6.2f) tail=(%6.2f,%6.2f,%6.2f)'
                  % (r.name, h.x, h.y, h.z, t.x, t.y, t.z))

    # verdict helper: thumb tip x minus hand-center x
    for label, arm, sgn in (('right-slot', right, 1), ('left-slot', left, -1)):
        mw = arm.matrix_world
        thumb = (mw @ arm.pose.bones['Bone.003'].tail).x
        pinky = (mw @ arm.pose.bones['Bone.010'].tail).x
        center = arm.location[0]
        rel = thumb - center
        inboard = (rel * sgn) < 0   # for +X hand, inboard = thumb at smaller x
        print('VERDICT %s: thumb.x=%.2f pinky.x=%.2f center=%.2f -> thumb %s'
              % (label, thumb, pinky, center,
                 'INBOARD' if inboard else 'OUTBOARD'))

    # ── render a still for the eyeball check ──
    scene = bpy.context.scene
    mat = bpy.data.materials.new('FP_Matte')
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get('Principled BSDF')
    bsdf.inputs['Base Color'].default_value = (0.62, 0.55, 0.50, 1.0)
    bsdf.inputs['Roughness'].default_value = 0.75
    for name in (RIGHT_MESH, LEFT_MESH):
        o = bpy.data.objects[name]
        o.data.materials.clear()
        o.data.materials.append(mat)

    cam_data = bpy.data.cameras.new('FP_Camera')
    cam_data.lens = 36.0
    cam = bpy.data.objects.new('FP_Camera', cam_data)
    cam.location = Vector((0.0, -8.2, 4.6))
    cam.rotation_euler = look_at_rotation(cam.location, Vector((0.0, 0.0, 3.3)))
    scene.collection.objects.link(cam)
    scene.camera = cam

    def add_sun(name, loc, energy, color=(1, 1, 1)):
        data = bpy.data.lights.new(name, 'SUN')
        data.energy, data.color = energy, color
        data.angle = math.radians(6)
        obj = bpy.data.objects.new(name, data)
        obj.location = loc
        obj.rotation_euler = look_at_rotation(Vector(loc), Vector((0, 0, 2.5)))
        scene.collection.objects.link(obj)
    add_sun('FP_Key', (-6, -8, 10), 2.0, (1.0, 0.97, 0.92))
    add_sun('FP_Fill', (7, -6, 2), 0.8, (0.85, 0.90, 1.0))

    world = bpy.data.worlds.new('FP_World')
    world.use_nodes = True
    bg = world.node_tree.nodes.get('Background')
    bg.inputs['Color'].default_value = (0.12, 0.13, 0.16, 1.0)
    scene.world = world
    try:
        scene.render.engine = 'BLENDER_EEVEE'
    except TypeError:
        scene.render.engine = 'BLENDER_EEVEE_NEXT'
    scene.render.resolution_x, scene.render.resolution_y = 960, 720
    scene.render.image_settings.file_format = 'PNG'
    scene.render.filepath = r'C:\tmp\chirality_rest.png'
    bpy.ops.render.render(write_still=True)
    print('rendered C:\\tmp\\chirality_rest.png')


main()
