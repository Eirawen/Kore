# Build a POSE SANDBOX .blend for Khaled to pose in the Blender GUI.
# Wristed rig, staged first-person, sword seated in the fist, FP camera active.
# Open the result, hit Numpad 0, and pose. Saved so no scene setup is needed.
#
#   blender --background cgtrader_hand_wristed.blend --python build_pose_sandbox.py
import bpy, math
from mathutils import Vector, Euler, Matrix, Quaternion

OUT_BLEND = r'\\wsl.localhost\Ubuntu\home\khaled\Kore\pose_sandbox.blend'
CHAINS = {
    'thumb':  ['Bone.001', 'Bone.002', 'Bone.003'],
    'index':  ['Bone.004', 'Bone.017', 'Bone.018', 'Bone.019'],
    'middle': ['Bone.005', 'Bone.014', 'Bone.015', 'Bone.016'],
    'ring':   ['Bone.006', 'Bone.011', 'Bone.012', 'Bone.013'],
    'pinky':  ['Bone.007', 'Bone.008', 'Bone.009', 'Bone.010'],
}
METACARPAL_FRACTION = 0.15
POSE_GRIP = {'f': [75, 85, 58], 'thumb': [40, 50, 28]}
HAND_SCALE, HAND_X = 3.118, 2.05
TILT_BACK, TIP_INWARD, ROLL_INWARD = -14.0, 9.0, 8.0
MATTE_COLOR, MATTE_ROUGH = (0.62, 0.55, 0.50, 1.0), 0.75
WORLD_COLOR = (0.12, 0.13, 0.16, 1.0)
RIGHT_ARM, RIGHT_MESH = 'Armature.001', 'Sphere.001'
LEFT_ARM,  LEFT_MESH  = 'Armature.003', 'Sphere.002'
KEEP = {RIGHT_ARM, LEFT_ARM, RIGHT_MESH, LEFT_MESH}
SWORD_GLB = r'C:\Users\kmessai\Downloads\Silverlight.glb'
SWORD_SCALE = 2.8
SWORD_LOC = (0.0, -0.15, 0.55)   # a STARTING seat — Khaled fixes it by eye
SWORD_ROT = (0, 0, 0)


def look_at(loc, target):
    return (target - loc).to_track_quat('-Z', 'Y').to_euler()


def strip_scene():
    for obj in list(bpy.data.objects):
        if obj.name not in KEEP:
            bpy.data.objects.remove(obj, do_unlink=True)
    for _ in range(3):
        bpy.ops.outliner.orphans_purge(do_recursive=True)


def stage_hands():
    right, left = bpy.data.objects[RIGHT_ARM], bpy.data.objects[LEFT_ARM]
    tb, ti, ri = (math.radians(a) for a in (TILT_BACK, TIP_INWARD, ROLL_INWARD))
    right.location = (HAND_X, 0, 0)
    right.rotation_euler = Euler((tb, ti, -ri), 'XYZ')
    right.scale = (-HAND_SCALE, HAND_SCALE, HAND_SCALE)
    left.location = (-HAND_X - 0.3, -0.6, -0.8)
    left.rotation_euler = Euler((tb, -ti, ri), 'XYZ')
    left.scale = (HAND_SCALE, HAND_SCALE, HAND_SCALE)
    bpy.context.view_layer.update()
    for name in (RIGHT_MESH, LEFT_MESH):
        m = bpy.data.objects[name]
        if m.matrix_world.determinant() < 0:
            import bmesh
            bm = bmesh.new(); bm.from_mesh(m.data)
            for f in bm.faces:
                f.normal_flip()
            bm.to_mesh(m.data); bm.free(); m.data.update()


def apply_matte(objs):
    mat = bpy.data.materials.new('FP_Matte'); mat.use_nodes = True
    b = mat.node_tree.nodes.get('Principled BSDF')
    b.inputs['Base Color'].default_value = MATTE_COLOR
    b.inputs['Roughness'].default_value = MATTE_ROUGH
    for o in objs:
        o.data.materials.clear(); o.data.materials.append(mat)


