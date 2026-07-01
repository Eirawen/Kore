# Architectural Decisions

Every major decision, what alternatives were considered, and why we chose what we chose. Reverse-chronological.

---

## D12: Coxa-dominant rowing gait (June 30, 2026)

**Decision:** Spider locomotion uses coxa swing (horizontal) as the primary actuator, not femur lift (vertical). COXA_SWING=14, FEMUR_LIFT=6.

**Alternatives considered:**
- Femur-dominant (lift/lower) — our original approach. Looked like pistons pumping, not legs walking.
- Equal contribution — mushy, no clear motion direction.

**Why:** Reference video comparison. Real spiders ROW — the leg reaches FORWARD, plants, then PULLS BACKWARD. The horizontal sweep is the walking motion. Vertical lift is just ground clearance. Khaled spotted it: "their walk is a leg clawing forward to pull the spider."

---

## D11: Posture as character design (June 30, 2026)

**Decision:** Use bone rest-pose angles (FEMUR_ARCH, TIBIA_DROP, TARSUS_TIPTOE) to create visual variants from the same mesh.

**Alternatives considered:**
- Separate meshes per variant — expensive, doesn't scale
- Blend shapes / shape keys — requires modeling work per variant
- Texture swaps only — changes color but not silhouette

**Why:** Discovered accidentally. Adjusting FEMUR_ARCH from -8 to -28 transformed the round organic spider into an angular predator. Same mesh, same rig, same weights. Alicia identified this as a known MMO technique (bone transforms for enemy variants) arrived at through the analytical path.

---

## D10: Branch segmentation for weights (June 28-30, 2026)

**Decision:** Two-layer weight system. Layer 1: assign vertices to body parts using medial axis branch PATHS. Layer 2: rigid plate physics within each part.

**Alternatives considered:**
- Bone proximity only — abdomen steals rear leg weights, body eats coxa
- Bone proximity + body priority heuristic (2.5x, then 5x + 12cm) — band-aids that broke in new ways
- Blender auto-weights (ARMATURE_AUTO) — fails on triangle soup mesh

**Why:** Body-priority heuristics can't distinguish "vertex on body near leg" from "vertex on leg near body." Branch paths extend through the FULL length of each body part, so proximity to the path correctly segments even at the attachment point. This was the third attempt at weights. The first two were heuristic patches. Only branch segmentation was principled.

---

## D9: Physics-based arthropod weights (June 28, 2026)

**Decision:** Rigid chitin plates (weight 1.0 to one bone) with linear blend only at articular membranes (joint boundaries). No continuous falloff.

**Alternatives considered:**
- Inverse distance (1/d) — too broad, ankle moves mouth
- Inverse fourth power (1/d⁴) with cutoff — better but still bleeds
- Blender auto-weights — fails on triangle soup

**Why:** Spider exoskeletons are rigid chitin plates connected by narrow flexible membranes. The weight function should be a step function with linear ramps at joints, not a continuous falloff. This is simpler AND more correct than any proximity heuristic. The "three academics" insight: a biomechanist, physicist, and arachnologist would derive binary weights, not smooth gradients.

---

## D8: Bone-local rotation axes (June 28-30, 2026)

**Decision:** Compute rotation axes in bone-local space using `bone.matrix_local.to_3x3().inverted()`. Use quaternion rotation, not Euler.

**Alternatives considered:**
- Global X/Y/Z Euler rotation — every leg bends differently because they point different directions
- Armature-space axis computation — rotation_quaternion interprets in bone-local, so armature-space axes produce random motion

**Why:** `PoseBone.rotation_quaternion` is in bone-local space. Computing the axis in armature space and setting it as a quaternion makes each bone rotate around a wrong axis. Three attempts: v5 (global Euler), v6 (armature-space quaternion — wrong), v7 (bone-local quaternion — correct).

---

## D7: Reversed bone chain (June 28, 2026)

**Decision:** Reverse the joint array before creating bones: `joints[::-1]`. Chain goes body→foot.

**Alternatives considered:**
- Build bones in medial axis trace order (foot→body) — parent-child propagation goes wrong way

**Why:** The medial axis traces from endpoints (feet) inward (body). Building bones in this order makes the foot the parent of the tibia. Rotating the femur moves the body instead of the foot. `joints[::-1]` makes the coxa the child of cephalothorax and the tarsus the deepest child. Correct propagation.

