"""
Diagnostic: Why don't the feet lift?
by Kore

Runs in Blender headless. Tests bone hierarchy, bend axes, and rotation propagation.
Compares armature-space axis (the bug) vs bone-local axis (the fix).

Run via:
  blender.exe --background --python diagnose_feet.py
"""

import bpy
import mathutils
from mathutils import Vector
import math
import sys

# ============================================================
# STEP 1: Import mesh and run rig
# ============================================================

WSL_PREFIX = r"\\wsl.localhost\Ubuntu"
GLB_PATH = WSL_PREFIX + r"\home\khaled\Kore\spider.glb"
RIG_SCRIPT = WSL_PREFIX + r"\home\khaled\Kore\tools\rig_spider_auto.py"

# Clear scene
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
for block in bpy.data.meshes:
    if block.users == 0:
        bpy.data.meshes.remove(block)
for block in bpy.data.armatures:
    if block.users == 0:
        bpy.data.armatures.remove(block)

print("=" * 60)
print("FOOT LIFT DIAGNOSTIC")
print("=" * 60)

print("\n[1] Importing spider mesh...")
bpy.ops.import_scene.gltf(filepath=GLB_PATH)

print("\n[2] Running rig...")
with open(RIG_SCRIPT, 'r') as f:
    exec(f.read())

# ============================================================
# STEP 2: Find armature
# ============================================================

arm = None
for obj in bpy.data.objects:
    if obj.type == 'ARMATURE' and 'SpiderRig' in obj.name:
        arm = obj
        break

if not arm:
    print("ERROR: No SpiderRig found!")
    sys.exit(1)

bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode='POSE')

# ============================================================
# STEP 3: Print bone hierarchy
# ============================================================

print("\n" + "=" * 60)
print("BONE HIERARCHY")
print("=" * 60)

legs = ['FL', 'FR', 'ML', 'MR', 'RL', 'RR']
segments = ['coxa', 'femur', 'tibia', 'tarsus']

for leg in legs:
    print(f"\n--- Leg {leg} ---")
    for seg in segments:
        name = f'leg_{leg}_{seg}'
        if name not in arm.pose.bones:
            print(f"  {name}: NOT FOUND")
            continue
        pb = arm.pose.bones[name]
        bone = pb.bone
        parent_name = bone.parent.name if bone.parent else "NONE"
        connected = bone.use_connect
        head = bone.head_local
        tail = bone.tail_local
        bone_len = (tail - head).length
        print(f"  {name}:")
        print(f"    parent={parent_name}, connected={connected}, length={bone_len:.4f}")
        print(f"    head=({head.x:.4f}, {head.y:.4f}, {head.z:.4f})")
        print(f"    tail=({tail.x:.4f}, {tail.y:.4f}, {tail.z:.4f})")

# ============================================================
# STEP 4: Axis analysis - armature vs bone-local
# ============================================================

print("\n" + "=" * 60)
print("BEND AXIS: ARMATURE-SPACE vs BONE-LOCAL")
print("=" * 60)
print("The animation sets rotation_quaternion, which expects BONE-LOCAL axes.")
print("The current code computes axes in ARMATURE space. This is the bug.\n")

for leg in ['FL', 'MR']:  # Just two legs to keep output manageable
    print(f"--- Leg {leg} ---")
    for seg in segments:
        name = f'leg_{leg}_{seg}'
        if name not in arm.pose.bones:
            continue
        bone = arm.pose.bones[name].bone

        # Current code: armature-space axis
        bone_dir = (bone.tail_local - bone.head_local).normalized()
        up = Vector((0, 0, 1))
        bend_arm = bone_dir.cross(up)
        if bend_arm.length < 0.001:
            bend_arm = bone_dir.cross(Vector((0, 1, 0)))
        bend_arm.normalize()

        # Fix: transform to bone-local space
        mat = bone.matrix_local.to_3x3()
        bend_local = mat.inverted() @ bend_arm
        bend_local.normalize()

        # Show bone's local frame in armature space
        local_x = mat @ Vector((1, 0, 0))
        local_y = mat @ Vector((0, 1, 0))  # should be along bone
        local_z = mat @ Vector((0, 0, 1))

        # How different are they?
        dot = bend_arm.dot(bend_local)

        print(f"  {seg}:")
        print(f"    bone_dir:        ({bone_dir.x:+.3f}, {bone_dir.y:+.3f}, {bone_dir.z:+.3f})")
        print(f"    bend ARMATURE:   ({bend_arm.x:+.3f}, {bend_arm.y:+.3f}, {bend_arm.z:+.3f})")
        print(f"    bend LOCAL:      ({bend_local.x:+.3f}, {bend_local.y:+.3f}, {bend_local.z:+.3f})")
        print(f"    local X in arm:  ({local_x.x:+.3f}, {local_x.y:+.3f}, {local_x.z:+.3f})")
        print(f"    local Y in arm:  ({local_y.x:+.3f}, {local_y.y:+.3f}, {local_y.z:+.3f})")
        print(f"    dot(arm, local): {dot:.3f} {'(SAME)' if abs(dot) > 0.99 else '(DIFFERENT!)'}")

