# Rigging & Animation Pipeline Architecture

Complete reference for the auto-rigging and animation system. Every stage, every decision, every alternative considered.

---

## Pipeline Overview

```
Input: .glb mesh (any creature, any topology)
  ↓
[1] VOXELIZE — trimesh, multi-resolution
  ↓ coarse (0.012m): stable topology, 11 branches, ~670 skeleton points
  ↓ fine (0.003m): precise centerlines, ~2744 skeleton points
  ↓
[2] SKELETONIZE — scikit-image 3D thinning (medial axis)
  ↓ extracts centerlines through every limb, body segment, appendage
  ↓
[3] TRACE BRANCHES — walk the skeleton from endpoints to junctions
  ↓ produces ordered point paths per branch
  ↓
[4] CLASSIFY — match branches to body parts
  ↓ legs: matched by foot position proximity to known landmarks
  ↓ abdomen: most spatially isolated non-leg branch
  ↓ pedipalps: medium non-leg branches (>20% avg leg length)
  ↓ fangs: short non-leg branches (>4% avg leg length)
  ↓
[5] REFINE — multi-resolution centerline improvement
  ↓ coarse paths snapped to fine skeleton points
  ↓ center refinement: surface averaging pushes to true geometric center
  ↓
[6] DETECT JOINTS — curvature analysis along refined paths
  ↓ peaks in direction-change signal = joint positions
  ↓ minimum segment filter (but NEVER merge endpoint segments — tarsus is short!)
  ↓
[7] GENERATE BLENDER SCRIPT — bone placement + weight computation
  ↓ transform_apply on mesh first (bakes 90° glTF rotation)
  ↓ armature at (0,0,0)
  ↓ bones from joints[::-1] (reversed: body→foot, not foot→body)
  ↓ two-layer weights: branch segmentation + rigid chitin plates
  ↓
[8] ANIMATE — bone-local quaternion keyframes
  ↓ rotation_quaternion in bone-local space
  ↓ axes computed via bone.matrix_local.to_3x3().inverted()
  ↓
[9] RENDER — headless Blender → ffmpeg → grid
  ↓ iterate.sh: one-command autonomous cycle
  ↓ 30 seconds per iteration
  ↓
Output: animated, rigged model visible through temporal grids
```

---

## Stage Details

### [1] Voxelization

**Library:** trimesh
**Method:** `mesh.voxelized(pitch)` → `ndimage.binary_fill_holes()` → uint8 grid

Multi-resolution approach discovered through failure:
- 0.012m: stable topology (11 branches), but ~1cm precision → bones slightly outside mesh
- 0.005m: better precision, still stable
- 0.003m: good precision + stable topology (sweet spot for fine pass)
- 0.002m: 4157 skeleton points but topology starts fragmenting
- 0.001m: 1.7GB RAM, topology breaks completely (too many spurious branches)

**Why multi-resolution:** Higher resolution = more precise centerlines BUT more spurious branch points that fragment the trace. Coarse pass finds the TOPOLOGY (which branches exist). Fine pass refines the POSITIONS (where exactly the centerline runs).

**Hole filling:** `ndimage.binary_fill_holes()` is critical. Triangle soup from Meshy has holes in the volume. Without filling, the medial axis runs along the surface instead of through the center.

### [2] Skeletonization

**Library:** scikit-image
**Method:** `skeletonize()` (was `skeletonize_3d` in older versions)

3D thinning: iteratively peels outer voxel layers until only a 1-voxel-thick skeleton remains. The skeleton IS the medial axis — the set of points maximally distant from the surface.

**Neighbor classification:**
```python
kernel = np.ones((3, 3, 3)); kernel[1,1,1] = 0
neighbor_counts = ndimage.convolve(skeleton, kernel) * skeleton
endpoints = neighbor_counts == 1    # tips of branches
branch_points = neighbor_counts >= 3  # junctions
regular_points = neighbor_counts == 2  # mid-segment
```

### [3] Branch Tracing

Walk from each endpoint along the skeleton until hitting a branch point or another endpoint. 26-connectivity (diagonal neighbors count). Each branch = an ordered list of voxel positions.

**Coordinate conversion:** voxel indices → world coords: `idx * pitch + voxels.transform[:3, 3]`
**glTF to Blender:** `to_blender(x, y, z) = (x, -z, y)` — Y-up to Z-up

### [4] Branch Classification

**Legs:** matched by proximity of branch start (foot tip) to known foot positions. Threshold: 0.15m. This is the one place that uses hardcoded landmarks — could be replaced by the LLM semantic layer (see rig-compiler.md).

