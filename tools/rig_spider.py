"""
Spider Rigging Script v0.3 — Landmark-Driven
by Kore

All joint positions from Khaled's vertex clicks.
No anatomical guessing. Just connecting dots.

Note: joint landmarks were taken from underside of mesh,
so a small Z offset is applied to center bones in the limbs.
"""

import bpy
import mathutils

# ============================================================
# LANDMARKS — all from direct vertex clicks in Blender
# ============================================================

Z_CLEARANCE = 0.03  # offset because landmarks were clicked from underside

FEET = {
    0: (0.699, -0.860, -0.301),
    1: (-0.9136, -0.857846, -0.301507),
    2: (0.850042, -0.083034, -0.314296),
    3: (-1.04919, -0.084804, -0.308886),
    4: (0.65095, 0.858764, -0.320038),
    5: (-0.868892, 0.867755, -0.322475),
}

LEGS = {
    0: {
        'ankle':    (0.521023, -0.669361, -0.27931),
        'knee':     (0.413548, -0.503744, -0.022546),
        'shoulder': (0.171667, -0.259735, 0.101885),
        'trap':     (0.006075, -0.146042, 0.041304),
    },
    1: {
        'ankle':    (-0.75766, -0.65179, -0.285871),
        'knee':     (-0.642341, -0.495739, -0.020839),
        'shoulder': (-0.406639, -0.249967, 0.109905),
        'trap':     (-0.234052, -0.127335, 0.037884),
    },
    2: {
        'ankle':    (0.627919, -0.078649, -0.285548),
        'knee':     (0.454835, -0.064666, -0.054955),
        'shoulder': (0.128288, -0.071325, 0.094212),
        'trap':     (0.013644, -0.073874, 0.047496),
    },
    3: {
        'ankle':    (-0.844274, -0.075825, -0.270036),
        'knee':     (-0.672766, -0.064042, -0.052618),
        'shoulder': (-0.34181, -0.063238, 0.069193),
        'trap':     (-0.229683, -0.078384, 0.047703),
    },
    4: {
        'ankle':    (0.549993, 0.489808, -0.248704),
        'knee':     (0.416724, 0.356367, -0.012532),
        'shoulder': (0.146938, 0.260133, 0.134091),
        'trap':     (-0.000635, 0.161637, 0.017548),
    },
    5: {
        'ankle':    (-0.76866, 0.489593, -0.248276),
        'knee':     (-0.633529, 0.358834, -0.011199),
        'shoulder': (-0.364356, 0.261301, 0.134923),
        'trap':     (-0.189756, 0.15007, 0.029117),
    },
}

BODY = {
    'center':  (-0.082222, -0.08215, -0.08215),
    'abdomen': (-0.090292, 0.484582, 0.20841),
}

APPENDAGES = {
    'feeler_L': (0.054876, -0.555862, 0.106817),
    'feeler_R': (-0.272162, -0.552321, 0.104595),
    'fang_L':   (-0.080756, -0.263288, 0.000598),
    'fang_R':   (-0.1341, -0.261401, -0.000428),
}

# ============================================================
# HELPERS
# ============================================================

def vec(t, z_offset=0):
    return mathutils.Vector((t[0], t[1], t[2] + z_offset))

def find_spider_mesh():
    for obj in bpy.data.objects:
        if obj.type == 'MESH' and 'Mesh' in obj.name:
            return obj
    for obj in bpy.data.objects:
        if obj.type == 'MESH':
            return obj
    return None

def create_bone(armature, name, head, tail, parent_name=None, connected=False):
    bone = armature.data.edit_bones.new(name)
    bone.head = head
    bone.tail = tail
    if parent_name and parent_name in armature.data.edit_bones:
        bone.parent = armature.data.edit_bones[parent_name]
        bone.use_connect = connected
    return bone

# ============================================================
# BUILD
# ============================================================

