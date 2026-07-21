# Retarget Khaled's hand-authored grip (poses/khaled_grip_base.blend, extracted
# by extract_khaled_grip.py) onto the CONSTRAINED wristed rig
# (cgtrader_hand_wristed.blend: hand 2-DOF, forearm pronation-only).
#
# What carries over verbatim:
#   - every finger-chain pose-bone quaternion (his splay is intentional
#     side-sword technique — index deliberately around the guard)
#   - the Sword seat RELATIVE to the hand bone-tail frame (bone-parented;
#     matrix_parent_inverse verified identity in his file)
# What gets transformed:
#   - his hand (wrist) quat carried ~40.7 deg of axial twist about bone-Y,
#     illegal on the constrained rig. Decompose q = qs @ qt (twist qt about Y,
#     swing qs). Forearm roll takes the twist; the hand keeps the swing
#     CONJUGATED by the twist (qt^-1 @ qs @ qt) — exact because forearm/hand
#     rest Y axes are collinear (probed: 0.00 deg apart).
# What gets discarded (workspace junk):
#   - his object-level armature/sword-world transforms; restaged at the
#     standard chirality-fixed FP placement (render_hands_fp.py values)
#   - his forearm pose (-143.5 roll + 91.7 swing = gross arm aiming in the
#     unconstrained sandbox; the grip assembly is rigid under the hand bone,
#     so this cannot affect contact)
#
# Verifies fingertip->handle-axis radials (world) against his ground truth,
# forces hide_render=False (gotcha 14b — his file had Sphere.001 render-
# hidden), renders palm/FP/back proof stills, and writes the final legal
# channels to poses/grip_retargeted.json for the attack-key scripts.
#
#   blender --background cgtrader_hand_wristed.blend --python retarget_grip.py --
import bpy, json, math
from mathutils import Vector, Euler, Matrix, Quaternion

GRIP_JSON = r'\\wsl.localhost\Ubuntu\home\khaled\Kore\poses\khaled_grip_extract.json'
OUT_JSON = r'\\wsl.localhost\Ubuntu\home\khaled\Kore\poses\grip_retargeted.json'

# AMENDMENT (2026-07-21, approved by Khaled): his authored thumb TIP
# (Bone.003) came in folded ~170 deg about a skew axis — anatomically broken
# (a thumb DIP flexes ~80 deg max). Relax the TIP to a natural flexion;
# his thumb BASE + MID (Bone.001/002) stay verbatim, as do all other
# fingers. Applied here at the grip-baseline level so every sword clip
# inherits it.
THUMB_TIP_FLEX_DEG = 40.0

# reuse the standard FP staging (constants + defs only, main() stripped)
SRC = r'\\wsl.localhost\Ubuntu\home\khaled\Kore\tools\seat_grip.py'
_code = open(SRC).read()
exec(_code[:_code.rfind('def main')])

LEFT_PARK = (-HAND_X - 0.4, -0.35, -0.75)


def load_extract():
    with open(GRIP_JSON) as f:
        return json.load(f)


def apply_finger_pose(arm, bones):
    """His finger channels verbatim; wrist/forearm handled separately."""
    clear_pose(arm)
    for name, q in bones.items():
        if name in ('hand', 'forearm'):
            continue
        pb = arm.pose.bones[name]
        pb.rotation_mode = 'QUATERNION'
        pb.rotation_quaternion = Quaternion(q)


def redistribute_wrist(arm, q_hand):
    """Twist->forearm roll, conjugated swing->hand. Returns report dict."""
    q = Quaternion(q_hand)
    qt = Quaternion((q.w, 0.0, q.y, 0.0)).normalized()      # twist about bone Y
    qs = q @ qt.inverted()                                   # q = qs @ qt
    q_hand_new = qt.inverted() @ qs @ qt                     # exact remainder
    twist_deg = math.degrees(2 * math.atan2(q.y, q.w))
    fore = arm.pose.bones['forearm']
    hand = arm.pose.bones['hand']
    fore.rotation_mode = 'QUATERNION'
    fore.rotation_quaternion = Quaternion((0, 1, 0), math.radians(twist_deg))
    hand.rotation_mode = 'QUATERNION'
    hand.rotation_quaternion = q_hand_new
    eul = q_hand_new.to_euler('XYZ')
    return {
        'forearm_roll_deg': round(twist_deg, 2),
        'hand_flex_deg': round(math.degrees(eul.x), 2),
        'hand_dev_deg': round(math.degrees(eul.z), 2),
        'hand_residual_y_deg': round(math.degrees(eul.y), 2),
        'hand_quat': list(q_hand_new),
    }


def distal_rot_target(arm, q_hand):
    """His composed distal orientation (identity forearm + raw hand quat),
    read with constraints muted so the illegal twist isn't clamped."""
    cons = [c for b in ('hand', 'forearm') for c in arm.pose.bones[b].constraints]
    for c in cons:
        c.influence = 0.0
    arm.pose.bones['forearm'].rotation_quaternion = Quaternion()
    arm.pose.bones['hand'].rotation_quaternion = Quaternion(q_hand)
    bpy.context.view_layer.update()
    R = arm.pose.bones['hand'].matrix.to_3x3().copy()
    for c in cons:
        c.influence = 1.0
    bpy.context.view_layer.update()
    return R


def import_sword_rel(right, rel_rows):
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
    sword.matrix_basis = Matrix(rel_rows)
    bpy.context.view_layer.update()
    if sword.matrix_world.determinant() < 0:
        import bmesh
        bm = bmesh.new(); bm.from_mesh(sword.data)
        for f in bm.faces:
            f.normal_flip()
        bm.to_mesh(sword.data); bm.free(); sword.data.update()
    return sword