**Abdomen:** most spatially ISOLATED non-leg branch. Measured by minimum distance from its tip to any other non-leg branch tip. The abdomen is alone in the rear; pedipalps and fangs cluster in the front. This is general for any arthropod.

**Pedipalps vs fangs:** classified by length relative to average leg length. Pedipalps > 20% of avg leg length, fangs > 4%.

**Orientation detection:** (analyze_spider_v4.py) Two independent signals:
1. Cross-sectional height asymmetry — abdomen is round (Y-span 0.346), cephalothorax is flat (Y-span 0.110)
2. Thin protrusion detection — head end has fangs/pedipalps (thin structures), rear tapers smoothly

### [5] Centerline Refinement

**Fine-pass snapping:** For each coarse path point, find the nearest fine skeleton point. This improves positional accuracy from ~1cm to ~3mm.

**Resampling:** Between consecutive coarse waypoints, find fine skeleton points near the connecting line segment. Sort by projection along the segment. This densifies the path with fine-resolution points.

**Center refinement (surface averaging):**
For each path point:
1. Find nearest mesh surface point (outward direction)
2. Cast ray in opposite direction (find other side)
3. Midpoint of two surface points = true geometric center
4. Repeat 4 iterations

**Important:** This only works if the starting point is already roughly inside the mesh. If it's outside, the algorithm pushes it FURTHER away. The voxel-based medial axis is already inside, so it works as a refinement step.

### [6] Joint Detection

**Curvature analysis:** Compute direction vectors along the path, then angle between consecutive directions. Smooth with `uniform_filter1d`. Peaks in the angle signal = joints (where the path changes direction).

**Peak selection:** Greedy — find highest peak, zero out neighborhood (min_separation), repeat for n_internal joints.

**Critical fix — endpoint preservation:** The original code merged segments shorter than `max(total_length / (n_joints * 3), 0.03)`. This ate the tarsus joint because the tarsus is genuinely short (~2cm). Fix: NEVER merge the last segment. Endpoint joints are always kept.

### [7] Blender Script Generation

**Transform apply:** `bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)` — bakes the mesh's 90° rotation and location offset into the vertex data. After this, mesh.location = (0,0,0) and rotation = identity. Armature created at origin. Everything in the same flat world space. THIS WAS THE GHOST OFFSET BUG. Hours of debugging.

**Bone chain reversal:** The medial axis traces from endpoints (feet) inward (body). Bones created in this order have the foot as the PARENT. Fix: `joints[::-1]` before creating bones. Now: body→coxa→femur→tibia→tarsus. Parent-child propagation goes the right way.

**Two-layer weights:**

Layer 1 — BRANCH SEGMENTATION:
- For each vertex, compute distance to each branch's FULL CENTERLINE PATH
- Closest branch = this vertex's body part
- At branch junctions (leg meets body): distance-based blend between paths
- This replaces all body-priority heuristics

Layer 2 — RIGID PLATE WEIGHTING:
- Within the assigned body part, find closest bone
- Project onto bone to get parameter t (0=head, 1=tail)
- If t is near a joint (within JOINT_BLEND_WIDTH): linear blend between adjacent bones
- Otherwise: weight 1.0 to that bone (rigid chitin plate)

**Why two layers:** Bone proximity alone can't segment body parts because body bones (short sticks) are near leg bones (at the attachment). The abdomen bone is closer to rear leg vertices than the leg's own coxa. Branch paths solve this because they extend through the FULL length of each body part.

**Body-blend check:** At the HEAD of the FIRST bone (coxa, body end after reversal): blend with cephalothorax. NOT at the tail of the last bone (would anchor feet to body — this was a bug).

### [8] Animation

**Rotation space:** `PoseBone.rotation_quaternion` is in BONE-LOCAL space. Must transform desired axis from armature space to bone-local: `bone.matrix_local.to_3x3().inverted() @ armature_axis`.

**Bend axis computation:**
```python
mat = bone.matrix_local.to_3x3()
up_local = mat.inverted() @ Vector((0, 0, 1))
bone_y = Vector((0, 1, 0))  # bone direction in local space
bend = up_local.cross(bone_y)  # perpendicular to both
```
Negative angle = lift (rotate toward +Z in armature space).

