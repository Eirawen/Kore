# Dump the current pose (bone rotations + object transforms + sword seat) from a
# saved .blend so Kore can inspect exactly what Khaled posed. Reads whatever
# .blend Blender was opened with.
#   blender --background <blend> --python read_poses.py
import bpy, json, math

ARMS = ['Armature.001', 'Armature.003']   # right, left(mirrored)
out = {}
for arm_name in ARMS:
    arm = bpy.data.objects.get(arm_name)
    if not arm:
        continue
    o = {
        'object': {
            'location':   [round(v, 4) for v in arm.location],
            'rot_eul_deg':[round(math.degrees(a), 2) for a in arm.rotation_euler],
            'scale':      [round(v, 4) for v in arm.scale],
        },
        'posed_bones': {},
    }
    for pb in arm.pose.bones:
        q = (pb.rotation_quaternion if pb.rotation_mode == 'QUATERNION'
             else pb.matrix_basis.to_quaternion())
        deg = round(math.degrees(q.angle), 2)
        if deg > 0.05:   # only non-identity bones
            o['posed_bones'][pb.name] = {
                'quat': [round(v, 4) for v in q],
                'axis': [round(v, 3) for v in q.axis],
                'deg': deg,
            }
    out[arm_name] = o

sw = bpy.data.objects.get('Sword')
if sw:
    out['Sword'] = {
        'parent_bone': sw.parent_bone,
        'loc': [round(v, 4) for v in sw.location],
        'rot_eul_deg': [round(math.degrees(a), 2) for a in sw.rotation_euler],
        'matrix_basis': [[round(v, 4) for v in row] for row in sw.matrix_basis],
    }

print('POSE_JSON_START')
print(json.dumps(out, indent=1))
print('POSE_JSON_END')