# ============================================================
# STEP 5: Rotation propagation test
# ============================================================

print("\n" + "=" * 60)
print("ROTATION PROPAGATION TEST")
print("=" * 60)

bpy.context.view_layer.update()

test_leg = 'FL'
bone_names = [f'leg_{test_leg}_{s}' for s in segments if f'leg_{test_leg}_{s}' in arm.pose.bones]

# Record rest positions
print(f"\n[A] Rest pose tail positions (leg {test_leg}):")
rest_tails = {}
for name in bone_names:
    pb = arm.pose.bones[name]
    tail_world = arm.matrix_world @ pb.tail
    rest_tails[name] = tail_world.copy()
    print(f"  {name}: tail Z = {tail_world.z:.4f}")

# ---- TEST 1: Armature-space axis (THE BUG) ----
femur_name = f'leg_{test_leg}_femur'
bone = arm.pose.bones[femur_name].bone
bone_dir = (bone.tail_local - bone.head_local).normalized()
bend_arm = bone_dir.cross(Vector((0, 0, 1)))
bend_arm.normalize()

pb = arm.pose.bones[femur_name]
pb.rotation_mode = 'QUATERNION'
pb.rotation_quaternion = mathutils.Quaternion(bend_arm, math.radians(-30))
bpy.context.view_layer.update()

print(f"\n[B] After femur -30deg around ARMATURE-SPACE axis (BUG):")
for name in bone_names:
    pb = arm.pose.bones[name]
    tail_world = arm.matrix_world @ pb.tail
    dz = tail_world.z - rest_tails[name].z
    dtotal = (tail_world - rest_tails[name]).length
    print(f"  {name}: tail Z = {tail_world.z:.4f}  dZ = {dz:+.4f}  |delta| = {dtotal:.4f}")

tarsus_name = f'leg_{test_leg}_tarsus'
if tarsus_name in rest_tails:
    bug_dz = (arm.matrix_world @ arm.pose.bones[tarsus_name].tail).z - rest_tails[tarsus_name].z
    print(f"\n  >>> TARSUS TIP Z-LIFT (BUG): {bug_dz:+.4f}m")

# Reset
arm.pose.bones[femur_name].rotation_quaternion = mathutils.Quaternion()
bpy.context.view_layer.update()

# ---- TEST 2: Bone-local axis (THE FIX) ----
mat = bone.matrix_local.to_3x3()
bend_local = mat.inverted() @ bend_arm
bend_local.normalize()

pb = arm.pose.bones[femur_name]
pb.rotation_quaternion = mathutils.Quaternion(bend_local, math.radians(-30))
bpy.context.view_layer.update()

print(f"\n[C] After femur -30deg around BONE-LOCAL axis (FIX):")
for name in bone_names:
    pb = arm.pose.bones[name]
    tail_world = arm.matrix_world @ pb.tail
    dz = tail_world.z - rest_tails[name].z
    dtotal = (tail_world - rest_tails[name]).length
    print(f"  {name}: tail Z = {tail_world.z:.4f}  dZ = {dz:+.4f}  |delta| = {dtotal:.4f}")

if tarsus_name in rest_tails:
    fix_dz = (arm.matrix_world @ arm.pose.bones[tarsus_name].tail).z - rest_tails[tarsus_name].z
    print(f"\n  >>> TARSUS TIP Z-LIFT (FIX): {fix_dz:+.4f}m")

# Reset
arm.pose.bones[femur_name].rotation_quaternion = mathutils.Quaternion()
bpy.context.view_layer.update()

# ============================================================
# STEP 6: Verdict
# ============================================================

print("\n" + "=" * 60)
print("VERDICT")
print("=" * 60)

if tarsus_name in rest_tails:
    print(f"\n  Bug (armature-space axis): tarsus Z-lift = {bug_dz:+.4f}m")
    print(f"  Fix (bone-local axis):     tarsus Z-lift = {fix_dz:+.4f}m")
    if abs(fix_dz) > abs(bug_dz) * 2:
        print(f"\n  CONFIRMED: Bone-local axis produces {abs(fix_dz)/max(abs(bug_dz), 0.0001):.1f}x more Z-lift.")
        print(f"  The bug is a coordinate-space mismatch in get_bone_bend_axis().")
        print(f"  Fix: transform armature-space axis to bone-local space")
        print(f"  via bone.matrix_local.to_3x3().inverted() @ axis")
    else:
        print(f"\n  INCONCLUSIVE: Both produce similar Z-lift.")
        print(f"  The issue may be elsewhere (weights? constraints?).")

print("\n" + "=" * 60)
print("DIAGNOSTIC COMPLETE")
print("=" * 60)
