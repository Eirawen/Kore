# Pose a real THRUST on the wristed rig (cgtrader_hand_wristed.blend).
#
# Khaled's correction: a thrust rotates the blade in the SAGITTAL (vertical
# fore-aft) plane, from up/ready -> pointing DOWNRANGE at the target, driven
# mostly by the ARM extending forward with the wrist setting final alignment.
# NOT a frontal-plane across->up sweep (that's a salute).
#
# So instead of point_in_line_quat (aims blade at the forearm axis -> up), we
# aim the blade at a DOWNRANGE world direction (+Y, into the FP screen) and add
# arm extension. Renders 3 key poses (chamber -> drive -> strike) from BOTH a
# first-person camera (blade should foreshorten INTO the screen) and a side
# camera (should read the up->forward sagittal rotation). Pose-first policy.
#
#   blender --background cgtrader_hand_wristed.blend --python pose_thrust.py --
import bpy, sys, math
from mathutils import Vector, Euler, Matrix, Quaternion

OUT_DIR = r'C:\tmp'
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
RES_X, RES_Y = 960, 720
RIGHT_ARM, RIGHT_MESH = 'Armature.001', 'Sphere.001'
LEFT_ARM,  LEFT_MESH  = 'Armature.003', 'Sphere.002'
KEEP = {RIGHT_ARM, LEFT_ARM, RIGHT_MESH, LEFT_MESH}
SWORD_GLB = r'C:\Users\kmessai\Downloads\Silverlight.glb'
SWORD_SCALE = 2.8
SWORD_LOC = (-0.73 * SWORD_SCALE, -0.22, 1.37)
SWORD_ROT = (0, -90, 0)

# Downrange aim for the thrust: into the FP screen (+Y), a hair up so the point
# doesn't drive into the floor.
AIM_WORLD = Vector((0, 1, 0.12)).normalized()

# Thrust key poses: (label, object-location, wrist frac, ARM-PITCH delta deg).
# The pitch is the piece the first pass missed: the whole forearm must pitch
# FORWARD (downrange) so the point drives level at the target instead of
# climbing. TILT_BACK is negative = tilts toward camera, so POSITIVE pitch
# tilts the forearm forward/downrange. Wrist (thrust_quat) sets final aim on
# top of the pitched arm; the reach is mostly arm, the wrist just finishes it.
THRUST_KEYS = [
    ('1_chamber', (HAND_X + 0.15, -1.05, -0.35), 0.0,  -10.0),
    ('2_drive',   (HAND_X - 0.20,  0.35, -0.15), 0.55,  14.0),
    ('3_strike',  (HAND_X - 0.50,  1.65, -0.25), 1.0,   32.0),
]


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
    left.location = (-HAND_X, 0, 0)
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


def setup_world():
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
    try:
        scene.render.engine = 'BLENDER_EEVEE'
    except TypeError:
        scene.render.engine = 'BLENDER_EEVEE_NEXT'
    scene.render.resolution_x, scene.render.resolution_y = RES_X, RES_Y
    scene.render.image_settings.file_format = 'PNG'

    # First-person camera: looks downrange (+Y). A blade thrust to +Y drives
    # AWAY from it and foreshortens -- the visual proof of a real thrust.
    fp = bpy.data.cameras.new('FP'); fp.lens = 30
    fpo = bpy.data.objects.new('FP', fp); scene.collection.objects.link(fpo)
    fpo.location = Vector((0, -8.2, 4.6))
    fpo.rotation_euler = look_at(fpo.location, Vector((0, 0.5, 3.4)))
    # Side camera: looks across (+X) so the up->forward sagittal rotation reads.
    sd = bpy.data.cameras.new('SIDE'); sd.lens = 50
    sdo = bpy.data.objects.new('SIDE', sd); scene.collection.objects.link(sdo)
    sdo.location = Vector((11, 0.2, 3.2))
    sdo.rotation_euler = look_at(sdo.location, Vector((HAND_X - 0.2, 0.3, 3.0)))
    return fpo, sdo


def clear_pose(arm):
    for pb in arm.pose.bones:
        pb.rotation_mode = 'QUATERNION'
        pb.rotation_quaternion = (1, 0, 0, 0)
        pb.location = (0, 0, 0); pb.scale = (1, 1, 1)