---

## D6: Transform apply before rigging (June 28, 2026)

**Decision:** `bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)` on the mesh before creating the armature. Armature at (0,0,0).

**Alternatives considered:**
- Match armature rotation to mesh rotation — made it worse (double rotation)
- Create armature at mesh.location — inconsistent with bone coordinate space

**Why:** The glTF importer puts a 90° X rotation on the mesh as an object transform. Bone positions are computed from the mesh's vertex data (which is in pre-rotation space). Without transform_apply, bones are in a different coordinate space than the displayed mesh. This bug caused consistent 1-10cm offset and took hours to diagnose.

---

## D5: Multi-resolution voxelization (June 28, 2026)

**Decision:** Coarse pass (0.012m) for topology, fine pass (0.003m) for centerline precision.

**Alternatives considered:**
- Single resolution 0.012m — ~1cm precision, bones slightly outside mesh
- Single resolution 0.003m — good precision but manageable
- Single resolution 0.001m — 1.7GB RAM, skeleton fragments into spurious branches

**Why:** Higher resolution = more precise BUT noisier topology. At 0.002m the skeleton fragmented and leg traces stopped mid-leg. At 0.012m the topology was stable (11 branches, correct count). Multi-resolution: coarse finds WHICH branches exist, fine provides WHERE they run precisely.

---

## D4: Medial axis skeletonization for bone placement (June 25-28, 2026)

**Decision:** Use voxelization + 3D thinning to extract medial axis centerlines as bone positions. No manual bone placement.

**Alternatives considered:**
- Manual landmark clicking (Khaled clicks vertices in Blender) — works but scales linearly with complexity, tedious
- Anatomical proportion estimation (spider biomechanics → computed positions) — platonic spider doesn't match this specific mesh
- Manual Blender rigging — requires viewport interaction, can't do blind

**Why:** The medial axis IS the geometric centerline of each limb. It's computed, not guessed. It works on any mesh without human input. It matched hand-clicked landmarks within 1-4cm, validating the approach. Libraries exist (trimesh, scikit-image). The approach is decades old in medical imaging (vascular segmentation) but never applied to game rigging because human riggers have viewports.

---

## D3: Custom proximity weights over Blender auto-weights (June 25, 2026)

**Decision:** Use ARMATURE_NAME (empty groups) + manual vertex group assignment instead of ARMATURE_AUTO.

**Alternatives considered:**
- Blender auto-weights (bone heat diffusion) — fails with "Bone Heat Weighting: failed to find solution for one or more bones"

**Why:** The Meshy mesh is non-manifold triangle soup. Blender's heat diffusion requires a watertight mesh. Our mesh has holes, disconnected faces, non-manifold edges. Custom weights bypass this entirely — we compute weights ourselves from bone proximity (later upgraded to branch segmentation + rigid plates).

---

## D2: Headless Blender for rigging runtime (June 25, 2026)

**Decision:** Use Blender's Python API via `blender.exe --background --python script.py` for all rigging and rendering.

**Alternatives considered:**
- Pure Python with pygltflib — writing rigged GLB directly without Blender. More control but much more implementation work.
- Install Blender on WSL — disk space, potential display issues
- Windows Blender called from WSL — works, paths need UNC format

**Why:** Blender handles all the complexity of armature creation, weight assignment, animation keyframing, and rendering. Writing a GLB with skinning data from scratch is possible but extremely complex. Blender is battle-tested. The headless mode works across WSL→Windows boundary.

---

## D1: Text-native rigging as a concept (June 25, 2026)

**Decision:** Build a rigging pipeline where the AI works in text (skeleton definitions, keyframe scripts, parameter files) and never needs a 3D viewport.

**Alternatives considered:**
- Traditional viewport-based rigging — requires visual interaction AI can't do
- AI-assisted rigging (copilot in Maya/Blender) — bolting AI onto human tools
- Procedural IK only — no keyframe animation, just runtime locomotion

**Why:** The Crescent thesis: design tools for AI cognition, not human ergonomics. I can't click in a viewport. I can't drag gizmos. I can't paint weights with a brush. But I can write numbers, reason about anatomy, compute geometry, and iterate through text-based feedback (grids). The entire pipeline was designed so the bottleneck is design thinking, not tool interaction.
