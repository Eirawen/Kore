# Seat the Silverlight rapier IN-LINE in the wristed rig's fist — the natural
# point-control thrust grip (Khaled's real-rapier reference):
#   thumb up the grip toward the blade, fingers wrapped, guard-shell forward,
#   pommel at the heel of the palm, blade IN-LINE with the forearm at a
#   NEUTRAL wrist.
#
# Fixes pose_thrust.py's buggy SWORD_LOC=(0,-0.15,0.55) which put the grip
# center at armature z=-1.69 — skewering the forearm. Correct seat: grip
# center in the PROBED fist void (gotcha #29), origin = void - S*(grip
# center offset along blade).
#
# Sword local anatomy (probe_sword.py, blade = +Z):
#   tip +0.95 | blade .. -0.35 | guard shell -0.4..-0.7 | grip -0.7..-0.9
#   (r~0.035) | pommel -0.9..-0.96.  At SWORD_SCALE the grip center (z=-0.8)
#   sits GRIP_DROP = 0.8*SCALE below the sword origin.
#
# Also probes (numeric, no render): posed finger joints in armature-local
# space, and the hand bone's local DOF signs (which X sign = palmar flexion,
# which Z sign = ulnar deviation) — feeds the Task-2 constraint clamps.
#
#   blender --background cgtrader_hand_wristed.blend --python seat_grip.py --
import bpy, math
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
# Rapier point-control grip: graded curl (pinky tightest at the pommel end,
# index loosest at the guard), thumb NEARLY STRAIGHT running up the grip.
POSE_RAPIER = {
    'index':  [58, 72, 42],
    'middle': [68, 82, 52],
    'ring':   [78, 88, 58],
    'pinky':  [84, 94, 62],
    'thumb':  [20, 22, 14],
}
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
GRIP_CENTER_Z = -0.80                 # sword-local z of the grip center
FIST_VOID = Vector((0.0, -0.22, 1.37))  # armature-local (gotcha #29)
# In-line seat: blade along armature +Z (forearm axis) at neutral wrist.
# rz spins the sword about its own blade axis to face the guard shell forward.
SWORD_RZ = 90.0    # spin about the blade axis: knuckle-bow over the fingers
# Guard-cage bottom is sword-local z=-0.68; seat it just above the index
# finger's top (armature z~1.55) so the fist fills the grip section and the
# pommel lands at the heel of the palm.
SWORD_LOC = (-0.06, FIST_VOID.y, 1.55 + 0.68 * SWORD_SCALE)
RZ_SWEEP = [0, 90, 180, 270]          # orientation probe for the knuckle-bow


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
    cam_data = bpy.data.cameras.new('GripCam'); cam_data.lens = 50.0
    cam = bpy.data.objects.new('GripCam', cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam
    return cam


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


def probe_joints(right):
    """Posed finger joints + hand bone frame, armature-local space."""
    deps = bpy.context.evaluated_depsgraph_get()
    ev = right.evaluated_get(deps)
    for finger, chain in CHAINS.items():
        pts = []
        for bn in chain:
            pts.append('(%5.2f,%5.2f,%5.2f)' % tuple(ev.pose.bones[bn].head))
        pts.append('tip(%5.2f,%5.2f,%5.2f)'
                   % tuple(ev.pose.bones[chain[-1]].tail))
        print('JOINT %-6s %s' % (finger, ' '.join(pts)))
    hb = ev.pose.bones['hand']
    print('JOINT hand head(%5.2f,%5.2f,%5.2f) tail(%5.2f,%5.2f,%5.2f)'
          % (tuple(hb.head) + tuple(hb.tail)))


def probe_dof_signs(right):
    """Which bone-local rotation sign is palmar flexion / ulnar deviation?
    Armature-local: palm = -Y, thumb side = sign of thumb-tip X."""
    pb = right.pose.bones['hand']
    tip_bone = CHAINS['middle'][-1]

    def tip_after(q):
        pb.rotation_quaternion = q
        bpy.context.view_layer.update()
        deps = bpy.context.evaluated_depsgraph_get()
        ev = right.evaluated_get(deps)
        t = Vector(ev.pose.bones[tip_bone].tail)
        return t
    base = tip_after(Quaternion())
    flex = tip_after(Quaternion((1, 0, 0), math.radians(40)))
    dev = tip_after(Quaternion((0, 0, 1), math.radians(30)))
    pb.rotation_quaternion = Quaternion()
    bpy.context.view_layer.update()
    deps = bpy.context.evaluated_depsgraph_get()
    ev = right.evaluated_get(deps)
    thumb_x = ev.pose.bones[CHAINS['thumb'][-1]].tail.x
    print('DOF base tip (%.3f,%.3f,%.3f)  thumb tip x=%.3f' %
          (base.x, base.y, base.z, thumb_x))
    print('DOF +X40 -> tip dY=%+.3f  (palmar flexion if dY<0, palm=-Y)'
          % (flex.y - base.y))
    print('DOF +Z30 -> tip dX=%+.3f  (radial if toward thumb x sign %+.0f)'
          % (dev.x - base.x, math.copysign(1, thumb_x)))


def import_sword(right):
    pre = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=SWORD_GLB)
    new = [o for o in bpy.data.objects if o not in pre]
    sword = [o for o in new if o.type == 'MESH'][0]
    for o in new:
        if o is not sword:
            bpy.data.objects.remove(o, do_unlink=True)
    sword.parent = right
    sword.parent_type = 'BONE'
    sword.parent_bone = 'hand'
    sword.matrix_parent_inverse.identity()
    bpy.context.view_layer.update()
    seat_sword(right, sword, SWORD_RZ)
    if sword.matrix_world.determinant() < 0:
        import bmesh
        bm = bmesh.new(); bm.from_mesh(sword.data)
        for f in bm.faces:
            f.normal_flip()
        bm.to_mesh(sword.data); bm.free(); sword.data.update()
    return sword