def apply_pose(arm, pose):
    clear_pose(arm)
    for finger, chain in CHAINS.items():
        angles = pose.get(finger, pose.get('f'))
        if angles is None:
            continue
        if finger == 'thumb':
            phalanges = chain
        else:
            m = arm.pose.bones[chain[0]]
            m.rotation_quaternion = Quaternion(
                (1, 0, 0), math.radians(angles[0] * METACARPAL_FRACTION))
            phalanges = chain[1:]
        for name, deg in zip(phalanges, angles):
            arm.pose.bones[name].rotation_quaternion = Quaternion(
                (1, 0, 0), math.radians(deg))


# Roll about the blade axis to un-reverse the grip. Aiming the blade direction
# leaves the roll free, so the shortest-arc alignment lands in a reverse (ice-
# pick) grip. This rolls the hand back to a natural thumb-forward thrust grip.
GRIP_ROLL_DEG = 0.0   # 180 overshoots into an extreme wrist crank; the real
                      # fix is re-seating a natural forward grip, not rolling.


def thrust_quat(arm, frac):
    """Bone-local wrist quaternion that rotates the blade (rest = armature-local
    -X) to point DOWNRANGE (AIM_WORLD, into the FP screen), plus a roll about
    the blade axis so the grip stays natural (not reversed). Slerped by frac."""
    d_blade = Vector((-1, 0, 0))
    R = arm.matrix_world.to_3x3()
    d_aim = (R.inverted() @ AIM_WORLD).normalized()      # downrange in arm-local
    Q = d_blade.rotation_difference(d_aim)               # armature space
    Q_roll = Quaternion(d_aim, math.radians(GRIP_ROLL_DEG))
    Q_total = Q_roll @ Q                                 # roll about the blade
    B = arm.data.bones['hand'].matrix_local.to_3x3()
    Rm = B.inverted() @ Q_total.to_matrix() @ B          # into bone local
    return Quaternion().slerp(Rm.to_quaternion(), frac)


def set_hand(arm, q):
    pb = arm.pose.bones['hand']
    pb.rotation_mode = 'QUATERNION'
    pb.rotation_quaternion = q
    bpy.context.view_layer.update()


def import_sword(right):
    pre = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=SWORD_GLB)
    new = [o for o in bpy.data.objects if o not in pre]
    meshes = [o for o in new if o.type == 'MESH']
    sword = meshes[0]
    for o in new:
        if o is not sword:
            bpy.data.objects.remove(o, do_unlink=True)
    sword.parent = right
    sword.parent_type = 'BONE'
    sword.parent_bone = 'hand'
    sword.matrix_parent_inverse.identity()
    bpy.context.view_layer.update()
    hand = right.pose.bones['hand']
    bone_tail_frame = hand.matrix @ Matrix.Translation((0, hand.bone.length, 0))
    seat = (Matrix.Translation(SWORD_LOC) @
            Euler([math.radians(a) for a in SWORD_ROT], 'XYZ').to_matrix().to_4x4() @
            Matrix.Diagonal((SWORD_SCALE,) * 3).to_4x4())
    sword.matrix_basis = bone_tail_frame.inverted() @ seat
    bpy.context.view_layer.update()
    if sword.matrix_world.determinant() < 0:
        import bmesh
        bm = bmesh.new(); bm.from_mesh(sword.data)
        for f in bm.faces:
            f.normal_flip()
        bm.to_mesh(sword.data); bm.free(); sword.data.update()
    return sword


def render(path, cam):
    bpy.context.scene.camera = cam
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print('rendered', path)


def main():
    right, left = bpy.data.objects[RIGHT_ARM], bpy.data.objects[LEFT_ARM]
    assert 'hand' in right.data.bones, 'need the WRISTED rig'
    strip_scene(); stage_hands()
    apply_matte([bpy.data.objects[RIGHT_MESH], bpy.data.objects[LEFT_MESH]])
    fp, side = setup_world()
    for arm in (right, left):
        apply_pose(arm, POSE_GRIP)
    bpy.context.view_layer.update()
    import_sword(right)
    # left arm rests low/back out of the way
    left.location = (-HAND_X - 0.3, -0.6, -0.8)
    for label, loc, frac, pitch in THRUST_KEYS:
        right.location = loc
        right.rotation_euler = Euler((math.radians(TILT_BACK + pitch),
                                      math.radians(TIP_INWARD),
                                      math.radians(-ROLL_INWARD)), 'XYZ')
        bpy.context.view_layer.update()   # refresh matrix_world BEFORE aiming
        set_hand(right, thrust_quat(right, frac))
        bpy.context.view_layer.update()
        render(OUT_DIR + '\\thrust_%s_fp.png' % label, fp)
        render(OUT_DIR + '\\thrust_%s_side.png' % label, side)


main()
