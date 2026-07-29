"""Read back what Khaled posed in fp_sandbox.blend.

Reports, per armature: the OBJECT transform (which is the real lever for the
framing complaint — location/rotation/scale of the whole arm) and any posed
bones. Plus the on-screen footprint of each hand mesh through the FP camera,
so "how much of the frame is this arm eating" is a NUMBER, not an opinion.

    blender --background fp_sandbox.blend --python read_fp_pose.py
"""
import bpy, json, math
from mathutils import Vector

scene = bpy.context.scene
cam = scene.camera
out = {'camera': {
    'location': [round(v, 4) for v in cam.location],
    'fov_v_deg': round(math.degrees(cam.data.angle_y), 2),
}}

def ndc(p):
    """world point -> normalised device coords through the FP camera."""
    from bpy_extras.object_utils import world_to_camera_view
    v = world_to_camera_view(scene, cam, p)
    return v.x, v.y, v.z

deps = bpy.context.evaluated_depsgraph_get()
MESH_OF = {'Armature.001': 'Sphere.001', 'Armature.003': 'Sphere.002'}

for arm_name, mesh_name in MESH_OF.items():
    arm = bpy.data.objects.get(arm_name)
    if not arm:
        continue
    rec = {
        'object': {
            'location':    [round(v, 4) for v in arm.location],
            'rot_eul_deg': [round(math.degrees(a), 2) for a in arm.rotation_euler],
            'scale':       [round(v, 4) for v in arm.scale],
            'hidden':      bool(arm.hide_render),
        },
        'posed_bones': {},
    }
    for pb in arm.pose.bones:
        q = (pb.rotation_quaternion if pb.rotation_mode == 'QUATERNION'
             else pb.matrix_basis.to_quaternion())
        deg = round(math.degrees(q.angle), 2)
        if deg > 0.05:
            rec['posed_bones'][pb.name] = {
                'quat': [round(v, 4) for v in q], 'deg': deg}

    m = bpy.data.objects.get(mesh_name)
    if m and not m.hide_render:
        eo = m.evaluated_get(deps)
        pts = [eo.matrix_world @ v.co for v in eo.data.vertices]
        uv = [ndc(p) for p in pts]
        front = [(x, y) for x, y, z in uv if z > 0]
        if front:
            xs = [x for x, y in front]; ys = [y for x, y in front]
            vis = [1 for x, y in front if 0 <= x <= 1 and 0 <= y <= 1]
            rec['screen'] = {
                'x_range': [round(min(xs), 3), round(max(xs), 3)],
                'y_range': [round(min(ys), 3), round(max(ys), 3)],
                'pct_verts_on_screen': round(100.0 * len(vis) / len(pts), 1),
                'frame_width_frac':  round(min(1, max(xs)) - max(0, min(xs)), 3),
                'frame_height_frac': round(min(1, max(ys)) - max(0, min(ys)), 3),
            }
    out[arm_name] = rec

print('FP_POSE_JSON_START')
print(json.dumps(out, indent=1))
print('FP_POSE_JSON_END')