**Swing axis:** armature Z transformed to bone-local. Swings the bone forward/backward in the horizontal plane (coxa's primary motion).

**Posture offset:** `FEMUR_ARCH` and `TIBIA_DROP` constants create the base leg arch. All animation layers on top. Changing these transforms the visual character of the same mesh (round→angular, docile→predatory).

**Gait formula:** For N alternating leg groups, `N × swing_fraction ≥ 1.0` for seamless motion. Two groups (alternating tripod) need ≥50% swing. Less = dead zone.

### [9] Autonomous Render Loop

**iterate.sh:** `bash tools/loop/iterate.sh [animation] [resolution] [camera]`

Pipeline:
1. Write config to `.render_config` (env vars unreliable across WSL→Windows)
2. Call Windows Blender headlessly: `blender.exe --background --python render_pipeline.py`
3. Blender imports spider.glb, runs rig script, runs animation script, renders PNG sequence
4. ffmpeg assembles PNGs into MP4
5. Vetinari grid tool chops MP4 into review grids
6. Grids at `/tmp/kore_output/grids/`

**Camera views:** side, front, top, 3/4. Set via KORE_CAMERA env var / config file.

**Render settings:** EEVEE, 16 samples, three-point lighting (key/fill/rim), camera auto-positioned from mesh bounding box.

**Blender 5.1 API change:** `action.fcurves` no longer exists. FCurves at `action.layers[].strips[].channelbags[].fcurves`. Handle both APIs with try/except.

---

## Bug Hall of Fame

In order of discovery. Each one cost hours.

| # | Bug | Symptom | Root Cause | Fix |
|---|-----|---------|------------|-----|
| 1 | Transform offset | Bones consistently 1-10cm outside mesh | Mesh had 90° rotation as object transform, armature didn't | `transform_apply` before rigging |
| 2 | Reversed chain | Rotating femur moved body, not foot | Bones built foot→body, parent-child backwards | `joints[::-1]` |
| 3 | Armature-space axes | Legs splay sideways instead of lifting | rotation_quaternion is bone-LOCAL, axes computed in armature space | `bone.matrix_local.to_3x3().inverted()` |
| 4 | Foot-to-body blend | Feet anchored to cephalothorax | Body-blend check on `chain[-1]` (foot end) instead of `chain[0]` (body end) | Flip condition to `chain_idx == 0` |
| 5 | Body priority bleed | Abdomen steals rear leg weights, coxa eaten by body | Bone proximity can't segment body parts | Two-layer weights: branch segmentation |
| 6 | Tarsus eaten | Mid legs missing tarsus bone | min_seg filter merges short endpoint segments | Never merge endpoint segments |
| 7 | Dead zone | All legs planted for 30% of cycle | SWING_FRACTION=0.35, two groups cover only 70% | SWING_FRACTION ≥ 0.50 |
| 8 | Flipper feet | Tarsus splays outward during swing | Tarsus curl (negative angle) around wrong-feeling axis | Keep tarsus at constant TIPTOE, no swing curl |
| 9 | WSL env vars | "threat" renders as "walk" | Environment variables unreliable across WSL→Windows | Config file fallback |
| 10 | Up-down pumping | Motion looks like pistons, not walking | Femur-dominant vertical animation, real spiders use coxa-dominant horizontal rowing | Redesign: COXA_SWING=14 primary, FEMUR_LIFT=6 secondary |

---

## Dependencies

```
Python: trimesh, numpy, scipy, scikit-image, rtree
Blender: 5.1 (Windows, called headlessly from WSL)
ffmpeg: for video assembly
Vetinari grid tool: ~/stitcher/contentGeneration/vetinari_cli.py
```

---

## Files

| File | Role |
|------|------|
| `tools/auto_rig.py` | Main pipeline: mesh → generated Blender script |
| `tools/rig_spider_auto.py` | Generated output: Blender Python that creates the rig |
| `tools/animate_prowl.py` | Burrow prowl: deliberate, rowing, predatory |
| `tools/animate_walk.py` | Generic walk cycle (v7, bone-local axes) |
| `tools/animate_threat.py` | Threat display v2: anticipation, fangs, snap-down |
| `tools/animate_feel.py` | Pedipalp sensing animation |
| `tools/rig_compiler.py` | Architecture prototype: LLM semantic layer |
| `tools/skeleton_extract.py` | Standalone skeleton extraction |
| `tools/analyze_spider_v4.py` | Orientation detection |
| `tools/loop/iterate.sh` | Autonomous render loop |
| `tools/loop/render_pipeline.py` | Headless Blender pipeline |
| `tools/loop/diagnose_feet.py` | Bone hierarchy diagnostic |
| `spider.glb` | The six-legged test spider |
