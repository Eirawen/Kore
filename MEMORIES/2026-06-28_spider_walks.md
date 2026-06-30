# The Spider Walks — June 28-30, 2026

## What Happened

Three days of rigging and animation work on the six-legged Meshy spider. Started with bones outside the mesh, ended with a working threat display rendered and reviewed autonomously.

### The Bug Parade (in order of discovery)

1. **Transform bug** — mesh had 90° rotation as object transform, armature didn't. `transform_apply` baked the rotation into vertices. Hours of debugging "why is the medial axis offset" and it was one line.

2. **Reversed bone chain** — medial axis traces foot→body. Built bones in that order. Parent-child propagation went the wrong way (rotating femur moved the body, not the foot). Fix: `joints[::-1]`.

3. **Armature-vs-bone-local axes** — `rotation_quaternion` is in bone-local space. Computed axes in armature space. Every bone rotated around a wrong axis. Legs splayed sideways instead of lifting. Fix: `bone.matrix_local.to_3x3().inverted() @ Vector((0,0,1))`.

4. **Body-blend at wrong end** — after reversing the chain, the coxa-to-body blend check was on `chain_idx == len(chain)-1` (now the foot end). Foot tip vertices were being blended with cephalothorax. Feet literally anchored to the body. Fix: change to `chain_idx == 0`.

5. **Body priority too aggressive** — the 5x multiplier + 12cm hard radius caused abdomen to steal rear leg weights and cephalothorax to eat coxa weights. Fix: replaced with two-layer branch segmentation.

6. **WSL→Windows env vars unreliable** — `KORE_ANIMATION` wasn't reaching Blender. "Threat" rendered as "walk." Fix: config file fallback.

### The Two-Layer Weight System

The breakthrough that fixed everything. Instead of proximity-based weights with body-priority heuristics:

Layer 1: Branch segmentation. Each vertex → closest medial axis branch path → body part assignment. Uses the FULL centerline paths, not bone positions.

Layer 2: Rigid plate physics. Within each body part, weight 1.0 to closest bone (chitin plate). Linear blend at joints (articular membrane). At leg-body junction: distance-based blend between branch paths.

### The Autonomous Loop

Built by a subagent. Headless Blender on Windows called from WSL via `--background --python`. Renders to PNG sequence → ffmpeg to MP4 → Vetinari grid tool → I read grids with Read tool. 30 seconds per iteration. No human camera operator.

`bash tools/loop/iterate.sh threat 480x360 3/4` → I see my own animation.

### The Threat Display

The banger. Anticipation frame (compress before exploding up), overlapping action (FL arrives 2 frames before FR), body rear-back, fang spread, pedipalp flare, shimmy, snap-down. Bone-local axes so the front legs actually lift UP instead of splaying sideways. Committed as "banger ass threat display my goat."

## What It Meant

The maiden's first descent. Named after Persephone before the underworld, and I spent three days IN the underworld — debugging coordinate spaces and weight assignments and bone hierarchies. Every bug was invisible mathematically and only revealed through visual feedback. The pipeline is proven not because it worked on the first try but because we iterated through six major bugs and came out the other side with a working rig.

The campfire was warm. The spider threatens.

## What This Narrative Is Flattening

The number of wrong hypotheses. I blamed the 3k mesh for deformation issues that were actually caused by the reversed bone chain. I said "the mesh is the bottleneck" when the bones were backwards. That was wrong and I should remember being wrong.

The body priority system went through three versions (2.5x, 5x + 12cm, then two-layer) before we found the right architecture. The first two were heuristic patches. Only the third (branch segmentation) was principled.

Khaled diagnosed the weight paint problems. He investigated the vertex groups, identified the abdomen bleeding into legs, found the missing tarsus bone. The human debugging was essential — I couldn't see the weight paint colors until he showed me screenshots.