def setup_world_cam():
    scene = bpy.context.scene
    world = bpy.data.worlds.new('FP_World'); world.use_nodes = True
    bg = world.node_tree.nodes.get('Background')
    bg.inputs['Color'].default_value = WORLD_COLOR
    bg.inputs['Strength'].default_value = 1.0
    scene.world = world

    def sun(name, loc, energy, color):
        d = bpy.data.lights.new(name, 'SUN')
        d.energy = energy; d.color = color; d.angle = math.radians(6)
        o = bpy.data.objects.new(name, d); o.location = loc
        o.rotation_euler = look_at(Vector(loc), Vector((0, 0, 2.5)))
        scene.collection.objects.link(o)
    sun('FP_Key', (-6, -8, 10), 2.0, (1.0, 0.97, 0.92))
    sun('FP_Fill', (7, -6, 2), 0.8, (0.85, 0.90, 1.0))

    fp = bpy.data.cameras.new('FP_Cam'); fp.lens = 30
    fpo = bpy.data.objects.new('FP_Cam', fp); scene.collection.objects.link(fpo)
    fpo.location = Vector((0, -8.2, 4.6))
    fpo.rotation_euler = look_at(fpo.location, Vector((0, 0.5, 3.4)))
    scene.camera = fpo
    try:
        scene.render.engine = 'BLENDER_EEVEE'
    except TypeError:
        scene.render.engine = 'BLENDER_EEVEE_NEXT'


def apply_pose(arm, pose):
    for pb in arm.pose.bones:
        pb.rotation_mode = 'QUATERNION'
        pb.rotation_quaternion = (1, 0, 0, 0)
    for finger, chain in CHAINS.items():
        angles = pose.get(finger, pose.get('f'))
        if finger == 'thumb':
            phalanges = chain
        else:
            arm.pose.bones[chain[0]].rotation_quaternion = Quaternion(
                (1, 0, 0), math.radians(angles[0] * METACARPAL_FRACTION))
            phalanges = chain[1:]
        for name, deg in zip(phalanges, angles):
            arm.pose.bones[name].rotation_quaternion = Quaternion(
                (1, 0, 0), math.radians(deg))


def import_sword(right):
    pre = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=SWORD_GLB)
    new = [o for o in bpy.data.objects if o not in pre]
    sword = [o for o in new if o.type == 'MESH'][0]
    for o in new:
        if o is not sword:
            bpy.data.objects.remove(o, do_unlink=True)
    sword.name = 'Sword'
    sword.parent = right
    sword.parent_type = 'BONE'
    sword.parent_bone = 'hand'
    sword.matrix_parent_inverse.identity()
    bpy.context.view_layer.update()
    hand = right.pose.bones['hand']
    frame = hand.matrix @ Matrix.Translation((0, hand.bone.length, 0))
    seat = (Matrix.Translation(SWORD_LOC) @
            Euler([math.radians(a) for a in SWORD_ROT], 'XYZ').to_matrix().to_4x4() @
            Matrix.Diagonal((SWORD_SCALE,) * 3).to_4x4())
    sword.matrix_basis = frame.inverted() @ seat
    bpy.context.view_layer.update()
    if sword.matrix_world.determinant() < 0:
        import bmesh
        bm = bmesh.new(); bm.from_mesh(sword.data)
        for f in bm.faces:
            f.normal_flip()
        bm.to_mesh(sword.data); bm.free(); sword.data.update()


def main():
    right, left = bpy.data.objects[RIGHT_ARM], bpy.data.objects[LEFT_ARM]
    strip_scene(); stage_hands()
    apply_matte([bpy.data.objects[RIGHT_MESH], bpy.data.objects[LEFT_MESH]])
    setup_world_cam()
    apply_pose(right, POSE_GRIP)
    apply_pose(left, {'f': [20, 30, 15], 'thumb': [15, 20, 10]})
    import_sword(right)
    bpy.context.scene.frame_start = 1
    bpy.context.scene.frame_end = 120
    bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)
    print('saved sandbox to', OUT_BLEND)


main()
