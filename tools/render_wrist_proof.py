# Proof renders for the wrist surgery. Works on BOTH the old rig (root 'Bone')
# and the new one (forearm+hand) so the same shots prove rest parity.
#
#   blender --background <blend> --python render_wrist_proof.py -- <tag>
#
# tag ('old' / 'new') prefixes the output files C:\tmp\wp_<tag>_<shot>.png.
# Old rig renders only the rest shots; new rig adds anti-egg wrist tilts and
# the sword point-in-line sequence (sword parented to the 'hand' BONE).
# Staging/lights/matte mirror tools/render_hands_fp.py so grids stay consistent.
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
POSE_IDLE = {'f': [20, 30, 15], 'thumb': [15, 20, 10]}
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
SWORD_LOC = (-0.73 * SWORD_SCALE, -0.22, 1.37)   # armature-local seat
SWORD_ROT = (0, -90, 0)                          # blade (+Z) -> local -X


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
    # chirality-flipped staging (gotcha #26): screen-right = mirrored mesh
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
    mat = bpy.data.materials.new('FP_Matte')
    mat.use_nodes = True
    b = mat.node_tree.nodes.get('Principled BSDF')
    b.inputs['Base Color'].default_value = MATTE_COLOR
    b.inputs['Roughness'].default_value = MATTE_ROUGH
    for o in objs:
        o.data.materials.clear()
        o.data.materials.append(mat)


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
        o = bpy.data.objects.new(name, d)
        o.location = loc
        o.rotation_euler = look_at(Vector(loc), Vector((0, 0, 2.5)))
        scene.collection.objects.link(o)
    sun('FP_Key',  (-6, -8, 10), 2.0, (1.0, 0.97, 0.92))
    sun('FP_Fill', (7, -6, 2),   0.8, (0.85, 0.90, 1.0))

    cam_data = bpy.data.cameras.new('WristCam'); cam_data.lens = 50.0
    cam = bpy.data.objects.new('WristCam', cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam
    try:
        scene.render.engine = 'BLENDER_EEVEE'
    except TypeError:
        scene.render.engine = 'BLENDER_EEVEE_NEXT'
    scene.render.resolution_x, scene.render.resolution_y = RES_X, RES_Y
    scene.render.image_settings.file_format = 'PNG'
    return cam


def aim_wrist(cam, wrist_world, back=4.6, side=0.4, up=0.9, aim_up=0.55):
    """Tight framing on the wrist: camera off to camera-left, slightly high."""
    loc = wrist_world + Vector((side, -back, up))
    cam.location = loc
    cam.rotation_euler = look_at(loc, wrist_world + Vector((0, 0, aim_up)))


def clear_pose(arm):
    for pb in arm.pose.bones:
        pb.rotation_mode = 'QUATERNION'
        pb.rotation_quaternion = (1, 0, 0, 0)
        pb.location = (0, 0, 0)
        pb.scale = (1, 1, 1)


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


def set_hand_quat(arm, q):
    pb = arm.pose.bones['hand']
    pb.rotation_mode = 'QUATERNION'
    pb.rotation_quaternion = q
    bpy.context.view_layer.update()


def hand_local_quat_for(arm, axis_deg):
    """Pose quaternion rotating the hand about its own bone-local axis."""
    axis, deg = axis_deg
    return Quaternion(axis, math.radians(deg))


def point_in_line_quat(arm, frac=1.0):
    """Pose quaternion (bone local) aligning the blade (armature-local -X at
    rest) with the forearm downrange axis. frac slerps from identity."""
    d_blade = Vector((-1, 0, 0))
    fb = arm.data.bones['forearm']
    d_fore = (Vector(fb.tail_local) - Vector(fb.head_local)).normalized()
    Q = d_blade.rotation_difference(d_fore)          # armature space
    B = arm.data.bones['hand'].matrix_local.to_3x3()
    Rm = B.inverted() @ Q.to_matrix() @ B            # into bone local
    q = Rm.to_quaternion()
    return Quaternion().slerp(q, frac)


def import_sword(right):
    pre = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=SWORD_GLB)
    new = [o for o in bpy.data.objects if o not in pre]
    meshes = [o for o in new if o.type == 'MESH']
    sword = meshes[0]
    for o in new:
        if o is not sword:
            bpy.data.objects.remove(o, do_unlink=True)
    sword.parent = None
    # parent to the hand BONE (not the object)
    sword.parent = right
    sword.parent_type = 'BONE'
    sword.parent_bone = 'hand'
    sword.matrix_parent_inverse.identity()
    bpy.context.view_layer.update()
    # seat: desired ARMATURE-LOCAL matrix, expressed relative to the bone-tail
    # frame that BONE parenting uses (bone matrix advanced by its length).
    hand = right.pose.bones['hand']            # rest pose here => rest frame
    bone_tail_frame = (hand.matrix @
                       Matrix.Translation((0, hand.bone.length, 0)))
    seat = (Matrix.Translation(SWORD_LOC) @
            Euler([math.radians(a) for a in SWORD_ROT], 'XYZ').to_matrix().to_4x4() @
            Matrix.Diagonal((SWORD_SCALE,) * 3).to_4x4())
    local = bone_tail_frame.inverted() @ seat
    sword.matrix_basis = local
    # inherit mirror from parent (-S,S,S) => negative determinant: flip normals
    bpy.context.view_layer.update()
    if sword.matrix_world.determinant() < 0:
        import bmesh
        bm = bmesh.new(); bm.from_mesh(sword.data)
        for f in bm.faces:
            f.normal_flip()
        bm.to_mesh(sword.data); bm.free(); sword.data.update()
    return sword