def build_rig():
    spider_mesh = find_spider_mesh()
    if spider_mesh is None:
        print("ERROR: No mesh found in scene!")
        return

    print(f"Found spider mesh: {spider_mesh.name}")

    # Clean up previous attempts
    for obj in list(bpy.data.objects):
        if 'SpiderRig' in obj.name:
            bpy.data.objects.remove(obj, do_unlink=True)
    for arm in list(bpy.data.armatures):
        if 'SpiderArmature' in arm.name:
            bpy.data.armatures.remove(arm)

    spider_mesh.select_set(True)
    bpy.context.view_layer.objects.active = spider_mesh
    bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')
    bpy.ops.object.select_all(action='DESELECT')

    # Create armature
    mesh_location = spider_mesh.location.copy()
    bpy.ops.object.armature_add(enter_editmode=True, location=mesh_location)
    armature = bpy.context.object
    armature.name = 'SpiderRig'
    armature.data.name = 'SpiderArmature'

    default_bone = armature.data.edit_bones.get('Bone')
    if default_bone:
        armature.data.edit_bones.remove(default_bone)

    bc = BODY['center']
    ac = BODY['abdomen']

    # --- ROOT ---
    root_head = vec(bc)
    root_tail = vec(bc)
    root_tail.z += 0.08
    create_bone(armature, 'root', root_head, root_tail)

    # --- CEPHALOTHORAX ---
    ceph_head = vec(bc)
    ceph_tail = vec(bc)
    ceph_tail.z += 0.12
    create_bone(armature, 'cephalothorax', ceph_head, ceph_tail, 'root')

    # --- HEAD ---
    fang_mid = vec(APPENDAGES['fang_L']).lerp(vec(APPENDAGES['fang_R']), 0.5)
    head_dir = (fang_mid - vec(bc)).normalized()
    head_tail = vec(bc) + head_dir * 0.15
    create_bone(armature, 'head', vec(bc), head_tail, 'cephalothorax')

    # --- ABDOMEN ---
    abd_dir = (vec(ac) - vec(bc)).normalized()
    abd_start = vec(bc) + abd_dir * 0.1
    create_bone(armature, 'abdomen', abd_start, vec(ac), 'root')

    # --- FANGS ---
    for side, key in [('L', 'fang_L'), ('R', 'fang_R')]:
        tip = vec(APPENDAGES[key])
        base = vec(bc).lerp(tip, 0.4)
        mid = vec(bc).lerp(tip, 0.7)
        create_bone(armature, f'fang_{side}_base', base, mid, 'head')
        create_bone(armature, f'fang_{side}_tip', mid, tip, f'fang_{side}_base', connected=True)

    # --- PEDIPALPS ---
    for side, key in [('L', 'feeler_L'), ('R', 'feeler_R')]:
        tip = vec(APPENDAGES[key])
        base = vec(bc).lerp(tip, 0.3)
        mid = vec(bc).lerp(tip, 0.65)
        create_bone(armature, f'pedipalp_{side}_base', base, mid, 'head')
        create_bone(armature, f'pedipalp_{side}_tip', mid, tip, f'pedipalp_{side}_base', connected=True)

    # --- LEGS — pure connect-the-dots ---
    leg_labels = {0: 'FL', 1: 'FR', 2: 'ML', 3: 'MR', 4: 'RL', 5: 'RR'}

    for leg_id in range(6):
        joints = LEGS[leg_id]
        foot = FEET[leg_id]
        prefix = f'leg_{leg_labels[leg_id]}'
        z = Z_CLEARANCE

        trap = vec(joints['trap'], z)
        shoulder = vec(joints['shoulder'], z)
        knee = vec(joints['knee'], z)
        ankle = vec(joints['ankle'], z)
        foot_tip = vec(foot)  # no Z offset on feet — they're on the ground

        create_bone(armature, f'{prefix}_coxa',
                     trap, shoulder, 'cephalothorax')
        create_bone(armature, f'{prefix}_femur',
                     shoulder, knee, f'{prefix}_coxa', connected=True)
        create_bone(armature, f'{prefix}_tibia',
                     knee, ankle, f'{prefix}_femur', connected=True)
        create_bone(armature, f'{prefix}_tarsus',
                     ankle, foot_tip, f'{prefix}_tibia', connected=True)

    # --- DONE WITH BONES ---
    bpy.ops.object.mode_set(mode='OBJECT')

    # --- PARENT WITH AUTO WEIGHTS ---
    bpy.ops.object.select_all(action='DESELECT')
    spider_mesh.select_set(True)
    armature.select_set(True)
    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.parent_set(type='ARMATURE_AUTO')

    print("=" * 50)
    print("RIGGING COMPLETE!")
    print(f"Bones: {len(armature.data.bones)}")
    print("=" * 50)

try:
    build_rig()
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
