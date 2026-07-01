# Gotchas — Non-Obvious Pitfalls for Rigging & Animation

Read this before touching the pipeline. Every item here cost hours.

## Rigging

### 1. Apply mesh transforms BEFORE creating the armature
The glTF importer puts a 90° X rotation on the mesh as an OBJECT TRANSFORM. If you create the armature without applying this, bones are in a different coordinate space than the mesh vertices. They look offset by ~10cm in all directions.
**Fix:** `bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)` on the mesh, then create armature at `(0, 0, 0)`.

### 2. Bone chain must go body→foot, not foot→body
The medial axis traces from endpoints (feet) inward (body). If you build bones in this order, the foot is the PARENT and the body is the CHILD. Rotating the femur moves the body instead of the foot.
**Fix:** Reverse the joints array before creating bones: `joints[::-1]`.

### 3. Medial axis resolution tradeoff
Higher voxel resolution = more precise centerlines BUT noisier skeleton with more spurious branches that fragment the trace. 0.001m gives sub-mm precision but the topology breaks. 0.012m gives stable topology but ~1cm precision.
**Fix:** Multi-resolution. Coarse (0.012m) for topology, fine (0.003m) for centerline refinement.

### 4. Triangle soup voxelization
Meshy meshes are non-manifold triangle soup. Blender's auto-weight painting (ARMATURE_AUTO) will FAIL with "Bone Heat Weighting: failed to find solution." Don't use it.
**Fix:** Custom proximity or physics-based weights via ARMATURE_NAME + manual vertex group assignment.

## Weights

### 5. Branch segmentation, not bone proximity
NEVER use bone proximity alone for body-part assignment. The abdomen bone is closer to rear leg vertices than leg bones are. Body-priority heuristics (multipliers, hard radii) are band-aids that break in new ways.
**Fix:** Two-layer weights. Layer 1: assign vertices to body parts using medial axis branch PATHS (full centerlines, not bone positions). Layer 2: rigid-plate weighting within each body part.

### 6. Body-blend check goes on the BODY end
After reversing the bone chain, `chain_idx == 0` is the body end (coxa) and `chain_idx == len(chain)-1` is the foot end. The body-blend check must use `chain_idx == 0` and `best_t < blend_t`, NOT `chain_idx == len(chain)-1` and `best_t > (1-blend_t)`. Getting this wrong anchors all foot vertices to the cephalothorax.

### 7. Abdomen is a "body" bone for weight purposes
When doing branch segmentation, vertices closest to the abdomen branch should be assigned to group "body", not to a separate "abdomen" group. Otherwise they might not get the body-priority treatment.

## Animation

### 8. rotation_quaternion is in BONE-LOCAL space
`PoseBone.rotation_quaternion` is interpreted in bone-local space, not armature space. If you compute the rotation axis in armature space and set it as a quaternion, the bone rotates around a wrong axis. Legs splay sideways instead of lifting.
**Fix:** Transform the desired rotation axis to bone-local space: `bone.matrix_local.to_3x3().inverted() @ armature_space_axis`.

### 9. Euler rotation_euler uses GLOBAL axes
The `set_rot(rx, ry, rz)` helper with `rotation_mode = 'XYZ'` rotates around global axes. Every leg points in a different direction, so global X produces different motion for each leg.
**Fix:** Use quaternion rotation around computed bone-local axes instead of Euler angles.

### 10. Blender 5.1 broke action.fcurves
`Action.fcurves` no longer exists in Blender 5.1. FCurves are now at `action.layers[].strips[].channelbags[].fcurves`. The Bezier smoothing code needs to handle both APIs.

## Pipeline

### 11. WSL→Windows environment variables are unreliable
`export KORE_ANIMATION=threat` in WSL doesn't reliably reach Windows Blender via `--background --python`. The animation defaults to "walk."
**Fix:** Write config to a file (`tools/loop/.render_config`) and read it from the Blender script via UNC path.

### 12. Walk cycles: N groups need ≥(1/N) swing fraction for seamless gait
For any walk cycle with N alternating leg groups, each group's swing phase must cover at least 1/N of the total cycle. Otherwise there are frames where ALL groups are in stance and nothing moves (dead zone).
- 2 groups (alternating tripod): swing ≥ 50%
- 3 groups (wave gait): swing ≥ 33%
- 4 groups: swing ≥ 25%

`N × swing_fraction ≥ 1.0` or the gait has gaps. "Deliberate" feel comes from amplitude and speed, not from spending more time standing still. Standing still reads as broken, not patient.

### 13. Blender headless path format
The `--python` argument to Windows Blender must use Windows UNC paths: `\\wsl.localhost\Ubuntu\path\to\script.py`. WSL paths like `/home/khaled/...` get mangled.
**Fix:** Use `wslpath -w` to convert, or hardcode the UNC prefix.