def measure_radials(right, sword):
    """Fingertip->handle-axis radial distances, WORLD units (his ground truth
    was armature-local * HAND_SCALE). Evaluated bones: constraints included."""
    bpy.context.view_layer.update()
    deps = bpy.context.evaluated_depsgraph_get()
    ev = right.evaluated_get(deps)
    M = sword.evaluated_get(deps).matrix_world
    p0 = M @ Vector((0, 0, -0.9))
    axis = ((M @ Vector((0, 0, -0.4))) - p0).normalized()
    out = {}
    for finger, chain in CHAINS.items():
        tip = right.matrix_world @ Vector(ev.pose.bones[chain[-1]].tail)
        d = tip - p0
        out[finger] = round((d - d.dot(axis) * axis).length, 4)
    return out


def posed_hand_center(right):
    """Center/radius of the posed RIGHT fist from evaluated finger joints."""
    bpy.context.view_layer.update()
    deps = bpy.context.evaluated_depsgraph_get()
    ev = right.evaluated_get(deps)
    pts = []
    for chain in CHAINS.values():
        for bn in chain:
            pts.append(right.matrix_world @ Vector(ev.pose.bones[bn].head))
        pts.append(right.matrix_world @ Vector(ev.pose.bones[chain[-1]].tail))
    c = sum(pts, Vector()) / len(pts)
    r = max((p - c).length for p in pts)
    return c, r


def unhide_renders():
    for o in bpy.data.objects:
        if o.type == 'MESH':
            o.hide_render = False


def render_shot(cam, name, loc, aim, lens=50):
    cam.data.lens = lens
    cam.location = loc
    cam.rotation_euler = look_at(Vector(loc), Vector(aim))
    bpy.context.scene.render.filepath = OUT_DIR + '\\rg_%s.png' % name
    bpy.ops.render.render(write_still=True)
    print('rendered', name)


def build_retargeted_grip():
    """Stage + apply the retargeted grip. Returns (right, left, sword, report).
    Import this (exec minus main) from the attack-key scripts."""
    data = load_extract()
    right, left = bpy.data.objects[RIGHT_ARM], bpy.data.objects[LEFT_ARM]
    assert 'hand' in right.data.bones, 'need the WRISTED rig'
    strip_scene(); stage_hands()
    apply_matte([bpy.data.objects[RIGHT_MESH], bpy.data.objects[LEFT_MESH]])

    rb = data['armatures']['Armature.001']['bones']
    lb = data['armatures']['Armature.003']['bones']
    apply_finger_pose(right, rb)
    apply_finger_pose(left, lb)

    # thumb-tip amendment (see THUMB_TIP_FLEX_DEG above): right hand only —
    # the left thumb tip in his extract is already in natural range.
    tip = right.pose.bones['Bone.003']
    tip.rotation_mode = 'QUATERNION'
    tip.rotation_quaternion = Quaternion((1, 0, 0),
                                         math.radians(THUMB_TIP_FLEX_DEG))

    # exactness check target BEFORE redistribution
    R_target = distal_rot_target(right, rb['hand'])
    report = redistribute_wrist(right, rb['hand'])
    bpy.context.view_layer.update()
    R_now = right.pose.bones['hand'].matrix.to_3x3()
    resid = (R_target.inverted() @ R_now).to_quaternion().angle
    report['distal_residual_deg'] = round(math.degrees(resid), 3)

    left.location = LEFT_PARK
    # relative seat = his matrix_basis (matrix_parent_inverse probed identity)
    rel = Matrix(data['sword']['matrix_basis'])
    sword = import_sword_rel(right, [list(r) for r in rel])
    unhide_renders()

    report['radials_world'] = measure_radials(right, sword)
    report['radials_khaled_world'] = {
        k: round(v * HAND_SCALE, 4)
        for k, v in data['radials_armature_local'].items()}
    report['radial_delta'] = {
        k: round(report['radials_world'][k] - report['radials_khaled_world'][k], 4)
        for k in report['radials_world']}
    return right, left, sword, report


def main():
    right, left, sword, report = build_retargeted_grip()
    cam = setup_world()
    print('RETARGET_REPORT', json.dumps(report, indent=1))

    # persist the final legal channels for the attack-key scripts
    final = {'right_bones': {}, 'left_bones': {}}
    for pb in right.pose.bones:
        final['right_bones'][pb.name] = list(pb.rotation_quaternion)
    for pb in left.pose.bones:
        final['left_bones'][pb.name] = list(pb.rotation_quaternion)
    final['sword_rel_matrix'] = [list(r) for r in sword.matrix_basis]
    final['left_park'] = list(LEFT_PARK)
    final['report'] = report
    with open(OUT_JSON, 'w') as f:
        json.dump(final, f, indent=1)
    print('WROTE', OUT_JSON)

    # ---- proof renders, close-cropped on the posed fist ----
    c, r = posed_hand_center(right)
    print('fist center %s radius %.2f' % (tuple(round(v, 2) for v in c), r))
    D = r * 4.6
    # palm side: from below/player-side — the side the fingers wrap on,
    # handle + pommel-at-heel readable past the guard cage
    render_shot(cam, 'palm', c + Vector((0.05, -0.70, -0.70)).normalized() * D, c, 50)
    # FP: player eye, behind/above
    render_shot(cam, 'fp', c + Vector((-0.10, -0.92, 0.38)).normalized() * D,
                c + Vector((0, 0.3, 0.25)), 50)
    # back of hand: from downrange (+Y), knuckle side
    render_shot(cam, 'back', c + Vector((-0.40, 0.88, 0.12)).normalized() * D, c, 50)


if __name__ == '__main__':
    main()
