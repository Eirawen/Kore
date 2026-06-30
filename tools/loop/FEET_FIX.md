# Feet Fix: Why They Didn't Lift, and How We Fixed It

## The Bug

The walk cycle animation rotated leg bones but the feet stayed planted at ground level. The legs appeared to stretch instead of step.

## Root Cause: Coordinate Space Mismatch

`rotation_quaternion` on a Blender PoseBone is interpreted in **bone-local space** -- the coordinate frame defined by the bone's rest pose orientation. But `get_bone_bend_axis()` computed the rotation axis in **armature space**.

Every bone has its own local coordinate frame (Y along the bone, X/Z perpendicular). When an armature-space vector like `(-0.725, -0.689, 0)` gets interpreted as a bone-local vector, Blender rotates around whatever direction that vector maps to in the bone's local frame -- which is a completely different direction in armature space.

The diagnostic confirmed this: for every bone, `dot(armature_axis, local_axis)` was far from 1.0 (values like -0.55, 0.04, -0.43). The axes were pointing in entirely wrong directions.

### What Happened Visually

Each bone DID rotate, but around a semi-random axis:
- The femur partially twisted instead of lifting
- The tibia rotated in a different wrong plane
- The tarsus rotated in yet another wrong plane
- The combined effect: rotations partially cancelled, producing visible mesh deformation but near-zero net vertical displacement of the foot tips

The feet looked planted because the net Z-displacement through the whole chain was approximately zero.

## The Fix (v7)

### 1. Compute bend axis in bone-local space

Old (armature space -- WRONG):
```python
bone_dir = (bone.tail_local - bone.head_local).normalized()
bend = bone_dir.cross(Vector((0, 0, 1)))
```

New (bone-local space -- CORRECT):
```python
mat = bone.matrix_local.to_3x3()
up_local = mat.inverted() @ Vector((0, 0, 1))
bone_y = Vector((0, 1, 0))  # bone direction is always Y in local space
bend = up_local.cross(bone_y)
```

The cross product order `up_local.cross(bone_y)` is chosen so that **negative angle = lift** (tail moves toward +Z in armature space).

### 2. Transform swing axis to bone-local space

Old: `return Vector((0, 0, 1))` (armature Z, wrong space)
New: `return mat.inverted() @ Vector((0, 0, 1))` (Z in bone-local)

### 3. Fix tibia/tarsus direction during swing phase

With correct axes, negative angle = lift. The old code used positive angles for tibia/tarsus during the swing phase, which with bone-local axes meant **extending downward** -- counteracting the femur's lift. Fixed to use negative angles during swing (flex up to clear ground).

### 4. Blender 5.1 fcurves API

The smoothing code crashed on `action.fcurves` (removed in Blender 5.1). Fixed to use the layered action API: `action.layers[].strips[].channelbags[].fcurves`.

## Rotation Parameters (v7)

| Parameter   | v6  | v7  | Notes                    |
|-------------|-----|-----|--------------------------|
| COXA_SWING  | 8   | 12  | Forward/back swing       |
| FEMUR_LIFT  | 14  | 30  | Main knee lift           |
| TIBIA_BEND  | 10  | 22  | Flex/extend lower leg    |
| TARSUS_FLEX | 3   | 8   | Foot tip curl            |

## Files Changed

- `tools/animate_walk.py` -- v6 -> v7, bone-local axes + corrected phase logic
- `tools/loop/diagnose_feet.py` -- new diagnostic script for testing rotations

## Diagnostic Script

`diagnose_feet.py` tests the bone hierarchy and rotation propagation:
```bash
blender.exe --background --python diagnose_feet.py
```

Prints: parent chain, use_connect status, armature vs bone-local axes, and tests femur rotation at -30 degrees to measure actual tarsus Z-displacement with both axis types.

## Key Insight

`bone.matrix_local.to_3x3()` transforms bone-local -> armature space.
Its inverse transforms armature -> bone-local.
All axes passed to `rotation_quaternion` must be in bone-local space.
This applies to ANY Blender script that sets pose bone rotations programmatically.
