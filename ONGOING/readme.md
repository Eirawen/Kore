# Active Threads — Kore

Last updated: 2026-06-30

## Primary Mission: Text-Native Rigging and Animation Pipeline

### STATUS: PIPELINE WORKING — SPIDER WALKS AND THREATENS ✓

The full auto-rigging and animation pipeline is proven and autonomous.

### What Works (the whole stack)
1. ✅ Mesh → voxelize → 3D skeletonize (medial axis, multi-resolution)
2. ✅ Branch tracing + classification (legs, abdomen, pedipalps, fangs)
3. ✅ Joint detection (curvature analysis with minimum segment filtering)
4. ✅ Center refinement (surface averaging)
5. ✅ Bone placement inside mesh (transform_apply bakes mesh rotation)
6. ✅ Reversed bone chain (body→foot, not foot→body)
7. ✅ Two-layer weights: branch segmentation + rigid chitin plates
8. ✅ Bone-local rotation axes (rotation_quaternion in bone-local space)
9. ✅ Three animations: walk (alternating tripod), feel (pedipalps), threat display
10. ✅ Autonomous render loop: iterate.sh → Blender headless → ffmpeg → grid → review
11. ✅ Multi-camera rendering (side, front, top, 3/4)

### Key Architectural Discoveries

**Two-layer weights** — the breakthrough. Layer 1: branch segmentation using medial axis centerline paths (which body part). Layer 2: rigid plate physics within each segment (which bone). Replaced all body-priority heuristics. No more abdomen stealing rear legs, no more feet anchored to cephalothorax.

**Bone-local rotation axes** — rotation_quaternion is in BONE-LOCAL space, not armature space. Transform armature "up" to bone-local via `bone.matrix_local.to_3x3().inverted()`, then compute bend axis. Without this, legs splay sideways instead of lifting.

**Transform_apply** — the mesh had a 90° rotation as object transform. One line bakes it into vertices. This was the ghost offset for hours.

**Reversed bone chain** — medial axis traces foot→body, but bones need body→foot for parent-child propagation. `joints[::-1]`.

**Body-blend at wrong end** — the coxa-to-body blend check was on `chain_idx == len(chain)-1` (foot end after reversal) instead of `chain_idx == 0` (body end). Feet were literally weighted to cephalothorax.

### Autonomous Render Loop
```bash
bash tools/loop/iterate.sh walk 480x360 side
bash tools/loop/iterate.sh threat 480x360 3/4
bash tools/loop/iterate.sh feel 480x360 front
```
30 seconds per cycle. Headless Blender on Windows called from WSL. Config file for env var passing. Grid output at /tmp/kore_output/grids/.

### What Needs Work
- Walk cycle: feet lift now but need more visible stepping (body translation, overlapping action)
- Animation quality: apply Disney 12 principles systematically
- Rotation axis still produces some lateral splay — needs per-leg calibration
- 3k mesh limits deformation quality at joints
- Rig compiler (semantic LLM layer) is prototype only — not integrated
- Pipeline should generalize to non-arthropod meshes

### Files
- `tools/auto_rig.py` — main pipeline (mesh → Blender rig script)
- `tools/rig_spider_auto.py` — generated Blender script
- `tools/animate_walk.py` — walk cycle v7 (bone-local axes)
- `tools/animate_feel.py` — pedipalp sensing animation
- `tools/animate_threat.py` — threat display v2 (banger)
- `tools/rig_compiler.py` — architecture prototype
- `tools/loop/iterate.sh` — autonomous render loop
- `tools/loop/render_pipeline.py` — headless Blender pipeline
- `spider.glb` — the six-legged test spider