def render(name, tag):
    path = OUT_DIR + '\\wp_%s_%s.png' % (tag, name)
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print('rendered', path)


def main():
    argv = sys.argv
    args = argv[argv.index('--') + 1:] if '--' in argv else []
    tag = args[0] if args else 'x'

    right = bpy.data.objects[RIGHT_ARM]
    left = bpy.data.objects[LEFT_ARM]
    is_new = 'hand' in right.data.bones

    strip_scene()
    stage_hands()
    apply_matte([bpy.data.objects[RIGHT_MESH], bpy.data.objects[LEFT_MESH]])
    cam = setup_world()

    root_name = 'forearm' if is_new else 'Bone'
    root = right.data.bones[root_name]
    split_local = Vector((0, 0.0351, 0.7855))     # wrist point (both rigs)
    wrist_world = right.matrix_world @ split_local
    print('wrist world:', tuple(round(v, 3) for v in wrist_world))

    # ---- rest shots (both rigs): idle curl, forearm+hand at identity ----
    for arm in (right, left):
        apply_pose(arm, POSE_IDLE)
    aim_wrist(cam, wrist_world)
    render('rest_tight', tag)
    # wider two-hand rest for parity context
    aim_wrist(cam, Vector((0, 0, wrist_world.z * 0.9)), back=7.5, side=0.0,
              up=1.6, aim_up=0.9)
    render('rest_wide', tag)

    if not is_new:
        return

    # ---- anti-egg: tilt the hand, forearm must stay put ----
    aim_wrist(cam, wrist_world)
    tilts = [('flex_neg40',  ((1, 0, 0), -40)),
             ('flex_pos40',  ((1, 0, 0),  40)),
             ('dev_neg30',   ((0, 0, 1), -30)),
             ('dev_pos30',   ((0, 0, 1),  30))]
    for name, ax in tilts:
        set_hand_quat(right, hand_local_quat_for(right, ax))
        render('tilt_' + name, tag)
    set_hand_quat(right, Quaternion())

    # ---- sword point-in-line ----
    for arm in (right, left):
        apply_pose(arm, POSE_GRIP)
    bpy.context.view_layer.update()
    import_sword(right)
    # wider framing: whole forearm + blade line must be visible
    aim_wrist(cam, wrist_world, back=13.0, side=1.0, up=2.2, aim_up=1.6)
    for name, frac in [('pil_000', 0.0), ('pil_050', 0.5), ('pil_100', 1.0)]:
        set_hand_quat(right, point_in_line_quat(right, frac))
        render(name, tag)
    # side view of the full point-in-line to read blade-forearm alignment
    loc = wrist_world + Vector((8.5, -7.0, 2.0))
    cam.location = loc
    cam.rotation_euler = look_at(loc, wrist_world + Vector((0, 0, 1.2)))
    render('pil_100_side', tag)


main()
