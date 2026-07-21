# Extract Khaled's hand-authored grip from poses/khaled_grip_base.blend
# (read-only treasure — this script only READS it).
#
# Dumps to poses/khaled_grip_extract.json:
#   - every pose-bone quaternion on both armatures (raw channels)
#   - the Sword seat RELATIVE to the hand bone-tail frame (recomputed from the
#     posed hand matrix, not trusted from raw matrix_basis alone)
#   - ground-truth fingertip->handle-axis radial distances (armature-local)
#   - hide_render flags (gotcha 14b)
#
#   blender --background poses/khaled_grip_base.blend --python extract_khaled_grip.py
import bpy, json, math
from mathutils import Vector, Matrix

OUT = r'\\wsl.localhost\Ubuntu\home\khaled\Kore\poses\khaled_grip_extract.json'
CHAINS = {
    'thumb':  ['Bone.001', 'Bone.002', 'Bone.003'],
    'index':  ['Bone.004', 'Bone.017', 'Bone.018', 'Bone.019'],
    'middle': ['Bone.005', 'Bone.014', 'Bone.015', 'Bone.016'],
    'ring':   ['Bone.006', 'Bone.011', 'Bone.012', 'Bone.013'],
    'pinky':  ['Bone.007', 'Bone.008', 'Bone.009', 'Bone.010'],
}

bpy.context.view_layer.update()
out = {'hide_render': {}, 'armatures': {}}

for o in bpy.data.objects:
    out['hide_render'][o.name] = o.hide_render

for arm_name in ('Armature.001', 'Armature.003'):
    arm = bpy.data.objects.get(arm_name)
    if not arm:
        continue
    a = {'object': {
            'location': list(arm.location),
            'rot_eul_deg': [math.degrees(v) for v in arm.rotation_euler],
            'scale': list(arm.scale)},
         'bones': {}}
    for pb in arm.pose.bones:
        if pb.rotation_mode == 'QUATERNION':
            q = pb.rotation_quaternion
        else:
            q = pb.matrix_basis.to_quaternion()
        a['bones'][pb.name] = list(q)
    out['armatures'][arm_name] = a

right = bpy.data.objects['Armature.001']
sw = bpy.data.objects.get('Sword')
if sw:
    hand = right.pose.bones['hand']
    bone_tail_frame = hand.matrix @ Matrix.Translation((0, hand.bone.length, 0))
    # armature-local seat of the sword (what bone-parenting composes to)
    seat_local = bone_tail_frame @ sw.matrix_basis
    out['sword'] = {
        'parent_bone': sw.parent_bone,
        'matrix_basis': [list(r) for r in sw.matrix_basis],
        'seat_armature_local': [list(r) for r in seat_local],
        'hand_bone_length': hand.bone.length,
    }
    # ---- ground-truth radials: fingertip -> handle axis, armature-local ----
    # sword local: blade = +Z, grip section z in [-0.9, -0.7], r ~ 0.035
    M = seat_local  # sword-local -> armature-local
    p0 = M @ Vector((0, 0, -0.9))   # pommel end of grip
    p1 = M @ Vector((0, 0, -0.4))   # top of guard region (axis direction anchor)
    axis = (p1 - p0).normalized()
    deps = bpy.context.evaluated_depsgraph_get()
    ev = right.evaluated_get(deps)
    radials = {}
    tips = {}
    for finger, chain in CHAINS.items():
        tip = Vector(ev.pose.bones[chain[-1]].tail)   # armature-local
        d = tip - p0
        radials[finger] = (d - d.dot(axis) * axis).length
        tips[finger] = list(tip)
    out['radials_armature_local'] = radials
    out['fingertips_armature_local'] = tips
    out['handle_axis'] = {'p0': list(p0), 'axis': list(axis)}
    # hand + forearm posed matrices for the retarget solver
    out['hand_pose_matrix'] = [list(r) for r in hand.matrix]
    fore = right.pose.bones['forearm']
    out['forearm_pose_matrix'] = [list(r) for r in fore.matrix]

with open(OUT, 'w') as f:
    json.dump(out, f, indent=1)
print('EXTRACT_OK ->', OUT)
print(json.dumps({'radials': out.get('radials_armature_local'),
                  'hide_render': {k: v for k, v in out['hide_render'].items() if v},
                  'sword_parent_bone': out.get('sword', {}).get('parent_bone')},
                 indent=1))