def seat_sword(right, sword, rz):
    hand = right.pose.bones['hand']
    bone_tail_frame = hand.matrix @ Matrix.Translation((0, hand.bone.length, 0))
    seat = (Matrix.Translation(SWORD_LOC) @
            Euler((0, 0, math.radians(rz)), 'XYZ').to_matrix().to_4x4() @
            Matrix.Diagonal((SWORD_SCALE,) * 3).to_4x4())
    sword.matrix_basis = bone_tail_frame.inverted() @ seat
    bpy.context.view_layer.update()


def render(name, cam, loc, target):
    cam.location = loc
    cam.rotation_euler = look_at(Vector(loc), Vector(target))
    bpy.context.scene.render.filepath = OUT_DIR + '\\grip_%s.png' % name
    bpy.ops.render.render(write_still=True)
    print('rendered', name)


def main():
    right, left = bpy.data.objects[RIGHT_ARM], bpy.data.objects[LEFT_ARM]
    assert 'hand' in right.data.bones, 'need the WRISTED rig'
    strip_scene(); stage_hands()
    apply_matte([bpy.data.objects[RIGHT_MESH], bpy.data.objects[LEFT_MESH]])
    cam = setup_world()
    apply_pose(right, POSE_RAPIER)
    apply_pose(left, POSE_RAPIER)
    bpy.context.view_layer.update()
    probe_joints(right)
    probe_dof_signs(right)
    sword = import_sword(right)
    left.location = (-HAND_X - 0.5, -0.9, -1.2)   # park the left hand low/back

    fist = right.matrix_world @ FIST_VOID
    print('FIST world (%.2f,%.2f,%.2f)' % tuple(fist))
    seat_sword(right, sword, SWORD_RZ)
    # close crops: FP-behind (player view), outside side, inboard 3/4 front
    render('fp', cam, fist + Vector((0.2, -4.6, 1.6)), fist + Vector((0, 0.6, 0.4)))
    render('side', cam, fist + Vector((5.2, -1.6, 0.9)), fist + Vector((0, 0, 0.5)))
    render('front34', cam, fist + Vector((-3.4, -3.6, 0.6)),
           fist + Vector((0, 0, 0.5)))


main()
